"""
Unit tests — Meal timing category enforcement.
Verifies that the planner respects meal-type category rules.
"""

import pytest
from datetime import date

from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.agents.agent_5_planner.meal_planner import (
    MEAL_CATEGORY_RULES,
    MealPlanner,
)
from nutrition_app.models.enums import FoodCategory, MealType
from nutrition_app.models.inventory import InventoryState
from nutrition_app.models.nutrition_targets import NutritionTargets


@pytest.fixture
def full_planner():
    catalog = FoodCatalog(load_extended=True)
    foods = {f.food_id: f for f in catalog.get_all_foods()}
    p = MealPlanner(food_catalog_lookup=foods)
    return p, catalog


@pytest.fixture
def targets():
    return NutritionTargets(
        user_id="test_timing",
        bmr_kcal=1700,
        tdee_kcal=2400,
        target_calories_kcal=2200,
        protein_g=165.0,
        carbs_g=220.0,
        fat_g=73.0,
    )


class TestMealCategoryRules:
    def test_all_meal_types_have_rules(self):
        """Every meal type in MEAL_DISTRIBUTION should have category rules."""
        from nutrition_app.agents.agent_5_planner.meal_planner import MEAL_DISTRIBUTION
        for meal_type in MEAL_DISTRIBUTION:
            assert meal_type in MEAL_CATEGORY_RULES, (
                f"Missing category rules for {meal_type.value}"
            )

    def test_breakfast_allows_dairy(self):
        assert FoodCategory.DAIRY in MEAL_CATEGORY_RULES[MealType.BREAKFAST]

    def test_breakfast_allows_grains(self):
        assert FoodCategory.GRAIN in MEAL_CATEGORY_RULES[MealType.BREAKFAST]

    def test_lunch_allows_protein(self):
        assert FoodCategory.PROTEIN in MEAL_CATEGORY_RULES[MealType.LUNCH]

    def test_lunch_allows_vegetables(self):
        assert FoodCategory.VEGETABLE in MEAL_CATEGORY_RULES[MealType.LUNCH]

    def test_dinner_allows_protein(self):
        assert FoodCategory.PROTEIN in MEAL_CATEGORY_RULES[MealType.DINNER]

    def test_snacks_allow_fruit(self):
        assert FoodCategory.FRUIT in MEAL_CATEGORY_RULES[MealType.MORNING_SNACK]
        assert FoodCategory.FRUIT in MEAL_CATEGORY_RULES[MealType.AFTERNOON_SNACK]


class TestNoTimingViolations:
    def test_generated_plan_has_no_violations(self, full_planner, targets):
        planner, catalog = full_planner
        match_result = catalog.match_foods(
            ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "עגבנייה", "יוגורט"]
        )
        inv = InventoryState(items={})
        plan = planner.generate_plan(targets, match_result, inv, "timing_test")
        violations = planner._check_timing_violations(plan)
        assert violations == [], f"Timing violations found: {violations}"

    def test_no_protein_in_breakfast(self, full_planner, targets):
        """Breakfast should not contain pure protein items (chicken, beef)."""
        planner, catalog = full_planner
        match_result = catalog.match_foods(
            ["חזה עוף", "אורז", "ביצה", "בננה", "סלמון", "יוגורט"]
        )
        inv = InventoryState(items={})
        plan = planner.generate_plan(targets, match_result, inv, "timing_test2")

        breakfast = next(
            (m for m in plan.meals if m.meal_type == MealType.BREAKFAST), None
        )
        assert breakfast is not None

        protein_foods = {FoodCategory.PROTEIN}
        allowed = set(MEAL_CATEGORY_RULES[MealType.BREAKFAST])

        for item in breakfast.items:
            food = planner._food_lookup.get(item.food_id)
            if food:
                assert food.category in allowed, (
                    f"Breakfast contains {food.category.value} item: {food.name_en}"
                )
