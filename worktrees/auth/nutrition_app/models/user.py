"""
User model — represents a user profile in the system.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from .enums import Gender, ActivityLevel, Goal
from nutrition_app.utils import utcnow


@dataclass
class UserProfile:
    user_id: str
    name: str
    gender: Gender
    date_of_birth: date
    height_cm: float
    weight_kg: float
    activity_level: ActivityLevel
    goal: Goal
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    notes: Optional[str] = None

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "gender": self.gender.value,
            "date_of_birth": self.date_of_birth.isoformat(),
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "activity_level": self.activity_level.value,
            "goal": self.goal.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        return cls(
            user_id=data["user_id"],
            name=data["name"],
            gender=Gender(data["gender"]),
            date_of_birth=date.fromisoformat(data["date_of_birth"]),
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            activity_level=ActivityLevel(data["activity_level"]),
            goal=Goal(data["goal"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            notes=data.get("notes"),
        )
