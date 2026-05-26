# storage_agents/ — Multi-User Data Isolation Audit

**Date:** 2026-05-11
**App root:** `C:\Users\User\Desktop\אפליקציית תזונאי\`
**Audited by:** Claude Code subagent (read-only)

---

## 1. Folder Tree

```
storage_agents/
├── users.json                          ← registry of all user accounts
├── audit/
│   ├── audit.log                       ← append-only system event log
│   ├── critic_log.txt                  ← Critic agent run log
│   ├── director_log.txt                ← Director agent run log
│   ├── expansion_log.txt               ← Daily expansion run log
│   ├── growth_metrics.json             ← time-series catalog growth stats
│   ├── metrics.json                    ← latest pipeline run metrics (git-conflicted)
│   └── director_reports/               ← 31 timestamped JSON reports (2026-03-30 → 2026-04-24)
│       └── YYYY-MM-DD_HH-MM.json
├── daily_summaries/
│   └── ui_user_001.json                ← per-user daily nutrition summary (keyed by date)
├── feedback/
│   └── feedback.json                   ← user-submitted feedback items
├── food_log/
│   └── ui_user_001.json                ← per-user food diary (keyed by date)
├── inventories/
│   └── aa03b295.json                   ← per-user pantry inventory (list of food items)
├── plans/                              ← 1,203 plan JSON files (approved + iterations)
│   └── YYYY-MM-DD_HH-MM-SS_<tag>.json ← contain user_id field ("auto_001", etc.)
├── profiles/
│   └── ui_user_001.json                ← per-user anthropometric + preference profile
├── recipe_images/
│   ├── pending_approvals.json          ← recipe→image candidates awaiting admin approval
│   ├── approved/                       ← (empty) approved recipe images
│   └── candidates/
│       └── recipe_NNN/                 ← 3 candidate JPEGs per recipe (50 recipes)
│           ├── 0.jpg
│           ├── 1.jpg
│           └── 2.jpg
├── recipes/
│   └── recipes.json                    ← global recipe catalog (~210+ recipes)
├── tasks/
│   ├── pending_tasks.json              ← Director-created tasks awaiting execution
│   ├── completed_tasks.json            ← tasks moved here after execution (currently [])
│   └── verdicts.json                   ← Critic approval/rejection records
├── templates/
│   └── menu_templates.json             ← meal pattern templates (kashrut + category rules)
├── water/
│   ├── 77bbcf60.json                   ← per-user water intake + goal
│   ├── 79b4fcd4.json
│   ├── aa03b295.json
│   └── ui_user_001.json
├── weekly_plans/                       ← (empty dir) weekly plan UI cache
│   └── {user_id}.json                  ← per-user calendar view saved plan
└── workouts/
    ├── aa03b295.json                   ← per-user workout log
    └── ui_user_001.json
```

**Total files:** ~1,350+ (dominated by 1,203 plan JSONs and ~150 recipe candidate images)

---

## 2. Per-Folder Classification

| Folder / File | Content Type | Classification | Reasoning |
|---|---|---|---|
| `users.json` | User account registry | **Hybrid** | Global file but contains one record per user; must remain accessible system-wide but is security-sensitive |
| `audit/audit.log` | System event log | **Global** | Logs pipeline events across all runs, no per-user payload |
| `audit/critic_log.txt` | Critic agent run log | **Global** | System-level observability for the Critic agent loop |
| `audit/director_log.txt` | Director agent run log | **Global** | System-level observability for the Director agent loop |
| `audit/expansion_log.txt` | Daily expansion log | **Global** | Logs catalog growth, not user data |
| `audit/growth_metrics.json` | Catalog size time-series | **Global** | Tracks system-wide food/recipe catalog health over time |
| `audit/metrics.json` | Latest pipeline metrics snapshot | **Global** | Aggregated pipeline statistics; currently has a git merge conflict |
| `audit/director_reports/` | Director analysis JSON per run | **Global** | Each report describes system-wide task queue state; references `food_id`s and plan quality, not individual users |
| `daily_summaries/` | Per-user daily nutrition summary | **Per-user** | File named `{user_id}.json`; contains calories/macros eaten vs. target per day for one user |
| `feedback/feedback.json` | User feedback items | **Hybrid** | Single flat file mixing all users' feedback; no explicit `user_id` field on outer record but feedback is user-submitted — needs splitting |
| `food_log/` | Per-user food diary | **Per-user** | File named `{user_id}.json`; contains dated food-eaten entries with entry UUIDs per user |
| `inventories/` | Per-user pantry inventory | **Per-user** | File named `{user_id}.json`; contains food items currently owned by one user |
| `plans/` | Meal plan snapshots (approved + iterations) | **Per-user** | Each plan JSON contains a `user_id` field (e.g. `"auto_001"`); plans are generated for a specific user's targets and inventory. Currently 1,203 files with no subdirectory by user. |
| `profiles/` | Per-user anthropometric + preferences | **Per-user** | File named `{user_id}.json`; contains name, DOB, height, weight, dietary preferences |
| `recipe_images/pending_approvals.json` | Admin approval queue | **Global** | Tracks which recipe images need admin review; not user-specific |
| `recipe_images/candidates/` | Candidate recipe images (JPEGs) | **Global** | Recipe imagery is system-wide content, not user data |
| `recipe_images/approved/` | Approved recipe images | **Global** | Same reasoning — system-wide recipe content |
| `recipes/recipes.json` | Recipe catalog | **Global** | Shared recipe library used by all users |
| `tasks/pending_tasks.json` | Director task queue | **Global** | System-level improvement tasks for agents (meal timing, variety, catalog expansion); not tied to any user |
| `tasks/completed_tasks.json` | Completed task records | **Global** | Same — system agent pipeline records |
| `tasks/verdicts.json` | Critic verdict records | **Global** | Same — system agent pipeline records |
| `templates/menu_templates.json` | Meal pattern templates | **Global** | Kashrut + category rules shared across all users |
| `water/` | Per-user water intake + goal | **Per-user** | File named `{user_id}.json`; contains daily water log and daily goal per user |
| `weekly_plans/` | UI weekly plan cache | **Per-user** | File named `{user_id}.json` (per `pages/9_history.py` line 67); stores the user's selected weekly plan for the calendar UI |
| `workouts/` | Per-user workout log | **Per-user** | File named `{user_id}.json`; contains workout entries with date, type, calories burned |

---

## 3. Read/Write Sites in Code

### 3.1 `users.json`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/user_manager.py` | 10 | `USERS_FILE` constant — read/write for `get_user`, `create_user`, `delete_user` | Path stays global; move to `storage_agents/system/users.json` |
| `pages/10_chat_log.py` | 382 | Read-only — loads first user name for greeting | Update path constant |

### 3.2 `profiles/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/repositories/profile_repository.py` | 41 | `base_dir` defaults to `storage_agents/profiles/`; reads/writes `{user_id}.json` | Change default to `storage_agents/users/{user_id}/profile.json` |

### 3.3 `food_log/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/repositories/food_log_repository.py` | 46 | `base_dir` defaults to `storage_agents/food_log/`; reads/writes `{user_id}.json` | Change default to `storage_agents/users/{user_id}/food_log.json` |

### 3.4 `daily_summaries/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/repositories/daily_summary_repository.py` | 27 | `base_dir` defaults to `storage_agents/daily_summaries/`; reads/writes `{user_id}.json` | Change default to `storage_agents/users/{user_id}/daily_summaries.json` |

### 3.5 `inventories/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/user_manager.py` | 62 | `_inventory_path()` builds `storage_agents/inventories/{user_id}.json`; read/write via `load_inventory`, `save_inventory`, `add_inventory_item` | Update helper to `storage_agents/users/{user_id}/inventory.json` |

### 3.6 `water/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/repositories/water_repository.py` | 35 | `base_dir` defaults to `storage_agents/water/`; reads/writes `{user_id}.json` | Change default to `storage_agents/users/{user_id}/water.json` |
| `nutrition_app/user_manager.py` | 148 | `initialize_water()` — creates initial water file on user creation | Update path |

### 3.7 `workouts/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/repositories/workout_repository.py` | 25 | `_storage_dir()` returns `storage_agents/workouts/`; reads/writes `{user_id}.json` | Change to `storage_agents/users/{user_id}/workouts.json` |
| `nutrition_app/user_manager.py` | 113 | `load_workouts` / workout helpers — same folder | Update path |

### 3.8 `plans/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/agents/agent_5_planner/meal_planner.py` | 93 | `_PLANS_DIR = storage_agents/plans` — writes plan snapshots | Change to `storage_agents/users/{user_id}/plans/` (requires passing `user_id` into planner) |
| `nutrition_app/agents/agent_8_director/director_agent.py` | 334 | `_load_last_plans()` reads from `storage_agents/plans/` to analyse recent plan quality | Must read from per-user path; if multi-user, scan all users or accept `user_id` param |
| `nutrition_app/agents/agent_9_critic/critic_agent.py` | 55 | `_plans_dir` set to `storage_agents/plans/` — reads plans for validation | Same as Director |
| `nutrition_app/agents/task_executor/task_executor.py` | 49 | `_plans_dir` set to `storage_agents/plans/` — reads/writes iteration plans | Same |

### 3.9 `weekly_plans/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `pages/9_history.py` | 65–67 | `PLANS_DIR / "{USER_ID}.json"` — UI saves/loads weekly plan selection | Change to `storage_agents/users/{user_id}/weekly_plan.json` |

### 3.10 `audit/` (all files)

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/agents/agent_8_director/director_agent.py` | 99–100 | Writes `audit/director_reports/{timestamp}.json` and appends to `director_log.txt` | Path stays; move to `storage_agents/system/audit/` |
| `nutrition_app/agents/agent_9_critic/critic_agent.py` | 53 | Writes to `audit/` (critic_log) | Same — move to system subtree |
| `nutrition_app/agents/task_executor/task_executor.py` | 48 | Writes to `audit/audit.log` | Same |
| `nutrition_app/autonomy/expansion/expansion_engine.py` | 55 | Writes to `audit/` (expansion_log, growth_metrics) | Same |
| `pages_admin/1_agents_dashboard.py` | 70, 90 | Reads `storage_agents/audit/director_reports/` and `tasks/` for dashboard | Update to system path |
| `pages_admin/3_audit_logs.py` | 37–39 | Reads all files under `audit/` | Update to system path |
| `run_autonomous_loop.py` | 68 | `STORAGE_DIR` root used by Director/Critic/Executor | Pass system-scoped path for tasks+audit |
| `run_daily_expansion.py` | 27 | `STORAGE` root passed to `ExpansionEngine` | Same |

### 3.11 `tasks/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/agents/agent_8_director/director_agent.py` | 98 | Writes `tasks/pending_tasks.json` | Move to `storage_agents/system/tasks/` |
| `nutrition_app/agents/task_executor/task_executor.py` | 47 | Reads `pending_tasks.json`, writes `completed_tasks.json` | Same |
| `nutrition_app/agents/agent_9_critic/critic_agent.py` | 53 | Reads `completed_tasks.json`, writes `verdicts.json`, re-writes `pending_tasks.json` | Same |

### 3.12 `recipes/`, `templates/`, `recipe_images/`

| File | Line | Operation | Change Required |
|---|---|---|---|
| `nutrition_app/agents/agent_11_recipes/recipe_manager.py` | 49 | Reads/writes `storage_agents/recipes/recipes.json` | Move to `storage_agents/system/recipes/recipes.json` |
| `nutrition_app/agents/agent_recipe_images/image_fetcher.py` | 33, 38 | Reads/writes `storage_agents/recipe_images/` and `storage_agents/recipes/` | Move both to `storage_agents/system/` subtree |
| `pages_admin/2_photo_manager.py` | 136 | Reads `storage_agents/recipe_images/approved` | Update to system path |
| `nutrition_app/autonomy/expansion/expansion_engine.py` | 53–54 | Reads/writes `storage_agents/recipes/` and `storage_agents/templates/` | Move to system subtree |

### 3.13 `feedback/feedback.json`

| File | Line | Operation | Change Required |
|---|---|---|---|
| (grep found no direct Python writer — appears written by UI pages) | — | Single flat file for all feedback | Add `user_id` field if missing; move to `storage_agents/system/feedback.json` or split per-user |

---

## 4. Recommended New Structure

```
storage_agents/
│
├── system/                             ← GLOBAL: agent pipeline + shared catalog
│   ├── users.json                      ← user account registry
│   ├── audit/
│   │   ├── audit.log
│   │   ├── director_log.txt
│   │   ├── critic_log.txt
│   │   ├── expansion_log.txt
│   │   ├── growth_metrics.json
│   │   ├── metrics.json
│   │   └── director_reports/
│   │       └── YYYY-MM-DD_HH-MM.json
│   ├── tasks/
│   │   ├── pending_tasks.json
│   │   ├── completed_tasks.json
│   │   └── verdicts.json
│   ├── recipes/
│   │   └── recipes.json
│   ├── templates/
│   │   └── menu_templates.json
│   ├── recipe_images/
│   │   ├── pending_approvals.json
│   │   ├── approved/
│   │   └── candidates/
│   │       └── recipe_NNN/
│   └── feedback.json                   ← system-wide; ensure user_id field on each record
│
└── users/                              ← PER-USER: one subdirectory per user_id
    └── {user_id}/                      ← e.g. "ui_user_001", "aa03b295"
        ├── profile.json                ← was profiles/{user_id}.json
        ├── inventory.json              ← was inventories/{user_id}.json
        ├── food_log.json               ← was food_log/{user_id}.json
        ├── daily_summaries.json        ← was daily_summaries/{user_id}.json
        ├── water.json                  ← was water/{user_id}.json
        ├── workouts.json               ← was workouts/{user_id}.json
        ├── weekly_plan.json            ← was weekly_plans/{user_id}.json
        └── plans/                      ← was plans/ (all files with this user's user_id)
            └── YYYY-MM-DD_HH-MM-SS_<tag>.json
```

**Key design decisions:**

1. The `plans/` flat directory (1,203 files, mixed user_ids) is the largest pain point. Filter by the `user_id` field inside each file to sort them into per-user subdirectories during migration.
2. `users.json` stays as a single global registry (`system/users.json`) because the user_manager needs to enumerate all users at login time. It is not per-user data.
3. `feedback.json` is classified global/system because there is currently no per-user split and feedback is processed by `agent_3_food`. If user-facing feedback history is ever needed, add `user_id` and move to per-user.
4. `recipes/`, `templates/`, and `recipe_images/` are purely shared catalog content — they never change per user.
5. Agent 8 (Director) and Agent 9 (Critic) read `plans/` to measure quality. After migration, they must accept a `user_id` parameter or scan `users/*/plans/` if running cross-user analysis.

---

## 5. Migration Plan

Below is a Python script outline to migrate the existing single-user data (current user IDs: `ui_user_001`, `aa03b295`, `79b4fcd4`, `77bbcf60`) into the new structure. Run once, then update all path constants in code.

```python
#!/usr/bin/env python3
"""
migrate_storage.py — one-time migration from flat storage_agents/ to
multi-user storage_agents/users/{user_id}/ + storage_agents/system/
"""

import json
import os
import shutil
from pathlib import Path

ROOT = Path("C:/Users/User/Desktop/אפליקציית תזונאי/storage_agents")
SYS  = ROOT / "system"
USR  = ROOT / "users"

# ── Step 1: Create system directories ────────────────────────────────────────
for d in [
    SYS / "audit" / "director_reports",
    SYS / "tasks",
    SYS / "recipes",
    SYS / "templates",
    SYS / "recipe_images" / "approved",
    SYS / "recipe_images" / "candidates",
]:
    d.mkdir(parents=True, exist_ok=True)

# ── Step 2: Move global files ─────────────────────────────────────────────────

# users.json
shutil.copy2(ROOT / "users.json", SYS / "users.json")

# audit/
for f in (ROOT / "audit").rglob("*"):
    dest = SYS / "audit" / f.relative_to(ROOT / "audit")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, dest)

# tasks/
for f in (ROOT / "tasks").iterdir():
    shutil.copy2(f, SYS / "tasks" / f.name)

# recipes/
shutil.copy2(ROOT / "recipes" / "recipes.json", SYS / "recipes" / "recipes.json")

# templates/
shutil.copy2(ROOT / "templates" / "menu_templates.json",
             SYS / "templates" / "menu_templates.json")

# recipe_images/
shutil.copy2(ROOT / "recipe_images" / "pending_approvals.json",
             SYS / "recipe_images" / "pending_approvals.json")
for candidate_dir in (ROOT / "recipe_images" / "candidates").iterdir():
    dest = SYS / "recipe_images" / "candidates" / candidate_dir.name
    if not dest.exists():
        shutil.copytree(candidate_dir, dest)
approved_src = ROOT / "recipe_images" / "approved"
if approved_src.exists():
    for f in approved_src.iterdir():
        shutil.copy2(f, SYS / "recipe_images" / "approved" / f.name)

# feedback
shutil.copy2(ROOT / "feedback" / "feedback.json", SYS / "feedback.json")

# ── Step 3: Discover all known user IDs ──────────────────────────────────────
known_ids = set()
# From users.json
with open(ROOT / "users.json", encoding="utf-8") as fh:
    known_ids.update(json.load(fh).keys())
# Also include legacy id used in profiles/food_log/daily_summaries
known_ids.add("ui_user_001")

# ── Step 4: Move per-user flat files ─────────────────────────────────────────
PER_USER_DIRS = {
    "profiles":        "profile.json",
    "inventories":     "inventory.json",
    "food_log":        "food_log.json",
    "daily_summaries": "daily_summaries.json",
    "water":           "water.json",
    "workouts":        "workouts.json",
    "weekly_plans":    "weekly_plan.json",
}

for folder, dest_name in PER_USER_DIRS.items():
    src_dir = ROOT / folder
    if not src_dir.exists():
        continue
    for src_file in src_dir.iterdir():
        user_id = src_file.stem          # filename without extension
        known_ids.add(user_id)
        dest_dir = USR / user_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_dir / dest_name)

# ── Step 5: Migrate plans/ by user_id field inside each JSON ─────────────────
plans_src = ROOT / "plans"
for plan_file in plans_src.glob("*.json"):
    try:
        with open(plan_file, encoding="utf-8") as fh:
            plan = json.load(fh)
        user_id = plan.get("user_id", "demo")
    except Exception:
        user_id = "demo"

    dest_plans = USR / user_id / "plans"
    dest_plans.mkdir(parents=True, exist_ok=True)
    shutil.copy2(plan_file, dest_plans / plan_file.name)

print("Migration complete (files copied; originals untouched).")
print(f"Users migrated: {sorted(known_ids)}")
print("Next steps:")
print("  1. Verify all destination files look correct.")
print("  2. Update path constants in nutrition_app/ and pages/ (see audit section 3).")
print("  3. Delete original flat folders after code is updated and tested.")
```

**Post-migration code changes (summary):**

| Constant / Default | Current value | New value |
|---|---|---|
| `USERS_FILE` in `user_manager.py:10` | `storage_agents/users.json` | `storage_agents/system/users.json` |
| `ProfileRepository.__init__` default `base_dir` | `storage_agents/profiles/` | `storage_agents/users/{user_id}/profile.json` (pass `user_id` to constructor) |
| `FoodLogRepository.__init__` default `base_dir` | `storage_agents/food_log/` | `storage_agents/users/{user_id}/food_log.json` |
| `DailySummaryRepository.__init__` default `base_dir` | `storage_agents/daily_summaries/` | `storage_agents/users/{user_id}/daily_summaries.json` |
| `WaterRepository.__init__` default `base_dir` | `storage_agents/water/` | `storage_agents/users/{user_id}/water.json` |
| `WorkoutRepository._storage_dir()` | `storage_agents/workouts/` | `storage_agents/users/{user_id}/workouts.json` |
| `_inventory_path()` in `user_manager.py:62` | `storage_agents/inventories/{user_id}.json` | `storage_agents/users/{user_id}/inventory.json` |
| `_PLANS_DIR` in `meal_planner.py:93` | `storage_agents/plans` | `storage_agents/users/{user_id}/plans/` |
| `_plans_dir` in `critic_agent.py:55` | `storage_agents/plans` | `storage_agents/users/{user_id}/plans/` |
| `_plans_dir` in `task_executor.py:49` | `storage_agents/plans` | `storage_agents/users/{user_id}/plans/` |
| `_BASE_DIR` in `director_agent.py:70` | `storage_agents/` | split: `tasks/audit` → `system/`, `plans` → per-user |
| `PLANS_DIR` in `pages/9_history.py:65` | `storage_agents/weekly_plans` | `storage_agents/users/{user_id}/weekly_plan.json` |
| `_BASE_DIR` in `director_agent.py`, `critic_agent.py`, `task_executor.py` for audit+tasks | `storage_agents/` | `storage_agents/system/` |

**Migration risk notes:**
- `metrics.json` currently has a git merge conflict — resolve this before or during migration.
- `plans/` has 1,203 files; the majority appear to belong to `user_id: "auto_001"` (the autonomous loop test user). These should be migrated to `users/auto_001/plans/`.
- The `feedback.json` entries do not contain a `user_id` field in the current schema — add one before splitting, or keep as a global system file for now.
- `weekly_plans/` directory currently exists but contains no files — easy to migrate by simply updating the path constant.
