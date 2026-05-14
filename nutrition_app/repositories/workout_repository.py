"""
Workout Repository — per-user workout persistence.

Backends:
  • Supabase (cloud)  — when SUPABASE_URL / SUPABASE_ANON_KEY are configured.
                        Stores UserWorkoutData as a JSONB blob in
                        the `user_workout_data` table, keyed by user_id.
  • Local JSON files  — fallback for local development.
                        Path: storage_agents/workouts/{user_id}.json
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
    """CRUD for workout data. Dual backend (Supabase or local JSON)."""

    # ── Backend selector ──────────────────────────────────────────────────────

    def _use_supabase(self) -> bool:
        try:
            from nutrition_app.db.supabase_client import is_supabase_configured
            return is_supabase_configured()
        except Exception:
            return False

    def _sb(self):
        from nutrition_app.db.supabase_client import get_supabase
        return get_supabase()

    # ── Supabase backend ──────────────────────────────────────────────────────

    def _sb_load(self, user_id: str) -> UserWorkoutData:
        rows = (
            self._sb().table("user_workout_data")
            .select("blob").eq("user_id", user_id).limit(1).execute()
        ).data
        if not rows:
            return UserWorkoutData(user_id=user_id)
        blob = rows[0].get("blob") or {}
        if isinstance(blob, str):
            blob = json.loads(blob)
        # Ensure user_id is set in the blob for from_dict
        blob.setdefault("user_id", user_id)
        return UserWorkoutData.from_dict(blob)

    def _sb_save(self, data: UserWorkoutData) -> None:
        self._sb().table("user_workout_data").upsert({
            "user_id":    data.user_id,
            "blob":       data.to_dict(),
            "updated_at": datetime.now().isoformat(),
        }, on_conflict="user_id").execute()

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _local_load(self, user_id: str) -> UserWorkoutData:
        path = _path(user_id)
        if not os.path.exists(path):
            return UserWorkoutData(user_id=user_id)
        with open(path, "r", encoding="utf-8") as f:
            return UserWorkoutData.from_dict(json.load(f))

    def _local_save(self, data: UserWorkoutData) -> None:
        with open(_path(data.user_id), "w", encoding="utf-8") as f:
            json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_workout_data(self, user_id: str) -> UserWorkoutData:
        if self._use_supabase():
            return self._sb_load(user_id)
        return self._local_load(user_id)

    def _save(self, data: UserWorkoutData) -> None:
        if self._use_supabase():
            self._sb_save(data)
        else:
            self._local_save(data)

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
