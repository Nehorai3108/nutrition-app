from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date
from api.deps import get_current_user
from api._tz import now_il_iso, today_il
import sys, os, uuid, sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "storage", "nutrition.db")


def _use_sb() -> bool:
    """בענן (Supabase מוגדר) — שומרים בענן כדי שהנתונים יישמרו לאורך זמן.
    בלי Supabase (פיתוח מקומי) — נשארים על SQLite."""
    return bool(os.environ.get("SUPABASE_URL"))


def _sb():
    from nutrition_app.db.supabase_client import get_supabase
    return get_supabase()


def _conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class AddWorkout(BaseModel):
    workout_type: str
    intensity: str
    duration_minutes: float
    calories_burned: float
    distance_km: Optional[float] = None
    mode: str = "type"
    date: Optional[str] = None


@router.post("/")
def add_workout(body: AddWorkout, user=Depends(get_current_user)):
    d = body.date or today_il().isoformat()
    row = {
        "entry_id": uuid.uuid4().hex, "user_id": user["id"], "date": d,
        "mode": body.mode, "workout_type": body.workout_type,
        "intensity": body.intensity, "duration_minutes": body.duration_minutes,
        "distance_km": body.distance_km, "calories_burned": body.calories_burned,
        "timestamp": now_il_iso(),
    }
    if _use_sb():
        _sb().table("workout_log").insert(row).execute()
    else:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO workout_log
                     (entry_id, user_id, date, mode, workout_type, intensity,
                      duration_minutes, distance_km, calories_burned, timestamp)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                tuple(row[k] for k in ("entry_id", "user_id", "date", "mode",
                      "workout_type", "intensity", "duration_minutes",
                      "distance_km", "calories_burned", "timestamp")),
            )
            conn.commit()
    return {"ok": True}


def _fetch_workouts(user_id: str, date_str: str) -> list:
    if _use_sb():
        return (_sb().table("workout_log").select("*")
                .eq("user_id", user_id).eq("date", date_str).execute()).data or []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workout_log WHERE user_id=? AND date=? ORDER BY rowid",
            (user_id, date_str),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{date_str}")
def get_workouts(date_str: str, user=Depends(get_current_user)):
    try:
        date.fromisoformat(date_str)
    except ValueError:
        date_str = today_il().isoformat()
    return {"workouts": _fetch_workouts(user["id"], date_str)}


@router.get("/{date_str}/summary")
def get_workout_summary(date_str: str, user=Depends(get_current_user)):
    try:
        date.fromisoformat(date_str)
    except ValueError:
        date_str = today_il().isoformat()
    workouts = _fetch_workouts(user["id"], date_str)
    burned = sum(w.get("calories_burned") or 0 for w in workouts)
    minutes = sum(w.get("duration_minutes") or 0 for w in workouts)
    return {
        "calories_burned": round(burned),
        "minutes": round(minutes),
        "count": len(workouts),
    }


@router.delete("/{entry_id}")
def delete_workout(entry_id: str, user=Depends(get_current_user)):
    if _use_sb():
        (_sb().table("workout_log").delete()
         .eq("user_id", user["id"]).eq("entry_id", entry_id).execute())
    else:
        with _conn() as conn:
            conn.execute(
                "DELETE FROM workout_log WHERE user_id=? AND entry_id=?",
                (user["id"], entry_id),
            )
            conn.commit()
    return {"ok": True}
