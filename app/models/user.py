"""
User model — Agent 1 (Data Contracts)
======================================
OWNED BY: Agent 1
SCOPE: Field definitions, enums, validation constraints, serialization only.

What is NOT here (by design):
- PAL multiplier values          → owned by Agent 2 (Nutrition Engine)
- Calorie delta per goal         → owned by Agent 2 (Nutrition Engine)
- TDEE / BMR formulas            → owned by Agent 2 (Nutrition Engine)
- Any calculation of any kind    → owned by Agent 2 (Nutrition Engine)

Contract for Agent 2:
  INPUT fields required from User:
    age, gender, height_cm, weight_kg, activity_level, goal,
    calorie_target_override (nullable)
  Agent 2 is responsible for mapping ActivityLevel → PAL multiplier
  Agent 2 is responsible for mapping Goal → calorie delta
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field


# ── Enums (values only — no business logic) ──────────────────────────────────

class ActivityLevel(str, Enum):
    """
    User's physical activity level.
    These are the valid string values for the activity_level field.

    AGENT 2 CONTRACT:
    Agent 2 (Nutrition Engine) is responsible for defining the PAL
    multiplier that corresponds to each value. This enum does NOT
    contain that mapping.
    """
    SEDENTARY         = "sedentary"
    LIGHTLY_ACTIVE    = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE       = "very_active"
    EXTRA_ACTIVE      = "extra_active"


class Goal(str, Enum):
    """
    User's dietary goal.
    These are the valid string values for the goal field.

    AGENT 2 CONTRACT:
    Agent 2 (Nutrition Engine) is responsible for defining the calorie
    surplus/deficit delta that corresponds to each value. This enum
    does NOT contain that mapping.
    """
    LOSE_WEIGHT  = "lose_weight"
    MAINTAIN     = "maintain"
    GAIN_MUSCLE  = "gain_muscle"


class DietaryRestriction(str, Enum):
    """Valid dietary restriction tags. Used by Agent 5 (Meal Planning Engine)
    to filter food items."""
    VEGETARIAN   = "vegetarian"
    VEGAN        = "vegan"
    GLUTEN_FREE  = "gluten_free"
    LACTOSE_FREE = "lactose_free"
    HALAL        = "halal"
    KOSHER       = "kosher"
    NUT_FREE     = "nut_free"


class SubscriptionTier(str, Enum):
    """User's subscription level. Used by Agent 7 (Payments)."""
    FREE    = "free"
    BASIC   = "basic"
    PREMIUM = "premium"


# ── User dataclass ────────────────────────────────────────────────────────────

@dataclass
class User:
    """
    Core user entity.

    FIELD OWNERSHIP:
    ┌──────────────────────────────┬───────────────────────────────────────┐
    │ Field                        │ Consumed by                           │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ age, gender, height_cm,      │ Agent 2 — Nutrition Engine            │
    │ weight_kg, activity_level,   │ (TDEE + calorie target)               │
    │ goal, calorie_target_override│                                       │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ dietary_restrictions         │ Agent 5 — Meal Planning Engine        │
    │                              │ (food item filtering)                 │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ subscription_tier            │ Agent 7 — Payments                    │
    ├──────────────────────────────┼───────────────────────────────────────┤
    │ id, email, name              │ All modules (identity reference)      │
    └──────────────────────────────┴───────────────────────────────────────┘
    """
    # Required fields
    name:           str
    email:          str
    age:            int
    gender:         str            # Allowed values: "male" | "female" | "other"
    height_cm:      float
    weight_kg:      float
    activity_level: ActivityLevel
    goal:           Goal

    # Optional fields
    id:                      UUID                      = field(default_factory=uuid4)
    calorie_target_override: Optional[int]             = None
    dietary_restrictions:    List[DietaryRestriction]  = field(default_factory=list)
    subscription_tier:       SubscriptionTier          = SubscriptionTier.FREE
    created_at:              datetime                  = field(default_factory=datetime.utcnow)
    updated_at:              datetime                  = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        # ── Validation constraints (Agent 1 authority) ──────────────────────
        assert self.gender in ("male", "female", "other"), \
            f"gender must be 'male', 'female', or 'other'. Got: {self.gender!r}"
        assert 10 <= self.age <= 120, \
            f"age must be between 10 and 120. Got: {self.age}"
        assert 50 <= self.height_cm <= 250, \
            f"height_cm must be between 50 and 250. Got: {self.height_cm}"
        assert 20 <= self.weight_kg <= 300, \
            f"weight_kg must be between 20 and 300. Got: {self.weight_kg}"
        if self.calorie_target_override is not None:
            assert 800 <= self.calorie_target_override <= 6000, \
                f"calorie_target_override must be 800–6000. Got: {self.calorie_target_override}"

    def to_dict(self) -> dict:
        return {
            "id":                      str(self.id),
            "name":                    self.name,
            "email":                   self.email,
            "age":                     self.age,
            "gender":                  self.gender,
            "height_cm":               self.height_cm,
            "weight_kg":               self.weight_kg,
            "activity_level":          self.activity_level.value,
            "goal":                    self.goal.value,
            "calorie_target_override": self.calorie_target_override,
            "dietary_restrictions":    [r.value for r in self.dietary_restrictions],
            "subscription_tier":       self.subscription_tier.value,
            "created_at":              self.created_at.isoformat(),
            "updated_at":              self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data["name"],
            email=data["email"],
            age=data["age"],
            gender=data["gender"],
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            activity_level=ActivityLevel(data["activity_level"]),
            goal=Goal(data["goal"]),
            calorie_target_override=data.get("calorie_target_override"),
            dietary_restrictions=[
                DietaryRestriction(r) for r in data.get("dietary_restrictions", [])
            ],
            subscription_tier=SubscriptionTier(
                data.get("subscription_tier", SubscriptionTier.FREE.value)
            ),
        )
