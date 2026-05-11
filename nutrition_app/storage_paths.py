"""
storage_paths.py — Centralised path helpers for per-user and global agent storage.

Usage:
    from nutrition_app.storage_paths import user_plans_dir, system_tasks_dir

Every helper ensures the directory exists (mkdir parents=True, exist_ok=True)
before returning it so callers never have to create it themselves.

The base root defaults to  <project-root>/storage_agents  but can be overridden
via the STORAGE_AGENTS_ROOT environment variable (useful for tests).
"""

import os
from pathlib import Path

# ── Base root ──────────────────────────────────────────────────────────────────
_DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "storage_agents"


def _get_root() -> Path:
    """Return the storage root, honouring STORAGE_AGENTS_ROOT env var."""
    env = os.environ.get("STORAGE_AGENTS_ROOT")
    if env:
        return Path(env)
    return _DEFAULT_ROOT


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Per-user helpers ───────────────────────────────────────────────────────────

def user_dir(user_id: str, root: Path | None = None) -> Path:
    """Return the root directory for a specific user, e.g. storage_agents/users/<user_id>/."""
    base = root or _get_root()
    return _ensure(base / "users" / user_id)


def user_plans_dir(user_id: str, root: Path | None = None) -> Path:
    """Return the plans directory for a user: storage_agents/users/<user_id>/plans/."""
    return _ensure(user_dir(user_id, root) / "plans")


def user_profile_file(user_id: str, root: Path | None = None) -> Path:
    """Return the profile JSON path for a user (parent dir is ensured)."""
    d = user_dir(user_id, root)
    return d / "profile.json"


def user_inventory_file(user_id: str, root: Path | None = None) -> Path:
    """Return the inventory JSON path for a user (parent dir is ensured)."""
    d = user_dir(user_id, root)
    return d / "inventory.json"


def user_food_log_file(user_id: str, root: Path | None = None) -> Path:
    """Return the food-log JSON path for a user (parent dir is ensured)."""
    d = user_dir(user_id, root)
    return d / "food_log.json"


def user_daily_summaries_file(user_id: str, root: Path | None = None) -> Path:
    """Return the daily-summaries JSON path for a user (parent dir is ensured)."""
    d = user_dir(user_id, root)
    return d / "daily_summaries.json"


def user_water_file(user_id: str, root: Path | None = None) -> Path:
    """Return the water JSON path for a user (parent dir is ensured)."""
    d = user_dir(user_id, root)
    return d / "water.json"


def user_workouts_file(user_id: str, root: Path | None = None) -> Path:
    """Return the workouts JSON path for a user (parent dir is ensured)."""
    d = user_dir(user_id, root)
    return d / "workouts.json"


def user_weekly_plan_file(user_id: str, root: Path | None = None) -> Path:
    """Return the weekly-plan JSON path for a user (parent dir is ensured)."""
    d = user_dir(user_id, root)
    return d / "weekly_plan.json"


def users_dir(root: Path | None = None) -> Path:
    """Return the top-level users directory: storage_agents/users/."""
    base = root or _get_root()
    return _ensure(base / "users")


# ── Global / system helpers ────────────────────────────────────────────────────

def system_dir(root: Path | None = None) -> Path:
    """Return the system (global) directory: storage_agents/system/."""
    base = root or _get_root()
    return _ensure(base / "system")


def system_tasks_dir(root: Path | None = None) -> Path:
    """Return the system tasks directory: storage_agents/system/tasks/."""
    return _ensure(system_dir(root) / "tasks")


def system_audit_dir(root: Path | None = None) -> Path:
    """Return the system audit directory: storage_agents/system/audit/."""
    return _ensure(system_dir(root) / "audit")


def system_director_reports_dir(root: Path | None = None) -> Path:
    """Return the director reports directory: storage_agents/system/audit/director_reports/."""
    return _ensure(system_audit_dir(root) / "director_reports")


def system_director_log(root: Path | None = None) -> Path:
    """Return the director log file path (parent dir ensured)."""
    return system_audit_dir(root) / "director_log.txt"


def system_critic_log(root: Path | None = None) -> Path:
    """Return the critic log file path (parent dir ensured)."""
    return system_audit_dir(root) / "critic_log.txt"


def system_audit_log(root: Path | None = None) -> Path:
    """Return the audit.log file path (parent dir ensured)."""
    return system_audit_dir(root) / "audit.log"


def system_recipes_dir(root: Path | None = None) -> Path:
    """Return the recipes directory: storage_agents/system/recipes/."""
    return _ensure(system_dir(root) / "recipes")


def system_templates_dir(root: Path | None = None) -> Path:
    """Return the templates directory: storage_agents/system/templates/."""
    return _ensure(system_dir(root) / "templates")


def system_recipe_images_dir(root: Path | None = None) -> Path:
    """Return the recipe_images directory: storage_agents/system/recipe_images/."""
    return _ensure(system_dir(root) / "recipe_images")


def system_users_file(root: Path | None = None) -> Path:
    """Return the global users.json file path (parent dir ensured)."""
    return system_dir(root) / "users.json"


# ── Legacy / transitional helpers (fall back to original flat paths) ──────────
# These return the OLD paths and are used only during the migration period.

def legacy_plans_dir(root: Path | None = None) -> Path:
    """Legacy flat plans directory: storage_agents/plans/  (pre-migration)."""
    base = root or _get_root()
    return _ensure(base / "plans")


def legacy_users_file(root: Path | None = None) -> Path:
    """Legacy users.json at storage_agents/users.json  (pre-migration)."""
    base = root or _get_root()
    return base / "users.json"
