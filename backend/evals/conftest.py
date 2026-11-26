"""Shared fixtures, readability metrics, and LLM-as-Judge helpers for TypeForge evals.

DUAL-MODE EXECUTION:
  - Default (CI / Local fast mode): Uses a domain-aware deterministic LLM stub
    so the entire eval suite runs in <2 seconds without external network calls
    or rate-limit failures.
  - Live mode (`RUN_LIVE_EVALS=1 pytest evals/ -v`): Calls the live Groq API
    via Instructor for both generation and LLM-as-Judge evaluation.
"""
import os
import re
from typing import List
import pytest
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

import ai_service
from ai_service import _chat_structured
from auth import get_current_user
from limiter import limiter
from server import app
from topics_router import CATALOG


# ---------- LLM-as-Judge Pydantic Schemas ----------
class FactualJudgeVerdict(BaseModel):
    """Structured output schema for the LLM-as-Judge factual accuracy evaluator."""
    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Factual accuracy score from 1 (completely wrong) to 5 (technically accurate).",
    )
    is_accurate: bool = Field(
        ...,
        description="True if the passage contains no technical misconceptions.",
    )
    reasoning: str = Field(
        ...,
        min_length=10,
        description="Concise explanation justifying the factual accuracy score.",
    )


class GroundingJudgeVerdict(BaseModel):
    """Structured output schema for the LLM-as-Judge RAG grounding evaluator."""
    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Grounding score from 1 (hallucinated/off-topic) to 5 (strictly grounded in context).",
    )
    is_grounded: bool = Field(
        ...,
        description="True if all claims in the passage are supported by the source context.",
    )
    reasoning: str = Field(
        ...,
        min_length=10,
        description="Concise explanation of how well the passage adheres to the context.",
    )


class QAAlignmentVerdict(BaseModel):
    """Structured output schema for the LLM-as-Judge Question-Answer alignment evaluator."""
    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Alignment score from 1 (unrelated/evasive) to 5 (direct, complete interview answer).",
    )
    answers_question: bool = Field(
        ...,
        description="True if the answer directly and accurately addresses the question.",
    )
    has_no_filler: bool = Field(
        ...,
        description="True if the answer begins directly with the explanation without conversational filler.",
    )
    reasoning: str = Field(
        ...,
        min_length=10,
        description="Concise explanation of how well the answer addresses the question.",
    )


# ---------- Readability & Content Quality Helpers ----------
def count_syllables(word: str) -> int:
    """Estimate syllable count in an English word using vowel-group heuristics."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 1
    if len(word) <= 3:
        return 1
    # Remove silent trailing 'e'
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]
    vowel_groups = re.findall(r"[aeiouy]+", word)
    return max(1, len(vowel_groups))


def flesch_kincaid_grade(text: str) -> float:
    """Compute the Flesch-Kincaid Grade Level of a passage.

    Formula:
      0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
    """
    words = [w for w in text.split() if re.search(r"[a-zA-Z0-9]", w)]
    if not words:
        return 0.0
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    num_sentences = max(1, len(sentences))
    num_words = len(words)
    num_syllables = sum(count_syllables(w) for w in words)

    asl = num_words / num_sentences
    asw = num_syllables / num_words
    return round(0.39 * asl + 11.8 * asw - 15.59, 2)


# ---------- LLM-as-Judge Functions ----------
def llm_judge_factual_accuracy(domain: str, topic: str, passage: str) -> FactualJudgeVerdict:
    """Evaluate factual accuracy of a generated passage using an LLM-as-Judge."""
    if os.environ.get("RUN_LIVE_EVALS", "0") != "1":
        # Deterministic judge logic for fast CI mode: checks for known hallucination traps
        lower = passage.lower()
        if "tcp is a connectionless protocol" in lower or "never guarantees delivery" in lower:
            return FactualJudgeVerdict(
                score=1,
                is_accurate=False,
                reasoning="Passage falsely claims TCP is connectionless and unreliable, confusing it with UDP.",
            )
        return FactualJudgeVerdict(
            score=5,
            is_accurate=True,
            reasoning=f"Passage accurately explains core technical concepts of {topic} in {domain}.",
        )

    system = (
        "You are a senior computer science professor evaluating educational content. "
        "Grade the factual accuracy of the passage on a strict 1 to 5 scale. "
        "Return strict JSON matching the requested schema."
    )
    user_msg = f"""
Domain: {domain}
Topic: {topic}

Passage to evaluate:
\"\"\"{passage}\"\"\"

Rubric:
5 = Completely accurate and pedagogically sound.
4 = Accurate with minor simplifications appropriate for typing drills.
3 = Mostly accurate but vague or slightly misleading.
2 = Contains a clear technical error.
1 = Fundamentally wrong or hallucinated.
""".strip()

    return _chat_structured(
        system=system,
        user=user_msg,
        response_model=FactualJudgeVerdict,
        temperature=0.1,
        max_tokens=400,
    )


def llm_judge_rag_grounding(context: str, passage: str) -> GroundingJudgeVerdict:
    """Evaluate whether a RAG-generated passage is strictly grounded in the source context."""
    if os.environ.get("RUN_LIVE_EVALS", "0") != "1":
        ctx_words = {w.lower().strip(".,;:()") for w in context.split() if len(w) > 4}
        pass_words = {w.lower().strip(".,;:()") for w in passage.split() if len(w) > 4}
        overlap = len(ctx_words & pass_words)
        if overlap >= 3:
            return GroundingJudgeVerdict(
                score=5,
                is_grounded=True,
                reasoning="Passage directly teaches the B-Tree indexing concepts from the provided context excerpts.",
            )
        return GroundingJudgeVerdict(
            score=1,
            is_grounded=False,
            reasoning="Passage introduces external concepts not present anywhere in the provided source context.",
        )

    system = (
        "You are a strict RAG faithfulness evaluator. "
        "Verify whether the generated passage relies ONLY on facts present in the source context. "
        "Return strict JSON matching the requested schema."
    )
    user_msg = f"""
SOURCE CONTEXT:
\"\"\"{context}\"\"\"

GENERATED PASSAGE:
\"\"\"{passage}\"\"\"

Rubric:
5 = Every claim is directly supported by the source context.
4 = Grounded in the context with minor paraphrasing.
3 = Partially grounded but adds unsupported details.
2 = Mostly ignores the context.
1 = Completely ungrounded hallucination on a different topic.
""".strip()

    return _chat_structured(
        system=system,
        user=user_msg,
        response_model=GroundingJudgeVerdict,
        temperature=0.1,
        max_tokens=400,
    )


def llm_judge_qa_alignment(question: str, answer: str, topic: str = "") -> QAAlignmentVerdict:
    """Evaluate whether a generated model answer directly and cleanly answers the generated question."""
    if os.environ.get("RUN_LIVE_EVALS", "0") != "1":
        q_words = {w.lower().strip(".,;:?()") for w in question.split() if len(w) > 3}
        a_words = {w.lower().strip(".,;:?()") for w in answer.split() if len(w) > 3}
        lower_a = answer.lower().strip()
        has_filler = lower_a.startswith(("sure", "great question", "certainly", "the answer is"))
        overlap = len(q_words & a_words)
        if overlap >= 1 and not has_filler:
            return QAAlignmentVerdict(
                score=5,
                answers_question=True,
                has_no_filler=True,
                reasoning=f"Answer directly addresses the question on {topic or 'the concept'} without conversational filler.",
            )
        return QAAlignmentVerdict(
            score=1,
            answers_question=False,
            has_no_filler=not has_filler,
            reasoning="Answer is unrelated to the question or contains conversational filler.",
        )

    system = (
        "You are a technical interview evaluator grading Question-Answer alignment. "
        "Verify that the answer directly addresses the question in its opening sentence, "
        "contains zero conversational filler, and is technically sound. "
        "Return strict JSON matching the requested schema."
    )
    user_msg = f"""
Topic: {topic}
Question: {question}
Answer:
\"\"\"{answer}\"\"\"

Rubric:
5 = Directly, completely, and concisely answers the question with zero filler.
4 = Directly answers the question with minor stylistic imprecision.
3 = Partially answers the question or drifts off-topic.
2 = Evasive, starts with conversational filler, or barely addresses the question.
1 = Completely unrelated to the question.
""".strip()

    return _chat_structured(
        system=system,
        user=user_msg,
        response_model=QAAlignmentVerdict,
        temperature=0.1,
        max_tokens=400,
    )


# ---------- In-Memory MongoDB Stub for Isolated Evals ----------
class EvalCollection:
    def __init__(self):
        self.data = []

    async def insert_one(self, doc):
        self.data.append(dict(doc))
        return type("Result", (), {"inserted_id": doc.get("id")})()

    async def insert_many(self, docs):
        for d in docs:
            self.data.append(dict(d))
        return type("Result", (), {"inserted_ids": [d.get("id") for d in docs]})()

    def find(self, query=None, projection=None):
        results = []
        for item in self.data:
            if not query or all(item.get(k) == v for k, v in query.items()):
                res = dict(item)
                if projection:
                    for pk, pv in projection.items():
                        if pv == 0 and pk in res:
                            del res[pk]
                results.append(res)

        class Cursor:
            def __init__(self, items):
                self._items = items

            def sort(self, *args, **kwargs):
                return self

            async def to_list(self, length=100):
                return self._items[:length]

        return Cursor(results)

    async def find_one(self, query=None, projection=None):
        for item in self.data:
            if not query or all(item.get(k) == v for k, v in query.items()):
                res = dict(item)
                if projection:
                    for pk, pv in projection.items():
                        if pv == 0 and pk in res:
                            del res[pk]
                return res
        return None

    async def delete_many(self, query):
        self.data = [i for i in self.data if not all(i.get(k) == v for k, v in query.items())]

    async def delete_one(self, query):
        for idx, i in enumerate(self.data):
            if all(i.get(k) == v for k, v in query.items()):
                self.data.pop(idx)
                break


class EvalDB:
    def __init__(self):
        self.documents = EvalCollection()
        self.document_chunks = EvalCollection()
        self.sessions = EvalCollection()
        self.users = EvalCollection()


def _build_realistic_passage(user_prompt: str) -> dict:
    """Produce realistic domain-and-length-appropriate Q&A responses when RUN_LIVE_EVALS != 1."""
    if "CONTEXT FROM USER'S DOCUMENT:" in user_prompt:
        return {
            "question": "Why do B-Tree indexes outperform binary search trees on block storage systems?",
            "text": (
                "B-Trees are self-balancing search trees designed to work efficiently on block storage systems. "
                "Unlike binary search trees, each B-Tree node can store dozens of keys and child pointers, "
                "which keeps the tree height shallow and minimizes expensive disk I/O operations during lookups. "
                "Database engines rely on B-Tree indexes to guarantee logarithmic time complexity for point queries "
                "and ordered range scans across millions of records."
            ),
            "notes": [
                "B-Trees store multiple keys per node to reduce tree height and disk reads.",
                "All leaf nodes in a B-Tree remain at the same depth for balanced O(log n) lookups.",
                "Database indexes use B-Trees for fast point lookups and sequential range scans.",
            ],
        }

    # Determine target length from prompt
    is_short = "25-40 words" in user_prompt
    is_long = "90-130 words" in user_prompt

    # Extract topic from prompt
    topic_match = re.search(r"- Topic:\s*(.+)", user_prompt)
    topic = topic_match.group(1).strip() if topic_match else "Computer Science"

    question = f"How does {topic} optimize system behavior and prevent runtime bottlenecks in production architectures?"

    base_sentences = [
        f"{topic} is a foundational concept in software engineering that optimizes how systems process data and manage execution state.",
        f"When engineers design scalable architectures, understanding {topic} prevents subtle performance bottlenecks and memory hazards.",
        f"Modern runtimes implement strict invariants around {topic} to maintain predictable latency under heavy concurrent workloads.",
        f"In practice, mastering {topic} requires balancing algorithmic complexity against hardware cache locality and maintainability.",
        f"Careful benchmarking and profiling help developers verify that {topic} behaves deterministically in production environments.",
        f"By combining clear abstractions with rigorous testing, teams leverage {topic} to build resilient distributed applications.",
    ]

    if is_short:
        text = " ".join(base_sentences[:2])
    elif is_long:
        text = " ".join(base_sentences[:6])
    else:
        text = " ".join(base_sentences[:3])

    return {
        "question": question,
        "text": text,
        "notes": [
            f"{topic} directly impacts system scalability and runtime efficiency.",
            f"Understanding {topic} helps prevent common production bottlenecks.",
            f"Practical mastery of {topic} balances theory with hardware constraints.",
        ],
    }


@pytest.fixture
def eval_client(monkeypatch):
    """FastAPI TestClient configured for Phase 3 LLM evaluations."""
    db = EvalDB()
    app.state.db = db
    fake_user = {"id": "eval-user-1", "email": "eval@typeforge.app", "role": "user"}
    app.dependency_overrides[get_current_user] = lambda: fake_user

    # Reset rate limiter before each eval test so matrix tests never hit 429
    try:
        limiter.reset()
    except Exception:
        pass

    if os.environ.get("RUN_LIVE_EVALS", "0") != "1":
        import json

        def stub_chat(system: str, user: str, max_tokens: int = 900, temperature: float = 0.6) -> str:
            if "Analyze this typing session" in user:
                return json.dumps({
                    "summary": "Consistent typing cadence with minor hesitation on punctuation symbols.",
                    "weak_keys": ["p", ";", "-"],
                    "error_patterns": ["adjacent key transpositions", "missed shift on uppercase"],
                    "recommendations": [
                        "Practice slow deliberate intervals on punctuation",
                        "Focus on right-pinky key reach",
                        "Maintain steady rhythm before accelerating",
                    ],
                    "next_topics": ["Indexing", "Transactions", "Query Optimization"],
                })
            if "You write concise reinforcement notes" in system:
                return json.dumps({
                    "headline": "Core principles and practical architectural trade-offs.",
                    "bullets": [
                        "Optimizes system throughput and resource utilization",
                        "Reduces worst-case latency spikes under load",
                        "Pairs clean abstraction boundaries with deterministic execution",
                    ],
                    "memory_hooks": [
                        "Structure drives speed: organize state to minimize overhead",
                        "Measure first, optimize second",
                    ],
                })
            return json.dumps(_build_realistic_passage(user))

        monkeypatch.setenv("TESTING", "0")
        monkeypatch.setattr(ai_service, "_chat", stub_chat)

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


BTREE_DOCUMENT_CONTENT = b"""# Database Indexing and B-Trees
B-Trees are self-balancing search trees designed to work efficiently on block storage systems and relational databases.
Unlike binary search trees, each B-Tree node can store dozens of keys and child pointers, which keeps the tree height shallow and minimizes expensive disk I/O operations during lookups.
All leaf nodes in a B-Tree remain at the exact same depth, guaranteeing logarithmic O(log n) time complexity for insertions, deletions, and point searches.
Database engines rely on B-Tree indexes to accelerate WHERE clause filtering, JOIN operations, and ordered range scans across millions of rows.
When a B-Tree node overflows during insertion, it splits into two nodes and promotes the median key to the parent node to preserve balance.
"""


@pytest.fixture
def seeded_document_id(eval_client) -> str:
    """Upload a reference B-Tree document and return its document_id for RAG evals."""
    files = {"file": ("btree_notes.md", BTREE_DOCUMENT_CONTENT, "text/markdown")}
    resp = eval_client.post("/api/documents", files=files)
    assert resp.status_code == 200, f"Failed to seed eval document: {resp.text}"
    return resp.json()["id"]
