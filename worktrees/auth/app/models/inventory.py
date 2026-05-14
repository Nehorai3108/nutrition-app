"""
Inventory model — MVP 1
Tracks what food items a user currently has at home.
Used by the Meal Planning Engine to prefer available ingredients
and flag missing ones. No expiry dates in MVP 1.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field


class InventoryUnit(str, Enum):
    GRAMS  = "g"
    ML     = "ml"
    UNITS  = "units"
    TBSP   = "tbsp"
    TSP    = "tsp"
    CUP    = "cup"


@dataclass
class InventoryItem:
    """
    One line in the user's inventory.

    CONTRACT:
    - food_item_id must reference a valid FoodItem
    - quantity = 0 means the item is out of stock (not removed, just flagged)
    """
    food_item_id: UUID
    quantity:     float
    unit:         InventoryUnit
    added_at:     datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        assert self.quantity >= 0, "quantity cannot be negative"

    @property
    def is_available(self) -> bool:
        return self.quantity > 0

    def to_dict(self) -> dict:
        return {
            "food_item_id": str(self.food_item_id),
            "quantity":     self.quantity,
            "unit":         self.unit.value,
            "added_at":     self.added_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InventoryItem":
        return cls(
            food_item_id=UUID(data["food_item_id"]),
            quantity=data["quantity"],
            unit=InventoryUnit(data["unit"]),
        )


@dataclass
class Inventory:
    """
    A user's complete food inventory.
    One Inventory document per user (upserted, not duplicated).

    CONTRACT:
    - Input from: User manual entry (MVP 1 only — no barcode/OCR)
    - Output to: Meal Planning Engine (available_ids set),
                 Mobile App (shopping list = missing items)
    """
    user_id:    UUID
    items:      List[InventoryItem] = field(default_factory=list)
    id:         UUID                = field(default_factory=uuid4)
    updated_at: datetime            = field(default_factory=datetime.utcnow)

    def get_item(self, food_item_id: UUID) -> Optional[InventoryItem]:
        """Return the InventoryItem for a given food_item_id, or None."""
        for item in self.items:
            if item.food_item_id == food_item_id:
                return item
        return None

    def has(self, food_item_id: UUID) -> bool:
        """True if the item exists in inventory with quantity > 0."""
        item = self.get_item(food_item_id)
        return item is not None and item.is_available

    def available_food_ids(self) -> List[UUID]:
        """Returns list of food_item_ids currently in stock."""
        return [i.food_item_id for i in self.items if i.is_available]

    def upsert(self, food_item_id: UUID, quantity: float, unit: InventoryUnit) -> None:
        """Add or update a food item in the inventory."""
        existing = self.get_item(food_item_id)
        if existing:
            existing.quantity = quantity
            existing.unit = unit
        else:
            self.items.append(InventoryItem(
                food_item_id=food_item_id,
                quantity=quantity,
                unit=unit,
            ))
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id":         str(self.id),
            "user_id":    str(self.user_id),
            "items":      [i.to_dict() for i in self.items],
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Inventory":
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            user_id=UUID(data["user_id"]),
            items=[InventoryItem.from_dict(i) for i in data.get("items", [])],
        )
