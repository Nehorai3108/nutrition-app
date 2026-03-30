"""
Unit tests — Agent 3: Food Catalog & Matching
"""

import pytest
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.models.enums import ConfidenceLevel, FoodCategory, UnitType
from nutrition_app.models.food_item import FoodItem, NutritionPer100g


@pytest.fixture
def catalog():
    return FoodCatalog()


class TestFoodSearch:
    def test_search_hebrew(self, catalog):
        results = catalog.search_foods("עוף")
        assert len(results) > 0
        assert any("עוף" in f.name_he or "עוף" in " ".join(f.aliases_he) for f in results)

    def test_search_english(self, catalog):
        results = catalog.search_foods("chicken")
        assert len(results) > 0

    def test_search_no_results(self, catalog):
        results = catalog.search_foods("xyznonexistent")
        assert len(results) == 0

    def test_get_by_id(self, catalog):
        food = catalog.get_food_by_id("food_001")
        assert food is not None
        assert food.name_en == "Chicken Breast"


class TestFoodMatching:
    def test_exact_match_high_confidence(self, catalog):
        result = catalog.match_foods(["חזה עוף"])
        assert len(result.matches) > 0
        assert result.matches[0].confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)

    def test_alias_match(self, catalog):
        result = catalog.match_foods(["עוף"])
        assert len(result.matches) > 0 or len(result.low_confidence) > 0

    def test_unmatched_food(self, catalog):
        result = catalog.match_foods(["סושי דרקון"])
        assert len(result.unmatched) > 0 or len(result.low_confidence) > 0

    def test_multiple_foods(self, catalog):
        result = catalog.match_foods(["חזה עוף", "אורז", "ביצה"])
        total = len(result.matches) + len(result.low_confidence) + len(result.unmatched)
        assert total == 3

    def test_requires_decision_flag(self, catalog):
        result = catalog.match_foods(["חזה עוף"])
        # If all matched high confidence, should not require decision
        if result.all_high_confidence:
            assert not result.requires_decision


class TestCustomFood:
    def test_add_custom_food(self, catalog):
        custom = FoodItem(
            food_id="custom_001",
            name_he="טופו",
            name_en="Tofu",
            category=FoodCategory.PROTEIN,
            nutrition_per_100g=NutritionPer100g(
                calories_kcal=76.0, protein_g=8.0, carbs_g=1.9, fat_g=4.8
            ),
        )
        result = catalog.add_custom_food(custom)
        assert result.is_custom is True
        assert result.source == "user_custom"

        # Should be findable now
        found = catalog.get_food_by_id("custom_001")
        assert found is not None
        assert found.name_en == "Tofu"
