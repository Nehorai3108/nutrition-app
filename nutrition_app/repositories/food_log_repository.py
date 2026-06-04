#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""food_log_repository.py — יומן אכילה יומי למשתמש

Backend priority:
  1. SQLite  (primary — local nutrition.db)
  2. Supabase (optional cloud — only for real UUID user_ids, per-user isolation)
  3. JSON    (legacy fallback)
"""

import os
import json
import uuid
import re
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


_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)


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
        return os.path.exists(self._db_path)

    def _use_supabase(self, user_id: str = "") -> bool:
        # Per-user isolation: only route to Supabase for real UUID user_ids.
        if not _UUID_RE.match((user_id or "").lower()):
            return False
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
                   calories, protein, carbs, fat, meal_type, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry.entry_id, user_id, day.isoformat(),
                entry.food_id, entry.food_name, entry.grams,
                entry.calories, entry.protein, entry.carbs, entry.fat,
                entry.meal_type, entry.timestamp,
            ))

    def _sqlite_remove_entry(self, user_id: str, day: date_cls, entry_id: str):
        with self._db() as conn:
            conn.execute(
                "DELETE FROM food_log WHERE user_id=? AND date=? AND entry_id=?",
                (user_id, day.isoformat(), entry_id),
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
        if self._use_supabase(user_id):
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
        if self._use_supabase(user_id):
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
        if self._use_supabase(user_id):
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
        if self._use_supabase(user_id):
            try:
                self._sb().table("food_log").delete()\
                    .eq("user_id", user_id).eq("date", day.isoformat()).execute()
                return
            except Exception:
                pass
        data = self._load(user_id)
        data.pop(day.isoformat(), None)
        self._save_json(user_id, data)

    def get_totals(self, user_id: str, day: date_cls) -> dict:
        entries = self.get_log(user_id, day)
        return {
            "calories": sum(e.calories or 0 for e in entries),
            "protein":  sum(e.protein  or 0 for e in entries),
            "carbs":    sum(e.carbs    or 0 for e in entries),
            "fat":      sum(e.fat      or 0 for e in entries),
            "count":    len(entries),
        }


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
    )
