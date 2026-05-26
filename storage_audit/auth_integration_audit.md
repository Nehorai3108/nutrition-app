# Auth Integration Audit — BiteFit Supabase Login

**Date of audit:** 2026-05-11  
**Scope:** Read-only analysis of entire Python codebase to identify every place "current user" is implicitly assumed, in preparation for wiring `st.session_state["user_id"]` (Supabase) cleanly.

---

## 1. Login Gate Placement

### The existing `require_auth()` machinery (ui/user_auth.py)

`ui/user_auth.py` already contains a fully-implemented `require_auth()` function with the st.stop() pattern. It:

1. Checks `is_supabase_configured()` — if Supabase secrets are absent, immediately returns `"ui_user_001"` (local dev bypass).
2. If Supabase IS configured and the user is not in session, renders the full login/signup UI and calls `st.stop()`.
3. Returns `get_user_id()` on success → the Supabase UUID string.

**Problem:** `app_user.py` (the main entry point / home page) NEVER calls `require_auth()`. It hard-codes `"ui_user_001"` directly at module load time (lines 114, 129, 236, etc.). All sub-pages that do call `require_auth()` get the correct flow, but the home page does not.

### Where the login gate must be inserted in app_user.py

| File | Approximate line | What must happen |
|------|-----------------|-----------------|
| `app_user.py` | After `inject_global_css()` (~line 56) and before any repository access (~line 113) | Add `from ui.user_auth import require_auth, logout_button` then call `_USER_ID = require_auth()` |
| `app_user.py` sidebar block | ~line 160 (inside `with st.sidebar:`) | Add `logout_button()` call after the navigation links |

### Suggested gate structure for app_user.py

```python
# Place immediately after inject_global_css(), before any repo calls (~line 57)
from ui.user_auth import require_auth, logout_button
_USER_ID = require_auth()   # stops page if not logged in

# Then replace every hard-coded "ui_user_001" in this file with _USER_ID
```

### Pages that already have the gate correctly

| Page file | Line where require_auth() is called |
|-----------|-------------------------------------|
| `pages/0_profile.py` | 26 |
| `pages/6_daily_menu.py` | 26 |
| `pages/7_workout_tracker.py` | 28 |
| `pages/8_calendar.py` | 35 |
| `pages/9_history.py` | 55 |
| `pages/10_chat_log.py` | 71 |

### Pages MISSING the gate (no require_auth() call at all)

| Page file | Notes |
|-----------|-------|
| `app_user.py` | Main home page — highest priority fix |
| `pages/2_receipt_scanner.py` | Stores scanned inventory to session_state only (no repo writes), but should still be gated |
| `pages/2_recipes.py` | No user-specific repo calls found, but should be gated for consistency |
| `pages/3_recipe_detail.py` | No user-specific repo calls found, should be gated |
| `pages/4_inventory.py` | Uses a sidebar user-selector (multi-user admin mode), not a user gate |
| `pages/5_scanner.py` | Stores OCR key in session only, no repo calls, but should be gated |
| `pages/7_weekly_workout_plan.py` | **Critical**: calls WorkoutRepository with hard-coded USER_ID (see section 3) |

---

## 2. session_state Keys Today

| Key | Where set | Where read | Notes |
|-----|-----------|------------|-------|
| `"bitefit_user"` | `ui/user_auth.py:57,76` (on login/signup) | `pages/0_profile.py:23`, `pages/6_daily_menu.py:39`, `pages/7_workout_tracker.py:25`, `pages/8_calendar.py:32`, `pages/9_history.py:23`, `pages/10_chat_log.py:26` | Dict `{"id": UUID, "email": str}`. Central auth token. |
| `"bitefit_session"` | `ui/user_auth.py:58,77` (on login/signup) | Not read elsewhere in pages | Supabase session object — stored but currently unused after login |
| `"last_plan"` | `app_user.py:987` (after pipeline run) | `app_user.py:1019,1022`, `pages/6_daily_menu.py:109,111,112`, `chatbot/tools.py:250,257,369,379,405,412,471` | The generated meal plan + targets dict. Not user-scoped — single slot per browser session |
| `"scanned_inventory"` | `pages/2_receipt_scanner.py:177,335`, `pages/5_scanner.py:203` | `app_user.py:130`, `pages/2_receipt_scanner.py:175,331,341,358`, `pages/5_scanner.py:208,209,225,230` | Map of `food_id -> quantity_g` from scanner. Not user-scoped. |
| `"scan_results"` | `pages/2_receipt_scanner.py:175,241,336`, `pages/5_scanner.py:203,225` | `pages/2_receipt_scanner.py:249`, `pages/5_scanner.py:208,209,229,230,260` | Intermediate OCR results. Not user-scoped. |
| `"chat_messages"` | `chatbot/sidebar_widget.py:26`, `pages/10_chat_log.py:372` | `chatbot/sidebar_widget.py:31,41,45,93,115,126`, `pages/10_chat_log.py:395,466,509,558,582,587,589,590` | Chat history. Not user-scoped — shared across all users in same session. |
| `"groq_history"` | `pages/10_chat_log.py:373` | `pages/10_chat_log.py:471,482,484,583,590` | Groq API conversation history. Not user-scoped. |
| `"pending_entries"` | `pages/10_chat_log.py:374` | `pages/10_chat_log.py:472,498,514,533,558,561,572,579,580,587` | Parsed food entries awaiting confirmation. Not user-scoped. |
| `"detected_meal"` | `pages/10_chat_log.py:375` | `pages/10_chat_log.py:489,528,529` | Detected meal type from chat. Not user-scoped. |
| `"_last_chat_error"` | `pages/10_chat_log.py:478,505` | `pages/10_chat_log.py:596,598,600` | Debug error display. Not user-scoped. |
| `"chatbot_catalog"` | `chatbot/tools.py:173` | `chatbot/tools.py:172,174` | Cached FoodCatalog instance. Shared — OK (no user data). |
| `"chatbot_inventory_mgr"` | `chatbot/tools.py:179` | `chatbot/tools.py:178,180` | Cached InventoryManager. Currently uses hard-coded user ID inside tool functions. |
| `"skipped_workouts_today"` | `app_user.py:305` | `app_user.py:303` | Set of skipped workout indices. Not user-scoped. |
| `f"edit_{workout_idx}"` (dynamic) | `app_user.py:298,348,352` | `app_user.py:286` | Per-workout edit toggle. Not user-scoped. |
| `f"sadded_{meal}_{food_id}"` (dynamic) | `pages/6_daily_menu.py:321` | `pages/6_daily_menu.py:302` | Per-food "added" flag in plan section. Not user-scoped. |
| `f"added_{meal}_{food_id}"` (dynamic) | `pages/6_daily_menu.py:666` | `pages/6_daily_menu.py:641` | Per-food "added" flag in recipe section. Not user-scoped. |
| `"ocr_space_key"` | `pages/5_scanner.py:129,138` | `pages/5_scanner.py:134,140,193` | OCR API key. Not user-scoped. |
| `"selected_date"` | `pages/8_calendar.py:143` | `pages/8_calendar.py:149` | Selected calendar date. Not user-scoped. |
| `"calendar_month"` | `pages/8_calendar.py:56,66` | `pages/8_calendar.py:54` | Calendar navigation state. Not user-scoped. |
| `"calendar_year"` | `pages/8_calendar.py:61,67` | `pages/8_calendar.py:59` | Calendar navigation state. Not user-scoped. |
| `"mode"` | `pages/9_history.py:142,146` | `pages/9_history.py:101` | History vs plan view mode. Not user-scoped. |
| `"woff"` | `pages/9_history.py:153,158` | `pages/9_history.py:102` | Week offset for history pagination. Not user-scoped. |
| `"sel_day"` | `pages/9_history.py:116,201` | `pages/9_history.py:103` | Selected day in history. Not user-scoped. |
| `"weekly_edit"` | `pages/7_weekly_workout_plan.py:103` | `pages/7_weekly_workout_plan.py:124,228,233,237` | Weekly workout plan edit buffer. Not user-scoped. |
| `"is_admin"` | `ui/auth.py:42` | `ui/auth.py:21` | Admin authentication flag. Separate from user auth. |
| `"orc"` | `pages_admin/1_agents_dashboard.py:133` | `pages_admin/1_agents_dashboard.py:137` | Admin: AutonomyOrchestrator instance. |
| `"cycles"` | `pages_admin/1_agents_dashboard.py:134,280` | `pages_admin/1_agents_dashboard.py:397` | Admin: cycle run results. |
| `"run_count"` | `pages_admin/1_agents_dashboard.py:135,146` | `pages_admin/1_agents_dashboard.py:145` | Admin: run counter. |
| `"director_report"` | `pages_admin/1_agents_dashboard.py:647` | `pages_admin/1_agents_dashboard.py:649` | Admin: director analysis result. |
| `"critic_verdicts"` | `pages_admin/1_agents_dashboard.py:688` | `pages_admin/1_agents_dashboard.py:690` | Admin: critic verdicts. |
| `"selected_user_id"` | `pages/4_inventory.py:48` (selectbox key) | `pages/4_inventory.py:44,80,84,91,125,143,185,192` | Admin/inventory: which user's inventory is shown. |

---

## 3. Repository Call Sites

Every call site where a `user_id` string is passed to a repository method. After the refactor, every call using a hard-coded ID must instead use `st.session_state["bitefit_user"]["id"]` (or the local-dev fallback `"ui_user_001"` via `require_auth()` / `get_user_id()`).

### app_user.py — hard-coded "ui_user_001" throughout

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `app_user.py` | 114 | `_profile_repo.load("ui_user_001")` | `_USER_ID` (from `require_auth()` at top) |
| `app_user.py` | 129 | `_load_inv("ui_user_001")` | `_USER_ID` |
| `app_user.py` | 236 | `_workout_repo.get_workout_data("ui_user_001")` | `_USER_ID` |
| `app_user.py` | 262 | `_workout_repo.remove_daily_workout("ui_user_001", ...)` | `_USER_ID` |
| `app_user.py` | 265 | `_workout_repo.clear_daily_workouts("ui_user_001", ...)` | `_USER_ID` |
| `app_user.py` | 293 | `_workout_repo.add_daily_workout("ui_user_001", ...)` | `_USER_ID` |
| `app_user.py` | 347 | `_workout_repo.add_daily_workout("ui_user_001", ...)` | `_USER_ID` |
| `app_user.py` | 427 | `_workout_repo.add_daily_workout("ui_user_001", ...)` | `_USER_ID` |
| `app_user.py` | 440 | `_WATER_USER_ID = "ui_user_001"` (all water calls follow) | Replace constant with `_USER_ID` |
| `app_user.py` | 442 | `water_repo.get_water_data(_WATER_USER_ID)` | via `_USER_ID` |
| `app_user.py` | 443 | `water_repo.get_water_intakes_for_date(_WATER_USER_ID, ...)` | via `_USER_ID` |
| `app_user.py` | 464 | `water_repo.add_water_intake(_WATER_USER_ID, ...)` | via `_USER_ID` |
| `app_user.py` | 469 | `water_repo.add_water_intake(_WATER_USER_ID, ...)` | via `_USER_ID` |
| `app_user.py` | 474 | `water_repo.add_water_intake(_WATER_USER_ID, ...)` | via `_USER_ID` |
| `app_user.py` | 479 | `water_repo.add_water_intake(_WATER_USER_ID, ...)` | via `_USER_ID` |
| `app_user.py` | 496 | `water_repo.add_water_intake(_WATER_USER_ID, ...)` | via `_USER_ID` |
| `app_user.py` | 520 | `water_repo.save_water_goal(_WATER_USER_ID, ...)` | via `_USER_ID` |
| `app_user.py` | 552 | `_DASH_USER = "ui_user_001"` (all dashboard calls follow) | Replace constant with `_USER_ID` |
| `app_user.py` | 561 | `_summary_repo.get(_DASH_USER, today)` | via `_USER_ID` |
| `app_user.py` | 562 | `_water_repo_db.get_water_intakes_for_date(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 563 | `_water_repo_db.get_water_goal(_DASH_USER)` | via `_USER_ID` |
| `app_user.py` | 564 | `_workout_repo_db.get_workout_data(_DASH_USER)` | via `_USER_ID` |
| `app_user.py` | 566 | `_food_log_repo.get_totals(_DASH_USER, today)` | via `_USER_ID` |
| `app_user.py` | 567 | `_food_log_repo.get_log(_DASH_USER, today)` | via `_USER_ID` |
| `app_user.py` | 795 | `_water_repo_home.add_water_intake(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 798 | `_water_repo_home.add_water_intake(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 801 | `_water_repo_home.add_water_intake(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 804 | `_water_repo_home.add_water_intake(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 808 | `_water_repo_home.get_water_intakes_for_date(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 827 | `_water_repo_home.remove_water_intake(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 829 | `_water_repo_home.add_water_intake(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 832 | `_water_repo_home.remove_water_intake(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 841 | `_food_log_repo.get_log(_DASH_USER, today)` | via `_USER_ID` |
| `app_user.py` | 876 | `_food_log_repo.remove_entry(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 880 | `_food_log_repo.add_entry(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 894 | `_food_log_repo.add_entry(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 905 | `_food_log_repo.remove_entry(_DASH_USER, ...)` | via `_USER_ID` |
| `app_user.py` | 929 | `UserProfile(user_id="ui_user_001", ...)` | `_USER_ID` |
| `app_user.py` | 948 | `workout_repo.resolve_workouts_for_date(user.user_id, ...)` | via `user.user_id`, which is set from `_USER_ID` at line 929 — fix line 929 and this follows |
| `app_user.py` | 1002 | `DailySummaryRepository().save(DailySummary(user_id=user.user_id, ...))` | via `user.user_id` — cascades from line 929 fix |

### pages/0_profile.py — already uses require_auth()

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `pages/0_profile.py` | 27–28 | `ProfileRepository(); repo.load(USER_ID)` | `USER_ID` already comes from `require_auth()` at line 26 — correct |
| `pages/0_profile.py` | 174 | `UserProfile(user_id=USER_ID, ...)` | Already correct |
| `pages/0_profile.py` | 359 | (profile save with `user_id=USER_ID`) | Already correct |

### pages/6_daily_menu.py — already uses require_auth()

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `pages/6_daily_menu.py` | 27 | `FoodLogRepository()` instantiation | n/a |
| `pages/6_daily_menu.py` | 30–31 | `ProfileRepository(); _profile_repo.load(USER_ID)` | `USER_ID` from `require_auth()` at line 26 — correct |
| `pages/6_daily_menu.py` | 312 | `_food_log_repo.add_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 507 | `_food_log_repo.add_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 522 | `_food_log_repo.get_log(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 566 | `_food_log_repo.remove_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 570 | `_food_log_repo.add_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 582 | `_food_log_repo.remove_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 655 | `_food_log_repo.add_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 858 | `_food_log_repo.add_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 886 | `_food_log_repo.add_entry(USER_ID, ...)` | Correct |
| `pages/6_daily_menu.py` | 901 | `_food_log_repo.get_log(USER_ID, ...)` | Correct |

### pages/7_workout_tracker.py — already uses require_auth()

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `pages/7_workout_tracker.py` | 29 | `WorkoutRepository()` instantiation | n/a |
| `pages/7_workout_tracker.py` | 32 | `ProfileRepository().load(USER_ID)` | `USER_ID` from `require_auth()` at line 28 — correct |
| `pages/7_workout_tracker.py` | 57 | `_repo.get_workout_data(USER_ID)` | Correct |
| `pages/7_workout_tracker.py` | 139 | `_repo.remove_daily_workout(USER_ID, ...)` | Correct |
| `pages/7_workout_tracker.py` | 143 | `_repo.add_daily_workout(USER_ID, ...)` | Correct |
| `pages/7_workout_tracker.py` | 146 | `_repo.remove_daily_workout(USER_ID, ...)` | Correct |
| `pages/7_workout_tracker.py` | 188 | `_repo.add_daily_workout(USER_ID, ...)` | Correct |

### pages/7_weekly_workout_plan.py — MISSING require_auth(), hard-coded ID

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `pages/7_weekly_workout_plan.py` | 35 | `USER_ID = "ui_user_001"` hard-coded constant | Replace with `USER_ID = require_auth()` |
| `pages/7_weekly_workout_plan.py` | 98 | `repo = WorkoutRepository()` instantiation | n/a |
| `pages/7_weekly_workout_plan.py` | 102 | `repo.get_workout_data(USER_ID)` | Fix line 35 first |
| `pages/7_weekly_workout_plan.py` | 225 | `WeeklyWorkoutPlan(user_id=USER_ID, ...)` | Fix line 35 first |
| `pages/7_weekly_workout_plan.py` | 232 | `repo.save_weekly_plan(USER_ID, plan)` | Fix line 35 first |
| `pages/7_weekly_workout_plan.py` | 238 | `repo.save_weekly_plan(USER_ID, WeeklyWorkoutPlan(user_id=USER_ID, ...))` | Fix line 35 first |

### pages/8_calendar.py — already uses require_auth()

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `pages/8_calendar.py` | 46 | `WorkoutRepository()` instantiation | n/a |
| `pages/8_calendar.py` | 47 | `WaterRepository()` instantiation | n/a |
| `pages/8_calendar.py` | 76 | `workout_repo.resolve_workouts_for_date(USER_ID, ...)` | `USER_ID` from `require_auth()` at line 35 — correct |
| `pages/8_calendar.py` | 77 | `water_repo.get_water_intakes_for_date(USER_ID, ...)` | Correct |
| `pages/8_calendar.py` | 79 | `water_repo.get_water_goal(USER_ID)` | Correct |

### pages/9_history.py — already uses require_auth()

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `pages/9_history.py` | 56–58 | `WorkoutRepository()`, `WaterRepository()`, `FoodLogRepository()` | n/a |
| `pages/9_history.py` | 67 | `PLAN_FILE = PLANS_DIR / f"{USER_ID}.json"` | `USER_ID` from `require_auth()` at line 55 — correct |
| `pages/9_history.py` | 120 | `workout_repo.get_workout_data(USER_ID)` | Correct |
| `pages/9_history.py` | 123 | `food_repo.get_totals(USER_ID, d)` | Correct |
| `pages/9_history.py` | 124 | `water_repo.get_water_intakes_for_date(USER_ID, d)` | Correct |
| `pages/9_history.py` | 244 | `food_repo.get_log(USER_ID, sel_date)` | Correct |
| `pages/9_history.py` | 245 | `food_repo.get_totals(USER_ID, sel_date)` | Correct |
| `pages/9_history.py` | 278 | `water_repo.get_water_intakes_for_date(USER_ID, sel_date)` | Correct |

### pages/10_chat_log.py — already uses require_auth()

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `pages/10_chat_log.py` | 70 | `FoodLogRepository()` instantiation | n/a |
| `pages/10_chat_log.py` | 573 | `food_log_repo.add_entry(USER_ID, ...)` | `USER_ID` from `require_auth()` at line 71 — correct |

### chatbot/tools.py — hard-coded "ui_user_001" throughout

| File | Line | Method called | Suggested user_id source |
|------|------|--------------|--------------------------|
| `chatbot/tools.py` | 424 | `mgr.get_state("ui_user_001")` | `get_user_id()` from `ui.user_auth` |
| `chatbot/tools.py` | 453 | `mgr.add_item("ui_user_001", ...)` | `get_user_id()` |
| `chatbot/tools.py` | 455 | `mgr.remove_item("ui_user_001", ...)` | `get_user_id()` |
| `chatbot/tools.py` | 458 | `mgr.get_state("ui_user_001")` | `get_user_id()` |
| `chatbot/tools.py` | 461 | `mgr.remove_item("ui_user_001", ...)` | `get_user_id()` |
| `chatbot/tools.py` | 463 | `mgr.add_item("ui_user_001", ...)` | `get_user_id()` |
| `chatbot/tools.py` | 490 | `mgr.get_state("ui_user_001")` | `get_user_id()` |

### pages/4_inventory.py — multi-user admin page (intentional)

| File | Line | Method called | Notes |
|------|------|--------------|-------|
| `pages/4_inventory.py` | 91 | `load_inventory(selected_id)` | `selected_id` comes from a sidebar selectbox — this is intentional multi-user admin |
| `pages/4_inventory.py` | 125,143 | `add_inventory_item(selected_id, ...)` | Admin — intentional |
| `pages/4_inventory.py` | 185 | `update_inventory_item(selected_id, ...)` | Admin — intentional |
| `pages/4_inventory.py` | 192 | `remove_inventory_item(selected_id, ...)` | Admin — intentional |

This page should remain admin-only. Consider adding `require_admin()` from `ui/auth.py` to it.

---

## 4. Existing Profile Flow

### How it works today

1. **app_user.py (home page)** loads the profile at module level with `_profile_repo.load("ui_user_001")` (line 114). The result is unpacked into module-level variables: `name`, `gender_choice`, `height`, `weight`, `dob`, `activity_choice`, `goal_choice`. These variables feed the meal plan generation pipeline. Because this runs at module scope (not inside a function), the profile loads once when the page first renders and is not user-keyed.

2. **pages/0_profile.py** is the dedicated profile editing page. It correctly calls `USER_ID = require_auth()` (line 26), then `repo.load(USER_ID)` (line 28). It presents three tabs (personal details, food preferences, targets) and saves via `repo.save(profile_dict)` which routes to Supabase (if configured) or a local JSON file at `storage_agents/profiles/{user_id}.json`.

3. **ProfileRepository** auto-detects the backend:
   - If `is_supabase_configured()` → reads/writes to Supabase `profiles` table, keyed by `user_id`.
   - Otherwise → reads/writes `storage_agents/profiles/{user_id}.json`.

4. The "who is the user" question is answered differently depending on the page:
   - Profile page and most sub-pages: `USER_ID = require_auth()` → correct Supabase UUID or `"ui_user_001"`.
   - **Home page (app_user.py): always `"ui_user_001"` — broken for multi-user.**

### What must change

- In `app_user.py`, add `_USER_ID = require_auth()` near the top (after `inject_global_css()`).
- Move the profile load (`_profile_repo.load(...)`) to after `_USER_ID` is resolved, inside the page body or inside `@st.cache_data` keyed by user_id.
- The `UserProfile` object constructed at line 929 (`user_id="ui_user_001"`) must use `_USER_ID` instead. This is the object passed to `DailySummaryRepository().save(...)` at line 1002, so fixing line 929 fixes the chain.
- The `chatbot/tools.py` functions receive no user context — they need to call `get_user_id()` from `ui.user_auth` at call time (not at module import time, since the user may not be logged in yet).

---

## 5. Hardcoded User References

Every location where `"ui_user_001"` or equivalent is hard-coded in production code paths (not test files):

| File | Line | Hard-coded value | Context |
|------|------|-----------------|---------|
| `app_user.py` | 114 | `"ui_user_001"` | Profile load at module scope |
| `app_user.py` | 129 | `"ui_user_001"` | Inventory load at module scope |
| `app_user.py` | 236 | `"ui_user_001"` | Workout data fetch in sidebar |
| `app_user.py` | 262 | `"ui_user_001"` | Remove workout in sidebar |
| `app_user.py` | 265 | `"ui_user_001"` | Clear workouts in sidebar |
| `app_user.py` | 293 | `"ui_user_001"` | Add workout (weekly plan copy) in sidebar |
| `app_user.py` | 347 | `"ui_user_001"` | Add workout (edit) in sidebar |
| `app_user.py` | 427 | `"ui_user_001"` | Add workout (new) in sidebar |
| `app_user.py` | 440 | `"ui_user_001"` | `_WATER_USER_ID` constant in water section |
| `app_user.py` | 552 | `"ui_user_001"` | `_DASH_USER` constant in dashboard section |
| `app_user.py` | 929 | `"ui_user_001"` | `UserProfile(user_id=...)` in pipeline |
| `chatbot/tools.py` | 424 | `"ui_user_001"` | `_get_inventory()` tool |
| `chatbot/tools.py` | 453 | `"ui_user_001"` | `_update_inventory()` — add action |
| `chatbot/tools.py` | 455 | `"ui_user_001"` | `_update_inventory()` — remove action |
| `chatbot/tools.py` | 458 | `"ui_user_001"` | `_update_inventory()` — set_quantity action |
| `chatbot/tools.py` | 461 | `"ui_user_001"` | `_update_inventory()` — set_quantity remove |
| `chatbot/tools.py` | 463 | `"ui_user_001"` | `_update_inventory()` — set_quantity add |
| `chatbot/tools.py` | 490 | `"ui_user_001"` | `_generate_new_meal_plan()` — inventory state |
| `pages/7_weekly_workout_plan.py` | 35 | `"ui_user_001"` | Module-level `USER_ID` constant |
| `nutrition_app/repositories/profile_repository.py` | 12 | `"ui_user_001"` | Default value in `_DEFAULTS` dict (used when creating a blank profile) |
| `ui/user_auth.py` | 25 | `"ui_user_001"` | `get_user_id()` fallback for local dev (intentional) |
| `ui/user_auth.py` | 40 | `"ui_user_001"` | `require_auth()` fallback when Supabase not configured (intentional) |

### Intentional vs. must-fix

- `ui/user_auth.py` lines 25 and 40: **Intentional** — these are the canonical local-dev fallback. Do not change.
- `nutrition_app/repositories/profile_repository.py` line 12: **Low risk** — this is a default dict used only when a profile does not exist yet. The actual `user_id` is overwritten with the passed argument in `_local_load()`. Acceptable to leave as is.
- All other entries above: **Must be replaced** with `_USER_ID` / `get_user_id()` as noted in section 3.

---

## Summary of Required Changes by Priority

| Priority | File | Action |
|----------|------|--------|
| 1 (critical) | `app_user.py` | Add `require_auth()` call near top; replace all 13 occurrences of `"ui_user_001"` with `_USER_ID` |
| 2 (critical) | `pages/7_weekly_workout_plan.py` | Replace hard-coded `USER_ID = "ui_user_001"` with `USER_ID = require_auth()` |
| 3 (high) | `chatbot/tools.py` | Replace all 7 hard-coded `"ui_user_001"` strings with `from ui.user_auth import get_user_id; get_user_id()` called at runtime |
| 4 (medium) | `pages/2_receipt_scanner.py` | Add `require_auth()` gate so unauthenticated users cannot reach scanner |
| 5 (medium) | `pages/4_inventory.py` | Add `require_admin()` gate; the per-user selectbox is intentional and fine |
| 6 (low) | `pages/2_recipes.py`, `pages/3_recipe_detail.py`, `pages/5_scanner.py` | Add `require_auth()` gate for consistency even if no direct repo calls |
