# Hunter Strength System — PRD v7

## v7 Update: Hunter Shop + Loot Drops + Inventory + Buff Activation

### New Currency
**Hunter Coins** — stored on profile (`coins` field). Awarded for:
- +20 per workout, +30 if all exercises done, +100 weekly perfect bonus
- +200 base boss-fight, +400 if rank-up
- +25 to +200 per achievement unlock (by tier: beginner 25, basic 50, medium 100, major/elite 200)
- Loot drops occasionally give coin packs (+20 to +110 with streak multiplier)

### Loot Drop System
After every completed workout: `roll_loot(streak)` returns 1 guaranteed drop + 20-35% bonus chance. Rarity weights:
- Default: common 60% / rare 30% / epic 9% / legendary 1%
- Streak ≥3: 45/40/13/2 (slight rare-weight boost)
- Streak ≥7: 0/60/35/5 (guaranteed ≥ rare)
- Streak ≥14: 30/40/25/5 (legendary chance 5x)

### Item Catalog (10 items, 4 categories)
- **Training**: Power Boost (+2.5% XP), Extra Set Token (+25 flat XP)
- **XP**: +25% XP, 2x XP, XP Surge (7d, +10%)
- **Recovery**: Fatigue Reset, Joint Recovery Buff
- **Boss**: Second Attempt Token, Adrenaline Surge (+50% XP), Monarch's Aura (legendary, +100%)

Rarities: common (grey #888) / rare (blue #5C9DFF) / epic (purple #C77CFF) / legendary (gold #FFD700)

### New Endpoints (4)
- `GET /api/shop/catalog` — full catalog
- `GET /api/profile/{id}/inventory` — coins, items[], active_buffs[]
- `POST /api/profile/{id}/shop/buy` `{item_key}` — deducts coins, adds to inventory
- `POST /api/profile/{id}/inventory/activate` `{item_key}` — moves to active_buffs (max 2)

### Buff Activation Flow
1. User taps "Activate" on item in inventory
2. Item removed from inventory, added to `active_buffs[]` with scope (workout / boss_fight / duration_7d / workout_or_boss)
3. Buff consumed automatically when matching session completes
4. Workout-scoped buff applies `xp_mult` to xp_gained → `buff_xp_extra` returned in workout-log response
5. Boss-fight scoped buff multiplies `xp_reward` (e.g., Adrenaline 1.5x → 1000 → 1500)

### Balance Rules Enforced
- Max 2 active buffs at once
- Buffs cannot fake strength — only XP/coin modifiers, no override of logged weights
- Buffs require workout_complete=true (partial sessions don't trigger loot or buff consumption)
- Insufficient coins → 400 with `detail.error="insufficient_coins"`

### Frontend
- **`/shop.tsx`**: Black Market with category filter (ALL/TRAINING/RECOVERY/XP/BOSS), rarity-colored item cards, coin balance pill, buy buttons (greyed if insufficient)
- **`/inventory.tsx`**: Hunter Cache showing Active Buffs section (max 2) + Item grid with quantity tags, Activate buttons
- **Dashboard header**: gold coin pill (tappable → shop) + cube icon (tappable → inventory) + planet icon (AI coach)
- **Workout completion alert**: now shows "🎁 [LOOT ACQUIRED]" section with rarity-tagged items

### Backend: 27/27 v7 tests PASS (23 v7 + 4 hotfix)
- Bug fixed: boss-fight `boss_coin`/`boss_applied` NameError on success path resolved
- All catalog/buy/activate/loot endpoints verified
- Buff scope isolation tested (workout buff NOT consumed by boss-fight, vice versa)

## Cumulative System (v1→v7)
- **15 backend endpoints**, all live-tested
- **116 achievements / 20 categories / 5 tiers**
- **120/120 cumulative backend tests** across all iterations PASS
- AI Coach via real Claude Sonnet 4.5 (Emergent LLM key)
