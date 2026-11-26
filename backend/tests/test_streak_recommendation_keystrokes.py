"""Additional tests for P1 features:
- Streak (current/longest/today/goal/goal_met)
- AI difficulty/length Recommendation (rolling 5 sessions)
- Per-keystroke timestamps stored & returned per-session, projected out of list/stats
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"


def _register(session=None):
    s = session or requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"TEST_p1_{uuid.uuid4().hex[:8]}@typeforge.app"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Test@1234", "name": "P1"}, timeout=15)
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return s, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, email


def _session_payload(diff="Intermediate", wpm=55.0, acc=96.0, keystrokes=None):
    p = {
        "domain": "DBMS", "topic": "INNER JOIN", "difficulty": diff,
        "target_text": "SELECT * FROM a INNER JOIN b ON a.id=b.a_id;",
        "typed_text":  "SELECT * FROM a INNER JOIN b ON a.id=b.a_id;",
        "duration_seconds": 30.0, "wpm": wpm, "raw_wpm": wpm + 5, "accuracy": acc,
        "correct_chars": 47, "incorrect_chars": 2, "total_chars": 49, "error_chars": [],
    }
    if keystrokes is not None:
        p["keystrokes"] = keystrokes
    return p


# ---------- Streak ----------
class TestStreakAndGoal:
    def test_empty_user_streak_zero(self):
        _, headers, _ = _register()
        r = requests.get(f"{API}/sessions/stats/overview", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "streak" in d and "recommendation" in d
        s = d["streak"]
        assert s["current"] == 0
        assert s["longest"] == 0
        assert s["today"] == 0
        assert s["goal"] == 3
        assert s["goal_met"] is False

    def test_today_count_and_streak_one(self):
        _, headers, _ = _register()
        # Create one session today
        r = requests.post(f"{API}/sessions", headers=headers, json=_session_payload(), timeout=15)
        assert r.status_code == 200
        r = requests.get(f"{API}/sessions/stats/overview", headers=headers, timeout=15)
        d = r.json()
        s = d["streak"]
        assert s["today"] == 1
        assert s["current"] == 1
        assert s["longest"] >= 1
        assert s["goal_met"] is False

    def test_goal_met_after_three(self):
        _, headers, _ = _register()
        for _ in range(3):
            r = requests.post(f"{API}/sessions", headers=headers, json=_session_payload(), timeout=15)
            assert r.status_code == 200
        r = requests.get(f"{API}/sessions/stats/overview", headers=headers, timeout=15)
        s = r.json()["streak"]
        assert s["today"] == 3
        assert s["goal_met"] is True


# ---------- Recommendation ----------
class TestRecommendation:
    def test_no_sessions_default_beginner_short(self):
        _, headers, _ = _register()
        d = requests.get(f"{API}/sessions/stats/overview", headers=headers, timeout=15).json()
        rec = d["recommendation"]
        assert rec["difficulty"] == "Beginner"
        assert rec["length"] == "short"
        assert rec["based_on_sessions"] == 0
        assert isinstance(rec["reason"], str) and len(rec["reason"]) > 0

    def test_bump_to_advanced_when_crushing(self):
        _, headers, _ = _register()
        # high acc + high wpm at Intermediate -> should bump to Advanced, length=long
        for _ in range(5):
            requests.post(f"{API}/sessions", headers=headers,
                          json=_session_payload(diff="Intermediate", wpm=70, acc=98), timeout=15)
        rec = requests.get(f"{API}/sessions/stats/overview", headers=headers, timeout=15).json()["recommendation"]
        assert rec["difficulty"] == "Advanced"
        assert rec["length"] == "long"
        assert rec["based_on_sessions"] == 5

    def test_drop_difficulty_when_struggling(self):
        _, headers, _ = _register()
        # low accuracy at Intermediate -> drop to Beginner, length=short
        for _ in range(5):
            requests.post(f"{API}/sessions", headers=headers,
                          json=_session_payload(diff="Intermediate", wpm=40, acc=70), timeout=15)
        rec = requests.get(f"{API}/sessions/stats/overview", headers=headers, timeout=15).json()["recommendation"]
        assert rec["difficulty"] == "Beginner"
        assert rec["length"] == "short"

    def test_stay_in_lane_medium_length(self):
        _, headers, _ = _register()
        # accuracy 90 (>=88, <95), wpm 40 -> stay; length=medium
        for _ in range(3):
            requests.post(f"{API}/sessions", headers=headers,
                          json=_session_payload(diff="Intermediate", wpm=40, acc=90), timeout=15)
        rec = requests.get(f"{API}/sessions/stats/overview", headers=headers, timeout=15).json()["recommendation"]
        assert rec["difficulty"] == "Intermediate"
        assert rec["length"] == "medium"
        assert rec["based_on_sessions"] == 3


# ---------- Keystrokes ----------
class TestKeystrokes:
    def test_keystrokes_persisted_and_returned_in_get_by_id(self):
        _, headers, _ = _register()
        ks = [{"t": float(i * 100), "correct": (i % 5 != 0)} for i in range(20)]
        r = requests.post(f"{API}/sessions", headers=headers, json=_session_payload(keystrokes=ks), timeout=15)
        assert r.status_code == 200
        sid = r.json()["id"]
        # GET single session -> keystrokes present
        r2 = requests.get(f"{API}/sessions/{sid}", headers=headers, timeout=15)
        assert r2.status_code == 200
        body = r2.json()
        assert isinstance(body.get("keystrokes"), list)
        assert len(body["keystrokes"]) == 20
        assert body["keystrokes"][0]["t"] == 0.0
        # i=0 -> 0%5==0 -> correct False; i=1 -> True; i=5 -> False
        assert body["keystrokes"][0]["correct"] is False
        assert body["keystrokes"][1]["correct"] is True
        assert body["keystrokes"][5]["correct"] is False

    def test_list_endpoint_excludes_keystrokes(self):
        _, headers, _ = _register()
        ks = [{"t": float(i * 50), "correct": True} for i in range(10)]
        requests.post(f"{API}/sessions", headers=headers, json=_session_payload(keystrokes=ks), timeout=15)
        r = requests.get(f"{API}/sessions", headers=headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        # SessionOut default-factory makes it [] when projected away - this is the contract
        assert items[0].get("keystrokes", []) == []

    def test_create_without_keystrokes_back_compat(self):
        _, headers, _ = _register()
        r = requests.post(f"{API}/sessions", headers=headers, json=_session_payload(), timeout=15)
        assert r.status_code == 200
        sid = r.json()["id"]
        r2 = requests.get(f"{API}/sessions/{sid}", headers=headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("keystrokes", []) == []
