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
    last_workout_date: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    block_start_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    boss_fight_count: int = 0
    achievements: List[str] = []

class SetLog(BaseModel):
    weight: float
    reps: int
    rpe: Optional[float] = None
    completed: bool = True

class ExerciseLog(BaseModel):
    name: str
    target_sets: int
    target_reps: int
    target_weight: float
    target_rpe: Optional[float] = None
    sets: List[SetLog] = []

class WorkoutLogInput(BaseModel):
    workout_id: str
    exercises: List[ExerciseLog]
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

def generate_block(squat: float, bench: float, deadlift: float, training_days: int) -> List[dict]:
    """Generate a 6-week powerlifting block.
    Weeks 1-4: Build (volume), Week 5: Heavy (intensification), Week 6: Deload
    """
    # Week templates: (label, intensity_pct, sets, reps)
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
            exercises = []
            if day_type == "SQUAT_DAY":
                exercises = [
                    {"name": "Back Squat", "sets": sets, "reps": reps, "weight": round_to_2_5(squat * pct), "target_rpe": target_rpe, "is_main": True},
                    {"name": "Romanian Deadlift", "sets": 3, "reps": 8, "weight": round_to_2_5(deadlift * 0.55), "target_rpe": 7, "is_main": False},
                    {"name": "Walking Lunges", "sets": 3, "reps": 10, "weight": round_to_2_5(squat * 0.25), "target_rpe": 7, "is_main": False},
                ]
            elif day_type == "BENCH_DAY":
                exercises = [
                    {"name": "Bench Press", "sets": sets, "reps": reps, "weight": round_to_2_5(bench * pct), "target_rpe": target_rpe, "is_main": True},
                    {"name": "Overhead Press", "sets": 3, "reps": 8, "weight": round_to_2_5(bench * 0.6), "target_rpe": 7, "is_main": False},
                    {"name": "Barbell Row", "sets": 4, "reps": 8, "weight": round_to_2_5(bench * 0.8), "target_rpe": 7, "is_main": False},
                ]
            elif day_type == "DEADLIFT_DAY":
                exercises = [
                    {"name": "Deadlift", "sets": sets, "reps": reps, "weight": round_to_2_5(deadlift * pct), "target_rpe": target_rpe, "is_main": True},
                    {"name": "Front Squat", "sets": 3, "reps": 6, "weight": round_to_2_5(squat * 0.6), "target_rpe": 7, "is_main": False},
                    {"name": "Pull-ups", "sets": 4, "reps": 8, "weight": 0, "target_rpe": 8, "is_main": False},
                ]
            elif day_type == "UPPER_ACC":
                exercises = [
                    {"name": "Close-Grip Bench", "sets": 4, "reps": 6, "weight": round_to_2_5(bench * 0.75), "target_rpe": 7, "is_main": False},
                    {"name": "Incline DB Press", "sets": 3, "reps": 10, "weight": round_to_2_5(bench * 0.3), "target_rpe": 7, "is_main": False},
                    {"name": "Lat Pulldown", "sets": 4, "reps": 12, "weight": round_to_2_5(bench * 0.5), "target_rpe": 7, "is_main": False},
                ]
            elif day_type == "LOWER_ACC":
                exercises = [
                    {"name": "Pause Squat", "sets": 4, "reps": 5, "weight": round_to_2_5(squat * 0.7), "target_rpe": 7, "is_main": False},
                    {"name": "Leg Press", "sets": 3, "reps": 12, "weight": round_to_2_5(squat * 1.0), "target_rpe": 7, "is_main": False},
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
    )
    pdoc = profile.model_dump()
    # generate first block
    workouts = generate_block(data.squat_max, data.bench_max, data.deadlift_max, data.training_days)
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

    # Compute XP
    xp_gained = 100  # base workout
    has_squat = any("Squat" in ex.name for ex in data.exercises)
    has_bench = any("Bench" in ex.name and "Press" in ex.name for ex in data.exercises)
    has_deadlift = any("Deadlift" in ex.name for ex in data.exercises)
    if target_w["day_type"] == "SQUAT_DAY" and has_squat:
        xp_gained += 150
    # bonus: hit all sets/reps target
    all_hit = True
    rpe_logged = False
    for ex in data.exercises:
        hit_count = sum(1 for s in ex.sets if s.completed and s.reps >= ex.target_reps)
        if hit_count < ex.target_sets:
            all_hit = False
        if any(s.rpe is not None for s in ex.sets):
            rpe_logged = True
    if all_hit:
        xp_gained += 50
    if rpe_logged:
        xp_gained += 25

    # Update workout
    target_w["completed"] = True
    target_w["completed_at"] = datetime.now(timezone.utc).isoformat()
    target_w["logs"] = [ex.model_dump() for ex in data.exercises]
    target_w["notes"] = data.notes
    target_w["xp_gained"] = xp_gained

    # Update streak
    today = datetime.now(timezone.utc).date().isoformat()
    last = p.get("last_workout_date")
    if last:
        last_date = datetime.fromisoformat(last).date() if "T" not in last else datetime.fromisoformat(last).date()
        diff = (datetime.now(timezone.utc).date() - last_date).days
        if diff == 0:
            pass
        elif diff == 1 or diff == 2:
            p["streak"] = p.get("streak", 0) + 1
        else:
            p["streak"] = 1
    else:
        p["streak"] = 1
    p["last_workout_date"] = today

    # weekly bonus: if all of this week's workouts now complete
    week_no = target_w["week"]
    week_workouts = [w for w in workouts if w["week"] == week_no]
    if all(w.get("completed") for w in week_workouts):
        xp_gained += 300
        if week_no == 6:
            xp_gained += 200  # deload

    apply_xp(p, xp_gained)
    completed_count = sum(1 for w in workouts if w.get("completed"))
    new_ach = check_achievements(p, completed_count)

    # Generate AI coach next-session suggestion based on last logs
    suggestion = build_progression_suggestion(target_w)

    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {
            "workouts": workouts,
            "xp": p["xp"],
            "level": p["level"],
            "streak": p["streak"],
            "last_workout_date": p["last_workout_date"],
            "achievements": p["achievements"],
        }}
    )

    return {
        "xp_gained": xp_gained,
        "total_xp": p["xp"],
        "level": p["level"],
        "streak": p["streak"],
        "new_achievements": [{"key": k, **ACHIEVEMENTS[k]} for k in new_ach],
        "suggestion": suggestion,
    }

def build_progression_suggestion(workout: dict) -> str:
    logs = workout.get("logs", [])
    if not logs:
        return "Keep showing up. The System rewards consistency."
    main = next((e for e in logs if any(s.get("completed") for s in e.get("sets", []))), logs[0])
    sets = main.get("sets", [])
    avg_rpe = [s["rpe"] for s in sets if s.get("rpe") is not None]
    target_rpe = main.get("target_rpe") or 8
    all_reps_hit = all(s.get("reps", 0) >= main.get("target_reps", 0) for s in sets if s.get("completed"))
    if avg_rpe:
        avg = sum(avg_rpe) / len(avg_rpe)
        if all_reps_hit and avg <= target_rpe - 1:
            return f"[SYSTEM]: Power surge detected. Add 2.5–5kg to {main['name']} next session."
        elif avg >= target_rpe + 1:
            return f"[SYSTEM]: Mana low. Hold {main['name']} weight next session. Recover."
        else:
            return f"[SYSTEM]: Solid execution on {main['name']}. Repeat the load next session."
    return f"[SYSTEM]: Quest complete. Log RPE next time for sharper guidance."

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

    # Regenerate block with new maxes
    new_workouts = generate_block(data.squat_max, data.bench_max, data.deadlift_max, p["training_days"])
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
            if any(k in ex_log["name"] for k in ["Back Squat", "Bench Press", "Deadlift"]) and "Romanian" not in ex_log["name"]:
                top_set = max(
                    (s for s in ex_log.get("sets", []) if s.get("completed")),
                    key=lambda s: s["weight"] * s["reps"],
                    default=None,
                )
                if top_set:
                    history.append({
                        "date": w.get("completed_at"),
                        "exercise": ex_log["name"],
                        "weight": top_set["weight"],
                        "reps": top_set["reps"],
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
            context += f"- Week {w['week']} ({w['week_label']}) {w['day_type']}\n"
            for ex in w.get("logs", []):
                if ex.get("sets"):
                    s = ex["sets"][0]
                    context += f"  • {ex['name']}: {s['weight']}kg x {s['reps']} (RPE {s.get('rpe','N/A')})\n"
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
