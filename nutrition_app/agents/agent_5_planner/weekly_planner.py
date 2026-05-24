"""
WeeklyPlanner — turn UserMealPreferences into a 7-day WeeklyPlan.

Round-robins through `picks[meal_type]` for each weekday and then applies
`fixed_day_overrides` on top (e.g. "friday.breakfast = treat variant"). The
daily targets come from NutritionTargets so we can flag deviations.

For post_workout / treat we currently place them on MORNING_SNACK /
EVENING_SNACK slots so they live inside the existing MealPlan model without
needing a MealType-enum migration (see plan decision #3).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional

from nutrition_app.models.enums import MealType
from nutrition_app.models.meal import Meal, MealItem, MealPlan
from nutrition_app.models.user_meal_preferences import (
    MEAL_TYPE_KEYS,
    UserMealPreferences,
    UserRecipeVariant,
    WEEKDAYS,
)
from nutrition_app.models.weekly_plan import WeeklyPlan


# Map our 5 picker meal-type keys → existing MealType enum slots.
_MEAL_TYPE_TO_ENUM: Dict[str, MealType] = {
    "breakfast": MealType.BREAKFAST,
    "lunch":     MealType.LUNCH,
    "dinner":    MealType.DINNER,
    "post_workout": MealType.MORNING_SNACK,
    "treat":     MealType.EVENING_SNACK,
}


def _monday_of(target: date) -> date:
    return target - timedelta(days=target.weekday())


def _variant_to_meal_item(variant: UserRecipeVariant) -> MealItem:
    nut = variant.total_nutrition or {}
    return MealItem(
        food_id=variant.variant_id,
        food_name=variant.name,
        quantity_g=0.0,                            # variant carries portion implicitly
        calories_kcal=nut.get("calories", 0) or 0,
        protein_g=nut.get("protein", 0) or 0,
        carbs_g=nut.get("carbs", 0) or 0,
        fat_g=nut.get("fat", 0) or 0,
    )


class WeeklyPlanner:

    def generate(
        self,
        user_id: str,
        preferences: UserMealPreferences,
        target_calories_kcal: float = 2000.0,
        target_protein_g: float = 120.0,
        target_carbs_g: float = 250.0,
        target_fat_g: float = 65.0,
        week_start: Optional[date] = None,
    ) -> WeeklyPlan:
        """Build a 7-day plan rotating through *preferences.picks*."""
        if week_start is None:
            week_start = _monday_of(date.today())
        plan_id = f"weekly_{uuid.uuid4().hex[:10]}"

        plan = WeeklyPlan(
            plan_id=plan_id,
            user_id=user_id,
            week_start=week_start,
            target_calories_kcal=target_calories_kcal,
            target_protein_g=target_protein_g,
            target_carbs_g=target_carbs_g,
            target_fat_g=target_fat_g,
        )

        variants_by_id = {v.variant_id: v for v in preferences.variants}

        for day_idx, weekday in enumerate(WEEKDAYS):
            plan_date = week_start + timedelta(days=day_idx)
            day_plan = MealPlan(
                plan_id=f"{plan_id}_{weekday}",
                user_id=user_id,
                run_id=plan_id,
                plan_date=plan_date,
                target_calories_kcal=target_calories_kcal,
            )

            for meal_type in MEAL_TYPE_KEYS:
                variant_id = self._select_variant_for(
                    preferences, weekday, meal_type, day_idx,
                )
                if not variant_id:
                    continue
                variant = variants_by_id.get(variant_id)
                if not variant:
                    continue
                meal_type_enum = _MEAL_TYPE_TO_ENUM[meal_type]
                day_plan.meals.append(Meal(
                    meal_type=meal_type_enum,
                    items=[_variant_to_meal_item(variant)],
                ))

            plan.days[weekday] = day_plan
        return plan

    @staticmethod
    def _select_variant_for(
        prefs: UserMealPreferences,
        weekday: str,
        meal_type: str,
        day_idx: int,
    ) -> Optional[str]:
        """Fixed override wins; otherwise round-robin the picks."""
        override_key = f"{weekday}.{meal_type}"
        if override_key in prefs.fixed_day_overrides:
            return prefs.fixed_day_overrides[override_key]
        picks = prefs.picks.get(meal_type) or []
        if not picks:
            return None
        return picks[day_idx % len(picks)]
