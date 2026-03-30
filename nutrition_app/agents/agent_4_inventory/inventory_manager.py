"""
Agent 4 — Inventory Manager Owner

Responsibility:
- Add/update/remove inventory items
- Quantity tracking
- Availability checks
- Reservation/deduction only after approval
- Stock consistency
- Before/after snapshots mandatory

Input:  user actions, approved plan, food references
Output: InventoryState, InventorySnapshot, InventoryChangeSet

Rules:
- No negative quantities
- Every change must be documented
- Before/after snapshots mandatory

Forbidden:
- Nutrition calculations
- Meal planning
- Food matching logic
- Performance policy design
"""

import uuid
from typing import Optional

from nutrition_app.utils import utcnow
from nutrition_app.models.enums import InventoryAction, UnitType
from nutrition_app.models.inventory import (
    InventoryChange,
    InventoryChangeSet,
    InventoryItem,
    InventorySnapshot,
    InventoryState,
)
from nutrition_app.models.meal import MealPlan


class InventoryManager:
    """Manages food inventory with full audit trail."""

    def __init__(self):
        self._states: dict = {}  # user_id -> InventoryState
        self._change_log: list = []

    def _ensure_state(self, user_id: str) -> InventoryState:
        if user_id not in self._states:
            self._states[user_id] = InventoryState()
        return self._states[user_id]

    def get_state(self, user_id: str) -> InventoryState:
        return self._ensure_state(user_id)

    def add_item(
        self, user_id: str, food_id: str, quantity: float, unit: str
    ) -> InventoryState:
        state = self._ensure_state(user_id)
        existing = state.get_by_food_id(food_id)

        if existing:
            change = InventoryChange(
                change_id=str(uuid.uuid4()),
                inventory_item_id=existing.inventory_item_id,
                food_id=food_id,
                action=InventoryAction.UPDATE,
                quantity_before=existing.quantity,
                quantity_after=existing.quantity + quantity,
                quantity_delta=quantity,
                reason="add_item",
            )
            existing.quantity += quantity
            existing.updated_at = utcnow()
        else:
            item_id = str(uuid.uuid4())
            new_item = InventoryItem(
                inventory_item_id=item_id,
                food_id=food_id,
                quantity=quantity,
                unit=UnitType(unit),
            )
            state.items[item_id] = new_item
            change = InventoryChange(
                change_id=str(uuid.uuid4()),
                inventory_item_id=item_id,
                food_id=food_id,
                action=InventoryAction.ADD,
                quantity_before=0.0,
                quantity_after=quantity,
                quantity_delta=quantity,
                reason="add_item",
            )

        self._change_log.append(change)
        return state

    def remove_item(self, user_id: str, food_id: str) -> InventoryState:
        state = self._ensure_state(user_id)
        item = state.get_by_food_id(food_id)
        if item:
            change = InventoryChange(
                change_id=str(uuid.uuid4()),
                inventory_item_id=item.inventory_item_id,
                food_id=food_id,
                action=InventoryAction.REMOVE,
                quantity_before=item.quantity,
                quantity_after=0.0,
                quantity_delta=-item.quantity,
                reason="remove_item",
            )
            del state.items[item.inventory_item_id]
            self._change_log.append(change)
        return state

    def check_availability(self, user_id: str, food_id: str, quantity: float) -> bool:
        state = self._ensure_state(user_id)
        return state.has_sufficient(food_id, quantity)

    def take_snapshot(self, user_id: str, run_id: str) -> InventorySnapshot:
        state = self._ensure_state(user_id)
        return InventorySnapshot(
            snapshot_id=str(uuid.uuid4()),
            run_id=run_id,
            timestamp=utcnow(),
            items=list(state.items.values()),
        )

    def deduct_for_plan(
        self, user_id: str, plan: MealPlan, run_id: str
    ) -> InventoryChangeSet:
        """Deduct inventory for an approved meal plan. Only called after confirmation."""
        state = self._ensure_state(user_id)
        snapshot_before = self.take_snapshot(user_id, run_id)
        changes = []

        for meal in plan.meals:
            for meal_item in meal.items:
                if not meal_item.from_inventory:
                    continue

                inv_item = state.get_by_food_id(meal_item.food_id)
                if inv_item is None:
                    continue

                deduct_qty = meal_item.quantity_g
                qty_before = inv_item.quantity
                qty_after = max(0.0, inv_item.quantity - deduct_qty)

                change = InventoryChange(
                    change_id=str(uuid.uuid4()),
                    inventory_item_id=inv_item.inventory_item_id,
                    food_id=meal_item.food_id,
                    action=InventoryAction.DEDUCT,
                    quantity_before=qty_before,
                    quantity_after=qty_after,
                    quantity_delta=-(qty_before - qty_after),
                    reason=f"meal_plan:{plan.plan_id}",
                    run_id=run_id,
                )
                inv_item.quantity = qty_after
                inv_item.updated_at = utcnow()
                changes.append(change)
                self._change_log.append(change)

        snapshot_after = self.take_snapshot(user_id, run_id)

        return InventoryChangeSet(
            run_id=run_id,
            changes=changes,
            snapshot_before=snapshot_before,
            snapshot_after=snapshot_after,
        )

    def get_change_log(self) -> list:
        return self._change_log
