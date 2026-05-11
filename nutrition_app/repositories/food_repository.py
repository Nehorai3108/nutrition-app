"""
Food Repository — Persistence for FoodItem catalog.
"""

from nutrition_app.repositories.base_repository import BaseRepository
from nutrition_app.models.food_item import FoodItem


class FoodRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "foods")

    def save_food(self, food: FoodItem) -> None:
        self.save(food.food_id, food.to_dict())

    def get_food(self, food_id: str) -> FoodItem | None:
        data = self.get(food_id)
        if data is None:
            return None
        return FoodItem.from_dict(data)
