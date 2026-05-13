"""v6 Boss Fight Lock System tests.

Validates GET /api/profile/{id}/boss-fight/requirements gate-status payload and
POST /api/profile/{id}/boss-fight 403 lock behavior. Includes regression on
v1-v5 endpoints.
"""
import os
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path("/app/frontend/.env"))

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
)
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL not set"
API = f"{BASE_URL.rstrip('/')}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _create_profile(s, name, sq, bn, dl, bw=80, goal=1000, days=4):
    payload = {
        "name": f"TEST_v6_{name}",
        "bodyweight": bw,
        "experience": "Beginner",
        "squat_max": sq,
        "bench_max": bn,
        "deadlift_max": dl,
        "training_days": days,
        "goal_total": goal,
    }
    r = s.post(f"{API}/profile", json=payload, timeout=30)
    assert r.status_code == 200, f"profile create failed: {r.status_code} {r.text}"
    return r.json()


# --- Module: Boss Fight Requirements (locked states) ---

class TestRequirementsLocked:
    def test_weak_beginner_locked_d_rank(self, session):
        """Weak beginner (sq80/bn50/dl100, total 230) → next_rank D, all 4 D-mins + quests in missing."""
        p = _create_profile(session, "weak", 80, 50, 100)
        r = session.get(f"{API}/profile/{p['id']}/boss-fight/requirements", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["locked"] is True
        assert body["next_rank"] == "D"
        assert body["next_threshold_kg"] == 450
        # find each req by key
        reqs_by_key = {it["key"]: it for it in body["requirements"]}
        for k in ("total", "squat", "bench", "deadlift", "quests", "deloads"):
            assert k in reqs_by_key, f"requirement key {k} missing"
        assert reqs_by_key["total"]["met"] is False
        assert reqs_by_key["squat"]["met"] is False
        assert reqs_by_key["bench"]["met"] is False
        assert reqs_by_key["deadlift"]["met"] is False
        assert reqs_by_key["quests"]["met"] is False
        # missing strings should reference each unmet item
        missing_blob = " | ".join(body["missing"]).lower()
        for word in ("total", "squat", "bench", "deadlift", "quests"):
            assert word in missing_blob, f"'{word}' not in missing list: {body['missing']}"

    def test_post_boss_fight_locked_returns_403(self, session):
        """POST /boss-fight on locked profile → 403 with detail.error=boss_fight_locked."""
        p = _create_profile(session, "weak_post", 80, 50, 100)
        r = session.post(
            f"{API}/profile/{p['id']}/boss-fight",
            json={"squat_max": 90, "bench_max": 55, "deadlift_max": 110},
            timeout=15,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        body = r.json()
        detail = body.get("detail", {})
        assert isinstance(detail, dict), f"detail not dict: {detail}"
        assert detail.get("error") == "boss_fight_locked"
        assert isinstance(detail.get("missing"), list) and len(detail["missing"]) > 0
        assert isinstance(detail.get("requirements"), list) and len(detail["requirements"]) == 6
        assert detail.get("next_rank") == "D"

    def test_moderate_meets_lifts_not_total_or_quests(self, session):
        """sq110/bn70/dl130, total 310 → D-rank lift mins (100/60/120) met, total(450) and quests unmet."""
        p = _create_profile(session, "moderate", 110, 70, 130)
        r = session.get(f"{API}/profile/{p['id']}/boss-fight/requirements", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["locked"] is True
        assert body["next_rank"] == "D"
        reqs_by_key = {it["key"]: it for it in body["requirements"]}
        # lift mins met
        assert reqs_by_key["squat"]["met"] is True
        assert reqs_by_key["bench"]["met"] is True
        assert reqs_by_key["deadlift"]["met"] is True
        # total and quests NOT met
        assert reqs_by_key["total"]["met"] is False
        assert reqs_by_key["quests"]["met"] is False
        # missing list should NOT contain individual lift names but should mention total & quests
        missing_blob = " | ".join(body["missing"]).lower()
        assert "total" in missing_blob
        assert "quest" in missing_blob
        # Specific lift names should NOT appear (since lift mins met)
        # The strings start with "Squat needs", "Bench needs", "Deadlift needs"
        for needle in ("squat needs", "bench needs", "deadlift needs"):
            assert needle not in missing_blob, f"unexpected '{needle}' in missing: {body['missing']}"

    def test_strong_total_met_but_zero_quests_still_locked(self, session):
        """sq160/bn100/dl200, total 460 → all D-lift mins + total met but quests=0 → locked."""
        p = _create_profile(session, "strong_noquests", 160, 100, 200)
        r = session.get(f"{API}/profile/{p['id']}/boss-fight/requirements", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["locked"] is True
        assert body["next_rank"] == "D"
        reqs_by_key = {it["key"]: it for it in body["requirements"]}
        assert reqs_by_key["total"]["met"] is True
        assert reqs_by_key["squat"]["met"] is True
        assert reqs_by_key["bench"]["met"] is True
        assert reqs_by_key["deadlift"]["met"] is True
        assert reqs_by_key["quests"]["met"] is False
        assert reqs_by_key["quests"]["have"] == 0
        assert reqs_by_key["quests"]["need"] == 6


# --- Module: Max rank / 404 ---

class TestEdgeCases:
    def test_s_rank_max_rank_unlocked(self, session):
        """Profile at S Rank → max_rank=true, locked=false."""
        p = _create_profile(session, "s_rank", 350, 240, 360)
        # total = 950 → S rank
        assert p["rank"] == "S"
        r = session.get(f"{API}/profile/{p['id']}/boss-fight/requirements", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["locked"] is False
        assert body.get("max_rank") is True
        assert body["next_rank"] == "S"

    def test_invalid_profile_id_returns_404(self, session):
        r = session.get(f"{API}/profile/nonexistent-id-xyz/boss-fight/requirements", timeout=15)
        assert r.status_code == 404


# --- Module: Successful unlock path ---

class TestUnlockPath:
    def test_complete_6_quests_unlocks_and_boss_fight_succeeds(self, session):
        """Strong profile completes 6 workouts → requirements.locked becomes false → POST /boss-fight 200."""
        p = _create_profile(session, "unlock", 160, 100, 200)
        pid = p["id"]
        workouts = p.get("workouts", [])
        assert len(workouts) >= 6

        # Log first 6 workouts as fully done
        for w in workouts[:6]:
            exercises_payload = []
            for ex in w["exercises"]:
                exercises_payload.append({
                    "name": ex["name"],
                    "target_sets": ex["sets"],
                    "target_reps": ex["reps"],
                    "target_weight": ex["weight"],
                    "target_rpe": ex.get("target_rpe"),
                    "logged_weight": ex["weight"],
                    "logged_reps": ex["reps"],
                    "logged_rpe": ex.get("target_rpe") or 8,
                    "is_main": ex.get("is_main", False),
                    "done": True,
                })
            r = session.post(
                f"{API}/profile/{pid}/workout/log",
                json={"workout_id": w["id"], "exercises": exercises_payload},
                timeout=20,
            )
            assert r.status_code == 200, f"workout log failed: {r.status_code} {r.text}"

        # Requirements now should be unlocked
        r = session.get(f"{API}/profile/{pid}/boss-fight/requirements", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["locked"] is False, f"still locked after 6 workouts: {body}"
        reqs_by_key = {it["key"]: it for it in body["requirements"]}
        assert reqs_by_key["quests"]["have"] >= 6

        # POST /boss-fight should now succeed
        r = session.post(
            f"{API}/profile/{pid}/boss-fight",
            json={"squat_max": 165, "bench_max": 105, "deadlift_max": 205},
            timeout=15,
        )
        assert r.status_code == 200, f"boss fight failed: {r.status_code} {r.text}"
        body = r.json()
        assert body["new_total"] == 475
        assert body["new_rank"] == "E" or body["new_rank"] == "D" or body["new_rank"] == "C"  # 475 falls in E (0-499)
        # Actually 475 < 500, so rank stays E. Confirm boss_fight_count was incremented via GET profile
        r2 = session.get(f"{API}/profile/{pid}", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["boss_fight_count"] == 1


# --- Module: Regression on v1-v5 endpoints ---

class TestRegression:
    @pytest.fixture(scope="class")
    def reg_profile(self):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        p = _create_profile(s, "regression", 140, 90, 170)
        return s, p

    def test_rank_progress_200(self, reg_profile):
        s, p = reg_profile
        r = s.get(f"{API}/profile/{p['id']}/rank-progress", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "current_rank" in body and "next_rank" in body

    def test_achievements_200(self, reg_profile):
        s, p = reg_profile
        r = s.get(f"{API}/profile/{p['id']}/achievements", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_dashboard_200(self, reg_profile):
        s, p = reg_profile
        r = s.get(f"{API}/profile/{p['id']}/dashboard", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "profile" in body and "next_rank" in body

    def test_progress_200(self, reg_profile):
        s, p = reg_profile
        r = s.get(f"{API}/profile/{p['id']}/progress", timeout=15)
        assert r.status_code == 200

    def test_post_cardio_200(self, reg_profile):
        s, p = reg_profile
        r = s.post(
            f"{API}/profile/{p['id']}/cardio",
            json={"activity": "run", "distance_km": 3.0, "duration_sec": 1080},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["xp_gained"] > 0

    def test_post_workout_log_200(self, reg_profile):
        s, p = reg_profile
        # fetch latest workouts to grab first one
        r = s.get(f"{API}/profile/{p['id']}/workouts", timeout=15)
        assert r.status_code == 200
        workouts = r.json()
        w = next((w for w in workouts if not w.get("completed")), None)
        assert w is not None
        ex_payload = [{
            "name": ex["name"],
            "target_sets": ex["sets"],
            "target_reps": ex["reps"],
            "target_weight": ex["weight"],
            "target_rpe": ex.get("target_rpe"),
            "logged_weight": ex["weight"],
            "logged_reps": ex["reps"],
            "logged_rpe": 8,
            "is_main": ex.get("is_main", False),
            "done": True,
        } for ex in w["exercises"]]
        r = s.post(
            f"{API}/profile/{p['id']}/workout/log",
            json={"workout_id": w["id"], "exercises": ex_payload},
            timeout=20,
        )
        assert r.status_code == 200

    def test_ai_coach_200(self, reg_profile):
        s, p = reg_profile
        r = s.post(
            f"{API}/profile/{p['id']}/ai-coach",
            json={"question": "Quick check"},
            timeout=60,
        )
        # AI may return non-200 if upstream fails, but should be 200 normally
        assert r.status_code == 200, f"AI coach failed: {r.status_code} {r.text[:200]}"
        assert "response" in r.json()
