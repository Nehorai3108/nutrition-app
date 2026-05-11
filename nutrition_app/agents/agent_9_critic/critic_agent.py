"""
Agent 9 — Critic Agent

Responsibility:
- Read completed tasks from storage_agents/tasks/completed_tasks.json
- Read the resulting outputs (meal plans, catalog updates)
- Validate that the work done actually solved the problem
- Approve or reject each completed task
- Write verdict to storage_agents/tasks/verdicts.json
- Re-queue rejected tasks back to pending_tasks.json

Input:  completed_tasks.json, meal plans, food catalog state
Output: verdicts.json

Rules:
- Read-only analysis of catalog and plans — no modifications
- Only writes to verdicts.json, pending_tasks.json (re-queue), and audit log
- Verdicts are final per review cycle

Forbidden:
- Executing fixes
- Modifying food catalog
- Modifying meal plans
- Modifying inventory
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from nutrition_app.models.enums import FoodCategory, MealType
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.agents.agent_8_director.director_agent import (
    MEAL_SUITABLE_CATEGORIES,
)

# ─── Base storage path ────────────────────────────────────────────
_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "storage_agents",
)

from nutrition_app.storage_paths import (  # noqa: E402
    system_tasks_dir,
    system_audit_dir,
    user_plans_dir,
    legacy_plans_dir,
)


class CriticAgent:
    """
    Reviews completed tasks and validates that the work actually solved the problem.
    Approves or rejects, re-queues failures.
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self._storage_dir = storage_dir or _BASE_DIR
        self._user_id = user_id

        from pathlib import Path as _Path
        _root = _Path(self._storage_dir).parent if (
            _Path(self._storage_dir).name == "storage_agents"
        ) else None

        self._tasks_dir = str(system_tasks_dir(_root))
        self._audit_dir = str(system_audit_dir(_root))

        if user_id:
            self._plans_dir = str(user_plans_dir(user_id, _root))
        else:
            self._plans_dir = str(legacy_plans_dir(_root))

        os.makedirs(self._tasks_dir, exist_ok=True)
        os.makedirs(self._audit_dir, exist_ok=True)

    # ─── Main entry point ─────────────────────────────────────────

    def review_completed_tasks(self) -> List[dict]:
        """Review all completed tasks and produce verdicts."""
        completed = self._load_json(os.path.join(self._tasks_dir, "completed_tasks.json"))
        if not completed:
            return []

        verdicts = []
        rejected_tasks = []

        for task in completed:
            task_type = task.get("type", "")
            verdict = self._review_task(task)
            verdicts.append(verdict)

            if verdict["verdict"] == "REJECTED":
                # Re-queue: copy task back to pending with original fields
                requeued = {k: v for k, v in task.items()}
                requeued["requeued_from"] = verdict["task_id"]
                requeued["requeued_at"] = datetime.now(timezone.utc).isoformat()
                rejected_tasks.append(requeued)

        # Save verdicts (append to existing)
        self._append_verdicts(verdicts)

        # Move rejected back to pending
        if rejected_tasks:
            self._requeue_tasks(rejected_tasks)

        # Clear completed_tasks.json (reviewed tasks are done)
        self._save_json(os.path.join(self._tasks_dir, "completed_tasks.json"), [])

        # Append to critic log
        self._append_log(verdicts)

        return verdicts

    # ─── Per-task review dispatch ─────────────────────────────────

    def _review_task(self, task: dict) -> dict:
        task_type = task.get("type", "")
        task_id = task.get("task_id", "unknown")

        if task_type == "expand_catalog":
            return self._review_expand_catalog(task)
        elif task_type == "improve_variety":
            return self._review_improve_variety(task)
        elif task_type == "fix_meal_timing":
            return self._review_fix_meal_timing(task)
        elif task_type == "rebalance_macros":
            return self._review_rebalance_macros(task)
        else:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": f"Unknown task type: {task_type}",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

    # ─── Review: expand_catalog ───────────────────────────────────

    def _review_expand_catalog(self, task: dict) -> dict:
        task_id = task.get("task_id", "unknown")
        catalog = FoodCatalog()
        foods = catalog.get_all_foods()

        category_counts: Dict[str, int] = {}
        for cat in FoodCategory:
            category_counts[cat.value] = 0
        for food in foods:
            category_counts[food.category.value] = category_counts.get(food.category.value, 0) + 1

        # Extract category from task details
        details = task.get("details", "")
        # Find which category was flagged
        flagged_category = None
        for cat in FoodCategory:
            if f"Category {cat.value}" in details:
                flagged_category = cat.value
                break

        if flagged_category and category_counts.get(flagged_category, 0) >= 5:
            return {
                "task_id": task_id,
                "verdict": "APPROVED",
                "reason": f"Category {flagged_category} now has {category_counts[flagged_category]} foods (>= 5).",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            count = category_counts.get(flagged_category, 0) if flagged_category else "?"
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": f"Category {flagged_category} still has only {count} foods (< 5).",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

    # ─── Review: improve_variety ──────────────────────────────────

    def _review_improve_variety(self, task: dict) -> dict:
        task_id = task.get("task_id", "unknown")
        details = task.get("details", "")

        # Extract food_id from details
        flagged_food_id = None
        if "food_id " in details:
            parts = details.split("food_id ")
            if len(parts) > 1:
                flagged_food_id = parts[1].split(" ")[0]

        plans = self._load_recent_plans(3)
        if not plans or not flagged_food_id:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": "Not enough plans to verify or missing food_id.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

        count = 0
        for plan in plans:
            for meal in plan.get("meals", []):
                for item in meal.get("items", []):
                    if item.get("food_id") == flagged_food_id:
                        count += 1
                        break

        if count <= 2:
            return {
                "task_id": task_id,
                "verdict": "APPROVED",
                "reason": f"food_id {flagged_food_id} appears in {count}/3 recent plans (<= 2).",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": f"food_id {flagged_food_id} still appears in {count}/3 recent plans (> 2).",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

    # ─── Review: fix_meal_timing ──────────────────────────────────

    def _review_fix_meal_timing(self, task: dict) -> dict:
        task_id = task.get("task_id", "unknown")
        latest_plan = self._load_latest_plan()

        if latest_plan is None:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": "No meal plan found to verify.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

        catalog = FoodCatalog()
        violations = []

        for meal in latest_plan.get("meals", []):
            meal_type_str = meal.get("meal_type", "")
            try:
                meal_type = MealType(meal_type_str)
            except ValueError:
                continue

            suitable = MEAL_SUITABLE_CATEGORIES.get(meal_type, [])
            suitable_values = [c.value for c in suitable]

            for item in meal.get("items", []):
                food_id = item.get("food_id", "")
                food = catalog.get_food_by_id(food_id)
                if food and food.category.value not in suitable_values:
                    violations.append(f"{meal_type_str}: {food.name_he} ({food.category.value})")

        if not violations:
            return {
                "task_id": task_id,
                "verdict": "APPROVED",
                "reason": "No meal timing violations found in latest plan.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": f"Still {len(violations)} timing violations: {', '.join(violations[:3])}.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

    # ─── Review: rebalance_macros ─────────────────────────────────

    def _review_rebalance_macros(self, task: dict) -> dict:
        task_id = task.get("task_id", "unknown")
        latest_plan = self._load_latest_plan()

        if latest_plan is None:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": "No meal plan found to verify.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

        totals = latest_plan.get("totals", {})
        total_protein = totals.get("protein_g", 0)
        total_carbs = totals.get("carbs_g", 0)
        total_fat = totals.get("fat_g", 0)

        protein_cal = total_protein * 4
        carbs_cal = total_carbs * 4
        fat_cal = total_fat * 9
        macro_total = protein_cal + carbs_cal + fat_cal

        if macro_total <= 0:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": "Macro total is zero — no data to evaluate.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

        protein_pct = (protein_cal / macro_total) * 100
        carbs_pct = (carbs_cal / macro_total) * 100

        if protein_pct >= 25 and carbs_pct <= 60:
            return {
                "task_id": task_id,
                "verdict": "APPROVED",
                "reason": f"Macros balanced: protein {protein_pct:.1f}%, carbs {carbs_pct:.1f}%.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "task_id": task_id,
                "verdict": "REJECTED",
                "reason": f"Macros still imbalanced: protein {protein_pct:.1f}%, carbs {carbs_pct:.1f}%.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

    # ─── Storage helpers ──────────────────────────────────────────

    def _load_json(self, path: str) -> list:
        if not os.path.isfile(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_json(self, path: str, data: list):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _append_verdicts(self, new_verdicts: list):
        path = os.path.join(self._tasks_dir, "verdicts.json")
        existing = self._load_json(path)
        existing.extend(new_verdicts)
        self._save_json(path, existing)

    def _requeue_tasks(self, tasks: list):
        path = os.path.join(self._tasks_dir, "pending_tasks.json")
        existing = self._load_json(path)
        existing.extend(tasks)
        self._save_json(path, existing)

    def _load_recent_plans(self, count: int) -> list:
        if not os.path.isdir(self._plans_dir):
            return []
        files = sorted(
            [f for f in os.listdir(self._plans_dir) if f.endswith(".json")],
            reverse=True,
        )
        plans = []
        for f in files[:count]:
            try:
                with open(os.path.join(self._plans_dir, f), "r", encoding="utf-8") as fh:
                    plans.append(json.load(fh))
            except (json.JSONDecodeError, OSError):
                continue
        return plans

    def _load_latest_plan(self) -> Optional[dict]:
        plans = self._load_recent_plans(1)
        return plans[0] if plans else None

    def _append_log(self, verdicts: list):
   