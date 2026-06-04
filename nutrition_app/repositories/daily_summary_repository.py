#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_summary_repository.py — שמירה וטעינה של סיכומים יומיים

Backends:
  • Supabase (cloud)  — `daily_summaries` table, unique on (user_id, date).
                        Only used when SUPABASE_URL / SUPABASE_ANON_KEY are in
                        secrets AND user_id is a real UUID (per-user isolation).
  • Local JSON files  — fallback for local development.
                        storage_agents/daily_summaries/{user_id}.json
"""

import os
import json
import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from nutrition_app.models.daily_summary import DailySummary

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)


class DailySummaryRepository:
    """Per-user daily summaries with dual backend (Supabase or local JSON)."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = None
            self._use_per_user_dirs = True
        else:
            self.base_dir = base_dir
            self._use_per_user_dirs = False
            os.makedirs(self.base_dir, exist_ok=True)

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

    def _schema_mismatch(self, e: Exception) -> bool:
        """Older Supabase projects may have a different daily_summaries shape
        (no summary_json column). Detect that error so callers degrade
        gracefully instead of crashing the dashboard."""
        s = str(e)
        return (
            "summary_json" in s
            or "Could not find the" in s
            or "does not exist" in s and "column" in s.lower()
        )

    def _sb_upsert(self, summary: DailySummary) -> None:
        try:
            self._sb().table("daily_summaries").upsert({
                "user_id":      summary.user_id,
                "date":         summary.date,
                "summary_json": summary.to_dict(),
                "updated_at":   datetime.now().isoformat(),
            }, on_conflict="user_id,date").execute()
        except Exception as e:
            if self._schema_mismatch(e):
                # Fall back to local JSON when the cloud schema is incompatible.
                all_data = self._load_all(summary.user_id)
                all_data[summary.date] = summary.to_dict()
                self._save_all(summary.user_id, all_data)
                return
            raise

    def _sb_get(self, user_id: str, date_str: str) -> Optional[DailySummary]:
        try:
            rows = (
                self._sb().table("daily_summaries")
                .select("summary_json")
                .eq("user_id", user_id)
                .eq("date", date_str)
                .limit(1)
                .execute()
            ).data
        except Exception as e:
            if self._schema_mismatch(e):
                # Schema doesn't have summary_json yet — return None (no summary).
                return None
            raise
        if not rows:
            return None
        blob = rows[0].get("summary_json")
        if isinstance(blob, str):
            blob = json.loads(blob)
        return DailySummary.from_dict(blob) if blob else None

    def _sb_get_range(self, user_id: str, start_iso: str, end_iso: str) -> List[DailySummary]:
        try:
            rows = (
                self._sb().table("daily_summaries")
                .select("summary_json")
                .eq("user_id", user_id)
                .gte("date", start_iso)
                .lte("date", end_iso)
                .order("date", desc=True)
                .execute()
            ).data or []
        except Exception as e:
            if self._schema_mismatch(e):
                return []
            raise
        results = []
        for row in rows:
            blob = row.get("summary_json")
            if isinstance(blob, str):
                blob = json.loads(blob)
            if blob:
                results.append(DailySummary.from_dict(blob))
        return results

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _path(self, user_id: str) -> str:
        if self._use_per_user_dirs:
            from nutrition_app.storage_paths import user_daily_summaries_file
            return str(user_daily_summaries_file(user_id))
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
        if self._use_supabase(summary.user_id):
            try:
                self._sb_upsert(summary)
                return
            except Exception:
                pass  # fall through to local save
        all_data = self._load_all(summary.user_id)
        all_data[summary.date] = summary.to_dict()
        self._save_all(summary.user_id, all_data)

    def get(self, user_id: str, date_obj) -> Optional[DailySummary]:
        """Load summary for a specific date. Returns None if not found."""
        date_str = date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj)
        if self._use_supabase(user_id):
            try:
                return self._sb_get(user_id, date_str)
            except Exception:
                pass  # fall through to local load
        data = self._load_all(user_id).get(date_str)
        return DailySummary.from_dict(data) if data else None

    def get_for_period(self, user_id: str, start: date, end: date) -> List[DailySummary]:
        """Return all summaries between start and end (inclusive), newest first."""
        if self._use_supabase(user_id):
            try:
                return self._sb_get_range(user_id, start.isoformat(), end.isoformat())
            except Exception:
                pass  # fall through to local load
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
