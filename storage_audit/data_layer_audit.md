# Data Layer Audit — Multi-User Refactor Contract

**Audit date:** 2026-05-11  
**Auditor:** Agent (read-only pass)  
**Scope:** All persistent entities, both SQLite (storage/nutrition.db) and JSON flat-file stores (storage_agents/)  
**Purpose:** Authoritative contract for implementing multi-user isolation.

---

## 1. Tables Inventory

This section covers every persistent store — SQLite tables and JSON flat-file "virtual tables".

### 1a. SQLite tables (storage/nutrition.db)

| Table | Columns | Current PK | Classification | Reasoning |
|---|---|---|---|---|
| `foods` | food_id, name_he, name_en, category, calories_kcal, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg, default_unit, default_serving_g, aliases_he, aliases_en, is_custom, source, created_at, updated_at | food_id (TEXT) | **shared** | Global nutrition catalog (USDA-style). No user context. `is_custom` flag exists but custom foods are not yet per-user. |
| `recipes` | recipe_id, name, servings, instructions, total_calories_kcal, total_protein_g, total_carbs_g, total_fat_g, total_fiber_g, per_serving_*, unresolved_ingredients, source, created_at, updated_at | recipe_id (TEXT) | **shared** | Recipe catalog, not scoped to a user. `source` column records origin but no user_id. |
| `recipe_ingredients` | ingredient_id, recipe_id, food_id, name_he, name_en, quantity_g | ingredient_id (TEXT) | **shared** | Child of `recipes`; inherits shared status. |
| `run_logs` | run_id, started_at, ended_at, items_fetched, items_saved, items_updated, items_failed, errors, status | run_id (TEXT) | **system** | Background job run metadata (food data collector). No user_id; tracks agent pipeline runs, not user actions. |

### 1b. JSON flat-file stores (storage_agents/)

Each store is implemented as a file-per-user (`{user_id}.json`) or a single global file.

| Logical store | File path pattern | Current "PK" | Classification | Reasoning |
|---|---|---|---|---|
| `users` | `storage_agents/users.json` (single dict, key=user_id) | user_id (str) | **user-scoped** | Registry of user accounts. Each entry is `{user_id, name, created_at}`. |
| `profiles` | `storage_agents/profiles/{user_id}.json` | Filename = user_id | **user-scoped** | Extended profile: gender, height, weight, activity_level, goal, meal_preferences. Directly identifies one user. Also has Supabase backend (table `profiles`, PK=user_id). |
| `inventories` | `storage_agents/inventories/{user_id}.json` | Filename = user_id | **user-scoped** | Per-user fridge/pantry. List of `{food_id, name_he, quantity_g, added_at}`. |
| `food_log` | `storage_agents/food_log/{user_id}.json` | Filename = user_id | **user-scoped** | Per-user daily food diary. Nested by date. Also has Supabase backend (table `food_log`, cols include user_id). |
| `daily_summaries` | `storage_agents/daily_summaries/{user_id}.json` | Filename = user_id | **user-scoped** | Per-user daily nutrition snapshots keyed by YYYY-MM-DD. |
| `water` | `storage_agents/water/{user_id}.json` | Filename = user_id | **user-scoped** | Per-user water intake log + daily goal. |
| `workouts` | `storage_agents/workouts/{user_id}.json` | Filename = user_id | **user-scoped** | Per-user weekly plan and daily workout log. |
| `recipes` (JSON) | `storage_agents/recipes/recipes.json` (single shared file) | recipe_id | **shared** | Shared recipe catalog (mirrors SQLite recipes). No user dimension. |
| `templates` | `storage_agents/templates/menu_templates.json` | template key | **shared** | Shared menu templates. No user dimension. |
| `tasks` | `storage_agents/tasks/pending_tasks.json`, `completed_tasks.json`, `verdicts.json` | task_id | **system** | Agent pipeline task queue. Fields: task_id, type, agent, priority, details. No user_id — tasks are system-level. |
| `plans` | `storage_agents/plans/*.json` | filename (timestamp) | **system** (currently), **should be user-scoped** | Saved meal plans. Currently stored as timestamped flat files with no user namespace in the filename. The JSON content contains `user_id` inside but the directory is not segregated. |
| `audit logs` | `storage_agents/audit/audit.log`, `director_log.txt`, `critic_log.txt` | line-based | **system** | Agent pipeline audit trail. No user data. |
| `feedback` | `storage_agents/feedback/feedback.json` | entry key | **system** | System-level feedback records. Not per-user. |
| `recipe_images` | `storage_agents/recipe_images/approved/`, `candidates/` | filename | **shared** | Shared image assets for recipes. |

---

## 2. Repository Methods Inventory

All public methods, their current signatures, the stores they touch, and their classification.

### BaseRepository (`nutrition_app/repositories/base_repository.py`)

These are inherited by `UserRepository`, `FoodRepository`, `InventoryRepository`, `InventoryChangeLogRepository`, `RunRepository`, and `ArtifactRepository`.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `get` | `get(self, key: str) -> Optional[dict]` | reads entity JSON file (keyed by entity_name) | varies by subclass |
| `get_all` | `get_all(self) -> Dict[str, Any]` | reads entity JSON file | varies by subclass |
| `save` | `save(self, key: str, value: dict) -> None` | writes entity JSON file | varies by subclass |
| `delete` | `delete(self, key: str) -> bool` | writes entity JSON file | varies by subclass |
| `count` | `count(self) -> int` | reads entity JSON file | varies by subclass |
| `exists` | `exists(self, key: str) -> bool` | reads entity JSON file | varies by subclass |

### UserRepository (`nutrition_app/repositories/user_repository.py`)

Stores `UserProfile` objects in `storage/data/users.json` (flat dict keyed by user_id). Note: this is a **different** storage location from `storage_agents/users.json` managed by `user_manager.py`. Both exist; see migration notes.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `save_user` | `save_user(self, user: UserProfile) -> None` | writes `users.json` | user-scoped |
| `get_user` | `get_user(self, user_id: str) -> UserProfile \| None` | reads `users.json` | user-scoped |
| (inherited) `get_all` | `get_all(self) -> Dict[str, Any]` | reads `users.json` | system/admin |
| (inherited) `delete` | `delete(self, key: str) -> bool` | writes `users.json` | user-scoped |

### FoodRepository (`nutrition_app/repositories/food_repository.py`)

Stores `FoodItem` objects in `storage/data/foods.json`.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `save_food` | `save_food(self, food: FoodItem) -> None` | writes `foods.json` | shared |
| `get_food` | `get_food(self, food_id: str) -> FoodItem \| None` | reads `foods.json` | shared |
| (inherited) `get_all` | `get_all(self) -> Dict[str, Any]` | reads `foods.json` | shared |
| (inherited) `delete` | `delete(self, key: str) -> bool` | writes `foods.json` | shared |

### InventoryRepository / InventoryChangeLogRepository (`nutrition_app/repositories/inventory_repository.py`)

Both extend BaseRepository directly. The storage key is the inventory_item_id, **not** the user_id. These have no user isolation at all — they write to a single shared `storage/data/inventory.json` and `storage/data/inventory_changelog.json`. This is the most critical gap.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| (inherited) `get` | `get(self, key: str) -> Optional[dict]` | reads `inventory.json` | **user-scoped — BROKEN** (no user isolation) |
| (inherited) `get_all` | `get_all(self) -> Dict[str, Any]` | reads `inventory.json` | **user-scoped — BROKEN** |
| (inherited) `save` | `save(self, key: str, value: dict) -> None` | writes `inventory.json` | **user-scoped — BROKEN** |
| (inherited) `delete` | `delete(self, key: str) -> bool` | writes `inventory.json` | **user-scoped — BROKEN** |

### ProfileRepository (`nutrition_app/repositories/profile_repository.py`)

Dual-backend (Supabase or local JSON). Already user-scoped by design.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `load` | `load(self, user_id: str) -> dict` | reads `storage_agents/profiles/{user_id}.json` OR Supabase `profiles` table | user-scoped |
| `save` | `save(self, profile: dict) -> None` | writes `storage_agents/profiles/{user_id}.json` OR Supabase `profiles` table | user-scoped |
| `_sb_load` | `_sb_load(self, user_id: str) -> Optional[dict]` | reads Supabase `profiles` | user-scoped (internal) |
| `_sb_save` | `_sb_save(self, profile: dict) -> None` | writes Supabase `profiles` | user-scoped (internal) |

### FoodLogRepository (`nutrition_app/repositories/food_log_repository.py`)

Dual-backend. Already user-scoped by design.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `get_log` | `get_log(self, user_id: str, day: date) -> List[FoodLogEntry]` | reads `storage_agents/food_log/{user_id}.json` OR Supabase `food_log` | user-scoped |
| `add_entry` | `add_entry(self, user_id: str, day: date, entry: FoodLogEntry)` | writes `storage_agents/food_log/{user_id}.json` OR Supabase `food_log` | user-scoped |
| `remove_entry` | `remove_entry(self, user_id: str, day: date, entry_id: str)` | writes `storage_agents/food_log/{user_id}.json` OR Supabase `food_log` | user-scoped |
| `get_totals` | `get_totals(self, user_id: str, day: date) -> dict` | reads via `get_log` | user-scoped |

### DailySummaryRepository (`nutrition_app/repositories/daily_summary_repository.py`)

Already user-scoped by design.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `save` | `save(self, summary: DailySummary) -> None` | writes `storage_agents/daily_summaries/{user_id}.json` | user-scoped |
| `get` | `get(self, user_id: str, date_obj) -> Optional[DailySummary]` | reads `storage_agents/daily_summaries/{user_id}.json` | user-scoped |
| `get_for_period` | `get_for_period(self, user_id: str, start: date, end: date) -> List[DailySummary]` | reads `storage_agents/daily_summaries/{user_id}.json` | user-scoped |
| `get_last_n_days` | `get_last_n_days(self, user_id: str, n: int = 7) -> List[DailySummary]` | reads via `get_for_period` | user-scoped |

### WaterRepository (`nutrition_app/repositories/water_repository.py`)

Already user-scoped by design.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `get_water_data` | `get_water_data(self, user_id: str) -> UserWaterData` | reads `storage_agents/water/{user_id}.json` | user-scoped |
| `save_water_data` | `save_water_data(self, water_data: UserWaterData) -> None` | writes `storage_agents/water/{user_id}.json` | user-scoped |
| `save_water_goal` | `save_water_goal(self, user_id: str, daily_goal_ml: float) -> WaterGoal` | reads+writes `storage_agents/water/{user_id}.json` | user-scoped |
| `add_water_intake` | `add_water_intake(self, user_id: str, amount_ml: float, timestamp, source, notes) -> WaterIntake` | reads+writes `storage_agents/water/{user_id}.json` | user-scoped |
| `remove_water_intake` | `remove_water_intake(self, user_id: str, water_id: str, date_str: str) -> bool` | reads+writes `storage_agents/water/{user_id}.json` | user-scoped |
| `get_daily_total` | `get_daily_total(self, user_id: str, date_obj) -> float` | reads via `get_water_data` | user-scoped |
| `get_week_total` | `get_week_total(self, user_id: str, end_date_obj) -> float` | reads via `get_water_data` | user-scoped |
| `get_water_intakes_for_date` | `get_water_intakes_for_date(self, user_id: str, date_obj) -> List[WaterIntake]` | reads via `get_water_data` | user-scoped |
| `get_water_intakes_for_period` | `get_water_intakes_for_period(self, user_id: str, start_date_obj, end_date_obj) -> List[WaterIntake]` | reads via `get_water_data` | user-scoped |
| `get_water_goal` | `get_water_goal(self, user_id: str) -> WaterGoal` | reads via `get_water_data` | user-scoped |

### WorkoutRepository (`nutrition_app/repositories/workout_repository.py`)

Already user-scoped by design.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `get_workout_data` | `get_workout_data(self, user_id: str) -> UserWorkoutData` | reads `storage_agents/workouts/{user_id}.json` | user-scoped |
| `save_weekly_plan` | `save_weekly_plan(self, user_id: str, plan: WeeklyWorkoutPlan) -> None` | reads+writes `storage_agents/workouts/{user_id}.json` | user-scoped |
| `add_daily_workout` | `add_daily_workout(self, user_id: str, day: date, entry: WorkoutEntry) -> None` | reads+writes `storage_agents/workouts/{user_id}.json` | user-scoped |
| `remove_daily_workout` | `remove_daily_workout(self, user_id: str, day: date, index: int) -> None` | reads+writes `storage_agents/workouts/{user_id}.json` | user-scoped |
| `clear_daily_workouts` | `clear_daily_workouts(self, user_id: str, day: date) -> None` | reads+writes `storage_agents/workouts/{user_id}.json` | user-scoped |
| `resolve_workouts_for_date` | `resolve_workouts_for_date(self, user_id: str, day: date) -> List[WorkoutEntry]` | reads `storage_agents/workouts/{user_id}.json` | user-scoped |

### RunRepository / ArtifactRepository (`nutrition_app/repositories/run_repository.py`)

Extends BaseRepository. Single shared files `storage/runs/runs_index.json` and `storage/artifacts/artifacts_index.json`. RunState model carries `user_id` internally.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| (inherited) `get` | `get(self, key: str) -> Optional[dict]` | reads `runs_index.json` / `artifacts_index.json` | **system** (run_id is PK, no user filtering) |
| (inherited) `get_all` | `get_all(self) -> Dict[str, Any]` | reads respective index file | **system** |
| (inherited) `save` | `save(self, key: str, value: dict) -> None` | writes respective index file | **system** |
| (inherited) `delete` | `delete(self, key: str) -> bool` | writes respective index file | **system** |

### user_manager.py module-level functions (`nutrition_app/user_manager.py`)

These are standalone functions (not a class). They manage the second user store at `storage_agents/users.json`.

| Method | Current Signature | Reads/Writes | Classification |
|---|---|---|---|
| `get_all_users` | `get_all_users() -> list[dict]` | reads `storage_agents/users.json` | system/admin |
| `get_user` | `get_user(user_id: str) -> Optional[dict]` | reads `storage_agents/users.json` | user-scoped |
| `create_user` | `create_user(name: str) -> dict` | writes `storage_agents/users.json`, initializes water file | system |
| `delete_user` | `delete_user(user_id: str)` | writes `storage_agents/users.json`, deletes inventory file | user-scoped |
| `load_inventory` | `load_inventory(user_id: str) -> list[dict]` | reads `storage_agents/inventories/{user_id}.json` | user-scoped |
| `save_inventory` | `save_inventory(user_id: str, items: list[dict])` | writes `storage_agents/inventories/{user_id}.json` | user-scoped |
| `add_inventory_item` | `add_inventory_item(user_id: str, food_id: str, name_he: str, quantity_g: float)` | reads+writes `storage_agents/inventories/{user_id}.json` | user-scoped |
| `update_inventory_item` | `update_inventory_item(user_id: str, food_id: str, quantity_g: float)` | reads+writes `storage_agents/inventories/{user_id}.json` | user-scoped |
| `remove_inventory_item` | `remove_inventory_item(user_id: str, food_id: str)` | reads+writes `storage_agents/inventories/{user_id}.json` | user-scoped |
| `load_workouts` | `load_workouts(user_id: str) -> list[dict]` | reads `storage_agents/workouts/{user_id}.json` | user-scoped |
| `save_workout` | `save_workout(user_id: str, workout: dict) -> dict` | reads+writes `storage_agents/workouts/{user_id}.json` | user-scoped |
| `delete_workout` | `delete_workout(user_id: str, workout_id: str)` | reads+writes `storage_agents/workouts/{user_id}.json` | user-scoped |
| `initialize_water` | `initialize_water(user_id: str, daily_goal_ml: float = 2000.0) -> dict` | writes `storage_agents/water/{user_id}.json` | user-scoped |
| `load_water` | `load_water(user_id: str) -> dict` | reads (or creates) `storage_agents/water/{user_id}.json` | user-scoped |

---

## 3. THE CONTRACT

> **Implementors follow this section verbatim. It is the normative specification.**

### 3a. Methods that MUST accept `user_id: str` as their first parameter

The following methods currently lack `user_id` isolation and must be refactored. Methods already correctly accepting `user_id` are noted as "already compliant" for completeness.

**MUST ADD `user_id` parameter (currently broken — no isolation):**

| File | Method | Action required |
|---|---|---|
| `repositories/inventory_repository.py` | `InventoryRepository.get` | Replace with user-namespaced storage key or separate file per user |
| `repositories/inventory_repository.py` | `InventoryRepository.get_all` | Must filter to user's items only |
| `repositories/inventory_repository.py` | `InventoryRepository.save` | Must namespace by user_id |
| `repositories/inventory_repository.py` | `InventoryRepository.delete` | Must namespace by user_id |
| `repositories/inventory_repository.py` | `InventoryChangeLogRepository.get` | Must namespace by user_id |
| `repositories/inventory_repository.py` | `InventoryChangeLogRepository.get_all` | Must filter to user's log only |
| `repositories/inventory_repository.py` | `InventoryChangeLogRepository.save` | Must namespace by user_id |
| `repositories/run_repository.py` | `RunRepository.get_all` | Must accept optional `user_id` filter to list only that user's runs |
| `repositories/run_repository.py` | `ArtifactRepository.get_all` | Must accept optional `user_id` filter |

**MUST ADD `user_id` parameter (plans directory — currently unnamespaced):**

| File | Method | Action required |
|---|---|---|
| `agents/agent_7_data_performance/data_manager.py` (or wherever plans are saved) | any plan-save method | Must write to `storage_agents/plans/{user_id}/` subdirectory |

**Already compliant (no change needed to signature, listed for audit completeness):**

| File | Method |
|---|---|
| `repositories/profile_repository.py` | `load(user_id)`, `save(profile)` (profile dict contains user_id) |
| `repositories/food_log_repository.py` | `get_log`, `add_entry`, `remove_entry`, `get_totals` |
| `repositories/daily_summary_repository.py` | `save`, `get`, `get_for_period`, `get_last_n_days` |
| `repositories/water_repository.py` | all 10 public methods |
| `repositories/workout_repository.py` | all 6 public methods |
| `user_manager.py` | all inventory, workout, water functions |

### 3b. Tables/stores that MUST add a `user_id` column (Postgres UUID, indexed, NOT NULL)

For the **Supabase (Postgres) migration** only. SQLite local dev uses file-per-user patterns and does not need schema changes except where noted.

| Table/Store | Column to add | Index | Constraint | Notes |
|---|---|---|---|---|
| Supabase `food_log` | `user_id UUID NOT NULL` | `CREATE INDEX ON food_log(user_id)` | NOT NULL, FK to `auth.users(id)` | Already present in code; verify it exists in Supabase schema |
| Supabase `profiles` | `user_id UUID NOT NULL` (PK) | primary key | NOT NULL | Already present per code; verify |
| `storage/data/inventory.json` (SQLite-mode BaseRepo) | Refactor to file-per-user pattern (`storage_agents/inventories/{user_id}.json`) — do NOT add a column; change storage strategy entirely | — | — | Current BaseRepository writes a single flat JSON for all users |
| `storage/data/inventory_changelog.json` | Same as above — file-per-user | — | — | Same issue as inventory |
| `storage_agents/plans/` | Segregate into `storage_agents/plans/{user_id}/` subdirectory | — | — | Currently all plans are in one flat directory |

**If/when SQLite tables are promoted to Postgres:**

| Table | Column to add | Index | Notes |
|---|---|---|---|
| `recipes` | `user_id UUID NULLABLE` | `CREATE INDEX ON recipes(user_id) WHERE user_id IS NOT NULL` | NULL = globally shared; non-null = user's custom recipe |
| `recipe_ingredients` | (inherits via recipe_id FK; no direct user_id needed) | — | Scoping is inherited through `recipes.user_id` |
| `foods` | `user_id UUID NULLABLE` | `CREATE INDEX ON foods(user_id) WHERE user_id IS NOT NULL` | NULL = shared catalog; non-null = user's custom food entry (`is_custom=true`) |
| `run_logs` | No change | — | System table; not user-facing |

### 3c. Tables/stores that DO NOT change (shared, no user_id)

| Table/Store | Reason |
|---|---|
| `foods` (shared rows, user_id IS NULL) | Global nutrition catalog. No per-user data. |
| `recipes` (shared rows, user_id IS NULL) | Global recipe catalog. |
| `recipe_ingredients` | Child of `recipes`; scoped via FK. |
| `run_logs` | Background agent job metadata. |
| `storage_agents/recipes/recipes.json` | Shared recipe catalog (JSON mirror). |
| `storage_agents/templates/menu_templates.json` | Shared planning templates. |
| `storage_agents/tasks/pending_tasks.json` | System agent task queue. |
| `storage_agents/tasks/completed_tasks.json` | System agent task archive. |
| `storage_agents/tasks/verdicts.json` | Critic verdicts. System-level. |
| `storage_agents/audit/*` | System audit logs. |
| `storage_agents/feedback/feedback.json` | System feedback. |
| `storage_agents/recipe_images/` | Shared static assets. |

### 3d. Default user_id for local dev fallback

```
DEFAULT_USER_ID = "demo"
```

- All repositories that accept `user_id` must default to `"demo"` when no user is authenticated.
- The existing default user is `"ui_user_001"` in current files. During migration, treat `"ui_user_001"` as an alias for `"demo"` (or rename existing files).
- Example pattern:

```python
def get_log(self, user_id: str = "demo", day: date = None) -> List[FoodLogEntry]:
    ...
```

---

## 4. Migration Notes

| Item | Issue | Recommended action |
|---|---|---|
| **Dual user registries** | Two separate user stores exist: `storage/data/users.json` (managed by `UserRepository`) and `storage_agents/users.json` (managed by `user_manager.py`). They have different schemas. | Consolidate into one. `user_manager.py` is the one actually used by the UI. `UserRepository` is the "domain" version. Pick one and delete the other, or merge. |
| **InventoryRepository is global** | `InventoryRepository` (BaseRepository subclass) stores all inventory items in a single `storage/data/inventory.json` dict keyed by `inventory_item_id`. There is no user_id key in the data. Meanwhile `user_manager.load_inventory()` correctly uses per-user files at `storage_agents/inventories/{user_id}.json`. These are two separate inventory systems. | The `user_manager.py` inventory functions are the ones actually used. `InventoryRepository` appears to be unused or used only inside `InventoryManager` (in-memory). Confirm which path the UI calls, then retire the unused one. If `InventoryRepository` is kept, rewrite it to use file-per-user pattern matching `user_manager.py`. |
| **plans/ directory not namespaced** | Saved meal plans under `storage_agents/plans/` are named by timestamp only (`2026-03-30_15-21-25_approved.json`). The user_id is inside the JSON content but not in the path. Multiple users would collide or see each other's plans. | Restructure to `storage_agents/plans/{user_id}/` and update all read/write code accordingly. |
| **Existing data backfill** | All current data belongs to a single demo user (`ui_user_001`, `aa03b295`, `79b4fcd4`, `77bbcf60`). These are test/demo accounts with no real PII. | Safe to wipe. If preserving, rename files from `{old_id}.json` to `demo.json` or the canonical demo user_id. No complex backfill needed. |
| **Supabase food_log table** | The code writes a `user_id` column to Supabase `food_log`, but the actual Supabase schema was not inspectable (no migration files found). | Verify the Supabase schema has `user_id` column with NOT NULL constraint and an index. Add RLS (Row Level Security) policy: `USING (user_id = auth.uid())`. |
| **Supabase profiles table** | Same caveat — code references `profiles` table with `user_id` PK. | Verify schema and add RLS. |
| **`is_custom` foods** | `foods` table has `is_custom INTEGER DEFAULT 0` and `source TEXT`. Custom foods currently have no user_id. | When promoting to multi-user, add `user_id UUID NULLABLE` to `foods`. Shared catalog rows have `user_id = NULL`. Custom rows have the creating user's id. Queries for the catalog should use `WHERE user_id IS NULL OR user_id = :current_user`. |
| **WorkoutRepository vs user_manager workouts** | Like inventory, two parallel workout stores exist: `WorkoutRepository` (class-based, structured `UserWorkoutData`) and `user_manager.save_workout()` (simple list). | Determine which the UI uses and retire the other. `WorkoutRepository` is richer and should be preferred. |
| **`storage/workouts.json`** | A stray `storage/workouts.json` file exists alongside `nutrition.db`. Not managed by any repository class found. | Inspect and migrate or delete. |
