"""
Agent 8 — Director Agent

Responsibility:
- Scan the current system state and identify what is missing or suboptimal
- Generate a prioritized task list for other agents
- Write tasks to storage_agents/tasks/pending_tasks.json
- NEVER execute tasks itself — only define and delegate

Input:  System state (food catalog, meal plans, storage)
Output: DirectorReport

Rules:
- Read-only analysis — no modifications to catalog, plans, or inventory
- Only writes to pending_tasks.json and audit files
- Never executes tasks — only creates them

Forbidden:
- Executing tasks
- Modifying food catalog
- Modifying meal plans
- Modifying inventory
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from nutrition_app.models.enums import FoodCategory, MealType
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.models.meal import MealPlan

# ─── Meal suitability mapping (same logic as agent_5_planner) ─────
MEAL_SUITABLE_CATEGORIES: Dict[MealType, List[FoodCategory]] = {
    MealType.BREAKFAST: [
        FoodCategory.DAIRY, FoodCategory.GRAIN, FoodCategory.FRUIT,
        FoodCategory.FAT, FoodCategory.BEVERAGE, FoodCategory.NUT_SEED,
    ],
    MealType.MORNING_SNACK: [
        FoodCategory.FRUIT, FoodCategory.DAIRY, FoodCategory.NUT_SEED,
        FoodCategory.BEVERAGE,
    ],
    MealType.LUNCH: [
        FoodCategory.PROTEIN, FoodCategory.GRAIN, FoodCategory.VEGETABLE,
        FoodCategory.FAT, FoodCategory.LEGUME, FoodCategory.CARBOHYDRATE,
    ],
    MealType.AFTERNOON_SNACK: [
        FoodCategory.FRUIT, FoodCategory.DAIRY, FoodCategory.NUT_SEED,
        FoodCategory.BEVERAGE,
    ],
    MealType.DINNER: [
        FoodCategory.PROTEIN, FoodCategory.VEGETABLE, FoodCategory.GRAIN,
        FoodCategory.FAT, FoodCategory.LEGUME, FoodCategory.CARBOHYDRATE,
    ],
    MealType.EVENING_SNACK: [
        FoodCategory.DAIRY, FoodCategory.FRUIT, FoodCategory.NUT_SEED,
    ],
}

# ─── Base storage path ────────────────────────────────────────────
_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "storage_agents",
)


@dataclass
class DirectorReport:
    timestamp: str
    tasks_created: List[dict] = field(default_factory=list)
    system_health_score: int = 100
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "tasks_created": self.tasks_created,
            "system_health_score": self.system_health_score,
            "summary": self.summary,
        }


class DirectorAgent:
    """
    Scans system state and produces a prioritized task list.
    Never executes tasks — only defines and delegates.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self._storage_dir = storage_dir or _BASE_DIR
        self._tasks_dir = os.path.join(self._storage_dir, "tasks")
        self._audit_dir = os.path.join(self._storage_dir, "audit")
        self._reports_dir = os.path.join(self._audit_dir, "director_reports")
        self._plans_dir = os.path.join(self._storage_dir, "plans")

        # Ensure directories exist
        for d in [self._tasks_dir, self._reports_dir]:
            os.makedirs(d, exist_ok=True)

    # ─── Main entry point ─────────────────────────────────────────

    def run_analysis(self) -> DirectorReport:
        """Run full system analysis and produce a DirectorReport."""
        now = datetime.now(timezone.utc)
        report = DirectorReport(timestamp=now.isoformat())

        issues_found = 0
        high_issues = 0

        # 1. Food catalog gap check
        catalog_tasks, cat_issues, cat_high = self._check_catalog_gaps()
        report.tasks_created.extend(catalog_tasks)
        issues_found += cat_issues
        high_issues += cat_high

        # 2. Meal variety check
        variety_tasks, var_issues, var_high = self._check_meal_variety()
        report.tasks_created.extend(variety_tasks)
        issues_found += var_issues
        high_issues += var_high

        # 3. Meal time appropriateness check
        timing_tasks, tim_issues, tim_high = self._check_meal_timing()
        report.tasks_created.extend(timing_tasks)
        issues_found += tim_issues
        high_issues += tim_high

        # 4. Nutrition balance check
        balance_tasks, bal_issues, bal_high = self._check_nutrition_balance()
        report.tasks_created.extend(balance_tasks)
        issues_found += bal_issues
        high_issues += bal_high

        # Calculate health score
        report.system_health_score = self._calculate_health_score(issues_found, high_issues)

        # Generate Hebrew summary
        report.summary = self._generate_summary(report)

        # Persist tasks to pending_tasks.json
        self._save_pending_tasks(report.tasks_created)

        # Save report
        self._save_report(report, now)

        # Append to director log
        self._append_log(report, now)

        return report

    # ─── Check 1: Food Catalog Gaps ───────────────────────────────

    def _check_catalog_gaps(self):
        catalog = FoodCatalog()
        foods = catalog.get_all_foods()

        category_counts: Dict[str, int] = {}
        for cat in FoodCategory:
            category_counts[cat.value] = 0
        for food in foods:
            category_counts[food.category.value] = category_counts.get(food.category.value, 0) + 1

        tasks = []
        issues = 0
        high = 0
        for cat_val, count in category_counts.items():
            if count < 5:
                task = {
                    "task_id": str(uuid.uuid4()),
                    "type": "expand_catalog",
                    "agent": "agent_3_food",
                    "priority": "high",
                    "details": f"Category {cat_val} has only {count} foods. Add at least 5 more.",
                }
                tasks.append(task)
                issues += 1
                high += 1

        return tasks, issues, high

    # ─── Check 2: Meal Variety ────────────────────────────────────

    def _check_meal_variety(self):
        plans = self._load_recent_plans(7)
        if len(plans) < 2:
            return [], 0, 0

        food_id_counts: Dict[str, int] = {}
        for plan in plans:
            seen_in_plan = set()
            for meal in plan.get("meals", []):
                for item in meal.get("items", []):
                    fid = item.get("food_id", "")
                    if fid and fid not in seen_in_plan:
                        seen_in_plan.add(fid)
                        food_id_counts[fid] = food_id_counts.get(fid, 0) + 1

        total_plans = len(plans)
        threshold = total_plans * 0.6

        tasks = []
        issues = 0
        for fid, count in food_id_counts.items():
            if count > threshold:
                task = {
                    "task_id": str(uuid.uuid4()),
                    "type": "improve_variety",
                    "agent": "agent_5_planner",
                    "priority": "medium",
                    "details": f"food_id {fid} appears in {count}/{total_plans} plans. Force rotation.",
                }
                tasks.append(task)
                issues += 1

        return tasks, issues, 0

    # ─── Check 3: Meal Time Appropriateness ───────────────────────

    def _check_meal_timing(self):
        latest_plan = self._load_latest_plan()
        if latest_plan is None:
            return [], 0, 0

        catalog = FoodCatalog()
        tasks = []
        issues = 0
        high = 0

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
                    task = {
                        "task_id": str(uuid.uuid4()),
                        "type": "fix_meal_timing",
                        "agent": "agent_5_planner",
                        "priority": "high",
                        "details": (
                            f"{meal_type_str.upper()} contains "
                            f"{food.category.value.upper()} category item: {food.name_he}"
                        ),
                    }
                    tasks.append(task)
                    issues += 1
                    high += 1

        return tasks, issues, high

    # ─── Check 4: Nutrition Balance ───────────────────────────────

    def _check_nutrition_balance(self):
        latest_plan = self._load_latest_plan()
        if latest_plan is None:
            return [], 0, 0

        totals = latest_plan.get("totals", {})
        total_cal = totals.get("calories_kcal", 0)
        total_protein = totals.get("protein_g", 0)
        total_carbs = totals.get("carbs_g", 0)
        total_fat = totals.get("fat_g", 0)

        if total_cal <= 0:
            return [], 0, 0

        protein_cal = total_protein * 4
        carbs_cal = total_carbs * 4
        fat_cal = total_fat * 9
        macro_total = protein_cal + carbs_cal + fat_cal

        if macro_total <= 0:
            return [], 0, 0

        protein_pct = (protein_cal / macro_total) * 100
        carbs_pct = (carbs_cal / macro_total) * 100
        fat_pct = (fat_cal / macro_total) * 100

        tasks = []
        issues = 0

        if protein_pct < 25 or carbs_pct > 60:
            task = {
                "task_id": str(uuid.uuid4()),
                "type": "rebalance_macros",
                "agent": "agent_2_nutrition",
                "priority": "medium",
                "details": f"Current: protein {protein_pct:.1f}%, carbs {carbs_pct:.1f}%, fat {fat_pct:.1f}%",
            }
            tasks.append(task)
            issues += 1

        return tasks, issues, 0

    # ─── Health Score ─────────────────────────────────────────────

    def _calculate_health_score(self, total_issues: int, high_issues: int) -> int:
        score = 100
        score -= high_issues * 15
        score -= (total_issues - high_issues) * 8
        return max(0, min(100, score))

    # ─── Summary (Hebrew) ─────────────────────────────────────────

    def _generate_summary(self, report: DirectorReport) -> str:
        n = len(report.tasks_created)
        score = report.system_health_score
        if n == 0:
            return f"המערכת תקינה. ציון בריאות: {score}/100. לא נמצאו בעיות."
        types = {}
        for t in report.tasks_created:
            types[t["type"]] = types.get(t["type"], 0) + 1
        parts = [f"{v} משימות {k}" for k, v in types.items()]
        return f"נמצאו {n} בעיות. ציון בריאות: {score}/100. פירוט: {', '.join(parts)}."

    # ─── Storage helpers ──────────────────────────────────────────

    def _load_recent_plans(self, count: int) -> list:
        """Load last N meal plans from storage_agents/plans/."""
        plans_dir = self._plans_dir
        if not os.path.isdir(plans_dir):
            return []
        files = sorted(
            [f for f in os.listdir(plans_dir) if f.endswith(".json")],
            reverse=True,
        )
        plans = []
        for f in files[:count]:
            try:
                with open(os.path.join(plans_dir, f), "r", encoding="utf-8") as fh:
                    plans.append(json.load(fh))
            except (json.JSONDecodeError, OSError):
                continue
        return plans

    def _load_latest_plan(self) -> Optional[dict]:
        plans = self._load_recent_plans(1)
        return plans[0] if plans else None

    def _save_pending_tasks(self, new_tasks: list):
        path = os.path.join(self._tasks_dir, "pending_tasks.json")
        existing = []
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.extend(new_tasks)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def _save_report(self, report: DirectorReport, ts: datetime):
        filename = ts.strftime("%Y-%m-%d_%H-%M") + ".json"
        path = os.path.join(self._reports_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    def _append_log(self, report: DirectorReport, ts: datetime):
        log_path = os.path.join(self._audit_dir, "director_log.txt")
        line = (
            f"[{ts.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"tasks={len(report.tasks_created)} "
            f"health={report.system_health_score} "
            f"summary={report.summary}\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
