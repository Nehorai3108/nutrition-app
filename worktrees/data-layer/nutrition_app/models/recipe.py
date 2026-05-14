"""
Recipe model — structured recipe with ingredients and nutrition.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RecipeIngredient:
    food_name: str        # Hebrew name to match against catalog
    food_name_en: str     # English name
    quantity: float       # Amount in default units
    unit: str             # "grams", "units", "tablespoon", "cup", etc.
    food_id: Optional[str] = None  # Resolved catalog food_id

    def to_dict(self) -> dict:
        return {
            "food_name": self.food_name,
            "food_name_en": self.food_name_en,
            "quantity": self.quantity,
            "unit": self.unit,
            "food_id": self.food_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecipeIngredient":
        return cls(**data)


@dataclass
class Recipe:
    recipe_id: str
    name_he: str
    name_en: str
    ingredients: List[RecipeIngredient]
    total_nutrition: dict  # {"calories": X, "protein": X, "carbs": X, "fat": X}
    portions: int = 1
    prep_time_minutes: int = 15
    meal_types: List[str] = field(default_factory=list)  # ["BREAKFAST", "DINNER"]
    tags: List[str] = field(default_factory=list)  # ["vegetarian", "quick"]
    kashrut: str = "parve"  # "dairy" | "meat" | "parve"
    image_path: Optional[str] = None  # Relative path to approved image file
    image_credit: Optional[str] = None  # Photographer credit (e.g., Pexels)

    def to_dict(self) -> dict:
        return {
            "recipe_id": self.recipe_id,
            "name_he": self.name_he,
            "name_en": self.name_en,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "total_nutrition": self.total_nutrition,
            "portions": self.portions,
            "prep_time_minutes": self.prep_time_minutes,
            "meal_types": self.meal_types,
            "tags": self.tags,
            "kashrut": self.kashrut,
            "image_path": self.image_path,
            "image_credit": self.image_credit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Recipe":
        ingredients = [RecipeIngredient.from_dict(i) for i in data.get("ingredients", [])]
        return cls(
            recipe_id=data["recipe_id"],
            name_he=data["name_he"],
            name_en=data["name_en"],
            ingredients=ingredients,
            total_nutrition=data["total_nutrition"],
            portions=data.get("portions", 1),
            prep_time_minutes=data.get("prep_time_minutes", 15),
            meal_types=data.get("meal_types", []),
            tags=data.get("tags", []),
            kashrut=data.get("kashrut", "parve"),
            image_path=data.get("image_path"),
            image_credit=data.get("image_credit"),
        )

    @property
    def calories_per_portion(self) -> float:
        return self.total_nutrition.get("calories", 0) / max(self.portions, 1)
