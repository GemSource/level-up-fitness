# Hunter Strength System — PRD v3

## Vision
Solo Leveling-inspired strength + cardio gamification with deep achievement system (84 trophies across 18 categories) and RPE-driven adaptive programming.

## v3 Highlights (Achievement Expansion)
**84 achievements across 18 categories** with XP tiers (basic 50 / medium 100 / major 250 / elite 500):
- Strength: Squat, Bench, Deadlift (6 thresholds each)
- Total: 500/600/700/800/900/1000kg
- Quests: 1/5/10/25/50/100 completed
- Weekly: 1/2/4/8 perfect weeks
- Streak: 3/7/14/30 day streak
- Run: distance (1/3/5/10km), total (10/25/50/100/250km), pace (sub 6/5:30/5/4:30 per km)
- Sprint: 100m<20s, 200m<40s, 400m<90s
- Bike: distance (5/10/20/50km), total (50/100/250/500km)
- Quality: First RPE-all-logged, perfect workouts (1/5/10)
- Elite ratios: 2x BW squat, 1.5x BW bench, 2.5x BW deadlift
- Hybrid: Lift+Run 5x, Lift+Bike 5x
- Volume: 10,000kg session, 25,000kg week
- Rank: E/D/C/B/A/S (auto-unlocks all prior ranks when ranking up)
- Special: 7-day no-days-off, Comeback Arc (5+ day return), Night Hunter (>9pm), Early Hunter (<6am)
- Boss: Boss Slayer

## Endpoints (v3)
- `POST /api/profile/{id}/cardio` — new endpoint for run/bike/sprint logging with auto-achievement detection

## Tech
- Backend: FastAPI + MongoDB; emergentintegrations for Claude Sonnet 4.5 AI coach
- Frontend: Expo Router + React Native
- 34/34 backend tests pass; AI coach hits real Anthropic via Emergent LLM key

## UI
- New `/cardio.tsx` modal with activity picker (run/bike/sprint)
- Rebuilt Rank tab: horizontal category filter (ALL · 84, RANK 1/6, QUESTS 2/5, …), tier-colored badges + XP labels
- Dashboard now shows both `CARDIO LOG` and `BOSS FIGHT` action buttons

## Design
Solo-Leveling system aesthetic: neon cyan + tier colors (basic green / medium cyan / major purple / elite gold), Rajdhani + JetBrains Mono.
