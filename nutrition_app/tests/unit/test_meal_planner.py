"""
Unit tests — Agent 5: Meal Planner
"""

import pytest
from nutrition_app.agents.agent_5_planner.meal_planner import MealPlanner
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.models.nutrition_targets import NutritionTargets
from nutrition_app.models.inventory import InventoryState


@pytest.fixture
def planner():
    catalog = FoodCatalog()
    foods = {f.food_id: f for f in catalog.get_all_foods()}
    p = MealPlanner()
    p.set_food_lookup(foods)
    return p


@pytest.fixture
def targets():
    return NutritionTargets(
        user_id="test_001",
        bmr_kcal=1700,
        tdee_kcal=2635,
        target_calories_kcal=2635,
        protein_g=164.7,
        carbs_g=296.4,
        fat_g=87.8,
    )


@pytest.fixture
def food_matches():
    catalog = FoodCatalog()
    return catalog.match_foods(["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "לחם", "עגבנייה"])


class TestPlanGeneration:
    def test_generates_meals(self, planner, targets, food_matches):
        plan = planner.generate_plan(targets, food_matches, InventoryState(), "run_001")
        assert len(plan.meals) > 0

    def test_plan_has_items(self, planner, targets, food_matches):
        plan = planner.generate_plan(targets, food_matches, InventoryState(), "run_001")
        total_items = sum(len(m.items) for m in plan.meals)
        assert total_items > 0

    def test_plan_respects_run_id(self, planner, targets, food_matches):
        plan = planner.generate_plan(targets, food_matches, InventoryState(), "run_xyz")
        assert plan.run_id == "run_xyz"

    def test_plan_has_calories(self, planner, targets, food_matches):
        plan = planner.generate_plan(targets, food_matches, InventoryState(), "run_001")
        assert plan.total_calories > 0


class TestPlanValidation:
    def test_empty_plan_fails_validation(self, planner):
        from nutrition_app.models.meal import MealPlan
        from datetime import date
        empty_plan = MealPlan(
            plan_id="empty", user_id="u", run_id="r",
            plan_date=date.today(), target_calories_kcal=2000
        )
        errors = planner.validate_plan(empty_plan)
        assert len(errors) > 0
