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
    # Optional measured lean body mass (kg). When None, downstream callers
    # (e.g. macro_calculator.effective_lbm_kg) must derive an estimate from
    # height/weight/gender — never silently default to 0.
    lean_body_mass_kg: Optional[float] = None
    # GLP-1 medication self-report — single tri-state boolean
    # (True / False / None=prefer-not-to-say). Behind FF_GLP1_AWARE_TARGETS.
    # Per privacy policy: we deliberately store NO other GLP1 detail —
    # no medication name, no dose, no injection schedule, no timing.
    glp1_medication_in_use: Optional[bool] = None

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
            "lean_body_mass_kg": self.lean_body_mass_kg,
            "glp1_medication_in_use": self.glp1_medication_in_use,
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
            lean_body_mass_kg=(
                float(data["lean_body_mass_kg"])
                if data.get("lean_body_mass_kg") is not None
                else None
            ),
            glp1_medication_in_use=(
                bool(data["glp1_medication_in_use"])
                if data.get("glp1_medication_in_use") is not None
                else None
            ),
        )
