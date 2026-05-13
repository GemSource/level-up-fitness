# Hunter Strength System — PRD v5

## v5 Update: Rank Progress Tracker

### New Endpoint
`GET /api/profile/{id}/rank-progress` — returns dynamic next-rank tracker (14/14 tests PASS).

### Response Schema
```json
{
  "current_rank": "C",
  "next_rank": "B",
  "next_threshold_kg": 700,
  "current_total": 620,
  "remaining_kg": 80,
  "progress_pct": 88.6,
  "lift_contributions": {"squat": 25, "bench": 27.5, "deadlift": 27.5},
  "xp": {"current": 1150, "level": 5, "next_level_xp": 1500},
  "projected_weeks": {"min": 16, "max": 32},
  "message": "[SYSTEM]: 80kg away from B Rank. Focus on your bench to break through.",
  "rank_up": false
}
```

### Logic
- **Lift contribution math**: distributes `remaining_kg` weighted by gap from ideal powerlifting ratios (squat 36% / bench 26% / deadlift 38% of total). Weaker lifts (further from ideal share) get more recommended kg.
- **Projected weeks**: if user has gained since `starting_total`, uses actual rate (kg/week). Otherwise falls back to `progression_mode` range.
- **Dynamic messaging tiers**: ≥95% → "Almost there"; 75-95% → references weakest lift + remaining kg; 50-75% → "Steady progression"; <50% → "The path is long"; S-rank → "Monarch" acknowledgement.

### Frontend
- **`/src/components/RankProgressCard.tsx`** — reusable component with `compact` prop
- **Progress page**: full card at top with all stats, lift breakdown, XP bar, projected ETA, motivational message
- **Dashboard**: compact widget (smaller badges, no lift breakdown) showing current→next rank transition with progress bar

## Cumulative System (v1-v5)
- 116 achievements / 20 categories / 5 tiers (Beginner→Elite)
- 84 lift achievements with bodyweight ratios + thresholds
- RPE-driven adaptive load (auto-adjusts upcoming sessions)
- Per-day intensity modifier (Low/Base/High)
- Goal-ratio progression mode (conservative/moderate/aggressive)
- Cardio log (run/bike/sprint) with pace + distance achievements
- AI Coach (Claude Sonnet 4.5) via Emergent LLM key
- Boss Fight max test with rank-up animation
- Auto-generated 6-week training blocks

Backend test totals across iterations: v1: 16/16, v3: 34/34, v4: 15/15, v5: 14/14 — all PASS.
