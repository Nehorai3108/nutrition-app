"""
Workout models — daily workout log and weekly workout plan.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from nutrition_app.models.enums import WorkoutIntensity, WorkoutType


def _entries_from_raw(raw) -> List["WorkoutEntry"]:
    """Accept either a single entry dict or a list of entry dicts (for migration)."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [WorkoutEntry.from_dict(e) for e in raw]
    if isinstance(raw, dict):
        return [WorkoutEntry.from_dict(raw)]
    return []


@dataclass
class WorkoutEntry:
    """A single workout — either logged for a specific day or scheduled in a weekly plan.

    - `intensity` + `workout_type` may be combined: picking a sport AND specifying
      intensity scales the burn rate by a multiplier.
    - `distance_km` takes precedence over duration for running/walking/hiking.
    """
    duration_minutes: int
    mode: str  # "intensity" or "type"
    intensity: Optional[WorkoutIntensity] = None
    workout_type: Optional[WorkoutType] = None
    distance_km: Optional[float] = None
    estimated_calories_burned: float = 0.0
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "duration_minutes": self.duration_minutes,
            "mode": self.mode,
            "intensity": self.intensity.value if self.intensity else None,
            "workout_type": self.workout_type.value if self.workout_type else None,
            "distance_km": self.distance_km,
            "estimated_calories_burned": self.estimated_calories_burned,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkoutEntry":
        return cls(
            duration_minutes=int(data.get("duration_minutes", 0)),
            mode=data.get("mode", "intensity"),
            intensity=WorkoutIntensity(data["intensity"]) if data.get("intensity") else None,
            workout_type=WorkoutType(data["workout_type"]) if data.get("workout_type") else None,
            distance_km=float(data["distance_km"]) if data.get("distance_km") else None,
            estimated_calories_burned=float(data.get("estimated_calories_burned", 0.0)),
            notes=data.get("notes"),
        )


@dataclass
class WeeklyWorkoutPlan:
    """A template of workouts keyed by weekday name (monday..sunday).
    Each day may contain multiple workouts."""
    user_id: str
    workouts_by_day: Dict[str, List[WorkoutEntry]] = field(default_factory=dict)
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "workouts_by_day": {
                d: [e.to_dict() for e in entries]
                for d, entries in self.workouts_by_day.items()
            },
            "updated_at": self.updated_at or datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WeeklyWorkoutPlan":
        return cls(
            user_id=data["user_id"],
            workouts_by_day={
                d: _entries_from_raw(raw)
                for d, raw in (data.get("workouts_by_day") or {}).items()
            },
            updated_at=data.get("updated_at"),
        )


@dataclass
class UserWorkoutData:
    user_id: str
    weekly_plan: Optional[WeeklyWorkoutPlan] = None
    # key = ISO date "YYYY-MM-DD" → list of workouts (may be multiple per day)
    daily_log: Dict[str, List[WorkoutEntry]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "weekly_plan": self.weekly_plan.to_dict() if self.weekly_plan else None,
            "daily_log": {
                d: [e.to_dict() for e in entries]
                for d, entries in self.daily_log.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserWorkoutData":
        wp = data.get("weekly_plan")
        return cls(
            user_id=data["user_id"],
            weekly_plan=WeeklyWorkoutPlan.from_dict(wp) if wp else None,
            daily_log={
                d: _entries_from_raw(raw)
                for d, raw in (data.get("daily_log") or {}).items()
            },
        )
