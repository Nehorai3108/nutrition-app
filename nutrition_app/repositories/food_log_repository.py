#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""food_log_repository.py — יומן אכילה יומי למשתמש

Backend priority:
  1. SQLite  (primary — local nutrition.db)
  2. Supabase (optional cloud)
  3. JSON    (legacy fallback)
"""

import os
import json
import uuid
import sqlite3
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
    image_url: Optional[str] = None


def _default_db_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "storage", "nutrition.db",
    )


def _default_json_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "storage_agents", "food_log",
    )


class FoodLogRepository:
    """Stores food eaten per user per day. Primary backend: SQLite."""

    def __init__(self, base_dir: Optional[str] = None, db_path: Optional[str] = None):
        self._db_path  = db_path or _default_db_path()
        self._base_dir = base_dir or _default_json_dir()
        os.makedirs(self._base_dir, exist_ok=True)

    # ── Backend selector ──────────────────────────────────────────────────────

    def _use_sqlite(self) -> bool:
        # Supabase wins when configured (production): it's the persistent store.
        # SQLite is local-dev only — on Render the committed nutrition.db lives on
        # an EPHEMERAL disk that is wiped on every deploy, which silently reset the
        # food log. Never use SQLite when Supabase is available.
        if self._use_supabase():
            return False
        return os.path.exists(self._db_path)

    def _use_supabase(self) -> bool:
        try:
            from nutrition_app.db.supabase_client import is_supabase_configured
            return is_supabase_configured()
        except Exception:
            return False

    def _db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _sb(self):
        from nutrition_app.db.supabase_client import get_supabase
        return get_supabase()

    # ── SQLite backend ────────────────────────────────────────────────────────

    def _ensure_user(self, conn: sqlite3.Connection, user_id: str):
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )

    def _sqlite_get_log(self, user_id: str, day: date_cls) -> List[FoodLogEntry]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM food_log WHERE user_id=? AND date=? ORDER BY rowid",
                (user_id, day.isoformat()),
            ).fetchall()
        return [_row_to_entry(dict(r)) for r in rows]

    def _sqlite_add_entry(self, user_id: str, day: date_cls, entry: FoodLogEntry):
        with self._db() as conn:
            self._ensure_user(conn, user_id)
            conn.execute("""
                INSERT OR REPLACE INTO food_log
                  (entry_id, user_id, date, food_id, food_name, grams,
                   calories, protein, carbs, fat, meal_type, timestamp, image_url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry.entry_id, user_id, day.isoformat(),
                entry.food_id, entry.food_name, entry.grams,
                entry.calories, entry.protein, entry.carbs, entry.fat,
                entry.meal_type, entry.timestamp, entry.image_url,
            ))

    def _sqlite_remove_entry(self, user_id: str, day: date_cls, entry_id: str):
        with self._db() as conn:
            conn.execute(
                "DELETE FROM food_log WHERE user_id=? AND entry_id=?",
                (user_id, entry_id),
            )

    def _sqlite_clear_day(self, user_id: str, day: date_cls):
        with self._db() as conn:
            conn.execute(
                "DELETE FROM food_log WHERE user_id=? AND date=?",
                (user_id, day.isoformat()),
            )

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
            "user_id": user_id, "date": day.isoformat(),
            "food_id": entry.food_id, "food_name": entry.food_name,
            "grams": entry.grams, "calories": entry.calories,
            "protein": entry.protein, "carbs": entry.carbs, "fat": entry.fat,
            "meal_type": entry.meal_type, "timestamp": entry.timestamp,
            "entry_id": entry.entry_id,
        }).execute()

    def _sb_remove_entry(self, user_id: str, day: date_cls, entry_id: str):
        self._sb().table("food_log").delete().eq("entry_id", entry_id).execute()

    # ── Local JSON backend (legacy) ───────────────────────────────────────────

    def _path(self, user_id: str) -> str:
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

    def _save_json(self, user_id: str, data: dict):
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_log(self, user_id: str, day: date_cls) -> List[FoodLogEntry]:
        if self._use_sqlite():
            try:
                return self._sqlite_get_log(user_id, day)
            except Exception:
                pass
        if self._use_supabase():
            try:
                return self._sb_get_log(user_id, day)
            except Exception:
                pass
        data = self._load(user_id)
        return [FoodLogEntry(**e) for e in data.get(day.isoformat(), [])]

    def add_entry(self, user_id: str, day: date_cls, entry: FoodLogEntry):
        if self._use_sqlite():
            try:
                self._sqlite_add_entry(user_id, day, entry)
                return
            except Exception:
                pass
        if self._use_supabase():
            try:
                self._sb_add_entry(user_id, day, entry)
                return
            except Exception:
                pass
        data = self._load(user_id)
        data.setdefault(day.isoformat(), []).append(asdict(entry))
        self._save_json(user_id, data)

    def remove_entry(self, user_id: str, day: date_cls, entry_id: str):
        if self._use_sqlite():
            try:
                self._sqlite_remove_entry(user_id, day, entry_id)
                return
            except Exception:
                pass
        if self._use_supabase():
            try:
                self._sb_remove_entry(user_id, day, entry_id)
                return
            except Exception:
                pass
        data = self._load(user_id)
        iso  = day.isoformat()
        data[iso] = [e for e in data.get(iso, []) if e.get("entry_id") != entry_id]
        if not data[iso]:
            data.pop(iso, None)
        self._save_json(user_id, data)

    def clear_day(self, user_id: str, day: date_cls) -> None:
        if self._use_sqlite():
            try:
                self._sqlite_clear_day(user_id, day)
                return
            except Exception:
                pass
        if self._use_supabase():
            try:
                self._sb().table("food_log").delete()\
                    .eq("user_id", user_id).eq("date", day.isoformat()).execute()
                return
            except Exception:
                pass
        data = self._load(user_id)
        data.pop(day.isoformat(), None)
        self._save_json(user_id, data)

    def get_history(self, user_id: str, start: date_cls, end: date_cls) -> dict:
        """Per-day nutrition totals between start and end (inclusive).

        Returns {iso_date: {calories, protein, carbs, fat, count}} for days
        that have at least one entry.
        """
        if self._use_sqlite():
            try:
                with self._db() as conn:
                    rows = conn.execute(
                        """SELECT date,
                                  SUM(calories) AS calories,
                                  SUM(protein)  AS protein,
                                  SUM(carbs)    AS carbs,
                                  SUM(fat)      AS fat,
                                  COUNT(*)      AS count
                           FROM food_log
                           WHERE user_id=? AND date BETWEEN ? AND ?
                           GROUP BY date""",
                        (user_id, start.isoformat(), end.isoformat()),
                    ).fetchall()
                return {
                    r["date"]: {
                        "calories": round(r["calories"] or 0),
                        "protein":  round(r["protein"] or 0, 1),
                        "carbs":    round(r["carbs"] or 0, 1),
                        "fat":      round(r["fat"] or 0, 1),
                        "count":    r["count"],
                    }
                    for r in rows
                }
            except Exception:
                pass
        # JSON fallback
        data = self._load(user_id)
        out = {}
        for iso, entries in data.items():
            try:
                d = date_cls.fromisoformat(iso)
            except ValueError:
                continue
            if start <= d <= end and entries:
                out[iso] = {
                    "calories": round(sum(e.get("calories", 0) for e in entries)),
                    "protein":  round(sum(e.get("protein", 0) for e in entries), 1),
                    "carbs":    round(sum(e.get("carbs", 0) for e in entries), 1),
                    "fat":      round(sum(e.get("fat", 0) for e in entries), 1),
                    "count":    len(entries),
                }
        return out

    def get_recent_foods(self, user_id: str, limit: int = 12) -> list:
        """Distinct recently-logged foods (newest first) for one-tap re-logging.

        Each item carries the nutrition from its most recent logging plus how
        many times it was logged.
        """
        if self._use_sqlite():
            try:
                with self._db() as conn:
                    rows = conn.execute(
                        """SELECT food_name, food_id, grams, calories, protein, carbs,
                                  fat, image_url, meal_type,
                                  MAX(timestamp) AS last, COUNT(*) AS cnt
                           FROM food_log
                           WHERE user_id=? AND food_name IS NOT NULL AND food_name != ''
                           GROUP BY food_name
                           ORDER BY last DESC
                           LIMIT ?""",
                        (user_id, limit),
                    ).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                pass
        # JSON fallback: aggregate across all days
        data = self._load(user_id)
        by_name = {}
        for iso in sorted(data.keys()):
            for e in data[iso]:
                name = e.get("food_name")
                if not name:
                    continue
                prev = by_name.get(name)
                cnt = (prev["cnt"] + 1) if prev else 1
                by_name[name] = {**e, "last": e.get("timestamp", iso), "cnt": cnt}
        items = sorted(by_name.values(), key=lambda x: x.get("last", ""), reverse=True)
        return items[:limit]

    def get_totals(self, user_id: str, day: date_cls) -> dict:
        entries = self.get_log(user_id, day)
        return {
            "calories": sum(e.calories or 0 for e in entries),
            "protein":  sum(e.protein  or 0 for e in entries),
            "carbs":    sum(e.carbs    or 0 for e in entries),
            "fat":      sum(e.fat      or 0 for e in entries),
            "count":    len(entries),
        }

    def get_totals_range(self, user_id: str, start: date_cls, end: date_cls) -> list[dict]:
        """Return daily totals for each day in [start, end] inclusive."""
        from datetime import timedelta
        results = []
        d = start
        while d <= end:
            t = self.get_totals(user_id, d)
            results.append({"date": d.isoformat(), **t})
            d += timedelta(days=1)
        return results


# ── Helper ────────────────────────────────────────────────────────────────────

def _row_to_entry(row: dict) -> FoodLogEntry:
    return FoodLogEntry(
        food_id   = row.get("food_id", ""),
        food_name = row.get("food_name", ""),
        grams     = float(row.get("grams") or 0),
        calories  = float(row.get("calories") or 0),
        protein   = float(row.get("protein") or 0),
        carbs     = float(row.get("carbs") or 0),
        fat       = float(row.get("fat") or 0),
        meal_type = row.get("meal_type", "lunch"),
        timestamp = row.get("timestamp", ""),
        entry_id  = row.get("entry_id", str(uuid.uuid4())),
        image_url = row.get("image_url"),
    )
