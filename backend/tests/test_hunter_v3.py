"""Hunter Strength System v3 — backend tests for 84-achievement expansion + cardio endpoint."""
import os
import pytest
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "http://localhost:8001").rstrip("/")

# Expected 84 achievement keys
EXPECTED_KEYS = {
    # Squat (6)
    "squat_100","squat_140","squat_180","squat_200","squat_220","squat_250",
    # Bench (6)
    "bench_100","bench_140","bench_160","bench_180","bench_200","bench_220",
    # Deadlift (6)
    "deadlift_140","deadlift_180","deadlift_220","deadlift_240","deadlift_260","deadlift_300",
    # Total (6)
    "total_500","total_600","total_700","total_800","total_900","total_1000",
    # Quests (6: 5 thresholds + first)
    "quests_5","quests_10","quests_25","quests_50","quests_100","first_workout",
    # Weekly (4)
    "perfect_week_1","perfect_week_2","perfect_week_4","perfect_week_8",
    # Streak (4)
    "streak_3","streak_7","streak_14","streak_30",
    # Run single (4) + total (5)
    "run_1k","run_3k","run_5k","run_10k",
    "run_total_10","run_total_25","run_total_50","run_total_100","run_total_250",
    # Pace (4)
    "pace_sub_6","pace_sub_5_30","pace_sub_5","pace_sub_4_30",
    # Sprint (3)
    "sprint_100_20","sprint_200_40","sprint_400_90",
    # Bike single (4) + total (4)
    "bike_5","bike_10","bike_20","bike_50",
    "bike_total_50","bike_total_100","bike_total_250","bike_total_500",
    # Quality (4)
    "rpe_first","perfect_workout_1","perfect_workout_5","perfect_workout_10",
    # Elite (3)
    "squat_specialist","bench_technician","deadlift_monster",
    # Hybrid (2)
    "hybrid_run_5","hybrid_bike_5",
    # Volume (2)
    "volume_session_10k","volume_week_25k",
    # Rank (6)
    "rank_e","rank_d","rank_c","rank_b","rank_a","rank_s",
    # Special (4)
    "no_days_off_7","comeback_arc","night_session","early_hunter",
    # Boss (1)
    "boss_slayer",
}

TIER_XP = {"basic": 50, "medium": 100, "major": 250, "elite": 500}


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def v3_profile(api):
    """Profile with bw=80, squat=200, bench=140, deadlift=240.
    Ratios: 2.5 squat, 1.75 bench, 3.0 deadlift; total=580 → rank D."""
    payload = {
        "name": "TEST_v3_strength",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 200, "bench_max": 140, "deadlift_max": 240,
        "training_days": 4, "goal_total": 1000,
    }
    r = api.post(f"{BASE_URL}/api/profile", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ----- Achievement catalog: 84 entries with full shape -----
def test_achievements_endpoint_returns_84_with_full_shape(api, v3_profile):
    r = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}/achievements")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) == 84, f"Expected 84 achievements, got {len(items)}"
    keys = {it["key"] for it in items}
    missing = EXPECTED_KEYS - keys
    extra = keys - EXPECTED_KEYS
    assert not missing, f"Missing keys: {missing}"
    assert not extra, f"Unexpected extras: {extra}"
    # Verify each has full shape
    for it in items:
        for fld in ("key","name","desc","category","tier","xp","unlocked"):
            assert fld in it, f"{it['key']} missing field {fld}"
        assert it["tier"] in TIER_XP, f"{it['key']} bad tier {it['tier']}"
        assert it["xp"] == TIER_XP[it["tier"]], f"{it['key']} xp mismatch"
        assert isinstance(it["unlocked"], bool)


def test_categories_coverage(api, v3_profile):
    r = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}/achievements")
    cats = {it["category"] for it in r.json()}
    # 18 categories per spec
    expected_cats = {
        "Squat","Bench","Deadlift","Total","Quests","Weekly","Streak",
        "Run","Pace","Sprint","Bike","Quality","Elite","Hybrid",
        "Volume","Rank","Special","Boss",
    }
    assert expected_cats.issubset(cats), f"Missing categories: {expected_cats - cats}"


# ----- Strength auto-unlock on profile create -----
def test_strength_autounlocks_on_profile_create(api, v3_profile):
    """bw=80, squat=200, bench=140, deadlift=240.
    Expect unlocked: squat_100/140/180/200, bench_100/140, deadlift_140/180/220/240,
    total_500, rank_d (total=580 in [500,599]), squat_specialist (200/80=2.5),
    bench_technician (140/80=1.75), deadlift_monster (240/80=3.0)."""
    r = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}/achievements")
    unlocked = {it["key"] for it in r.json() if it["unlocked"]}
    must_have = {
        "squat_100","squat_140","squat_180","squat_200",
        "bench_100","bench_140",
        "deadlift_140","deadlift_180","deadlift_220","deadlift_240",
        "total_500",
        "rank_d",
        "squat_specialist","bench_technician","deadlift_monster",
    }
    missing = must_have - unlocked
    assert not missing, f"Missing auto-unlocks: {missing}"
    # These should NOT be unlocked at these maxes
    must_not_have = {"squat_220","bench_160","deadlift_260","total_600","rank_c"}
    wrong = must_not_have & unlocked
    assert not wrong, f"Wrongly unlocked: {wrong}"


def test_xp_awarded_for_unlocks_on_create(api):
    """Each unlocked achievement on create should add its tier XP."""
    payload = {
        "name": "TEST_v3_xp_check",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 200, "bench_max": 140, "deadlift_max": 240,
        "training_days": 4, "goal_total": 1000,
    }
    r = api.post(f"{BASE_URL}/api/profile", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    # XP should be positive (achievements were unlocked on creation)
    # apply_xp may have leveled up; just verify xp>0 OR level>1
    assert body["xp"] > 0 or body["level"] > 1, body


# ----- Cardio: RUN -----
def test_cardio_run_5km_5min_pace(api, v3_profile):
    """5km in 1500s = 300 sec/km = 5:00 exactly.
    Unlocks: run_1k, run_3k, run_5k. Pace<360 sub_6 YES, <330 sub_5_30 YES, <300 sub_5 NO."""
    r = api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "run", "distance_km": 5, "duration_sec": 1500,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    new_keys = {a["key"] for a in body["new_achievements"]}
    # Distance-based
    for k in ("run_1k","run_3k","run_5k"):
        assert k in new_keys, f"{k} should unlock; got {new_keys}"
    assert "run_10k" not in new_keys
    # Pace: 300 == not < 300 (strict)
    assert "pace_sub_6" in new_keys
    assert "pace_sub_5_30" in new_keys
    assert "pace_sub_5" not in new_keys, "pace 300sec/km should NOT unlock sub_5 (strict <)"
    # Stats
    assert body["stats"]["total_run_km"] == 5
    assert body["stats"]["longest_run_km"] == 5
    assert body["stats"]["best_run_pace_sec_per_km"] == 300


def test_total_run_km_accumulates_and_best_pace(api, v3_profile):
    """Second run adds to total; faster pace overrides best."""
    pre = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}").json()
    pre_total = pre.get("total_run_km", 0)
    pre_pace = pre.get("best_run_pace_sec_per_km")
    # Slower pace (400 s/km) → should NOT override best
    r1 = api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "run", "distance_km": 2, "duration_sec": 800,
    })
    assert r1.status_code == 200
    s = r1.json()["stats"]
    assert s["total_run_km"] == round(pre_total + 2, 2)
    assert s["best_run_pace_sec_per_km"] == pre_pace  # unchanged
    # Faster pace (250 s/km) → updates best
    r2 = api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "run", "distance_km": 4, "duration_sec": 1000,
    })
    assert r2.status_code == 200
    s2 = r2.json()["stats"]
    assert s2["best_run_pace_sec_per_km"] == 250
    # Now sub_5 and sub_4_30 should unlock
    ach = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}/achievements").json()
    unlocked = {a["key"] for a in ach if a["unlocked"]}
    assert "pace_sub_5" in unlocked
    assert "pace_sub_4_30" in unlocked


# ----- Cardio: SPRINT -----
def test_cardio_sprint_100m_under_20(api, v3_profile):
    r = api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "sprint", "sprint_distance_m": 100, "sprint_time_sec": 18.5,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    new_keys = {a["key"] for a in body["new_achievements"]}
    assert "sprint_100_20" in new_keys
    # Verify per-distance storage
    p = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}").json()
    assert p["best_sprint_100m"] == 18.5


def test_cardio_sprint_per_distance_storage(api, v3_profile):
    # 200m at 35s
    api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "sprint", "sprint_distance_m": 200, "sprint_time_sec": 35.0,
    })
    # 400m at 85s
    api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "sprint", "sprint_distance_m": 400, "sprint_time_sec": 85.0,
    })
    p = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}").json()
    assert p["best_sprint_100m"] == 18.5
    assert p["best_sprint_200m"] == 35.0
    assert p["best_sprint_400m"] == 85.0
    # Slower attempt shouldn't override best
    api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "sprint", "sprint_distance_m": 100, "sprint_time_sec": 19.5,
    })
    p2 = api.get(f"{BASE_URL}/api/profile/{v3_profile['id']}").json()
    assert p2["best_sprint_100m"] == 18.5  # unchanged


# ----- Cardio: BIKE -----
def test_cardio_bike_10km(api, v3_profile):
    r = api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "bike", "distance_km": 10,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    new_keys = {a["key"] for a in body["new_achievements"]}
    assert "bike_5" in new_keys
    assert "bike_10" in new_keys
    assert "bike_20" not in new_keys
    assert body["stats"]["total_bike_km"] == 10
    assert body["stats"]["longest_bike_km"] == 10


# ----- Cardio: validation -----
def test_cardio_run_missing_fields_returns_400(api, v3_profile):
    r = api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "run", "distance_km": 5,  # missing duration_sec
    })
    assert r.status_code == 400


def test_cardio_invalid_activity_returns_400(api, v3_profile):
    r = api.post(f"{BASE_URL}/api/profile/{v3_profile['id']}/cardio", json={
        "activity": "swim", "distance_km": 1,
    })
    assert r.status_code == 400


def test_cardio_invalid_profile_404(api):
    r = api.post(f"{BASE_URL}/api/profile/nope-uuid/cardio", json={
        "activity": "bike", "distance_km": 5,
    })
    assert r.status_code == 404


# ----- Tier XP awarded on unlock via cardio -----
def test_cardio_unlock_grants_tier_xp(api):
    """Create fresh profile, log a run that unlocks 3 basic + pace medium achievements."""
    payload = {
        "name": "TEST_v3_cardio_xp",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 50, "bench_max": 40, "deadlift_max": 60,  # tiny, no strength achievements
        "training_days": 4, "goal_total": 500,
    }
    pr = api.post(f"{BASE_URL}/api/profile", json=payload).json()
    pre_xp = pr["xp"]
    pre_lvl = pr["level"]
    r = api.post(f"{BASE_URL}/api/profile/{pr['id']}/cardio", json={
        "activity": "run", "distance_km": 5, "duration_sec": 1500,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    # achievement_xp in response should equal sum of tier xp of new achievements
    expected_ach_xp = sum(TIER_XP[a["tier"]] for a in body["new_achievements"])
    assert body["achievement_xp"] == expected_ach_xp, body
    # base cardio xp = 50 + min(150,5*15)=75 → 125
    # Verify total grew by at least achievement_xp + 125 (modulo level-up math)
    total_after = body["total_xp"]
    # Just verify it's increased meaningfully
    # since apply_xp may level up, compute total absolute xp gained
    def abs_xp(level, xp):
        # sum of (500 + 250*(L-1)) for L=1..level-1 + xp
        s = 0
        for L in range(1, level):
            s += 500 + 250 * (L - 1)
        return s + xp
    grown = abs_xp(body["level"], total_after) - abs_xp(pre_lvl, pre_xp)
    assert grown == 125 + expected_ach_xp, (grown, expected_ach_xp)


# ----- Session volume from workout log -----
def test_workout_log_session_volume_kg_and_volume_10k(api):
    """Build a profile with strong lifts so SQUAT_DAY at week 5 (HEAVY 87.5%) gives big weights.
    But to hit 10k easier, manually create profile and craft logged weights/reps."""
    payload = {
        "name": "TEST_v3_volume",
        "bodyweight": 90, "experience": "Advanced",
        "squat_max": 250, "bench_max": 180, "deadlift_max": 300,
        "training_days": 4, "goal_total": 1000,
    }
    pr = api.post(f"{BASE_URL}/api/profile", json=payload).json()
    # Use week 5 SQUAT_DAY (HEAVY)
    w = next(x for x in pr["workouts"] if x["week"] == 5 and x["day_type"] == "SQUAT_DAY")
    # session_volume = sum(logged_weight * logged_reps * target_sets) for done exercises
    # Override logged_weight/reps to ensure >= 10000kg
    rows = []
    for ex in w["exercises"]:
        rows.append({
            "name": ex["name"],
            "target_sets": ex["sets"],
            "target_reps": ex["reps"],
            "target_weight": ex["weight"],
            "target_rpe": ex.get("target_rpe"),
            "logged_weight": 200,   # heavy
            "logged_reps": 10,
            "logged_rpe": ex.get("target_rpe"),
            "is_main": ex.get("is_main", False),
            "done": True,
        })
    # sets per exercise: 4,3,3 => volume = 200*10*(4+3+3) = 200*10*10 = 20000
    r = api.post(f"{BASE_URL}/api/profile/{pr['id']}/workout/log", json={
        "workout_id": w["id"], "exercises": rows,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    new_keys = {a["key"] for a in body["new_achievements"]}
    assert "volume_session_10k" in new_keys, f"expected volume_session_10k unlock; new={new_keys}"
    # Fetch workout to verify session_volume_kg stored on the workout
    gw = api.get(f"{BASE_URL}/api/profile/{pr['id']}/workout/{w['id']}").json()
    assert gw.get("session_volume_kg") == 20000.0, gw.get("session_volume_kg")
    # Profile max_session_volume_kg updated
    p2 = api.get(f"{BASE_URL}/api/profile/{pr['id']}").json()
    assert p2["max_session_volume_kg"] == 20000.0


def test_session_volume_below_10k_does_not_unlock(api):
    payload = {
        "name": "TEST_v3_volume_low",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 100, "bench_max": 80, "deadlift_max": 120,
        "training_days": 4, "goal_total": 800,
    }
    pr = api.post(f"{BASE_URL}/api/profile", json=payload).json()
    w = next(x for x in pr["workouts"] if x["week"] == 1 and x["day_type"] == "SQUAT_DAY")
    rows = []
    for ex in w["exercises"]:
        rows.append({
            "name": ex["name"], "target_sets": ex["sets"], "target_reps": ex["reps"],
            "target_weight": ex["weight"], "target_rpe": ex.get("target_rpe"),
            "logged_weight": ex["weight"], "logged_reps": ex["reps"],
            "logged_rpe": ex.get("target_rpe"),
            "is_main": ex.get("is_main", False), "done": True,
        })
    r = api.post(f"{BASE_URL}/api/profile/{pr['id']}/workout/log", json={
        "workout_id": w["id"], "exercises": rows,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    new_keys = {a["key"] for a in body["new_achievements"]}
    assert "volume_session_10k" not in new_keys


# ----- Comeback achievement (last workout 5+ days ago) -----
def test_comeback_achievement_unlocks_after_5_day_gap(api):
    payload = {
        "name": "TEST_v3_comeback",
        "bodyweight": 80, "experience": "Intermediate",
        "squat_max": 150, "bench_max": 100, "deadlift_max": 200,
        "training_days": 4, "goal_total": 800,
    }
    pr = api.post(f"{BASE_URL}/api/profile", json=payload).json()
    # Manually backdate last_workout_date 10 days ago via direct DB
    import subprocess, json as _json
    ten_days_ago = (datetime.now(timezone.utc) - timedelta(days=10)).date().isoformat()
    cmd = [
        "mongosh","--quiet","--eval",
        f'db.getSiblingDB("hunter_db").profiles.updateOne({{id:"{pr["id"]}"}},'
        f'{{$set:{{last_workout_date:"{ten_days_ago}", streak: 5}}}})'
    ]
    subprocess.run(cmd, check=False, capture_output=True, timeout=10)
    # Now complete a workout - should trigger comeback (diff>=5)
    w = next(x for x in pr["workouts"] if x["week"] == 1 and x["day_type"] == "UPPER_ACC")
    rows = []
    for ex in w["exercises"]:
        rows.append({
            "name": ex["name"], "target_sets": ex["sets"], "target_reps": ex["reps"],
            "target_weight": ex["weight"], "target_rpe": ex.get("target_rpe"),
            "logged_weight": ex["weight"], "logged_reps": ex["reps"],
            "logged_rpe": ex.get("target_rpe"),
            "is_main": False, "done": True,
        })
    r = api.post(f"{BASE_URL}/api/profile/{pr['id']}/workout/log", json={
        "workout_id": w["id"], "exercises": rows,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    new_keys = {a["key"] for a in body["new_achievements"]}
    assert "comeback_arc" in new_keys, f"comeback_arc should unlock; got {new_keys}"
    # Verify comeback_count persisted
    p2 = api.get(f"{BASE_URL}/api/profile/{pr['id']}").json()
    assert p2["comeback_count"] >= 1


# ----- Existing endpoints still work -----
def test_existing_endpoints_smoke(api, v3_profile):
    pid = v3_profile["id"]
    # dashboard
    d = api.get(f"{BASE_URL}/api/profile/{pid}/dashboard")
    assert d.status_code == 200 and "profile" in d.json()
    # workouts list
    w = api.get(f"{BASE_URL}/api/profile/{pid}/workouts")
    assert w.status_code == 200 and len(w.json()) == 24
    # progress
    pr = api.get(f"{BASE_URL}/api/profile/{pid}/progress")
    assert pr.status_code == 200
    # 404
    r404 = api.get(f"{BASE_URL}/api/profile/does-not-exist")
    assert r404.status_code == 404


# ----- Cleanup -----
def test_v3_cleanup_test_profiles():
    import subprocess
    try:
        subprocess.run(
            ["mongosh","--quiet","--eval",
             'db.getSiblingDB("hunter_db").profiles.deleteMany({name: /^TEST_v3/})'],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:
        pass
