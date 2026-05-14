"""
FoodItem model — Agent 1 (Data Contracts)
==========================================
OWNED BY: Agent 1
SCOPE: Field definitions, enums, validation constraints, serialization only.

What is NOT here (by design):
- Per-portion calorie calculation   → owned by Agent 2 (Nutrition Engine)
- Macro scaling formulas            → owned by Agent 2 (Nutrition Engine)
- Any arithmetic on food values     → owned by Agent 2 (Nutrition Engine)

Contract for Agent 2:
  The formula for any per-portion macro value is:
    macro_value = (macro_per_100g / 100) * quantity_g
  Agent 2 is solely responsible for implementing and calling this formula.
  It must use the fields: calories_per_100g, protein_per_100g,
  carbs_per_100g, fat_per_100g directly from this model.

Contract for Agent 5:
  default_serving_g is a hint for the Meal Planning Engine.
  Agent 5 decides whether and how to use it.

CRITICAL RULE:
  calories_per_100g and all macro_per_100g fields are the single source
  of truth. They must never be modified by the AI layer.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field


# ── Enums ────────────────────────────────────────────────────────────────────

class FoodCategory(str, Enum):
    """
    Broad category of the food item.
    Used by Agent 5 (Meal Planning Engine) for meal composition logic.
    """
    PROTEIN      = "protein"
    CARBOHYDRATE = "carbohydrate"
    VEGETABLE    = "vegetable"
    FRUIT        = "fruit"
    DAIRY        = "dairy"
    FAT_OIL      = "fat_oil"
    BEVERAGE     = "beverage"
    SNACK        = "snack"
    CONDIMENT    = "condiment"
    OTHER        = "other"


# ── FoodItem dataclass ────────────────────────────────────────────────────────

@dataclass
class FoodItem:
    """
    A single food product.

    FIELD OWNERSHIP:
    ┌──────────────────────────────┬───────────────────────────────────────┐
    │ Field                        │ Consumed by                           │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ calories_per_100g,           │ Agent 2 — Nutrition Engine            │
    │ protein_per_100g,            │ (all macro calculations)              │
    │ carbs_per_100g, fat_per_100g │                                       │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ category, default_serving_g  │ Agent 5 — Meal Planning Engine        │
    │                              │ (meal composition + portion hints)    │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ id, name                     │ All modules (reference + display)     │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ is_custom, created_by_user_id│ Agent 3 — Food Database               │
    └──────────────────────────────┴───────────────────────────────────────┘

    STORAGE RULE:
    All macro values are stored per 100g. No exceptions.
    No pre-computed portion values are stored on this model.
    """
    # Required fields
    name:              str
    calories_per_100g: float
    protein_per_100g:  float
    carbs_per_100g:    float
    fat_per_100g:      float
    category:          FoodCategory

    # Optional fields
    id:                  UUID            = field(default_factory=uuid4)
    brand:               Optional[str]   = None
    fiber_per_100g:      Optional[float] = None
    default_serving_g:   Optional[float] = None
    is_custom:           bool            = False
    created_by_user_id:  Optional[UUID]  = None
    created_at:          datetime        = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        # ── Validation constraints (Agent 1 authority) ──────────────────────
        assert 0 <= self.calories_per_100g <= 900, \
            f"calories_per_100g must be 0–900. Got: {self.calories_per_100g}"
        assert 0 <= self.protein_per_100g <= 100, \
            f"protein_per_100g must be 0–100. Got: {self.protein_per_100g}"
        assert 0 <= self.carbs_per_100g <= 100, \
            f"carbs_per_100g must be 0–100. Got: {self.carbs_per_100g}"
        assert 0 <= self.fat_per_100g <= 100, \
            f"fat_per_100g must be 0–100. Got: {self.fat_per_100g}"
        if self.fiber_per_100g is not None:
            assert 0 <= self.fiber_per_100g <= 100, \
                f"fiber_per_100g must be 0–100. Got: {self.fiber_per_100g}"
        if self.default_serving_g is not None:
            assert self.default_serving_g >= 1, \
                f"default_serving_g must be >= 1. Got: {self.default_serving_g}"

    def to_dict(self) -> dict:
        return {
            "id":                  str(self.id),
            "name":                self.name,
            "brand":               self.brand,
            "calories_per_100g":   self.calories_per_100g,
            "protein_per_100g":    self.protein_per_100g,
            "carbs_per_100g":      self.carbs_per_100g,
            "fat_per_100g":        self.fat_per_100g,
            "fiber_per_100g":      self.fiber_per_100g,
            "default_serving_g":   self.default_serving_g,
            "category":            self.category.value,
            "is_custom":           self.is_custom,
            "created_by_user_id":  str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at":          self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FoodItem":
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data["name"],
            brand=data.get("brand"),
            calories_per_100g=data["calories_per_100g"],
            protein_per_100g=data["protein_per_100g"],
            carbs_per_100g=data["carbs_per_100g"],
            fat_per_100g=data["fat_per_100g"],
            fiber_per_100g=data.get("fiber_per_100g"),
            default_serving_g=data.get("default_serving_g"),
            category=FoodCategory(data["category"]),
            is_custom=data.get("is_custom", False),
            created_by_user_id=UUID(data["created_by_user_id"])
                if data.get("created_by_user_id") else None,
        )
