# Audit — Multi-User Demo Readiness (target: Friday May 15, 2026)

Each finding has a self-contained **Prompt for Claude Code** at the bottom. Paste it as-is into Claude Code; no extra context required.

---

## User-reported issues

### [BLOCKER 1] All users see "Dvir Yona" data because user_id falls back to a hardcoded constant

**What's broken:** `app_user.py:82` resolves `_USER_ID` with `st.session_state.get("user_id", "ui_user_001")`. When Supabase is not configured OR when session_state hasn't been populated yet, every visitor is treated as the user `ui_user_001`, whose profile JSON is "דביר יונה". Profile, inventory, workouts, water, food log, daily summary, and dashboard all key off this same `_USER_ID`.

**Where:**
- `app_user.py:82` — `_USER_ID: str = st.session_state.get("user_id", "ui_user_001")`
- `ui/user_auth.py:25, 40` — `return "ui_user_001"`
- `nutrition_app/repositories/profile_repository.py:12` — `_DEFAULTS["user_id"] = "ui_user_001"`
- Seed file: `storage_agents/profiles/ui_user_001.json` (line 3: `"name": "דביר יונה"`)

**Prompt for Claude Code:**
> The Streamlit nutrition app at `C:\Users\User\Desktop\אפליקציית תזונאי` has a hard-coded fallback `user_id = "ui_user_001"` that takes effect whenever Supabase auth is missing or session_state is empty. Every page and every repository (`ProfileRepository`, `WorkoutRepository`, `WaterRepository`, `DailySummaryRepository`, `FoodLogRepository`, `InventoryManager`) ends up reading the data belonging to the seed user "דביר יונה" instead of the actual logged-in user. The fallback lives in `app_user.py` line 82, `ui/user_auth.py` lines 25 and 40, and `nutrition_app/repositories/profile_repository.py` line 12. Remove every hard-coded `"ui_user_001"` from production code paths and replace it with a strict authenticated user id obtained from the active Supabase session; when no authenticated user exists, the app must render the login screen and stop, never silently impersonate the seed user. Also delete or rename the seed profile file `storage_agents/profiles/ui_user_001.json` so it can never be reached. Verify by signing up two fresh users in two browsers and confirming each sees their own (empty) dashboard.

---

### [BLOCKER 2] Sign-up does not create a profile row; new users land on a half-initialized dashboard with placeholder defaults

**What's broken:** `_do_signup` in `auth/login_ui.py` only calls `supabase.auth.sign_up({email, password})` and writes session_state — it never inserts a row into the `profiles` table. On first dashboard render, `ProfileRepository._sb_load(user_id)` returns None and the code falls through to `_DEFAULTS` (`"ישראל ישראלי"`, dob `1990-05-15`, height 178, weight 82). The dashboard then calculates BMR/TDEE based on those placeholder numbers and shows them as if they belong to the user. With Supabase's default "confirm email before issuing a session" behavior, `resp.session` is None on success, so subsequent RLS-protected queries fail silently and the user is stuck on the placeholder view.

**Where:**
- `auth/login_ui.py:50-64` — `_do_signup`
- `nutrition_app/repositories/profile_repository.py:11-28` — `_DEFAULTS`
- `app_user.py:142` — `_profile = _profile_repo.load(_USER_ID)` (fallthrough to defaults)
- `nutrition_app/db/schema.sql:30-47` — `profiles` table

**Prompt for Claude Code:**
> In `C:\Users\User\Desktop\אפליקציית תזונאי\auth\login_ui.py` the `_do_signup` function creates a Supabase auth user but never seeds a corresponding row in the application's `profiles` table (`nutrition_app/db/schema.sql` lines 30-47) or in any of the per-user data stores. The result is that a freshly-signed-up user lands on the home dashboard at `app_user.py` line 142 where `ProfileRepository.load()` returns the hard-coded `_DEFAULTS` dict (`profile_repository.py` lines 11-28) — they see a fake "ישראל ישראלי" placeholder profile and BMR/TDEE numbers calculated from defaults. Additionally, with Supabase's default email-confirmation flow, `resp.session` will be None for a freshly-registered user, so subsequent RLS-protected reads silently return empty. Make signup atomically: (a) create the auth user, (b) insert an initial `profiles` row for them, (c) redirect them to the profile-onboarding page so they fill in their real height/weight/dob/goal before the dashboard renders, and (d) handle the "email confirmation pending" case explicitly (either disable confirmation for the demo or show a clear "check your email" screen instead of letting them in). Also note that the `profiles` table in `schema.sql` is missing columns the code already writes (`date_of_birth`, `pace`, `weekly_change_kg`, `target_weight_kg`, `weeks_to_goal`, `meal_preferences` as JSON) — extend the schema.

---

### [BLOCKER 3] Bottom navigation bar uses raw HTML `<a href>` links that bypass Streamlit's internal router

**What's broken:** `bottom_nav` in `ui/components.py:614-651` builds the nav bar with raw HTML anchor tags (`<a href="/daily_menu">`) injected via `st.markdown(unsafe_allow_html=True)`. These are browser-native navigations, not `st.page_link` / `st.switch_page`. Clicking them causes a full page reload — drops in-memory state, can pop a new tab in some embeds, and re-runs the auth gate which then trips the `ui_user_001` fallback. Both user-reported symptoms ("opens in a new tab" + "shows Dvir's data") trace back here.

**Where:**
- `ui/components.py:614-651` — `bottom_nav`, specifically line 649: `html += f'<a href="{href}" class="{cls}">{SVG[key]}<span>{label}</span></a>'`
- Called from: `app_user.py:914`, `pages/6_daily_menu.py`, `pages/9_history.py`, `pages/10_chat_log.py`, `pages/7_workout_tracker.py`
- Contrast: `app_user.py:190-198` uses `st.page_link` correctly

**Prompt for Claude Code:**
> In `C:\Users\User\Desktop\אפליקציית תזונאי\ui\components.py` lines 614-651 the `bottom_nav` function renders a fixed bottom navigation bar using raw HTML `<a href="/...">` anchor tags via `st.markdown(unsafe_allow_html=True)`. This bypasses Streamlit's multipage router, causes a full page reload on every click, can pop a new tab depending on host, and on landing re-triggers `app_user.py`'s auth resolution which (due to a separate `ui_user_001` fallback bug) often surfaces the wrong user's data. The fix should preserve the existing visual design (fixed bottom bar, icons, active state) but use Streamlit's native page navigation (`st.page_link` with the page-file path, or `st.switch_page`) so clicks stay inside the same Streamlit session and use the router. The other in-page sidebar in the same app (`app_user.py` lines 190-198) already demonstrates the correct pattern with `st.page_link`. Verify the fix by clicking each bottom-nav item and confirming (1) the URL changes in-place without a full reload, (2) no new tab opens, (3) the logged-in user's session and data persist across the navigation.

---

### [BLOCKER 4] Inventory & Scanner pages let any visitor pick any user from a global dropdown

**What's broken:** `pages/4_inventory.py` does not call `require_auth()`. Instead, its sidebar loads ALL users from `storage_agents/users.json` via `get_all_users()` and presents them as a selectbox. Anyone — even unauthenticated — sees a list of every account and can pick any one to view, edit, add to, or delete the inventory of. Same pattern in `pages/5_scanner.py`. This is one of the root causes of "clicking a bottom-nav item takes me to Dvir's data".

**Where:**
- `pages/4_inventory.py:37-70` — sidebar user picker; body operates on `selected_id`
- `pages/5_scanner.py:108-122` plus calls to `add_inventory_item(selected_id, ...)` at lines 258 and 277

**Prompt for Claude Code:**
> `C:\Users\User\Desktop\אפליקציית תזונאי\pages\4_inventory.py` and `C:\Users\User\Desktop\אפליקציית תזונאי\pages\5_scanner.py` are designed around an older "nutritionist managing many clients" model — they load every account on the system via `get_all_users()` and expose a dropdown so any visitor can pick any user and read or modify that user's inventory, scan into it, or delete the account entirely. These pages have no `require_auth()` gate at all. Convert both pages to single-tenant pages that operate ONLY on the currently-logged-in user's id: add `from ui.user_auth import require_auth` and `USER_ID = require_auth()` at the top, remove the user-selector dropdown and the "create user / delete user" admin controls, and replace every use of `selected_id` with `USER_ID`. The "create user" flow belongs in the signup screen, not here. Confirm the page is unreachable when logged out and that user A cannot see user B's inventory.

---

## Multi-tenancy / data isolation

### [BLOCKER 5] Workout / water / daily-summary repositories only persist to local JSON; no Supabase backend

**What's broken:** Three of the user-data repositories — `WorkoutRepository`, `WaterRepository`, `DailySummaryRepository` — write exclusively to JSON files under `storage_agents/{workouts,water,daily_summaries}/{user_id}.json`. They have no Supabase code path even though `schema.sql` defines the tables with RLS. On Railway/Streamlit Cloud the local filesystem is ephemeral or shared; data evaporates on redeploy or collides under concurrent access.

**Where:**
- `nutrition_app/repositories/workout_repository.py` — no `_sb_*` methods anywhere
- `nutrition_app/repositories/water_repository.py` — same
- `nutrition_app/repositories/daily_summary_repository.py` — same
- Contrast: `food_log_repository.py` and `profile_repository.py` have dual backends

**Prompt for Claude Code:**
> The Streamlit app at `C:\Users\User\Desktop\אפליקציית תזונאי` persists most user data through repository classes in `nutrition_app/repositories/`. Two of them — `food_log_repository.py` and `profile_repository.py` — have dual backends (Supabase when configured, local JSON otherwise) and correctly filter/insert by `user_id`. The other three — `workout_repository.py`, `water_repository.py`, `daily_summary_repository.py` — only write to local JSON under `storage_agents/`. On a multi-user deployment (Railway / Streamlit Cloud) the local filesystem is ephemeral or shared, so this means workout history, water intake, and daily summaries either disappear on redeploy or are stored on a writable volume that breaks under concurrent access. The `nutrition_app/db/schema.sql` already defines `workouts`, `water_log`, and `water_goals` tables with row-level security. Add Supabase backends to all three repositories following the exact pattern used in `food_log_repository.py` (`_use_supabase()`, `_sb_*` methods, `.eq("user_id", user_id)` on every read, `user_id` stamped on every write). Verify that two demo users in two browsers see independent workout/water/summary data and that data survives a restart.

---

### [BLOCKER 6] Seed data ("Dvir Yona") checked into the repo

**What's broken:** The repo ships `storage_agents/profiles/ui_user_001.json` (Dvir Yona), `storage_agents/users.json` (two more "Dvir" accounts with ids `79b4fcd4` and `aa03b295`), and corresponding `workouts/`, `daily_summaries/`, `water/`, `inventories/` files keyed to those ids. On any deploy the seed data is present; combined with the `ui_user_001` fallback, first thing any visitor sees is Dvir's history.

**Where:**
- `storage_agents/profiles/ui_user_001.json`
- `storage_agents/users.json`
- `storage_agents/daily_summaries/ui_user_001.json`, `storage_agents/workouts/ui_user_001.json`, etc.

**Prompt for Claude Code:**
> The repository at `C:\Users\User\Desktop\אפליקציית תזונאי\storage_agents\` is checked in with personal seed data for the developer "Dvir Yona": `profiles/ui_user_001.json`, `users.json` (two more "Dvir" accounts), and matching `workouts/`, `daily_summaries/`, `water/`, `inventories/` files. The fallback `user_id = "ui_user_001"` in `app_user.py` and `ui/user_auth.py` will pick up this data for any visitor whose auth context can't be resolved. Wipe these seed files (or move them to a `seed_data/dev_only/` folder outside the runtime path) and add `storage_agents/profiles/`, `storage_agents/daily_summaries/`, `storage_agents/workouts/`, `storage_agents/water/`, `storage_agents/inventories/`, `storage_agents/food_log/`, `storage_agents/weekly_plans/`, and `storage_agents/users.json` to `.gitignore`. Confirm the runtime directories are created on demand (the existing code in each repo already does `os.makedirs(..., exist_ok=True)`).

---

## Auth & sign-up

### [BLOCKER 7] Supabase SERVICE key and admin password committed in `.streamlit/secrets.toml`

**What's broken:** `.streamlit/secrets.toml` contains `SUPABASE_SERVICE_KEY = "sb_secret_..."` (RLS-bypass key) and `admin_password = "dvir4331"`. If this file is in git history, the key is public. For a Friday demo where the URL goes out, this is critical.

**Where:** `.streamlit/secrets.toml`

**Prompt for Claude Code:**
> The file `C:\Users\User\Desktop\אפליקציית תזונאי\.streamlit\secrets.toml` contains an admin password and a Supabase SERVICE key (which bypasses Row-Level Security). Confirm whether this file is in git history (`git log --all -- .streamlit/secrets.toml`). If yes, rotate both the Supabase service key (Supabase dashboard → Project Settings → API → Reset service_role key) and the admin password immediately, and rewrite git history or accept the leak. Ensure `.streamlit/secrets.toml` is listed in `.gitignore`. For the demo deploy, secrets should be injected via the host's secret manager (Railway env vars, Streamlit Cloud secrets UI) — not committed. The application code reads from both env and `st.secrets`, so removing the file from the repo and providing the values via env will not break local development if a developer maintains a local-only copy.

---

### [MAJOR 8] Two competing auth modules disagree about login state

**What's broken:** `ui/user_auth.py` (used by every sub-page) falls back to `"ui_user_001"` when Supabase isn't configured. `auth/login_ui.py` (used by `app_user.py`) has no fallback. They share session-state keys but disagree on behavior. Two `is_supabase_configured()` implementations exist (`auth/supabase_client.py` reads env+secrets, `nutrition_app/db/supabase_client.py` reads only secrets) and can disagree.

**Where:**
- `ui/user_auth.py` (whole file)
- `auth/login_ui.py` (whole file)
- `auth/supabase_client.py:36-48` vs `nutrition_app/db/supabase_client.py:18-26`

**Prompt for Claude Code:**
> The app at `C:\Users\User\Desktop\אפליקציית תזונאי` has two parallel authentication implementations that share session-state keys but disagree on behavior: `ui/user_auth.py` (older — used by every page in `pages/`) and `auth/login_ui.py` (newer — used only by `app_user.py`). Each also has its own `is_supabase_configured()` (in `auth/supabase_client.py` vs `nutrition_app/db/supabase_client.py`) with different credential sources. The result is that the home page and the subpages can disagree about whether a user is logged in and what their id is. Consolidate to a single auth module and a single Supabase client. Pick one source of truth for credentials (env + secrets, in that order), one session_state key shape (recommend `user_id` and `user_email`), one `require_auth()` entry point that every page calls including `app_user.py`, and delete the duplicate. Update every page that imports from the deprecated module. Verify by signing in once and confirming every page recognizes the same user without falling back.

---

### [MAJOR 9] Sign-up succeeds but Supabase session is None when email confirmation is enabled

**What's broken:** `_set_session` writes `user_id` to session_state even when `resp.session` is None (Supabase's default response when email confirmation is required). The app proceeds past the auth gate, but every RLS-protected query silently returns empty. The user has no idea why their data won't save.

**Where:** `auth/login_ui.py:21-28` (`_set_session`), `50-57` (`_do_signup`)

**Prompt for Claude Code:**
> In `C:\Users\User\Desktop\אפליקציית תזונאי\auth\login_ui.py` the `_do_signup` flow writes the user to session_state as soon as `resp.user` is present, even when `resp.session` is None (which is what Supabase returns when email confirmation is required). The user appears authenticated to the app but Supabase RLS-protected queries silently return empty results because `auth.uid()` is null on the server side. Decide on one of two policies for the demo: (1) disable email confirmation in the Supabase project settings, OR (2) treat a None session as a pending state — do not write `user_id` to session_state, show a "check your email to confirm" screen, and only enter the app after the confirmation link is clicked (re-fetch session via `get_supabase().auth.get_session()` on every page load). Same applies to the signup branch when the user already exists but isn't confirmed.

---

### [MAJOR 10] Supabase `profiles` schema is missing columns the application writes

**What's broken:** The code writes `meal_preferences`, `date_of_birth`, `pace`, `weekly_change_kg`, `target_weight_kg`, `weeks_to_goal`. None of those columns exist in `schema.sql`. Profile saves silently drop half the data or error out.

**Where:**
- Schema: `nutrition_app/db/schema.sql:30-47`
- Writer: `nutrition_app/repositories/profile_repository.py:84-97`
- Readers: `app_user.py:610-617`, `pages/0_profile.py:91, 149, 372`

**Prompt for Claude Code:**
> The Supabase `profiles` schema in `C:\Users\User\Desktop\אפליקציית תזונאי\nutrition_app\db\schema.sql` lines 30-47 is missing columns that the application reads and writes: `date_of_birth`, `pace`, `weekly_change_kg`, `target_weight_kg`, `weeks_to_goal`, `meal_preferences` (stored as a JSON text). When a user saves their profile via `pages/0_profile.py`, the upsert in `ProfileRepository._sb_save` (`nutrition_app/repositories/profile_repository.py` lines 84-97) either errors out or silently drops the extra fields, depending on the Supabase REST behavior. Extend the schema with the missing columns (`date_of_birth DATE`, `pace TEXT`, `weekly_change_kg FLOAT`, `target_weight_kg FLOAT`, `weeks_to_goal INT`, `meal_preferences JSONB`), update `_sb_save` and `_sb_load` to include them, and verify that a round-trip "save profile → reload page" preserves every field. Include a migration script that adds the columns to any existing Supabase project.

---

### [MAJOR 11] `app_user.py` silently falls through to seed user when Supabase isn't configured

**What's broken:** `app_user.py:70` only renders the login UI when `is_supabase_configured()` is true. If the configuration check fails (env not loaded on the host), the app silently grants access as `"ui_user_001"`. A misconfigured deploy doesn't fail loud — it just shows everyone Dvir's data.

**Where:** `app_user.py:70-82`

**Prompt for Claude Code:**
> In `C:\Users\User\Desktop\אפליקציית תזונאי\app_user.py` line 70, the auth gate only fires when `is_supabase_configured()` is true. When Supabase credentials are missing (env not loaded, `.streamlit/secrets.toml` not present on the host), the app silently falls back to `_USER_ID = "ui_user_001"` and shows everyone the seed user's data. For a multi-user demo, make Supabase configuration mandatory: if `is_supabase_configured()` returns false, render an error screen ("Server misconfigured — please contact support") and `st.stop()` instead of falling through. Remove the local-dev fallback entirely from production paths.

---

### [MAJOR 12] No password-reset / forgot-password flow

**What's broken:** No code anywhere matches `reset_password`, `forgot.password`, or `send.*reset`. If a demo user mistypes during signup they're locked out.

**Where:** Absent. Belongs in `auth/login_ui.py`.

**Prompt for Claude Code:**
> The Streamlit nutrition app at `C:\Users\User\Desktop\אפליקציית תזונאי` has no password-reset flow. Add a "forgot password" link on the login form in `auth/login_ui.py` that calls `supabase.auth.reset_password_for_email(email)` and shows a "check your inbox" confirmation. Also add a screen that handles the Supabase recovery redirect (the link in the email lands on a URL with a `type=recovery` token — Streamlit needs to read it from the query params and prompt for a new password via `supabase.auth.update_user({password: new_pw})`). For the Friday demo the minimum is the "send reset email" button; the full recovery landing page can be deferred if the demo flow is "we pre-seed your account, here is your password".

---

## Other / Major

### [MAJOR 13] Five `pages/` files have no `require_auth()` gate

**What's broken:** `pages/2_recipes.py`, `2_receipt_scanner.py`, `3_recipe_detail.py`, `4_inventory.py`, `5_scanner.py` import zero auth helpers. Direct-URL access works while logged out.

**Prompt for Claude Code:**
> In `C:\Users\User\Desktop\אפליקציית תזונאי\pages\` the files `2_recipes.py`, `2_receipt_scanner.py`, `3_recipe_detail.py`, `4_inventory.py`, and `5_scanner.py` do not gate access behind authentication — they import zero auth helpers and can be loaded by anyone with the URL. Add the same `from ui.user_auth import require_auth, logout_button` import and `USER_ID = require_auth()` (called before any data access) that the other pages use (`0_profile.py`, `6_daily_menu.py`, `7_workout_tracker.py`, `7_weekly_workout_plan.py`, `8_calendar.py`, `9_history.py`, `10_chat_log.py`). Also add the standard sidebar logout button so the user can sign out from any page. Confirm that visiting `/recipes`, `/inventory`, etc., while logged out redirects to the login screen.

---

### [MAJOR 14] Chat history bleeds across users sharing the same browser

**What's broken:** `chatbot/sidebar_widget.py:25-31` stores conversation under bare key `"chat_messages"`. Second user on the same browser inherits the first user's chat history until manually cleared.

**Prompt for Claude Code:**
> In `C:\Users\User\Desktop\אפליקציית תזונאי\chatbot\sidebar_widget.py` the chat history is stored under the bare session-state key `"chat_messages"`. When two users share the same browser (which is the common demo scenario), the second user logs in and sees the first user's chat. Namespace the key by the current user id (e.g., `f"chat_messages_{user_id}"`) and have the `logout` function in `auth/login_ui.py` / `ui/user_auth.py` clear all chat-related session state on signout. Verify by logging in as user A, sending a chat, logging out, logging in as user B, and confirming an empty conversation.

---

## Minor

- **Sidebar email reads only the legacy `bitefit_user` key** — fragile if anyone simplifies the login code. Files: `pages/0_profile.py:23`, `pages/6_daily_menu.py:39`, `pages/7_workout_tracker.py:25`, `pages/8_calendar.py:32`, `pages/9_history.py:23`.
- **`_DEFAULTS["user_id"] = "ui_user_001"` in `profile_repository.py:12`** — defensive landmine; the `except` branch on line 118 returns `dict(_DEFAULTS)` with the seed id intact.
- **`worktrees/auth/` and `worktrees/data-layer/`** — full stale copies of the codebase still containing `ui_user_001` references. Confuse search. Delete or gitignore.
- **`selected_user_id` session key collision** between `4_inventory.py` and `5_scanner.py` — moot once both pages lose the picker.

---

## Friday checklist (suggested order)

1. **Rotate** the Supabase service key and admin password (BLOCKER 7) — do this FIRST before any other work, while you're tracking down git history.
2. Strip `"ui_user_001"` fallback from all runtime code (BLOCKER 1).
3. Make `is_supabase_configured()` mandatory in `app_user.py` (MAJOR 11).
4. Convert `4_inventory.py` + `5_scanner.py` to single-tenant + add `require_auth` to the other 3 unprotected pages (BLOCKER 4, MAJOR 13).
5. Replace raw `<a>` in `bottom_nav` with `st.page_link` (BLOCKER 3).
6. Seed `profiles` row on signup; extend schema with missing columns; handle email-confirmation case (BLOCKER 2, MAJOR 9, MAJOR 10).
7. Add Supabase backends to workout/water/daily-summary repos (BLOCKER 5).
8. Wipe `storage_agents/*/ui_user_001.json` and Dvir rows in `users.json`; gitignore `storage_agents/` (BLOCKER 6).
9. Consolidate two auth modules (MAJOR 8).
10. Add password reset (MAJOR 12) and namespace chat history (MAJOR 14).

End-to-end demo verification: sign up two NEW users in two different browsers (incognito + normal). Each one fills in their profile, logs a workout, logs water, adds inventory, clicks every bottom-nav item. Confirm no cross-contamination, no new tabs, no "ישראל ישראלי" or "דביר" anywhere on screen.
