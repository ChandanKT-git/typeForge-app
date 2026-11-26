"""Phase C Evaluation 5: Question-Answer Alignment via LLM-as-Judge.

Verifies that in Concept Q&A mode:
  1. Every generated `text` (model answer) directly and accurately answers `question`.
  2. The answer starts immediately with the explanation (no conversational filler).
  3. The RAG `/api/documents/generate-drill` Q&A pair also passes alignment grading.
  4. Negative control: a mismatched Question/Answer pair is rejected (score <= 2/5).
"""
import pytest
from topics_router import CATALOG
from evals.conftest import llm_judge_qa_alignment


QA_ALIGNMENT_CASES = [
    ("Programming", CATALOG["Programming"][0]),
    ("DBMS", CATALOG["DBMS"][0]),
    ("OS", CATALOG["OS"][0]),
    ("Networking", CATALOG["Networking"][0]),
    ("AI/ML", CATALOG["AI/ML"][0]),
]


@pytest.mark.parametrize("domain,topic", QA_ALIGNMENT_CASES)
def test_generated_qa_passes_alignment_judge(eval_client, domain, topic):
    """Every conceptual /api/ai/generate Q&A pair must score >= 4/5 on Question-Answer alignment."""
    resp = eval_client.post(
        "/api/ai/generate",
        json={
            "domain": domain,
            "topic": topic,
            "difficulty": "Intermediate",
            "length": "medium",
            "include_code": False,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["mode"] == "qa"
    assert data["question"] and data["question"].endswith("?")

    verdict = llm_judge_qa_alignment(
        question=data["question"],
        answer=data["text"],
        topic=topic,
    )
    assert verdict.score >= 4, (
        f"Q&A alignment score {verdict.score}/5 too low for {domain}/{topic}: {verdict.reasoning}"
    )
    assert verdict.answers_question is True
    assert verdict.has_no_filler is True


def test_rag_drill_qa_passes_alignment_judge(eval_client, seeded_document_id):
    """RAG-generated Q&A drill from an uploaded document must pass Question-Answer alignment."""
    resp = eval_client.post(
        "/api/documents/generate-drill",
        json={
            "document_id": seeded_document_id,
            "query": "B-Tree disk I/O",
            "difficulty": "Intermediate",
            "length": "medium",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["mode"] == "qa"
    verdict = llm_judge_qa_alignment(
        question=data["question"],
        answer=data["text"],
        topic="B-Trees",
    )
    assert verdict.score >= 4, f"RAG Q&A alignment score {verdict.score}/5 too low: {verdict.reasoning}"
    assert verdict.answers_question is True


def test_qa_alignment_judge_rejects_mismatched_answer():
    """Negative control: an answer about CSS Flexbox paired with a question about B-Trees must score <= 2/5."""
    question = "Why do B-Tree database indexes minimize disk seek operations compared to binary search trees?"
    mismatched_answer = (
        "CSS Flexbox aligns container items along a main axis and cross axis using justify-content "
        "and align-items properties for responsive browser layouts."
    )
    verdict = llm_judge_qa_alignment(
        question=question,
        answer=mismatched_answer,
        topic="B-Trees",
    )
    assert verdict.score <= 2, f"Expected judge to penalize mismatched Q&A, got {verdict.score}/5"
    assert verdict.answers_question is False
