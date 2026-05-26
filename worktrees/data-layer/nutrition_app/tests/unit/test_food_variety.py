"""
Unit tests — Food variety and rotation.
Verifies that the planner uses diverse foods across plans.
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
        user_id="test_variety",
        bmr_kcal=1700,
        tdee_kcal=2400,
        target_calories_kcal=2200,
        protein_g=165.0,
        carbs_g=220.0,
        fat_g=73.0,
    )


class TestExtendedCatalog:
    def test_catalog_loads_extended_foods(self):
        catalog = FoodCatalog(load_extended=True)
        foods = catalog.get_all_foods()
        assert len(foods) > 20, f"Only {len(foods)} foods loaded (expected 70+)"

    def test_extended_catalog_has_all_categories(self):
        catalog = FoodCatalog(load_extended=True)
        foods = catalog.get_all_foods()
        from nutrition_app.models.enums import FoodCategory

        categories_found = set()
        for food in foods:
            categories_found.add(food.category)

        # Should have at least these categories
        for cat in [
            FoodCategory.PROTEIN, FoodCategory.GRAIN, FoodCategory.VEGETABLE,
            FoodCategory.FRUIT, FoodCategory.DAIRY, FoodCategory.FAT,
            FoodCategory.LEGUME, FoodCategory.NUT_SEED,
        ]:
            assert cat in categories_found, f"Missing category: {cat.value}"


class TestFoodDiversity:
    def test_plan_uses_at_least_8_unique_foods(self, targets):
        catalog = FoodCatalog(load_extended=True)
        foods = {f.food_id: f for f in catalog.get_all_foods()}
        planner = MealPlanner(food_catalog_lookup=foods)
        match_result = catalog.match_foods(
            ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "עגבנייה",
             "יוגורט", "סלמון", "קינואה", "שקדים"]
        )
        inv = InventoryState(items={})
        plan = planner.generate_plan(targets, match_result, inv, "variety_run")

        unique_foods = set()
        for meal in plan.meals:
            for item in meal.items:
                unique_foods.add(item.food_id)

        assert len(unique_foods) >= 8, (
            f"Only {len(unique_foods)} unique foods (need >= 8)"
        )

    def test_different_seeds_produce_different_plans(self, targets):
        catalog = FoodCatalog(load_extended=True)
        foods = {f.food_id: f for f in catalog.get_all_foods()}
        match_result = catalog.match_foods(["חזה עוף", "אורז", "ביצה"])
        inv = InventoryState(items={})

        plans_foods = []
        for seed in range(3):
            planner = MealPlanner(food_catalog_lookup=dict(foods))
            plan = planner.generate_plan(
                targets, match_result, inv, f"seed_{seed}", seed_offset=seed * 10
            )
            food_ids = set(
                item.food_id for m in plan.meals for item in m.items
            )
            plans_foods.append(food_ids)

        # At least 2 of 3 plans should differ
        all_same = plans_foods[0] == plans_foods[1] == plans_foods[2]
        assert not all_same, "All 3 plans have identical foods — no rotation"

    def test_multiple_plans_cover_many_unique_foods(self, targets):
        """Across 3 plans, we should see at least 15 unique foods."""
        catalog = FoodCatalog(load_extended=True)
        foods = {f.food_id: f for f in catalog.get_all_foods()}
        match_result = catalog.match_foods(
            ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית"]
        )
        inv = InventoryState(items={})

        all_foods_seen = set()
        for seed in range(3):
            planner = MealPlanner(food_catalog_lookup=dict(foods))
            plan = planner.generate_plan(
                targets, match_result, inv, f"multi_{seed}", seed_offset=seed * 7
            )
            for m in plan.meals:
                for item in m.items:
                    all_foods_seen.add(item.food_id)

        assert len(all_foods_seen) >= 15, (
            f"Only {len(all_foods_seen)} unique foods across 3 plans (need >= 15)"
        )
