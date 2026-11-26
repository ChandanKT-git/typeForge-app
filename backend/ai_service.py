"""Groq-powered AI service: content generation (Concept Q&A + Code Passages), mistake analysis, summary.

PHASE 2 UPGRADE — STRUCTURED OUTPUTS & GUARDRAILS:
  Replaces fragile regex-based JSON parsing with Instructor + Pydantic response
  models. Instructor sends the Pydantic JSON schema to Groq, validates the LLM
  response automatically, and retries with validation-error feedback (up to
  max_retries) so the LLM can self-correct malformed output.

PHASE 4 UPGRADE — LLM OBSERVABILITY:
  Every LLM call (_chat and _chat_structured) is instrumented with high-resolution
  latency timing and traced via `observability.trace_llm_call` (Langfuse + local
  ring buffer), capturing model, prompts, structured output, token estimates,
  user_id, and domain/topic metadata.

PHASE 5 UPGRADE — SEMANTIC CACHING:
  Caches generated content in MongoDB (`generation_cache` with 24h TTL index)
  keyed by 384-d semantic embeddings (cosine similarity >= 0.92) and structural
  constraints including format version (`qa_v1` vs `passage_v1`).

Q&A RECALL MODE UPGRADE (PHASE A):
  Conceptual topics (`include_code=False`) generate a sharp interview/concept-check
  question (`question`) paired with a direct, single-paragraph model answer (`text`)
  enforced by `QALLMResponse` validators. Code runs (`include_code=True`) continue
  to generate code-focused passages (`mode="passage"`).
"""
import os
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar

import instructor
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from groq import Groq

from auth import get_current_user
from topics_router import CATALOG
from limiter import limiter
from observability import trace_llm_call
from text_processing import sanitize_for_typing

router = APIRouter(prefix="/ai", tags=["ai"])

GROQ_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
_raw_client: Optional[Groq] = None
_structured_client = None

T = TypeVar("T", bound=BaseModel)


def _groq() -> Groq:
    """Return a lazy-initialized raw Groq client."""
    global _raw_client
    if _raw_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
        _raw_client = Groq(api_key=api_key)
    return _raw_client


def _instructor_groq():
    """Return a lazy-initialized Instructor-patched Groq client."""
    global _structured_client
    if _structured_client is None:
        _structured_client = instructor.from_groq(_groq(), mode=instructor.Mode.JSON)
    return _structured_client


def _extract_json(text: str) -> dict:
    """Fallback helper to extract a JSON object from a raw string response."""
    if not text:
        return {}
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if m:
            text = m.group(1)
    try:
        return json.loads(text)
    except Exception:
        return {}


# ---------- API Request / Response Schemas ----------
class GenerateIn(BaseModel):
    domain: str = Field(..., description="Programming, DBMS, OS, Networking, AI/ML")
    topic: str
    difficulty: str = Field("Intermediate")
    length: str = Field("medium")  # short / medium / long
    include_code: bool = False
    bypass_cache: bool = False


class GenerateOut(BaseModel):
    question: Optional[str] = None
    text: str
    notes: List[str]
    domain: str
    topic: str
    difficulty: str
    mode: Literal["qa", "passage"] = "passage"


class MistakeIn(BaseModel):
    target: str
    typed: str
    duration_seconds: float
    wpm: float
    accuracy: float
    domain: Optional[str] = None
    topic: Optional[str] = None
    question: Optional[str] = None


class MistakeOut(BaseModel):
    summary: str
    weak_keys: List[str]
    error_patterns: List[str]
    recommendations: List[str]
    next_topics: List[str]


class SummaryIn(BaseModel):
    text: str
    domain: str
    topic: str
    question: Optional[str] = None


class SummaryOut(BaseModel):
    headline: str
    bullets: List[str]
    memory_hooks: List[str]


# ---------- Instructor LLM Structured Output Schemas ----------
class GenerateLLMResponse(BaseModel):
    """Pydantic schema enforced by Instructor for code/passage generation."""
    text: str = Field(
        ...,
        min_length=20,
        description="Clean, ASCII-only typing practice passage.",
    )
    notes: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1 to 5 concise learning takeaways from the passage.",
    )


FILLER_PREFIXES = (
    "sure",
    "great question",
    "good question",
    "certainly",
    "of course",
    "the answer is",
    "here is the answer",
    "to answer this question",
)

BULLET_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)


class QALLMResponse(BaseModel):
    """Pydantic schema enforced by Instructor for Concept Q&A generation.

    GUARDRAILS:
      1. `question` must be a single line (>= 10 chars) ending with '?'.
      2. `text` (the model answer) must be a direct single paragraph (>= 20 chars)
         with no conversational filler ("Sure!", "Great question!") and no bullet lists.
      3. `text` must not simply repeat `question` verbatim.
    """
    question: str = Field(
        ...,
        min_length=10,
        description="A sharp, single-line technical interview or concept-check question ending with '?'.",
    )
    text: str = Field(
        ...,
        min_length=20,
        description="A direct, single-paragraph ASCII-safe model answer to the question.",
    )
    notes: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1 to 5 concise learning takeaways from the Q&A.",
    )

    @field_validator("question")
    @classmethod
    def validate_question_format(cls, v: str) -> str:
        cleaned = v.strip()
        if "\n" in cleaned or "\r" in cleaned:
            raise ValueError("question must be a single line without newlines")
        if not cleaned.endswith("?"):
            raise ValueError("question must end with a question mark '?'")
        return cleaned

    @field_validator("text")
    @classmethod
    def validate_answer_format(cls, v: str) -> str:
        cleaned = v.strip()
        lower = cleaned.lower()
        for prefix in FILLER_PREFIXES:
            if lower.startswith(prefix):
                raise ValueError(
                    f"Answer must start directly with the technical explanation, not conversational filler ('{prefix}')"
                )
        if BULLET_LINE_RE.search(cleaned):
            raise ValueError("Answer must be a continuous prose paragraph without bullet points or numbered lists")
        return cleaned

    @model_validator(mode="after")
    def validate_answer_does_not_repeat_question(self) -> "QALLMResponse":
        q_norm = re.sub(r"\W+", " ", self.question.lower()).strip()
        a_norm = re.sub(r"\W+", " ", self.text.lower()).strip()
        if q_norm and a_norm.startswith(q_norm):
            raise ValueError("Answer must not repeat the question verbatim at the start")
        return self


class MistakeLLMResponse(BaseModel):
    """Pydantic schema enforced by Instructor for post-session mistake analysis."""
    summary: str = Field(
        default="Solid attempt. Focus on consistency and accuracy on tricky keys.",
        min_length=5,
        description="2 short sentences summarizing typing performance.",
    )
    weak_keys: List[str] = Field(
        default_factory=list,
        description="Single characters the user mistyped most often (max 6).",
    )
    error_patterns: List[str] = Field(
        default_factory=list,
        description="Observed error patterns such as transpositions or shift misses (max 5).",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="3 to 5 concrete typing drills or practice tips.",
    )
    next_topics: List[str] = Field(
        default_factory=list,
        description="3 recommended next topics in the same domain.",
    )


class SummaryLLMResponse(BaseModel):
    """Pydantic schema enforced by Instructor for concept reinforcement summaries."""
    headline: str = Field(
        ...,
        min_length=5,
        description="One-sentence key takeaway headline.",
    )
    bullets: List[str] = Field(
        default_factory=list,
        description="3 to 5 key learning points from the passage.",
    )
    memory_hooks: List[str] = Field(
        default_factory=list,
        description="2 to 3 mnemonic-style memory aids.",
    )


def _chat(system: str, user: str, max_tokens: int = 900, temperature: float = 0.6) -> str:
    """Raw string LLM completion (maintained for backward compatibility and test mocking)."""
    start = time.perf_counter()
    if os.environ.get("TESTING", "0") == "1":
        if "Analyze this typing session" in user:
            result = '{"summary": "Good job", "weak_keys": ["a"], "error_patterns": [], "recommendations": [], "next_topics": []}'
        elif "You write concise reinforcement notes" in system:
            result = '{"headline": "Good job", "bullets": [], "memory_hooks": []}'
        else:
            result = (
                '{"question": "How does this core computer science concept operate in practice?", '
                '"text": "This is a test paragraph that is purely ASCII.", '
                '"notes": ["Note 1"]}'
            )
        latency_ms = (time.perf_counter() - start) * 1000
        trace_llm_call(
            name="ai_chat_raw",
            model=GROQ_MODEL,
            system_prompt=system,
            user_prompt=user,
            output=result,
            latency_ms=latency_ms,
        )
        return result
    try:
        resp = _groq().chat.completions.create(
            model=GROQ_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        result = resp.choices[0].message.content or ""
        latency_ms = (time.perf_counter() - start) * 1000
        trace_llm_call(
            name="ai_chat_raw",
            model=GROQ_MODEL,
            system_prompt=system,
            user_prompt=user,
            output=result,
            latency_ms=latency_ms,
        )
        return result
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        trace_llm_call(
            name="ai_chat_raw",
            model=GROQ_MODEL,
            system_prompt=system,
            user_prompt=user,
            output="",
            latency_ms=latency_ms,
            status="error",
            error_message=str(e),
        )
        raise HTTPException(status_code=502, detail=f"AI provider error: {e}")


_DEFAULT_CHAT_FN = _chat


def _chat_structured(
    system: str,
    user: str,
    response_model: Type[T],
    max_retries: int = 2,
    max_tokens: int = 900,
    temperature: float = 0.6,
    trace_name: str = "ai_structured",
    user_id: Optional[str] = None,
    trace_metadata: Optional[Dict[str, Any]] = None,
) -> T:
    """Call Groq via Instructor, trace latency/tokens with Langfuse, and return a validated Pydantic model."""
    start = time.perf_counter()
    if os.environ.get("TESTING", "0") == "1" or _chat is not _DEFAULT_CHAT_FN:
        raw = _chat(system, user, max_tokens=max_tokens, temperature=temperature)
        data = _extract_json(raw)
        # Backward compatibility for legacy test mocks that only return {"text": ..., "notes": ...}
        if response_model is QALLMResponse and isinstance(data, dict) and "question" not in data and data.get("text"):
            data = {
                **data,
                "question": "How does this core technical concept operate in practice?",
            }
        try:
            validated = response_model.model_validate(data)
            latency_ms = (time.perf_counter() - start) * 1000
            trace_llm_call(
                name=trace_name,
                model=GROQ_MODEL,
                system_prompt=system,
                user_prompt=user,
                output=validated.model_dump_json(),
                latency_ms=latency_ms,
                user_id=user_id,
                metadata=trace_metadata,
            )
            return validated
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            trace_llm_call(
                name=trace_name,
                model=GROQ_MODEL,
                system_prompt=system,
                user_prompt=user,
                output=raw,
                latency_ms=latency_ms,
                user_id=user_id,
                metadata=trace_metadata,
                status="error",
                error_message=str(e),
            )
            raise HTTPException(status_code=502, detail=f"AI output failed schema validation: {e}")

    try:
        validated = _instructor_groq().chat.completions.create(
            model=GROQ_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=response_model,
            max_retries=max_retries,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        trace_llm_call(
            name=trace_name,
            model=GROQ_MODEL,
            system_prompt=system,
            user_prompt=user,
            output=validated.model_dump_json(),
            latency_ms=latency_ms,
            user_id=user_id,
            metadata=trace_metadata,
        )
        return validated
    except HTTPException:
        raise
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        trace_llm_call(
            name=trace_name,
            model=GROQ_MODEL,
            system_prompt=system,
            user_prompt=user,
            output="",
            latency_ms=latency_ms,
            user_id=user_id,
            metadata=trace_metadata,
            status="error",
            error_message=str(e),
        )
        raise HTTPException(status_code=502, detail=f"AI provider error: {e}")


# ---------- Phase 5: Semantic Caching ----------
SEMANTIC_CACHE_THRESHOLD = 0.92


async def check_semantic_cache(
    db: Any,
    request_text: str,
    threshold: float = SEMANTIC_CACHE_THRESHOLD,
    constraints: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Check if a semantically similar request was generated in the last 24 hours."""
    cache_col = getattr(db, "generation_cache", None)
    if cache_col is None:
        return None

    try:
        from document_router import cosine_similarity, embed_texts

        query_embedding = embed_texts([request_text])[0]
        entries = await cache_col.find({}, {"_id": 0}).to_list(500)

        best_score = 0.0
        best_entry = None
        for entry in entries:
            if constraints:
                entry_constraints = entry.get("constraints") or {}
                if any(entry_constraints.get(k) != v for k, v in constraints.items()):
                    continue
            emb = entry.get("embedding")
            if not emb:
                continue
            sim = cosine_similarity(query_embedding, emb)
            if sim > best_score:
                best_score = sim
                best_entry = entry

        if best_score >= threshold and best_entry is not None:
            return best_entry.get("response")
    except Exception:
        return None
    return None


async def store_semantic_cache(
    db: Any,
    request_text: str,
    response_data: Dict[str, Any],
    constraints: Optional[Dict[str, Any]] = None,
) -> None:
    """Embed `request_text` and store the generated response in `db.generation_cache`."""
    cache_col = getattr(db, "generation_cache", None)
    if cache_col is None:
        return

    try:
        from document_router import embed_texts

        query_embedding = embed_texts([request_text])[0]
        await cache_col.insert_one(
            {
                "request_text": request_text,
                "embedding": query_embedding,
                "response": response_data,
                "constraints": constraints or {},
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception:
        pass


# ---------- Endpoints ----------
@router.post("/generate", response_model=GenerateOut)
@limiter.limit("10/minute")
async def generate_content(payload: GenerateIn, request: Request, user: dict = Depends(get_current_user)):
    """Generate Concept Q&A (`include_code=False`) or Code Passage (`include_code=True`)."""
    if payload.domain not in CATALOG or payload.topic not in CATALOG[payload.domain]:
        raise HTTPException(status_code=400, detail="Invalid domain or topic")

    mode: Literal["qa", "passage"] = "passage" if payload.include_code else "qa"
    cache_format = "qa_v1" if mode == "qa" else "passage_v1"

    db = getattr(request.app.state, "db", None)
    cache_query_text = f"{payload.domain} : {payload.topic}"
    cache_constraints = {
        "domain": payload.domain,
        "difficulty": payload.difficulty,
        "length": payload.length.lower(),
        "include_code": payload.include_code,
        "format": cache_format,
    }

    # 1. Check Semantic Cache before calling Groq (unless bypass_cache=True)
    if not payload.bypass_cache and db is not None:
        cache_start = time.perf_counter()
        cached = await check_semantic_cache(
            db,
            request_text=cache_query_text,
            threshold=SEMANTIC_CACHE_THRESHOLD,
            constraints=cache_constraints,
        )
        if cached and cached.get("text") and (mode == "passage" or cached.get("question")):
            latency_ms = (time.perf_counter() - cache_start) * 1000
            trace_llm_call(
                name="ai_generate",
                model=GROQ_MODEL,
                system_prompt="SEMANTIC_CACHE_HIT",
                user_prompt=cache_query_text,
                output=json.dumps(cached),
                latency_ms=latency_ms,
                user_id=user.get("id"),
                metadata={
                    **cache_constraints,
                    "topic": payload.topic,
                    "mode": mode,
                    "cache_hit": True,
                },
            )
            return GenerateOut(
                question=cached.get("question") if mode == "qa" else None,
                text=cached["text"],
                notes=cached.get("notes") or [],
                domain=payload.domain,
                topic=payload.topic,
                difficulty=payload.difficulty,
                mode=mode,
            )

    length_map = {"short": "25-40 words", "medium": "50-80 words", "long": "90-130 words"}
    target_len = length_map.get(payload.length.lower(), "50-80 words")

    difficulty_question_guidance = {
        "Beginner": "Ask a foundational 'What is...' or 'How does X work at a basic level?' question.",
        "Intermediate": "Ask a practical 'How does X handle Y?' or 'When would you choose X over Y?' interview question.",
        "Advanced": "Ask a deep architectural 'Why does X trade off Y for Z under load?' or edge-case systems question.",
    }.get(payload.difficulty, "Ask a clear technical interview question.")

    if mode == "qa":
        system = (
            "You are a senior technical interviewer and curriculum author for a typing-while-learning app. "
            "You generate one sharp interview/concept-check question and one direct, single-paragraph model answer "
            "that the learner will type after mentally recalling the answer. "
            "Output STRICT JSON matching the requested schema. No markdown, no commentary."
        )
        user_msg = f"""
Generate a Concept Q&A typing drill for:
- Domain: {payload.domain}
- Topic: {payload.topic}
- Difficulty: {payload.difficulty} ({difficulty_question_guidance})
- Answer target length: {target_len}

Rules:
- `question`: ONE single-line question ending with '?'. No newlines.
- `text` (the model answer):
  - Directly answer the question in the very first words (NEVER start with "Sure", "Great question", "The answer is", etc.).
  - Single continuous paragraph of {target_len}. No bullet points or numbered lists.
  - Use only printable ASCII characters (a-z A-Z 0-9 and basic punctuation: . , ; : ' " ( ) - ?). No smart quotes, no emojis, no backticks.
- `notes`: 3 concise one-line takeaways summarizing key concepts from the answer.

Return JSON shape:
{{"question": "<question ending with ?>", "text": "<direct model answer paragraph>", "notes": ["..", "..", ".."]}}
""".strip()

        qa_result = _chat_structured(
            system,
            user_msg,
            response_model=QALLMResponse,
            max_tokens=900,
            temperature=0.55,
            trace_name="ai_generate",
            user_id=user.get("id"),
            trace_metadata={
                "domain": payload.domain,
                "topic": payload.topic,
                "difficulty": payload.difficulty,
                "length": payload.length,
                "include_code": payload.include_code,
                "mode": "qa",
                "cache_hit": False,
            },
        )
        question = sanitize_for_typing(qa_result.question.strip())
        question = re.sub(r"\s+", " ", question).strip()
        if not question.endswith("?"):
            question = question.rstrip(".!") + "?"

        text = sanitize_for_typing(qa_result.text.strip())
        text = re.sub(r"\s+", " ", text).strip()
        notes_list = [str(n) for n in qa_result.notes][:5]
    else:
        system = (
            "You are a curriculum author for a premium typing-while-learning app. "
            "Write clean, accurate, typing-friendly educational paragraphs about technical concepts. "
            "Output STRICT JSON matching the requested schema. No markdown, no commentary."
        )
        code_rule = (
            "Include ONE short inline code snippet inside the text using ASCII chars only "
            "(no smart quotes, no backticks, no emojis). Keep punctuation simple."
        )
        user_msg = f"""
Generate typing practice content for:
- Domain: {payload.domain}
- Topic: {payload.topic}
- Difficulty: {payload.difficulty}
- Approx length: {target_len}
- include_code: {payload.include_code}

Rules:
- Use only ASCII characters (a-z A-Z 0-9 and basic punctuation: . , ; : ' " ( ) - ?). No smart quotes. No emojis.
- Keep sentences typing-friendly (avoid unusual symbols).
- Be technically precise and educational.
- {code_rule}
- Provide 3 concise concept "notes" (one-liners) the user just learned.

Return JSON shape:
{{"text": "<paragraph>", "notes": ["..","..",".."]}}
""".strip()

        pass_result = _chat_structured(
            system,
            user_msg,
            response_model=GenerateLLMResponse,
            max_tokens=900,
            temperature=0.55,
            trace_name="ai_generate",
            user_id=user.get("id"),
            trace_metadata={
                "domain": payload.domain,
                "topic": payload.topic,
                "difficulty": payload.difficulty,
                "length": payload.length,
                "include_code": payload.include_code,
                "mode": "passage",
                "cache_hit": False,
            },
        )
        question = None
        text = sanitize_for_typing(pass_result.text.strip())
        text = re.sub(r"\s+", " ", text).strip()
        notes_list = [str(n) for n in pass_result.notes][:5]

    if not text:
        raise HTTPException(status_code=502, detail="AI returned empty content")

    # 2. Store in Semantic Cache with format version
    if db is not None:
        await store_semantic_cache(
            db,
            request_text=cache_query_text,
            response_data={"question": question, "text": text, "notes": notes_list, "mode": mode},
            constraints=cache_constraints,
        )

    return GenerateOut(
        question=question,
        text=text,
        notes=notes_list,
        domain=payload.domain,
        topic=payload.topic,
        difficulty=payload.difficulty,
        mode=mode,
    )


@router.post("/analyze", response_model=MistakeOut)
@limiter.limit("10/minute")
async def analyze_mistakes(payload: MistakeIn, request: Request, user: dict = Depends(get_current_user)):
    """Analyze typing mistakes with Instructor schema validation and observability tracing."""
    target = payload.target[:1500]
    typed = payload.typed[:1500]
    question_line = f"Question Answered: {payload.question}\n" if payload.question else ""

    system = (
        "You analyze typing performance and learning patterns. "
        "You return concise actionable JSON matching the schema. No markdown, no prose outside JSON."
    )
    user_msg = f"""
Analyze this typing session and produce JSON.

Domain: {payload.domain or "n/a"}
Topic: {payload.topic or "n/a"}
{question_line}WPM: {payload.wpm}
Accuracy: {payload.accuracy}%
Duration (s): {payload.duration_seconds}

TARGET:
\"\"\"{target}\"\"\"

TYPED:
\"\"\"{typed}\"\"\"

Output JSON shape:
{{
  "summary": "<2 short sentences>",
  "weak_keys": ["a","s",...],          // single chars the user mistypes most often (max 6)
  "error_patterns": ["transposition of e/r", "shift-key misses on capitals", ...],  // max 5
  "recommendations": ["...", "...", "..."],   // 3-5 concrete drills
  "next_topics": ["...", "...", "..."]        // 3 next topics in same domain
}}
""".strip()

    result = _chat_structured(
        system,
        user_msg,
        response_model=MistakeLLMResponse,
        max_tokens=700,
        temperature=0.4,
        trace_name="ai_analyze",
        user_id=user.get("id"),
        trace_metadata={
            "domain": payload.domain,
            "topic": payload.topic,
            "wpm": payload.wpm,
            "accuracy": payload.accuracy,
        },
    )
    return MistakeOut(
        summary=result.summary.strip()
        or "Solid attempt. Focus on consistency and accuracy on tricky keys.",
        weak_keys=[str(k)[:1] for k in result.weak_keys if str(k)][:6],
        error_patterns=[str(p) for p in result.error_patterns][:5],
        recommendations=[str(r) for r in result.recommendations][:6],
        next_topics=[str(t) for t in result.next_topics][:5],
    )


@router.post("/summary", response_model=SummaryOut)
@limiter.limit("10/minute")
async def concept_summary(payload: SummaryIn, request: Request, user: dict = Depends(get_current_user)):
    """Generate concept reinforcement notes with Instructor schema validation and observability tracing."""
    question_block = f"Question: {payload.question}\n" if payload.question else ""
    system = (
        "You write concise reinforcement notes for a learner who just typed a passage. "
        "Output STRICT JSON matching the requested schema."
    )
    user_msg = f"""
Domain: {payload.domain}
Topic: {payload.topic}
{question_block}
Passage just typed:
\"\"\"{payload.text[:2000]}\"\"\"

Return JSON:
{{
  "headline": "<one sentence takeaway>",
  "bullets": ["...","...","..."],     // 3-5 key learning points
  "memory_hooks": ["...","..."]       // 2-3 mnemonic-style memory aids
}}
""".strip()

    result = _chat_structured(
        system,
        user_msg,
        response_model=SummaryLLMResponse,
        max_tokens=550,
        temperature=0.5,
        trace_name="ai_summary",
        user_id=user.get("id"),
        trace_metadata={
            "domain": payload.domain,
            "topic": payload.topic,
        },
    )
    return SummaryOut(
        headline=result.headline.strip() or f"Quick recap of {payload.topic}.",
        bullets=[str(b) for b in result.bullets][:5],
        memory_hooks=[str(m) for m in result.memory_hooks][:3],
    )
