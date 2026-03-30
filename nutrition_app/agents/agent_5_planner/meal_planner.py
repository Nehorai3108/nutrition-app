"""
Agent 5 — Meal Planning Engine Owner

Responsibility:
- Build daily meal plan
- Match to nutrition targets
- Use available inventory
- Split into meals
- Deterministic meal construction

Input:  NutritionTargets, FoodMatchResult, InventoryState
Output: MealPlan

Rules:
- MUST NOT modify inventory
- MUST NOT modify targets
- MUST stay within defined deviation tolerances
- Prefer available (inventory) food when possible

Forbidden:
- AI generation
- DB writes
- Inventory deduction
- Contract changes
"""

import uuid
from datetime import date, datetime
from typing import List, Optional

from nutrition_app.models.enums import MealType
from nutrition_app.models.food_item import FoodItem
from nutrition_app.models.food_match import FoodMatchResult
from nutrition_app.models.inventory import InventoryState
from nutrition_app.models.meal import Meal, MealItem, MealPlan
from nutrition_app.models.nutrition_targets import NutritionTargets


# ─── Meal Distribution (% of daily calories per meal) ───────────────
MEAL_DISTRIBUTION = {
    MealType.BREAKFAST: 0.25,
    MealType.MORNING_SNACK: 0.10,
    MealType.LUNCH: 0.30,
    MealType.AFTERNOON_SNACK: 0.10,
    MealType.DINNER: 0.25,
}

# ─── Acceptable Deviation Tolerance ─────────────────────────────────
MAX_CALORIE_DEVIATION_PCT = 5.0  # ±5% from target
MAX_MACRO_DEVIATION_PCT = 10.0    # ±10% per macro


class MealPlanner:
    """Deterministic meal plan builder. No AI, no writes."""

    def __init__(self, food_catalog_lookup=None):
        self._food_lookup = food_catalog_lookup or {}

    def set_food_lookup(self, foods: dict):
        """Set food_id -> FoodItem lookup dict."""
        self._food_lookup = foods

    def generate_plan(
        self,
        targets: NutritionTargets,
        food_matches: FoodMatchResult,
        inventory: InventoryState,
        run_id: str,
    ) -> MealPlan:
        plan_id = str(uuid.uuid4())

        # Collect available food_ids from high/medium confidence matches
        available_food_ids = [m.food_id for m in food_matches.matches if m.food_id]

        meals = []
        for meal_type, calorie_pct in MEAL_DISTRIBUTION.items():
            meal_calories = targets.target_calories_kcal * calorie_pct
            meal = self._build_meal(
                meal_type=meal_type,
                target_calories=meal_calories,
                available_food_ids=available_food_ids,
                inventory=inventory,
                targets=targets,
                calorie_pct=calorie_pct,
            )
            meals.append(meal)

        return MealPlan(
            plan_id=plan_id,
            user_id=targets.user_id,
            run_id=run_id,
            plan_date=date.today(),
            meals=meals,
            target_calories_kcal=targets.target_calories_kcal,
        )

    def _build_meal(
        self,
        meal_type: MealType,
        target_calories: float,
        available_food_ids: List[str],
        inventory: InventoryState,
        targets: NutritionTargets,
        calorie_pct: float,
    ) -> Meal:
        """Build a single meal targeting the given calorie amount."""
        items = []
        remaining_calories = target_calories

        # Distribute macros proportionally
        target_protein = targets.protein_g * calorie_pct
        target_carbs = targets.carbs_g * calorie_pct
        target_fat = targets.fat_g * calorie_pct

        for food_id in available_food_ids:
            if remaining_calories <= 10:
                break

            food = self._food_lookup.get(food_id)
            if food is None:
                continue

            # Calculate portion to contribute ~portion of remaining calories
            if food.nutrition_per_100g.calories_kcal <= 0:
                continue

            portion_g = min(
                food.default_serving_g,
                (remaining_calories / food.nutrition_per_100g.calories_kcal) * 100,
            )
            portion_g = round(max(10.0, portion_g), 1)

            macros = food.macros_for_grams(portion_g)

            # Check if in inventory
            from_inventory = False
            inv_item_id = None
            inv_item = inventory.get_by_food_id(food_id)
            if inv_item and inv_item.quantity >= portion_g:
                from_inventory = True
                inv_item_id = inv_item.inventory_item_id

            items.append(MealItem(
                food_id=food_id,
                food_name=food.name_he,
                quantity_g=portion_g,
                calories_kcal=macros["calories_kcal"],
                protein_g=macros["protein_g"],
                carbs_g=macros["carbs_g"],
                fat_g=macros["fat_g"],
                from_inventory=from_inventory,
                inventory_item_id=inv_item_id,
            ))

            remaining_calories -= macros["calories_kcal"]

        return Meal(meal_type=meal_type, items=items)

    def validate_plan(self, plan: MealPlan) -> List[str]:
        """Validate that plan meets deviation tolerances."""
        errors = []

        if plan.target_calories_kcal > 0:
            dev = abs(plan.calorie_deviation_pct)
            if dev > MAX_CALORIE_DEVIATION_PCT:
                errors.append(
                    f"Calorie deviation {plan.calorie_deviation_pct}% "
                    f"exceeds ±{MAX_CALORIE_DEVIATION_PCT}%"
                )

        if not plan.meals:
            errors.append("Plan has no meals")

        return errors
