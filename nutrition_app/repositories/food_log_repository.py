#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""food_log_repository.py — יומן אכילה יומי למשתמש

Supports two backends:
  • Supabase (cloud)  — when SUPABASE_URL / SUPABASE_ANON_KEY are in secrets
  • Local JSON files  — fallback for local development
"""

import os
import json
import uuid
from datetime import date as date_cls
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class FoodLogEntry:
    food_id: str
    food_name: str
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    meal_type: str
    timestamp: str
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class FoodLogRepository:
    """
    Stores food eaten per user per day.

    Auto-selects backend:
      - Supabase when credentials present in st.secrets
      - Local JSON (storage_agents/food_log/{user_id}.json) otherwise
    """

    def __init__(self, base_dir: Optional[str] = None):
        # Local JSON fallback
        if base_dir is None:
            self._base_dir = None
            self._use_per_user_dirs = True
        else:
            self._base_dir = base_dir
            self._use_per_user_dirs = False
            os.makedirs(self._base_dir, exist_ok=True)

    # ── Backend selector ──────────────────────────────────────────────────────

    def _use_supabase(self, user_id: str = "") -> bool:
        import re
        if not re.match(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            (user_id or "").lower()
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

    def _sb_get_log(self, user_id: str, day: date_cls) -> List[FoodLogEntry]:
        rows = (
            self._sb().table("food_log")
            .select("*")
            .eq("user_id", user_id)
            .eq("date", day.isoformat())
            .execute()
        ).data or []
        return [_row_to_entry(r) for r in rows]

    def _sb_add_entry(self, user_id: str, day: date_cls, entry: FoodLogEntry):
        self._sb().table("food_log").insert({
            "user_id":   user_id,
            "date":      day.isoformat(),
            "food_id":   entry.food_id,
            "food_name": entry.food_name,
            "grams":     entry.grams,
            "calories":  entry.calories,
            "protein":   entry.protein,
            "carbs":     entry.carbs,
            "fat":       entry.fat,
            "meal_type": entry.meal_type,
            "timestamp": entry.timestamp,
            "entry_id":  entry.entry_id,
        }).execute()

    def _sb_remove_entry(self, user_id: str, day: date_cls, entry_id: str):
        self._sb().table("food_log").delete().eq("entry_id", entry_id).execute()

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _path(self, user_id: str) -> str:
        if self._use_per_user_dirs:
            from nutrition_app.storage_paths import user_food_log_file
            return str(user_food_log_file(user_id))
        return os.path.join(self._base_dir, f"{user_id}.json")

    def _load(self, user_id: str) -> dict:
        path = self._path(user_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, user_id: str, data: dict):
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_log(self, user_id: str, day: date_cls) -> List[FoodLogEntry]:
        if self._use_supabase(user_id):
            return self._sb_get_log(user_id, day)
        data = self._load(user_id)
        return [FoodLogEntry(**e) for e in data.get(day.isoformat(), [])]

    def add_entry(self, user_id: str, day: date_cls, entry: FoodLogEntry):
        if self._use_supabase(user_id):
            self._sb_add_entry(user_id, day, entry)
            return
        data = self._load(user_id)
        data.setdefault(day.isoformat(), []).append(asdict(entry))
        self._save(user_id, data)

    def remove_entry(self, user_id: str, day: date_cls, entry_id: str):
        if self._use_supabase(user_id):
            self._sb_remove_entry(user_id, day, entry_id)
            return
        data = self._load(user_id)
        iso  = day.isoformat()
        data[iso] = [e for e in data.get(iso, []) if e.get("entry_id") != entry_id]
        if not data[iso]:
            data.pop(iso, None)
        self._save(user_id, data)

    def get_totals(self, user_id: str, day: date_cls) -> dict:
        entries = self.get_log(user_id, day)
        return {
            "calories": sum(e.calories for e in entries),
            "protein":  sum(e.protein  for e in entries),
            "carbs":    sum(e.carbs    for e in entries),
            "fat":      sum(e.fat      for e in entries),
            "count":    len(entries),
        }


# ── Helper ────────────────────────────────────────────────────────────────────

def _row_to_entry(row: dict) -> FoodLogEntry:
    return FoodLogEntry(
        food_id   = row.get("food_id", ""),
        food_name = row.get("food_name", ""),
        grams     = float(row.get("grams", 0)),
        calories  = float(row.get("calories", 0)),
        protein   = float(row.get("protein", 0)),
        carbs     = float(row.get("carbs", 0)),
        fat       = float(row.get("fat", 0)),
        meal_type = row.get("meal_type", "lunch"),
        timestamp = row.get("timestamp", ""),
        entry_id  = row.get("entry_id", ""),
    )
