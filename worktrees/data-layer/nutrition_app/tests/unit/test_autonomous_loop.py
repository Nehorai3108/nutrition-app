"""
Integration test — Autonomous loop convergence.
Verifies the full system produces a valid plan.
"""

import pytest
from datetime import date

from nutrition_app.models.enums import Gender, ActivityLevel, Goal
from nutrition_app.models.user import UserProfile
from nutrition_app.models.inventory import InventoryState
from nutrition_app.agents.agent_2_nutrition.nutrition_engine import NutritionEngine
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.agents.agent_5_planner.meal_planner import MealPlanner


@pytest.fixture
def full_pipeline():
    """Set up the full pipeline components."""
    user = UserProfile(
        user_id="integration_test",
        name="Test User",
        gender=Gender.MALE,
        date_of_birth=date(1990, 5, 15),
        height_cm=178.0,
        weight_kg=82.0,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=Goal.LOSE_WEIGHT,
    )
    engine = NutritionEngine()
    targets = engine.calculate_targets(user)

    catalog = FoodCatalog(load_extended=True)
    all_foods = catalog.get_all_foods()
    food_lookup = {f.food_id: f for f in all_foods}

    match_result = catalog.match_foods(
        ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית",
         "עגבנייה", "יוגורט", "סלמון", "קינואה", "שקדים",
         "ברוקולי", "תפוח", "לחם"]
    )

    inv = InventoryState(items={})

    planner = MealPlanner(food_catalog_lookup=food_lookup)

    return planner, targets, match_result, inv


class TestFullPipeline:
    def test_produces_valid_plan(self, full_pipeline):
        planner, targets, match_result, inv = full_pipeline
        plan = planner.generate_plan(targets, match_result, inv, "integration_run")

        # At least 3 meals with items
        meals_with_items = sum(1 for m in plan.meals if m.items)
        assert meals_with_items >= 3, f"Only {meals_with_items} meals have items"

        # Calories within +/-15%
        assert abs(plan.calorie_deviation_pct) <= 15, (
            f"Deviation {plan.calorie_deviation_pct:+.1f}% exceeds bounds"
        )

        # Macro targets
        p_cal = plan.total_protein * 4
        c_cal = plan.total_carbs * 4
        f_cal = plan.total_fat * 9
        m_total = p_cal + c_cal + f_cal
        assert m_total > 0

        protein_pct = (p_cal / m_total) * 100
        carbs_pct = (c_cal / m_total) * 100
        assert protein_pct >= 20, f"Protein {protein_pct:.1f}% too low"
        assert carbs_pct <= 65, f"Carbs {carbs_pct:.1f}% too high"

        # No timing violations
        violations = planner._check_timing_violations(plan)
        assert violations == [], f"Timing violations: {violations}"

        # At least 8 unique foods
        unique = set(item.food_id for m in plan.meals for item in m.items)
        assert len(unique) >= 8, f"Only {len(unique)} unique foods"

    def test_validation_passes(self, full_pipeline):
        planner, targets, match_result, inv = full_pipeline
        plan = planner.generate_plan(targets, match_result, inv, "validation_run")
        errors = planner.validate_plan(plan)
        assert errors == [], f"Validation errors: {errors}"

    def test_converges_within_iterations(self, full_pipeline):
        """The system should produce a valid plan within 3 attempts."""
        planner, targets, match_result, inv = full_pipeline

        for i in range(3):
            plan = planner.generate_plan(
                targets, match_result, inv,
                f"convergence_{i}", seed_offset=i
            )
            errors = planner.validate_plan(plan)
            if not errors:
                break

        assert not errors, f"Failed to converge after 3 attempts: {errors}"
