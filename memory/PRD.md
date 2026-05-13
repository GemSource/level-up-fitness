# Hunter Strength System — PRD v6

## v6 Update: Boss Fight Lock System

### New Endpoint
`GET /api/profile/{id}/boss-fight/requirements` — returns gate status for the user's next-rank Boss Fight (14/14 tests PASS).

### Response Schema
```json
{
  "locked": true,
  "next_rank": "C",
  "next_threshold_kg": 550,
  "rank_threshold_kg": 600,
  "requirements": [
    {"key":"total","label":"Total","have":580,"need":550,"unit":"kg","met":true},
    {"key":"squat","label":"Squat","have":140,"need":130,"unit":"kg","met":true},
    {"key":"bench","label":"Bench","have":80,"need":90,"unit":"kg","met":false},
    {"key":"deadlift","label":"Deadlift","have":160,"need":150,"unit":"kg","met":true},
    {"key":"quests","label":"Quests Completed","have":8,"need":12,"unit":"","met":false},
    {"key":"deloads","label":"Deload Weeks","have":0,"need":1,"unit":"","met":false}
  ],
  "missing": ["Bench needs +10kg","Complete 4 more quests completed","Complete 1 more deload weeks"],
  "max_rank": false
}
```

### Requirement Tiers (per next-rank target)
| Target | Total | Squat | Bench | Deadlift | Quests | Deloads |
|--------|-------|-------|-------|----------|--------|---------|
| D      | 450   | 100   | 60    | 120      | 6      | 0       |
| C      | 550   | 130   | 90    | 150      | 12     | 1       |
| B      | 650   | 150   | 110   | 170      | 20     | 1       |
| A      | 750   | 180   | 130   | 200      | 30     | 2       |
| S      | 850   | 220   | 150   | 240      | 50     | 2       |

### Enforcement
`POST /api/profile/{id}/boss-fight` now calls `evaluate_boss_requirements()` first. Returns **403 Forbidden** with structured detail if locked:
```json
{"detail": {"error":"boss_fight_locked","message":"Boss Fight Locked","next_rank":"C","missing":[...],"requirements":[...]}}
```

### Frontend
- **`/boss-fight` screen**: when locked, shows red-bordered SystemFrame with:
  - Lock icon + "BOSS FIGHT LOCKED" header
  - Per-requirement row (✓ met / ✗ unmet) showing `have / need` values
  - Red "MISSING" box listing actionable gaps ("Bench needs +10kg", "Complete 4 more quests")
  - Input fields dimmed (editable=false)
  - Engage button shows "LOCKED — COMPLETE REQUIREMENTS" with neutral styling
- Submit handler parses 403 structured response and re-displays missing list as alert

## Cumulative System (v1-v6)
- 8+ feature areas: onboarding, auto-block, RPE adaptive load, day-intensity, goal-ratio progression, cardio, AI coach, rank progress, boss-fight gates
- 116 achievements / 20 categories / 5 tiers
- 11 backend endpoints; AI via real Claude Sonnet 4.5
- Backend total tests: v1: 16, v3: 34, v4: 15, v5: 14, v6: 14 — **93/93 PASS**
