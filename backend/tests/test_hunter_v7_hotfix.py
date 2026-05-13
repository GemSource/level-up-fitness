"""
v7 hotfix verification — boss-fight buff consumption (boss_mult).
Verifies the previously failing 200-path now succeeds AND that an active
boss_fight-scoped buff is consumed + multiplies xp_reward.
"""
import os
import pytest
import requests


def _load_backend_url():
    url = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
    if url:
        return url.rstrip("/")
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    raise RuntimeError("EXPO_PUBLIC_BACKEND_URL not set")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _create_profile(client, name, sq, bn, dl, goal=900, days=3, exp="intermediate"):
    payload = {
        "name": name, "bodyweight": 80.0, "experience": exp,
        "squat_max": sq, "bench_max": bn, "deadlift_max": dl,
        "training_days": days, "goal_total": goal,
    }
    r = client.post(f"{API}/profile", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _complete_workout(client, pid, workout, rpe=8):
    ex_inputs = []
    for ex in workout["exercises"]:
        ex_inputs.append({
            "name": ex["name"], "sets": ex["sets"], "reps": ex["reps"],
            "weight": ex["weight"], "is_main": ex.get("is_main", False),
            "target_sets": ex["sets"], "target_weight": ex["weight"],
            "target_reps": ex["reps"], "target_rpe": ex.get("target_rpe"),
            "logged_weight": ex["weight"], "logged_reps": ex["reps"],
            "logged_rpe": rpe, "done": True,
        })
    return client.post(f"{API}/profile/{pid}/workout/log",
                       json={"workout_id": workout["id"], "exercises": ex_inputs})


def _unlock_boss(client, name, sq=160, bn=100, dl=200):
    prof = _create_profile(client, name=name, sq=sq, bn=bn, dl=dl)
    pid = prof["id"]
    for _ in range(6):
        ws = client.get(f"{API}/profile/{pid}/workouts").json()
        nxt = next((w for w in ws if not w.get("completed")), None)
        if not nxt:
            break
        r = _complete_workout(client, pid, nxt, rpe=8)
        assert r.status_code == 200, r.text
    req = client.get(f"{API}/profile/{pid}/boss-fight/requirements").json()
    assert req.get("locked") is False, f"still locked: {req}"
    return pid


# ---- Hotfix: previously failing test re-verified ----
class TestBossFightHotfix:
    def test_boss_fight_returns_200_with_all_v7_fields(self, client):
        """Previously failed with 500 NameError. Should now return 200 with required fields."""
        pid = _unlock_boss(client, "TEST_v7hf_basic")
        before = client.get(f"{API}/profile/{pid}/inventory").json()
        coins_before = before["coins"]

        r = client.post(f"{API}/profile/{pid}/boss-fight",
                        json={"squat_max": 165, "bench_max": 105, "deadlift_max": 205})
        assert r.status_code == 200, r.text
        d = r.json()
        # required v7 fields
        for k in ("coins_gained", "total_coins", "buff_used", "new_achievements",
                  "xp_reward", "old_rank", "new_rank", "rank_up"):
            assert k in d, f"missing field {k} in response: {d}"
        # coins_gained in 200 or 400
        assert d["coins_gained"] in (200, 400), f"coins_gained should be 200 or 400, got {d['coins_gained']}"
        # buff_used null when no active boss buff
        assert d["buff_used"] is None
        # total_coins >= coins_before + coins_gained (extra from new achievement coin rewards is allowed)
        assert d["total_coins"] >= coins_before + d["coins_gained"], (
            f"total_coins {d['total_coins']} < {coins_before} + {d['coins_gained']}")
        # Persistence: GET inventory reflects new coins
        inv_after = client.get(f"{API}/profile/{pid}/inventory").json()
        assert inv_after["coins"] == d["total_coins"], (
            f"persisted coins {inv_after['coins']} != response {d['total_coins']}")

    def test_boss_fight_rank_up_grants_400_coins(self, client):
        """When new_rank != old_rank, coins_gained should be 400."""
        pid = _unlock_boss(client, "TEST_v7hf_rankup")
        # Push maxes high enough to bump rank (E→D requires total >= ~500-ish; bumping to 200/130/250=580)
        r = client.post(f"{API}/profile/{pid}/boss-fight",
                        json={"squat_max": 210, "bench_max": 140, "deadlift_max": 260})
        assert r.status_code == 200, r.text
        d = r.json()
        if d["rank_up"]:
            assert d["coins_gained"] == 400, f"rank_up should yield 400 coins, got {d['coins_gained']}"
        else:
            assert d["coins_gained"] == 200


# ---- Buff consumption (boss_mult) ----
class TestBossFightBuffConsumption:
    def test_boss_mult_buff_consumed_and_multiplies_xp(self, client):
        """Activate adrenaline (boss_mult x1.5, scope=boss_fight). Post boss-fight:
        - xp_reward should be 1500 (1000 * 1.5)
        - buff_used should reflect the adrenaline item (not None)
        - adrenaline removed from active_buffs after consumption
        """
        pid = _unlock_boss(client, "TEST_v7hf_buff")
        inv = client.get(f"{API}/profile/{pid}/inventory").json()
        if inv["coins"] < 300:
            pytest.skip(f"need 300 coins for adrenaline, have {inv['coins']}")
        # Buy + activate adrenaline
        rb = client.post(f"{API}/profile/{pid}/shop/buy", json={"item_key": "adrenaline"})
        assert rb.status_code == 200, rb.text
        ra = client.post(f"{API}/profile/{pid}/inventory/activate", json={"item_key": "adrenaline"})
        assert ra.status_code == 200, ra.text
        active = ra.json()["active_buffs"]
        assert any(b["item_key"] == "adrenaline" for b in active), f"adrenaline not active: {active}"

        # Boss fight
        r = client.post(f"{API}/profile/{pid}/boss-fight",
                        json={"squat_max": 165, "bench_max": 105, "deadlift_max": 205})
        assert r.status_code == 200, r.text
        d = r.json()

        # buff_used reflects adrenaline (consume_active_buff returns catalog dict w/o item_key)
        assert d["buff_used"] is not None, "buff_used should not be None when boss buff active"
        bu = d["buff_used"]
        assert bu.get("name") == "Adrenaline Surge", f"buff_used not adrenaline: {bu}"
        assert bu.get("effect") == "boss_mult"
        assert abs(float(bu.get("value", 0)) - 1.5) < 0.01
        assert bu.get("scope") == "boss_fight"

        # xp_reward = 1000 * 1.5 = 1500
        assert d["xp_reward"] == 1500, f"expected xp_reward=1500 with 1.5x buff, got {d['xp_reward']}"

        # Buff removed from active_buffs
        inv_after = client.get(f"{API}/profile/{pid}/inventory").json()
        assert all(b.get("item_key") != "adrenaline" for b in inv_after["active_buffs"]), (
            f"adrenaline not consumed: {inv_after['active_buffs']}")

    def test_workout_scoped_buff_NOT_consumed_by_boss_fight(self, client):
        """A workout-scoped buff (power_boost) should NOT be consumed by a boss-fight."""
        pid = _unlock_boss(client, "TEST_v7hf_scope_isolation")
        inv = client.get(f"{API}/profile/{pid}/inventory").json()
        if inv["coins"] < 80:
            pytest.skip(f"need 80 coins for power_boost, have {inv['coins']}")
        assert client.post(f"{API}/profile/{pid}/shop/buy", json={"item_key": "power_boost"}).status_code == 200
        assert client.post(f"{API}/profile/{pid}/inventory/activate", json={"item_key": "power_boost"}).status_code == 200

        r = client.post(f"{API}/profile/{pid}/boss-fight",
                        json={"squat_max": 165, "bench_max": 105, "deadlift_max": 205})
        assert r.status_code == 200, r.text
        d = r.json()
        # boss-fight should NOT consume workout-scoped buff
        assert d["buff_used"] is None, f"workout-scoped buff incorrectly consumed: {d['buff_used']}"
        assert d["xp_reward"] == 1000, f"xp_reward should be unmultiplied 1000, got {d['xp_reward']}"

        inv_after = client.get(f"{API}/profile/{pid}/inventory").json()
        assert any(b.get("item_key") == "power_boost" for b in inv_after["active_buffs"]), (
            "power_boost (workout scope) should still be active after boss-fight")
