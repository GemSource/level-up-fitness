"""Hunter Strength System v5 — Rank Progress Tracker endpoint tests."""
import os
import pytest
import requests

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def _make_profile(s, name, bw, sq, bn, dl, goal=1000):
    r = s.post(f"{API}/profile", json={
        "name": f"TEST_{name}", "bodyweight": bw, "experience": "Intermediate",
        "squat_max": sq, "bench_max": bn, "deadlift_max": dl,
        "training_days": 4, "goal_total": goal,
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ---------- Core rank-progress endpoint ----------
class TestRankProgressCRank:
    """bw=80 sq=230 bn=160 dl=230 total=620 → C rank, next B (700), remaining 80, pct≈88.6%"""

    def test_c_rank_profile_progress(self, s):
        pid = _make_profile(s, "c_rank", 80, 230, 160, 230)
        r = s.get(f"{API}/profile/{pid}/rank-progress")
        assert r.status_code == 200, r.text
        d = r.json()

        assert d["current_rank"] == "C", d
        assert d["next_rank"] == "B"
        assert d["next_threshold_kg"] == 700
        assert d["current_total"] == 620
        assert d["remaining_kg"] == 80
        # pct = 620/700 * 100 = 88.57 → rounded 88.6
        assert 88.0 <= d["progress_pct"] <= 89.0, d["progress_pct"]
        assert d["rank_up"] is False

    def test_lift_contributions_sum_approx_remaining(self, s):
        pid = _make_profile(s, "c_rank_contrib", 80, 230, 160, 230)
        d = s.get(f"{API}/profile/{pid}/rank-progress").json()
        contribs = d["lift_contributions"]
        assert set(contribs.keys()) == {"squat", "bench", "deadlift"}, contribs
        s_sum = sum(contribs.values())
        # Rounded to 2.5 each → allow ±5kg drift from 80
        assert abs(s_sum - d["remaining_kg"]) <= 7.5, f"sum={s_sum} rem={d['remaining_kg']}"

    def test_xp_structure(self, s):
        pid = _make_profile(s, "xp_check", 80, 230, 160, 230)
        d = s.get(f"{API}/profile/{pid}/rank-progress").json()
        xp = d["xp"]
        assert set(xp.keys()) >= {"current", "level", "next_level_xp"}
        assert isinstance(xp["current"], int)
        assert isinstance(xp["level"], int)
        assert isinstance(xp["next_level_xp"], int)
        assert xp["next_level_xp"] > 0

    def test_projected_weeks_present_when_not_rank_up(self, s):
        pid = _make_profile(s, "weeks_check", 80, 230, 160, 230)
        d = s.get(f"{API}/profile/{pid}/rank-progress").json()
        pw = d["projected_weeks"]
        assert pw is not None
        assert "min" in pw and "max" in pw
        assert pw["min"] <= pw["max"]

    def test_message_75_to_95_mentions_remaining_and_weakest(self, s):
        pid = _make_profile(s, "msg_c", 80, 230, 160, 230)
        d = s.get(f"{API}/profile/{pid}/rank-progress").json()
        msg = d["message"]
        # pct≈88.6 → tier 75-95 → mentions remaining kg + weakest lift name
        # Either '80kg' or '80' appears for remaining, and a lift name
        assert any(lift in msg.lower() for lift in ["squat", "bench", "deadlift"]), msg
        assert "80" in msg, msg


# ---------- S-rank profile ----------
class TestRankProgressSRank:
    def test_s_rank_profile(self, s):
        pid = _make_profile(s, "s_rank", 90, 350, 240, 360, goal=1000)
        r = s.get(f"{API}/profile/{pid}/rank-progress")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["current_rank"] == "S", d
        assert d["rank_up"] is True
        assert d["remaining_kg"] == 0
        assert d["progress_pct"] == 100 or d["progress_pct"] == 100.0
        # Message should be the Monarch one
        assert "Monarch" in d["message"] or "System" in d["message"]


# ---------- E-rank profile ----------
class TestRankProgressERank:
    def test_e_rank_profile(self, s):
        pid = _make_profile(s, "e_rank", 70, 60, 40, 80, goal=400)
        r = s.get(f"{API}/profile/{pid}/rank-progress")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["current_rank"] == "E"
        assert d["next_rank"] == "D"
        assert d["next_threshold_kg"] == 500
        assert d["current_total"] == 180
        assert d["remaining_kg"] == 320

    def test_e_rank_message_path_is_long(self, s):
        pid = _make_profile(s, "e_rank_msg", 70, 60, 40, 80, goal=400)
        d = s.get(f"{API}/profile/{pid}/rank-progress").json()
        # 180/500 = 36% → <50 → "path is long"
        assert d["progress_pct"] < 50.0
        assert "path is long" in d["message"].lower()


# ---------- Invalid id ----------
class TestRankProgressInvalid:
    def test_404_for_invalid_profile(self, s):
        r = s.get(f"{API}/profile/nonexistent-uuid-1234/rank-progress")
        assert r.status_code == 404


# ---------- Regression: other endpoints still work ----------
class TestRegressionOtherEndpoints:
    @pytest.fixture(scope="class")
    def pid(self):
        sess = requests.Session()
        sess.headers.update({"Content-Type": "application/json"})
        r = sess.post(f"{API}/profile", json={
            "name": "TEST_regress", "bodyweight": 80, "experience": "Intermediate",
            "squat_max": 140, "bench_max": 100, "deadlift_max": 160,
            "training_days": 4, "goal_total": 600,
        })
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def test_dashboard(self, s, pid):
        r = s.get(f"{API}/profile/{pid}/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert "profile" in d and "today_quest" in d and "next_rank" in d

    def test_workouts_list(self, s, pid):
        r = s.get(f"{API}/profile/{pid}/workouts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_progress(self, s, pid):
        r = s.get(f"{API}/profile/{pid}/progress")
        assert r.status_code == 200
        d = r.json()
        assert "current" in d and "next_rank" in d and "history" in d

    def test_cardio_log(self, s, pid):
        r = s.post(f"{API}/profile/{pid}/cardio", json={
            "activity": "run", "distance_km": 3.0, "duration_sec": 1080,
        })
        assert r.status_code == 200
        d = r.json()
        assert "xp_gained" in d and d["xp_gained"] > 0

    def test_ai_coach_endpoint_responds(self, s, pid):
        r = s.post(f"{API}/profile/{pid}/ai-coach", json={"question": "Quick check"})
        # Endpoint should respond 200 even if LLM offline (returns offline msg)
        assert r.status_code == 200
        assert "response" in r.json()
