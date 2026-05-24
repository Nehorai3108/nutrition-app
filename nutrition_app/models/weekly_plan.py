"""
WeeklyPlan — seven daily MealPlans (Mon..Sun) generated from UserMealPreferences.

Reuses the existing MealPlan/Meal/MealItem domain models for per-day storage so
the rest of the system (display, logging) can treat each day exactly like a
single-day plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from nutrition_app.models.meal import MealPlan
from nutrition_app.models.user_meal_preferences import WEEKDAYS
from nutrition_app.utils import utcnow


@dataclass
class WeeklyPlan:
    """Seven-day plan keyed by lowercase weekday name ('monday'..'sunday').

    `target_calories_kcal` is the daily target (so weekly = *7). Per-day
    totals come from the inner MealPlan; weekly totals are computed on read.
    """
    plan_id: str
    user_id: str
    week_start: date                          # the Monday this plan begins
    days: Dict[str, MealPlan] = field(default_factory=dict)
    target_calories_kcal: float = 0.0
    target_protein_g: float = 0.0
    target_carbs_g: float = 0.0
    target_fat_g: float = 0.0
    created_at: datetime = field(default_factory=utcnow)

    def day_plan(self, weekday: str) -> Optional[MealPlan]:
        return self.days.get(weekday.lower())

    def date_for(self, weekday: str) -> date:
        idx = WEEKDAYS.index(weekday.lower())
        return self.week_start + timedelta(days=idx)

    def weekday_for(self, target_date: date) -> str:
        delta = (target_date - self.week_start).days
        if 0 <= delta < 7:
            return WEEKDAYS[delta]
        # Out of range: fall back to the natural weekday name.
        return WEEKDAYS[target_date.weekday()]

    # ── Weekly totals (sums across days) ─────────────────────────────────────

    @property
    def weekly_calories(self) -> float:
        return round(sum(d.total_calories for d in self.days.values()), 1)

    @property
    def weekly_protein(self) -> float:
        return round(sum(d.total_protein for d in self.days.values()), 1)

    @property
    def weekly_carbs(self) -> float:
        return round(sum(d.total_carbs for d in self.days.values()), 1)

    @property
    def weekly_fat(self) -> float:
        return round(sum(d.total_fat for d in self.days.values()), 1)

    @property
    def avg_daily_calories(self) -> float:
        n = max(len(self.days), 1)
        return round(self.weekly_calories / n, 1)

    @property
    def avg_daily_protein(self) -> float:
        n = max(len(self.days), 1)
        return round(self.weekly_protein / n, 1)

    @property
    def avg_daily_carbs(self) -> float:
        n = max(len(self.days), 1)
        return round(self.weekly_carbs / n, 1)

    @property
    def avg_daily_fat(self) -> float:
        n = max(len(self.days), 1)
        return round(self.weekly_fat / n, 1)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "week_start": self.week_start.isoformat(),
            "days": {wd: mp.to_dict() for wd, mp in self.days.items()},
            "targets": {
                "calories_kcal": self.target_calories_kcal,
                "protein_g": self.target_protein_g,
                "carbs_g": self.target_carbs_g,
                "fat_g": self.target_fat_g,
            },
            "weekly_totals": {
                "calories_kcal": self.weekly_calories,
                "protein_g": self.weekly_protein,
                "carbs_g": self.weekly_carbs,
                "fat_g": self.weekly_fat,
            },
            "avg_daily_totals": {
                "calories_kcal": self.avg_daily_calories,
                "protein_g": self.avg_daily_protein,
                "carbs_g": self.avg_daily_carbs,
                "fat_g": self.avg_daily_fat,
            },
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
