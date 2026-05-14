"""
Workout Adjuster — adds workout burn & macro shift to NutritionTargets.
Owner: Agent 2 (Nutrition)

Deterministic only. No AI.
"""

from dataclasses import replace
from typing import Iterable, List

from nutrition_app.models.enums import WorkoutIntensity, WorkoutType
from nutrition_app.models.nutrition_targets import NutritionTargets
from nutrition_app.models.user import UserProfile
from nutrition_app.models.workout import WorkoutEntry


# ─── Intensity burn table (kcal/min/kg) ────────────────────────────
# Values derived from Compendium of Physical Activities MET equivalents.
INTENSITY_KCAL_PER_MIN_PER_KG = {
    WorkoutIntensity.LOW:      0.055,  # ~3 MET
    WorkoutIntensity.MODERATE: 0.093,  # ~5 MET
    WorkoutIntensity.HIGH:     0.140,  # ~7.5 MET
    WorkoutIntensity.EXTREME:  0.187,  # ~10 MET
}

# ─── MET values per workout type ───────────────────────────────────
# Values from the Compendium of Physical Activities (standard moderate pace).
MET_BY_TYPE = {
    # Cardio / endurance
    WorkoutType.RUNNING:        9.8,
    WorkoutType.WALKING:        3.5,
    WorkoutType.HIKING:         6.0,
    WorkoutType.CYCLING:        7.5,
    WorkoutType.SWIMMING:       8.0,
    WorkoutType.ROWING:         7.0,
    WorkoutType.ELLIPTICAL:     5.0,
    WorkoutType.STAIR_CLIMBING: 8.8,
    WorkoutType.JUMPING_ROPE:   11.8,
    # Strength / studio
    WorkoutType.STRENGTH:       5.0,
    WorkoutType.CROSSFIT:       8.0,
    WorkoutType.HIIT:           10.0,
    WorkoutType.PILATES:        3.0,
    WorkoutType.YOGA:           2.5,
    WorkoutType.DANCE:          5.5,
    # Combat sports
    WorkoutType.BOXING:         9.5,
    WorkoutType.KICKBOXING:     10.3,
    WorkoutType.MARTIAL_ARTS:   10.0,
    WorkoutType.WRESTLING:      7.0,
    # Ball sports
    WorkoutType.SOCCER:         8.5,
    WorkoutType.BASKETBALL:     8.0,
    WorkoutType.TENNIS:         7.3,
    WorkoutType.TABLE_TENNIS:   4.0,
    WorkoutType.BADMINTON:      5.5,
    WorkoutType.VOLLEYBALL:     4.0,
    WorkoutType.BASEBALL:       5.0,
    WorkoutType.HANDBALL:       12.0,
    WorkoutType.RUGBY:          8.3,
    WorkoutType.HOCKEY:         8.0,
    WorkoutType.GOLF:           4.8,
    # Outdoor / adventure
    WorkoutType.CLIMBING:       8.0,
    WorkoutType.SKIING:         7.0,
    WorkoutType.SNOWBOARDING:   5.3,
    WorkoutType.SURFING:        5.0,
    WorkoutType.SKATING:        7.0,
    # Fallback
    WorkoutType.OTHER:          5.0,
}

# ─── Intensity multiplier for type mode ────────────────────────────
# When the user picks a sport AND specifies intensity, the MET value
# is scaled by this factor (light tennis rally vs. competitive match).
TYPE_INTENSITY_MULTIPLIER = {
    WorkoutIntensity.LOW:      0.80,
    WorkoutIntensity.MODERATE: 1.00,
    WorkoutIntensity.HIGH:     1.20,
    WorkoutIntensity.EXTREME:  1.40,
}

# ─── Distance-based calorie estimation (kcal per kg per km) ─────────
# For running/walking/hiking, distance is the primary input when the user
# provides it. Values are well-established approximations for flat terrain.
DISTANCE_KCAL_PER_KG_PER_KM = {
    WorkoutType.RUNNING: 1.036,
    WorkoutType.WALKING: 0.53,
    WorkoutType.HIKING:  0.70,
}

DISTANCE_SUPPORTED_TYPES = set(DISTANCE_KCAL_PER_KG_PER_KM.keys())

# ─── Workout-day macro distribution (% of total calories) ──────────
# Relative to baseline MACRO_DISTRIBUTION in nutrition_engine.py:
# more carbs for energy, more protein for recovery, less fat.
WORKOUT_DAY_MACRO_DISTRIBUTION = {
    "lose_weight": {"protein_pct": 0.32, "carbs_pct": 0.45, "fat_pct": 0.23},
    "maintain":    {"protein_pct": 0.28, "carbs_pct": 0.50, "fat_pct": 0.22},
    "gain_weight": {"protein_pct": 0.28, "carbs_pct": 0.54, "fat_pct": 0.18},
}


def estimate_calories_burned(entry: WorkoutEntry, user_weight_kg: float) -> float:
    """Estimate calories burned for a workout entry based on its mode.

    Modes:
    - "intensity":  INTENSITY_KCAL_PER_MIN_PER_KG × weight × duration
    - "type":       either
                       (a) distance-based for running/walking/hiking when
                           distance_km > 0:  kcal/kg/km × weight × distance,
                       (b) MET × weight × hours  (duration-based),
                    scaled by TYPE_INTENSITY_MULTIPLIER if an intensity
                    is also provided.
    """
    # ── intensity-only mode ────────────────────────────────────────
    if entry.mode == "intensity" and entry.intensity is not None:
        if entry.duration_minutes <= 0:
            return 0.0
        rate = INTENSITY_KCAL_PER_MIN_PER_KG[entry.intensity]
        return round(rate * user_weight_kg * entry.duration_minutes, 1)

    # ── type mode ──────────────────────────────────────────────────
    if entry.mode == "type" and entry.workout_type is not None:
        base = 0.0
        # Prefer distance-based calc when type supports it and distance provided
        distance = getattr(entry, "distance_km", None) or 0.0
        if entry.workout_type in DISTANCE_SUPPORTED_TYPES and distance > 0:
            rate = DISTANCE_KCAL_PER_KG_PER_KM[entry.workout_type]
            base = rate * user_weight_kg * distance
        elif entry.duration_minutes > 0:
            met = MET_BY_TYPE[entry.workout_type]
            base = met * user_weight_kg * (entry.duration_minutes / 60.0)

        if base <= 0:
            return 0.0

        # Optional intensity scaling on top of the type
        if entry.intensity is not None:
            base *= TYPE_INTENSITY_MULTIPLIER[entry.intensity]

        return round(base, 1)

    return 0.0


def _macros_from_calories(calories: float, dist: dict) -> tuple:
    """Shared helper: convert calories + macro % distribution → (protein_g, carbs_g, fat_g)."""
    protein_g = round((calories * dist["protein_pct"]) / 4.0, 1)
    carbs_g = round((calories * dist["carbs_pct"]) / 4.0, 1)
    fat_g = round((calories * dist["fat_pct"]) / 9.0, 1)
    return protein_g, carbs_g, fat_g


def adjust_targets_for_workouts(
    targets: NutritionTargets,
    workouts: Iterable[WorkoutEntry],
    user: UserProfile,
) -> NutritionTargets:
    """
    Return a new NutritionTargets adjusted for all workouts done on a day:
    - target_calories_kcal += sum of estimated burns across all workouts
    - macros recalculated using workout-day distribution if any burn > 0

    Each workout entry gets its `estimated_calories_burned` field populated.
    """
    total_burn = 0.0
    for w in workouts:
        burn = estimate_calories_burned(w, user.weight_kg)
        w.estimated_calories_burned = burn
        total_burn += burn

    if total_burn <= 0:
        return targets

    total_burn = round(total_burn, 1)
    new_calories = round(targets.target_calories_kcal + total_burn, 1)
    dist = WORKOUT_DAY_MACRO_DISTRIBUTION[user.goal.value]
    protein_g, carbs_g, fat_g = _macros_from_calories(new_calories, dist)

    return replace(
        targets,
        target_calories_kcal=new_calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        calculation_method=(
            f"{targets.calculation_method} + workout_adjustment(+{int(total_burn)}kcal)"
        ),
    )


def adjust_targets_for_workout(
    targets: NutritionTargets,
    workout: WorkoutEntry,
    user: UserProfile,
) -> NutritionTargets:
    """Backwards-compatible single-workout wrapper."""
    return adjust_targets_for_workouts(targets, [workout], user)
