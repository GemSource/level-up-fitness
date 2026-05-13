"""Backend tests for Hunter Strength System (new per-exercise log schema)."""
import os
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Use public URL where frontend points
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "http://localhost:8001").rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _build_rows(workout):
    """Helper: convert workout exercises into log rows."""
    return [
        {
            "name": ex["name"],
            "target_sets": ex["sets"],
            "target_reps": ex["reps"],
            "target_weight": ex["weight"],
            "target_rpe": ex.get("target_rpe"),
            "logged_weight": ex["weight"],
            "logged_reps": ex["reps"],
            "logged_rpe": ex.get("target_rpe"),
            "is_main": ex.get("is_main", False),
            "done": True,
        }
        for ex in workout["exercises"]
    ]


# ---------- Health ----------
def test_root(api):
    r = api.get(f"{BASE_URL}/api/")
    assert r.status_code == 200
    assert "Hunter" in r.json()["message"]


# ---------- (1) progression_mode bucket selection ----------
@pytest.mark.parametrize("squat,bench,dl,goal,expected_mode", [
    (300, 200, 400, 1000, "conservative"),  # ratio = 1000/900 ≈ 1.11 < 1.25
    (200, 140, 240, 1000, "moderate"),      # ratio = 1000/580 ≈ 1.724 in [1.25,1.75]
    (150, 100, 180, 1000, "aggressive"),    # ratio = 1000/430 ≈ 2.33 > 1.75
])
def test_progression_mode_buckets(api, squat, bench, dl, goal, expected_mode):
    r = api.post(f"{BASE_URL}/api/profile", json={
        "name": f"TEST_mode_{expected_mode}",
        "bodyweight": 80,
        "experience": "Intermediate",
        "squat_max": squat, "bench_max": bench, "deadlift_max": dl,
        "training_days": 4, "goal_total": goal,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["progression_mode"] == expected_mode, body
    assert isinstance(body["estimated_weeks_to_goal"], dict)
    assert "min" in body["estimated_weeks_to_goal"] and "max" in body["estimated_weeks_to_goal"]


# ---------- (2) estimated_weeks_to_goal range matches mode ----------
def test_estimated_weeks_dict_shape_and_range(api):
    # moderate: 1000 - 580 = 420 gap; min = 420/5 = 84, max = 420/2.5 = 168
    r = api.post(f"{BASE_URL}/api/profile", json={
        "name": "TEST_eta_moderate",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 200, "bench_max": 140, "deadlift_max": 240,
        "training_days": 4, "goal_total": 1000,
    })
    assert r.status_code == 200, r.text
    eta = r.json()["estimated_weeks_to_goal"]
    assert eta["min"] == 84
    assert eta["max"] == 168


# ---------- (3) Daily training weights from per-day intensity modifier ----------
def test_daily_weights_per_day_modifier(api):
    r = api.post(f"{BASE_URL}/api/profile", json={
        "name": "TEST_daily_weights",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 200, "bench_max": 140, "deadlift_max": 240,
        "training_days": 4, "goal_total": 1000,
    })
    assert r.status_code == 200, r.text
    workouts = r.json()["workouts"]
    # week 1 squat day (BASE): squat = round(200*0.70)=140
    sq = next(w for w in workouts if w["week"] == 1 and w["day_type"] == "SQUAT_DAY")
    sq_main = next(e for e in sq["exercises"] if e.get("is_main"))
    assert sq_main["weight"] == 140.0, sq_main
    assert sq["day_tag"] == "BASE"
    # week 1 bench day (HIGH +2.5%): bench = round_to_2_5(140 * 0.725) = 102.5
    bn = next(w for w in workouts if w["week"] == 1 and w["day_type"] == "BENCH_DAY")
    bn_main = next(e for e in bn["exercises"] if e.get("is_main"))
    assert bn_main["weight"] == 102.5, bn_main
    assert bn["day_tag"] == "HIGH"
    # week 1 deadlift day (BASE): deadlift = round_to_2_5(240*0.70)=167.5 (round(67.2)=67*2.5=167.5)
    dl = next(w for w in workouts if w["week"] == 1 and w["day_type"] == "DEADLIFT_DAY")
    dl_main = next(e for e in dl["exercises"] if e.get("is_main"))
    assert dl["day_tag"] == "BASE"
    assert dl_main["weight"] == 167.5, dl_main


# ---------- (11) Machine rounding to 5kg ----------
def test_machine_rounding_5kg(api):
    r = api.post(f"{BASE_URL}/api/profile", json={
        "name": "TEST_machine",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 187, "bench_max": 137, "deadlift_max": 233,  # odd numbers
        "training_days": 5, "goal_total": 1000,
    })
    assert r.status_code == 200, r.text
    workouts = r.json()["workouts"]
    upper = next(w for w in workouts if w["day_type"] == "UPPER_ACC")
    lat = next(e for e in upper["exercises"] if e["name"] == "Lat Pulldown")
    assert lat["weight"] % 5 == 0, f"Lat Pulldown not 5kg multiple: {lat['weight']}"
    lower = next(w for w in workouts if w["day_type"] == "LOWER_ACC")
    leg = next(e for e in lower["exercises"] if e["name"] == "Leg Press")
    assert leg["weight"] % 5 == 0, f"Leg Press not 5kg multiple: {leg['weight']}"
    # accessory days are LOW tag
    assert upper["day_tag"] == "LOW"
    assert lower["day_tag"] == "LOW"


# ---------- Shared fixture for log/RPE/progress/boss tests ----------
@pytest.fixture(scope="module")
def profile(api):
    payload = {
        "name": "TEST_Hunter",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 200, "bench_max": 140, "deadlift_max": 240,
        "training_days": 4, "goal_total": 1000,
    }
    r = api.post(f"{BASE_URL}/api/profile", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["workouts"]) == 24
    return body


# ---------- (5) Partial log → workout NOT complete ----------
def test_partial_log_does_not_complete_workout(api, profile):
    # Use week 1 UPPER_ACC (no main lift impact on subsequent squat tests)
    w = next(x for x in profile["workouts"] if x["week"] == 1 and x["day_type"] == "UPPER_ACC")
    rows = _build_rows(w)
    rows[0]["done"] = True
    rows[1]["done"] = False
    rows[2]["done"] = False
    payload = {"workout_id": w["id"], "exercises": rows, "notes": "TEST_partial"}
    r = api.post(f"{BASE_URL}/api/profile/{profile['id']}/workout/log", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workout_complete"] is False
    assert body["exercises_done"] == 1
    assert body["exercises_total"] == 3
    # XP: 1 done × 20 = 20 (no main, no all-done bonus, no all-rpe bonus since done=1)
    # done_ex has logged_rpe -> +50 RPE bonus (since all done_ex have rpe)
    assert body["xp_gained"] == 70, body  # 20 + 50 (RPE bonus on done_ex)

    # Verify via dashboard the workout is not marked complete
    dash = api.get(f"{BASE_URL}/api/profile/{profile['id']}/dashboard").json()
    completed_ids = [c for c in [dash.get("today_quest", {}).get("id")] if c]
    # Re-fetch the workout
    g = api.get(f"{BASE_URL}/api/profile/{profile['id']}/workout/{w['id']}").json()
    assert g["completed"] is False


# ---------- (4) Full log XP math + (6) workout complete + streak ----------
def test_full_log_xp_math_and_complete(api, profile):
    w = next(x for x in profile["workouts"] if x["week"] == 1 and x["day_type"] == "SQUAT_DAY")
    rows = _build_rows(w)
    # Main lift logged_rpe == target_rpe → 0 adjustment
    for r_ in rows:
        r_["logged_rpe"] = r_["target_rpe"]
    payload = {"workout_id": w["id"], "exercises": rows, "notes": "TEST_full"}
    r = api.post(f"{BASE_URL}/api/profile/{profile['id']}/workout/log", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workout_complete"] is True
    # 3 done × 20 = 60 + 50 main + 100 all + 50 all-rpe = 260
    assert body["xp_gained"] == 260, body
    assert body["main_lift_adjustment_kg"] == 0.0
    assert body["main_lift_key"] == "squat"
    assert "Optimal load" in body["suggestion"]


# ---------- (7) RPE < target → +2.5kg + upcoming SQUAT_DAY workouts updated ----------
def test_rpe_low_increments_upcoming_squat_workouts(api, profile):
    # Snapshot week2 squat day main weight BEFORE
    pre = api.get(f"{BASE_URL}/api/profile/{profile['id']}").json()
    upcoming = [w for w in pre["workouts"]
                if w["day_type"] == "SQUAT_DAY" and not w["completed"]]
    pre_weights = [next(e["weight"] for e in w["exercises"] if e.get("is_main")) for w in upcoming]
    target_id = upcoming[0]["id"]

    # Log first upcoming squat workout with logged_rpe BELOW target
    w = next(x for x in pre["workouts"] if x["id"] == target_id)
    rows = _build_rows(w)
    for r_ in rows:
        if r_["is_main"]:
            r_["logged_rpe"] = (r_["target_rpe"] or 7) - 1.0  # below target
        else:
            r_["logged_rpe"] = r_["target_rpe"]
    payload = {"workout_id": target_id, "exercises": rows, "notes": "TEST_rpe_low"}
    r = api.post(f"{BASE_URL}/api/profile/{profile['id']}/workout/log", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["main_lift_adjustment_kg"] == 2.5
    assert "+2.5kg" in body["suggestion"]

    # Verify remaining upcoming squat workouts had +2.5kg applied
    post = api.get(f"{BASE_URL}/api/profile/{profile['id']}").json()
    remaining = [w for w in post["workouts"]
                 if w["day_type"] == "SQUAT_DAY" and not w["completed"]]
    post_weights = [next(e["weight"] for e in w["exercises"] if e.get("is_main")) for w in remaining]
    # The first (target_id) is now completed; compare upcoming-ones-after vs original upcoming-after-first
    pre_after = pre_weights[1:]
    assert len(post_weights) == len(pre_after), (post_weights, pre_after)
    for a, b in zip(post_weights, pre_after):
        assert a == b + 2.5, (a, b)


# ---------- (8) RPE > target → -2.5kg ----------
def test_rpe_high_decrements(api, profile):
    pre = api.get(f"{BASE_URL}/api/profile/{profile['id']}").json()
    upcoming_bench = [w for w in pre["workouts"]
                      if w["day_type"] == "BENCH_DAY" and not w["completed"]]
    target_id = upcoming_bench[0]["id"]
    w = next(x for x in pre["workouts"] if x["id"] == target_id)
    rows = _build_rows(w)
    for r_ in rows:
        if r_["is_main"]:
            r_["logged_rpe"] = (r_["target_rpe"] or 7) + 1.0
        else:
            r_["logged_rpe"] = r_["target_rpe"]
    payload = {"workout_id": target_id, "exercises": rows}
    r = api.post(f"{BASE_URL}/api/profile/{profile['id']}/workout/log", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["main_lift_adjustment_kg"] == -2.5
    assert body["main_lift_key"] == "bench"
    assert "-2.5kg" in body["suggestion"]


# ---------- (10) GET /progress structure ----------
def test_progress_endpoint(api, profile):
    r = api.get(f"{BASE_URL}/api/profile/{profile['id']}/progress")
    assert r.status_code == 200
    p = r.json()
    for k in ("progression_mode", "goal_ratio", "estimated_weeks_to_goal", "pending_adjustments"):
        assert k in p, f"missing {k}"
    assert isinstance(p["estimated_weeks_to_goal"], dict)
    assert {"min", "max"} <= set(p["estimated_weeks_to_goal"].keys())
    assert {"squat", "bench", "deadlift"} <= set(p["pending_adjustments"].keys())
    # pending_adjustments should reflect prior RPE-driven changes
    assert p["pending_adjustments"]["squat"] == 2.5
    assert p["pending_adjustments"]["bench"] == -2.5


# ---------- (9) Boss fight resets pending_adjustments ----------
def test_boss_fight_resets_adjustments(api, profile):
    r = api.post(
        f"{BASE_URL}/api/profile/{profile['id']}/boss-fight",
        json={"squat_max": 230, "bench_max": 160, "deadlift_max": 260},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["new_total"] == 650
    # Verify pending_adjustments reset + progression_mode recomputed
    prog = api.get(f"{BASE_URL}/api/profile/{profile['id']}/progress").json()
    assert prog["pending_adjustments"] == {"squat": 0.0, "bench": 0.0, "deadlift": 0.0}
    assert prog["progression_mode"] in ("conservative", "moderate", "aggressive")
    # 1000/650 ≈ 1.538 → moderate
    assert prog["progression_mode"] == "moderate"


# ---------- (12) AI coach with new schema ----------
def test_ai_coach_with_new_log_schema(api, profile):
    r = api.post(
        f"{BASE_URL}/api/profile/{profile['id']}/ai-coach",
        json={"question": "Tactical advice for next squat session?"},
        timeout=90,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "response" in body and isinstance(body["response"], str)
    assert len(body["response"]) > 10
    assert "[SYSTEM OFFLINE]" not in body["response"], body["response"]


# ---------- 404 ----------
def test_profile_404(api):
    r = api.get(f"{BASE_URL}/api/profile/nope-id/dashboard")
    assert r.status_code == 404


# ---------- Cleanup ----------
def test_cleanup_test_profiles():
    """Remove TEST_ prefixed profiles via mongosh."""
    import subprocess
    try:
        subprocess.run(
            ["mongosh", "--quiet", "--eval",
             'db.getSiblingDB("hunter_db").profiles.deleteMany({name: /^TEST_/})'],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:
        pass
