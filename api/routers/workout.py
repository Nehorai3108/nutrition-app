from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from api.deps import get_current_user
import sys, os, uuid, sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "storage", "nutrition.db")


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
    d = body.date or date.today().isoformat()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO workout_log
                 (entry_id, user_id, date, mode, workout_type, intensity,
                  duration_minutes, distance_km, calories_burned, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                uuid.uuid4().hex, user["id"], d, body.mode, body.workout_type,
                body.intensity, body.duration_minutes, body.distance_km,
                body.calories_burned, datetime.now().isoformat(),
            ),
        )
        conn.commit()
    return {"ok": True}


@router.get("/{date_str}")
def get_workouts(date_str: str, user=Depends(get_current_user)):
    try:
        date.fromisoformat(date_str)
    except ValueError:
        date_str = date.today().isoformat()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workout_log WHERE user_id=? AND date=? ORDER BY rowid",
            (user["id"], date_str),
        ).fetchall()
    return {"workouts": [dict(r) for r in rows]}


@router.get("/{date_str}/summary")
def get_workout_summary(date_str: str, user=Depends(get_current_user)):
    try:
        date.fromisoformat(date_str)
    except ValueError:
        date_str = date.today().isoformat()
    with _conn() as conn:
        row = conn.execute(
            """SELECT COALESCE(SUM(calories_burned),0) AS burned,
                      COALESCE(SUM(duration_minutes),0) AS minutes,
                      COUNT(*) AS count
               FROM workout_log WHERE user_id=? AND date=?""",
            (user["id"], date_str),
        ).fetchone()
    return {
        "calories_burned": round(row["burned"]),
        "minutes": round(row["minutes"]),
        "count": row["count"],
    }


@router.delete("/{entry_id}")
def delete_workout(entry_id: str, user=Depends(get_current_user)):
    with _conn() as conn:
        conn.execute(
            "DELETE FROM workout_log WHERE user_id=? AND entry_id=?",
            (user["id"], entry_id),
        )
        conn.commit()
    return {"ok": True}
