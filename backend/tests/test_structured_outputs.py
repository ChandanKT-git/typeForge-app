"""Phase 2 tests: Structured outputs, Pydantic guardrails, and Instructor integration."""
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

import ai_service
from ai_service import (
    GenerateLLMResponse,
    MistakeLLMResponse,
    SummaryLLMResponse,
    _chat_structured,
)
from server import app
from auth import get_current_user


def test_generate_llm_response_schema_guardrails():
    # Valid response passes
    valid = GenerateLLMResponse(
        text="A binary search tree maintains sorted keys for fast lookup operations.",
        notes=["BST lookup is O(log n) on average", "In-order traversal yields sorted keys"],
    )
    assert len(valid.text) >= 20
    assert len(valid.notes) == 2

    # Too short passage (< 20 chars) must fail Pydantic validation
    with pytest.raises(ValidationError):
        GenerateLLMResponse(text="Too short", notes=["Note 1"])

    # Empty notes list must fail Pydantic validation (min_length=1)
    with pytest.raises(ValidationError):
        GenerateLLMResponse(
            text="A binary search tree maintains sorted keys for fast lookup operations.",
            notes=[],
        )


def test_mistake_llm_response_schema_guardrails():
    valid = MistakeLLMResponse(
        summary="Strong typing speed with minor errors on punctuation.",
        weak_keys=["p", ";"],
        error_patterns=["missed semicolon"],
        recommendations=["Practice punctuation drills"],
        next_topics=["B-Trees"],
    )
    assert valid.weak_keys == ["p", ";"]

    # Too short summary (< 5 chars) must fail validation
    with pytest.raises(ValidationError):
        MistakeLLMResponse(summary="Hi")


def test_summary_llm_response_schema_guardrails():
    valid = SummaryLLMResponse(
        headline="Virtual memory abstracts physical RAM into contiguous address spaces.",
        bullets=["Page tables map virtual to physical frames"],
        memory_hooks=["VM = Virtual Map"],
    )
    assert "Virtual memory" in valid.headline

    with pytest.raises(ValidationError):
        SummaryLLMResponse(headline="No")


def test_instructor_client_invocation(monkeypatch):
    """Verify _chat_structured calls Instructor with response_model and max_retries."""
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            model_cls = kwargs["response_model"]
            return model_cls(
                text="Recursion solves problems by breaking them into smaller self-similar subproblems.",
                notes=["Base case stops recursion", "Call stack tracks frames"],
            )

    class FakeInstructorClient:
        def __init__(self):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setattr(ai_service, "_instructor_groq", lambda: FakeInstructorClient())

    res = _chat_structured(
        system="System prompt",
        user="User prompt",
        response_model=GenerateLLMResponse,
        max_retries=2,
        max_tokens=600,
        temperature=0.5,
    )
    assert isinstance(res, GenerateLLMResponse)
    assert captured["response_model"] is GenerateLLMResponse
    assert captured["max_retries"] == 2
    assert captured["max_tokens"] == 600
    assert captured["temperature"] == 0.5


def test_endpoints_with_structured_outputs(monkeypatch):
    """Verify /api/ai/generate, /api/ai/analyze, and /api/ai/summary return validated outputs."""
    fake_user = {"id": "u-1", "email": "user@typeforge.app", "role": "user"}
    app.dependency_overrides[get_current_user] = lambda: fake_user
    monkeypatch.setenv("TESTING", "1")
    client = TestClient(app)

    try:
        # 1. /api/ai/generate
        gen_resp = client.post(
            "/api/ai/generate",
            json={
                "domain": "Programming",
                "topic": "Recursion",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": False,
            },
        )
        assert gen_resp.status_code == 200, gen_resp.text
        gen_data = gen_resp.json()
        assert len(gen_data["text"]) >= 20
        assert len(gen_data["notes"]) >= 1

        # 2. /api/ai/analyze
        ana_resp = client.post(
            "/api/ai/analyze",
            json={
                "target": "Recursion solves problems cleanly.",
                "typed": "Recursion solves prblems cleanly.",
                "duration_seconds": 10.0,
                "wpm": 55.0,
                "accuracy": 95.0,
                "domain": "Programming",
                "topic": "Recursion",
            },
        )
        assert ana_resp.status_code == 200, ana_resp.text
        ana_data = ana_resp.json()
        assert ana_data["summary"] == "Good job"
        assert ana_data["weak_keys"] == ["a"]

        # 3. /api/ai/summary
        sum_resp = client.post(
            "/api/ai/summary",
            json={
                "text": "Recursion solves problems by breaking them into subproblems.",
                "domain": "Programming",
                "topic": "Recursion",
            },
        )
        assert sum_resp.status_code == 200, sum_resp.text
        sum_data = sum_resp.json()
        assert sum_data["headline"] == "Good job"
    finally:
        app.dependency_overrides.clear()
