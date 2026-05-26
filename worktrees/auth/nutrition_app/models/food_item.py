"""
FoodItem model — nutritional source of truth per food item.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .enums import FoodCategory, UnitType


@dataclass
class NutritionPer100g:
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0

    def to_dict(self) -> dict:
        return {
            "calories_kcal": self.calories_kcal,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "fiber_g": self.fiber_g,
            "sugar_g": self.sugar_g,
            "sodium_mg": self.sodium_mg,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NutritionPer100g":
        return cls(**data)


@dataclass
class FoodItem:
    food_id: str
    name_he: str
    name_en: str
    category: FoodCategory
    nutrition_per_100g: NutritionPer100g
    default_unit: UnitType = UnitType.GRAM
    default_serving_g: float = 100.0
    aliases_he: List[str] = field(default_factory=list)
    aliases_en: List[str] = field(default_factory=list)
    is_custom: bool = False
    source: str = "catalog"

    def to_dict(self) -> dict:
        return {
            "food_id": self.food_id,
            "name_he": self.name_he,
            "name_en": self.name_en,
            "category": self.category.value,
            "nutrition_per_100g": self.nutrition_per_100g.to_dict(),
            "default_unit": self.default_unit.value,
            "default_serving_g": self.default_serving_g,
            "aliases_he": self.aliases_he,
            "aliases_en": self.aliases_en,
            "is_custom": self.is_custom,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FoodItem":
        return cls(
            food_id=data["food_id"],
            name_he=data["name_he"],
            name_en=data["name_en"],
            category=FoodCategory(data["category"]),
            nutrition_per_100g=NutritionPer100g.from_dict(data["nutrition_per_100g"]),
            default_unit=UnitType(data.get("default_unit", "gram")),
            default_serving_g=data.get("default_serving_g", 100.0),
            aliases_he=data.get("aliases_he", []),
            aliases_en=data.get("aliases_en", []),
            is_custom=data.get("is_custom", False),
            source=data.get("source", "catalog"),
        )

    def calories_for_grams(self, grams: float) -> float:
        return round(self.nutrition_per_100g.calories_kcal * grams / 100.0, 1)

    def macros_for_grams(self, grams: float) -> dict:
        factor = grams / 100.0
        n = self.nutrition_per_100g
        return {
            "calories_kcal": round(n.calories_kcal * factor, 1),
            "protein_g": round(n.protein_g * factor, 1),
            "carbs_g": round(n.carbs_g * factor, 1),
            "fat_g": round(n.fat_g * factor, 1),
            "fiber_g": round(n.fiber_g * factor, 1),
        }
