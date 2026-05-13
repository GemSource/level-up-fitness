from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---------------- Models ----------------
class OnboardingInput(BaseModel):
    name: str
    bodyweight: float
    experience: str  # Beginner / Intermediate / Advanced
    squat_max: float
    bench_max: float
    deadlift_max: float
    training_days: int = 4
    goal_total: float = 1000.0

class Profile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    bodyweight: float
    experience: str
    squat_max: float
    bench_max: float
    deadlift_max: float
    training_days: int
    goal_total: float
    total: float
    rank: str
    xp: int = 0
    level: int = 1
    streak: int = 0
    progression_mode: str = "moderate"
    goal_ratio: float = 1.5
    estimated_weeks_to_goal: Dict[str, int] = {"min": 0, "max": 0}
    last_workout_date: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    block_start_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    boss_fight_count: int = 0
    achievements: List[str] = []
    pending_adjustments: Dict[str, float] = {"squat": 0.0, "bench": 0.0, "deadlift": 0.0}

class ExerciseLogRow(BaseModel):
    name: str
    target_sets: int
    target_reps: int
    target_weight: float
    target_rpe: Optional[float] = None
    logged_weight: Optional[float] = None
    logged_reps: Optional[int] = None
    logged_rpe: Optional[float] = None
    is_main: bool = False
    done: bool = False

class WorkoutLogInput(BaseModel):
    workout_id: str
    exercises: List[ExerciseLogRow]
    notes: Optional[str] = None

class BossFightInput(BaseModel):
    squat_max: float
    bench_max: float
    deadlift_max: float

class AICoachInput(BaseModel):
    question: Optional[str] = None

# ---------------- Helpers ----------------
RANKS = [
    ("E", 0, 499),
    ("D", 500, 599),
    ("C", 600, 699),
    ("B", 700, 799),
    ("A", 800, 899),
    ("S", 900, 99999),
]

def compute_rank(total: float) -> str:
    for r, lo, hi in RANKS:
        if lo <= total <= hi:
            return r
    return "E"

def next_rank_info(total: float) -> Dict[str, Any]:
    for r, lo, hi in RANKS:
        if total < lo:
            return {"rank": r, "kg_to_reach": lo - total, "threshold": lo}
    return {"rank": "S", "kg_to_reach": 0, "threshold": 900}

def xp_for_level(level: int) -> int:
    return 500 + (level - 1) * 250  # increasing curve

def apply_xp(profile: dict, amount: int) -> dict:
    profile["xp"] = profile.get("xp", 0) + amount
    while profile["xp"] >= xp_for_level(profile.get("level", 1)):
        profile["xp"] -= xp_for_level(profile["level"])
        profile["level"] = profile.get("level", 1) + 1
    return profile

# ---------- Workout Block Generation ----------
def round_to_2_5(w: float) -> float:
    return round(w / 2.5) * 2.5

def round_to_5(w: float) -> float:
    return round(w / 5) * 5

def progression_mode_from_ratio(goal_ratio: float) -> str:
    if goal_ratio < 1.25:
        return "conservative"
    if goal_ratio <= 1.75:
        return "moderate"
    return "aggressive"

def estimate_weeks_to_goal(current_total: float, goal_total: float, mode: str) -> Dict[str, int]:
    """RPE-driven progression is non-linear. Provide a realistic weekly-gain range
    for display purposes only — NOT used to compute daily training weights."""
    if current_total >= goal_total:
        return {"min": 0, "max": 0}
    gap = goal_total - current_total
    rng = {"conservative": (1.0, 2.5), "moderate": (2.5, 5.0), "aggressive": (5.0, 7.5)}[mode]
    # min weeks = gap / max gain, max weeks = gap / min gain
    return {"min": int(gap / rng[1]), "max": int(gap / rng[0])}

# Per-day intensity modifier inside a week (Low/Base/High). NOT goal-based.
DAY_INTENSITY = {
    "SQUAT_DAY": 0.0,        # BASE
    "BENCH_DAY": 0.025,      # HIGH
    "DEADLIFT_DAY": 0.0,     # BASE
    "UPPER_ACC": -0.025,     # LOW
    "LOWER_ACC": -0.025,     # LOW
    "CONDITIONING": -0.025,  # LOW
}
DAY_TAG = {
    "SQUAT_DAY": "BASE", "BENCH_DAY": "HIGH", "DEADLIFT_DAY": "BASE",
    "UPPER_ACC": "LOW", "LOWER_ACC": "LOW", "CONDITIONING": "LOW",
}

def generate_block(squat: float, bench: float, deadlift: float, training_days: int, goal_ratio: float = 1.5, adjustments: Optional[Dict[str, float]] = None) -> List[dict]:
    """Generate a 6-week powerlifting block.
    Weeks 1-4: Build (volume), Week 5: Heavy (intensification), Week 6: Deload.
    Daily weights = current_1RM * week_pct * (1 + day_intensity_modifier).
    Optional `adjustments` dict applies RPE-driven kg adjustments per main lift (squat/bench/deadlift)."""
    adj = adjustments or {"squat": 0.0, "bench": 0.0, "deadlift": 0.0}
    # Base week templates — NO goal-based shift on daily weights
    week_specs = {
        1: ("BUILD", 0.70, 4, 6),
        2: ("BUILD", 0.725, 4, 6),
        3: ("BUILD", 0.75, 5, 5),
        4: ("BUILD", 0.775, 5, 5),
        5: ("HEAVY", 0.875, 4, 3),
        6: ("DELOAD", 0.55, 3, 5),
    }

    # Day templates by training_days/week
    days_map = {
        3: ["SQUAT_DAY", "BENCH_DAY", "DEADLIFT_DAY"],
        4: ["SQUAT_DAY", "BENCH_DAY", "DEADLIFT_DAY", "UPPER_ACC"],
        5: ["SQUAT_DAY", "BENCH_DAY", "DEADLIFT_DAY", "UPPER_ACC", "LOWER_ACC"],
        6: ["SQUAT_DAY", "BENCH_DAY", "DEADLIFT_DAY", "UPPER_ACC", "LOWER_ACC", "CONDITIONING"],
    }
    days = days_map.get(training_days, days_map[4])

    workouts = []
    for week in range(1, 7):
        label, pct, sets, reps = week_specs[week]
        target_rpe = {1: 6.5, 2: 7, 3: 7.5, 4: 8, 5: 9, 6: 6}[week]
        for day_idx, day_type in enumerate(days):
            day_mod = DAY_INTENSITY.get(day_type, 0.0)
            day_pct = pct + day_mod  # apply Low/Base/High intensity modifier
            day_tag = DAY_TAG.get(day_type, "BASE")
            sq_w = round_to_2_5(squat * day_pct + adj.get("squat", 0.0))
            bn_w = round_to_2_5(bench * day_pct + adj.get("bench", 0.0))
            dl_w = round_to_2_5(deadlift * day_pct + adj.get("deadlift", 0.0))
            exercises = []
            if day_type == "SQUAT_DAY":
                exercises = [
                    {"name": "Back Squat", "sets": sets, "reps": reps, "weight": sq_w, "target_rpe": target_rpe, "is_main": True},
                    {"name": "Romanian Deadlift", "sets": 3, "reps": 8, "weight": round_to_2_5(deadlift * 0.55), "target_rpe": 7, "is_main": False},
                    {"name": "Walking Lunges", "sets": 3, "reps": 10, "weight": round_to_2_5(squat * 0.25), "target_rpe": 7, "is_main": False},
                ]
            elif day_type == "BENCH_DAY":
                exercises = [
                    {"name": "Bench Press", "sets": sets, "reps": reps, "weight": bn_w, "target_rpe": target_rpe, "is_main": True},
                    {"name": "Overhead Press", "sets": 3, "reps": 8, "weight": round_to_2_5(bench * 0.6), "target_rpe": 7, "is_main": False},
                    {"name": "Barbell Row", "sets": 4, "reps": 8, "weight": round_to_2_5(bench * 0.8), "target_rpe": 7, "is_main": False},
                ]
            elif day_type == "DEADLIFT_DAY":
                exercises = [
                    {"name": "Deadlift", "sets": sets, "reps": reps, "weight": dl_w, "target_rpe": target_rpe, "is_main": True},
                    {"name": "Front Squat", "sets": 3, "reps": 6, "weight": round_to_2_5(squat * 0.6), "target_rpe": 7, "is_main": False},
                    {"name": "Pull-ups", "sets": 4, "reps": 8, "weight": 0, "target_rpe": 8, "is_main": False},
                ]
            elif day_type == "UPPER_ACC":
                exercises = [
                    {"name": "Close-Grip Bench", "sets": 4, "reps": 6, "weight": round_to_2_5(bench * 0.75), "target_rpe": 7, "is_main": False},
                    {"name": "Incline DB Press", "sets": 3, "reps": 10, "weight": round_to_2_5(bench * 0.3), "target_rpe": 7, "is_main": False},
                    {"name": "Lat Pulldown", "sets": 4, "reps": 12, "weight": round_to_5(bench * 0.5), "target_rpe": 7, "is_main": False},
                ]
            elif day_type == "LOWER_ACC":
                exercises = [
                    {"name": "Pause Squat", "sets": 4, "reps": 5, "weight": round_to_2_5(squat * 0.7), "target_rpe": 7, "is_main": False},
                    {"name": "Leg Press", "sets": 3, "reps": 12, "weight": round_to_5(squat * 1.0), "target_rpe": 7, "is_main": False},
                    {"name": "Hamstring Curl", "sets": 3, "reps": 12, "weight": 0, "target_rpe": 7, "is_main": False},
                ]
            elif day_type == "CONDITIONING":
                exercises = [
                    {"name": "Sled Push", "sets": 5, "reps": 1, "weight": round_to_2_5(bodyweight_safe(squat)), "target_rpe": 8, "is_main": False},
                    {"name": "Farmer Walk", "sets": 4, "reps": 1, "weight": round_to_2_5(deadlift * 0.4), "target_rpe": 8, "is_main": False},
                ]

            workouts.append({
                "id": str(uuid.uuid4()),
                "week": week,
                "week_label": label,
                "day_index": day_idx,
                "day_type": day_type,
                "day_tag": day_tag,  # LOW / BASE / HIGH intensity day
                "exercises": exercises,
                "completed": False,
                "completed_at": None,
                "logs": [],
                "notes": None,
            })
    return workouts

def bodyweight_safe(x):
    return max(40, x * 0.5)

# ---------------- Achievements ----------------
ACHIEVEMENTS = {
    "first_workout": {"name": "First Awakening", "desc": "Complete your first quest"},
    "five_workouts": {"name": "Apprentice Hunter", "desc": "Complete 5 quests"},
    "perfect_week": {"name": "Perfect Week", "desc": "Complete all workouts in a week"},
    "squat_200": {"name": "200kg Squat", "desc": "Squat 200kg or more"},
    "bench_140": {"name": "140kg Bench", "desc": "Bench 140kg or more"},
    "deadlift_240": {"name": "240kg Deadlift", "desc": "Deadlift 240kg or more"},
    "rank_d": {"name": "Reached D Rank", "desc": "Achieve D Rank"},
    "rank_c": {"name": "Reached C Rank", "desc": "Achieve C Rank"},
    "rank_b": {"name": "Reached B Rank", "desc": "Achieve B Rank"},
    "rank_a": {"name": "Reached A Rank", "desc": "Achieve A Rank"},
    "rank_s": {"name": "S Rank Hunter", "desc": "Achieve S Rank — Monarch"},
    "boss_slayer": {"name": "Boss Slayer", "desc": "Complete a Boss Fight"},
}

def check_achievements(profile: dict, completed_workouts: int) -> List[str]:
    new = []
    a = set(profile.get("achievements", []))
    def add(key):
        if key not in a:
            a.add(key)
            new.append(key)
    if completed_workouts >= 1: add("first_workout")
    if completed_workouts >= 5: add("five_workouts")
    if profile["squat_max"] >= 200: add("squat_200")
    if profile["bench_max"] >= 140: add("bench_140")
    if profile["deadlift_max"] >= 240: add("deadlift_240")
    rank = profile["rank"]
    for r in ["D","C","B","A","S"]:
        if rank == r:
            add(f"rank_{r.lower()}")
    if profile.get("boss_fight_count", 0) >= 1: add("boss_slayer")
    profile["achievements"] = list(a)
    return new

# ---------------- Routes ----------------
@api_router.get("/")
async def root():
    return {"message": "Hunter Strength System API"}

@api_router.post("/profile")
async def create_profile(data: OnboardingInput):
    total = data.squat_max + data.bench_max + data.deadlift_max
    rank = compute_rank(total)
    goal_ratio = data.goal_total / max(total, 1)
    mode = progression_mode_from_ratio(goal_ratio)
    eta = estimate_weeks_to_goal(total, data.goal_total, mode)
    profile = Profile(
        name=data.name,
        bodyweight=data.bodyweight,
        experience=data.experience,
        squat_max=data.squat_max,
        bench_max=data.bench_max,
        deadlift_max=data.deadlift_max,
        training_days=data.training_days,
        goal_total=data.goal_total,
        total=total,
        rank=rank,
        progression_mode=mode,
        goal_ratio=round(goal_ratio, 3),
        estimated_weeks_to_goal=eta,
    )
    pdoc = profile.model_dump()
    # generate first block (scaled by goal ratio)
    workouts = generate_block(data.squat_max, data.bench_max, data.deadlift_max, data.training_days, goal_ratio)
    pdoc["workouts"] = workouts
    check_achievements(pdoc, 0)
    await db.profiles.insert_one(pdoc)
    pdoc.pop("_id", None)
    return pdoc

@api_router.get("/profile/{profile_id}")
async def get_profile(profile_id: str):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")
    return p

@api_router.get("/profile/{profile_id}/dashboard")
async def dashboard(profile_id: str):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")
    workouts = p.get("workouts", [])
    completed = [w for w in workouts if w.get("completed")]
    # find next workout
    next_workout = next((w for w in workouts if not w.get("completed")), None)
    nr = next_rank_info(p["total"])
    return {
        "profile": {k: v for k, v in p.items() if k != "workouts"},
        "today_quest": next_workout,
        "next_rank": nr,
        "completed_count": len(completed),
        "total_workouts": len(workouts),
        "xp_to_next_level": xp_for_level(p.get("level", 1)),
    }

@api_router.get("/profile/{profile_id}/workouts")
async def list_workouts(profile_id: str):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0, "workouts": 1})
    if not p:
        raise HTTPException(404, "Profile not found")
    return p.get("workouts", [])

@api_router.get("/profile/{profile_id}/workout/{workout_id}")
async def get_workout(profile_id: str, workout_id: str):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")
    w = next((w for w in p.get("workouts", []) if w["id"] == workout_id), None)
    if not w:
        raise HTTPException(404, "Workout not found")
    return w

@api_router.post("/profile/{profile_id}/workout/log")
async def log_workout(profile_id: str, data: WorkoutLogInput):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")
    workouts = p.get("workouts", [])
    target_w = None
    for w in workouts:
        if w["id"] == data.workout_id:
            target_w = w
            break
    if not target_w:
        raise HTTPException(404, "Workout not found")
    if target_w.get("completed"):
        raise HTTPException(400, "Workout already completed")

    # ---- New XP rules (per-exercise model) ----
    # +20 per exercise done, +50 main lift done, +100 all done bonus, +50 all RPE logged
    xp_gained = 0
    total_ex = len(data.exercises)
    done_ex = [ex for ex in data.exercises if ex.done]
    xp_gained += 20 * len(done_ex)
    for ex in done_ex:
        if ex.is_main:
            xp_gained += 50
    if total_ex > 0 and len(done_ex) == total_ex:
        xp_gained += 100  # all done bonus
    if all((ex.logged_rpe is not None) for ex in done_ex) and done_ex:
        xp_gained += 50  # all RPE logged

    # Mark workout complete only if every required exercise is done
    workout_complete = (total_ex > 0 and len(done_ex) == total_ex)

    target_w["logs"] = [ex.model_dump() for ex in data.exercises]
    target_w["notes"] = data.notes
    target_w["completed"] = workout_complete
    if workout_complete:
        target_w["completed_at"] = datetime.now(timezone.utc).isoformat()
    target_w["xp_gained"] = xp_gained

    # Streak only advances on a completed quest
    if workout_complete:
        today = datetime.now(timezone.utc).date().isoformat()
        last = p.get("last_workout_date")
        if last:
            last_date = datetime.fromisoformat(last).date()
            diff = (datetime.now(timezone.utc).date() - last_date).days
            if diff == 0:
                pass
            elif diff == 1:
                p["streak"] = p.get("streak", 0) + 1
            else:
                p["streak"] = 1
        else:
            p["streak"] = 1
        p["last_workout_date"] = today

    # Weekly bonus (added BEFORE apply_xp so it persists correctly)
    if workout_complete:
        week_no = target_w["week"]
        week_workouts = [w for w in workouts if w["week"] == week_no]
        if all(w.get("completed") for w in week_workouts):
            xp_gained += 300
            if week_no == 6:
                xp_gained += 200  # deload

    apply_xp(p, xp_gained)

    # ---- RPE-driven progression for the main lift ----
    main_logs = [ex for ex in data.exercises if ex.is_main and ex.done]
    suggestion_text = ""
    rpe_adjustment = 0.0
    main_lift_key = None
    if main_logs:
        main = main_logs[0]
        if "Squat" in main.name:
            main_lift_key = "squat"
        elif "Bench" in main.name and "Press" in main.name:
            main_lift_key = "bench"
        elif "Deadlift" in main.name and "Romanian" not in main.name:
            main_lift_key = "deadlift"
        if main_lift_key and main.logged_rpe is not None and main.target_rpe is not None:
            if main.logged_rpe < main.target_rpe:
                rpe_adjustment = 2.5
                suggestion_text = f"[SYSTEM]: Power surge detected. +2.5kg to {main.name} next session."
            elif main.logged_rpe > main.target_rpe:
                rpe_adjustment = -2.5
                suggestion_text = f"[SYSTEM]: Mana strain. -2.5kg to {main.name} next session. Recover."
            else:
                rpe_adjustment = 0.0
                suggestion_text = f"[SYSTEM]: Optimal load on {main.name}. Hold for next session."
            # Apply adjustment to remaining upcoming workouts of the same main-lift type
            day_type_of_lift = {"squat": "SQUAT_DAY", "bench": "BENCH_DAY", "deadlift": "DEADLIFT_DAY"}[main_lift_key]
            for fw in workouts:
                if fw.get("completed") or fw.get("day_type") != day_type_of_lift:
                    continue
                for fex in fw.get("exercises", []):
                    if fex.get("is_main"):
                        fex["weight"] = round_to_2_5(fex["weight"] + rpe_adjustment)
            # Persist adjustment trail on profile
            pa = p.get("pending_adjustments", {"squat": 0.0, "bench": 0.0, "deadlift": 0.0})
            pa[main_lift_key] = pa.get(main_lift_key, 0.0) + rpe_adjustment
            p["pending_adjustments"] = pa
    if not suggestion_text:
        suggestion_text = build_progression_suggestion(target_w)

    completed_count = sum(1 for w in workouts if w.get("completed"))
    new_ach = check_achievements(p, completed_count)

    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {
            "workouts": workouts,
            "xp": p["xp"],
            "level": p["level"],
            "streak": p["streak"],
            "last_workout_date": p["last_workout_date"],
            "achievements": p["achievements"],
            "pending_adjustments": p.get("pending_adjustments", {"squat": 0.0, "bench": 0.0, "deadlift": 0.0}),
        }}
    )

    return {
        "xp_gained": xp_gained,
        "total_xp": p["xp"],
        "level": p["level"],
        "streak": p["streak"],
        "workout_complete": workout_complete,
        "exercises_done": len(done_ex),
        "exercises_total": total_ex,
        "main_lift_adjustment_kg": rpe_adjustment,
        "main_lift_key": main_lift_key,
        "new_achievements": [{"key": k, **ACHIEVEMENTS[k]} for k in new_ach],
        "suggestion": suggestion_text,
    }

def build_progression_suggestion(workout: dict) -> str:
    logs = workout.get("logs", [])
    if not logs:
        return "Keep showing up. The System rewards consistency."
    main = next((e for e in logs if e.get("is_main") and e.get("done")), logs[0])
    name = main.get("name", "main lift")
    rpe = main.get("logged_rpe")
    target = main.get("target_rpe") or 8
    if rpe is None:
        return f"[SYSTEM]: Quest complete. Log RPE next time for sharper guidance."
    if rpe < target:
        return f"[SYSTEM]: Power surge detected. +2.5kg to {name} next session."
    elif rpe > target:
        return f"[SYSTEM]: Mana strain. -2.5kg to {name} next session. Recover."
    return f"[SYSTEM]: Optimal load on {name}. Hold for next session."

@api_router.post("/profile/{profile_id}/boss-fight")
async def boss_fight(profile_id: str, data: BossFightInput):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")
    old_rank = p["rank"]
    old_total = p["total"]
    new_total = data.squat_max + data.bench_max + data.deadlift_max
    new_rank = compute_rank(new_total)
    p["squat_max"] = data.squat_max
    p["bench_max"] = data.bench_max
    p["deadlift_max"] = data.deadlift_max
    p["total"] = new_total
    p["rank"] = new_rank
    p["boss_fight_count"] = p.get("boss_fight_count", 0) + 1

    xp_reward = 1000
    apply_xp(p, xp_reward)

    # Recompute goal ratio + progression mode based on new total
    goal_ratio = p["goal_total"] / max(new_total, 1)
    new_mode = progression_mode_from_ratio(goal_ratio)
    eta = estimate_weeks_to_goal(new_total, p["goal_total"], new_mode)
    p["progression_mode"] = new_mode
    p["goal_ratio"] = round(goal_ratio, 3)
    p["estimated_weeks_to_goal"] = eta
    # Reset RPE-driven adjustments since maxes are now fresh
    p["pending_adjustments"] = {"squat": 0.0, "bench": 0.0, "deadlift": 0.0}
    # Regenerate block with new maxes (no carry-over adjustments)
    new_workouts = generate_block(data.squat_max, data.bench_max, data.deadlift_max, p["training_days"], goal_ratio)
    p["block_start_date"] = datetime.now(timezone.utc).isoformat()
    completed_count = sum(1 for w in p.get("workouts", []) if w.get("completed"))
    new_ach = check_achievements(p, completed_count)

    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {
            "squat_max": p["squat_max"],
            "bench_max": p["bench_max"],
            "deadlift_max": p["deadlift_max"],
            "total": p["total"],
            "rank": p["rank"],
            "boss_fight_count": p["boss_fight_count"],
            "xp": p["xp"],
            "level": p["level"],
            "achievements": p["achievements"],
            "workouts": new_workouts,
            "block_start_date": p["block_start_date"],
            "progression_mode": p["progression_mode"],
            "goal_ratio": p["goal_ratio"],
            "estimated_weeks_to_goal": p["estimated_weeks_to_goal"],
            "pending_adjustments": p["pending_adjustments"],
        }}
    )
    return {
        "old_rank": old_rank,
        "new_rank": new_rank,
        "old_total": old_total,
        "new_total": new_total,
        "rank_up": new_rank != old_rank,
        "xp_reward": xp_reward,
        "new_achievements": [{"key": k, **ACHIEVEMENTS[k]} for k in new_ach],
    }

@api_router.get("/profile/{profile_id}/achievements")
async def get_achievements(profile_id: str):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0, "achievements": 1})
    if not p:
        raise HTTPException(404, "Profile not found")
    unlocked = set(p.get("achievements", []))
    return [
        {"key": k, "name": v["name"], "desc": v["desc"], "unlocked": k in unlocked}
        for k, v in ACHIEVEMENTS.items()
    ]

@api_router.get("/profile/{profile_id}/progress")
async def get_progress(profile_id: str):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")
    workouts = p.get("workouts", [])
    completed = [w for w in workouts if w.get("completed")]
    history = []
    for w in completed:
        for ex_log in w.get("logs", []):
            if not ex_log.get("done"):
                continue
            name = ex_log.get("name", "")
            if any(k in name for k in ["Back Squat", "Bench Press", "Deadlift"]) and "Romanian" not in name:
                if ex_log.get("logged_weight") is not None and ex_log.get("logged_reps") is not None:
                    history.append({
                        "date": w.get("completed_at"),
                        "exercise": name,
                        "weight": ex_log["logged_weight"],
                        "reps": ex_log["logged_reps"],
                    })
    return {
        "current": {
            "squat": p["squat_max"],
            "bench": p["bench_max"],
            "deadlift": p["deadlift_max"],
            "total": p["total"],
        },
        "goal_total": p["goal_total"],
        "rank": p["rank"],
        "progression_mode": p.get("progression_mode", "moderate"),
        "goal_ratio": p.get("goal_ratio", 1.5),
        "estimated_weeks_to_goal": p.get("estimated_weeks_to_goal", {"min": 0, "max": 0}),
        "pending_adjustments": p.get("pending_adjustments", {"squat": 0.0, "bench": 0.0, "deadlift": 0.0}),
        "next_rank": next_rank_info(p["total"]),
        "history": history,
        "completed_count": len(completed),
        "total_count": len(workouts),
    }

@api_router.post("/profile/{profile_id}/ai-coach")
async def ai_coach(profile_id: str, data: AICoachInput):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")

    workouts = p.get("workouts", [])
    completed = [w for w in workouts if w.get("completed")][-5:]
    next_q = next((w for w in workouts if not w.get("completed")), None)

    context = f"""Hunter Profile:
Name: {p['name']}
Rank: {p['rank']} | Total: {p['total']}kg | Goal: {p['goal_total']}kg
Squat: {p['squat_max']}kg | Bench: {p['bench_max']}kg | Deadlift: {p['deadlift_max']}kg
Experience: {p['experience']} | Training days/week: {p['training_days']}
Level: {p.get('level',1)} | Streak: {p.get('streak',0)} sessions
"""
    if completed:
        context += "\nRecent completed quests:\n"
        for w in completed[-3:]:
            context += f"- Week {w['week']} ({w['week_label']}) {w['day_type']} [{w.get('day_tag','')}]\n"
            for ex in w.get("logs", []):
                if ex.get("done"):
                    context += (
                        f"  \u2022 {ex['name']}: target {ex.get('target_weight')}kg x{ex.get('target_reps')} "
                        f"(RPE {ex.get('target_rpe','-')}); logged "
                        f"{ex.get('logged_weight','-')}kg x {ex.get('logged_reps','-')} "
                        f"(RPE {ex.get('logged_rpe','-')})\n"
                    )
    if next_q:
        context += f"\nNext quest: Week {next_q['week']} ({next_q['week_label']}) — {next_q['day_type']}\n"
        for ex in next_q.get("exercises", []):
            context += f"  • {ex['name']}: {ex['sets']}x{ex['reps']} @ {ex['weight']}kg (RPE {ex.get('target_rpe')})\n"

    question = data.question or "Analyze my last session and give me 3 concise tactical recommendations for the next quest. Speak as the System Hunter Coach — in-character, terse, like a Solo Leveling system message. Keep total under 180 words."

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ['EMERGENT_LLM_KEY']
        chat = LlmChat(
            api_key=api_key,
            session_id=f"hunter-{profile_id}",
            system_message=(
                "You are 'The System' — an AI coach inspired by Solo Leveling. "
                "You speak in terse, dramatic, in-character system messages to a powerlifter (the Hunter). "
                "Be tactical and specific about weights, RPE, recovery. Use phrases like [SYSTEM], [ALERT], [QUEST UPDATE]. "
                "Stay concise. Always end with a single empowering line."
            ),
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        msg = UserMessage(text=context + "\n\nHunter's question: " + question)
        response = await chat.send_message(msg)
        return {"response": response}
    except Exception as e:
        logging.exception("AI coach error")
        return {"response": f"[SYSTEM OFFLINE] Connection to the System severed. Retry shortly. ({type(e).__name__})"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
