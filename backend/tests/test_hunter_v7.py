"""
v7 Hunter — Shop + Loot Drop + Inventory + Buff system pytest suite.
Targets endpoints: /shop/catalog, /profile/{id}/inventory, /shop/buy, /inventory/activate,
plus coin/buff/loot integration into /workout/log and /boss-fight.
Regression: dashboard, achievements, rank-progress, progress, cardio, ai-coach, 404s.
"""
import os
import pytest
import requests
from typing import Any, Dict, List

def _load_backend_url():
    # Prefer env, else read from /app/frontend/.env
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


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _create_profile(client, name="TEST_v7_default", sq=100, bn=70, dl=130, goal=500, days=4, exp="intermediate"):
    payload = {
        "name": name,
        "bodyweight": 80.0,
        "experience": exp,
        "squat_max": sq,
        "bench_max": bn,
        "deadlift_max": dl,
        "training_days": days,
        "goal_total": goal,
    }
    r = client.post(f"{API}/profile", json=payload)
    assert r.status_code == 200, f"profile create failed: {r.status_code} {r.text}"
    return r.json()


def _complete_workout(client, pid: str, workout: Dict[str, Any], rpe: int = 8):
    """Mark every exercise as done at target weight/reps to fully complete the quest."""
    ex_inputs = []
    for ex in workout["exercises"]:
        ex_inputs.append({
            "name": ex["name"],
            "sets": ex["sets"],
            "reps": ex["reps"],
            "weight": ex["weight"],
            "is_main": ex.get("is_main", False),
            "target_sets": ex["sets"],
            "target_weight": ex["weight"],
            "target_reps": ex["reps"],
            "target_rpe": ex.get("target_rpe"),
            "logged_weight": ex["weight"],
            "logged_reps": ex["reps"],
            "logged_rpe": rpe,
            "done": True,
        })
    body = {"workout_id": workout["id"], "exercises": ex_inputs}
    r = client.post(f"{API}/profile/{pid}/workout/log", json=body)
    return r


# ---------------- shop catalog ----------------
class TestShopCatalog:
    def test_catalog_returns_10_items_with_required_fields(self, client):
        r = client.get(f"{API}/shop/catalog")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) == 10, f"expected 10 catalog items, got {len(items)}"
        required = {"key", "name", "desc", "category", "rarity", "price", "effect", "value", "scope", "rarity_color"}
        for it in items:
            missing = required - set(it.keys())
            assert not missing, f"item {it.get('key')} missing fields: {missing}"
            assert isinstance(it["price"], int) and it["price"] > 0
            assert it["rarity"] in {"common", "rare", "epic", "legendary"}
            assert it["rarity_color"].startswith("#")


# ---------------- create profile awards coins ----------------
class TestCoinsOnCreate:
    def test_initial_coins_awarded_from_auto_unlocked_achievements(self, client):
        # sq100/bn70/dl130 -> total 300 (E rank), but squat_100 + deadlift_100 etc auto-unlock
        prof = _create_profile(client, name="TEST_v7_create_coins", sq=100, bn=70, dl=130)
        assert "coins" in prof, "profile missing 'coins' field"
        assert prof["coins"] > 0, f"expected coins > 0 after auto-unlocked achievements, got {prof['coins']}"


# ---------------- inventory shape ----------------
class TestInventoryShape:
    def test_inventory_returns_expected_keys(self, client):
        prof = _create_profile(client, name="TEST_v7_inv_shape")
        r = client.get(f"{API}/profile/{prof['id']}/inventory")
        assert r.status_code == 200
        data = r.json()
        assert set(data.keys()) >= {"coins", "items", "active_buffs"}
        assert isinstance(data["items"], list)
        assert isinstance(data["active_buffs"], list)
        assert isinstance(data["coins"], int)

    def test_inventory_invalid_profile_returns_404(self, client):
        r = client.get(f"{API}/profile/does-not-exist-v7/inventory")
        assert r.status_code == 404


# ---------------- shop buy ----------------
class TestShopBuy:
    def test_buy_with_sufficient_coins(self, client):
        prof = _create_profile(client, name="TEST_v7_buy_ok")
        pid = prof["id"]
        # Top up coins directly via Mongo? No — just pick a cheap item if affordable, else pre-grant via DB unsupported.
        # power_boost costs 80, and create awards coins from achievements (squat_100 beginner=25 + deadlift_100 beginner=25 + bench_50? ...). Verify dynamically.
        inv = client.get(f"{API}/profile/{pid}/inventory").json()
        coins_now = inv["coins"]
        if coins_now < 80:
            pytest.skip(f"initial coins {coins_now} < 80, can't buy power_boost without DB seeding")
        r = client.post(f"{API}/profile/{pid}/shop/buy", json={"item_key": "power_boost"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["coins"] == coins_now - 80
        assert data["inventory"].get("power_boost", 0) >= 1
        assert data["purchased"]["name"] == "Power Boost"
        # Verify via GET inventory
        inv2 = client.get(f"{API}/profile/{pid}/inventory").json()
        assert inv2["coins"] == coins_now - 80
        assert any(it["key"] == "power_boost" for it in inv2["items"])

    def test_buy_insufficient_coins_returns_400(self, client):
        prof = _create_profile(client, name="TEST_v7_buy_poor", sq=60, bn=40, dl=80)
        # Profile has minimal/zero coins. Try to buy legendary_aura (1500)
        r = client.post(f"{API}/profile/{prof['id']}/shop/buy", json={"item_key": "legendary_aura"})
        assert r.status_code == 400
        detail = r.json().get("detail")
        assert isinstance(detail, dict)
        assert detail.get("error") == "insufficient_coins"

    def test_buy_unknown_item_returns_400(self, client):
        prof = _create_profile(client, name="TEST_v7_buy_unknown")
        r = client.post(f"{API}/profile/{prof['id']}/shop/buy", json={"item_key": "no_such_item"})
        assert r.status_code == 400

    def test_buy_invalid_profile_404(self, client):
        r = client.post(f"{API}/profile/no-such-pid/shop/buy", json={"item_key": "power_boost"})
        assert r.status_code == 404


# ---------------- activate ----------------
class TestActivate:
    def _seed_inventory(self, client, item_key: str, count: int = 1):
        prof = _create_profile(client, name=f"TEST_v7_activate_{item_key}_{count}")
        pid = prof["id"]
        # Buy items if affordable
        inv = client.get(f"{API}/profile/{pid}/inventory").json()
        catalog = {x["key"]: x for x in client.get(f"{API}/shop/catalog").json()}
        price = catalog[item_key]["price"]
        if inv["coins"] < price * count:
            pytest.skip(f"insufficient seed coins {inv['coins']} for {count}x {item_key} @ {price}")
        for _ in range(count):
            r = client.post(f"{API}/profile/{pid}/shop/buy", json={"item_key": item_key})
            assert r.status_code == 200
        return pid

    def test_activate_moves_item_to_active_buffs(self, client):
        pid = self._seed_inventory(client, "power_boost", 1)
        r = client.post(f"{API}/profile/{pid}/inventory/activate", json={"item_key": "power_boost"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["active_buffs"]) == 1
        assert data["active_buffs"][0]["item_key"] == "power_boost"
        assert data["active_buffs"][0]["scope"] == "workout"
        assert "power_boost" not in data["inventory"] or data["inventory"]["power_boost"] == 0

    def test_max_two_active_buffs(self, client):
        # Need 3 cheap items - use power_boost (80) x3 = 240. Some profiles won't have 240 initially.
        # Seed strong profile via achievements -> sq100/bn70/dl130 unlocks squat_100, deadlift_100 etc.
        prof = _create_profile(client, name="TEST_v7_max_buffs", sq=100, bn=70, dl=130)
        pid = prof["id"]
        inv = client.get(f"{API}/profile/{pid}/inventory").json()
        if inv["coins"] < 240:
            pytest.skip(f"need >=240 coins for 3 power_boost buys, have {inv['coins']}")
        for _ in range(3):
            assert client.post(f"{API}/profile/{pid}/shop/buy", json={"item_key": "power_boost"}).status_code == 200
        # Activate first two
        for _ in range(2):
            r = client.post(f"{API}/profile/{pid}/inventory/activate", json={"item_key": "power_boost"})
            assert r.status_code == 200, r.text
        # Third should fail
        r3 = client.post(f"{API}/profile/{pid}/inventory/activate", json={"item_key": "power_boost"})
        assert r3.status_code == 400, f"expected 400 on 3rd activate, got {r3.status_code}: {r3.text}"

    def test_activate_item_not_in_inventory(self, client):
        prof = _create_profile(client, name="TEST_v7_act_empty")
        r = client.post(f"{API}/profile/{prof['id']}/inventory/activate", json={"item_key": "power_boost"})
        assert r.status_code == 400


# ---------------- workout log: coins + loot + buff consumption ----------------
class TestWorkoutLogV7:
    def test_full_workout_yields_coins_and_loot(self, client):
        prof = _create_profile(client, name="TEST_v7_workout_full")
        pid = prof["id"]
        workouts = client.get(f"{API}/profile/{pid}/workouts").json()
        first = workouts[0]
        r = _complete_workout(client, pid, first, rpe=8)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["workout_complete"] is True
        assert "coins_gained" in d and d["coins_gained"] >= 20, d
        assert "total_coins" in d
        assert "loot_drops" in d
        assert isinstance(d["loot_drops"], list) and len(d["loot_drops"]) >= 1
        # Each loot entry has required keys
        for drop in d["loot_drops"]:
            assert "type" in drop and drop["type"] in {"coins", "item"}
            assert "rarity" in drop
            assert "rarity_color" in drop
            assert "name" in drop

    def test_partial_workout_no_coins_no_loot(self, client):
        prof = _create_profile(client, name="TEST_v7_workout_partial")
        pid = prof["id"]
        workouts = client.get(f"{API}/profile/{pid}/workouts").json()
        first = workouts[0]
        # Log only the FIRST exercise as done (partial)
        ex_list = first["exercises"]
        ex_inputs = []
        for idx, ex in enumerate(ex_list):
            ex_inputs.append({
                "name": ex["name"], "sets": ex["sets"], "reps": ex["reps"],
                "weight": ex["weight"], "is_main": ex.get("is_main", False),
                "target_sets": ex["sets"],
                "target_weight": ex["weight"], "target_reps": ex["reps"],
                "target_rpe": ex.get("target_rpe"),
                "logged_weight": ex["weight"] if idx == 0 else None,
                "logged_reps": ex["reps"] if idx == 0 else None,
                "logged_rpe": 8 if idx == 0 else None,
                "done": idx == 0,
            })
        body = {"workout_id": first["id"], "exercises": ex_inputs}
        r = client.post(f"{API}/profile/{pid}/workout/log", json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["workout_complete"] is False
        assert d.get("coins_gained", 0) == 0
        assert d.get("loot_drops", []) == []

    def test_xp_mult_buff_consumed_on_workout(self, client):
        # Create profile with coins to buy xp_25 (100 coins)
        prof = _create_profile(client, name="TEST_v7_buff_consume", sq=100, bn=70, dl=130)
        pid = prof["id"]
        inv = client.get(f"{API}/profile/{pid}/inventory").json()
        if inv["coins"] < 100:
            pytest.skip(f"need 100 coins, have {inv['coins']}")
        # Buy + activate xp_25 (xp_mult 1.25, scope=workout)
        assert client.post(f"{API}/profile/{pid}/shop/buy", json={"item_key": "xp_25"}).status_code == 200
        ar = client.post(f"{API}/profile/{pid}/inventory/activate", json={"item_key": "xp_25"})
        assert ar.status_code == 200
        assert len(ar.json()["active_buffs"]) == 1
        # Complete workout
        workouts = client.get(f"{API}/profile/{pid}/workouts").json()
        first = workouts[0]
        r = _complete_workout(client, pid, first, rpe=8)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("buff_xp_extra", 0) > 0, f"expected buff_xp_extra > 0, got {d.get('buff_xp_extra')}"
        # Buff should be consumed
        inv_after = client.get(f"{API}/profile/{pid}/inventory").json()
        active = inv_after["active_buffs"]
        assert all(b["item_key"] != "xp_25" for b in active), f"xp_25 buff not consumed: {active}"


# ---------------- boss-fight v7 coins/buff fields ----------------
class TestBossFightV7:
    def _unlock_d_rank(self, client) -> str:
        """Create profile that meets D-rank requirements (sq160/bn100/dl200) and log 6 workouts."""
        prof = _create_profile(client, name="TEST_v7_boss_unlock", sq=160, bn=100, dl=200, goal=900, days=3, exp="intermediate")
        pid = prof["id"]
        # Log 6 workouts to clear quests requirement
        for _ in range(6):
            ws = client.get(f"{API}/profile/{pid}/workouts").json()
            nxt = next((w for w in ws if not w.get("completed")), None)
            if not nxt:
                break
            r = _complete_workout(client, pid, nxt, rpe=8)
            assert r.status_code == 200
        req = client.get(f"{API}/profile/{pid}/boss-fight/requirements").json()
        assert req.get("locked") is False, f"profile still locked after 6 workouts: {req}"
        return pid

    def test_boss_fight_response_v7_fields(self, client):
        pid = self._unlock_d_rank(client)
        body = {"squat_max": 165, "bench_max": 105, "deadlift_max": 205}
        r = client.post(f"{API}/profile/{pid}/boss-fight", json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "coins_gained" in d, "boss-fight response missing coins_gained"
        assert d["coins_gained"] >= 200, f"coins_gained should be >= 200, got {d['coins_gained']}"
        assert "total_coins" in d
        assert "buff_used" in d

    def test_boss_fight_locked_for_weak_profile(self, client):
        prof = _create_profile(client, name="TEST_v7_boss_locked_weak", sq=60, bn=40, dl=80)
        body = {"squat_max": 70, "bench_max": 50, "deadlift_max": 90}
        r = client.post(f"{API}/profile/{prof['id']}/boss-fight", json=body)
        assert r.status_code == 403
        assert r.json()["detail"]["error"] == "boss_fight_locked"


# ---------------- regression on previous endpoints ----------------
class TestRegression:
    @pytest.fixture(scope="class")
    def pid(self):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        prof = _create_profile(s, name="TEST_v7_regression")
        return prof["id"], s

    def test_dashboard(self, pid):
        p, s = pid
        r = s.get(f"{API}/profile/{p}/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert "profile" in d and "today_quest" in d and "next_rank" in d

    def test_rank_progress(self, pid):
        p, s = pid
        r = s.get(f"{API}/profile/{p}/rank-progress")
        assert r.status_code == 200

    def test_achievements(self, pid):
        p, s = pid
        r = s.get(f"{API}/profile/{p}/achievements")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_progress(self, pid):
        p, s = pid
        r = s.get(f"{API}/profile/{p}/progress")
        assert r.status_code == 200

    def test_boss_requirements(self, pid):
        p, s = pid
        r = s.get(f"{API}/profile/{p}/boss-fight/requirements")
        assert r.status_code == 200
        assert "locked" in r.json()

    def test_cardio_no_loot(self, pid):
        p, s = pid
        # Try cardio log; non-workout cardio should not generate loot_drops field
        body = {"type": "run", "distance_km": 3.0, "duration_sec": 1200}
        r = s.post(f"{API}/profile/{p}/cardio/log", json=body)
        # Endpoint may or may not exist with this exact shape; just check no 500
        assert r.status_code in (200, 400, 404, 422), r.text
        if r.status_code == 200:
            assert "loot_drops" not in r.json(), "cardio should not produce loot_drops"


# ---------------- ai-coach quick smoke ----------------
class TestAICoach:
    def test_ai_coach_returns_response_string(self, client):
        prof = _create_profile(client, name="TEST_v7_ai")
        r = client.post(f"{API}/profile/{prof['id']}/ai-coach", json={"question": "ping"})
        assert r.status_code == 200
        assert "response" in r.json()
