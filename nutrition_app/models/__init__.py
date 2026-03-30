"""
Models — All domain models for the nutrition system.
Owner: Agent 1 (Domain & Contracts)
"""

from .enums import (
    Gender, ActivityLevel, Goal,
    MealType, UnitType, FoodCategory,
    ConfidenceLevel, InventoryAction,
    WorkflowStage, StageStatus, DecisionType, ArtifactType,
)
from .user import UserProfile
from .food_item import FoodItem, NutritionPer100g
from .food_match import FoodMatch, FoodMatchResult
from .inventory import (
    InventoryItem,
    InventoryChange,
    InventoryChangeSet,
    InventorySnapshot,
    InventoryState,
)
from .meal import Meal, MealItem, MealPlan
from .nutrition_targets import NutritionTargets
from .workflow import (
    ArtifactRecord,
    DecisionGate,
    RunState,
    StageResult,
)
