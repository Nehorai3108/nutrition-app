"""
System Reporter — daily statistics from the food cache and unknown queue.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

_DB_PATH = os.path.join(os.path.dirname(__file__), "food_cache.db")
_LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


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


def generate_daily_report() -> dict:
    """
    Generate a daily statistics report.

    Returns:
        cache_size     — unique known foods in cache
        queue_size     — unresolved foods (pending + failed)
        coverage_rate  — cache_size / (cache_size + queue_size) * 100
        resolved_today — items resolved today (last_attempt date == today, status='resolved')
        top_failed     — top 5 foods by attempt count with status='failed'
        trend          — coverage_rate delta vs yesterday (% points), None on first run
    """
    today_str = datetime.utcnow().date().isoformat()

    with _get_conn() as conn:
        _ensure_tables(conn)

        # Unique known queries in cache
        cache_size: int = conn.execute(
            "SELECT COUNT(DISTINCT LOWER(name_query)) FROM food_cache"
        ).fetchone()[0]

        # Unresolved: pending + failed
        queue_size: int = conn.execute(
            "SELECT COUNT(*) FROM unknown_foods WHERE status IN ('pending', 'failed')"
        ).fetchone()[0]

        # Resolved today
        resolved_today: int = conn.execute(
            "SELECT COUNT(*) FROM unknown_foods "
            "WHERE status = 'resolved' AND last_attempt LIKE ?",
            (f"{today_str}%",),
        ).fetchone()[0]

        # Top 5 failed foods by attempt count
        top_failed_rows = conn.execute(
            "SELECT query, attempts FROM unknown_foods "
            "WHERE status = 'failed' ORDER BY attempts DESC LIMIT 5"
        ).fetchall()
        top_failed = [
            {"query": r["query"], "attempts": r["attempts"]}
            for r in top_failed_rows
        ]

    # Coverage rate
    total = cache_size + queue_size
    coverage_rate = round(cache_size / total * 100, 1) if total > 0 else 100.0

    # Trend vs yesterday's log
    trend: Optional[float] = None
    yesterday_str = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
    yesterday_log = os.path.join(_LOGS_DIR, f"daily_{yesterday_str}.json")
    if os.path.exists(yesterday_log):
        with open(yesterday_log, encoding="utf-8") as f:
            yesterday_data = json.load(f)
        yesterday_coverage = (
            yesterday_data.get("report", {}).get("coverage_rate", coverage_rate)
        )
        trend = round(coverage_rate - yesterday_coverage, 1)

    return {
        "date": today_str,
        "cache_size": cache_size,
        "queue_size": queue_size,
        "coverage_rate": coverage_rate,
        "resolved_today": resolved_today,
        "top_failed": top_failed,
        "trend": trend,
    }
