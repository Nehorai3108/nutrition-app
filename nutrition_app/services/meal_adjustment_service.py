"""
MealAdjustmentService — single chokepoint for every mutation of a user's
meal preferences and weekly plan.

UI buttons (Pick / Adjust / Swap / Set fixed day) call this service. The
future AI adjustment agent will call the *same* methods — no UI rewrite
needed when the agent ships.

Every mutation returns an AdjustmentResult so callers can show before/after
deltas without recomputing themselves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.models.user_meal_preferences import (
    MEAL_TYPE_KEYS,
    UserMealPreferences,
    UserRecipeVariant,
)
from nutrition_app.models.weekly_plan import WeeklyPlan
from nutrition_app.repositories.user_meal_preferences_repository import (
    UserMealPreferencesRepository,
)


# ─── Result envelope ───────────────────────────────────────────────────────

@dataclass
class NutritionSnapshot:
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0

    def to_dict(self) -> dict:
        return {
            "calories": round(self.calories, 1),
            "protein": round(self.protein, 1),
            "carbs": round(self.carbs, 1),
            "fat": round(self.fat, 1),
        }

    def minus(self, other: "NutritionSnapshot") -> "NutritionSnapshot":
        return NutritionSnapshot(
            calories=self.calories - other.calories,
            protein=self.protein - other.protein,
            carbs=self.carbs - other.carbs,
            fat=self.fat - other.fat,
        )


@dataclass
class AdjustmentResult:
    ok: bool
    before: NutritionSnapshot = field(default_factory=NutritionSnapshot)
    after: NutritionSnapshot = field(default_factory=NutritionSnapshot)
    delta: NutritionSnapshot = field(default_factory=NutritionSnapshot)
    warnings: List[str] = field(default_factory=list)
    payload: Dict = field(default_factory=dict)   # variant_id, plan_date, etc.

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "delta": self.delta.to_dict(),
            "warnings": self.warnings,
            "payload": self.payload,
        }


# ─── Pure helpers (no Streamlit, no I/O) ───────────────────────────────────

def compute_variant_nutrition(
    base_recipe: dict,
    ingredient_overrides: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Compute per-portion macros for a variant.

    Scales each macro proportional to the *override-vs-original mass ratio*
    so we don't need to re-resolve every ingredient against the catalog.

    For ingredients without an override, the base ratio is 1.0. For ingredients
    with an override, ratio = override_qty / base_qty. The overall scaling for
    the recipe is the mass-weighted average of per-ingredient ratios.
    """
    ingredient_overrides = ingredient_overrides or {}
    base_nut = base_recipe.get("total_nutrition") or {}
    portions = max(base_recipe.get("portions", 1), 1)

    base_cal = base_nut.get("calories", 0) / portions
    base_protein = base_nut.get("protein", 0) / portions
    base_carbs = base_nut.get("carbs", 0) / portions
    base_fat = base_nut.get("fat", 0) / portions

    if not ingredient_overrides:
        return {
            "calories": round(base_cal, 1),
            "protein": round(base_protein, 1),
            "carbs": round(base_carbs, 1),
            "fat": round(base_fat, 1),
        }

    # Mass-weighted scaling factor.
    ingredients = base_recipe.get("ingredients") or []
    total_base_mass = 0.0
    total_new_mass = 0.0
    for ing in ingredients:
        qty = float(ing.get("quantity", 0) or 0)
        total_base_mass += qty
        override = ingredient_overrides.get(ing.get("food_name_en") or "")
        new_qty = float(override) if override is not None else qty
        total_new_mass += new_qty

    if total_base_mass <= 0:
        scale = 1.0
    else:
        scale = total_new_mass / total_base_mass

    return {
        "calories": round(base_cal * scale, 1),
        "protein": round(base_protein * scale, 1),
        "carbs": round(base_carbs * scale, 1),
        "fat": round(base_fat * scale, 1),
    }


def _variant_snapshot(variant: UserRecipeVariant) -> NutritionSnapshot:
    n = variant.total_nutrition or {}
    return NutritionSnapshot(
        calories=n.get("calories", 0) or 0,
        protein=n.get("protein", 0) or 0,
        carbs=n.get("carbs", 0) or 0,
        fat=n.get("fat", 0) or 0,
    )


# ─── Service ───────────────────────────────────────────────────────────────

class MealAdjustmentService:
    """The single seam UI and future AI agent share for meal mutations."""

    def __init__(
        self,
        repo: Optional[UserMealPreferencesRepository] = None,
        recipe_manager: Optional[RecipeManager] = None,
    ):
        self._repo = repo or UserMealPreferencesRepository()
        self._mgr = recipe_manager or RecipeManager()

    # ── State helpers ───────────────────────────────────────────────────────

    def load_or_init(self, user_id: str) -> UserMealPreferences:
        prefs = self._repo.load(user_id)
        if prefs is None:
            prefs = UserMealPreferences.empty(user_id)
        return prefs

    def save(self, prefs: UserMealPreferences) -> None:
        self._repo.save(prefs)

    def mark_onboarded(self, prefs: UserMealPreferences) -> None:
        from nutrition_app.utils import utcnow
        prefs.onboarded_at = utcnow()
        self._repo.save(prefs)

    def set_liked_ingredients(
        self,
        prefs: UserMealPreferences,
        food_ids: List[str],
    ) -> AdjustmentResult:
        """Replace the user's liked-ingredient list with *food_ids*.

        Order is preserved (first-seen wins); duplicates are removed. The
        suggestion service will use this list to soft-rank meal candidates.
        Allergies/dislikes on the profile still hard-filter — this only
        affects ordering.
        """
        seen: dict = {}
        for fid in food_ids or []:
            if fid and fid not in seen:
                seen[fid] = True
        prefs.liked_ingredients = list(seen.keys())
        self._repo.save(prefs)
        return AdjustmentResult(
            ok=True,
            payload={"count": len(prefs.liked_ingredients)},
        )

    def skip_meal_type(
        self,
        prefs: UserMealPreferences,
        meal_type: str,
    ) -> AdjustmentResult:
        """Mark *meal_type* as skipped — planner will omit it from the weekly plan."""
        if meal_type not in MEAL_TYPE_KEYS:
            return AdjustmentResult(ok=False, warnings=[f"unknown meal_type: {meal_type}"])
        if meal_type not in prefs.skipped_meal_types:
            prefs.skipped_meal_types.append(meal_type)
        return AdjustmentResult(ok=True, payload={"meal_type": meal_type, "skipped": True})

    def unskip_meal_type(
        self,
        prefs: UserMealPreferences,
        meal_type: str,
    ) -> AdjustmentResult:
        """Remove *meal_type* from the skipped list so it participates in planning again."""
        prefs.skipped_meal_types = [m for m in prefs.skipped_meal_types if m != meal_type]
        return AdjustmentResult(ok=True, payload={"meal_type": meal_type, "skipped": False})

    def reset_preferences(self, user_id: str) -> UserMealPreferences:
        """Wipe picks, variants, fixed overrides, and onboarding flag.

        Returns a fresh empty UserMealPreferences (already persisted). After
        this call app_user.py will redirect the user back to the picker on
        their next navigation.

        The repository keeps the local JSON file, just with an empty payload —
        we don't delete files so audit/history can be reconstructed later.
        """
        empty = UserMealPreferences.empty(user_id)
        self._repo.save(empty)
        return empty

    # ── Mutations (the public AI-agent-friendly API) ─────────────────────────

    def pick_recipe(
        self,
        prefs: UserMealPreferences,
        meal_type: str,
        recipe_id: str,
        ingredient_overrides: Optional[Dict[str, float]] = None,
        name: Optional[str] = None,
    ) -> AdjustmentResult:
        """Create a UserRecipeVariant for *recipe_id* and append it to picks."""
        meal_type = meal_type.lower()
        if meal_type not in MEAL_TYPE_KEYS:
            return AdjustmentResult(ok=False, warnings=[f"unknown meal_type: {meal_type}"])

        recipe = self._mgr.get_recipe(recipe_id)
        if not recipe:
            return AdjustmentResult(ok=False, warnings=[f"unknown recipe_id: {recipe_id}"])

        overrides = dict(ingredient_overrides or {})
        nutrition = compute_variant_nutrition(recipe, overrides)
        variant = UserRecipeVariant(
            variant_id=UserRecipeVariant.new_id(),
            base_recipe_id=recipe_id,
            name=name or recipe.get("name_he") or recipe.get("name_en") or recipe_id,
            meal_type=meal_type,
            ingredient_overrides=overrides,
            total_nutrition=nutrition,
        )
        prefs.add_variant(variant)
        prefs.picks.setdefault(meal_type, []).append(variant.variant_id)

        after = _variant_snapshot(variant)
        return AdjustmentResult(
            ok=True,
            before=NutritionSnapshot(),
            after=after,
            delta=after,
            payload={"variant_id": variant.variant_id, "meal_type": meal_type},
        )

    def adjust_variant(
        self,
        prefs: UserMealPreferences,
        variant_id: str,
        ingredient_overrides: Dict[str, float],
        new_name: Optional[str] = None,
    ) -> AdjustmentResult:
        """Apply ingredient quantity overrides to an existing variant.

        The full overrides dict replaces the previous one (idempotent).
        """
        variant = prefs.variant_by_id(variant_id)
        if not variant:
            return AdjustmentResult(ok=False, warnings=[f"unknown variant: {variant_id}"])
        recipe = self._mgr.get_recipe(variant.base_recipe_id)
        if not recipe:
            return AdjustmentResult(ok=False, warnings=[f"base recipe missing: {variant.base_recipe_id}"])

        before = _variant_snapshot(variant)
        variant.ingredient_overrides = dict(ingredient_overrides or {})
        variant.total_nutrition = compute_variant_nutrition(recipe, variant.ingredient_overrides)
        if new_name:
            variant.name = new_name
        after = _variant_snapshot(variant)

        return AdjustmentResult(
            ok=True,
            before=before,
            after=after,
            delta=after.minus(before),
            payload={"variant_id": variant_id},
        )

    def unpick_variant(
        self,
        prefs: UserMealPreferences,
        variant_id: str,
    ) -> AdjustmentResult:
        """Remove a variant from picks and from the variants list entirely."""
        variant = prefs.variant_by_id(variant_id)
        if not variant:
            return AdjustmentResult(ok=False, warnings=[f"unknown variant: {variant_id}"])
        before = _variant_snapshot(variant)
        prefs.remove_variant(variant_id)
        return AdjustmentResult(
            ok=True,
            before=before,
            after=NutritionSnapshot(),
            delta=NutritionSnapshot().minus(before),
            payload={"variant_id": variant_id},
        )

    def set_fixed_override(
        self,
        prefs: UserMealPreferences,
        weekday: str,
        meal_type: str,
        variant_id: Optional[str],
    ) -> AdjustmentResult:
        """Pin *variant_id* to *weekday.meal_type*. Pass variant_id=None to clear."""
        weekday = weekday.lower()
        meal_type = meal_type.lower()
        key = f"{weekday}.{meal_type}"

        if variant_id is None:
            prefs.fixed_day_overrides.pop(key, None)
            return AdjustmentResult(ok=True, payload={"key": key, "cleared": True})

        variant = prefs.variant_by_id(variant_id)
        if not variant:
            return AdjustmentResult(ok=False, warnings=[f"unknown variant: {variant_id}"])

        prefs.fixed_day_overrides[key] = variant_id
        snap = _variant_snapshot(variant)
        return AdjustmentResult(
            ok=True,
            before=NutritionSnapshot(),
            after=snap,
            delta=snap,
            payload={"key": key, "variant_id": variant_id},
        )

    # ── Plan-level mutations (for the daily-menu page) ──────────────────────

    def swap_meal_in_plan(
        self,
        plan: WeeklyPlan,
        weekday: str,
        meal_type: str,
        variant: UserRecipeVariant,
    ) -> AdjustmentResult:
        """Replace a meal in the given weekly plan with a different variant.

        Note: this only mutates the in-memory WeeklyPlan. Persisting the
        weekly plan is the caller's responsibility (we typically regenerate
        the plan from prefs rather than storing it).
        """
        from nutrition_app.models.enums import MealType
        from nutrition_app.models.meal import Meal, MealItem

        weekday = weekday.lower()
        day = plan.day_plan(weekday)
        if day is None:
            return AdjustmentResult(ok=False, warnings=[f"no plan for {weekday}"])

        # Build a daily before-snapshot.
        before = NutritionSnapshot(
            calories=day.total_calories,
            protein=day.total_protein,
            carbs=day.total_carbs,
            fat=day.total_fat,
        )

        # Find the existing Meal for this meal_type and replace it.
        # For post_workout/treat (tag-based) we co-locate them on
        # MORNING_SNACK / EVENING_SNACK respectively. Caller can decide.
        meal_type_enum_value = {
            "breakfast": MealType.BREAKFAST,
            "lunch": MealType.LUNCH,
            "dinner": MealType.DINNER,
            "post_workout": MealType.MORNING_SNACK,
            "treat": MealType.EVENING_SNACK,
        }.get(meal_type, MealType.MORNING_SNACK)

        nut = variant.total_nutrition or {}
        new_item = MealItem(
            food_id=variant.variant_id,
            food_name=variant.name,
            quantity_g=0.0,
            calories_kcal=nut.get("calories", 0) or 0,
            protein_g=nut.get("protein", 0) or 0,
            carbs_g=nut.get("carbs", 0) or 0,
            fat_g=nut.get("fat", 0) or 0,
        )

        replaced = False
        for m in day.meals:
            if m.meal_type == meal_type_enum_value:
                m.items = [new_item]
                replaced = True
                break
        if not replaced:
            day.meals.append(Meal(meal_type=meal_type_enum_value, items=[new_item]))

        after = NutritionSnapshot(
            calories=day.total_calories,
            protein=day.total_protein,
            carbs=day.total_carbs,
            fat=day.total_fat,
        )
        warnings: List[str] = []
        if plan.target_calories_kcal and after.calories > plan.target_calories_kcal * 1.15:
            warnings.append(f"daily calories exceed target by {round((after.calories/plan.target_calories_kcal-1)*100,1)}%")

        return AdjustmentResult(
            ok=True,
            before=before,
            after=after,
            delta=after.minus(before),
            warnings=warnings,
            payload={"weekday": weekday, "meal_type": meal_type, "variant_id": variant.variant_id},
        )
