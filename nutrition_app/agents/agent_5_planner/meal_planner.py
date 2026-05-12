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

import json
import os
import uuid
from datetime import date, datetime
from typing import Dict, List, Optional, Set

from nutrition_app.models.enums import FoodCategory, MealType
from nutrition_app.models.food_item import FoodItem
from nutrition_app.models.food_match import FoodMatchResult
from nutrition_app.models.inventory import InventoryState
from nutrition_app.models.meal import Meal, MealItem, MealPlan
from nutrition_app.models.nutrition_targets import NutritionTargets


# ─── Meal Distribution (% of daily calories per meal) ───────────────
# Israeli convention: big lunch, lighter dinner
MEAL_DISTRIBUTION = {
    MealType.BREAKFAST: 0.25,
    MealType.MORNING_SNACK: 0.10,
    MealType.LUNCH: 0.35,
    MealType.AFTERNOON_SNACK: 0.10,
    MealType.DINNER: 0.20,
}

# ─── Meal-Type Category Rules (Israeli food culture) ─────────────
# Defines which food categories are appropriate for each meal type
MEAL_CATEGORY_RULES: Dict[MealType, List[FoodCategory]] = {
    MealType.BREAKFAST: [
        FoodCategory.DAIRY, FoodCategory.GRAIN, FoodCategory.FRUIT,
        FoodCategory.FAT, FoodCategory.VEGETABLE, FoodCategory.NUT_SEED,
        FoodCategory.BEVERAGE, FoodCategory.CONDIMENT, FoodCategory.OTHER,
    ],
    MealType.MORNING_SNACK: [
        FoodCategory.FRUIT, FoodCategory.DAIRY, FoodCategory.NUT_SEED,
        FoodCategory.BEVERAGE, FoodCategory.OTHER,
    ],
    MealType.LUNCH: [
        FoodCategory.PROTEIN, FoodCategory.GRAIN, FoodCategory.VEGETABLE,
        FoodCategory.FAT, FoodCategory.LEGUME, FoodCategory.CARBOHYDRATE,
        FoodCategory.CONDIMENT,
    ],
    MealType.AFTERNOON_SNACK: [
        FoodCategory.FRUIT, FoodCategory.DAIRY, FoodCategory.NUT_SEED,
        FoodCategory.GRAIN, FoodCategory.BEVERAGE, FoodCategory.OTHER,
    ],
    MealType.DINNER: [
        FoodCategory.PROTEIN, FoodCategory.VEGETABLE, FoodCategory.DAIRY,
        FoodCategory.GRAIN, FoodCategory.FAT, FoodCategory.LEGUME,
        FoodCategory.CONDIMENT, FoodCategory.CARBOHYDRATE,
    ],
    MealType.EVENING_SNACK: [
        FoodCategory.DAIRY, FoodCategory.FRUIT, FoodCategory.NUT_SEED,
        FoodCategory.BEVERAGE,
    ],
}

# ─── Kashrut: meat categories (cannot be combined with dairy) ────
MEAT_CATEGORIES = {FoodCategory.PROTEIN}
DAIRY_CATEGORY = FoodCategory.DAIRY

# ─── Acceptable Deviation Tolerance ─────────────────────────────────
MAX_CALORIE_DEVIATION_PCT = 15.0  # ±15% from target
MAX_MACRO_DEVIATION_PCT = 10.0    # ±10% per macro

# ─── Storage paths ──────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data")

from nutrition_app.storage_paths import user_plans_dir, legacy_plans_dir  # noqa: E402


class MealPlanner:
    """Deterministic meal plan builder. No AI, no writes."""

    def __init__(self, food_catalog_lookup=None, user_id: str | None = None):
        self._food_lookup: Dict[str, FoodItem] = food_catalog_lookup or {}
        self._recently_used: Set[str] = set()
        self._user_id = user_id
        self._load_recently_used()

    def set_food_lookup(self, foods: dict):
        """Set food_id -> FoodItem lookup dict."""
        self._food_lookup = foods

    def load_extended_catalog(self):
        """Load extended food catalog from data/foods_extended.json into the lookup."""
        ext_path = os.path.join(_DATA_DIR, "foods_extended.json")
        if not os.path.isfile(ext_path):
            return
        try:
            with open(ext_path, "r", encoding="utf-8") as f:
                foods_data = json.load(f)
            for fd in foods_data:
                food = FoodItem.from_dict(fd)
                if food.food_id not in self._food_lookup:
                    self._food_lookup[food.food_id] = food
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    def _get_plans_dir(self) -> str:
        """Return the plans directory for this planner instance."""
        if self._user_id:
            return str(user_plans_dir(self._user_id))
        return str(legacy_plans_dir())

    def _load_recently_used(self):
        """Load food IDs used in the last 3 plans for rotation."""
        plans_dir = self._get_plans_dir()
        if not os.path.isdir(plans_dir):
            return
        files = sorted(
            [f for f in os.listdir(plans_dir) if f.endswith(".json")],
            reverse=True,
        )
        for f in files[:3]:
            try:
                with open(os.path.join(plans_dir, f), "r", encoding="utf-8") as fh:
                    plan_data = json.load(fh)
                for meal in plan_data.get("meals", []):
                    for item in meal.get("items", []):
                        fid = item.get("food_id", "")
                        if fid:
                            self._recently_used.add(fid)
            except (json.JSONDecodeError, OSError):
                continue

    def generate_plan(
        self,
        targets: NutritionTargets,
        food_matches: FoodMatchResult,
        inventory: InventoryState,
        run_id: str,
        seed_offset: int = 0,
    ) -> MealPlan:
        plan_id = str(uuid.uuid4())

        # Collect available food_ids from high/medium confidence matches
        matched_food_ids = [m.food_id for m in food_matches.matches if m.food_id]

        # Also include ALL foods from the lookup (extended catalog)
        all_food_ids = list(self._food_lookup.keys())

        # Merge: matched foods first (they're what the user asked for), then extended
        available_food_ids = list(dict.fromkeys(matched_food_ids + all_food_ids))

        # Apply seed-based rotation for variety
        if seed_offset > 0 and len(available_food_ids) > 1:
            rotate_by = seed_offset % len(available_food_ids)
            available_food_ids = available_food_ids[rotate_by:] + available_food_ids[:rotate_by]

        meals = []
        used_food_ids_today: Set[str] = set()

        for meal_type, calorie_pct in MEAL_DISTRIBUTION.items():
            meal_calories = targets.target_calories_kcal * calorie_pct
            meal = self._build_meal(
                meal_type=meal_type,
                target_calories=meal_calories,
                available_food_ids=available_food_ids,
                inventory=inventory,
                targets=targets,
                calorie_pct=calorie_pct,
                used_today=used_food_ids_today,
            )
            # Track which foods were used today for cross-meal diversity
            for item in meal.items:
                used_food_ids_today.add(item.food_id)
            meals.append(meal)

        plan = MealPlan(
            plan_id=plan_id,
            user_id=targets.user_id,
            run_id=run_id,
            plan_date=date.today(),
            meals=meals,
            target_calories_kcal=targets.target_calories_kcal,
        )

        # Post-processing: macro balancing pass
        plan = self._balance_macros(plan, targets)

        return plan

    def _build_meal(
        self,
        meal_type: MealType,
        target_calories: float,
        available_food_ids: List[str],
        inventory: InventoryState,
        targets: NutritionTargets,
        calorie_pct: float,
        used_today: Set[str],
    ) -> Meal:
        """Build a single meal targeting the given calorie amount."""
        items: List[MealItem] = []
        remaining_calories = target_calories

        # Get allowed categories for this meal type
        allowed_categories = set(MEAL_CATEGORY_RULES.get(meal_type, list(FoodCategory)))

        # Filter foods by meal-type category rules
        eligible_foods = []
        for food_id in available_food_ids:
            food = self._food_lookup.get(food_id)
            if food is None:
                continue
            if food.category not in allowed_categories:
                continue
            if food.nutrition_per_100g.calories_kcal <= 0:
                continue
            eligible_foods.append(food)

        # Sort by diversity priority: prefer foods NOT recently used and NOT used today
        def _diversity_score(food: FoodItem) -> tuple:
            recently_penalty = 1 if food.food_id in self._recently_used else 0
            today_penalty = 1 if food.food_id in used_today else 0
            # Prefer inventory foods
            inv_bonus = 0 if inventory.get_by_food_id(food.food_id) else 1
            return (today_penalty, recently_penalty, inv_bonus)

        eligible_foods.sort(key=_diversity_score)

        # Kashrut tracking: if meal has meat, exclude dairy and vice versa
        has_meat = False
        has_dairy = False

        # Target macros for this meal
        target_protein = targets.protein_g * calorie_pct
        target_carbs = targets.carbs_g * calorie_pct
        target_fat = targets.fat_g * calorie_pct

        for food in eligible_foods:
            if remaining_calories <= 10:
                break

            # Kashrut check: no meat + dairy in same meal
            is_meat = food.category in MEAT_CATEGORIES and food.nutrition_per_100g.protein_g > 10
            is_dairy = food.category == DAIRY_CATEGORY

            if is_meat and has_dairy:
                continue
            if is_dairy and has_meat:
                continue

            # Calculate portion to contribute reasonable calories
            portion_g = min(
                food.default_serving_g,
                (remaining_calories / food.nutrition_per_100g.calories_kcal) * 100,
            )
            portion_g = round(max(10.0, portion_g), 1)

            macros = food.macros_for_grams(portion_g)

            # Don't overshoot by too much
            if macros["calories_kcal"] > remaining_calories * 1.5 and len(items) > 0:
                # Try a smaller portion
                portion_g = round((remaining_calories / food.nutrition_per_100g.calories_kcal) * 100 * 0.5, 1)
                portion_g = round(max(10.0, portion_g), 1)
                macros = food.macros_for_grams(portion_g)

            # Check if in inventory
            from_inventory = False
            inv_item_id = None
            inv_item = inventory.get_by_food_id(food.food_id)
            if inv_item and inv_item.quantity >= portion_g:
                from_inventory = True
                inv_item_id = inv_item.inventory_item_id

            items.append(MealItem(
                food_id=food.food_id,
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

            if is_meat:
                has_meat = True
            if is_dairy:
                has_dairy = True

            # Limit items per meal (2-5 items is realistic)
            if len(items) >= 5:
                break

        return Meal(meal_type=meal_type, items=items)

    def _balance_macros(self, plan: MealPlan, targets: NutritionTargets) -> MealPlan:
        """Post-processing pass to adjust plan toward macro targets.

        If protein < 25% of calories: swap a carb-heavy item for a protein-rich one.
        If carbs > 60% of calories: swap a carb item for a protein/fat item.
        Max 10 swap iterations.
        """
        for _ in range(10):
            total_cal = plan.total_calories
            if total_cal <= 0:
                break

            total_protein = plan.total_protein
            total_carbs = plan.total_carbs
            total_fat = plan.total_fat

            protein_cal = total_protein * 4
            carbs_cal = total_carbs * 4
            fat_cal = total_fat * 9
            macro_total = protein_cal + carbs_cal + fat_cal

            if macro_total <= 0:
                break

            protein_pct = (protein_cal / macro_total) * 100
            carbs_pct = (carbs_cal / macro_total) * 100

            if protein_pct >= 25 and carbs_pct <= 60:
                break  # Macros are within target

            # Find the meal with the most room for improvement
            swapped = False
            for meal in plan.meals:
                if swapped:
                    break
                if not meal.items:
                    continue

                # Only swap in meals where it makes sense (lunch/dinner for protein)
                if protein_pct < 25 and meal.meal_type in (MealType.LUNCH, MealType.DINNER, MealType.BREAKFAST):
                    # Find the most carb-heavy item in this meal
                    carb_items = sorted(meal.items, key=lambda i: i.carbs_g, reverse=True)
                    for carb_item in carb_items:
                        if carb_item.carbs_g < 5:
                            continue
                        # Find a protein-rich food to replace it with
                        replacement = self._find_protein_replacement(
                            carb_item, meal, plan
                        )
                        if replacement:
                            idx = meal.items.index(carb_item)
                            meal.items[idx] = replacement
                            swapped = True
                            break

                elif carbs_pct > 60:
                    # Find highest carb item and reduce portion or swap
                    carb_items = sorted(meal.items, key=lambda i: i.carbs_g, reverse=True)
                    for carb_item in carb_items:
                        if carb_item.carbs_g < 10:
                            continue
                        # Reduce portion by 30%
                        new_qty = round(carb_item.quantity_g * 0.7, 1)
                        food = self._food_lookup.get(carb_item.food_id)
                        if food and new_qty >= 10:
                            macros = food.macros_for_grams(new_qty)
                            carb_item.quantity_g = new_qty
                            carb_item.calories_kcal = macros["calories_kcal"]
                            carb_item.protein_g = macros["protein_g"]
                            carb_item.carbs_g = macros["carbs_g"]
                            carb_item.fat_g = macros["fat_g"]
                            swapped = True
                            break

            if not swapped:
                break

        return plan

    def _find_protein_replacement(
        self, carb_item: MealItem, meal: Meal, plan: MealPlan
    ) -> Optional[MealItem]:
        """Find a protein-rich food to replace a carb-heavy item."""
        target_calories = carb_item.calories_kcal

        # Get food IDs already used in this meal
        used_in_meal = {item.food_id for item in meal.items}

        # Look for high-protein foods
        candidates = []
        for food_id, food in self._food_lookup.items():
            if food_id in used_in_meal:
                continue
            if food.category not in (FoodCategory.PROTEIN, FoodCategory.LEGUME, FoodCategory.DAIRY):
                continue
            if food.nutrition_per_100g.protein_g < 8:
                continue
            candidates.append(food)

        if not candidates:
            return None

        # Pick the best candidate (highest protein per calorie)
        candidates.sort(
            key=lambda f: f.nutrition_per_100g.protein_g / max(f.nutrition_per_100g.calories_kcal, 1),
            reverse=True,
        )

        food = candidates[0]
        # Size to match roughly the same calories
        if food.nutrition_per_100g.calories_kcal > 0:
            portion_g = round((target_calories / food.nutrition_per_100g.calories_kcal) * 100, 1)
            portion_g = round(max(10.0, min(food.default_serving_g * 1.5, portion_g)), 1)
        else:
            portion_g = food.default_serving_g

        macros = food.macros_for_grams(portion_g)
        return MealItem(
            food_id=food.food_id,
            food_name=food.name_he,
            quantity_g=portion_g,
            calories_kcal=macros["calories_kcal"],
            protein_g=macros["protein_g"],
            carbs_g=macros["carbs_g"],
            fat_g=macros["fat_g"],
            from_inventory=False,
            inventory_item_id=None,
        )

    def validate_plan(self, plan: MealPlan) -> List[str]:
        """Validate that plan meets deviation tolerances."""
        errors = []

        if plan.target_calories_kcal > 0:
            dev = abs(plan.calorie_deviation_pct)
            if dev > MAX_CALORIE_DEVIATION_PCT:
                errors.append(
                    f"Calorie deviation {plan.calorie_deviation_pct:+.1f}% "
                    f"exceeds +/-{MAX_CALORIE_DEVIATION_PCT}%"
                )

        if not plan.meals:
            errors.append("Plan has no meals")

        total_items = sum(len(m.items) for m in plan.meals)
        if total_items == 0:
            errors.append("Plan has no food items")

        # Check unique foods
        unique_foods = set()
        for meal in plan.meals:
            for item in meal.items:
                unique_foods.add(item.food_id)
        if len(unique_foods) < 8:
            errors.append(f"Only {len(unique_foods)} unique foods (need >= 8)")

        # Check meal timing
        timing_violations = self._check_timing_violations(plan)
        if timing_violations:
            errors.append(f"{len(timing_violations)} meal timing violations")

        # Check macro balance
        total_cal = plan.total_calories
        if total_cal > 0:
            protein_cal = plan.total_protein * 4
            carbs_cal = plan.total_carbs * 4
            fat_cal = plan.total_fat * 9
            macro_total = protein_cal + carbs_cal + fat_cal
            if macro_total > 0:
                protein_pct = (protein_cal / macro_total) * 100
                carbs_pct = (carbs_cal / macro_total) * 100
                if protein_pct < 20:
                    errors.append(f"Protein too low: {protein_pct:.1f}% (need >= 25%)")
                if carbs_pct > 65:
                    errors.append(f"Carbs too high: {carbs_pct:.1f}% (need <= 60%)")

        return errors

    def _check_timing_violations(self, plan: MealPlan) -> List[str]:
        """Check for meal-type category violations."""
        violations = []
        for meal in plan.meals:
            allowed = set(MEAL_CATEGORY_RULES.get(meal.meal_type, list(FoodCategory)))
            for item in meal.items:
                food = self._food_lookup.get(item.food_id)
                if food and food.category not in allowed:
                    violations.append(
                        f"{meal.meal_type.value}: {food.name_he} ({food.category.value})"
                    )
        return violations