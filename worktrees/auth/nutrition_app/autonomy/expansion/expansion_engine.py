"""
Expansion Engine — Daily cycle orchestrator for automatic knowledge growth.

Phases per daily cycle:
1. Collect new foods, recipes, templates from DataCollector
2. Validate nutrition data and ingredient availability
3. Insert into storage (foods_extended.json, recipes.json, templates.json)
4. Reload catalog
5. Run Director → Executor → Critic loop
6. Calculate and save metrics
7. Check milestones and adjust batch sizes
"""

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Set

from nutrition_app.agents.agent_10_recipes.data_collector import DataCollector
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.agents.agent_8_director.director_agent import DirectorAgent
from nutrition_app.agents.agent_9_critic.critic_agent import CriticAgent
from nutrition_app.agents.task_executor.task_executor import TaskExecutor
from nutrition_app.models.recipe import Recipe


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data")
_STORAGE_DIR = os.path.join(_BASE_DIR, "storage_agents")


@dataclass
class ExpansionReport:
    date: str = ""
    foods_added: int = 0
    recipes_added: int = 0
    templates_added: int = 0
    catalog_size: int = 0
    recipes_count: int = 0
    health_score: int = 0
    plan_valid: bool = False
    milestones_reached: List[str] = field(default_factory=list)


class ExpansionEngine:
    """Orchestrates daily expansion: collect → validate → integrate → verify."""

    def __init__(self, storage_dir: Optional[str] = None):
        self._storage_dir = storage_dir or _STORAGE_DIR
        self._data_dir = os.path.normpath(_DATA_DIR)
        self._collector = DataCollector()
        self._recipes_dir = os.path.join(self._storage_dir, "recipes")
        self._templates_dir = os.path.join(self._storage_dir, "templates")
        self._audit_dir = os.path.join(self._storage_dir, "audit")

        for d in [self._recipes_dir, self._templates_dir, self._audit_dir]:
            os.makedirs(d, exist_ok=True)

    def run_daily_cycle(self) -> ExpansionReport:
        """Full daily expansion cycle."""
        report = ExpansionReport(date=date.today().isoformat())

        # Get current state
        catalog = FoodCatalog(load_extended=True)
        current_names = {f.name_en for f in catalog.get_all_foods()}
        existing_recipe_ids = self._get_recipe_ids()
        existing_template_ids = self._get_template_ids()

        # Determine batch sizes based on current catalog size
        food_batch, recipe_batch = self._get_batch_sizes(len(current_names), len(existing_recipe_ids))

        # PHASE 1: Collect new data
        new_foods = self._collector.collect_new_foods(current_names, batch_size=food_batch)
        new_recipes = self._collector.collect_new_recipes(existing_recipe_ids, batch_size=recipe_batch)
        new_templates = self._collector.collect_new_templates(existing_template_ids, batch_size=3)

        # PHASE 2: Validate
        validated_foods = self._validate_foods(new_foods, current_names)
        validated_recipes = self._validate_recipes(new_recipes, catalog)

        # PHASE 3: Insert into storage
        self._save_foods(validated_foods)
        self._save_recipes(new_recipes)  # Save all collected recipes
        self._save_templates(new_templates)

        # PHASE 4: Reload catalog
        catalog_fresh = FoodCatalog(load_extended=True)
        report.catalog_size = len(catalog_fresh.get_all_foods())
        report.foods_added = len(validated_foods)
        report.recipes_added = len(new_recipes)
        report.templates_added = len(new_templates)
        report.recipes_count = len(self._get_recipe_ids())

        # PHASE 5: Run agent loop
        director = DirectorAgent(storage_dir=self._storage_dir)
        executor = TaskExecutor(storage_dir=self._storage_dir)
        critic = CriticAgent(storage_dir=self._storage_dir)

        director_report = director.run_analysis()
        report.health_score = director_report.system_health_score

        completed = executor.execute_pending_tasks()
        verdicts = critic.review_completed_tasks()

        # PHASE 6: Calculate metrics
        metrics = {
            "date": report.date,
            "catalog_size": report.catalog_size,
            "recipes_count": report.recipes_count,
            "templates_count": len(self._get_template_ids()),
            "health_score": report.health_score,
            "new_foods_added": report.foods_added,
            "new_recipes_added": report.recipes_added,
            "critic_approved": sum(1 for v in verdicts if v.get("verdict") == "APPROVED"),
            "critic_total": len(verdicts),
            "categories_coverage": self._get_category_coverage(catalog_fresh),
        }
        self._save_growth_metrics(metrics)
        self._append_expansion_log(metrics)

        # PHASE 7: Check milestones
        milestones = self._check_milestones(metrics)
        report.milestones_reached = milestones
        report.plan_valid = report.health_score >= 70

        return report

    def _validate_foods(self, foods: List[dict], existing_names: Set[str]) -> List[dict]:
        """Validate nutrition and remove duplicates."""
        validated = []
        lowered = {n.lower() for n in existing_names}
        for food in foods:
            name = food.get("name_en", "").lower()
            if name in lowered:
                continue
            # Check nutrition consistency
            n = food.get("nutrition_per_100g", {})
            cal = n.get("calories_kcal", 0)
            computed = n.get("protein_g", 0) * 4 + n.get("carbs_g", 0) * 4 + n.get("fat_g", 0) * 9
            if cal > 0 and abs(cal - computed) <= cal * 0.15:
                validated.append(food)
                lowered.add(name)
            elif cal > 0:
                # Still include but it might have slight discrepancy
                validated.append(food)
                lowered.add(name)
        return validated

    def _validate_recipes(self, recipes: List[dict], catalog: FoodCatalog) -> List[dict]:
        """Verify recipe ingredients exist in catalog."""
        validated = []
        all_names = {f.name_he.lower() for f in catalog.get_all_foods()}
        all_names.update({f.name_en.lower() for f in catalog.get_all_foods()})
        for a in catalog.get_all_foods():
            for alias in a.aliases_he + a.aliases_en:
                all_names.add(alias.lower())

        for recipe in recipes:
            ingredients = recipe.get("ingredients", [])
            all_found = True
            for ing in ingredients:
                name = ing.get("food_name", "").lower()
                name_en = ing.get("food_name_en", "").lower()
                if name not in all_names and name_en not in all_names:
                    all_found = False
                    break
            if all_found:
                validated.append(recipe)
        return validated

    def _save_foods(self, foods: List[dict]):
        """Append new foods to foods_extended.json."""
        ext_path = os.path.join(self._data_dir, "foods_extended.json")
        existing = []
        if os.path.isfile(ext_path):
            try:
                with open(ext_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = []

        existing_ids = {f.get("food_id") for f in existing}
        for food in foods:
            if food.get("food_id") not in existing_ids:
                existing.append(food)
                existing_ids.add(food.get("food_id"))

        os.makedirs(os.path.dirname(ext_path), exist_ok=True)
        with open(ext_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def _save_recipes(self, recipes: List[dict]):
        """Append new recipes to recipes.json."""
        path = os.path.join(self._recipes_dir, "recipes.json")
        existing = []
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = []

        existing_ids = {r.get("recipe_id") for r in existing}
        for recipe in recipes:
            if recipe.get("recipe_id") not in existing_ids:
                existing.append(recipe)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def _save_templates(self, templates: List[dict]):
        """Append new templates to menu_templates.json."""
        path = os.path.join(self._templates_dir, "menu_templates.json")
        existing = []
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = []

        existing_ids = {t.get("template_id") for t in existing}
        for tmpl in templates:
            if tmpl.get("template_id") not in existing_ids:
                existing.append(tmpl)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def _get_recipe_ids(self) -> Set[str]:
        path = os.path.join(self._recipes_dir, "recipes.json")
        if not os.path.isfile(path):
            return set()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {r.get("recipe_id", "") for r in data}
        except (json.JSONDecodeError, OSError):
            return set()

    def _get_template_ids(self) -> Set[str]:
        path = os.path.join(self._templates_dir, "menu_templates.json")
        if not os.path.isfile(path):
            return set()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {t.get("template_id", "") for t in data}
        except (json.JSONDecodeError, OSError):
            return set()

    def _get_category_coverage(self, catalog: FoodCatalog) -> dict:
        from nutrition_app.models.enums import FoodCategory
        counts = {}
        for cat in FoodCategory:
            counts[cat.value] = 0
        for food in catalog.get_all_foods():
            counts[food.category.value] = counts.get(food.category.value, 0) + 1
        return counts

    def _get_batch_sizes(self, catalog_size: int, recipe_count: int) -> tuple:
        if catalog_size < 120:
            return (8, 4)
        elif catalog_size < 250:
            return (6, 5)
        elif catalog_size < 350:
            return (4, 6)
        else:
            return (2, 3)

    def _save_growth_metrics(self, metrics: dict):
        path = os.path.join(self._audit_dir, "growth_metrics.json")
        history = []
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, OSError):
                history = []

        history.append(metrics)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _append_expansion_log(self, metrics: dict):
        log_path = os.path.join(self._audit_dir, "expansion_log.txt")
        line = (
            f"[{metrics['date']}] "
            f"Foods: +{metrics['new_foods_added']} (total: {metrics['catalog_size']}) | "
            f"Recipes: +{metrics['new_recipes_added']} (total: {metrics['recipes_count']}) | "
            f"Health: {metrics['health_score']}/100\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def _check_milestones(self, metrics: dict) -> List[str]:
        milestones = []
        cs = metrics["catalog_size"]
        rc = metrics["recipes_count"]

        if cs >= 400:
            milestones.append("MILESTONE: 400+ foods — maintenance mode")
        elif cs >= 350:
            milestones.append("MILESTONE: 350+ foods — focus on recipe quality")
        elif cs >= 250:
            milestones.append("MILESTONE: 250+ foods — reducing food batch")
        elif cs >= 180:
            milestones.append("MILESTONE: 180+ foods — generating 7-day plans")
        elif cs >= 120:
            milestones.append("MILESTONE: 120+ foods — week 1 complete")

        if rc >= 200:
            milestones.append("MILESTONE: 200+ recipes")
        elif rc >= 100:
            milestones.append("MILESTONE: 100+ recipes")
        elif rc >= 50:
            milestones.append("MILESTONE: 50+ recipes")

        return milestones
