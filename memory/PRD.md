# Hunter Strength System — PRD

## Vision
A Solo Leveling-inspired powerlifting tracker that gamifies strength training as a quest/rank progression system (E → S Rank, goal 1000kg total).

## Features (MVP)
- **Onboarding**: name, bodyweight, experience, 1RMs (Squat/Bench/Deadlift), training days/week, goal total
- **Auto-generated 6-week training block**: Weeks 1-4 (Build), Week 5 (Heavy), Week 6 (Deload). Days customized by training frequency (3-6).
- **Dashboard**: Rank badge, XP bar with level, current total, S/B/D maxes, streak, today's quest preview
- **Quest log**: List/filter by week, see all 24+ workouts
- **Workout logging**: Per-set weight/reps/RPE + completion toggle + notes
- **XP system**: +100 base, +150 squat day, +50 all-reps hit, +25 RPE logged, +300 perfect week, +200 deload, +1000 boss fight
- **Rank system**: E (<500) → D (500-599) → C (600-699) → B (700-799) → A (800-899) → S (900+)
- **Progress screen**: Goal % bar, current maxes, top-set history per lift
- **Rank/Achievements screen**: Rank ladder visual + 12 unlockable trophies
- **Boss Fight (max test)**: enter new 1RMs → calculate new rank + animated rank-up + regenerate block
- **AI Coach (Claude Sonnet 4.5)**: in-character "System" analyzes last quest + suggests progression. Uses Emergent LLM key.

## Tech Stack
- Backend: FastAPI + MongoDB (motor)
- Frontend: Expo Router + React Native (mobile-first)
- LLM: emergentintegrations → Claude Sonnet 4.5
- No auth — local profile stored via AsyncStorage

## Design
Heavy Solo-Leveling RPG: neon cyan/danger red on void black, sharp corner frames, Rajdhani + JetBrains Mono fonts, [SYSTEM] alert language, rank badges with rank-tier coloring, glow shadows.
