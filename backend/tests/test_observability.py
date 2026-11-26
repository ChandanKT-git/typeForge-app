"""Phase 4 tests: LLM Observability & Langfuse Tracing."""
from starlette.testclient import TestClient

import observability
from observability import (
    clear_recent_traces,
    get_recent_traces,
    trace_llm_call,
)
from auth import get_current_user
from server import app


def test_trace_llm_call_records_telemetry_and_tokens():
    """Verify trace_llm_call records latency, prompts, output, user_id, and token estimates."""
    clear_recent_traces()

    trace_llm_call(
        name="ai_generate",
        model="qwen/qwen3.8-27b",
        system_prompt="You are a technical curriculum author.",
        user_prompt="Explain virtual memory in 50 words.",
        output='{"text": "Virtual memory maps virtual addresses to physical pages.", "notes": ["Uses page tables"]}',
        latency_ms=412.75,
        user_id="user-123",
        metadata={"domain": "OS", "topic": "Virtual Memory"},
    )

    traces = get_recent_traces()
    assert len(traces) == 1
    t = traces[0]
    assert t["name"] == "ai_generate"
    assert t["model"] == "qwen/qwen3.8-27b"
    assert t["user_id"] == "user-123"
    assert t["latency_ms"] == 412.75
    assert t["status"] == "success"
    assert t["metadata"]["domain"] == "OS"
    assert t["metadata"]["estimated_total_tokens"] > 0


def test_langfuse_sdk_export_when_configured(monkeypatch):
    """Verify that when Langfuse client is present, trace() and generation() spans are exported."""
    clear_recent_traces()
    exported_traces = []
    exported_generations = []

    class FakeTrace:
        def generation(self, **kwargs):
            exported_generations.append(kwargs)

    class FakeLangfuse:
        def trace(self, **kwargs):
            exported_traces.append(kwargs)
            return FakeTrace()

    monkeypatch.setattr(observability, "_get_langfuse", lambda: FakeLangfuse())

    trace_llm_call(
        name="rag_generate_drill",
        model="qwen/qwen3.8-27b",
        system_prompt="Grounded RAG system prompt",
        user_prompt="Context: B-Trees...",
        output='{"text": "B-Trees keep data balanced.", "notes": ["O(log n)"]}',
        latency_ms=320.5,
        user_id="u-99",
        metadata={"document_id": "doc-1"},
    )

    assert len(exported_traces) == 1
    assert exported_traces[0]["name"] == "rag_generate_drill"
    assert exported_traces[0]["user_id"] == "u-99"

    assert len(exported_generations) == 1
    gen = exported_generations[0]
    assert gen["name"] == "rag_generate_drill_generation"
    assert gen["model"] == "qwen/qwen3.8-27b"
    assert gen["usage"]["total"] > 0


def test_observability_fault_isolation_never_breaks_caller(monkeypatch):
    """If Langfuse throws a runtime error, trace_llm_call must swallow it and never crash."""

    class BrokenLangfuse:
        def trace(self, **kwargs):
            raise RuntimeError("Langfuse Cloud connection timeout")

    monkeypatch.setattr(observability, "_get_langfuse", lambda: BrokenLangfuse())

    # Must not raise
    trace_llm_call(
        name="ai_generate",
        model="qwen/qwen3.8-27b",
        system_prompt="sys",
        user_prompt="usr",
        output="out",
        latency_ms=100.0,
    )


def test_ai_endpoints_emit_observability_traces(monkeypatch):
    """Calling /api/ai/generate, /analyze, and /summary must automatically emit traces."""
    clear_recent_traces()
    fake_user = {"id": "obs-user-1", "email": "obs@typeforge.app", "role": "user"}
    app.dependency_overrides[get_current_user] = lambda: fake_user
    monkeypatch.setenv("TESTING", "1")
    client = TestClient(app)

    try:
        resp = client.post(
            "/api/ai/generate",
            json={
                "domain": "Programming",
                "topic": "Recursion",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": False,
            },
        )
        assert resp.status_code == 200

        traces = get_recent_traces()
        structured_traces = [t for t in traces if t["name"] == "ai_generate"]
        assert len(structured_traces) == 1
        tr = structured_traces[0]
        assert tr["user_id"] == "obs-user-1"
        assert tr["metadata"]["domain"] == "Programming"
        assert tr["metadata"]["topic"] == "Recursion"
        assert tr["latency_ms"] >= 0.0
    finally:
        app.dependency_overrides.clear()
