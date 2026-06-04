#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
user_meal_preferences_repository.py — persist UserMealPreferences.

Follows the ProfileRepository pattern: auto-select Supabase (cloud) when the
user_id looks like a UUID and Supabase is configured, otherwise fall back to
local JSON files under storage_agents/user_preferences/.

Schema (Supabase table `user_meal_preferences`, optional):
    user_id          uuid primary key
    picks            jsonb        -- {meal_type: [variant_id, ...]}
    fixed_overrides  jsonb        -- {"friday.breakfast": variant_id, ...}
    variants         jsonb        -- list of variant dicts
    onboarded_at     timestamptz
    updated_at       timestamptz
"""
import json
import os
import re
from datetime import datetime
from typing import Optional

from nutrition_app.models.user_meal_preferences import UserMealPreferences
from nutrition_app.utils import utcnow


class UserMealPreferencesRepository:

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "storage_agents", "user_preferences",
            )
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    # ── Backend selector ──────────────────────────────────────────────────────

    def _use_supabase(self, user_id: str = "") -> bool:
        if not re.match(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            (user_id or "").lower(),
        ):
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
        try:
            rows = (
                self._sb().table("user_meal_preferences")
                .select("*").eq("user_id", user_id).limit(1).execute()
            ).data
        except Exception:
            # Table may not exist yet — degrade gracefully to local backend.
            return None
        if not rows:
            return None
        row = rows[0]
        return {
            "user_id": user_id,
            "picks": row.get("picks") or {},
            "fixed_day_overrides": row.get("fixed_overrides") or {},
            "variants": row.get("variants") or [],
            "liked_ingredients": row.get("liked_ingredients") or [],
            "onboarded_at": row.get("onboarded_at"),
            "updated_at": row.get("updated_at"),
            "show_streaks": bool(row.get("show_streaks", False)),
            "daily_notifications": bool(row.get("daily_notifications", False)),
            "weekly_summary": bool(row.get("weekly_summary", False)),
        }

    def _sb_save(self, prefs: UserMealPreferences) -> bool:
        import re as _re
        prefs.updated_at = utcnow()
        payload = {
            "user_id": prefs.user_id,
            "picks": prefs.picks,
            "fixed_overrides": prefs.fixed_day_overrides,
            "variants": [v.to_dict() for v in prefs.variants],
            "liked_ingredients": list(prefs.liked_ingredients),
            "onboarded_at": prefs.onboarded_at.isoformat() if isinstance(prefs.onboarded_at, datetime) else prefs.onboarded_at,
            "updated_at": prefs.updated_at.isoformat(),
            "show_streaks": prefs.show_streaks,
            "daily_notifications": prefs.daily_notifications,
            "weekly_summary": prefs.weekly_summary,
        }
        # Drift-tolerant: strip unknown columns and retry, up to 8 times.
        # Same pattern ProfileRepository uses for schema drift.
        for _ in range(8):
            try:
                self._sb().table("user_meal_preferences").upsert(
                    payload, on_conflict="user_id"
                ).execute()
                return True
            except Exception as e:
                msg = str(e)
                m = _re.search(r"Could not find the '([^']+)' column", msg)
                if not m:
                    return False
                col = m.group(1)
                if col not in payload or col == "user_id":
                    return False
                payload.pop(col, None)
        return False

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _path(self, user_id: str) -> str:
        return os.path.join(self.base_dir, f"{user_id}.json")

    def _local_load(self, user_id: str) -> Optional[dict]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _local_save(self, prefs: UserMealPreferences) -> None:
        prefs.updated_at = utcnow()
        data = prefs.to_dict()
        with open(self._path(prefs.user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, user_id: str) -> Optional[UserMealPreferences]:
        """Return persisted preferences, or None if the user has never saved."""
        if self._use_supabase(user_id):
            data = self._sb_load(user_id)
            if data is not None:
                return UserMealPreferences.from_dict(data)
        data = self._local_load(user_id)
        if data is None:
            return None
        return UserMealPreferences.from_dict(data)

    def save(self, prefs: UserMealPreferences) -> None:
        """Persist preferences. Falls back to local JSON if Supabase fails."""
        wrote_cloud = False
        if self._use_supabase(prefs.user_id):
            wrote_cloud = self._sb_save(prefs)
        # Always keep a local copy too — survives Supabase outages and makes
        # dev iteration trivial.
        self._local_save(prefs)
        _ = wrote_cloud  # not currently surfaced; kept for future telemetry

    def has_completed_onboarding(self, user_id: str) -> bool:
        prefs = self.load(user_id)
        return bool(prefs and prefs.is_onboarded)
