#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
water.py — מודלים לעקיבות צריכת מים
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List
from uuid import uuid4


@dataclass
class WaterIntake:
    """
    רישום של צריכת מים בזמן מסוים.

    Attributes:
        water_id: מזהה ייחודי לרישום
        user_id: מזהה המשתמש
        timestamp: זמן ספציפי של הצריכה (ISO 8601)
        amount_ml: כמות המים בסמ״ק
        source: מקור המים (בקבוק, כוס, וכו׳)
        notes: הערות אופציונליות
    """
    water_id: str
    user_id: str
    timestamp: str  # ISO 8601 format
    amount_ml: float
    source: str = "water"
    notes: Optional[str] = None

    @classmethod
    def create(cls, user_id: str, amount_ml: float, timestamp: Optional[str] = None,
               source: str = "water", notes: Optional[str] = None) -> "WaterIntake":
        """Create a new water intake entry."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        return cls(
            water_id=str(uuid4())[:8],  # Short UUID
            user_id=user_id,
            timestamp=timestamp,
            amount_ml=amount_ml,
            source=source,
            notes=notes,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WaterIntake":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class WaterGoal:
    """
    מטרת צריכת מים יומית.

    Attributes:
        user_id: מזהה המשתמש
        daily_goal_ml: מטרה יומית בסמ״ק (ברירת מחדל: 2000)
        weekly_goal_ml: מטרה שבועית מחושבת
        created_at: מתי נוצרה המטרה
        updated_at: עדכון אחרון
    """
    user_id: str
    daily_goal_ml: float = 2000.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def weekly_goal_ml(self) -> float:
        """Calculate weekly goal from daily goal."""
        return self.daily_goal_ml * 7

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WaterGoal":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class UserWaterData:
    """
    נתוני מים מלאים עבור משתמש.

    כולל רישום יומי של צריכת מים ומטרה עדכנית.

    Attributes:
        user_id: מזהה המשתמש
        daily_log: מילון של תאריכים (YYYY-MM-DD) לרשימת ערכים
        goal: מטרת המים הנוכחית
        updated_at: עדכון אחרון
    """
    user_id: str
    daily_log: Dict[str, List[WaterIntake]] = field(default_factory=dict)
    goal: Optional[WaterGoal] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Ensure goal exists."""
        if self.goal is None:
            self.goal = WaterGoal(user_id=self.user_id)

    def get_daily_total(self, date_str: str) -> float:
        """
        Get total water intake for a specific date (YYYY-MM-DD).

        Args:
            date_str: Date in format YYYY-MM-DD

        Returns:
            Total water in ml for the day, or 0 if no intakes
        """
        intakes = self.daily_log.get(date_str, [])
        return sum(w.amount_ml for w in intakes)

    def get_week_total(self, end_date_str: str) -> float:
        """
        Get total water intake for the 7 days ending on end_date (inclusive).

        Args:
            end_date_str: End date in format YYYY-MM-DD

        Returns:
            Total water in ml for the week
        """
        from datetime import datetime, timedelta

        end_date = datetime.fromisoformat(end_date_str)
        start_date = end_date - timedelta(days=6)

        total = 0.0
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            total += self.get_daily_total(date_key)
            current_date += timedelta(days=1)

        return total

    def get_intakes_for_date(self, date_str: str) -> List[WaterIntake]:
        """Get all water intakes for a specific date."""
        return self.daily_log.get(date_str, [])

    def add_intake(self, intake: WaterIntake) -> None:
        """Add a water intake entry."""
        # Extract date from ISO timestamp
        date_str = intake.timestamp[:10]  # YYYY-MM-DD
        if date_str not in self.daily_log:
            self.daily_log[date_str] = []
        self.daily_log[date_str].append(intake)
        self.daily_log[date_str].sort(key=lambda x: x.timestamp)
        self.updated_at = datetime.now().isoformat()

    def remove_intake(self, water_id: str, date_str: str) -> bool:
        """Remove a water intake entry by ID."""
        if date_str not in self.daily_log:
            return False

        initial_len = len(self.daily_log[date_str])
        self.daily_log[date_str] = [w for w in self.daily_log[date_str] if w.water_id != water_id]

        if len(self.daily_log[date_str]) < initial_len:
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "daily_log": {
                date: [intake.to_dict() for intake in intakes]
                for date, intakes in self.daily_log.items()
            },
            "goal": self.goal.to_dict() if self.goal else None,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserWaterData":
        """Create from dictionary."""
        daily_log = {}
        for date, intakes_data in data.get("daily_log", {}).items():
            daily_log[date] = [WaterIntake.from_dict(i) for i in intakes_data]

        goal = None
        if data.get("goal"):
            goal = WaterGoal.from_dict(data["goal"])

        return cls(
            user_id=data["user_id"],
            daily_log=daily_log,
            goal=goal,
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
