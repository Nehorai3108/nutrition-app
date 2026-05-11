"""
Unknown Queue — tracks food queries that couldn't be resolved by any source.
"""

import os
import sqlite3
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(__file__), "food_cache.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
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


def add_to_queue(query: str) -> None:
    """Add a query to the unknown queue, or increment attempts if already present."""
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        _ensure_table(conn)
        existing = conn.execute(
            "SELECT id, attempts FROM unknown_foods WHERE LOWER(query) = LOWER(?)", (query,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE unknown_foods SET attempts = ?, last_attempt = ?, status = 'pending' WHERE id = ?",
                (existing["attempts"] + 1, now, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO unknown_foods (query, attempts, last_attempt, status) VALUES (?, 1, ?, 'pending')",
                (query, now),
            )
        conn.commit()


def get_pending_queue() -> list:
    """Return all pending unknown food queries."""
    with _get_conn() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT query, attempts, last_attempt, status FROM unknown_foods WHERE status = 'pending'"
        ).fetchall()
    return [dict(row) for row in rows]


def update_status(query: str, status: str) -> None:
    """Update the status of an unknown queue entry ('resolved' | 'failed' | 'pending')."""
    with _get_conn() as conn:
        _ensure_table(conn)
        conn.execute(
            "UPDATE unknown_foods SET status = ? WHERE LOWER(query) = LOWER(?)",
            (status, query),
        )
        conn.commit()


def queue_count() -> int:
    """Return total number of entries in the unknown queue."""
    with _get_conn() as conn:
        _ensure_table(conn)
        return conn.execute("SELECT COUNT(*) FROM unknown_foods").fetchone()[0]
