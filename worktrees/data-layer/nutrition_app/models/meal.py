"""
Meal and MealPlan models — structured daily meal planning.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional
from .enums import MealType
from nutrition_app.utils import utcnow


@dataclass
class MealItem:
    food_id: str
    food_name: str
    quantity_g: float
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    from_inventory: bool = False
    inventory_item_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "food_id": self.food_id,
            "food_name": self.food_name,
            "quantity_g": self.quantity_g,
            "calories_kcal": self.calories_kcal,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "from_inventory": self.from_inventory,
            "inventory_item_id": self.inventory_item_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MealItem":
        return cls(**data)


@dataclass
class Meal:
    meal_type: MealType
    items: List[MealItem] = field(default_factory=list)

    @property
    def total_calories(self) -> float:
        return round(sum(i.calories_kcal for i in self.items), 1)

    @property
    def total_protein(self) -> float:
        return round(sum(i.protein_g for i in self.items), 1)

    @property
    def total_carbs(self) -> float:
        return round(sum(i.carbs_g for i in self.items), 1)

    @property
    def total_fat(self) -> float:
        return round(sum(i.fat_g for i in self.items), 1)

    def to_dict(self) -> dict:
        return {
            "meal_type": self.meal_type.value,
            "items": [item.to_dict() for item in self.items],
            "totals": {
                "calories_kcal": self.total_calories,
                "protein_g": self.total_protein,
                "carbs_g": self.total_carbs,
                "fat_g": self.total_fat,
            },
        }


@dataclass
class MealPlan:
    plan_id: str
    user_id: str
    run_id: str
    plan_date: date
    meals: List[Meal] = field(default_factory=list)
    target_calories_kcal: float = 0.0
    created_at: datetime = field(default_factory=utcnow)

    @property
    def total_calories(self) -> float:
        return round(sum(m.total_calories for m in self.meals), 1)

    @property
    def total_protein(self) -> float:
        return round(sum(m.total_protein for m in self.meals), 1)

    @property
    def total_carbs(self) -> float:
        return round(sum(m.total_carbs for m in self.meals), 1)

    @property
    def total_fat(self) -> float:
        return round(sum(m.total_fat for m in self.meals), 1)

    @property
    def calorie_deviation_pct(self) -> float:
        if self.target_calories_kcal == 0:
            return 0.0
        return round(
            ((self.total_calories - self.target_calories_kcal) / self.target_calories_kcal) * 100,
            1,
        )

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "run_id": self.run_id,
            "plan_date": self.plan_date.isoformat(),
            "meals": [meal.to_dict() for meal in self.meals],
            "target_calories_kcal": self.target_calories_kcal,
            "totals": {
                "calories_kcal": self.total_calories,
                "protein_g": self.total_protein,
                "carbs_g": self.total_carbs,
                "fat_g": self.total_fat,
            },
            "calorie_deviation_pct": self.calorie_deviation_pct,
            "created_at": self.created_at.isoformat(),
        }
