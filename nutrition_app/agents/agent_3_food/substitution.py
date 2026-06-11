"""
Agent 3 — Food Substitution Engine

Responsibility:
- Find similar food alternatives for a given food item
- Match by food group (protein→protein, carb→carb...)
- Score by macro-profile similarity (per 100 kcal)
- Size portions to match the calories being replaced
- Respect allergies, disliked foods, and kashrut context

Deterministic — no AI, no writes.
"""

from __future__ import annotations

import math
import re
from typing import List, Optional, Set

from nutrition_app.models.enums import FoodCategory
from nutrition_app.models.food_item import FoodItem
from nutrition_app.utils.household_units import suggested_quantity

# ─── Swap groups: categories considered interchangeable ─────────────
_SWAP_GROUPS: List[Set[FoodCategory]] = [
    {FoodCategory.PROTEIN, FoodCategory.LEGUME},
    {FoodCategory.GRAIN, FoodCategory.CARBOHYDRATE},
    {FoodCategory.FAT, FoodCategory.NUT_SEED},
    {FoodCategory.DAIRY},
    {FoodCategory.VEGETABLE},
    {FoodCategory.FRUIT},
    {FoodCategory.BEVERAGE},
    {FoodCategory.SNACK, FoodCategory.SWEET},
]

_HEBREW_RE = re.compile("[֐-׿]")

# Parve protein keywords — allowed with dairy despite PROTEIN category
_PARVE_KEYWORDS = ("ביצה", "טונה", "דג", "סלמון", "סרדינ", "טופו", "לוקוס", "אמנון", "בקלה")

# Allergy group → food keywords it implies (names rarely contain the group word itself)
_ALLERGY_GROUPS = {
    "דגים": ["דג", "טונה", "סלמון", "סרדינ", "מקרל", "אמנון", "בקלה", "לוקוס",
             "דניס", "פורל", "הרינג", "אנשובי", "קלמארי", "שרימפס", "חסילונ", "פירות ים"],
    "אגוזים": ["אגוז", "שקד", "קשיו", "פיסטוק", "לוז", "פקאן", "מקדמיה"],
    "בוטנים": ["בוטן", "במבה"],
    "ביצים": ["ביצה", "חביתה", "מיונז"],
    "גלוטן": ["לחם", "פיתה", "פסטה", "קוסקוס", "בורגול", "סולת", "קמח", "בורקס",
              "קרואסון", "לחמני", "חלה", "מצה", "פתיתים", "שיבולת שועל", "בייגל"],
    "לקטוז": ["חלב", "גבינ", "יוגורט", "קוטג", "שמנת", "חמאה", "גלידה"],
    "חלב": ["חלב", "גבינ", "יוגורט", "קוטג", "שמנת", "חמאה", "גלידה"],
    "סויה": ["סויה", "טופו", "אדממה"],
    "שומשום": ["שומשום", "טחינה", "חלבה"],
}


def _expand_blocked_terms(terms: List[str]) -> List[str]:
    """Expand allergy-group names into the food keywords they imply."""
    expanded = list(terms)
    for term in terms:
        t = (term or "").strip()
        for group, keywords in _ALLERGY_GROUPS.items():
            if t and (t in group or group in t):
                expanded.extend(keywords)
    return expanded


def _swap_group(category: FoodCategory) -> Set[FoodCategory]:
    for group in _SWAP_GROUPS:
        if category in group:
            return group
    return {category}


def _is_meat(food: FoodItem) -> bool:
    """Meat for kashrut purposes: high-protein PROTEIN that is not parve."""
    if food.category != FoodCategory.PROTEIN:
        return False
    if (food.nutrition_per_100g.protein_g or 0) <= 10:
        return False
    name = f"{food.name_he or ''} {food.name_en or ''}"
    return not any(kw in name for kw in _PARVE_KEYWORDS)


def _matches_any_term(food: FoodItem, terms: List[str]) -> bool:
    """Check if any term appears in the food's names/aliases (or vice versa)."""
    names = [food.name_he or "", food.name_en or ""]
    names += list(food.aliases_he or []) + list(food.aliases_en or [])
    names = [n.strip().lower() for n in names if n]
    for term in terms:
        t = (term or "").strip().lower()
        if not t:
            continue
        for n in names:
            if t in n or n in t:
                return True
    return False


def _macro_profile(food: FoodItem) -> Optional[tuple]:
    """Grams of (protein, carbs, fat) per 100 kcal."""
    n = food.nutrition_per_100g
    cal = n.calories_kcal or 0
    if cal <= 0:
        return None
    return (
        (n.protein_g or 0) / cal * 100,
        (n.carbs_g or 0) / cal * 100,
        (n.fat_g or 0) / cal * 100,
    )


def portion_macros(food: FoodItem, grams: float) -> dict:
    """None-safe macro calculation for a portion (DB rows may have NULL fields)."""
    n = food.nutrition_per_100g
    factor = grams / 100.0
    return {
        "calories_kcal": round((n.calories_kcal or 0) * factor, 1),
        "protein_g": round((n.protein_g or 0) * factor, 1),
        "carbs_g": round((n.carbs_g or 0) * factor, 1),
        "fat_g": round((n.fat_g or 0) * factor, 1),
    }


def meal_kashrut_flags(catalog, food_names: List[str]) -> tuple:
    """Resolve meal items by name and return (has_meat, has_dairy)."""
    has_meat = False
    has_dairy = False
    for name in food_names:
        if not name:
            continue
        hits = catalog.search_foods(name, limit=1)
        if not hits:
            continue
        food = hits[0]
        if _is_meat(food):
            has_meat = True
        if food.category == FoodCategory.DAIRY:
            has_dairy = True
    return has_meat, has_dairy


class SubstitutionEngine:
    """Finds calorie-matched alternatives for a food item. No AI, no writes."""

    def __init__(self, catalog):
        self._catalog = catalog

    def find_alternatives(
        self,
        food_name: str,
        target_calories: Optional[float] = None,
        k: int = 4,
        allergies: Optional[List[str]] = None,
        disliked: Optional[List[str]] = None,
        exclude_names: Optional[List[str]] = None,
        meal_has_meat: bool = False,
        meal_has_dairy: bool = False,
    ) -> List[dict]:
        """Return up to k alternative foods, each sized to ~target_calories.

        Each result: {food_id, name, name_en, quantity, unit, grams,
                      calories, protein, carbs, fat, category}
        """
        hits = self._catalog.search_foods(food_name, limit=1)
        if not hits:
            return []
        source = hits[0]
        return self.find_alternatives_for_food(
            source,
            target_calories=target_calories,
            k=k,
            allergies=allergies,
            disliked=disliked,
            exclude_names=exclude_names,
            meal_has_meat=meal_has_meat,
            meal_has_dairy=meal_has_dairy,
        )

    def find_alternatives_for_food(
        self,
        source: FoodItem,
        target_calories: Optional[float] = None,
        k: int = 4,
        allergies: Optional[List[str]] = None,
        disliked: Optional[List[str]] = None,
        exclude_names: Optional[List[str]] = None,
        meal_has_meat: bool = False,
        meal_has_dairy: bool = False,
    ) -> List[dict]:
        allergies = allergies or []
        disliked = disliked or []
        exclude_names = exclude_names or []
        blocked_terms = _expand_blocked_terms(list(allergies) + list(disliked)) + list(exclude_names)

        group = _swap_group(source.category)
        source_profile = _macro_profile(source)

        if target_calories is None or target_calories <= 0:
            n = source.nutrition_per_100g
            cal100 = n.calories_kcal or 0
            target_calories = max(50.0, cal100 * (source.default_serving_g or 100) / 100)

        scored = []
        for food in self._catalog.get_all_foods():
            if food.food_id == source.food_id:
                continue
            if food.category not in group:
                continue
            # Hebrew-first app: skip foreign-only entries (e.g. raw OpenFoodFacts rows)
            if not _HEBREW_RE.search(food.name_he or ""):
                continue
            profile = _macro_profile(food)
            if profile is None:
                continue
            # Same food under a different entry (e.g. "אורז" vs "אורז לבן")
            if _matches_any_term(food, [source.name_he, source.name_en]):
                continue
            if blocked_terms and _matches_any_term(food, blocked_terms):
                continue
            # Kashrut context: no meat into a dairy meal, no dairy into a meat meal
            if meal_has_dairy and _is_meat(food):
                continue
            if meal_has_meat and food.category == FoodCategory.DAIRY:
                continue

            if source_profile is not None:
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(source_profile, profile)))
            else:
                dist = 0.0
            # Prefer Hebrew-DB entries (cleaner names) on ties
            src_rank = 0 if (food.source in ("json", "manual", "catalog")) else 1
            scored.append((dist, src_rank, food.name_he or food.name_en or "", food))

        scored.sort(key=lambda x: x[:3])

        results = []
        seen_names: Set[str] = set()
        for _, _, _, food in scored:
            display_name = food.name_he or food.name_en
            if not display_name or display_name in seen_names:
                continue
            seen_names.add(display_name)

            cal100 = food.nutrition_per_100g.calories_kcal or 0
            qty, unit, grams = suggested_quantity(display_name, target_calories, cal100)
            macros = portion_macros(food, grams)
            results.append({
                "food_id": food.food_id,
                "name": display_name,
                "name_en": food.name_en or "",
                "quantity": qty,
                "unit": unit,
                "grams": grams,
                "calories": round(macros["calories_kcal"]),
                "protein": round(macros["protein_g"], 1),
                "carbs": round(macros["carbs_g"], 1),
                "fat": round(macros["fat_g"], 1),
                "category": food.category.value,
            })
            if len(results) >= k:
                break
        return results
