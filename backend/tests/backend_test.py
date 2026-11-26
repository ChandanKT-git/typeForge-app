"""TypeForge backend pytest suite.
Covers: health, auth, topics, AI generate/analyze/summary, sessions CRUD + stats.
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@typeforge.app"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin@1234")


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def fresh_user(api):
    """Register a brand-new user for tests that need clean history."""
    email = f"TEST_{uuid.uuid4().hex[:8]}@typeforge.app"
    r = api.post(f"{API}/auth/register", json={"email": email, "password": "Test@1234", "name": "Tester"}, timeout=15)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return {"email": email, "password": "Test@1234", "token": data["token"], "id": data["user"]["id"]}


@pytest.fixture(scope="session")
def auth_headers(fresh_user):
    return {"Authorization": f"Bearer {fresh_user['token']}", "Content-Type": "application/json"}


# ---------- health & root ----------
class TestHealth:
    def test_root(self, api):
        r = api.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_health(self, api):
        r = api.get(f"{API}/health", timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ---------- auth ----------
class TestAuth:
    def test_admin_login(self, api):
        r = api.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "token" in d and isinstance(d["token"], str) and len(d["token"]) > 20
        assert d["user"]["email"] == ADMIN_EMAIL
        assert d["user"]["role"] == "admin"

    def test_login_invalid_password(self, api):
        r = api.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "WRONGPASS"}, timeout=15)
        assert r.status_code == 401

    def test_register_duplicate(self, api, fresh_user):
        r = api.post(f"{API}/auth/register",
                     json={"email": fresh_user["email"], "password": "Test@1234"}, timeout=15)
        assert r.status_code == 400

    def test_me_with_bearer(self, api, fresh_user, auth_headers):
        r = api.get(f"{API}/auth/me", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["email"].lower() == fresh_user["email"].lower()

    def test_me_without_token(self, api):
        plain = requests.Session()  # no cookies
        r = plain.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_logout(self, api, auth_headers):
        r = api.post(f"{API}/auth/logout", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ---------- topics ----------
class TestTopics:
    def test_topics_catalog(self, api):
        r = api.get(f"{API}/topics", timeout=10)
        assert r.status_code == 200
        d = r.json()
        names = [x["name"] for x in d["domains"]]
        for expected in ["Programming", "DBMS", "OS", "Networking", "AI/ML"]:
            assert expected in names, f"missing domain {expected}"
        assert d["difficulties"] == ["Beginner", "Intermediate", "Advanced"]
        # each domain has topics
        for dom in d["domains"]:
            assert len(dom["topics"]) >= 5


# ---------- ai ----------
class TestAIAuth:
    def test_generate_requires_auth(self, api):
        r = requests.post(f"{API}/ai/generate",
                          json={"domain": "DBMS", "topic": "INNER JOIN", "difficulty": "Intermediate",
                                "length": "short", "include_code": False}, timeout=15)
        assert r.status_code == 401


class TestAIGenerate:
    @pytest.fixture(scope="class")
    def generated(self, auth_headers):
        r = requests.post(f"{API}/ai/generate",
                          headers=auth_headers,
                          json={"domain": "DBMS", "topic": "INNER JOIN", "difficulty": "Intermediate",
                                "length": "short", "include_code": False}, timeout=45)
        assert r.status_code == 200, f"AI generate failed: {r.status_code} {r.text[:200]}"
        return r.json()

    def test_generate_shape(self, generated):
        assert set(generated.keys()) >= {"text", "notes", "domain", "topic", "difficulty"}
        assert generated["domain"] == "DBMS"
        assert generated["topic"] == "INNER JOIN"
        assert generated["difficulty"] == "Intermediate"

    def test_generate_text_ascii_only(self, generated):
        text = generated["text"]
        assert isinstance(text, str) and len(text) > 30
        # ASCII-only
        for ch in text:
            assert 32 <= ord(ch) <= 126 or ch in "\t\r\n", f"non-ASCII: {repr(ch)}"

    def test_generate_notes(self, generated):
        notes = generated["notes"]
        assert isinstance(notes, list)
        # may be 0-5; if present, strings
        for n in notes:
            assert isinstance(n, str)


# ---------- sessions ----------
class TestSessions:
    @pytest.fixture(scope="class")
    def created(self, auth_headers):
        payload = {
            "domain": "DBMS", "topic": "INNER JOIN", "difficulty": "Intermediate",
            "target_text": "SELECT * FROM a INNER JOIN b ON a.id = b.a_id;",
            "typed_text":  "SELECT * FROM a INNER JOIN b ON a.id = b.a_id;",
            "duration_seconds": 30.5, "wpm": 55.2, "raw_wpm": 60.0, "accuracy": 96.4,
            "correct_chars": 47, "incorrect_chars": 2, "total_chars": 49,
            "error_chars": ["e", "n"],
        }
        r = requests.post(f"{API}/sessions", headers=auth_headers, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_create_session(self, created):
        assert "id" in created and "created_at" in created
        assert created["wpm"] == 55.2
        assert created["domain"] == "DBMS"

    def test_create_requires_auth(self):
        r = requests.post(f"{API}/sessions", json={}, timeout=10)
        assert r.status_code in (401, 422)  # 422 for missing fields if validation runs first; 401 expected

    def test_list_sessions(self, auth_headers, created):
        r = requests.get(f"{API}/sessions", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1
        assert items[0]["created_at"] >= items[-1]["created_at"]  # desc order

    def test_get_single_session(self, auth_headers, created):
        r = requests.get(f"{API}/sessions/{created['id']}", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    def test_get_unknown_session_404(self, auth_headers):
        r = requests.get(f"{API}/sessions/{uuid.uuid4().hex}", headers=auth_headers, timeout=10)
        assert r.status_code == 404

    def test_other_user_cannot_access(self, api, created):
        # Register another user, try to fetch the first user's session
        email = f"TEST_other_{uuid.uuid4().hex[:6]}@typeforge.app"
        r = api.post(f"{API}/auth/register", json={"email": email, "password": "Test@1234"}, timeout=15)
        assert r.status_code == 200
        token2 = r.json()["token"]
        r2 = requests.get(f"{API}/sessions/{created['id']}",
                          headers={"Authorization": f"Bearer {token2}"}, timeout=10)
        assert r2.status_code == 404

    def test_stats_overview(self, auth_headers, created):
        r = requests.get(f"{API}/sessions/stats/overview", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["total_sessions", "avg_wpm", "best_wpm", "avg_accuracy", "last_30", "by_domain"]:
            assert k in d, f"missing key {k}"
        assert d["total_sessions"] >= 1
        assert d["best_wpm"] >= 55.2 - 0.01
        assert any(b["domain"] == "DBMS" for b in d["by_domain"])


# ---------- ai analyze + summary ----------
class TestAISecondary:
    def test_analyze(self, auth_headers):
        body = {
            "target": "SELECT * FROM a INNER JOIN b ON a.id = b.a_id;",
            "typed":  "SELECT * FROM a INNR JOIN b ON a.id = b.a_id;",
            "duration_seconds": 30, "wpm": 55, "accuracy": 95,
            "domain": "DBMS", "topic": "INNER JOIN",
        }
        r = requests.post(f"{API}/ai/analyze", headers=auth_headers, json=body, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["summary", "weak_keys", "error_patterns", "recommendations", "next_topics"]:
            assert k in d
        assert isinstance(d["summary"], str) and len(d["summary"]) > 0

    def test_summary(self, auth_headers):
        body = {
            "text": "An INNER JOIN returns rows that have matching values in both tables.",
            "domain": "DBMS", "topic": "INNER JOIN",
        }
        r = requests.post(f"{API}/ai/summary", headers=auth_headers, json=body, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["headline", "bullets", "memory_hooks"]:
            assert k in d
