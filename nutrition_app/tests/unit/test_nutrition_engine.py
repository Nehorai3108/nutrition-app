"""
Unit tests — Agent 2: Nutrition Engine
Tests BMR, TDEE, target calories, and macro calculations.
"""

import pytest
from datetime import date
from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal
from nutrition_app.agents.agent_2_nutrition.nutrition_engine import NutritionEngine


@pytest.fixture
def engine():
    return NutritionEngine()


@pytest.fixture
def male_user():
    return UserProfile(
        user_id="test_001",
        name="Test User",
        gender=Gender.MALE,
        date_of_birth=date(1990, 1, 1),
        height_cm=175.0,
        weight_kg=80.0,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=Goal.MAINTAIN,
    )


@pytest.fixture
def female_user():
    return UserProfile(
        user_id="test_002",
        name="Test Female",
        gender=Gender.FEMALE,
        date_of_birth=date(1995, 6, 15),
        height_cm=165.0,
        weight_kg=60.0,
        activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        goal=Goal.LOSE_WEIGHT,
    )


class TestBMR:
    def test_male_bmr(self, engine, male_user):
        targets = engine.calculate_targets(male_user)
        # Mifflin-St Jeor: 10*80 + 6.25*175 - 5*age + 5
        assert targets.bmr_kcal > 0
        assert targets.calculation_method == "mifflin_st_jeor"

    def test_female_bmr(self, engine, female_user):
        targets = engine.calculate_targets(female_user)
        assert targets.bmr_kcal > 0
        # Female BMR should be lower than male with similar stats
        male_targets = engine.calculate_targets(
            UserProfile(
                user_id="cmp", name="M", gender=Gender.MALE,
                date_of_birth=female_user.date_of_birth,
                height_cm=female_user.height_cm,
                weight_kg=female_user.weight_kg,
                activity_level=female_user.activity_level,
                goal=female_user.goal,
            )
        )
        assert targets.bmr_kcal < male_targets.bmr_kcal


class TestTDEE:
    def test_tdee_greater_than_bmr(self, engine, male_user):
        targets = engine.calculate_targets(male_user)
        assert targets.tdee_kcal > targets.bmr_kcal

    def test_activity_increases_tdee(self, engine, male_user):
        male_user.activity_level = ActivityLevel.SEDENTARY
        low = engine.calculate_targets(male_user)
        male_user.activity_level = ActivityLevel.VERY_ACTIVE
        high = engine.calculate_targets(male_user)
        assert high.tdee_kcal > low.tdee_kcal


class TestTargetCalories:
    def test_lose_weight_deficit(self, engine, male_user):
        male_user.goal = Goal.LOSE_WEIGHT
        targets = engine.calculate_targets(male_user)
        assert targets.target_calories_kcal < targets.tdee_kcal

    def test_maintain_equals_tdee(self, engine, male_user):
        male_user.goal = Goal.MAINTAIN
        targets = engine.calculate_targets(male_user)
        assert targets.target_calories_kcal == targets.tdee_kcal

    def test_gain_weight_surplus(self, engine, male_user):
        male_user.goal = Goal.GAIN_WEIGHT
        targets = engine.calculate_targets(male_user)
        assert targets.target_calories_kcal > targets.tdee_kcal

    def test_minimum_calories_floor(self, engine):
        tiny_user = UserProfile(
            user_id="tiny", name="Tiny", gender=Gender.FEMALE,
            date_of_birth=date(2000, 1, 1), height_cm=150.0, weight_kg=40.0,
            activity_level=ActivityLevel.SEDENTARY, goal=Goal.LOSE_WEIGHT,
        )
        targets = engine.calculate_targets(tiny_user)
        assert targets.target_calories_kcal >= 1200.0


class TestMacros:
    def test_macros_positive(self, engine, male_user):
        targets = engine.calculate_targets(male_user)
        assert targets.protein_g > 0
        assert targets.carbs_g > 0
        assert targets.fat_g > 0

    def test_macro_calories_match_target(self, engine, male_user):
        targets = engine.calculate_targets(male_user)
        macro_cals = targets.protein_g * 4 + targets.carbs_g * 4 + targets.fat_g * 9
        assert abs(macro_cals - targets.target_calories_kcal) <= 10  # rounding tolerance

    def test_percentages_sum_roughly_100(self, engine, male_user):
        targets = engine.calculate_targets(male_user)
        total_pct = targets.protein_pct + targets.carbs_pct + targets.fat_pct
        assert 95 <= total_pct <= 105  # rounding tolerance


class TestValidation:
    def test_valid_targets_pass(self, engine, male_user):
        targets = engine.calculate_targets(male_user)
        errors = engine.validate_targets(targets)
        assert errors == []
