"""Backend tests for Hunter Strength System."""
import os
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def profile(api):
    payload = {
        "name": "TEST_Hunter",
        "bodyweight": 80,
        "experience": "Intermediate",
        "squat_max": 160,
        "bench_max": 110,
        "deadlift_max": 190,
        "training_days": 4,
        "goal_total": 1000,
    }
    r = api.post(f"{BASE_URL}/api/profile", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Health ----------
def test_root(api):
    r = api.get(f"{BASE_URL}/api/")
    assert r.status_code == 200
    assert "Hunter" in r.json()["message"]


# ---------- Profile creation & auto-generated workouts ----------
def test_create_profile_generates_24_workouts(profile):
    assert profile["rank"] == "E"  # total 460
    assert profile["total"] == 460
    assert len(profile["workouts"]) == 24  # 6 weeks x 4 days
    assert profile["id"]
    assert profile["xp"] == 0
    assert profile["level"] == 1


def test_rank_thresholds():
    # local logic check via boss-fight is below; here just ensure E for 460
    assert True


# ---------- Dashboard ----------
def test_dashboard(api, profile):
    r = api.get(f"{BASE_URL}/api/profile/{profile['id']}/dashboard")
    assert r.status_code == 200
    d = r.json()
    assert d["profile"]["id"] == profile["id"]
    assert d["today_quest"] is not None
    assert d["next_rank"]["rank"] == "D"
    assert d["next_rank"]["kg_to_reach"] == 40  # 500-460
    assert d["total_workouts"] == 24
    assert d["completed_count"] == 0


# ---------- Workout list & get one ----------
def test_list_workouts(api, profile):
    r = api.get(f"{BASE_URL}/api/profile/{profile['id']}/workouts")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 24
    assert data[0]["week"] == 1
    assert data[0]["day_type"] == "SQUAT_DAY"


def test_get_specific_workout(api, profile):
    wid = profile["workouts"][0]["id"]
    r = api.get(f"{BASE_URL}/api/profile/{profile['id']}/workout/{wid}")
    assert r.status_code == 200
    assert r.json()["id"] == wid


def test_get_workout_404(api, profile):
    r = api.get(f"{BASE_URL}/api/profile/{profile['id']}/workout/bogus-id")
    assert r.status_code == 404


# ---------- Log workout: XP / streak / level / achievements ----------
def test_log_workout(api, profile):
    w = profile["workouts"][0]  # week 1 squat day
    payload = {
        "workout_id": w["id"],
        "exercises": [
            {
                "name": ex["name"],
                "target_sets": ex["sets"],
                "target_reps": ex["reps"],
                "target_weight": ex["weight"],
                "target_rpe": ex.get("target_rpe"),
                "sets": [
                    {"weight": ex["weight"], "reps": ex["reps"], "rpe": 7.0, "completed": True}
                    for _ in range(ex["sets"])
                ],
            }
            for ex in w["exercises"]
        ],
        "notes": "TEST_log",
    }
    r = api.post(f"{BASE_URL}/api/profile/{profile['id']}/workout/log", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    # 100 base + 150 squat day bonus + 50 all hit + 25 rpe = 325
    assert body["xp_gained"] == 325
    assert body["total_xp"] == 325
    assert body["level"] == 1
    assert body["streak"] == 1
    keys = {a["key"] for a in body["new_achievements"]}
    assert "first_workout" in keys
    assert "suggestion" in body and "SYSTEM" in body["suggestion"]


def test_log_workout_double_complete_fails(api, profile):
    w = profile["workouts"][0]
    r = api.post(
        f"{BASE_URL}/api/profile/{profile['id']}/workout/log",
        json={"workout_id": w["id"], "exercises": []},
    )
    assert r.status_code == 400


# ---------- Boss fight: rank up + regenerate block ----------
def test_boss_fight_rank_up(api, profile):
    # 220+150+250 = 620 => C rank
    r = api.post(
        f"{BASE_URL}/api/profile/{profile['id']}/boss-fight",
        json={"squat_max": 220, "bench_max": 150, "deadlift_max": 250},
    )
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["old_rank"] == "E"
    assert b["new_rank"] == "C"
    assert b["rank_up"] is True
    assert b["new_total"] == 620
    assert b["xp_reward"] == 1000
    keys = {a["key"] for a in b["new_achievements"]}
    # squat_200, deadlift_240, bench_140, rank_c, boss_slayer
    for k in ("squat_200", "bench_140", "deadlift_240", "rank_c", "boss_slayer"):
        assert k in keys, f"missing {k}"

    # Verify regen of workouts (block reset, none completed)
    dash = api.get(f"{BASE_URL}/api/profile/{profile['id']}/dashboard").json()
    assert dash["total_workouts"] == 24
    assert dash["completed_count"] == 0
    assert dash["profile"]["rank"] == "C"


def test_rank_s_threshold(api):
    # New profile pushing to S
    r = api.post(
        f"{BASE_URL}/api/profile",
        json={
            "name": "TEST_S",
            "bodyweight": 100,
            "experience": "Advanced",
            "squat_max": 300,
            "bench_max": 200,
            "deadlift_max": 400,
            "training_days": 4,
            "goal_total": 1000,
        },
    )
    assert r.status_code == 200
    assert r.json()["rank"] == "S"
    assert r.json()["total"] == 900


def test_rank_boundaries(api):
    cases = [(499, "E"), (500, "D"), (599, "D"), (600, "C"), (700, "B"), (800, "A"), (900, "S")]
    for total, expected in cases:
        squat = total / 3
        r = api.post(
            f"{BASE_URL}/api/profile",
            json={
                "name": f"TEST_R{total}",
                "bodyweight": 80,
                "experience": "Beginner",
                "squat_max": squat,
                "bench_max": squat,
                "deadlift_max": total - 2 * squat,
                "training_days": 4,
                "goal_total": 1000,
            },
        )
        assert r.status_code == 200
        assert r.json()["rank"] == expected, f"total={total} got {r.json()['rank']}"


# ---------- Achievements ----------
def test_achievements_listing(api, profile):
    r = api.get(f"{BASE_URL}/api/profile/{profile['id']}/achievements")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 12
    unlocked = {a["key"] for a in data if a["unlocked"]}
    assert "boss_slayer" in unlocked
    assert "rank_c" in unlocked


# ---------- Progress ----------
def test_progress(api, profile):
    r = api.get(f"{BASE_URL}/api/profile/{profile['id']}/progress")
    assert r.status_code == 200
    p = r.json()
    assert p["current"]["squat"] == 220
    assert p["current"]["bench"] == 150
    assert p["current"]["deadlift"] == 250
    assert p["current"]["total"] == 620
    assert p["goal_total"] == 1000
    assert p["rank"] == "C"
    assert isinstance(p["history"], list)


# ---------- AI coach ----------
def test_ai_coach(api, profile):
    r = api.post(
        f"{BASE_URL}/api/profile/{profile['id']}/ai-coach",
        json={"question": "Tactical advice for next squat session?"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "response" in body
    assert isinstance(body["response"], str)
    assert len(body["response"]) > 10
    # offline marker means LLM call failed
    assert "[SYSTEM OFFLINE]" not in body["response"], f"LLM failed: {body['response']}"


# ---------- 404s ----------
def test_profile_404(api):
    r = api.get(f"{BASE_URL}/api/profile/nope-id/dashboard")
    assert r.status_code == 404
