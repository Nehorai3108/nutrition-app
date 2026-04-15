"""
Food Cache — SQLite-backed cache for nutrition lookups.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional

_DB_PATH = os.path.join(os.path.dirname(__file__), "food_cache.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
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
    conn.commit()


def get_cached(query: str) -> Optional[dict]:
    """Return cached result for query (case-insensitive) or None."""
    with _get_conn() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT * FROM food_cache WHERE LOWER(name_query) = LOWER(?) ORDER BY created_at DESC LIMIT 1",
            (query,),
        ).fetchone()
    if row is None:
        return None
    return {
        "found":      True,
        "query":      row["name_query"],
        "food_name":  row["food_name"],
        "fdc_id":     row["fdc_id"],
        "calories":   row["calories"],
        "protein":    row["protein"],
        "carbs":      row["carbs"],
        "fat":        row["fat"],
        "fiber":      row["fiber"],
        "source":     row["source"],
        "from_cache": True,
        "error":      None,
    }


def save_to_cache(query: str, result: dict, source: str) -> None:
    """Persist a successful lookup result into the cache."""
    with _get_conn() as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO food_cache
                (name_query, fdc_id, food_name, calories, protein, carbs, fat, fiber, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query,
                result.get("fdc_id"),
                result.get("food_name"),
                result.get("calories"),
                result.get("protein"),
                result.get("carbs"),
                result.get("fat"),
                result.get("fiber"),
                source,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()


def cache_count() -> int:
    """Return total number of cached entries."""
    with _get_conn() as conn:
        _ensure_table(conn)
        return conn.execute("SELECT COUNT(*) FROM food_cache").fetchone()[0]
