"""Tests for Session models backward compatibility."""
from sessions_router import SessionCreate, SessionOut


def test_session_create_backward_compatibility():
    payload = {
        "domain": "Programming",
        "topic": "Recursion",
        "difficulty": "Intermediate",
        "target_text": "Sample target text for testing typing arena.",
        "typed_text": "Sample target text for testing typing arena.",
        "duration_seconds": 12.5,
        "wpm": 60.0,
        "raw_wpm": 62.0,
        "accuracy": 98.5,
        "correct_chars": 44,
        "incorrect_chars": 1,
        "total_chars": 45,
    }
    session = SessionCreate(**payload)
    assert session.source_type == "ai"
    assert session.source_document_id is None


def test_session_create_document_source():
    payload = {
        "domain": "Custom Document",
        "topic": "os_notes.pdf",
        "difficulty": "Intermediate",
        "source_type": "document",
        "source_document_id": "doc-uuid-1234",
        "target_text": "Virtual memory abstracts physical RAM into pages.",
        "typed_text": "Virtual memory abstracts physical RAM into pages.",
        "duration_seconds": 15.0,
        "wpm": 55.0,
        "raw_wpm": 56.0,
        "accuracy": 100.0,
        "correct_chars": 50,
        "incorrect_chars": 0,
        "total_chars": 50,
    }
    session = SessionCreate(**payload)
    assert session.source_type == "document"
    assert session.source_document_id == "doc-uuid-1234"


def test_session_out_defaults():
    session_out = SessionOut(
        id="s-1",
        domain="OS",
        topic="Paging",
        difficulty="Intermediate",
        duration_seconds=10.0,
        wpm=50.0,
        raw_wpm=50.0,
        accuracy=100.0,
        correct_chars=40,
        incorrect_chars=0,
        total_chars=40,
        error_chars=[],
        target_text="text",
        typed_text="text",
        created_at="2026-10-13T00:00:00Z",
    )
    assert session_out.source_type == "ai"
    assert session_out.source_document_id is None
