# Hunter Strength System — PRD

## Vision
Solo Leveling-inspired powerlifting tracker that gamifies strength training as a quest/rank progression system (E→S Rank, goal 1000kg total).

## Core Mechanics (v2)
### Weight Calculation
`Training Weight = Current 1RM × Program Week % × Day Intensity Modifier`
- Per-day modifier: SQUAT_DAY/DEADLIFT_DAY = BASE (±0%), BENCH_DAY = HIGH (+2.5%), accessories = LOW (-2.5%)
- Barbell rounds to 2.5kg; Machine exercises (Lat Pulldown, Leg Press) round to 5kg
- Goal ratio decoupled from daily weights — affects only ETA pacing, not load

### RPE-Driven Progression
- Logged RPE < Target → +2.5kg applied to all remaining uncompleted same-day_type workouts
- Logged RPE == Target → hold
- Logged RPE > Target → −2.5kg applied
- Stored per-lift in `pending_adjustments` on profile

### Goal-Based Scaling (display only)
- Ratio < 1.25 → conservative (ETA ~1–2.5kg/week)
- Ratio 1.25–1.75 → moderate (ETA ~2.5–5kg/week)
- Ratio > 1.75 → aggressive (ETA ~5–7.5kg/week)

### XP System
- +20 per exercise done
- +50 main lift done
- +100 bonus when all exercises done
- +50 bonus when all done-exercises have RPE logged
- +300 weekly perfect bonus / +200 deload week bonus
- +1000 Boss Fight reward
- Levels: 500 XP base, +250 per level

### Rank Thresholds
E (<500) → D (500-599) → C (600-699) → B (700-799) → A (800-899) → S (900+)

### Block Structure
- 6 weeks: W1-4 Build / W5 Heavy / W6 Deload
- Days customized by training_days (3-6)
- Every 12 weeks → Boss Fight regenerates block from new maxes

## Tech
- Backend: FastAPI + MongoDB (motor), single embedded profile doc with workouts array
- Frontend: Expo Router + React Native
- LLM: emergentintegrations → Claude Sonnet 4.5 (in-character System Coach)
- No auth — local profile_id in AsyncStorage

## UI Screens
1. Onboarding (4-step) → 2. Dashboard (Status) → 3. Quest log (filter by week) → 4. Workout log (row-per-exercise, Done checkbox, live progress bar) → 5. Progress (goal %, history, mode badge, ETA range) → 6. Rank/Achievements (rank ladder + 12 trophies) → 7. Boss Fight (max test + animated rank-up) → 8. AI Coach modal

## Design
Heavy Solo-Leveling: neon cyan/danger red on void black, Rajdhani + JetBrains Mono, sharp corner frames, [SYSTEM] alerts, rank-tier colored badges.
