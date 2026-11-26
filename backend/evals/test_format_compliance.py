"""Phase 3 Evaluation 1: Format Compliance & Schema Adherence.

Verifies that every AI endpoint (/generate, /analyze, /summary, and
/documents/generate-drill) returns 100% schema-valid responses conforming
to our Pydantic models across diverse CS domains, topics, and difficulty tiers.
"""
import pytest
from ai_service import GenerateOut, MistakeOut, SummaryOut
from document_router import GenerateFromDocOut
from topics_router import CATALOG


# Build a test matrix across 5 distinct domains in CATALOG
FORMAT_TEST_CASES = [
    ("Programming", CATALOG["Programming"][0], "Beginner"),
    ("DBMS", CATALOG["DBMS"][0], "Intermediate"),
    ("OS", CATALOG["OS"][0], "Advanced"),
    ("Networking", CATALOG["Networking"][0], "Beginner"),
    ("AI/ML", CATALOG["AI/ML"][0], "Intermediate"),
]


@pytest.mark.parametrize("domain,topic,difficulty", FORMAT_TEST_CASES)
def test_generate_endpoint_format_compliance(eval_client, domain, topic, difficulty):
    """Every /api/ai/generate call must return a valid GenerateOut schema."""
    response = eval_client.post(
        "/api/ai/generate",
        json={
            "domain": domain,
            "topic": topic,
            "difficulty": difficulty,
            "length": "medium",
            "include_code": False,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # Validate against Pydantic schema
    result = GenerateOut.model_validate(data)
    assert len(result.text) >= 20
    assert 1 <= len(result.notes) <= 5
    assert result.domain == domain
    assert result.topic == topic
    assert result.difficulty == difficulty


def test_analyze_endpoint_format_compliance(eval_client):
    """/api/ai/analyze must return a valid MistakeOut schema with single-char weak_keys."""
    response = eval_client.post(
        "/api/ai/analyze",
        json={
            "target": "Virtual memory maps virtual addresses to physical RAM frames using page tables.",
            "typed": "Virtual memry maps virtual adresses to physical RAM frames using page tables.",
            "duration_seconds": 18.4,
            "wpm": 52.0,
            "accuracy": 94.5,
            "domain": "OS",
            "topic": CATALOG["OS"][0],
        },
    )
    assert response.status_code == 200, response.text
    result = MistakeOut.model_validate(response.json())

    assert len(result.summary) >= 5
    assert len(result.weak_keys) <= 6
    for key in result.weak_keys:
        assert len(key) == 1, f"Expected single-character weak key, got '{key}'"
    assert len(result.error_patterns) <= 5
    assert len(result.recommendations) <= 6
    assert len(result.next_topics) <= 5


def test_summary_endpoint_format_compliance(eval_client):
    """/api/ai/summary must return a valid SummaryOut schema."""
    response = eval_client.post(
        "/api/ai/summary",
        json={
            "text": "B-Trees maintain balanced leaf depths to guarantee logarithmic lookup performance.",
            "domain": "DBMS",
            "topic": CATALOG["DBMS"][0],
        },
    )
    assert response.status_code == 200, response.text
    result = SummaryOut.model_validate(response.json())

    assert len(result.headline) >= 5
    assert len(result.bullets) <= 5
    assert len(result.memory_hooks) <= 3


def test_rag_drill_endpoint_format_compliance(eval_client, seeded_document_id):
    """/api/documents/generate-drill must return a valid GenerateFromDocOut schema."""
    response = eval_client.post(
        "/api/documents/generate-drill",
        json={
            "document_id": seeded_document_id,
            "query": "B-Tree node splitting",
            "difficulty": "Intermediate",
            "length": "medium",
        },
    )
    assert response.status_code == 200, response.text
    result = GenerateFromDocOut.model_validate(response.json())

    assert len(result.text) >= 20
    assert 1 <= len(result.notes) <= 5
    assert len(result.source_chunks) >= 1
    assert result.domain == "Custom Document"
    assert result.topic == "btree_notes.md"
