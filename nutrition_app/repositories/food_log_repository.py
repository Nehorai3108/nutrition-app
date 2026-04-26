#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""food_log_repository.py — יומן אכילה יומי למשתמש"""

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
    """Stores actual food eaten per user per day.

    Storage: storage_agents/food_log/{user_id}.json
    Format:  { "YYYY-MM-DD": [ {entry}, ... ], ... }
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "storage_agents",
                "food_log",
            )
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        return os.path.join(self.base_dir, f"{user_id}.json")

    def _load(self, user_id: str) -> dict:
        path = self._path(user_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, user_id: str, data: dict) -> None:
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_log(self, user_id: str, day: date_cls) -> List[FoodLogEntry]:
        data = self._load(user_id)
        entries = data.get(day.isoformat(), [])
        return [FoodLogEntry(**e) for e in entries]

    def add_entry(self, user_id: str, day: date_cls, entry: FoodLogEntry) -> None:
        data = self._load(user_id)
        iso = day.isoformat()
        data.setdefault(iso, []).append(asdict(entry))
        self._save(user_id, data)

    def remove_entry(self, user_id: str, day: date_cls, entry_id: str) -> None:
        data = self._load(user_id)
        iso = day.isoformat()
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
