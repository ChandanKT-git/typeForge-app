"""Phase 5 tests: Semantic Caching with MongoDB & Vector Cosine Similarity."""
import asyncio
from datetime import datetime
import pytest
from starlette.testclient import TestClient

import ai_service
from ai_service import check_semantic_cache, store_semantic_cache
from auth import get_current_user
from limiter import limiter
from observability import clear_recent_traces, get_recent_traces
from server import app
from tests.test_document_e2e import FakeCollection


class CacheFakeDB:
    def __init__(self):
        self.generation_cache = FakeCollection()


def test_semantic_cache_hit_on_identical_and_near_identical_queries():
    """Verify store_semantic_cache and check_semantic_cache hit when similarity >= 0.92."""
    db = CacheFakeDB()

    async def _run():
        await store_semantic_cache(
            db,
            request_text="Programming : Recursion and Recursive Functions",
            response_data={
                "text": "Recursion solves complex problems by reducing them to simpler instances.",
                "notes": ["Requires a base case", "Uses call stack frames"],
            },
            constraints={"difficulty": "Intermediate", "length": "medium", "include_code": False},
        )

        # Verify native datetime stored for MongoDB TTL index compatibility
        stored_doc = db.generation_cache.data[0]
        assert isinstance(stored_doc["created_at"], datetime)

        # 1. Exact semantic match -> HIT
        hit = await check_semantic_cache(
            db,
            request_text="Programming : Recursion and Recursive Functions",
            threshold=0.92,
            constraints={"difficulty": "Intermediate", "length": "medium", "include_code": False},
        )
        assert hit is not None
        assert "Recursion solves complex problems" in hit["text"]

        # 2. Completely different topic -> MISS
        miss = await check_semantic_cache(
            db,
            request_text="Networking : TCP Congestion Control and Sliding Windows",
            threshold=0.92,
            constraints={"difficulty": "Intermediate", "length": "medium", "include_code": False},
        )
        assert miss is None

        # 3. Same topic but different length constraint ('long' vs 'medium') -> MISS
        constraint_miss = await check_semantic_cache(
            db,
            request_text="Programming : Recursion and Recursive Functions",
            threshold=0.92,
            constraints={"difficulty": "Intermediate", "length": "long", "include_code": False},
        )
        assert constraint_miss is None

    asyncio.run(_run())


def test_generate_endpoint_uses_semantic_cache_and_skips_second_llm_call(monkeypatch):
    """End-to-end test: second call to /api/ai/generate hits semantic cache without calling LLM."""
    db = CacheFakeDB()
    app.state.db = db
    fake_user = {"id": "cache-user-1", "email": "cache@typeforge.app", "role": "user"}
    app.dependency_overrides[get_current_user] = lambda: fake_user
    try:
        limiter.reset()
    except Exception:
        pass

    llm_call_count = {"count": 0}

    def counting_chat(system: str, user: str, max_tokens: int = 900, temperature: float = 0.6) -> str:
        llm_call_count["count"] += 1
        return '{"text": "Recursion breaks a problem into smaller self-similar subproblems with a base case.", "notes": ["Base case terminates recursion"]}'

    monkeypatch.setenv("TESTING", "0")
    monkeypatch.setattr(ai_service, "_chat", counting_chat)
    clear_recent_traces()
    client = TestClient(app)

    try:
        payload = {
            "domain": "Programming",
            "topic": "Recursion",
            "difficulty": "Intermediate",
            "length": "medium",
            "include_code": False,
        }

        # First request: Cache MISS -> calls LLM (count becomes 1)
        r1 = client.post("/api/ai/generate", json=payload)
        assert r1.status_code == 200, r1.text
        assert llm_call_count["count"] == 1

        # Second identical request: Cache HIT -> does NOT call LLM (count stays 1)
        r2 = client.post("/api/ai/generate", json=payload)
        assert r2.status_code == 200, r2.text
        assert r2.json()["text"] == r1.json()["text"]
        assert llm_call_count["count"] == 1

        # Verify observability recorded cache_hit=True on the second request
        traces = [t for t in get_recent_traces() if t["name"] == "ai_generate"]
        assert len(traces) == 2
        assert traces[0]["metadata"]["cache_hit"] is False
        assert traces[1]["metadata"]["cache_hit"] is True

        # Third request with bypass_cache=True -> forces fresh LLM generation (count becomes 2)
        r3 = client.post("/api/ai/generate", json={**payload, "bypass_cache": True})
        assert r3.status_code == 200
        assert llm_call_count["count"] == 2
    finally:
        app.dependency_overrides.clear()
