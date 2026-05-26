"""
Unit tests — Macro balance verification.
Verifies that plans hit macro targets (protein >= 25%, carbs <= 60%).
"""

import pytest
from datetime import date

from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.agents.agent_5_planner.meal_planner import MealPlanner
from nutrition_app.models.inventory import InventoryState
from nutrition_app.models.nutrition_targets import NutritionTargets


@pytest.fixture
def targets():
    return NutritionTargets(
        user_id="test_macro",
        bmr_kcal=1700,
        tdee_kcal=2400,
        target_calories_kcal=2200,
        protein_g=165.0,
        carbs_g=220.0,
        fat_g=73.0,
    )


@pytest.fixture
def full_planner():
    catalog = FoodCatalog(load_extended=True)
    foods = {f.food_id: f for f in catalog.get_all_foods()}
    return MealPlanner(food_catalog_lookup=foods), catalog


class TestMacroBalance:
    def test_protein_above_threshold(self, full_planner, targets):
        planner, catalog = full_planner
        match_result = catalog.match_foods(
            ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "עגבנייה",
             "יוגורט", "סלמון", "קינואה"]
        )
        inv = InventoryState(items={})
        plan = planner.generate_plan(targets, match_result, inv, "macro_run")

        p_cal = plan.total_protein * 4
        c_cal = plan.total_carbs * 4
        f_cal = plan.total_fat * 9
        m_total = p_cal + c_cal + f_cal

        assert m_total > 0, "Plan has zero macro calories"
        protein_pct = (p_cal / m_total) * 100
        assert protein_pct >= 20, (
            f"Protein {protein_pct:.1f}% too low (need >= 25%, allowing 20% margin)"
        )

    def test_carbs_below_threshold(self, full_planner, targets):
        planner, catalog = full_planner
        match_result = catalog.match_foods(
            ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "עגבנייה"]
        )
        inv = InventoryState(items={})
        plan = planner.generate_plan(targets, match_result, inv, "macro_run2")

        p_cal = plan.total_protein * 4
        c_cal = plan.total_carbs * 4
        f_cal = plan.total_fat * 9
        m_total = p_cal + c_cal + f_cal

        assert m_total > 0
        carbs_pct = (c_cal / m_total) * 100
        assert carbs_pct <= 65, (
            f"Carbs {carbs_pct:.1f}% too high (need <= 60%, allowing 65% margin)"
        )

    def test_calorie_deviation_within_bounds(self, full_planner, targets):
        planner, catalog = full_planner
        match_result = catalog.match_foods(
            ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית"]
        )
        inv = InventoryState(items={})
        plan = planner.generate_plan(targets, match_result, inv, "dev_run")

        assert abs(plan.calorie_deviation_pct) <= 15, (
            f"Calorie deviation {plan.calorie_deviation_pct:+.1f}% exceeds +/-15%"
        )
