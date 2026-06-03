# Audit Feedback — 2026-06-02

## BRIEF_CRITIQUES

### design_brief.md

**Item 1 (Wire `bottom_nav()` on every missing page)**
- Current-state claim is stale: brief says "only called in app_user.py, pages/6_daily_menu.py, and pages/14_settings.py." As of today 9 pages already have bottom_nav wired (6_daily_menu, 7_workout_tracker, 9_history, 10_chat_log, 11_meal_wizard, 12_barcode, 14_settings, 16_hydration, and app_user.py). Only 6 pages remain genuinely missing: `0_profile`, `4_inventory`, `8_calendar`, `7_weekly_workout_plan`, `2_recipes`, `13_meal_preferences`.
- Acceptance criterion says "5 bottom-nav icons" — the nav now has **9 items** after the "water" tab was added. The criterion is stale and will fail a literal reading.
- The brief also omits three pages that exist but have no bottom_nav: `pages/2_receipt_scanner.py`, `pages/3_recipe_detail.py`, `pages/5_scanner.py`.

**Item 5 (Fix `layout="wide"` to `layout="centered"`)**
- The file list is incomplete. These pages also have `layout="wide"` but are NOT listed: `pages/10_chat_log.py`, `pages/7_weekly_workout_plan.py`, `pages/2_receipt_scanner.py`, `pages/3_recipe_detail.py`, `pages/5_scanner.py`, `pages/14_settings.py`. A partial sweep will leave half the problem unfixed.
- Acceptance criterion 1 ("No visual flash on page load") is **not code-verifiable** — it requires manual testing in a browser. The secondary criterion ("st.columns([1,1]) splits at ~240px each") is measurable but also requires running the app. Neither can be checked by `grep` or `py_compile`.

**Quick-win: `pages/14_settings.py` lines 39–44**
- NOT yet done. `pages/14_settings.py:39` still has `<h2 style="margin-bottom:2px">⚙️ הגדרות</h2>` and line 48 has `<h3 style="margin-bottom:2px">מצב שקט</h3>`. The `page_header()` / `section_header()` functions are imported in `0_profile.py` but never imported or called in `settings.py`. This item is in "Quick Wins" so it lacks a formal acceptance criterion and risks being skipped.

No structural or scope issues — Item 2 (FAB), Item 3 (sidebar cleanup), Item 4 (onboarding wizard) are well-specified with realistic scope. File references all exist.

---

### structure_brief.md

No issues with file references — all referenced paths (`auth/supabase_client.py`, `static/manifest.json`, `static/sw.js`, `ui/components.py`, `pyproject.toml`) exist.

**Acceptance criteria missing from security items** — P0–P8 each have a "Change" and a "Why" but no verifiable "Done when:" clause. Example: P0 says "Rotate `SUPABASE_SERVICE_KEY`" but doesn't state "Done when: `.env` no longer contains a value starting with `sb_secret_`". Without a checkpoint, the implementor has no way to definitively close an item. This makes audit of P0–P8 completion impossible without reading `.env` directly.

No scope or duplication issues.

---

### research_brief.md

**Critical: duplicate stale content.** The file contains two separate "# Research Brief — 2026-05-31" sections. The v2 section (lines 1–162) correctly notes hydration is already implemented. But the v1 section (lines 164–262) is still appended verbatim — it lists "Water / Hydration Tracking" as Feature #2 missing, which is factually wrong. `pages/16_hydration.py` exists and is fully wired. Any implementor reading the bottom of the file will attempt to re-implement a shipped feature.

**No acceptance criteria for any feature.** Each feature has an implementation sketch but no testable done conditions. Example: Feature #1 (Fasting Timer) lists new files to create but has no "Done when: `pages/15_fasting.py` compiles, protocol picker renders on load, streak counter persists across sessions." Nothing to check off or audit.

No duplicate items with other briefs. File references in feature sketches all resolve: `food_catalog.py`, `inventory_manager.py`, `nutrition_targets.py`, `food_item.py`, `agent_11_recipes/` all confirmed to exist.

---

## IMPLEMENTOR_FEEDBACK

### Last run: 2026-06-02 10:00 — Promote hydration goal calculation to nutrition engine (FIX 2)

**Overall:** APPROVED

Verification of all three acceptance criteria:
- `calculate_hydration_goal` at `nutrition_engine.py:212` — exists, grep-confirmed ✅
- `_calc_goal_from_profile` absent from `pages/16_hydration.py` — no match, confirmed ✅
- Math: `max(1500.0, min(4000.0, round(weight_kg * 35 / 50) * 50))` — 70 kg → 2450, 0 kg → 2000 (default branch), 120 kg → 4000 (clamped) — all correct ✅

Function signature takes `weight_kg: float` (not a profile dict), which matches the stated rationale and is consistent with how the page uses it. No regressions in `nutrition_engine.py` — the new function is appended after existing validation code and does not touch `NutritionEngine`, `NutritionTargets`, or `validate_targets`.

LGTM — clean extraction with zero behaviour change; function is now available for reuse by any page that loads a profile.

---

**Open debt (declared in log, not yet done):**
- **FIX 3:** Surface daily water total in `pages/6_daily_menu.py` header. Confirmed still open — `grep water|hydration|WaterRepository pages/6_daily_menu.py` returns no matches.

---

## NEXT_PRIORITY

Batch these two items in one implementor session:

**1. Wire `bottom_nav()` on the 6 remaining stranded pages:**
`pages/0_profile.py`, `pages/4_inventory.py`, `pages/8_calendar.py`, `pages/7_weekly_workout_plan.py`, `pages/2_recipes.py`, `pages/13_meal_preferences.py`

Each requires adding `from ui.components import bottom_nav` (if not already imported) and a single `bottom_nav("<key>")` call before any `st.stop()`. Suggested active keys: `"profile"`, `"log"`, `"home"`, `"workout"`, `"home"`, `"home"`. Acceptance criterion: `grep -l bottom_nav pages/0_profile.py pages/4_inventory.py pages/8_calendar.py pages/7_weekly_workout_plan.py pages/2_recipes.py pages/13_meal_preferences.py` returns all 6 files.

**2. Close FIX 3:** Add a water-total widget to the header section of `pages/6_daily_menu.py`. Pattern: instantiate `WaterRepository`, call `.get_daily_total(user_id, today)`, render as a small metric alongside the existing macro summary. Acceptance criterion: `grep WaterRepository pages/6_daily_menu.py` returns a match.

**Reason:** Item 1 is the highest-impact UX gap still open — users on profile, inventory, calendar, and recipe pages have no navigation path to any other screen without the hidden sidebar. Dead-end pages hurt retention directly. Item 2 closes declared debt from the hydration feature cycle. Both are S-tier effort.

After this batch: sweep `layout="wide"` → `layout="centered"` across ALL remaining pages — use the full list of 15 pages with `layout="wide"` found in this audit, not just the 10 listed in design_brief Item 5.
