"""
מאזן יומי חכם — per-meal calorie balancing.

לכל ארוחה יש יעד (חלק מהיעד היומי). כשהמשתמש אוכל פחות/יותר מהיעד של ארוחה,
הוא יכול "להעביר" את ההפרש לארוחה אחרת — כך שהסכום היומי נשמר. אין גלישה
למחר: ה-adjustments נשמרים פר-יום ומתאפסים בכל יום חדש.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os, sqlite3, json
from api.deps import get_current_user
from api._tz import today_il

router = APIRouter()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "storage", "nutrition.db")

# סדר וחלוקת ברירת המחדל של הארוחות (תואם ל-daily_menu)
MEAL_ORDER = ["BREAKFAST", "MORNING_SNACK", "LUNCH", "AFTERNOON_SNACK", "DINNER", "EVENING_SNACK"]
MEAL_DISTRIBUTION = {
    "BREAKFAST": 0.25, "MORNING_SNACK": 0.08, "LUNCH": 0.30,
    "AFTERNOON_SNACK": 0.08, "DINNER": 0.22, "EVENING_SNACK": 0.07,
}


def _use_sb() -> bool:
    return bool(os.environ.get("SUPABASE_URL"))


def _sb():
    from nutrition_app.db.supabase_client import get_supabase
    return get_supabase()


def _conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS meal_balance (
        user_id TEXT NOT NULL, date TEXT NOT NULL,
        adjustments TEXT DEFAULT '{}', PRIMARY KEY (user_id, date))""")
    return conn


def _load_adjustments(user_id: str, date_str: str) -> dict:
    """{meal: delta_kcal} — סכום ה-deltas תמיד 0 (זו חלוקה מחדש)."""
    if _use_sb():
        rows = (_sb().table("meal_balance").select("adjustments")
                .eq("user_id", user_id).eq("date", date_str).limit(1).execute()).data
        if rows:
            adj = rows[0].get("adjustments")
            return adj if isinstance(adj, dict) else (json.loads(adj) if adj else {})
        return {}
    with _conn() as c:
        row = c.execute("SELECT adjustments FROM meal_balance WHERE user_id=? AND date=?",
                        (user_id, date_str)).fetchone()
        return json.loads(row["adjustments"]) if row and row["adjustments"] else {}


def _save_adjustments(user_id: str, date_str: str, adj: dict) -> None:
    if _use_sb():
        _sb().table("meal_balance").upsert(
            {"user_id": user_id, "date": date_str, "adjustments": adj},
            on_conflict="user_id,date").execute()
    else:
        with _conn() as c:
            c.execute("""INSERT INTO meal_balance (user_id, date, adjustments) VALUES (?,?,?)
                         ON CONFLICT(user_id,date) DO UPDATE SET adjustments=excluded.adjustments""",
                      (user_id, date_str, json.dumps(adj)))
            c.commit()


def _eaten_by_meal(user_id: str, date_str: str) -> dict:
    from datetime import date as _date
    from nutrition_app.repositories.food_log_repository import FoodLogRepository
    eaten = {m: 0.0 for m in MEAL_ORDER}
    try:
        entries = FoodLogRepository().get_log(user_id, _date.fromisoformat(date_str))
        for e in entries:
            mt = (getattr(e, "meal_type", "") or "").upper()
            if mt in eaten:
                eaten[mt] += float(getattr(e, "calories", 0) or 0)
    except Exception:
        pass
    return eaten


def _build_balance(user_id: str, date_str: str) -> dict:
    from api.routers.profile import get_targets
    daily = get_targets({"id": user_id}).get("calories", 2000) or 2000
    adj = _load_adjustments(user_id, date_str)
    eaten = _eaten_by_meal(user_id, date_str)

    meals = []
    for m in MEAL_ORDER:
        base = round(daily * MEAL_DISTRIBUTION[m])
        delta = round(adj.get(m, 0))
        target = max(0, base + delta)
        ate = round(eaten.get(m, 0))
        meals.append({
            "meal": m, "base_target": base, "adjustment": delta,
            "target": target, "eaten": ate, "remaining": target - ate,
        })
    total_eaten = round(sum(eaten.values()))
    return {
        "date": date_str,
        "daily_target": round(daily),
        "daily_eaten": total_eaten,
        "daily_remaining": round(daily) - total_eaten,
        "meals": meals,
    }


class MoveRequest(BaseModel):
    from_meal: str
    to_meal: str
    amount: float


@router.get("/{date_str}")
def get_balance(date_str: str, user=Depends(get_current_user)):
    return _build_balance(user["id"], date_str)


@router.post("/{date_str}/move")
def move_calories(date_str: str, body: MoveRequest, user=Depends(get_current_user)):
    fm, tm = body.from_meal.upper(), body.to_meal.upper()
    if fm not in MEAL_ORDER or tm not in MEAL_ORDER or fm == tm:
        raise HTTPException(status_code=400, detail="ארוחות לא תקינות")
    amt = round(float(body.amount))
    if amt == 0:
        return _build_balance(user["id"], date_str)
    adj = _load_adjustments(user["id"], date_str)
    adj[fm] = round(adj.get(fm, 0)) - amt
    adj[tm] = round(adj.get(tm, 0)) + amt
    _save_adjustments(user["id"], date_str, adj)
    return _build_balance(user["id"], date_str)


@router.delete("/{date_str}")
def reset_balance(date_str: str, user=Depends(get_current_user)):
    """איפוס ההתאמות של היום — חזרה לחלוקת ברירת המחדל."""
    _save_adjustments(user["id"], date_str, {})
    return _build_balance(user["id"], date_str)
