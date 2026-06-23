"""
Usage metering + free-tier rate limiting.

Tracks per-user daily counts of the expensive AI features (food-photo scans,
chat messages) and enforces free-tier caps so a flood of free users can't run
up the Groq bill. Paid ("pro") users are unlimited.

Storage: Supabase table `usage_daily` in production; local SQLite for dev.
Design principle: FAIL OPEN — if the store is unreachable or the table is
missing, allow the action (never block a user because metering broke). Run
db/migrations/usage_daily.sql once in Supabase to activate limiting in prod.
"""
import os
import sqlite3
from contextlib import closing
from datetime import date

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, "storage", "nutrition.db")

# ── Free-tier daily caps (per feature). Pro = unlimited. ─────────────────
FREE_LIMITS = {
    "camera": 3,    # food-photo scans / day (the most expensive feature)
    "chat":  30,    # chat messages / day (cheap, generous cap)
}

# Owner / admin emails — always unlimited (never rate-limited). Comma-separated
# in OWNER_EMAILS env; defaults to the project owner.
OWNER_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("OWNER_EMAILS", "dviryona8@gmail.com").split(",")
    if e.strip()
}


def is_owner(email: str | None) -> bool:
    return bool(email) and email.strip().lower() in OWNER_EMAILS

_CREATE = """
CREATE TABLE IF NOT EXISTS usage_daily (
    user_id  TEXT NOT NULL,
    day      TEXT NOT NULL,
    feature  TEXT NOT NULL,
    count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day, feature)
)
"""


def _use_sb() -> bool:
    return bool(os.environ.get("SUPABASE_URL"))


def _sb():
    from nutrition_app.db.supabase_client import get_supabase
    return get_supabase()


def _conn():
    # autocommit (isolation_level=None): every statement commits immediately, so
    # there are no lingering transactions/snapshots — a fresh reader always sees
    # the latest write (the per-call connection model otherwise hit a WAL
    # visibility issue where a committed INSERT read back as 0).
    conn = sqlite3.connect(_DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE)
    return conn


def _today() -> str:
    try:
        from api._tz import today_il
        return today_il().isoformat()
    except Exception:
        return date.today().isoformat()


# ── tier ──────────────────────────────────────────────────────────────────
def get_tier(user_id: str) -> str:
    """'free' or 'pro'. Stored in the profile (meal_preferences JSONB, schema-proof)."""
    try:
        from nutrition_app.repositories.profile_repository import ProfileRepository
        p = ProfileRepository().load(user_id)
        tier = (p.get("tier")
                or (p.get("meal_preferences") or {}).get("tier")
                or "free")
        return "pro" if str(tier).lower() == "pro" else "free"
    except Exception:
        return "free"


# ── counts ─────────────────────────────────────────────────────────────────
def get_count(user_id: str, feature: str, day: str | None = None) -> int:
    day = day or _today()
    try:
        if _use_sb():
            rows = (_sb().table("usage_daily").select("count")
                    .eq("user_id", user_id).eq("day", day).eq("feature", feature)
                    .limit(1).execute()).data
            return int(rows[0]["count"]) if rows else 0
        with closing(_conn()) as c:
            row = c.execute(
                "SELECT count FROM usage_daily WHERE user_id=? AND day=? AND feature=?",
                (user_id, day, feature),
            ).fetchone()
            return int(row["count"]) if row else 0
    except Exception:
        return 0  # fail open


def _increment(user_id: str, feature: str, day: str | None = None) -> None:
    day = day or _today()
    try:
        if _use_sb():
            current = get_count(user_id, feature, day)
            (_sb().table("usage_daily").upsert(
                {"user_id": user_id, "day": day, "feature": feature, "count": current + 1},
                on_conflict="user_id,day,feature",
            ).execute())
            return
        with closing(_conn()) as c:
            c.execute(
                """INSERT INTO usage_daily (user_id, day, feature, count)
                   VALUES (?, ?, ?, 1)
                   ON CONFLICT(user_id, day, feature)
                   DO UPDATE SET count = count + 1""",
                (user_id, day, feature),
            )
            c.commit()
    except Exception:
        pass  # fail open — never block on a metering error


# ── public gate ─────────────────────────────────────────────────────────────
def check(user_id: str, feature: str) -> dict:
    """Is this feature allowed right now? Returns status without consuming."""
    limit = FREE_LIMITS.get(feature)
    if get_tier(user_id) == "pro" or limit is None:
        return {"allowed": True, "tier": "pro" if limit is None else get_tier(user_id),
                "used": 0, "limit": None, "remaining": None}
    used = get_count(user_id, feature)
    return {
        "allowed": used < limit,
        "tier": "free",
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }


def check_and_consume(user_id: str, feature: str) -> dict:
    """Check the limit; if allowed, count one use. Returns the same shape as check()."""
    status = check(user_id, feature)
    if status["allowed"]:
        _increment(user_id, feature)
        if status["limit"] is not None:
            status["used"] += 1
            status["remaining"] = max(0, status["limit"] - status["used"])
    return status
