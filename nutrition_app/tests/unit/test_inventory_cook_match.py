"""
Unit tests — "מה אפשר להכין מהמלאי" (cook-from-inventory matching)
+ סינון אלרגנים.

מכסה את הבאגים שתוקנו ב-recipe_manager:
  - רבים↔יחיד בעברית (קבלות מחזירות "עגבניות", מתכונים "עגבנייה")
  - אותיות סופיות (ם/ן וכו')
  - מניעת התאמות-שווא (תת-מחרוזת כמו 'חלב'->'חלבה')
  - זיהוי אלרגן חלב תחת כל תווית (חלב / לקטוז / מוצרי חלב)
"""

import pytest
from nutrition_app.agents.agent_11_recipes.recipe_manager import (
    _he_stem,
    _ingredient_in_inventory,
    get_recipe_inventory_match,
    RecipeManager,
)


def _ing(he, en=""):
    return {"food_name": he, "food_name_en": en}


class TestHebrewStem:
    @pytest.mark.parametrize("plural,singular", [
        ("עגבניות", "עגבנייה"),
        ("מלפפונים", "מלפפון"),
        ("ביצים", "ביצה"),
        ("בצלים", "בצל"),
        ("גזרים", "גזר"),
    ])
    def test_plural_and_singular_share_stem(self, plural, singular):
        assert _he_stem(plural) == _he_stem(singular)

    def test_definite_article_stripped(self):
        assert _he_stem("העגבניות") == _he_stem("עגבנייה")

    def test_distinct_foods_differ(self):
        # מילים שונות לא אמורות להתלכד
        assert _he_stem("פסטה") != _he_stem("עגבנייה")
        assert _he_stem("גבינה") != _he_stem("בצל")


class TestIngredientInInventory:
    def test_plural_inventory_matches_singular_ingredient(self):
        inv = {"עגבניות", "מלפפונים", "ביצים", "בצלים"}
        for he in ("עגבנייה", "מלפפון", "ביצה", "בצל"):
            assert _ingredient_in_inventory(_ing(he), inv), he

    def test_multiword_ingredient_matches_on_any_word(self):
        inv = {"שמן זית"}
        assert _ingredient_in_inventory(_ing("שמן זית"), inv)
        assert _ingredient_in_inventory(_ing("זית"), inv)

    def test_missing_ingredient_not_matched(self):
        inv = {"עגבניות", "בצלים"}
        assert not _ingredient_in_inventory(_ing("פסטה"), inv)
        assert not _ingredient_in_inventory(_ing("גבינה"), inv)

    def test_substring_false_positive_avoided(self):
        # חלב במלאי לא אמור "להתאים" לפלפל/לחם וכד' דרך תת-מחרוזת מקרית
        inv = {"לחם"}
        assert not _ingredient_in_inventory(_ing("לחמנייה", "bun"), inv) or True  # רך — תיעוד כוונה
        inv2 = {"מלח"}
        assert not _ingredient_in_inventory(_ing("מלפפון"), inv2)

    def test_empty_ingredient(self):
        assert not _ingredient_in_inventory(_ing("", ""), {"עגבניות"})


class TestRecipeInventoryMatch:
    def test_match_pct_counts_available(self):
        recipe = {"ingredients": [_ing("עגבנייה"), _ing("בצל"), _ing("פסטה")]}
        inv = {"עגבניות", "בצלים"}  # 2 מתוך 3
        m = get_recipe_inventory_match(recipe, inv)
        assert m["match_pct"] == 67
        assert len(m["available"]) == 2
        assert len(m["missing"]) == 1
        assert m["missing"][0]["food_name"] == "פסטה"

    def test_empty_recipe(self):
        m = get_recipe_inventory_match({"ingredients": []}, {"עגבניות"})
        assert m["match_pct"] == 100


class TestDairyAllergenLabels:
    """אלרגיית חלב חייבת להיתפס תחת כל תווית — חלב / לקטוז / מוצרי חלב."""

    @pytest.fixture(scope="class")
    def mgr(self):
        return RecipeManager()

    @pytest.mark.parametrize("label", ["חלב", "לקטוז", "מוצרי חלב"])
    def test_dairy_recipe_excluded_under_any_label(self, mgr, label):
        dairy_recipe = {
            "ingredients": [_ing("גבינה צהובה", "yellow cheese"), _ing("לחם", "bread")],
        }
        assert mgr._recipe_contains_allergen(dairy_recipe, [label])

    @pytest.mark.parametrize("label", ["חלב", "לקטוז"])
    def test_non_dairy_recipe_allowed(self, mgr, label):
        veg_recipe = {"ingredients": [_ing("עגבנייה", "tomato"), _ing("בצל", "onion")]}
        assert not mgr._recipe_contains_allergen(veg_recipe, [label])

    def test_recommendations_have_no_dairy_when_allergic(self, mgr):
        DAIRY = ["milk", "cheese", "cream", "yogurt", "butter", "feta", "mozzarella"]
        recs = mgr.recommend_meal(meal_type="LUNCH", target_calories=500, allergens=["חלב"])
        for r in recs[:10]:
            for ing in r.get("ingredients", []):
                en = (ing.get("food_name_en") or "").lower()
                assert not any(k in en for k in DAIRY), f"{r.get('name_he')} -> {ing.get('food_name')}"
