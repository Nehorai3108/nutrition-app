# Research Brief — 2026-05-31 (v2 — Full Feature Audit)

## Existing Feature Inventory (confirmed from codebase)

| Page | Feature |
|------|---------|
| `0_profile.py` | User profile — personal details, goals, activity level |
| `2_receipt_scanner.py` | Receipt/document scanner — OCR to add foods to inventory |
| `2_recipes.py` | Recipe browser — search and view recipes |
| `3_recipe_detail.py` | Recipe detail view — ingredients, instructions, macros |
| `4_inventory.py` | Personal inventory — manage pantry items |
| `5_scanner.py` | Food scanner (secondary/legacy scan entry point) |
| `6_daily_menu.py` | Daily menu — AI meal recommendations (breakfast/lunch/dinner) |
| `7_weekly_workout_plan.py` | Weekly workout plan — per-day training schedule |
| `7_workout_tracker.py` | Workout tracker — log sessions, calories burned |
| `8_calendar.py` | Calendar — food, water, workout event timeline |
| `9_history.py` | History & weekly planning — past plans and progress |
| `10_chat_log.py` | AI nutrition chat — Groq/llama-3.3-70b conversational logging |
| `11_meal_wizard.py` | Guided meal plan wizard — mobile-friendly onboarding flow |
| `12_barcode.py` | Barcode scanner — product lookup + community database |
| `13_meal_preferences.py` | Meal preferences picker — first-login cuisine/food preferences |
| `14_settings.py` | Settings — Calm Mode (quiet notifications) |
| `16_hydration.py` | **Hydration tracking** — daily water intake log *(already implemented)* |

**Correction to v1 brief:** Feature #2 (Hydration Tracking) is already shipped as `pages/16_hydration.py`. Reorder priority accordingly.

## Backend Capabilities (Agent Map)

| Agent | Responsibility |
|-------|---------------|
| Agent 1 (Contracts) | Domain models, schemas, validation |
| Agent 2 (Nutrition) | BMR/TDEE via Mifflin-St Jeor, macro targets (protein/carb/fat splits by goal), fiber floors, workout calorie adjustment |
| Agent 3 (Food) | Food catalog, search, matching |
| Agent 4 (Inventory) | Inventory management, availability, deduction |
| Agent 5 (Planner) | Deterministic meal plan + weekly planner |
| Agent 6 (AI) | Text formatting, summaries (Groq) |
| Agent 7 (Data) | Persistence, artifact management, cleanup |
| Agent 8 (Director) | Gap identification, task creation |
| Agent 9 (Critic) | Task review, approval/rejection |
| Agent 10/11 (Recipes) | Recipe data collection, filtering, unit conversion, instructions |
| Agent food_data | Food data enrichment pipeline |
| Agent recipe_images | Recipe image fetching |
| Agent chat_parser | Parse AI chat responses into structured food logs |

**Notable gaps in agent layer:** No dedicated micronutrient agent, no fasting agent, no kosher resolution service, no streak/gamification state manager.

---

## Top 10 Missing Features (v2 — corrected ranking)

| # | Feature | Impact | Complexity | Reuses |
|---|---------|--------|------------|--------|
| 1 | Intermittent Fasting Timer | High | S | `pages/8_calendar.py`, `pages/0_profile.py` |
| 2 | Habit Streaks & Gamification | High | S–M | `pages/8_calendar.py`, `pages/9_history.py` |
| 3 | Kosher Status on Barcode Scan | High | M | `pages/12_barcode.py`, `nutrition_app/agents/agent_3_food/` |
| 4 | GLP-1 Medication Tracker | High | S–M | `pages/0_profile.py`, `pages/14_settings.py` |
| 5 | Micronutrient Tracking (5–6 key nutrients) | High | M | `nutrition_app/agents/agent_2_nutrition/nutrition_engine.py` |
| 6 | Proactive AI Coaching (nudges) | Medium | M | `pages/10_chat_log.py`, `nutrition_app/agents/agent_6_ai/ai_layer.py` |
| 7 | Recipe Suggestions from Inventory | Medium | M | `nutrition_app/agents/agent_4_inventory/`, `nutrition_app/agents/agent_11_recipes/` |
| 8 | Hydration Goal Auto-Calculation | Medium | S | `pages/16_hydration.py`, `nutrition_app/agents/agent_2_nutrition/nutrition_engine.py` |
| 9 | AI Meal Photo Scanning | Medium | L | `pages/12_barcode.py`, `nutrition_app/agents/agent_6_ai/` |
| 10 | CGM Integration | Low | L | — (new integration) |

---

## Feature Deep-Dives (top 3)

### 1. Intermittent Fasting Timer

- **What it is:** Persistent countdown/count-up timer showing fasting window (16:8, 18:6, 5:2, OMAD). User taps "Start Fast" — timer counts elapsed hours, shows % progress toward goal window, alerts on eating window open/close. Streak counter for consecutive fasting days.
- **Why now:** Zero (fasting app) has 10M+ logged fasts. 65M+ US adults practice intermittent fasting. Israel has high keto/IF adoption. BiteFit already tracks daily calories — a fast breaks calorie tracking naturally; zero additional data entry needed. Highest retention-per-engineering-hour ratio of any missing feature.
- **Implementation sketch:**
  - New page: `pages/15_fasting.py` — protocol picker, live timer widget, streak display
  - Model: `nutrition_app/models/fasting_session.py` — `{user_id, start_ts, target_hours, protocol, ended_ts}`
  - Repository: `nutrition_app/repositories/fasting_repository.py` — CRUD + streak calc
  - Wire into `pages/8_calendar.py` — fasting window overlays as calendar dots
  - Wire into `pages/6_daily_menu.py` — suppress meal suggestions during fasting window
- **Existing code to reuse:**
  - `nutrition_app/models/user.py` — user_id FK
  - `pages/8_calendar.py` — extend calendar events to include fasting blocks
  - `nutrition_app/agents/agent_7_data_performance/data_manager.py` — persist sessions
  - `nutrition_app/repositories/profile_repository.py` — repo pattern to follow

### 2. Habit Streaks & Gamification

- **What it is:** Daily streaks for logging meals, hitting water goal, completing workouts, and staying within calorie budget. Weekly challenge badges (e.g., "7-day protein champion"). A simple XP/level system displayed on the profile page. Push notification on streak milestone.
- **Why now:** Duolingo's streak mechanic is the most-copied feature in consumer apps for a reason — daily active use directly correlates with streak length. BiteFit already has a calendar (`pages/8_calendar.py`) and history (`pages/9_history.py`) that store daily completions; streaks can be computed from existing data with zero new tracking infrastructure.
- **Implementation sketch:**
  - New service: `nutrition_app/services/streak_calculator.py` — reads food_log + water + workout records, computes per-category streaks
  - Extend `pages/0_profile.py` — add streak badges section (flame icons, best streak, current streak)
  - Extend `pages/9_history.py` — weekly completion heatmap (GitHub-style grid)
  - New page (optional): `pages/17_achievements.py` — full badge gallery
  - No new storage needed: compute from existing logs at read time (cache if slow)
- **Existing code to reuse:**
  - `pages/8_calendar.py` — already stores daily events; streaks derive from this
  - `pages/9_history.py` — history UI patterns for streak display
  - `nutrition_app/agents/agent_7_data_performance/data_manager.py` — log access

### 3. GLP-1 Medication Tracker

- **What it is:** Optional profile flag "I'm taking GLP-1 medication (Ozempic/Wegovy/Mounjaro)". Unlocks: weekly dose reminder, appetite suppression mode (auto-reduces calorie targets by 15–20% during low-appetite days), nausea logging (1–5 scale), side effect notes, and a weekly progress check-in. Protein targets are automatically elevated (GLP-1 users lose muscle mass without high protein).
- **Why now:** GLP-1 drugs are subsidized in Israel for BMI ≥30 since 2023 (via Kupat Holim). 400,000+ Israelis are estimated to be on or about to start GLP-1 drugs. Zero Hebrew-language GLP-1 nutrition companion apps exist. BiteFit's existing calorie + protein targeting infrastructure is exactly what GLP-1 users need — just with modified defaults.
- **Implementation sketch:**
  - Extend `nutrition_app/models/user.py` — add `glp1_active: bool`, `glp1_drug: str | None`, `glp1_start_date: date | None`
  - Extend `nutrition_app/agents/agent_2_nutrition/nutrition_engine.py` — if `glp1_active`, increase `PROTEIN_PER_KG` to 2.4, add `appetite_suppression_factor` parameter
  - Extend `pages/0_profile.py` — GLP-1 toggle in medical section (with disclaimer)
  - New widget in `pages/6_daily_menu.py` — "נוסעים ב-Ozempic? סמן ארוחה קטנה" low-appetite day button
  - New log model: `nutrition_app/models/glp1_log.py` — `{date, dose_mg, nausea_score, notes}`
  - Surface in `pages/9_history.py` — dose timeline + side effect trend
- **Existing code to reuse:**
  - `nutrition_app/agents/agent_2_nutrition/nutrition_engine.py` — `PROTEIN_PER_KG` dict, `GOAL_CALORIE_ADJUSTMENT` dict
  - `pages/0_profile.py` — medical profile section pattern
  - `nutrition_app/models/user.py` — user model to extend

---

## Israeli Market Notes

- **Kosher tracking is table-stakes.** 75%+ of Israeli households check kosher status. Kaspenu (launched April 2025) already does this. BiteFit's barcode scanner returns nutrition but no kosher badge — fix this before any other Israel-specific feature.
- **GLP-1 is a blue ocean in Hebrew.** 400K+ Israeli users on semaglutide; no dedicated Hebrew app. Earliest mover wins.
- **Sabbath mode:** Suppress push notifications Friday sunset → Saturday night. One cron rule, configurable in `pages/14_settings.py` (Calm Mode already exists as a template).
- **Local food database gaps:** Open Food Facts has sparse coverage for Strauss, Tnuva, Osem products. The community barcode flow (`pages/12_barcode.py`) is the right answer — gamify contributions with streak points once gamification ships.
- **Passover mode:** Seasonal flag — Chametz vs. Kosher lePesach per product in April. High engagement for observant users. Low engineering cost once kosher resolver is live.
- **Hebrew RTL rendering:** Food names mixing Hebrew + brand names (e.g., "Danone דנונה") need careful `direction: rtl` CSS treatment in Streamlit.

---

## Deprioritize

| Feature | Reason |
|---------|--------|
| **CGM Integration** | Requires Dexcom/FreeStyle API partnership, compliance review, ML for pattern analysis. Revisit at 50K+ users. |
| **Social / Community Features** | Cold-start problem, real-time infra cost, moderation burden. Defer until product-market fit confirmed. |
| **Full Micronutrient Database (80+ nutrients)** | Build 5–6 highest-impact ones first (iron, B12, D, calcium, folate, zinc) — full 80-nutrient USDA build is years of data work. |
| **AI Meal Photo Scanning** | Accuracy on Israeli home-cooked food (shakshuka, hummus, falafel) is poor with generic models. Needs fine-tuned local cuisine dataset. Build after barcode + OCR coverage matures. |
| **Full Social Feed** | Engineering distraction; community value only appears at scale. Barcode community contributions (already in `pages/12_barcode.py`) are sufficient social layer for now. |

---

## Competitive Intelligence (from live market research)

### Direct Israeli Competitors
| App | Key Differentiator | Threat Level |
|-----|-------------------|--------------|
| **Kaspenu** (Apr 2025) | Kosher labeling, additives, Israeli food scores, price comparison | High — validates market, currently nutrition-light |
| **Caloria** | **50K+ Israeli local foods + 3M global products, Hebrew UI, barcode scanner** | High — most feature-complete Hebrew competitor |
| **Nutrino** | Israeli-founded, AI-driven personalized food recommendations (acquired by Medtronic) | Medium — B2B pivot, less consumer threat |
| **KosherScan** | Rabbi-verified kosher database, barcode scan | Low — kosher-only, not full nutrition |

**Key insight:** Caloria is the primary Hebrew-language competitor to benchmark against. BiteFit needs differentiation beyond food logging — GLP-1 support, fasting timers, and gamification are all gaps Caloria does not cover.

### Global Market Sizing (validated)
- AI nutrition coaching: **USD 1.58B (2025) → USD 17.59B (2035)** — 27% CAGR
- Diet/nutrition apps overall: **USD 6.94B (2026) → USD 27.73B (2035)**
- Gamification impact: **40% engagement boost**, 50%+ of top diet apps now have it
- Social accountability: **25% higher engagement** vs. solo tracking
- GLP-1 specialized apps (Glapp, Shotsy, Pep) have emerged as a new category — signals user demand for integration into nutrition trackers rather than separate apps

### AI Photo Scanning — Updated Feasibility
DexCom launched AI photo food logging in July 2025; Lifesum shipped "Multimodal Tracker" (photo/voice/barcode/text) in early 2025. **This feature is moving from "premium" to "expected" faster than anticipated.** Recommend upgrading from Deprioritize to medium-term roadmap (6–9 months), using an API like LogMeal or Clarifai rather than building from scratch. Complexity drops from L → M with an API approach.

---

# Research Brief — 2026-05-31

## Market Context

The global diet and nutrition app market is at USD 6.94B in 2026, growing at 16.64% CAGR toward USD 27.73B by 2035, driven by AI personalization, GLP-1 medication adoption, and wearable integrations. Apps are racing past macro tracking into photo-based logging, micronutrient depth, and AI coaching that learns over time. The Israeli market is especially ripe: Kaspenu launched April 2025 as the first local barcode nutrition app (French Yuka-inspired), showing strong appetite for Hebrew-first, kosher-aware apps — and no dominant player yet in full nutrition tracking.

---

## Top 10 Missing Features

| # | Feature | Impact | Complexity | Reuses |
|---|---------|--------|------------|--------|
| 1 | Intermittent Fasting Timer | High | S | `pages/8_calendar.py`, `pages/0_profile.py` |
| 2 | Water / Hydration Tracking | High | S | `pages/8_calendar.py` (partially referenced) |
| 3 | Habit Streaks & Gamification | High | S–M | `pages/8_calendar.py`, `pages/9_history.py` |
| 4 | Kosher Status on Barcode Scan | High | M | `pages/12_barcode.py`, `nutrition_app/agents/agent_3_food/` |
| 5 | Micronutrient Tracking (vitamins/minerals) | High | M | `nutrition_app/agents/agent_2_nutrition/nutrition_engine.py`, `nutrition_app/models/nutrition_targets.py` |
| 6 | AI Meal Photo Scanning | High | L | `pages/12_barcode.py`, `nutrition_app/agents/agent_6_ai/` |
| 7 | GLP-1 Medication Tracker | Medium | S–M | `pages/0_profile.py`, `pages/14_settings.py` |
| 8 | Proactive AI Coaching (push nudges) | Medium | M | `pages/10_chat_log.py`, `nutrition_app/agents/agent_6_ai/ai_layer.py` |
| 9 | Recipe Suggestions from Inventory | Medium | M | `nutrition_app/agents/agent_4_inventory/`, `nutrition_app/agents/agent_11_recipes/` |
| 10 | CGM Integration | Low | L | — (new integration) |

---

## Feature Deep-Dives (top 3)

### 1. Intermittent Fasting Timer

- **What it is:** A persistent timer UI showing current fasting window, elapsed time, and goal window (16:8, 18:6, 5:2, OMAD). User sets eating window; app tracks streak of consecutive fasting days and alerts when eating window opens/closes.
- **Why now:** Zero (fasting app) has 10M+ logged fasts; 65M+ US users fast. Israel has high keto/IF adoption. Fasting is tightly coupled to calorie goals already tracked in BiteFit — natural fit. Zero complexity, high retention impact.
- **Implementation sketch:**
  - New page: `pages/15_fasting.py` — timer UI, protocol picker, streak counter
  - Model: `nutrition_app/models/fasting_session.py` — stores start_time, target_hours, protocol
  - Repository: `nutrition_app/repositories/fasting_repository.py`
  - Wire into `pages/8_calendar.py` calendar dots to show fasting days
- **Existing code to reuse:**
  - `nutrition_app/models/user.py` — link to user_id
  - `pages/8_calendar.py` — extend calendar to display fasting window overlays
  - `nutrition_app/agents/agent_7_data_performance/data_manager.py` — persist sessions

---

### 2. Water / Hydration Tracking

- **What it is:** Daily water intake goal (auto-calculated: ~35 ml/kg body weight, adjusted for activity), per-drink logging (cup, bottle, custom ml), progress ring, smart reminder nudges. Optional: track water from food sources.
- **Why now:** Already referenced in `pages/8_calendar.py` (calendar tracks water events). Users expect it as table-stakes. Simple to implement with high daily engagement (3–8 log events per day vs. 3 meals). Personalised goal reuses existing weight + activity data from the profile.
- **Implementation sketch:**
  - New page: `pages/16_hydration.py` — daily intake dial, quick-add buttons (200ml, 350ml, 500ml, custom)
  - Model: `nutrition_app/models/hydration_log.py` — date, user_id, entries: [{time, ml}]
  - Goal calculation: extend `nutrition_app/agents/agent_2_nutrition/nutrition_engine.py` with `calculate_hydration_goal(user) -> float` (ml/day)
  - Surface daily total in `pages/6_daily_menu.py` header widget
- **Existing code to reuse:**
  - `nutrition_app/models/user.py` — weight_kg + activity_level already present for goal calc
  - `pages/8_calendar.py` — already has water tracking scaffold, just needs backend
  - `nutrition_app/repositories/profile_repository.py` — pattern for user-scoped repos

---

### 3. Kosher Status on Barcode Scan

- **What it is:** When a user scans a barcode (`pages/12_barcode.py`), also surface the product's kosher certification status (Mehadrin, Rabbanut, Chalav Yisrael, Pareve, Dairy, Meat, Treif/Unknown). Pull from Open Food Facts `kosher` tags + cross-reference Israeli Chief Rabbinate open data.
- **Why now:** Kaspenu launched April 2025 as first Israeli barcode nutrition app with kosher data — immediate competitive signal. BiteFit already has a barcode scanner and inventory system. Kosher status is the single most Israel-specific differentiator possible, zero algorithmic complexity, pure data enrichment. 75%+ of Israeli households consider kosher status when shopping.
- **Implementation sketch:**
  - Extend `pages/12_barcode.py` — after food lookup, call a new `KosherResolver`
  - New service: `nutrition_app/agents/agent_3_food/kosher_resolver.py`
    - Step 1: Check Open Food Facts product JSON for `labels_tags` containing `en:kosher` / `en:kosher-mehadrin` etc.
    - Step 2: If not found, query Israeli Rabbinate open API (or cached CSV)
    - Step 3: Return `KosherStatus(certification: str, authority: str, dairy_meat_pareve: str)`
  - UI: add colored badge to barcode result card (green=Kosher, yellow=Pareve, grey=Unknown, red=Treif)
  - Extend `nutrition_app/models/food_item.py` with optional `kosher_status: KosherStatus | None`
- **Existing code to reuse:**
  - `pages/12_barcode.py` — entire scan + result display flow
  - `nutrition_app/agents/agent_3_food/food_catalog.py` — food lookup pipeline to plug into
  - `nutrition_app/agents/agent_4_inventory/inventory_manager.py` — can store kosher status per item

---

## Israeli Market Notes

- **Kosher tracking is table-stakes.** Not optional for Israeli users. Current scanner shows nutrition but not kosher certification — competitors (Kaspenu, KosherScan) already doing this.
- **Sabbath mode:** Disable push notifications from Friday sunset to Saturday night. Many Israeli users will expect this. One-line cron rule; can be toggled in `pages/14_settings.py`.
- **Local food database gaps:** Open Food Facts has poor coverage for Israeli supermarket brands (Strauss, Tnuva, Osem). A community barcode contribution flow (already partially in `pages/12_barcode.py` — "קהילתי") is the right answer. Incentivize with streak points once gamification ships.
- **Hebrew number formatting:** Nutrition labels in Israel use metric (g, ml) — no conversion needed. But right-to-left text rendering for food names with both Hebrew and English (e.g., brand names) needs careful `direction: rtl` CSS.
- **GLP-1 is subsidized in Israel** (semaglutide covered by Kupat Holim for BMI ≥30 since 2023). This creates a large addressable user segment with specific needs: high-protein emphasis, small frequent meals, nausea logging, dose reminders. No Hebrew GLP-1 app exists yet.
- **Passover mode:** Seasonal feature — flag Chametz vs. Kosher lePesach status in April. Very high engagement signal for observant users.

---

## Deprioritize

| Feature | Reason |
|---------|--------|
| **CGM Integration** | Requires Dexcom/FreeStyle API partnership agreements, FDA-adjacent compliance territory, ML for pattern analysis. Overkill for current stage; revisit at 50K+ users. |
| **Social / Community Features** | High engineering cost (real-time infra, moderation), cold-start problem (needs users before it's valuable), and distraction from core tracking quality. Defer until product-market fit is solid. |
| **Full Micronutrient Database (80+ nutrients)** | USDA FoodData integration is feasible, but building accurate Israeli food entries for 80+ nutrients is years of data work. Better MVP: add 5–6 highest-impact micronutrients (iron, B12, D, calcium, folate, zinc) using existing food data. |
| **Recipe Suggestion from Inventory** | Agent 11 already has recipe filtering; Agent 4 has inventory. The gap is matching logic. Worth building but lower urgency than fasting/hydration which have zero overlap with existing features. |
| **AI Meal Photo Scanning** | Computer vision accuracy for home-cooked Israeli food (shakshuka, hummus, falafel) is poor with generic models. Requires fine-tuning on local cuisine data. High cost, medium accuracy. Build after barcode + OCR coverage is mature. |
