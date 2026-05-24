"""
RecipeSuggestionService — preference-aware recipe candidates for the picker.

Given a meal-type key ("breakfast", "lunch", "dinner", "post_workout", "treat")
and the user's profile dict (with `meal_preferences.allergies`,
`meal_preferences.disliked_foods`, `meal_preferences.kashrut`), return up to N
recipes for the picker UI.

Filter rules (locked in the approved plan, decision #5):
- Allergies are HARD-EXCLUDED regardless of quantity. Reuses the existing
  Hebrew allergen → English keyword map on RecipeManager.
- "Disliked foods" excludes a recipe only when the disliked food appears as a
  MAIN ingredient. "Main" = in the top-3 ingredients by mass OR ≥ 20% of the
  recipe's total ingredient mass. Trace amounts don't exclude.
- Kashrut is filtered when the profile sets a strict mode (anything other
  than 'flexible' or 'parve').

The same entry point will be called by the future AI adjustment agent, which
is why this lives in services/ rather than inside a Streamlit page.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager

# Meal-type keys → recipe-data lookup strategy.
#   For breakfast/lunch/dinner we match the MealType field (uppercased).
#   For post_workout/treat we match by tag.
_MEAL_TYPE_KIND: Dict[str, str] = {
    "breakfast": "meal_type",
    "lunch":     "meal_type",
    "dinner":    "meal_type",
    "post_workout": "tag",
    "treat":     "tag",
}

_MEAL_TYPE_VALUE: Dict[str, str] = {
    "breakfast":   "BREAKFAST",
    "lunch":       "LUNCH",
    "dinner":      "DINNER",
    "post_workout": "post_workout",
    "treat":       "treat",
}


# Macro-group mapping for the ingredient-picker step. Keys are the Hebrew tab
# labels the UI renders; values are the FoodItem.category strings included in
# that group. Beverages, condiments, snacks, sweets, and "other" are
# intentionally excluded — they're not main meal ingredients.
INGREDIENT_GROUPS: List[Tuple[str, str, List[str]]] = [
    # (group_key, hebrew_label, category_values)
    ("protein", "חלבון",      ["protein", "dairy"]),
    ("carbs",   "פחמימות",     ["carbohydrate", "grain", "legume"]),
    ("fat",     "שומן",        ["fat", "nut_seed"]),
    ("veg",     "ירקות",       ["vegetable"]),
    ("fruit",   "פירות",       ["fruit"]),
]


class RecipeSuggestionService:

    def __init__(self, recipe_manager: Optional[RecipeManager] = None):
        self._mgr = recipe_manager or RecipeManager()
        # Lazy cache of liked-ingredient token sets so we don't re-resolve
        # food_ids → name tokens for every recipe call.
        self._liked_tokens_cache: Dict[Tuple[str, ...], Set[str]] = {}

    # ── Public API ──────────────────────────────────────────────────────────

    def suggest_for_meal_type(
        self,
        meal_type: str,
        profile: Optional[dict] = None,
        n: int = 6,
        liked_ingredients: Optional[List[str]] = None,
    ) -> List[dict]:
        """Return up to *n* recipe dicts for *meal_type*, filtered by *profile*.

        meal_type must be one of: breakfast, lunch, dinner, post_workout, treat.
        profile is the user-profile dict produced by ProfileRepository.load(),
        or None for no filtering.

        liked_ingredients (optional) is a list of catalog food_id strings the
        user marked as favorites. Recipes containing more of these ingredients
        rank higher in the result list. This is a *soft* signal — recipes
        without overlap still appear. Allergies and dislikes are unaffected.
        """
        meal_type = (meal_type or "").lower()
        if meal_type not in _MEAL_TYPE_KIND:
            return []

        candidates = self._candidates_for(meal_type)

        prefs = (profile or {}).get("meal_preferences") or {}
        allergies = [a for a in (prefs.get("allergies") or []) if a]
        disliked = [d.lower().strip() for d in (prefs.get("disliked_foods") or []) if d]
        kashrut = (prefs.get("kashrut") or "").lower()

        filtered: List[dict] = []
        for recipe in candidates:
            # Skip recipes missing nutrition data — we can't recommend
            # something whose macros we don't know.
            nut = recipe.get("total_nutrition")
            if not nut or not nut.get("calories"):
                continue
            if self._recipe_blocked_by_kashrut(recipe, kashrut):
                continue
            if allergies and self._mgr._recipe_contains_allergen(recipe, allergies):
                continue
            if disliked and self._recipe_has_disliked_main(recipe, disliked):
                continue
            filtered.append(recipe)

        # Resolve liked food_ids → matchable tokens (name_en + aliases) once.
        liked_tokens = self._resolve_liked_tokens(liked_ingredients) if liked_ingredients else set()

        def _overlap(recipe: dict) -> int:
            if not liked_tokens:
                return 0
            count = 0
            for ing in recipe.get("ingredients", []):
                en = (ing.get("food_name_en") or "").lower()
                he = (ing.get("food_name") or "").lower()
                tokens = {en, he}
                tokens.update(en.split())
                if any(tok and tok in liked_tokens for tok in tokens):
                    count += 1
                    continue
                # Substring match (covers "olive oil" liked → "extra virgin olive oil" ingredient)
                if any(lt and (lt in en or lt in he) for lt in liked_tokens):
                    count += 1
            return count

        # Sort by (-overlap, prep_time, calories): higher overlap wins,
        # ties broken by quicker prep and lower calorie load.
        filtered.sort(key=lambda r: (
            -_overlap(r),
            r.get("prep_time_minutes", 999),
            r.get("total_nutrition", {}).get("calories", 0),
        ))
        return filtered[:n]

    # ── Liked-ingredient resolution ─────────────────────────────────────────

    def _resolve_liked_tokens(self, food_ids: List[str]) -> Set[str]:
        """Resolve food_ids → set of lowercased name tokens for matching.

        Cached per call signature so repeated calls in one wizard render don't
        hit the FoodCatalog repeatedly. The cache key is the sorted tuple of
        food_ids.
        """
        if not food_ids:
            return set()
        key = tuple(sorted(food_ids))
        cached = self._liked_tokens_cache.get(key)
        if cached is not None:
            return cached

        try:
            from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
            catalog = FoodCatalog()
        except Exception:
            return set()

        tokens: Set[str] = set()
        for fid in food_ids:
            food = catalog.get_by_id(fid) if hasattr(catalog, "get_by_id") else None
            if not food:
                # Fallback: linear scan of the all-foods list.
                try:
                    for f in catalog.get_all_foods():
                        if getattr(f, "food_id", None) == fid:
                            food = f
                            break
                except Exception:
                    food = None
            if not food:
                continue
            for attr in ("name_en", "name_he"):
                val = (getattr(food, attr, "") or "").lower().strip()
                if val:
                    tokens.add(val)
                    tokens.update(val.split())
            for alias_attr in ("aliases_en", "aliases_he"):
                for a in (getattr(food, alias_attr, None) or []):
                    a_low = (a or "").lower().strip()
                    if a_low:
                        tokens.add(a_low)
                        tokens.update(a_low.split())

        # Strip very short noise tokens that would match everything.
        tokens = {t for t in tokens if len(t) >= 2}
        self._liked_tokens_cache[key] = tokens
        return tokens

    # ── Filtering helpers ───────────────────────────────────────────────────

    def _candidates_for(self, meal_type: str) -> List[dict]:
        kind = _MEAL_TYPE_KIND[meal_type]
        value = _MEAL_TYPE_VALUE[meal_type]
        if kind == "meal_type":
            return list(self._mgr._by_meal_type.get(value.upper(), []))
        # tag
        return list(self._mgr._by_tag.get(value.lower(), []))

    @staticmethod
    def _recipe_blocked_by_kashrut(recipe: dict, kashrut: str) -> bool:
        """Mirror the strict modes used by RecipeManager but for a single recipe."""
        if not kashrut or kashrut == "flexible":
            return False
        recipe_k = (recipe.get("kashrut") or "parve").lower()
        if kashrut == "parve":
            # 'parve' on the profile is the *default*; treat as no restriction.
            return False
        if kashrut == "parve_only":
            return recipe_k != "parve"
        if kashrut == "strict_dairy":
            return recipe_k not in ("dairy", "parve")
        if kashrut == "strict_meat":
            return recipe_k not in ("meat", "parve")
        return False

    @staticmethod
    def _recipe_has_disliked_main(recipe: dict, disliked: Iterable[str]) -> bool:
        """Return True iff any *disliked* food is a MAIN ingredient.

        Main = top-3 by mass, OR ≥ 20% of total ingredient mass.
        Disliked tokens are matched case-insensitively against the ingredient's
        Hebrew name, English name, and individual English words.
        """
        ingredients = recipe.get("ingredients") or []
        if not ingredients:
            return False

        def _mass(ing: dict) -> float:
            qty = ing.get("quantity", 0) or 0
            unit = (ing.get("unit") or "grams").lower()
            # Treat all non-gram units as ~roughly equivalent for ranking. The
            # picker only needs main-vs-trace discrimination, not precise mass.
            if unit in ("grams", "gram", "ml"):
                return float(qty)
            return float(qty) * 50.0  # rough fallback for "units", tablespoon, etc.

        total = sum(_mass(i) for i in ingredients) or 1.0
        ranked = sorted(ingredients, key=_mass, reverse=True)
        top_three: Set[int] = {id(r) for r in ranked[:3]}
        disliked_norm = [d.lower().strip() for d in disliked if d]

        for ing in ingredients:
            en = (ing.get("food_name_en") or "").lower()
            he = (ing.get("food_name") or "").lower()
            mass = _mass(ing)
            is_main = (id(ing) in top_three) or (mass / total >= 0.20)
            if not is_main:
                continue
            tokens = {en, he}
            tokens.update(en.split())
            for d in disliked_norm:
                if not d:
                    continue
                # Match either substring direction so "egg" hits "eggs" and
                # "ביצה" hits "ביצים".
                for tok in tokens:
                    if not tok:
                        continue
                    if d in tok or tok in d:
                        return True
        return False
