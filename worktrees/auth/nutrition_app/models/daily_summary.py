#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_summary.py — סיכום יומי של תזונה ופעילות
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DailySummary:
    """
    Snapshot of a user's nutrition and activity for one day.
    Saved every time a meal plan is generated.
    """
    user_id: str
    date: str                   # YYYY-MM-DD

    # Eaten (from generated meal plan)
    calories_eaten: float = 0.0
    protein_eaten: float = 0.0
    carbs_eaten: float = 0.0
    fat_eaten: float = 0.0

    # Targets (from NutritionEngine)
    calories_target: float = 0.0
    protein_target: float = 0.0
    carbs_target: float = 0.0
    fat_target: float = 0.0

    # Activity
    calories_burned: float = 0.0   # From workouts

    # Water (snapshot at save time)
    water_ml: float = 0.0

    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # ── Computed helpers ─────────────────────────────────────────────────────

    @property
    def net_calories(self) -> float:
        """Calories eaten minus calories burned from exercise."""
        return self.calories_eaten - self.calories_burned

    @property
    def calorie_balance(self) -> float:
        """
        Deficit (negative) or surplus (positive) vs target.
        deficit = net_calories - target  (negative means you ate less than target)
        """
        return self.net_calories - self.calories_target

    @property
    def is_deficit(self) -> bool:
        return self.calorie_balance < 0

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "date": self.date,
            "calories_eaten": self.calories_eaten,
            "protein_eaten": self.protein_eaten,
            "carbs_eaten": self.carbs_eaten,
            "fat_eaten": self.fat_eaten,
            "calories_target": self.calories_target,
            "protein_target": self.protein_target,
            "carbs_target": self.carbs_target,
            "fat_target": self.fat_target,
            "calories_burned": self.calories_burned,
            "water_ml": self.water_ml,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailySummary":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
