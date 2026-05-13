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
    # Aggregate stats for achievements
    total_run_km: float = 0.0
    total_bike_km: float = 0.0
    longest_run_km: float = 0.0
    longest_bike_km: float = 0.0
    best_run_pace_sec_per_km: Optional[float] = None
    best_sprint_100m: Optional[float] = None
    best_sprint_200m: Optional[float] = None
    best_sprint_400m: Optional[float] = None
    perfect_workouts: int = 0
    perfect_weeks: int = 0
    weeks_completed: List[int] = []
    longest_streak: int = 0
    max_session_volume_kg: float = 0.0
    max_weekly_volume_kg: float = 0.0
    weekly_volume_log: Dict[str, float] = {}  # iso-week → kg
    cardio_dates: List[str] = []  # ISO dates of cardio sessions
    workout_dates: List[str] = []  # ISO dates of completed workouts
    hybrid_run_sessions: int = 0
    hybrid_bike_sessions: int = 0
    night_sessions: int = 0
    early_sessions: int = 0
    comeback_count: int = 0
    no_days_off_max: int = 0  # consecutive days trained (lift OR cardio)

class CardioInput(BaseModel):
    activity: str  # "run" | "bike" | "sprint"
    distance_km: Optional[float] = None  # for run/bike
    duration_sec: Optional[float] = None
    sprint_distance_m: Optional[int] = None  # 100/200/400
    sprint_time_sec: Optional[float] = None
    notes: Optional[str] = None

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

# ---------------- Achievements V2 (60+) ----------------
# tier: basic=50, medium=100, major=250, elite=500 XP
def _ach(name, desc, category, tier="basic"):
    return {"name": name, "desc": desc, "category": category, "tier": tier}

ACHIEVEMENTS = {
    # Strength: Squat
    "squat_100": _ach("100kg Squat", "Squat 100kg or more", "Squat", "basic"),
    "squat_140": _ach("140kg Squat", "Squat 140kg or more", "Squat", "basic"),
    "squat_180": _ach("180kg Squat", "Squat 180kg or more", "Squat", "medium"),
    "squat_200": _ach("200kg Squat", "Squat 200kg or more", "Squat", "medium"),
    "squat_220": _ach("220kg Squat", "Squat 220kg or more", "Squat", "major"),
    "squat_250": _ach("250kg Squat", "Squat 250kg or more", "Squat", "elite"),
    # Strength: Bench
    "bench_100": _ach("100kg Bench", "Bench 100kg or more", "Bench", "basic"),
    "bench_140": _ach("140kg Bench", "Bench 140kg or more", "Bench", "basic"),
    "bench_160": _ach("160kg Bench", "Bench 160kg or more", "Bench", "medium"),
    "bench_180": _ach("180kg Bench", "Bench 180kg or more", "Bench", "medium"),
    "bench_200": _ach("200kg Bench", "Bench 200kg or more", "Bench", "major"),
    "bench_220": _ach("220kg Bench", "Bench 220kg or more", "Bench", "elite"),
    # Strength: Deadlift
    "deadlift_140": _ach("140kg Deadlift", "Deadlift 140kg or more", "Deadlift", "basic"),
    "deadlift_180": _ach("180kg Deadlift", "Deadlift 180kg or more", "Deadlift", "basic"),
    "deadlift_220": _ach("220kg Deadlift", "Deadlift 220kg or more", "Deadlift", "medium"),
    "deadlift_240": _ach("240kg Deadlift", "Deadlift 240kg or more", "Deadlift", "medium"),
    "deadlift_260": _ach("260kg Deadlift", "Deadlift 260kg or more", "Deadlift", "major"),
    "deadlift_300": _ach("300kg Deadlift", "Deadlift 300kg or more", "Deadlift", "elite"),
    # Total
    "total_500": _ach("500kg Total", "Reach a 500kg powerlifting total", "Total", "basic"),
    "total_600": _ach("600kg Total", "Reach a 600kg powerlifting total", "Total", "medium"),
    "total_700": _ach("700kg Total", "Reach a 700kg powerlifting total", "Total", "medium"),
    "total_800": _ach("800kg Total", "Reach an 800kg powerlifting total", "Total", "major"),
    "total_900": _ach("900kg Total", "Reach a 900kg powerlifting total", "Total", "major"),
    "total_1000": _ach("1000kg Total — Final Boss", "Conquer the 1000kg total", "Total", "elite"),
    # Quest count
    "quests_5": _ach("Apprentice Hunter", "Complete 5 quests", "Quests", "basic"),
    "quests_10": _ach("Seasoned Hunter", "Complete 10 quests", "Quests", "basic"),
    "quests_25": _ach("Veteran Hunter", "Complete 25 quests", "Quests", "medium"),
    "quests_50": _ach("Elite Hunter", "Complete 50 quests", "Quests", "major"),
    "quests_100": _ach("Master Hunter", "Complete 100 quests", "Quests", "elite"),
    # Weekly consistency
    "perfect_week_1": _ach("Perfect Week", "Complete all workouts in one week", "Weekly", "basic"),
    "perfect_week_2": _ach("Two Perfect Weeks", "Two perfect training weeks", "Weekly", "medium"),
    "perfect_week_4": _ach("Four Perfect Weeks", "Four perfect training weeks", "Weekly", "major"),
    "perfect_week_8": _ach("Eight Perfect Weeks", "Eight perfect training weeks", "Weekly", "elite"),
    # Streak
    "streak_3": _ach("3 Day Streak", "Train 3 days in a row", "Streak", "basic"),
    "streak_7": _ach("7 Day Streak", "Train 7 days in a row", "Streak", "medium"),
    "streak_14": _ach("14 Day Streak", "Train 14 days in a row", "Streak", "major"),
    "streak_30": _ach("30 Day Streak", "Train 30 days in a row", "Streak", "elite"),
    # Running distance (single session)
    "run_1k": _ach("First Mile-ish", "Run 1km in a single session", "Run", "basic"),
    "run_3k": _ach("3km Run", "Run 3km in a single session", "Run", "basic"),
    "run_5k": _ach("5km Run", "Run 5km in a single session", "Run", "medium"),
    "run_10k": _ach("10km Run", "Run 10km in a single session", "Run", "major"),
    # Running total
    "run_total_10": _ach("10km Runner", "Run 10km accumulated", "Run", "basic"),
    "run_total_25": _ach("25km Runner", "Run 25km accumulated", "Run", "basic"),
    "run_total_50": _ach("50km Runner", "Run 50km accumulated", "Run", "medium"),
    "run_total_100": _ach("100km Runner", "Run 100km accumulated", "Run", "major"),
    "run_total_250": _ach("250km Runner", "Run 250km accumulated", "Run", "elite"),
    # Pace
    "pace_sub_6": _ach("Sub 6:00/km", "Run a session at sub-6:00 per km", "Pace", "basic"),
    "pace_sub_5_30": _ach("Sub 5:30/km", "Run a session at sub-5:30 per km", "Pace", "medium"),
    "pace_sub_5": _ach("Sub 5:00/km", "Run a session at sub-5:00 per km", "Pace", "major"),
    "pace_sub_4_30": _ach("Sub 4:30/km", "Run a session at sub-4:30 per km", "Pace", "elite"),
    # Sprints
    "sprint_100_20": _ach("100m under 20s", "Sprint 100m under 20 seconds", "Sprint", "basic"),
    "sprint_200_40": _ach("200m under 40s", "Sprint 200m under 40 seconds", "Sprint", "medium"),
    "sprint_400_90": _ach("400m under 90s", "Sprint 400m under 90 seconds", "Sprint", "major"),
    # Bike single ride
    "bike_5": _ach("5km Ride", "Cycle 5km in a single ride", "Bike", "basic"),
    "bike_10": _ach("10km Ride", "Cycle 10km in a single ride", "Bike", "basic"),
    "bike_20": _ach("20km Ride", "Cycle 20km in a single ride", "Bike", "medium"),
    "bike_50": _ach("50km Ride", "Cycle 50km in a single ride", "Bike", "major"),
    # Bike total
    "bike_total_50": _ach("50km Cyclist", "Cycle 50km accumulated", "Bike", "basic"),
    "bike_total_100": _ach("100km Cyclist", "Cycle 100km accumulated", "Bike", "medium"),
    "bike_total_250": _ach("250km Cyclist", "Cycle 250km accumulated", "Bike", "major"),
    "bike_total_500": _ach("500km Cyclist", "Cycle 500km accumulated", "Bike", "elite"),
    # Workout quality
    "rpe_first": _ach("Calibrated", "Log RPE for every exercise in a session", "Quality", "basic"),
    "perfect_workout_1": _ach("Perfect Workout", "Hit every prescribed set/rep target", "Quality", "basic"),
    "perfect_workout_5": _ach("Five Perfect Workouts", "Five flawless quests", "Quality", "medium"),
    "perfect_workout_10": _ach("Ten Perfect Workouts", "Ten flawless quests", "Quality", "major"),
    # Elite bodyweight ratios
    "squat_specialist": _ach("Squat Specialist", "Squat 2x bodyweight", "Elite", "major"),
    "bench_technician": _ach("Bench Technician", "Bench 1.5x bodyweight", "Elite", "major"),
    "deadlift_monster": _ach("Deadlift Monster", "Deadlift 2.5x bodyweight", "Elite", "elite"),
    # Hybrid
    "hybrid_run_5": _ach("Iron + Mile", "Lift + run same session 5 times", "Hybrid", "medium"),
    "hybrid_bike_5": _ach("Iron + Wheels", "Lift + bike same session 5 times", "Hybrid", "medium"),
    # Volume
    "volume_session_10k": _ach("10,000kg Session", "Lift 10,000kg total in one session", "Volume", "medium"),
    "volume_week_25k": _ach("25,000kg Week", "Lift 25,000kg total in one week", "Volume", "major"),
    # Rank progression
    "rank_e": _ach("Awakened — E Rank", "Reach E Rank", "Rank", "basic"),
    "rank_d": _ach("Reached D Rank", "Reach D Rank", "Rank", "basic"),
    "rank_c": _ach("Reached C Rank", "Reach C Rank", "Rank", "medium"),
    "rank_b": _ach("Reached B Rank", "Reach B Rank", "Rank", "medium"),
    "rank_a": _ach("Reached A Rank", "Reach A Rank", "Rank", "major"),
    "rank_s": _ach("S Rank — Monarch", "Reach S Rank", "Rank", "elite"),
    # Special / fun
    "no_days_off_7": _ach("No Days Off", "Train 7 consecutive days (lift or cardio)", "Special", "medium"),
    "comeback_arc": _ach("Comeback Arc", "Return after 5+ missed days", "Special", "basic"),
    "night_session": _ach("Night Hunter", "Train after 9pm", "Special", "basic"),
    "early_hunter": _ach("Early Hunter", "Train before 6am", "Special", "basic"),
    # Boss / first
    "first_workout": _ach("First Awakening", "Complete your first quest", "Quests", "basic"),
    "boss_slayer": _ach("Boss Slayer", "Complete a Boss Fight", "Boss", "major"),
}

TIER_XP = {"basic": 50, "medium": 100, "major": 250, "elite": 500}

def check_achievements(profile: dict, completed_workouts: int) -> List[str]:
    """Returns list of NEWLY unlocked achievement keys. Awards XP for each."""
    a = set(profile.get("achievements", []))
    new: List[str] = []

    def add(key):
        if key not in a:
            a.add(key)
            new.append(key)

    sq = profile.get("squat_max", 0)
    bn = profile.get("bench_max", 0)
    dl = profile.get("deadlift_max", 0)
    total = profile.get("total", 0)
    bw = profile.get("bodyweight", 1) or 1

    # Strength single-lift
    for thr in [100, 140, 180, 200, 220, 250]:
        if sq >= thr: add(f"squat_{thr}")
    for thr in [100, 140, 160, 180, 200, 220]:
        if bn >= thr: add(f"bench_{thr}")
    for thr in [140, 180, 220, 240, 260, 300]:
        if dl >= thr: add(f"deadlift_{thr}")

    # Total
    for thr in [500, 600, 700, 800, 900, 1000]:
        if total >= thr: add(f"total_{thr}")

    # Quest counts
    if completed_workouts >= 1: add("first_workout")
    for thr in [5, 10, 25, 50, 100]:
        if completed_workouts >= thr: add(f"quests_{thr}")

    # Perfect weeks
    pw = profile.get("perfect_weeks", 0)
    if pw >= 1: add("perfect_week_1")
    if pw >= 2: add("perfect_week_2")
    if pw >= 4: add("perfect_week_4")
    if pw >= 8: add("perfect_week_8")

    # Streak
    streak = max(profile.get("streak", 0), profile.get("longest_streak", 0))
    for thr in [3, 7, 14, 30]:
        if streak >= thr: add(f"streak_{thr}")

    # Running
    lr = profile.get("longest_run_km", 0)
    if lr >= 1: add("run_1k")
    if lr >= 3: add("run_3k")
    if lr >= 5: add("run_5k")
    if lr >= 10: add("run_10k")
    tr = profile.get("total_run_km", 0)
    if tr >= 10: add("run_total_10")
    if tr >= 25: add("run_total_25")
    if tr >= 50: add("run_total_50")
    if tr >= 100: add("run_total_100")
    if tr >= 250: add("run_total_250")

    # Pace (lower seconds-per-km = faster)
    pace = profile.get("best_run_pace_sec_per_km")
    if pace is not None:
        if pace < 360: add("pace_sub_6")
        if pace < 330: add("pace_sub_5_30")
        if pace < 300: add("pace_sub_5")
        if pace < 270: add("pace_sub_4_30")

    # Sprints
    if profile.get("best_sprint_100m") is not None and profile["best_sprint_100m"] < 20:
        add("sprint_100_20")
    if profile.get("best_sprint_200m") is not None and profile["best_sprint_200m"] < 40:
        add("sprint_200_40")
    if profile.get("best_sprint_400m") is not None and profile["best_sprint_400m"] < 90:
        add("sprint_400_90")

    # Bike
    lb = profile.get("longest_bike_km", 0)
    if lb >= 5: add("bike_5")
    if lb >= 10: add("bike_10")
    if lb >= 20: add("bike_20")
    if lb >= 50: add("bike_50")
    tb = profile.get("total_bike_km", 0)
    if tb >= 50: add("bike_total_50")
    if tb >= 100: add("bike_total_100")
    if tb >= 250: add("bike_total_250")
    if tb >= 500: add("bike_total_500")

    # Quality
    if profile.get("rpe_logged_once"): add("rpe_first")
    pwo = profile.get("perfect_workouts", 0)
    if pwo >= 1: add("perfect_workout_1")
    if pwo >= 5: add("perfect_workout_5")
    if pwo >= 10: add("perfect_workout_10")

    # Elite bodyweight ratios
    if sq >= bw * 2.0: add("squat_specialist")
    if bn >= bw * 1.5: add("bench_technician")
    if dl >= bw * 2.5: add("deadlift_monster")

    # Hybrid
    if profile.get("hybrid_run_sessions", 0) >= 5: add("hybrid_run_5")
    if profile.get("hybrid_bike_sessions", 0) >= 5: add("hybrid_bike_5")

    # Volume
    if profile.get("max_session_volume_kg", 0) >= 10000: add("volume_session_10k")
    if profile.get("max_weekly_volume_kg", 0) >= 25000: add("volume_week_25k")

    # Rank
    add(f"rank_{profile.get('rank','E').lower()}")
    # (don't add ranks below — only current)

    # Special
    if profile.get("no_days_off_max", 0) >= 7: add("no_days_off_7")
    if profile.get("comeback_count", 0) >= 1: add("comeback_arc")
    if profile.get("night_sessions", 0) >= 1: add("night_session")
    if profile.get("early_sessions", 0) >= 1: add("early_hunter")
    if profile.get("boss_fight_count", 0) >= 1: add("boss_slayer")

    profile["achievements"] = list(a)
    # Award XP for each new unlock
    xp_bonus = 0
    for k in new:
        tier = ACHIEVEMENTS.get(k, {}).get("tier", "basic")
        xp_bonus += TIER_XP.get(tier, 50)
    if xp_bonus > 0:
        apply_xp(profile, xp_bonus)
    profile["achievement_xp_last"] = xp_bonus
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
    all_rpe_logged = bool(done_ex) and all((ex.logged_rpe is not None) for ex in done_ex)
    if all_rpe_logged:
        xp_gained += 50  # all RPE logged

    # Mark workout complete only if every required exercise is done
    workout_complete = (total_ex > 0 and len(done_ex) == total_ex)

    # ---- Track aggregate stats for achievements ----
    # Session volume
    session_volume_kg = 0.0
    for ex in done_ex:
        if ex.logged_weight and ex.logged_reps and ex.target_sets:
            session_volume_kg += float(ex.logged_weight) * int(ex.logged_reps) * int(ex.target_sets)
    if session_volume_kg > p.get("max_session_volume_kg", 0):
        p["max_session_volume_kg"] = session_volume_kg

    # Perfect workout: every exercise done AND every logged_reps >= target_reps
    is_perfect = workout_complete and all(
        (ex.logged_reps is not None and ex.logged_reps >= ex.target_reps) for ex in done_ex
    )
    if is_perfect:
        p["perfect_workouts"] = p.get("perfect_workouts", 0) + 1

    # First-time RPE-all-logged
    if all_rpe_logged:
        p["rpe_logged_once"] = True

    # Time-of-day tracking
    now = datetime.now(timezone.utc)
    hr = now.hour
    if hr >= 21 or hr < 2:
        p["night_sessions"] = p.get("night_sessions", 0) + 1
    if 3 <= hr < 6:
        p["early_sessions"] = p.get("early_sessions", 0) + 1

    target_w["session_volume_kg"] = session_volume_kg
    target_w["logs"] = [ex.model_dump() for ex in data.exercises]
    target_w["notes"] = data.notes
    target_w["completed"] = workout_complete
    if workout_complete:
        target_w["completed_at"] = now.isoformat()
    target_w["xp_gained"] = xp_gained

    # Streak + comeback + workout dates + no_days_off
    if workout_complete:
        today = now.date().isoformat()
        last = p.get("last_workout_date")
        if last:
            try:
                last_date = datetime.fromisoformat(last).date()
            except Exception:
                last_date = now.date()
            diff = (now.date() - last_date).days
            if diff == 0:
                pass
            elif diff == 1:
                p["streak"] = p.get("streak", 0) + 1
            else:
                if diff >= 5:
                    p["comeback_count"] = p.get("comeback_count", 0) + 1
                p["streak"] = 1
        else:
            p["streak"] = 1
        p["last_workout_date"] = today
        p["longest_streak"] = max(p.get("longest_streak", 0), p.get("streak", 0))

        wd = set(p.get("workout_dates", []))
        wd.add(today)
        p["workout_dates"] = list(wd)

        # Hybrid same-session detection
        cardio_today = today in set(p.get("cardio_dates", []))
        if cardio_today:
            # find activity types today (best-effort: count any same-day cardio session of type)
            p["hybrid_run_sessions"] = p.get("hybrid_run_sessions", 0) + (1 if p.get("_last_cardio_activity") == "run" else 0)
            p["hybrid_bike_sessions"] = p.get("hybrid_bike_sessions", 0) + (1 if p.get("_last_cardio_activity") == "bike" else 0)

        # No-days-off: consecutive days with lift OR cardio
        all_dates = sorted(set(p.get("workout_dates", [])) | set(p.get("cardio_dates", [])))
        ndo = 1
        max_ndo = 1
        for i in range(1, len(all_dates)):
            d1 = datetime.fromisoformat(all_dates[i-1]).date()
            d2 = datetime.fromisoformat(all_dates[i]).date()
            if (d2 - d1).days == 1:
                ndo += 1
                max_ndo = max(max_ndo, ndo)
            else:
                ndo = 1
        p["no_days_off_max"] = max(p.get("no_days_off_max", 0), max_ndo)

    # Weekly bonus + perfect weeks + weekly volume bucket
    if workout_complete:
        week_no = target_w["week"]
        week_workouts = [w for w in workouts if w["week"] == week_no]
        if all(w.get("completed") for w in week_workouts):
            xp_gained += 300
            if week_no == 6:
                xp_gained += 200  # deload
            done_weeks = set(p.get("weeks_completed", []))
            # Use block_start_date + week to make a unique key
            week_key = f"{p.get('block_start_date','')[:10]}:W{week_no}"
            if week_key not in done_weeks:
                done_weeks.add(week_key)
                p["weeks_completed"] = list(done_weeks)
                p["perfect_weeks"] = p.get("perfect_weeks", 0) + 1
        # Weekly volume bucket (ISO year-week)
        iso_yr, iso_wk, _ = now.date().isocalendar()
        wk_key = f"{iso_yr}-W{iso_wk:02d}"
        wkv = dict(p.get("weekly_volume_log", {}))
        wkv[wk_key] = float(wkv.get(wk_key, 0.0)) + session_volume_kg
        p["weekly_volume_log"] = wkv
        if wkv[wk_key] > p.get("max_weekly_volume_kg", 0):
            p["max_weekly_volume_kg"] = wkv[wk_key]

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
            "longest_streak": p.get("longest_streak", p.get("streak", 0)),
            "last_workout_date": p["last_workout_date"],
            "achievements": p["achievements"],
            "pending_adjustments": p.get("pending_adjustments", {"squat": 0.0, "bench": 0.0, "deadlift": 0.0}),
            "perfect_workouts": p.get("perfect_workouts", 0),
            "perfect_weeks": p.get("perfect_weeks", 0),
            "weeks_completed": p.get("weeks_completed", []),
            "max_session_volume_kg": p.get("max_session_volume_kg", 0.0),
            "max_weekly_volume_kg": p.get("max_weekly_volume_kg", 0.0),
            "weekly_volume_log": p.get("weekly_volume_log", {}),
            "rpe_logged_once": p.get("rpe_logged_once", False),
            "night_sessions": p.get("night_sessions", 0),
            "early_sessions": p.get("early_sessions", 0),
            "comeback_count": p.get("comeback_count", 0),
            "workout_dates": p.get("workout_dates", []),
            "hybrid_run_sessions": p.get("hybrid_run_sessions", 0),
            "hybrid_bike_sessions": p.get("hybrid_bike_sessions", 0),
            "no_days_off_max": p.get("no_days_off_max", 0),
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
        {
            "key": k,
            "name": v["name"],
            "desc": v["desc"],
            "category": v.get("category", "Special"),
            "tier": v.get("tier", "basic"),
            "xp": TIER_XP.get(v.get("tier", "basic"), 50),
            "unlocked": k in unlocked,
        }
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

@api_router.post("/profile/{profile_id}/cardio")
async def log_cardio(profile_id: str, data: CardioInput):
    p = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Profile not found")
    activity = data.activity.lower()
    if activity not in ("run", "bike", "sprint"):
        raise HTTPException(400, "activity must be run, bike, or sprint")

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    hr = now.hour
    xp_gained = 50  # base cardio reward

    if activity == "run":
        if not data.distance_km or not data.duration_sec:
            raise HTTPException(400, "run requires distance_km and duration_sec")
        p["total_run_km"] = round(p.get("total_run_km", 0.0) + data.distance_km, 2)
        if data.distance_km > p.get("longest_run_km", 0):
            p["longest_run_km"] = data.distance_km
        pace = data.duration_sec / max(data.distance_km, 0.001)
        best = p.get("best_run_pace_sec_per_km")
        if best is None or pace < best:
            p["best_run_pace_sec_per_km"] = pace
        p["_last_cardio_activity"] = "run"
        xp_gained += int(min(150, data.distance_km * 15))
    elif activity == "bike":
        if not data.distance_km:
            raise HTTPException(400, "bike requires distance_km")
        p["total_bike_km"] = round(p.get("total_bike_km", 0.0) + data.distance_km, 2)
        if data.distance_km > p.get("longest_bike_km", 0):
            p["longest_bike_km"] = data.distance_km
        p["_last_cardio_activity"] = "bike"
        xp_gained += int(min(150, data.distance_km * 5))
    elif activity == "sprint":
        if not data.sprint_distance_m or not data.sprint_time_sec:
            raise HTTPException(400, "sprint requires sprint_distance_m and sprint_time_sec")
        key = f"best_sprint_{data.sprint_distance_m}m"
        prev = p.get(key)
        if prev is None or data.sprint_time_sec < prev:
            p[key] = data.sprint_time_sec
        p["_last_cardio_activity"] = "sprint"
        xp_gained += 75

    # Time-of-day tracking
    if hr >= 21 or hr < 2:
        p["night_sessions"] = p.get("night_sessions", 0) + 1
    if 3 <= hr < 6:
        p["early_sessions"] = p.get("early_sessions", 0) + 1

    # Cardio date + hybrid check
    cardio_dates = set(p.get("cardio_dates", []))
    cardio_dates.add(today)
    p["cardio_dates"] = list(cardio_dates)
    workout_dates = set(p.get("workout_dates", []))
    if today in workout_dates:
        if activity == "run":
            p["hybrid_run_sessions"] = p.get("hybrid_run_sessions", 0) + 1
        elif activity == "bike":
            p["hybrid_bike_sessions"] = p.get("hybrid_bike_sessions", 0) + 1

    # No-days-off recompute
    all_dates = sorted(workout_dates | cardio_dates)
    ndo = 1
    max_ndo = 1
    for i in range(1, len(all_dates)):
        d1 = datetime.fromisoformat(all_dates[i-1]).date()
        d2 = datetime.fromisoformat(all_dates[i]).date()
        if (d2 - d1).days == 1:
            ndo += 1
            max_ndo = max(max_ndo, ndo)
        else:
            ndo = 1
    p["no_days_off_max"] = max(p.get("no_days_off_max", 0), max_ndo)

    apply_xp(p, xp_gained)
    completed_count = sum(1 for w in p.get("workouts", []) if w.get("completed"))
    new_ach = check_achievements(p, completed_count)
    ach_xp = p.get("achievement_xp_last", 0)

    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {
            "xp": p["xp"],
            "level": p["level"],
            "total_run_km": p.get("total_run_km", 0.0),
            "longest_run_km": p.get("longest_run_km", 0.0),
            "best_run_pace_sec_per_km": p.get("best_run_pace_sec_per_km"),
            "total_bike_km": p.get("total_bike_km", 0.0),
            "longest_bike_km": p.get("longest_bike_km", 0.0),
            "best_sprint_100m": p.get("best_sprint_100m"),
            "best_sprint_200m": p.get("best_sprint_200m"),
            "best_sprint_400m": p.get("best_sprint_400m"),
            "cardio_dates": p["cardio_dates"],
            "hybrid_run_sessions": p.get("hybrid_run_sessions", 0),
            "hybrid_bike_sessions": p.get("hybrid_bike_sessions", 0),
            "no_days_off_max": p.get("no_days_off_max", 0),
            "night_sessions": p.get("night_sessions", 0),
            "early_sessions": p.get("early_sessions", 0),
            "achievements": p["achievements"],
        }}
    )
    return {
        "xp_gained": xp_gained,
        "achievement_xp": ach_xp,
        "total_xp": p["xp"],
        "level": p["level"],
        "new_achievements": [{"key": k, **ACHIEVEMENTS[k], "xp": TIER_XP.get(ACHIEVEMENTS[k].get('tier','basic'),50)} for k in new_ach],
        "stats": {
            "total_run_km": p.get("total_run_km", 0.0),
            "total_bike_km": p.get("total_bike_km", 0.0),
            "longest_run_km": p.get("longest_run_km", 0.0),
            "longest_bike_km": p.get("longest_bike_km", 0.0),
            "best_run_pace_sec_per_km": p.get("best_run_pace_sec_per_km"),
        },
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
