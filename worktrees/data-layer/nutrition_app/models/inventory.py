"""
Inventory models — tracking food stock quantities and changes.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from .enums import InventoryAction, UnitType
from nutrition_app.utils import utcnow


@dataclass
class InventoryItem:
    inventory_item_id: str
    food_id: str
    quantity: float
    unit: UnitType
    expiry_date: Optional[str] = None
    added_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "inventory_item_id": self.inventory_item_id,
            "food_id": self.food_id,
            "quantity": self.quantity,
            "unit": self.unit.value,
            "expiry_date": self.expiry_date,
            "added_at": self.added_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InventoryItem":
        return cls(
            inventory_item_id=data["inventory_item_id"],
            food_id=data["food_id"],
            quantity=data["quantity"],
            unit=UnitType(data["unit"]),
            expiry_date=data.get("expiry_date"),
            added_at=datetime.fromisoformat(data["added_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class InventoryChange:
    change_id: str
    inventory_item_id: str
    food_id: str
    action: InventoryAction
    quantity_before: float
    quantity_after: float
    quantity_delta: float
    reason: str
    run_id: Optional[str] = None
    timestamp: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "inventory_item_id": self.inventory_item_id,
            "food_id": self.food_id,
            "action": self.action.value,
            "quantity_before": self.quantity_before,
            "quantity_after": self.quantity_after,
            "quantity_delta": self.quantity_delta,
            "reason": self.reason,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class InventorySnapshot:
    snapshot_id: str
    run_id: str
    timestamp: datetime
    items: List[InventoryItem]

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class InventoryChangeSet:
    run_id: str
    changes: List[InventoryChange]
    snapshot_before: InventorySnapshot
    snapshot_after: Optional[InventorySnapshot] = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "changes": [c.to_dict() for c in self.changes],
            "snapshot_before": self.snapshot_before.to_dict(),
            "snapshot_after": self.snapshot_after.to_dict() if self.snapshot_after else None,
        }


@dataclass
class InventoryState:
    items: Dict[str, InventoryItem] = field(default_factory=dict)

    def get_by_food_id(self, food_id: str) -> Optional[InventoryItem]:
        for item in self.items.values():
            if item.food_id == food_id:
                return item
        return None

    def has_sufficient(self, food_id: str, required_quantity: float) -> bool:
        item = self.get_by_food_id(food_id)
        if item is None:
            return False
        return item.quantity >= required_quantity

    def to_dict(self) -> dict:
        return {
            "items": {k: v.to_dict() for k, v in self.items.items()},
        }
