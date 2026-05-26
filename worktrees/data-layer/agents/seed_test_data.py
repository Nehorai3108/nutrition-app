"""
seed_test_data.py — Seeds test data into food_cache.db for scheduler tests.

Inserts:
  - 10 known foods directly into food_cache (simulating resolved lookups)
  - 5 unknown foods into unknown_foods with status='pending'
"""

import os
import sys
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

_DB_PATH = os.path.join(os.path.dirname(__file__), "food_cache.db")

_KNOWN_FOODS = [
    ("chicken breast",  "Chicken Breast",     165.0, 31.0, 0.0,  3.6,  0.0),
    ("egg",             "Whole Egg",           155.0, 13.0, 1.1,  11.0, 0.0),
    ("brown rice",      "Brown Rice cooked",   112.0,  2.6, 23.5,  0.9,  1.8),
    ("banana",          "Banana",               89.0,  1.1, 23.0,  0.3,  2.6),
    ("olive oil",       "Olive Oil",           884.0,  0.0,  0.0, 100.0, 0.0),
    ("broccoli",        "Broccoli",             34.0,  2.8,  7.0,  0.4,  2.6),
    ("greek yogurt",    "Greek Yogurt plain",   59.0, 10.0,  3.6,  0.4,  0.0),
    ("almonds",         "Almonds",             579.0, 21.0, 22.0, 50.0,  12.5),
    ("oats",            "Rolled Oats",         389.0, 17.0, 66.0,  7.0,  10.6),
    ("salmon",          "Atlantic Salmon",     208.0, 20.0,  0.0, 13.0,  0.0),
]

_UNKNOWN_FOODS = [
    "sfenj moroccan",
    "dragon fruit smoothie bowl",
    "quinoa energy cake",
    "freekeh pilaf",
    "iced matcha oat latte",
]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name_query  TEXT NOT NULL,
            fdc_id      INTEGER,
            food_name   TEXT,
            calories    REAL,
            protein     REAL,
            carbs       REAL,
            fat         REAL,
            fiber       REAL,
            source      TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name_query ON food_cache(name_query)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS unknown_foods (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            query        TEXT NOT NULL UNIQUE,
            attempts     INTEGER NOT NULL DEFAULT 1,
            last_attempt TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.commit()


def seed() -> None:
    now = datetime.utcnow().isoformat()

    with _get_conn() as conn:
        _ensure_tables(conn)

        # Insert known foods into cache (skip if already present)
        inserted_known = 0
        for query, food_name, cal, pro, carb, fat, fiber in _KNOWN_FOODS:
            existing = conn.execute(
                "SELECT id FROM food_cache WHERE LOWER(name_query) = LOWER(?)", (query,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO food_cache "
                    "(name_query, food_name, calories, protein, carbs, fat, fiber, source, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'seed', ?)",
                    (query, food_name, cal, pro, carb, fat, fiber, now),
                )
                inserted_known += 1

        # Insert unknown foods into queue (skip if already present)
        inserted_unknown = 0
        for query in _UNKNOWN_FOODS:
            existing = conn.execute(
                "SELECT id FROM unknown_foods WHERE LOWER(query) = LOWER(?)", (query,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO unknown_foods (query, attempts, last_attempt, status) "
                    "VALUES (?, 1, ?, 'pending')",
                    (query, now),
                )
                inserted_unknown += 1

        conn.commit()

    print(f"[seed] Inserted {inserted_known} known food(s) into food_cache")
    print(f"[seed] Inserted {inserted_unknown} unknown food(s) into unknown_foods queue")
    print(f"[seed] Skipped duplicates (already present)")


if __name__ == "__main__":
    seed()
