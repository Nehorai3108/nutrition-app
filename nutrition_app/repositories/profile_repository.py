#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
profile_repository.py — שמירה וטעינה של פרופיל מורחב
"""
import json
import os
from datetime import datetime, date
from typing import Optional

_DEFAULTS = {
    "user_id": "",  # never default to a real user id — caller must supply
    "name": "",
    "gender": "male",
    "date_of_birth": "",
    "height_cm": 0.0,
    "weight_kg": 0.0,
    "activity_level": "moderately_active",
    "goal": "maintain",
    "meal_preferences": {
        "kashrut": "parve",          # parve / dairy / meat
        "allergies": [],             # list of strings
        "preferred_foods": [],       # food names the user likes
        "disliked_foods": [],        # food names to avoid
        "meals_per_day": 5,
    },
    "updated_at": "",
}


class ProfileRepository:
    """
    Stores user profile (incl. meal preferences).
    Auto-selects Supabase (cloud) or local JSON (dev) backend.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "storage_agents", "profiles",
            )
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    # ── Backend selector ──────────────────────────────────────────────────────

    def _use_supabase(self) -> bool:
        try:
            from nutrition_app.db.supabase_client import is_supabase_configured
            if not is_supabase_configured():
                return False
            # בהקשר Streamlit — דרוש משתמש מחובר אמיתי (לא dev)
            try:
                import streamlit as st
                if st.runtime.exists():
                    uid = st.session_state.get("user_id", "")
                    return bool(uid and uid != "ui_user_001")
            except Exception:
                pass
            return True  # בהקשר API — מספיק ש-Supabase מוגדר
        except Exception:
            return False

    def _sb(self):
        from nutrition_app.db.supabase_client import get_supabase
        return get_supabase()

    # ── Supabase backend ──────────────────────────────────────────────────────

    def _sb_load(self, user_id: str) -> Optional[dict]:
        rows = (
            self._sb().table("profiles")
            .select("*").eq("user_id", user_id).limit(1).execute()
        ).data
        if not rows:
            return None
        row = rows[0]
        # meal_preferences is JSONB — Supabase Python client returns it as a
        # parsed dict already, but tolerate string-form for legacy rows.
        prefs_raw = row.get("meal_preferences")
        if isinstance(prefs_raw, str):
            try:
                prefs = json.loads(prefs_raw)
            except (ValueError, TypeError):
                prefs = {}
        elif isinstance(prefs_raw, dict):
            prefs = prefs_raw
        else:
            prefs = {}
        # Goal-planning fields: prefer the dedicated column, but fall back to the
        # JSONB copy (which always survives even when the columns don't exist).
        target_weight = row.get("target_weight_kg")
        if target_weight is None:
            target_weight = prefs.get("target_weight_kg")
        weeks_to_goal = row.get("weeks_to_goal")
        if weeks_to_goal is None:
            weeks_to_goal = prefs.get("weeks_to_goal")
        weekly_change = row.get("weekly_change_kg")
        if weekly_change is None:
            weekly_change = prefs.get("weekly_change_kg")
        pace = row.get("pace") or prefs.get("pace")

        d = dict(_DEFAULTS)
        d.update({
            "user_id":          user_id,
            "name":             row.get("name") or "",
            "gender":           row.get("gender") or d["gender"],
            "date_of_birth":    row.get("date_of_birth") or "",
            "height_cm":        row.get("height_cm") or d["height_cm"],
            "weight_kg":        row.get("weight_kg") or d["weight_kg"],
            "activity_level":   row.get("activity_level") or d["activity_level"],
            "goal":             row.get("goal") or d["goal"],
            "pace":             pace,
            "weekly_change_kg": weekly_change,
            "target_weight_kg": target_weight,
            # alias: the mobile app uses "target_weight"; expose both so every
            # caller resolves the value regardless of which key it reads.
            "target_weight":    target_weight,
            "weeks_to_goal":    weeks_to_goal,
            "meal_preferences": {**_DEFAULTS["meal_preferences"], **prefs},
        })
        return d

    def _sb_save(self, profile: dict) -> None:
        target_weight = profile.get("target_weight_kg") or profile.get("target_weight")
        weeks_to_goal = profile.get("weeks_to_goal")
        weekly_change = profile.get("weekly_change_kg")
        pace          = profile.get("pace")

        # Goal-planning fields are ALSO embedded in meal_preferences (JSONB).
        # The dedicated columns may not exist on older Supabase projects — when
        # PostgREST strips them (see schema-drift loop below), the JSONB copy
        # survives so target weight + timeline are never silently lost.
        prefs = dict(profile.get("meal_preferences", {}) or {})
        prefs["target_weight_kg"] = target_weight
        prefs["weeks_to_goal"]    = weeks_to_goal
        prefs["weekly_change_kg"] = weekly_change
        prefs["pace"]             = pace

        payload = {
            "user_id":          profile["user_id"],
            "name":             profile.get("name"),
            "gender":           profile.get("gender"),
            "date_of_birth":    profile.get("date_of_birth") or None,
            "height_cm":        profile.get("height_cm"),
            "weight_kg":        profile.get("weight_kg"),
            "activity_level":   profile.get("activity_level"),
            "goal":             profile.get("goal"),
            "pace":             pace,
            "weekly_change_kg": weekly_change,
            # the mobile app sends "target_weight"; fall back to it so the value
            # actually persists to the target_weight_kg column.
            "target_weight_kg": target_weight,
            "weeks_to_goal":    weeks_to_goal,
            "meal_preferences": prefs,  # JSONB — always present, holds a copy
            "updated_at":       datetime.now().isoformat(),
        }
        # Schema drift: older Supabase projects may be missing newer columns.
        # Strip any column PostgREST reports as unknown and retry, up to 8 times.
        import re as _re
        for _ in range(8):
            try:
                self._sb().table("profiles").upsert(payload, on_conflict="user_id").execute()
                return
            except Exception as e:
                msg = str(e)
                m = _re.search(r"Could not find the '([^']+)' column", msg)
                if not m:
                    raise
                col = m.group(1)
                if col not in payload or col == "user_id":
                    raise
                payload.pop(col, None)
        raise RuntimeError("Failed to save profile after stripping unknown columns")

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _path(self, user_id: str) -> str:
        return os.path.join(self.base_dir, f"{user_id}.json")

    def _local_load(self, user_id: str) -> dict:
        path = self._path(user_id)
        if not os.path.exists(path):
            d = dict(_DEFAULTS); d["user_id"] = user_id; return d
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in _DEFAULTS.items():
                if k not in data:
                    data[k] = v
            for k, v in _DEFAULTS["meal_preferences"].items():
                data["meal_preferences"].setdefault(k, v)
            # normalize target-weight aliases so every caller resolves the value
            tw = data.get("target_weight") or data.get("target_weight_kg")
            if tw:
                data["target_weight"] = tw
                data["target_weight_kg"] = tw
            return data
        except (json.JSONDecodeError, IOError):
            return dict(_DEFAULTS)

    def _local_save(self, profile: dict) -> None:
        profile["updated_at"] = datetime.now().isoformat()
        with open(self._path(profile["user_id"]), "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, user_id: str) -> dict:
        if self._use_supabase():
            try:
                return self._sb_load(user_id) or {**_DEFAULTS, "user_id": user_id}
            except Exception:
                # RLS / network error — fall back to local JSON silently
                pass
        return self._local_load(user_id)

    def save(self, profile: dict) -> None:
        if self._use_supabase():
            try:
                self._sb_save(profile)
                return
            except Exception:
                pass  # fall through to local save
        self._local_save(profile)
