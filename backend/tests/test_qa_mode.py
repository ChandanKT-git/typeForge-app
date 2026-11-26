"""Phase A tests: Concept Q&A schemas, validators, mode routing, RAG Q&A, cache versioning, and session fields."""
import asyncio
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

import ai_service
from ai_service import QALLMResponse, check_semantic_cache, store_semantic_cache
from auth import get_current_user
from limiter import limiter
from server import app
from sessions_router import SessionCreate, SessionOut
from tests.test_document_e2e import FakeDB


def test_qa_llm_response_validators():
    """Verify QALLMResponse accepts valid Q&A and rejects malformed questions, filler, repetition, and bullets."""
    valid = QALLMResponse(
        question="Why do B-Trees outperform binary search trees on disk-backed storage?",
        text=(
            "B-Trees pack dozens of keys into each node to match disk block sizes, "
            "which keeps the tree height shallow and minimizes expensive disk seek operations."
        ),
        notes=["High branching factor reduces tree height", "Matches OS page/block size"],
    )
    assert valid.question.endswith("?")

    # 1. Question without '?' must fail
    with pytest.raises(ValidationError, match="question mark"):
        QALLMResponse(
            question="Explain how B-Trees work on disk storage",
            text="B-Trees store multiple keys per node to reduce disk I/O operations.",
            notes=["Note 1"],
        )

    # 2. Multi-line question must fail
    with pytest.raises(ValidationError, match="single line"):
        QALLMResponse(
            question="Line one of question\nLine two ending with?",
            text="B-Trees store multiple keys per node to reduce disk I/O operations.",
            notes=["Note 1"],
        )

    # 3. Answer starting with conversational filler must fail
    for filler in [
        "Sure, B-Trees store multiple keys per node to reduce disk I/O operations.",
        "Great question! B-Trees store multiple keys per node to reduce disk I/O.",
        "The answer is that B-Trees store multiple keys per node on disk.",
    ]:
        with pytest.raises(ValidationError, match="conversational filler"):
            QALLMResponse(
                question="Why do B-Trees outperform binary search trees on disk?",
                text=filler,
                notes=["Note 1"],
            )

    # 4. Answer containing markdown bullet list must fail
    with pytest.raises(ValidationError, match="bullet points"):
        QALLMResponse(
            question="What are the primary properties of a B-Tree index?",
            text="A B-Tree has two key properties:\n- Self-balancing nodes\n- High branching factor",
            notes=["Note 1"],
        )

    # 5. Answer verbatim repeating the question at the start must fail
    with pytest.raises(ValidationError, match="repeat the question"):
        QALLMResponse(
            question="Why do B-Trees outperform binary search trees on disk?",
            text="Why do B-Trees outperform binary search trees on disk? Because they minimize disk seeks.",
            notes=["Note 1"],
        )


def test_generate_mode_routing_qa_vs_passage(monkeypatch):
    """Verify include_code=False routes to mode='qa' and include_code=True routes to mode='passage'."""
    fake_db = FakeDB()
    app.state.db = fake_db
    fake_user = {"id": "qa-user-1", "email": "qa@typeforge.app", "role": "user"}
    app.dependency_overrides[get_current_user] = lambda: fake_user
    try:
        limiter.reset()
    except Exception:
        pass
    monkeypatch.setenv("TESTING", "1")
    client = TestClient(app)

    try:
        # 1. Conceptual run (include_code=False) -> mode="qa" with question
        r_qa = client.post(
            "/api/ai/generate",
            json={
                "domain": "Programming",
                "topic": "Recursion",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": False,
            },
        )
        assert r_qa.status_code == 200, r_qa.text
        data_qa = r_qa.json()
        assert data_qa["mode"] == "qa"
        assert data_qa["question"] is not None
        assert data_qa["question"].endswith("?")
        assert len(data_qa["text"]) >= 20

        # 2. Code run (include_code=True) -> mode="passage" with question=None
        r_code = client.post(
            "/api/ai/generate",
            json={
                "domain": "Programming",
                "topic": "Recursion",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": True,
            },
        )
        assert r_code.status_code == 200, r_code.text
        data_code = r_code.json()
        assert data_code["mode"] == "passage"
        assert data_code["question"] is None
        assert len(data_code["text"]) >= 20
    finally:
        app.dependency_overrides.clear()


def test_rag_generate_drill_returns_grounded_qa(monkeypatch):
    """Verify /api/documents/generate-drill returns mode='qa' and a grounded question."""
    fake_db = FakeDB()
    app.state.db = fake_db
    fake_user = {"id": "qa-user-2", "email": "qa2@typeforge.app", "role": "user"}
    app.dependency_overrides[get_current_user] = lambda: fake_user
    monkeypatch.setenv("TESTING", "1")
    client = TestClient(app)

    try:
        content = (
            b"# Raft Consensus Notes\n"
            b"Raft achieves distributed consensus via leader election and log replication across a cluster.\n"
            b"A candidate must receive votes from a majority quorum of nodes to become the active leader.\n"
            b"Followers append log entries in strict sequential order as dictated by the leader's heartbeat RPCs.\n"
        )
        up = client.post("/api/documents", files={"file": ("raft.md", content, "text/markdown")})
        assert up.status_code == 200
        doc_id = up.json()["id"]

        drill = client.post(
            "/api/documents/generate-drill",
            json={"document_id": doc_id, "query": "leader election", "difficulty": "Intermediate"},
        )
        assert drill.status_code == 200, drill.text
        d = drill.json()
        assert d["mode"] == "qa"
        assert d["question"] is not None
        assert d["question"].endswith("?")
        assert len(d["text"]) >= 20
    finally:
        app.dependency_overrides.clear()


def test_semantic_cache_format_version_isolation():
    """Verify an old passage cache entry (without format='qa_v1') is never served for a Q&A request."""
    from tests.test_semantic_cache import CacheFakeDB

    db = CacheFakeDB()

    async def _run():
        # Store legacy passage entry without format="qa_v1"
        await store_semantic_cache(
            db,
            request_text="Programming : Recursion",
            response_data={"text": "Legacy paragraph without question.", "notes": ["Note 1"]},
            constraints={
                "domain": "Programming",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": False,
            },
        )

        # Querying with format="qa_v1" must MISS the legacy entry
        miss = await check_semantic_cache(
            db,
            request_text="Programming : Recursion",
            constraints={
                "domain": "Programming",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": False,
                "format": "qa_v1",
            },
        )
        assert miss is None

        # Store a qa_v1 entry and verify it HITS and returns the question
        await store_semantic_cache(
            db,
            request_text="Programming : Recursion",
            response_data={
                "question": "What prevents infinite recursion in a recursive function?",
                "text": "A well-defined base case terminates recursion before exhausting stack frames.",
                "notes": ["Base case stops recursion"],
                "mode": "qa",
            },
            constraints={
                "domain": "Programming",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": False,
                "format": "qa_v1",
            },
        )

        hit = await check_semantic_cache(
            db,
            request_text="Programming : Recursion",
            constraints={
                "domain": "Programming",
                "difficulty": "Intermediate",
                "length": "medium",
                "include_code": False,
                "format": "qa_v1",
            },
        )
        assert hit is not None
        assert hit["question"] == "What prevents infinite recursion in a recursive function?"

    asyncio.run(_run())


def test_session_models_support_question_and_recall_ms():
    """Verify SessionCreate and SessionOut persist question and recall_ms while defaulting to None."""
    with_qa = SessionCreate(
        domain="OS",
        topic="Virtual Memory",
        difficulty="Advanced",
        question="Why do multi-level page tables reduce memory overhead compared to a flat page table?",
        recall_ms=4250,
        target_text="Multi-level page tables only allocate inner page table nodes for active virtual address regions.",
        typed_text="Multi-level page tables only allocate inner page table nodes for active virtual address regions.",
        duration_seconds=18.2,
        wpm=64.0,
        raw_wpm=65.0,
        accuracy=99.0,
        correct_chars=95,
        incorrect_chars=1,
        total_chars=96,
    )
    assert with_qa.question.endswith("?")
    assert with_qa.recall_ms == 4250

    out = SessionOut(id="sess-qa-1", created_at="2026-11-26T00:00:00Z", **with_qa.model_dump())
    assert out.question == with_qa.question
    assert out.recall_ms == 4250

