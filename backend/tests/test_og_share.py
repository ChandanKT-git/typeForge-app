"""Tests for the public OG image share endpoints (1200x630 PNG + meta JSON)."""
import os
import io
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def user_and_session():
    """Register a fresh user and create a real session to share."""
    email = f"TEST_og_{uuid.uuid4().hex[:8]}@typeforge.app"
    r = requests.post(
        f"{API}/auth/register",
        json={"email": email, "password": "Test@1234", "name": "OG Tester"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "domain": "DBMS",
        "topic": "INNER JOIN",
        "difficulty": "Intermediate",
        "target_text": "SELECT * FROM a INNER JOIN b ON a.id = b.a_id;",
        "typed_text":  "SELECT * FROM a INNER JOIN b ON a.id = b.a_id;",
        "duration_seconds": 30.5,
        "wpm": 55.2,
        "raw_wpm": 60.0,
        "accuracy": 96.4,
        "correct_chars": 47,
        "incorrect_chars": 2,
        "total_chars": 49,
        "error_chars": ["e", "n"],
    }
    r = requests.post(f"{API}/sessions", headers=headers, json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return {"token": token, "headers": headers, "session": r.json()}


# ---------- OG PNG ----------
class TestOGPng:
    def test_png_status_and_content_type(self, user_and_session):
        sid = user_and_session["session"]["id"]
        # PUBLIC - no auth header
        r = requests.get(f"{API}/og/sessions/{sid}.png", timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("Content-Type", "").startswith("image/png")
        # sanity: body begins with PNG signature
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(r.content) > 1000  # non-trivial

    def test_png_dimensions_1200x630(self, user_and_session):
        sid = user_and_session["session"]["id"]
        r = requests.get(f"{API}/og/sessions/{sid}.png", timeout=30)
        assert r.status_code == 200
        try:
            from PIL import Image
        except Exception:
            pytest.skip("Pillow not available in test env")
        img = Image.open(io.BytesIO(r.content))
        assert img.size == (1200, 630), f"expected (1200,630), got {img.size}"

    def test_png_is_public_no_auth(self, user_and_session):
        """Explicitly confirm no Authorization header required."""
        sid = user_and_session["session"]["id"]
        s = requests.Session()  # no auth
        r = s.get(f"{API}/og/sessions/{sid}.png", timeout=30)
        assert r.status_code == 200

    def test_png_unknown_session_404(self):
        bogus = uuid.uuid4().hex
        r = requests.get(f"{API}/og/sessions/{bogus}.png", timeout=15)
        assert r.status_code == 404


# ---------- OG meta ----------
class TestOGMeta:
    def test_meta_shape_and_no_leak(self, user_and_session):
        sid = user_and_session["session"]["id"]
        r = requests.get(f"{API}/og/sessions/{sid}/meta", timeout=15)
        assert r.status_code == 200
        d = r.json()
        expected_keys = {
            "id", "domain", "topic", "difficulty", "wpm", "raw_wpm",
            "accuracy", "duration_seconds", "incorrect_chars", "created_at",
        }
        assert set(d.keys()) == expected_keys, f"unexpected keys: {set(d.keys()) ^ expected_keys}"
        # Do NOT leak sensitive fields:
        for forbidden in ["user_id", "target_text", "typed_text", "keystrokes", "_id"]:
            assert forbidden not in d, f"meta leaked {forbidden}"
        assert d["id"] == sid
        assert d["domain"] == "DBMS"
        assert d["topic"] == "INNER JOIN"
        assert d["difficulty"] == "Intermediate"
        assert abs(d["wpm"] - 55.2) < 0.01
        assert abs(d["accuracy"] - 96.4) < 0.01

    def test_meta_unknown_404(self):
        r = requests.get(f"{API}/og/sessions/{uuid.uuid4().hex}/meta", timeout=10)
        assert r.status_code == 404
