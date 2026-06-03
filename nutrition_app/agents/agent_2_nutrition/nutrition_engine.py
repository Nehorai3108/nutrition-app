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

from typing import List

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

# ─── Calorie Deficit/Surplus by Goal + Pace ─────────────────────────
# pace: "slow" / "moderate" / "fast"
# 1 kg body fat ≈ 7700 kcal
GOAL_CALORIE_ADJUSTMENT = {
    "lose_weight": {
        "slow":     -275,   # ~0.25 kg/week
        "moderate": -550,   # ~0.5  kg/week
        "fast":     -1100,  # ~1.0  kg/week
    },
    "maintain": {
        "slow": 0, "moderate": 0, "fast": 0,
    },
    "gain_weight": {
        "slow":     +200,   # lean bulk ~0.2 kg/week
        "moderate": +350,   # ~0.35 kg/week
        "fast":     +500,   # ~0.5  kg/week
    },
}

# ─── Protein targets (g per kg body weight) ─────────────────────────
# Evidence-based ranges (ISSN, ACSM guidelines):
PROTEIN_PER_KG = {
    "lose_weight": 2.0,   # High protein preserves muscle during deficit
    "maintain":    1.8,
    "gain_weight": 1.8,   # Enough to support hypertrophy
}

# ─── Fat: minimum for hormonal health (g per kg body weight) ─────────
FAT_MIN_PER_KG = 0.8   # ~0.8–1.0 g/kg is hormonal floor


class NutritionEngine:
    """Deterministic nutrition calculator. No AI, no heuristics."""

    def calculate_targets(self, user: UserProfile,
                          pace: str = "moderate",
                          target_weight_kg: float = None,
                          weekly_change_kg: float = None) -> NutritionTargets:
        """
        weekly_change_kg: if provided, overrides pace.
          e.g. 0.5 → 0.5 kg/week loss (for lose_weight) or gain (for gain_weight)
        """
        bmr  = self._calculate_bmr(user)
        tdee = self._calculate_tdee(bmr, user.activity_level.value)

        if weekly_change_kg is not None and weekly_change_kg > 0:
            # Convert kg/week → kcal/day  (1 kg body fat ≈ 7700 kcal)
            kcal_per_day = round(weekly_change_kg * 7700 / 7)
            if user.goal.value == "lose_weight":
                adjustment = -kcal_per_day
            elif user.goal.value == "gain_weight":
                adjustment = +kcal_per_day
            else:
                adjustment = 0
            target_calories = max(round(tdee + adjustment, 1), 1200.0)
            weekly_delta_kg = weekly_change_kg
        else:
            target_calories = self._calculate_target_calories(tdee, user.goal.value, pace)
            weekly_delta_kg = abs(
                GOAL_CALORIE_ADJUSTMENT[user.goal.value].get(pace, 0)
            ) / 7700.0

        protein_g, carbs_g, fat_g = self._calculate_macros(
            target_calories, user.goal.value, user.weight_kg
        )

        # Weeks to goal
        weeks_to_goal = None
        if target_weight_kg and target_weight_kg != user.weight_kg and weekly_delta_kg > 0:
            delta_kg = abs(target_weight_kg - user.weight_kg)
            weeks_to_goal = round(delta_kg / weekly_delta_kg)

        notes = f"weekly={weekly_change_kg or ''}kg"
        if weeks_to_goal:
            notes += f", ~{weeks_to_goal} שבועות ליעד"

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
            calculation_method="mifflin_st_jeor_v2",
            notes=notes,
        )

    def _calculate_bmr(self, user: UserProfile) -> float:
        """
        Mifflin-St Jeor Equation:
        Male:   10 * weight(kg) + 6.25 * height(cm) - 5 * age(y) + 5
        Female: 10 * weight(kg) + 6.25 * height(cm) - 5 * age(y) - 161
        """
        base = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age
        bmr = base + 5 if user.gender == Gender.MALE else base - 161
        return round(bmr, 1)

    def _calculate_tdee(self, bmr: float, activity_level: str) -> float:
        multiplier = ACTIVITY_MULTIPLIERS[activity_level]
        return round(bmr * multiplier, 1)

    def _calculate_target_calories(self, tdee: float, goal: str, pace: str) -> float:
        adjustment = GOAL_CALORIE_ADJUSTMENT[goal].get(pace, 0)
        target = tdee + adjustment
        # Safety floor: never below 1200 kcal
        target = max(target, 1200.0)
        return round(target, 1)

    def _calculate_macros(self, target_calories: float,
                          goal: str, weight_kg: float) -> tuple:
        """
        Evidence-based macro calculation:
        - Protein: fixed g/kg body weight (preserves muscle, supports goals)
        - Fat:     minimum g/kg for hormonal health, then fill based on goal
        - Carbs:   remaining calories
        """
        # Protein: g/kg → kcal → g
        protein_g = round(PROTEIN_PER_KG[goal] * weight_kg, 1)
        protein_kcal = protein_g * 4

        # Fat: minimum floor
        fat_g_min = round(FAT_MIN_PER_KG * weight_kg, 1)

        # Remaining calories for fat + carbs
        remaining = target_calories - protein_kcal

        if goal == "lose_weight":
            # Higher fat, lower carbs helps satiety
            fat_pct_of_remaining = 0.40
        elif goal == "gain_weight":
            # More carbs for energy and anabolic signalling
            fat_pct_of_remaining = 0.25
        else:  # maintain
            fat_pct_of_remaining = 0.33

        fat_kcal = max(remaining * fat_pct_of_remaining, fat_g_min * 9)
        fat_g = round(fat_kcal / 9, 1)

        carbs_kcal = target_calories - protein_kcal - fat_g * 9
        carbs_g = round(max(carbs_kcal, 0) / 4, 1)

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


def calculate_hydration_goal(weight_kg: float) -> float:
    """
    Return recommended daily water goal in ml based on body weight.

    Formula: 35 ml/kg, rounded to the nearest 50 ml.
    Clamped: minimum 1500 ml, maximum 4000 ml.
    Returns 2000.0 when weight_kg is unknown (0 or negative).
    """
    if weight_kg > 0:
        return max(1500.0, min(4000.0, round(weight_kg * 35 / 50) * 50))
    return 2000.0


def adjust_targets_for_workouts(
    targets: NutritionTargets,
    workouts: List,
    user: UserProfile,
) -> NutritionTargets:
    """Add workout calorie burn to daily targets, redistributing across macros."""
    total_burn = sum(w.estimated_calories_burned for w in workouts)
    if total_burn <= 0:
        return targets

    new_target = targets.target_calories_kcal + total_burn

    engine = NutritionEngine()
    protein_g, carbs_g, fat_g = engine._calculate_macros(new_target, user.goal.value)

    return NutritionTargets(
        user_id=targets.user_id,
        bmr_kcal=targets.bmr_kcal,
        tdee_kcal=targets.tdee_kcal,
        target_calories_kcal=round(new_target, 1),
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        fiber_g_min=targets.fiber_g_min,
        fiber_g_max=targets.fiber_g_max,
        calculation_method=targets.calculation_method,
        notes=f"Adjusted for {len(workouts)} workout(s), +{total_burn:.0f} kcal",
    )
