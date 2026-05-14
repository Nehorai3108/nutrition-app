"""
Workout Repository — per-user JSON persistence of workouts.
Pattern mirrors nutrition_app/user_manager.py inventory functions.

Storage: storage_agents/workouts/{user_id}.json
"""

import json
import os
from datetime import date as date_cls, datetime
from typing import List

from nutrition_app.models.workout import (
    UserWorkoutData,
    WeeklyWorkoutPlan,
    WorkoutEntry,
)

_WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _storage_dir() -> str:
    folder = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "storage_agents",
        "workouts",
    )
    os.makedirs(folder, exist_ok=True)
    return folder


def _path(user_id: str) -> str:
    return os.path.join(_storage_dir(), f"{user_id}.json")


class WorkoutRepository:
    """CRUD for workout data. JSON file per user."""

    def get_workout_data(self, user_id: str) -> UserWorkoutData:
        path = _path(user_id)
        if not os.path.exists(path):
            return UserWorkoutData(user_id=user_id)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return UserWorkoutData.from_dict(data)

    def _save(self, data: UserWorkoutData) -> None:
        with open(_path(data.user_id), "w", encoding="utf-8") as f:
            json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)

    def save_weekly_plan(self, user_id: str, plan: WeeklyWorkoutPlan) -> None:
        current = self.get_workout_data(user_id)
        plan.updated_at = datetime.now().isoformat()
        current.weekly_plan = plan
        self._save(current)

    def add_daily_workout(self, user_id: str, day: date_cls, entry: WorkoutEntry) -> None:
        """Append a workout to the list for that day."""
        current = self.get_workout_data(user_id)
        iso = day.isoformat()
        current.daily_log.setdefault(iso, []).append(entry)
        self._save(current)

    def remove_daily_workout(self, user_id: str, day: date_cls, index: int) -> None:
        """Remove a single workout by index from that day's list."""
        current = self.get_workout_data(user_id)
        iso = day.isoformat()
        entries = current.daily_log.get(iso)
        if entries and 0 <= index < len(entries):
            entries.pop(index)
            if not entries:
                current.daily_log.pop(iso, None)
            self._save(current)

    def clear_daily_workouts(self, user_id: str, day: date_cls) -> None:
        """Remove all workouts for a given day."""
        current = self.get_workout_data(user_id)
        current.daily_log.pop(day.isoformat(), None)
        self._save(current)

    def resolve_workouts_for_date(
        self, user_id: str, day: date_cls
    ) -> List[WorkoutEntry]:
        """
        Return the list of workouts for the given day.
        Daily log overrides the weekly plan for that day entirely.
        Returns an empty list if nothing scheduled.
        """
        data = self.get_workout_data(user_id)
        iso = day.isoformat()
        if iso in data.daily_log:
            return list(data.daily_log[iso])
        if data.weekly_plan is not None:
            weekday = _WEEKDAY_NAMES[day.weekday()]
            return list(data.weekly_plan.workouts_by_day.get(weekday, []))
        return []
