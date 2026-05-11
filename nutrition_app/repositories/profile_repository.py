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
    "user_id": "ui_user_001",
    "name": "ישראל ישראלי",
    "gender": "male",
    "date_of_birth": "1990-05-15",
    "height_cm": 178.0,
    "weight_kg": 82.0,
    "activity_level": "moderately_active",
    "goal": "lose_weight",
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
            # base_dir is kept for backward-compat; new default uses per-user dirs
            self.base_dir = None
            self._use_per_user_dirs = True
        else:
            self.base_dir = base_dir
            self._use_per_user_dirs = False
            os.makedirs(self.base_dir, exist_ok=True)

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

    def _sb_load(self, user_id: str) -> Optional[dict]:
        rows = (
            self._sb().table("profiles")
            .select("*").eq("user_id", user_id).limit(1).execute()
        ).data
        if not rows:
            return None
        row = rows[0]
        # Rebuild nested meal_preferences from flat columns
        prefs = json.loads(row.get("meal_preferences") or "{}")
        d = dict(_DEFAULTS)
        d.update({
            "user_id":        user_id,
            "name":           row.get("name") or d["name"],
            "gender":         row.get("gender") or d["gender"],
            "height_cm":      row.get("height_cm") or d["height_cm"],
            "weight_kg":      row.get("weight_kg") or d["weight_kg"],
            "activity_level": row.get("activity_level") or d["activity_level"],
            "goal":           row.get("goal") or d["goal"],
            "meal_preferences": {**_DEFAULTS["meal_preferences"], **prefs},
        })
        return d

    def _sb_save(self, profile: dict) -> None:
        prefs_json = json.dumps(profile.get("meal_preferences", {}), ensure_ascii=False)
        payload = {
            "user_id":          profile["user_id"],
            "name":             profile.get("name"),
            "gender":           profile.get("gender"),
            "height_cm":        profile.get("height_cm"),
            "weight_kg":        profile.get("weight_kg"),
            "activity_level":   profile.get("activity_level"),
            "goal":             profile.get("goal"),
            "meal_preferences": prefs_json,
            "updated_at":       datetime.now().isoformat(),
        }
        self._sb().table("profiles").upsert(payload, on_conflict="user_id").execute()

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _path(self, user_id: str) -> str:
        if self._use_per_user_dirs:
            from nutrition_app.storage_paths import user_profile_file
            return str(user_profile_file(user_id))
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
            return self._sb_load(user_id) or {**_DEFAULTS, "user_id": user_id}
        return se