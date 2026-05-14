"""
Unit tests — Agent 1: Contract validation
Tests schema consistency and model serialization.
"""

import pytest
from datetime import date
from nutrition_app.models.user import UserProfile
from nutrition_app.models.food_item import FoodItem, NutritionPer100g
from nutrition_app.models.nutrition_targets import NutritionTargets
from nutrition_app.models.enums import (
    Gender, ActivityLevel, Goal, FoodCategory, UnitType,
    WorkflowStage, StageStatus,
)
from nutrition_app.agents.agent_1_contracts.contracts_agent import ContractsAgent


@pytest.fixture
def agent():
    return ContractsAgent()


class TestUserProfileContract:
    def test_valid_profile(self, agent):
        data = {
            "user_id": "u1", "name": "Test", "gender": "male",
            "date_of_birth": "1990-01-01", "height_cm": 175, "weight_kg": 80,
            "activity_level": "moderately_active", "goal": "maintain",
        }
        errors = agent.validate_user_profile(data)
        assert errors == []

    def test_missing_fields(self, agent):
        errors = agent.validate_user_profile({"user_id": "u1"})
        assert len(errors) > 0

    def test_out_of_range_height(self, agent):
        data = {
            "user_id": "u1", "name": "Test", "gender": "male",
            "date_of_birth": "1990-01-01", "height_cm": 999, "weight_kg": 80,
            "activity_level": "moderately_active", "goal": "maintain",
        }
        errors = agent.validate_user_profile(data)
        assert any("height" in e for e in errors)


class TestFoodItemContract:
    def test_valid_food(self, agent):
        data = {
            "food_id": "f1", "name_he": "עוף", "name_en": "Chicken",
            "category": "protein",
            "nutrition_per_100g": {
                "calories_kcal": 165, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6
            },
        }
        errors = agent.validate_food_item(data)
        assert errors == []

    def test_negative_calories(self, agent):
        data = {
            "food_id": "f1", "name_he": "x", "name_en": "x", "category": "protein",
            "nutrition_per_100g": {
                "calories_kcal": -10, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6
            },
        }
        errors = agent.validate_food_item(data)
        assert any("Negative" in e for e in errors)


class TestSerializationRoundtrip:
    def test_user_profile_roundtrip(self):
        user = UserProfile(
            user_id="u1", name="Test", gender=Gender.MALE,
            date_of_birth=date(1990, 1, 1), height_cm=175, weight_kg=80,
            activity_level=ActivityLevel.MODERATELY_ACTIVE, goal=Goal.MAINTAIN,
        )
        data = user.to_dict()
        restored = UserProfile.from_dict(data)
        assert restored.user_id == user.user_id
        assert restored.gender == user.gender
        assert restored.height_cm == user.height_cm

    def test_food_item_roundtrip(self):
        food = FoodItem(
            food_id="f1", name_he="עוף", name_en="Chicken",
            category=FoodCategory.PROTEIN,
            nutrition_per_100g=NutritionPer100g(
                calories_kcal=165, protein_g=31, carbs_g=0, fat_g=3.6
            ),
        )
        data = food.to_dict()
        restored = FoodItem.from_dict(data)
        assert restored.food_id == food.food_id
        assert restored.nutrition_per_100g.protein_g == 31
