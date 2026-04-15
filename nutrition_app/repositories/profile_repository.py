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
    Stores user profile (incl. meal preferences) in:
      storage_agents/profiles/{user_id}.json
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "storage_agents", "profiles",
            )
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        return os.path.join(self.base_dir, f"{user_id}.json")

    def load(self, user_id: str) -> dict:
        """Load profile; returns defaults if file not found."""
        path = self._path(user_id)
        if not os.path.exists(path):
            d = dict(_DEFAULTS)
            d["user_id"] = user_id
            return d
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # backfill any missing keys from defaults
            for k, v in _DEFAULTS.items():
                if k not in data:
                    data[k] = v
            if "meal_preferences" in _DEFAULTS:
                for k, v in _DEFAULTS["meal_preferences"].items():
                    data["meal_preferences"].setdefault(k, v)
            return data
        except (json.JSONDecodeError, IOError):
            return dict(_DEFAULTS)

    def save(self, profile: dict) -> None:
        """Save profile dict to disk."""
        profile["updated_at"] = datetime.now().isoformat()
        with open(self._path(profile["user_id"]), "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
