"""Hunter Strength System v4 — beginner-tier achievement expansion tests."""
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


# ---------- Achievement catalog ----------
class TestAchievementCatalog:
    def test_achievements_count_and_tiers(self, s):
        # Need a profile id to list achievements
        r = s.post(f"{API}/profile", json={
            "name": "TEST_catalog", "bodyweight": 80, "experience": "Beginner",
            "squat_max": 60, "bench_max": 40, "deadlift_max": 80,
            "training_days": 3, "goal_total": 400,
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        r = s.get(f"{API}/profile/{pid}/achievements")
        assert r.status_code == 200
        ach = r.json()
        assert len(ach) == 116, f"Expected 116 achievements, got {len(ach)}"
        tiers = {a["tier"] for a in ach}
        assert tiers == {"beginner", "basic", "medium", "major", "elite"}, tiers
        # Validate TIER_XP mapping in returned xp field
        expected_xp = {"beginner": 25, "basic": 50, "medium": 100, "major": 250, "elite": 500}
        for a in ach:
            assert a["xp"] == expected_xp[a["tier"]], a

        # Verify old removed keys aren't present
        keys = {a["key"] for a in ach}
        for removed in ("squat_specialist", "bench_technician", "deadlift_monster"):
            assert removed not in keys, f"Removed key {removed} still in catalog"
        # New ladder keys present
        for required in ("bench_bw_05", "bench_bw_075", "bench_bw_1", "bench_bw_125", "bench_bw_15",
                         "squat_bw_1", "squat_bw_15", "squat_bw_2", "squat_bw_25",
                         "deadlift_bw_1", "deadlift_bw_15", "deadlift_bw_2", "deadlift_bw_25", "deadlift_bw_3",
                         "first_squat", "first_bench", "first_deadlift", "first_workout", "first_week", "first_deload",
                         "gain_lift_5", "gain_lift_10", "gain_total_20", "gain_total_50", "quests_3"):
            assert required in keys, f"Missing required key {required}"


# ---------- Beginner profile auto-unlocks ----------
class TestBeginnerProfile:
    def test_beginner_auto_unlocks(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_beg", "bodyweight": 80, "experience": "Beginner",
            "squat_max": 60, "bench_max": 40, "deadlift_max": 80,
            "training_days": 3, "goal_total": 400,
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        unlocked = set(r.json()["achievements"])
        for k in ("squat_60", "bench_40", "deadlift_60", "bench_bw_05", "deadlift_bw_1", "rank_e"):
            assert k in unlocked, f"Beginner missing {k}; got {unlocked}"


# ---------- Strong profile ladder ----------
class TestStrongProfile:
    def test_strong_ladder(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_strong", "bodyweight": 80, "experience": "Advanced",
            "squat_max": 200, "bench_max": 140, "deadlift_max": 240,
            "training_days": 4, "goal_total": 700,
        })
        assert r.status_code == 200, r.text
        unlocked = set(r.json()["achievements"])
        for k in ("bench_bw_15", "squat_bw_2", "deadlift_bw_25", "deadlift_bw_3",
                  "total_500", "rank_e"):
            assert k in unlocked, f"Strong missing {k}"


# ---------- First-session by day_type ----------
def _complete_workout(s, pid, workout):
    payload = {
        "workout_id": workout["id"],
        "exercises": [
            {
                "name": ex["name"],
                "target_sets": ex["sets"],
                "target_reps": ex["reps"],
                "target_weight": ex["weight"],
                "target_rpe": ex.get("target_rpe"),
                "logged_weight": ex["weight"],
                "logged_reps": ex["reps"],
                "logged_rpe": ex.get("target_rpe") or 7,
                "is_main": ex.get("is_main", False),
                "done": True,
            }
            for ex in workout["exercises"]
        ],
        "notes": "TEST",
    }
    return s.post(f"{API}/profile/{pid}/workout/log", json=payload)


class TestFirstSessions:
    def test_first_squat_bench_deadlift(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_first", "bodyweight": 80, "experience": "Beginner",
            "squat_max": 60, "bench_max": 40, "deadlift_max": 80,
            "training_days": 3, "goal_total": 400,
        })
        pid = r.json()["id"]
        workouts = r.json()["workouts"]

        # Complete SQUAT_DAY of week 1
        sq = next(w for w in workouts if w["day_type"] == "SQUAT_DAY" and w["week"] == 1)
        resp = _complete_workout(s, pid, sq)
        assert resp.status_code == 200, resp.text
        keys = {a["key"] for a in resp.json()["new_achievements"]}
        assert "first_squat" in keys, keys

        bn = next(w for w in workouts if w["day_type"] == "BENCH_DAY" and w["week"] == 1)
        resp = _complete_workout(s, pid, bn)
        keys = {a["key"] for a in resp.json()["new_achievements"]}
        assert "first_bench" in keys

        dl = next(w for w in workouts if w["day_type"] == "DEADLIFT_DAY" and w["week"] == 1)
        resp = _complete_workout(s, pid, dl)
        body = resp.json()
        keys = {a["key"] for a in body["new_achievements"]}
        assert "first_deadlift" in keys
        # All W1 done for training_days=3 → first_week should also unlock
        assert "first_week" in keys, f"first_week missing on W1 completion: {keys}"
        # Weekly bonus +300 included in xp_gained for this final workout
        assert body["xp_gained"] >= 300, f"Expected >=300 (incl. weekly bonus); got {body['xp_gained']}"


# ---------- Full week + deload ----------
class TestWeekAndDeload:
    def test_first_week_and_deload(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_week", "bodyweight": 80, "experience": "Beginner",
            "squat_max": 60, "bench_max": 40, "deadlift_max": 80,
            "training_days": 3, "goal_total": 400,
        })
        pid = r.json()["id"]
        workouts = r.json()["workouts"]

        # Complete every workout in W6 (deload) - need W1..W5 also marked? No - deload trigger uses week_no==6
        w6 = [w for w in workouts if w["week"] == 6]
        last_resp = None
        for w in w6:
            last_resp = _complete_workout(s, pid, w)
            assert last_resp.status_code == 200
        body = last_resp.json()
        # Last response should include weekly bonus 300 + deload 200 = at least 500 over base
        assert body["xp_gained"] >= 500, f"Expected deload bonus, got {body['xp_gained']}"
        # Profile achievements list should contain first_deload
        ach_resp = s.get(f"{API}/profile/{pid}")
        unlocked = set(ach_resp.json()["achievements"])
        assert "first_deload" in unlocked
        assert "first_week" in unlocked


# ---------- Progression achievements ----------
class TestProgression:
    def test_gain_lift_via_boss_fight(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_prog", "bodyweight": 80, "experience": "Beginner",
            "squat_max": 100, "bench_max": 80, "deadlift_max": 120,
            "training_days": 3, "goal_total": 500,
        })
        pid = r.json()["id"]
        # Boss fight: squat +10 only
        r2 = s.post(f"{API}/profile/{pid}/boss-fight", json={
            "squat_max": 110, "bench_max": 80, "deadlift_max": 120,
        })
        assert r2.status_code == 200, r2.text
        keys = {a["key"] for a in r2.json()["new_achievements"]}
        assert "gain_lift_5" in keys, keys
        assert "gain_lift_10" in keys, keys

    def test_gain_total_thresholds(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_total", "bodyweight": 80, "experience": "Intermediate",
            "squat_max": 120, "bench_max": 80, "deadlift_max": 140,
            "training_days": 3, "goal_total": 500,
        })
        pid = r.json()["id"]
        # +25 total
        r2 = s.post(f"{API}/profile/{pid}/boss-fight", json={
            "squat_max": 130, "bench_max": 85, "deadlift_max": 150,  # +10+5+10=+25
        })
        assert r2.status_code == 200
        keys = {a["key"] for a in r2.json()["new_achievements"]}
        assert "gain_total_20" in keys, keys
        assert "gain_total_50" not in keys

        # Push total to +60 from starting 340 → new total 400
        r3 = s.post(f"{API}/profile/{pid}/boss-fight", json={
            "squat_max": 140, "bench_max": 95, "deadlift_max": 165,  # total=400 (+60)
        })
        assert r3.status_code == 200
        # Check via profile (cumulative)
        prof = s.get(f"{API}/profile/{pid}").json()
        unlocked = set(prof["achievements"])
        assert "gain_total_50" in unlocked, unlocked


# ---------- Rank chain ----------
class TestRankChain:
    def test_rank_chain_unlocks_lower(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_rank", "bodyweight": 80, "experience": "Advanced",
            "squat_max": 220, "bench_max": 160, "deadlift_max": 240,  # total 620 → C
            "training_days": 4, "goal_total": 800,
        })
        pid = r.json()["id"]
        unlocked = set(r.json()["achievements"])
        for k in ("rank_e", "rank_d", "rank_c"):
            assert k in unlocked, f"Rank chain missing {k}"
        assert "rank_b" not in unlocked


# ---------- Regression ----------
class TestRegression:
    @pytest.fixture(scope="class")
    def pid(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_reg", "bodyweight": 75, "experience": "Intermediate",
            "squat_max": 120, "bench_max": 90, "deadlift_max": 150,
            "training_days": 4, "goal_total": 500,
        })
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def test_dashboard(self, s, pid):
        r = s.get(f"{API}/profile/{pid}/dashboard")
        assert r.status_code == 200
        body = r.json()
        assert "today_quest" in body
        assert "next_rank" in body
        assert body["total_workouts"] > 0

    def test_workouts_list(self, s, pid):
        r = s.get(f"{API}/profile/{pid}/workouts")
        assert r.status_code == 200
        assert len(r.json()) >= 24  # 6 weeks * 4 days

    def test_workout_detail(self, s, pid):
        ws = s.get(f"{API}/profile/{pid}/workouts").json()
        wid = ws[0]["id"]
        r = s.get(f"{API}/profile/{pid}/workout/{wid}")
        assert r.status_code == 200
        assert r.json()["id"] == wid

    def test_progress(self, s, pid):
        r = s.get(f"{API}/profile/{pid}/progress")
        assert r.status_code == 200
        body = r.json()
        assert "current" in body and "goal_total" in body

    def test_cardio_run(self, s, pid):
        r = s.post(f"{API}/profile/{pid}/cardio", json={
            "activity": "run", "distance_km": 5.0, "duration_sec": 1500,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["xp_gained"] > 0
        assert body["stats"]["total_run_km"] >= 5.0

    def test_404_invalid_profile(self, s):
        bad = "00000000-0000-0000-0000-000000000000"
        for path in (f"/profile/{bad}", f"/profile/{bad}/dashboard",
                     f"/profile/{bad}/workouts", f"/profile/{bad}/achievements",
                     f"/profile/{bad}/progress"):
            r = s.get(f"{API}{path}")
            assert r.status_code == 404, f"{path} returned {r.status_code}"


# ---------- Workout log tier XP ----------
class TestWorkoutLogXP:
    def test_beginner_xp_via_first_workout(self, s):
        r = s.post(f"{API}/profile", json={
            "name": "TEST_xp", "bodyweight": 80, "experience": "Beginner",
            "squat_max": 60, "bench_max": 40, "deadlift_max": 80,
            "training_days": 3, "goal_total": 400,
        })
        pid = r.json()["id"]
        workouts = r.json()["workouts"]
        sq = next(w for w in workouts if w["day_type"] == "SQUAT_DAY" and w["week"] == 1)
        resp = _complete_workout(s, pid, sq)
        body = resp.json()
        keys = {a["key"] for a in body["new_achievements"]}
        # first_squat (beginner=25) + first_workout (beginner=25) should be among unlocks
        assert "first_squat" in keys
        assert "first_workout" in keys
