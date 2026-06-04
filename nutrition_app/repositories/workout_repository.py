"""
workout_repository.py — per-user workout persistence.

Backends:
  • Supabase (cloud)  — when SUPABASE_URL / SUPABASE_ANON_KEY are configured
                        AND user_id is a real UUID (per-user isolation).
                        Stores UserWorkoutData as a JSONB blob in the
                        `workout_data` table, keyed by user_id.
  • Local JSON files  — fallback for local development.
                        Path: storage_agents/workouts/{user_id}.json
"""

import json
import os
import re
from datetime import date as date_cls, datetime
from typing import List, Optional

from nutrition_app.models.workout import (
    UserWorkoutData,
    WeeklyWorkoutPlan,
    WorkoutEntry,
)

_WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

from nutrition_app.storage_paths import user_workouts_file  # noqa: E402

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)


def _path(user_id: str) -> str:
    return str(user_workouts_file(user_id))


class WorkoutRepository:
    """CRUD for workout data. Auto-selects Supabase or local JSON backend."""

    # ── Backend selector ──────────────────────────────────────────────────────

    def _use_supabase(self, user_id: str = "") -> bool:
        # Per-user isolation: only route to Supabase for real UUID user_ids.
        if not _UUID_RE.match((user_id or "").lower()):
            return False
        try:
            from nutrition_app.db.supabase_client import is_supabase_configured
            return is_supabase_configured()
        except Exception:
            return False

    def _sb(self):
        from nutrition_app.db.supabase_client import get_supabase
        return get_supabase()

    # ── Supabase backend ──────────────────────────────────────────────────────

    def _sb_load(self, user_id: str) -> Optional[dict]:
        rows = (
            self._sb().table("workout_data")
            .select("data").eq("user_id", user_id).limit(1).execute()
        ).data
        if rows:
            blob = rows[0]["data"] or {}
            if isinstance(blob, str):
                blob = json.loads(blob)
            # Ensure user_id is set in the blob for from_dict
            blob.setdefault("user_id", user_id)
            return blob
        return None

    def _sb_save(self, user_id: str, data: dict) -> None:
        self._sb().table("workout_data").upsert(
            {"user_id": user_id, "data": data, "updated_at": datetime.now().isoformat()},
            on_conflict="user_id"
        ).execute()

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _local_load(self, user_id: str) -> Optional[dict]:
        p = _path(user_id)
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _local_save(self, data: UserWorkoutData) -> None:
        with open(_path(data.user_id), "w", encoding="utf-8") as f:
            json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_workout_data(self, user_id: str) -> UserWorkoutData:
        if self._use_supabase(user_id):
            try:
                raw = self._sb_load(user_id)
            except Exception:
                raw = self._local_load(user_id)
        else:
            raw = self._local_load(user_id)
        if raw is None:
            return UserWorkoutData(user_id=user_id)
        raw.setdefault("user_id", user_id)
        return UserWorkoutData.from_dict(raw)

    def _save(self, data: UserWorkoutData) -> None:
        if self._use_supabase(data.user_id):
            try:
                self._sb_save(data.user_id, data.to_dict())
                return
            except Exception:
                pass  # fall through to local save
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
