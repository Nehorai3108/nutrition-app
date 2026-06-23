"""
Public waitlist signup — collects emails from the landing page (no auth).

Stores to the Supabase `waitlist` table. Anonymous INSERT is allowed by RLS
(see db/migrations/waitlist.sql); nobody can read the list via the API.
Fails gracefully so a storage hiccup never shows the visitor an error.
"""
import os
import re
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class WaitlistEntry(BaseModel):
    email: str
    source: str | None = None
    goal: str | None = None


def _use_sb() -> bool:
    return bool(os.environ.get("SUPABASE_URL"))


def _sb():
    from nutrition_app.db.supabase_client import get_supabase
    return get_supabase()


@router.post("/")
def join_waitlist(entry: WaitlistEntry):
    email = (entry.email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        return {"ok": False, "error": "invalid_email"}

    if not _use_sb():
        # Dev / no DB configured — accept so the page UX works.
        return {"ok": True, "stored": False}

    try:
        from datetime import datetime
        _sb().table("waitlist").upsert(
            {
                "email": email,
                "source": (entry.source or "landing")[:60],
                "goal": (entry.goal or None),
                "created_at": datetime.utcnow().isoformat(),
            },
            on_conflict="email",
        ).execute()
        return {"ok": True, "stored": True}
    except Exception:
        # Never surface a storage error to the visitor.
        return {"ok": True, "stored": False}
