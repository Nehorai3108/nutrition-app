#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_summary_repository.py — שמירה וטעינה של סיכומים יומיים
"""

import os
import json
from datetime import date, timedelta
from typing import Dict, List, Optional

from nutrition_app.models.daily_summary import DailySummary


class DailySummaryRepository:
    """
    Stores per-user daily summaries in:
      storage_agents/daily_summaries/{user_id}.json

    Format: { "YYYY-MM-DD": { ...DailySummary fields... }, ... }
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "storage_agents", "daily_summaries",
            )
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        return os.path.join(self.base_dir, f"{user_id}.json")

    def _load_all(self, user_id: str) -> Dict[str, dict]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_all(self, user_id: str, data: Dict[str, dict]) -> None:
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def save(self, summary: DailySummary) -> None:
        """Save or overwrite the summary for the given date."""
        all_data = self._load_all(summary.user_id)
        all_data[summary.date] = summary.to_dict()
        self._save_all(summary.user_id, all_data)

    def get(self, user_id: str, date_obj) -> Optional[DailySummary]:
        """Load summary for a specific date. Returns None if not found."""
        date_str = date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj)
        data = self._load_all(user_id).get(date_str)
        return DailySummary.from_dict(data) if data else None

    def get_for_period(self, user_id: str, start: date, end: date) -> List[DailySummary]:
        """Return all summaries between start and end (inclusive), newest first."""
        all_data = self._load_all(user_id)
        results = []
        current = start
        while current <= end:
            key = current.isoformat()
            if key in all_data:
                results.append(DailySummary.from_dict(all_data[key]))
            current += timedelta(days=1)
        results.sort(key=lambda s: s.date, reverse=True)
        return results

    def get_last_n_days(self, user_id: str, n: int = 7) -> List[DailySummary]:
        """Convenience: return summaries for the last n days."""
        today = date.today()
        return self.get_for_period(user_id, today - timedelta(days=n - 1), today)
