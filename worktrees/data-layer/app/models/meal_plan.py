"""
MealPlan model — MVP 1
Represents a single day's structured meal plan for one user.
Contains 3–4 meals, each with measured food items.
All macro totals are computed deterministically — never from AI.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import date, datetime
from dataclasses import dataclass, field


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH     = "lunch"
    DINNER    = "dinner"
    SNACK     = "snack"


@dataclass
class MacroTotals:
    """
    Aggregated nutrition values.
    Always computed from FoodItem data — never stored as a free-form value.
    """
    calories:   float
    protein_g:  float
    carbs_g:    float
    fat_g:      float

    def __add__(self, other: "MacroTotals") -> "MacroTotals":
        return MacroTotals(
            calories=round(self.calories  + other.calories,  2),
            protein_g=round(self.protein_g + other.protein_g, 2),
            carbs_g=round(self.carbs_g   + other.carbs_g,   2),
            fat_g=round(self.fat_g     + other.fat_g,     2),
        )

    def to_dict(self) -> dict:
        return {
            "calories":  self.calories,
            "protein_g": self.protein_g,
            "carbs_g":   self.carbs_g,
            "fat_g":     self.fat_g,
        }

    @classmethod
    def zero(cls) -> "MacroTotals":
        return cls(calories=0, protein_g=0, carbs_g=0, fat_g=0)


@dataclass
class MealItem:
    """
    A single food item measured in grams, inside a meal.
    Computed fields (calories, protein_g, carbs_g, fat_g) are populated
    by the Nutrition Engine based on the FoodItem's per-100g values.

    CONTRACT:
    - food_item_id must resolve to a valid FoodItem in the Food DB
    - All computed fields are read-only after creation
    """
    food_item_id: UUID
    quantity_g:   float

    # Computed by Nutrition Engine — not set manually
    calories:  float = 0.0
    protein_g: float = 0.0
    carbs_g:   float = 0.0
    fat_g:     float = 0.0

    def __post_init__(self):
        assert self.quantity_g >= 1, "quantity_g must be at least 1"

    @property
    def totals(self) -> MacroTotals:
        return MacroTotals(
            calories=self.calories,
            protein_g=self.protein_g,
            carbs_g=self.carbs_g,
            fat_g=self.fat_g,
        )

    def to_dict(self) -> dict:
        return {
            "food_item_id": str(self.food_item_id),
            "quantity_g":   self.quantity_g,
            "calories":     self.calories,
            "protein_g":    self.protein_g,
            "carbs_g":      self.carbs_g,
            "fat_g":        self.fat_g,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MealItem":
        return cls(
            food_item_id=UUID(data["food_item_id"]),
            quantity_g=data["quantity_g"],
            calories=data.get("calories", 0.0),
            protein_g=data.get("protein_g", 0.0),
            carbs_g=data.get("carbs_g", 0.0),
            fat_g=data.get("fat_g", 0.0),
        )


@dataclass
class Meal:
    """
    One meal within a day plan (e.g. Breakfast, Lunch, Dinner, Snack).

    CONTRACT:
    - name is optional — may be set by AI for display purposes only
    - totals are always recomputed from items, not stored independently
    """
    meal_type: MealType
    items:     List[MealItem]   = field(default_factory=list)
    meal_id:   UUID             = field(default_factory=uuid4)
    name:      Optional[str]    = None   # AI-generated display name (cosmetic only)

    @property
    def totals(self) -> MacroTotals:
        result = MacroTotals.zero()
        for item in self.items:
            result = result + item.totals
        return result

    def to_dict(self) -> dict:
        return {
            "meal_id":   str(self.meal_id),
            "meal_type": self.meal_type.value,
            "name":      self.name,
            "items":     [i.to_dict() for i in self.items],
            "totals":    self.totals.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Meal":
        return cls(
            meal_id=UUID(data["meal_id"]) if "meal_id" in data else uuid4(),
            meal_type=MealType(data["meal_type"]),
            name=data.get("name"),
            items=[MealItem.from_dict(i) for i in data.get("items", [])],
        )


class MealPlanStatus(str, Enum):
    DRAFT     = "draft"
    CONFIRMED = "confirmed"


@dataclass
class MealPlan:
    """
    A full day's meal plan for a user.

    CONTRACT:
    - Input from: Meal Planning Engine (generated), or user edits
    - Output to: Mobile App (display), Inventory Manager (deduction)
    - calorie_target comes from Nutrition Engine output (or user override)
    - totals are always recomputed from meal items — never stored as free values
    """
    user_id:        UUID
    date:           date
    calorie_target: int
    meals:          List[Meal]       = field(default_factory=list)
    id:             UUID             = field(default_factory=uuid4)
    status:         MealPlanStatus   = MealPlanStatus.DRAFT
    created_at:     datetime         = field(default_factory=datetime.utcnow)
    updated_at:     datetime         = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        assert 800 <= self.calorie_target <= 6000, "calorie_target out of range"
        assert 1 <= len(self.meals) <= 6,          "meals must be between 1 and 6"

    @property
    def totals(self) -> MacroTotals:
        result = MacroTotals.zero()
        for meal in self.meals:
            result = result + meal.totals
        return result

    @property
    def calorie_gap(self) -> float:
        """How many kcal remain to reach the daily target. Negative = over target."""
        return round(self.calorie_target - self.totals.calories, 2)

    def to_dict(self) -> dict:
        return {
            "id":             str(self.id),
            "user_id":        str(self.user_id),
            "date":           self.date.isoformat(),
            "calorie_target": self.calorie_target,
            "meals":          [m.to_dict() for m in self.meals],
            "totals":         self.totals.to_dict(),
            "calorie_gap":    self.calorie_gap,
            "status":         self.status.value,
            "created_at":     self.created_at.isoformat(),
            "updated_at":     self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MealPlan":
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            user_id=UUID(data["user_id"]),
            date=date.fromisoformat(data["date"]),
            calorie_target=data["calorie_target"],
            meals=[Meal.from_dict(m) for m in data.get("meals", [])],
            status=MealPlanStatus(data.get("status", MealPlanStatus.DRAFT.value)),
        )
