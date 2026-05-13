# Hunter Strength System — PRD v4

## v4 Update: Beginner-Friendly Achievement Tiers (116 total)

### New Tier System (5 visual tiers with XP rewards)
- **🟢 Beginner** (+25 XP) — green glow — entry wins for new lifters
- **🔵 Basic** (+50 XP) — cyan
- **🔷 Medium** (+100 XP) — blue
- **🟣 Major** (+250 XP) — purple
- **🟡 Elite** (+500 XP) — gold

### Achievement Categories (20 total, 116 achievements)
- **Firsts**: First Workout, First Week, First Deload
- **Strength ladders**: Squat 60-250kg (11 tiers), Bench 40-220kg (11 tiers), Deadlift 60-300kg (10 tiers)
- **Bodyweight ratios**: Bench 0.5/0.75/1/1.25/1.5x BW; Squat 1/1.5/2/2.5x BW; Deadlift 1/1.5/2/2.5/3x BW
- **Progression** (from baseline): +5kg/+10kg single lift, +20kg/+50kg total
- **Total**: 500/600/700/800/900/1000kg
- **Quests**: 1/3/5/10/25/50/100 completed
- **Weekly/Streak**: Perfect weeks (1/2/4/8), Streak (3/7/14/30 days)
- **Cardio**: Run (distance/total/pace), Bike (single/total), Sprint (100m/200m/400m)
- **Quality**: RPE logged, Perfect workouts
- **Hybrid**: Lift+Run/Bike same session
- **Volume**: 10k session, 25k week
- **Rank**: E→S (auto-unlock chain)
- **Special**: No Days Off, Comeback Arc, Night Hunter, Early Hunter
- **Boss**: Boss Slayer

### Tracking Added in v4
- `starting_squat/bench/deadlift/total` — baseline from onboarding (NOT reset by Boss Fight, so progression accrues forever)
- `session_types_completed` — list of day_types user has completed
- `first_week_done`, `first_deload_done` — first-time milestone flags

### Backend: 15/15 v4 tests PASS
- Beginner profile (60/40/80kg, bw 80) auto-unlocks 6 entry achievements on signup
- Strong profile (200/140/240) gets full ladder + elite bodyweight ratios
- First-session detection by day_type fires on first SQUAT/BENCH/DEADLIFT day
- Progression: Boss-fight increases trigger gain_lift_5/_10 and gain_total_20/_50
- Rank chain still auto-unlocks all lower tiers

### Frontend
- Tier color updated: beginner → green (#7CFFCB), basic → cyan, medium → blue, major → purple, elite → gold
- Category filter chips include new Firsts, Bodyweight, Progression
