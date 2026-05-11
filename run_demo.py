"""
Smoke test — runs the full pipeline end-to-end with sample data.
Usage: python run_demo.py
"""

from datetime import date

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal
from nutrition_app.models.inventory import InventoryState
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.agents.agent_6_ai import AILayer


def main():
    # ── Step 1: User Profile ─────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Create User Profile")
    print("=" * 60)

    user = UserProfile(
        user_id="demo_001",
        name="ישראל ישראלי",
        gender=Gender.MALE,
        date_of_birth=date(1990, 5, 15),
        height_cm=178.0,
        weight_kg=82.0,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=Goal.LOSE_WEIGHT,
    )
    print(f"  Name: {user.name}")
    print(f"  Age: {user.age}")
    print(f"  Height: {user.height_cm}cm, Weight: {user.weight_kg}kg")
    print(f"  Activity: {user.activity_level.value}, Goal: {user.goal.value}")

    # ── Step 2: Calculate Nutrition Targets ───────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Calculate Nutrition Targets")
    print("=" * 60)

    engine = NutritionEngine()
    targets = engine.calculate_targets(user)

    print(f"  BMR:              {targets.bmr_kcal} kcal")
    print(f"  TDEE:             {targets.tdee_kcal} kcal")
    print(f"  Target Calories:  {targets.target_calories_kcal} kcal")
    print(f"  Protein:          {targets.protein_g}g ({targets.protein_pct}%)")
    print(f"  Carbs:            {targets.carbs_g}g ({targets.carbs_pct}%)")
    print(f"  Fat:              {targets.fat_g}g ({targets.fat_pct}%)")

    validation_errors = engine.validate_targets(targets)
    if validation_errors:
        print(f"  VALIDATION ERRORS: {validation_errors}")
    else:
        print("  Validation: OK")

    # ── Step 3: Match Foods ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Match Foods from Catalog")
    print("=" * 60)

    catalog = FoodCatalog()
    food_queries = ["חזה עוף", "אורז", "ביצה", "בננה", "שמן זית", "לחם", "עגבנייה", "קוטג׳", "מלפפון"]
    match_result = catalog.match_foods(food_queries)

    print(f"  Matched:        {len(match_result.matches)} items")
    for m in match_result.matches:
        print(f"    {m.query} -> {m.food_name} (confidence: {m.confidence_score:.2f}, {m.confidence_level.value})")

    if match_result.low_confidence:
        print(f"  Low confidence: {len(match_result.low_confidence)} items")
        for m in match_result.low_confidence:
            print(f"    {m.query} -> {m.food_name} (confidence: {m.confidence_score:.2f})")

    if match_result.unmatched:
        print(f"  Unmatched:      {match_result.unmatched}")

    print(f"  Requires decision: {match_result.requires_decision}")

    # ── Step 4: Check Inventory ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 4: Inventory Check")
    print("=" * 60)

    inv_manager = InventoryManager()
    inv_manager.add_item("demo_001", "food_001", 500.0, "gram")   # chicken
    inv_manager.add_item("demo_001", "food_002", 1000.0, "gram")  # rice
    inv_manager.add_item("demo_001", "food_003", 300.0, "gram")   # eggs
    inv_manager.add_item("demo_001", "food_004", 360.0, "gram")   # bananas

    state = inv_manager.get_state("demo_001")
    print(f"  Inventory items: {len(state.items)}")
    for item in state.items.values():
        print(f"    {item.food_id}: {item.quantity}g")

    # ── Step 5: Generate Meal Plan ───────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 5: Generate Meal Plan")
    print("=" * 60)

    planner = MealPlanner()
    food_lookup = {f.food_id: f for f in catalog.get_all_foods()}
    planner.set_food_lookup(food_lookup)

    plan = planner.generate_plan(
        targets=targets,
        food_matches=match_result,
        inventory=state,
        run_id="demo_run_001",
    )

    print(f"  Plan ID:    {plan.plan_id}")
    print(f"  Date:       {plan.plan_date}")
    print(f"  Meals:      {len(plan.meals)}")
    print(f"  Total kcal: {plan.total_calories}")
    print(f"  Deviation:  {plan.calorie_deviation_pct:+.1f}%")

    plan_errors = planner.validate_plan(plan)
    if plan_errors:
        print(f"  PLAN ERRORS: {plan_errors}")
    else:
        print("  Validation: OK")

    # ── Step 6: AI Summary ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 6: AI Summary (User-Facing Text)")
    print("=" * 60)

    ai = AILayer()
    summary = ai.generate_plan_summary(plan)
    print(summary)

    # ── Step 7: Deduct Inventory ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 7: Deduct Inventory (after confirmation)")
    print("=" * 60)

    changeset = inv_manager.deduct_for_plan("demo_001", plan, "demo_run_001")
    print(f"  Changes made: {len(changeset.changes)}")
    for change in changeset.changes:
        print(f"    {change.food_id}: {change.quantity_before}g -> {change.quantity_after}g ({change.quantity_delta:+.1f}g)")

    # ── Done ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
