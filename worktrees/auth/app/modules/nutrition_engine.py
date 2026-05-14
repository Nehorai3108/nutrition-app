"""
Nutrition Engine — Agent 2 Implementation
==========================================
OWNED BY:  Agent 2
REPLACES:  Agent 1 stub

Responsibilities:
- BMR  : Mifflin-St Jeor formula
- TDEE : BMR × activity (PAL) multiplier
- Calorie target : TDEE ± goal delta  (or manual override)
- Macro targets  : configurable protein / carbs / fat split

Isolation rules (from contracts.md §9):
- Must NOT import MealPlanningEngine or InventoryManager
- Must NOT call any AI service
- Must produce identical output for identical input (deterministic)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.food_item import FoodItem


# ── Physical constants (kcal/g — immutable, not configurable) ─────────────────

_KCAL_PER_G_PROTEIN: float = 4.0
_KCAL_PER_G_CARBS:   float = 4.0
_KCAL_PER_G_FAT:     float = 9.0


# ── Configuration (Agent 2 authority — all values live here) ──────────────────

# PAL multipliers: ActivityLevel enum value → multiplier
# Source: Mifflin-St Jeor standard PAL table
_ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary":          1.2,
    "lightly_active":     1.375,
    "moderately_active":  1.55,
    "very_active":        1.725,
    "extra_active":       1.9,
}

# Calorie delta applied to TDEE per goal
_GOAL_CALORIE_DELTA: dict[str, int] = {
    "lose_weight":  -500,
    "maintain":        0,
    "gain_muscle":  +300,
}

# Macro split as fraction of total kcal (must sum to 1.0)
_MACRO_RATIO: dict[str, float] = {
    "protein": 0.30,
    "carbs":   0.40,
    "fat":     0.30,
}

# Safety floor — enforced after goal delta, before returning calorie_target
# Must stay >= 800 (hard lower bound defined in contracts.md §6.2)
_CALORIE_SAFETY_FLOOR: int = 1200


# ── Output Contract (structure frozen by Agent 1 — do not change fields) ──────

@dataclass
class NutritionProfile:
    """
    OUTPUT CONTRACT — what Agent 2 must produce.
    This structure is frozen by Agent 1 and cannot be changed without
    a contract revision affecting Agents 5 and 8.

    CONSUMED BY:
    - Agent 5 (Meal Planning Engine): uses calorie_target
    - Agent 8 (Mobile App): displays all fields to the user

    FIELD CONSTRAINTS (Agent 1 authority):
    - calorie_target   : int, must be >= 800
    - bmr              : float, must be > 0
    - tdee             : float, must be >= bmr
    - *_target_g       : float, must be >= 0
    - user_id          : str (UUID), must match a valid User.id
    """
    user_id:            str     # UUID string — references User.id
    bmr:                float   # Basal Metabolic Rate (kcal/day)
    tdee:               float   # Total Daily Energy Expenditure (kcal/day)
    calorie_target:     int     # Final daily calorie target (kcal)
    protein_target_g:   float   # Daily protein target (grams)
    carbs_target_g:     float   # Daily carbohydrate target (grams)
    fat_target_g:       float   # Daily fat target (grams)

    def __post_init__(self):
        # Output validation — Agent 1 authority (do not change these guards)
        assert self.bmr > 0,                  "bmr must be > 0"
        assert self.tdee >= self.bmr,         "tdee must be >= bmr"
        assert self.calorie_target >= 800,    "calorie_target must be >= 800"
        assert self.protein_target_g >= 0,    "protein_target_g must be >= 0"
        assert self.carbs_target_g >= 0,      "carbs_target_g must be >= 0"
        assert self.fat_target_g >= 0,        "fat_target_g must be >= 0"

    def to_dict(self) -> dict:
        return {
            "user_id":           self.user_id,
            "bmr":               self.bmr,
            "tdee":              self.tdee,
            "calorie_target":    self.calorie_target,
            "protein_target_g":  self.protein_target_g,
            "carbs_target_g":    self.carbs_target_g,
            "fat_target_g":      self.fat_target_g,
        }


# ── Internal helpers ───────────────────────────────────────────────────────────

def _compute_bmr(user: "User") -> float:
    """
    Mifflin-St Jeor BMR formula.

        Male  : (10 × weight_kg) + (6.25 × height_cm) − (5 × age) + 5
        Female: (10 × weight_kg) + (6.25 × height_cm) − (5 × age) − 161
        Other : midpoint of male and female results  →  base − 78.0

    Returns a positive float (kcal/day).
    """
    base = 10.0 * user.weight_kg + 6.25 * user.height_cm - 5.0 * user.age

    if user.gender == "male":
        return round(base + 5.0, 2)
    if user.gender == "female":
        return round(base - 161.0, 2)
    # "other" — deterministic midpoint: (base + 5 + base − 161) / 2 = base − 78
    return round(base - 78.0, 2)


def _compute_tdee(bmr: float, activity_level: str) -> float:
    """TDEE = BMR × PAL multiplier."""
    multiplier = _ACTIVITY_MULTIPLIERS[activity_level]
    return round(bmr * multiplier, 2)


def _compute_calorie_target(tdee: float, goal: str, override: int | None) -> int:
    """
    Derive final daily calorie target.

    Override logic (contracts.md §6.3):
      IF override IS NOT NULL → use it directly (skip TDEE-based formula)
      ELSE                    → TDEE + goal_delta, then apply safety floor
    """
    if override is not None:
        return override

    raw = tdee + _GOAL_CALORIE_DELTA[goal]
    return max(int(round(raw)), _CALORIE_SAFETY_FLOOR)


def _compute_macros(calorie_target: int) -> tuple[float, float, float]:
    """
    Split calorie_target into daily gram targets for protein, carbs, and fat.
    Returns (protein_g, carbs_g, fat_g).
    """
    protein_g = round(calorie_target * _MACRO_RATIO["protein"] / _KCAL_PER_G_PROTEIN, 1)
    carbs_g   = round(calorie_target * _MACRO_RATIO["carbs"]   / _KCAL_PER_G_CARBS,   1)
    fat_g     = round(calorie_target * _MACRO_RATIO["fat"]     / _KCAL_PER_G_FAT,     1)
    return protein_g, carbs_g, fat_g


def _read_macro(food_item: Union["FoodItem", dict], field: str) -> float:
    """Read a field from a FoodItem object or a plain dict — supports both."""
    if isinstance(food_item, dict):
        return food_item[field]
    return getattr(food_item, field)


# ── Public API ─────────────────────────────────────────────────────────────────

class NutritionEngine:
    """
    Deterministic calorie and macro calculator.

    INPUT CONTRACT  — required User fields:
        age, gender, height_cm, weight_kg, activity_level, goal,
        calorie_target_override (may be None)

    OUTPUT CONTRACT — returns NutritionProfile (frozen by Agent 1).

    This class has no internal state. All methods are pure functions
    wrapped in a class for inter-module compatibility.
    """

    def calculate(self, user: "User") -> NutritionProfile:
        """
        Derive a NutritionProfile from a User object.

        Steps:
          1. BMR          — Mifflin-St Jeor formula (gender-aware)
          2. TDEE         — BMR × PAL multiplier for user's activity level
          3. Calorie target — TDEE ± goal delta, then safety floor
                             (or direct override if set)
          4. Macros       — calorie_target distributed by configured ratio

        Deterministic: identical User input always produces identical output.
        """
        # Step 1 & 2 — always computed (NutritionProfile requires bmr > 0 and tdee >= bmr)
        bmr  = _compute_bmr(user)
        tdee = _compute_tdee(bmr, user.activity_level.value
                             if hasattr(user.activity_level, "value")
                             else user.activity_level)

        # Step 3 — calorie target (override or formula)
        calorie_target = _compute_calorie_target(
            tdee,
            user.goal.value if hasattr(user.goal, "value") else user.goal,
            user.calorie_target_override,
        )

        # Step 4 — macro distribution
        protein_g, carbs_g, fat_g = _compute_macros(calorie_target)

        return NutritionProfile(
            user_id=str(user.id),
            bmr=bmr,
            tdee=tdee,
            calorie_target=calorie_target,
            protein_target_g=protein_g,
            carbs_target_g=carbs_g,
            fat_target_g=fat_g,
        )

    @staticmethod
    def compute_item_macros(
        food_item: Union["FoodItem", dict],
        quantity_g: float,
    ) -> dict:
        """
        Scale a food item's per-100g values to an actual portion.

        Required formula (contracts.md §5.4, frozen by Agent 1):
            value = (macro_per_100g / 100) * quantity_g

        Parameters
        ----------
        food_item : FoodItem | dict
            Must expose: calories_per_100g, protein_per_100g,
                         carbs_per_100g, fat_per_100g
        quantity_g : float
            Actual portion in grams (must be >= 1).

        Returns
        -------
        dict with keys: calories, protein_g, carbs_g, fat_g
        """
        factor = quantity_g / 100.0

        return {
            "calories":  round(_read_macro(food_item, "calories_per_100g") * factor, 2),
            "protein_g": round(_read_macro(food_item, "protein_per_100g")  * factor, 2),
            "carbs_g":   round(_read_macro(food_item, "carbs_per_100g")    * factor, 2),
            "fat_g":     round(_read_macro(food_item, "fat_per_100g")      * factor, 2),
        }
