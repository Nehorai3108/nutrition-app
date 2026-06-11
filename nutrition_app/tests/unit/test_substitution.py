"""Tests for Agent 3 SubstitutionEngine — dynamic food swaps."""

import pytest

from nutrition_app.agents.agent_3_food import FoodCatalog, SubstitutionEngine
from nutrition_app.models.enums import FoodCategory
from nutrition_app.models.food_item import FoodItem, NutritionPer100g


def _make_catalog():
    """Static catalog (10 built-in foods) + a few extras for swap coverage."""
    catalog = FoodCatalog(load_extended=False)
    extras = [
        FoodItem(
            food_id="food_t01", name_he="דג סלמון", name_en="Salmon",
            category=FoodCategory.PROTEIN,
            nutrition_per_100g=NutritionPer100g(
                calories_kcal=208.0, protein_g=20.0, carbs_g=0.0, fat_g=13.0
            ),
            default_serving_g=150.0,
        ),
        FoodItem(
            food_id="food_t02", name_he="הודו", name_en="Turkey Breast",
            category=FoodCategory.PROTEIN,
            nutrition_per_100g=NutritionPer100g(
                calories_kcal=135.0, protein_g=30.0, carbs_g=0.0, fat_g=1.0
            ),
            default_serving_g=150.0,
        ),
        FoodItem(
            food_id="food_t03", name_he="קוסקוס", name_en="Couscous",
            category=FoodCategory.GRAIN,
            nutrition_per_100g=NutritionPer100g(
                calories_kcal=112.0, protein_g=3.8, carbs_g=23.0, fat_g=0.2
            ),
            default_serving_g=150.0,
        ),
    ]
    for f in extras:
        catalog.add_custom_food(f)
    return catalog


@pytest.fixture
def engine():
    return SubstitutionEngine(_make_catalog())


def test_protein_swap_returns_proteins_only(engine):
    alts = engine.find_alternatives("חזה עוף", target_calories=250, k=4)
    assert alts, "expected protein alternatives for chicken breast"
    names = [a["name"] for a in alts]
    assert "חזה עוף" not in names
    for a in alts:
        assert a["category"] in ("protein", "legume")


def test_macro_similarity_prefers_lean_protein(engine):
    alts = engine.find_alternatives("חזה עוף", target_calories=250, k=4)
    # Turkey breast is the closest macro profile to chicken breast
    assert alts[0]["name"] == "הודו"


def test_carb_swap_stays_in_carb_group(engine):
    alts = engine.find_alternatives("אורז לבן", target_calories=200, k=4)
    assert alts
    for a in alts:
        assert a["category"] in ("grain", "carbohydrate")
        assert a["name"] != "אורז לבן"


def test_calories_roughly_match_target(engine):
    target = 250
    alts = engine.find_alternatives("חזה עוף", target_calories=target, k=4)
    for a in alts:
        # Household-unit rounding allows deviation, but should be in range
        assert 0.4 * target <= a["calories"] <= 1.8 * target


def test_disliked_foods_excluded(engine):
    alts = engine.find_alternatives(
        "חזה עוף", target_calories=250, k=4, disliked=["דג סלמון"]
    )
    names = [a["name"] for a in alts]
    assert "דג סלמון" not in names


def test_dairy_meal_blocks_meat_but_allows_parve(engine):
    alts = engine.find_alternatives(
        "חזה עוף", target_calories=250, k=10, meal_has_dairy=True
    )
    names = [a["name"] for a in alts]
    assert "הודו" not in names          # meat blocked in dairy meal
    assert "דג סלמון" in names           # fish is parve — allowed
    assert "ביצה" in names               # egg is parve — allowed


def test_meat_meal_blocks_dairy(engine):
    alts = engine.find_alternatives(
        "גבינת קוטג׳", target_calories=150, k=10, meal_has_meat=True
    )
    for a in alts:
        assert a["category"] != "dairy"


def test_allergy_group_expansion_blocks_fish(engine):
    # User declares "דגים" — salmon must be excluded even though its name
    # ("דג סלמון") would match, but tuna-style names without "דג" must too
    alts = engine.find_alternatives(
        "חזה עוף", target_calories=250, k=10, allergies=["דגים"]
    )
    names = [a["name"] for a in alts]
    assert "דג סלמון" not in names


def test_unknown_food_returns_empty(engine):
    assert engine.find_alternatives("מזון שלא קיים בכלל", target_calories=100) == []


def test_result_shape(engine):
    alts = engine.find_alternatives("חזה עוף", target_calories=250, k=2)
    for a in alts:
        for key in ("food_id", "name", "quantity", "unit", "grams",
                    "calories", "protein", "carbs", "fat", "category"):
            assert key in a
        assert a["grams"] > 0
        assert a["calories"] > 0
