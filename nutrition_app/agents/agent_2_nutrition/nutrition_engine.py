"""
Agent 2 — Nutrition Engine Owner

Responsibility:
- Calculate BMR (Mifflin-St Jeor)
- Calculate TDEE
- Calculate target calories based on goal
- Calculate macro distribution
- Validation rules around nutrition calculations

Input:  UserProfile
Output: NutritionTargets

Rules:
- Deterministic only
- No AI
- No undocumented heuristics
- Consistent, defined rounding

Forbidden:
- Food selection
- Inventory access
- Meal plan creation
- Storage design
"""

from nutrition_app.models.user import UserProfile
from nutrition_app.models.nutrition_targets import NutritionTargets
from nutrition_app.models.enums import Gender, Goal


# ─── Activity Multipliers (Mifflin-St Jeor standard) ────────────────
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "extra_active": 1.9,
}

# ─── Calorie Adjustment by Goal ─────────────────────────────────────
GOAL_CALORIE_ADJUSTMENT = {
    "lose_weight": -500,     # 500 kcal deficit
    "maintain": 0,
    "gain_weight": +300,     # 300 kcal surplus
}

# ─── Macro Distribution (% of total calories) ───────────────────────
MACRO_DISTRIBUTION = {
    "lose_weight":  {"protein_pct": 0.30, "carbs_pct": 0.40, "fat_pct": 0.30},
    "maintain":     {"protein_pct": 0.25, "carbs_pct": 0.45, "fat_pct": 0.30},
    "gain_weight":  {"protein_pct": 0.25, "carbs_pct": 0.50, "fat_pct": 0.25},
}


class NutritionEngine:
    """Deterministic nutrition calculator. No AI, no heuristics."""

    def calculate_targets(self, user: UserProfile) -> NutritionTargets:
        bmr = self._calculate_bmr(user)
        tdee = self._calculate_tdee(bmr, user.activity_level.value)
        target_calories = self._calculate_target_calories(tdee, user.goal.value)
        protein_g, carbs_g, fat_g = self._calculate_macros(target_calories, user.goal.value)

        return NutritionTargets(
            user_id=user.user_id,
            bmr_kcal=bmr,
            tdee_kcal=tdee,
            target_calories_kcal=target_calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g_min=25.0,
            fiber_g_max=38.0,
            calculation_method="mifflin_st_jeor",
        )

    def _calculate_bmr(self, user: UserProfile) -> float:
        """
        Mifflin-St Jeor Equation:
        Male:   10 * weight(kg) + 6.25 * height(cm) - 5 * age(y) + 5
        Female: 10 * weight(kg) + 6.25 * height(cm) - 5 * age(y) - 161
        """
        base = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age
        if user.gender == Gender.MALE:
            bmr = base + 5
        else:
            bmr = base - 161
        return round(bmr, 1)

    def _calculate_tdee(self, bmr: float, activity_level: str) -> float:
        multiplier = ACTIVITY_MULTIPLIERS[activity_level]
        return round(bmr * multiplier, 1)

    def _calculate_target_calories(self, tdee: float, goal: str) -> float:
        adjustment = GOAL_CALORIE_ADJUSTMENT[goal]
        target = tdee + adjustment
        # Minimum safe calorie floor
        target = max(target, 1200.0)
        return round(target, 1)

    def _calculate_macros(self, target_calories: float, goal: str) -> tuple:
        """
        Returns (protein_g, carbs_g, fat_g) based on goal-specific distribution.
        Protein: 4 kcal/g
        Carbs:   4 kcal/g
        Fat:     9 kcal/g
        """
        dist = MACRO_DISTRIBUTION[goal]
        protein_g = round((target_calories * dist["protein_pct"]) / 4.0, 1)
        carbs_g = round((target_calories * dist["carbs_pct"]) / 4.0, 1)
        fat_g = round((target_calories * dist["fat_pct"]) / 9.0, 1)
        return protein_g, carbs_g, fat_g

    def validate_targets(self, targets: NutritionTargets) -> list:
        """Validate calculated targets for consistency."""
        errors = []
        if targets.bmr_kcal <= 0:
            errors.append("BMR must be positive")
        if targets.tdee_kcal < targets.bmr_kcal:
            errors.append("TDEE cannot be less than BMR")
        if targets.target_calories_kcal < 1200:
            errors.append("Target calories below safe minimum (1200)")
        if targets.protein_g <= 0 or targets.carbs_g <= 0 or targets.fat_g <= 0:
            errors.append("All macros must be positive")

        # Verify macro calories roughly match target
        macro_cals = targets.protein_g * 4 + targets.carbs_g * 4 + targets.fat_g * 9
        deviation = abs(macro_cals - targets.target_calories_kcal)
        if deviation > 10:  # Allow 10 kcal rounding tolerance
            errors.append(
                f"Macro calories ({macro_cals:.1f}) deviate from target "
                f"({targets.target_calories_kcal:.1f}) by {deviation:.1f} kcal"
            )
        return errors
