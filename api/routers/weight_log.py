"""
weight_log — מעקב משקל מסונכרן בענן (Supabase), כדי שלא יימחק בהחלפת מכשיר.

טבלה: weight_log (user_id uuid, date date, kg numeric), ייחודי על (user_id, date).
בסביבת פיתוח ללא Supabase ה-endpoints מחזירים ריק/no-op — האפליקציה שומרת מקומית.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.deps import get_current_user

router = APIRouter()


class WeightEntry(BaseModel):
    date: str   # YYYY-MM-DD
    kg: float


def _sb():
    """Supabase client, or None when not configured (local dev)."""
    try:
        from nutrition_app.db.supabase_client import is_supabase_configured, get_supabase
        return get_supabase() if is_supabase_configured() else None
    except Exception:
        return None


@router.get("/")
def get_weight_log(user=Depends(get_current_user)):
    """כל שקילות המשתמש, מהישן לחדש."""
    sb = _sb()
    if not sb:
        return {"log": []}
    try:
        res = (sb.table("weight_log")
               .select("date, kg")
               .eq("user_id", user["id"])
               .order("date")
               .execute())
        log = [{"date": r["date"], "kg": float(r["kg"])} for r in (res.data or [])]
        return {"log": log}
    except Exception:
        return {"log": []}


@router.post("/")
def add_weight(body: WeightEntry, user=Depends(get_current_user)):
    """הוספה/עדכון שקילה לתאריך (upsert על user_id+date)."""
    if not body.kg or body.kg < 30 or body.kg > 300:
        return {"ok": False, "error": "invalid_weight"}
    sb = _sb()
    if not sb:
        return {"ok": True, "synced": False}
    try:
        sb.table("weight_log").upsert(
            {"user_id": user["id"], "date": body.date, "kg": body.kg},
            on_conflict="user_id,date",
        ).execute()
        return {"ok": True, "synced": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}
