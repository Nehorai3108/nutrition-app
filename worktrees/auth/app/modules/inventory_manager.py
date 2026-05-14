"""
Inventory Manager — Interface Contract (Agent 1 handoff to Agent 4)
====================================================================
!! NON-AUTHORITATIVE DRAFT — FOR STRUCTURAL REFERENCE ONLY !!

OWNED BY:     Agent 4
WRITTEN BY:   Agent 1 (interface stub only)
PURPOSE:      Define the input contract, output contract, and method
              signatures that Agent 4 must satisfy.
              Agent 4 must replace this file's implementation entirely.
              Agent 1 does NOT define inventory business logic,
              deduction policies, or unit conversion rules.

--------------------------------------------------------------------
WHAT AGENT 4 MUST IMPLEMENT (not defined here):
  - Add / update / remove inventory items
  - Check availability of a food item
  - Deduct used quantities after meal plan confirmation
  - Shopping list generation
  - Any unit conversion logic
  - Persistence strategy (DB, cache, etc.)
--------------------------------------------------------------------
WHAT THIS FILE DEFINES (Agent 1 authority):
  - AvailabilityReport output structure and field types
  - Required method signatures for the InventoryManager class
  - Required inputs and outputs per method
  - Module isolation rules
--------------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.models.inventory import Inventory, InventoryUnit
    from app.models.food_item import FoodItem


# ── Output Contract ───────────────────────────────────────────────────────────

@dataclass
class AvailabilityReport:
    """
    OUTPUT CONTRACT — produced by InventoryManager.check_availability().
    This structure is frozen by Agent 1.

    CONSUMED BY:
    - Agent 5 (Meal Planning Engine): uses available_ids to prefer in-stock items
    - Agent 8 (Mobile App): displays shopping_list to user

    FIELD CONSTRAINTS (Agent 1 authority):
    - available_ids  : list of UUID, subset of required_food_ids
    - missing_ids    : list of UUID, subset of required_food_ids
    - shopping_list  : list of str (human-readable food names)
    - available_ids + missing_ids must equal the full set of required_food_ids
    """
    available_ids:  List[UUID]   = field(default_factory=list)
    missing_ids:    List[UUID]   = field(default_factory=list)
    shopping_list:  List[str]    = field(default_factory=list)


# ── Module Interface ──────────────────────────────────────────────────────────

class InventoryManager:
    """
    !! STUB ONLY — Agent 4 must replace this implementation !!

    METHOD CONTRACTS (signatures frozen by Agent 1):

    ┌──────────────────────────────────────────────────────────────────────┐
    │ add_item(inventory, food_item_id, quantity, unit) -> Inventory       │
    │   Adds or replaces a food item in the user's inventory.              │
    │   If food_item_id already exists → quantity is replaced, not added.  │
    ├──────────────────────────────────────────────────────────────────────┤
    │ remove_item(inventory, food_item_id) -> Inventory                    │
    │   Completely removes an item entry from the inventory.               │
    ├──────────────────────────────────────────────────────────────────────┤
    │ set_quantity(inventory, food_item_id, new_quantity) -> Inventory     │
    │   Updates the quantity of an existing item.                          │
    │   Raises ValueError if food_item_id is not found.                   │
    ├──────────────────────────────────────────────────────────────────────┤
    │ check_availability(inventory, required_food_ids, food_db)            │
    │   -> AvailabilityReport                                              │
    │   Checks which of required_food_ids are available in inventory.      │
    │   food_db is used to resolve item names for shopping_list.           │
    ├──────────────────────────────────────────────────────────────────────┤
    │ get_available_ids(inventory) -> List[UUID]                           │
    │   Returns all food_item_ids with quantity > 0.                       │
    │   Passed directly to Agent 5 as the available_ids input.            │
    ├──────────────────────────────────────────────────────────────────────┤
    │ deduct_meal_plan(inventory, required) -> Inventory                   │
    │   Deducts used quantities after a meal plan is confirmed.            │
    │   required: List[Tuple[UUID, float]] = (food_item_id, quantity_g)   │
    │   Quantity floor is 0 — must never go negative.                     │
    │   Called only when MealPlan.status changes to "confirmed".          │
    └──────────────────────────────────────────────────────────────────────┘

    ISOLATION RULES:
      - Must NOT import or call NutritionEngine
      - Must NOT import or call MealPlanningEngine
      - Must NOT perform calorie calculations of any kind
      - Must NOT call any AI service
      - Inventory quantity must never go below 0
    """

    def add_item(
        self,
        inventory: "Inventory",
        food_item_id: UUID,
        quantity: float,
        unit: "InventoryUnit",
    ) -> "Inventory":
        raise NotImplementedError("InventoryManager.add_item() — Agent 4 must implement.")

    def remove_item(
        self,
        inventory: "Inventory",
        food_item_id: UUID,
    ) -> "Inventory":
        raise NotImplementedError("InventoryManager.remove_item() — Agent 4 must implement.")

    def set_quantity(
        self,
        inventory: "Inventory",
        food_item_id: UUID,
        new_quantity: float,
    ) -> "Inventory":
        raise NotImplementedError("InventoryManager.set_quantity() — Agent 4 must implement.")

    def check_availability(
        self,
        inventory: "Inventory",
        required_food_ids: List[UUID],
        food_db: dict,
    ) -> AvailabilityReport:
        raise NotImplementedError("InventoryManager.check_availability() — Agent 4 must implement.")

    def get_available_ids(
        self,
        inventory: "Inventory",
    ) -> List[UUID]:
        raise NotImplementedError("InventoryManager.get_available_ids() — Agent 4 must implement.")

    def deduct_meal_plan(
        self,
        inventory: "Inventory",
        required: List[tuple],
    ) -> "Inventory":
        raise NotImplementedError("InventoryManager.deduct_meal_plan() — Agent 4 must implement.")
