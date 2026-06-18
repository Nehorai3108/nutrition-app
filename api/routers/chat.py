from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "storage", "nutrition.db")


@router.get("/insight")
def daily_insight(user=Depends(get_current_user)):
    """תובנה פרואקטיבית של Biti — מבוססת נתוני היום של המשתמש.

    הקוד מחשב את המספרים (יעד, נאכל, נשרף, מה שנותר); הניסוח בעברית
    דטרמיניסטי וטבעי — תלוי במצב בפועל.
    """
    from datetime import date, datetime
    from api._tz import now_il, today_il
    import sqlite3

    # Targets
    try:
        from api.routers.profile import get_targets
        t = get_targets(user)
    except Exception:
        t = {"calories": 2000, "protein": 150, "carbs": 250, "fat": 67}

    # Eaten today
    try:
        from nutrition_app.repositories.food_log_repository import FoodLogRepository
        totals = FoodLogRepository().get_totals(user["id"], today_il())
    except Exception:
        totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "count": 0}

    # Burned today
    burned = 0
    try:
        conn = sqlite3.connect(_DB_PATH)
        row = conn.execute(
            "SELECT COALESCE(SUM(calories_burned),0) FROM workout_log WHERE user_id=? AND date=?",
            (user["id"], today_il().isoformat()),
        ).fetchone()
        burned = round(row[0] or 0)
        conn.close()
    except Exception:
        pass

    eaten_cal = round(totals.get("calories", 0))
    eaten_prot = round(totals.get("protein", 0))
    target_cal = round(t.get("calories", 2000))
    target_prot = round(t.get("protein", 150))
    budget = target_cal + burned
    remaining_cal = budget - eaten_cal
    remaining_prot = target_prot - eaten_prot
    count = totals.get("count", 0)

    hour = now_il().hour
    if hour < 11:
        greet = "בוקר טוב"
    elif hour < 16:
        greet = "צהריים טובים"
    elif hour < 21:
        greet = "ערב טוב"
    else:
        greet = "לילה טוב"

    lines = []
    if count == 0:
        lines.append(f"{greet}! עוד לא רשמת ארוחות היום. היעד שלך הוא {target_cal} קק\"ל.")
        lines.append("ספר לי מה אכלת או צלם ארוחה ואעדכן לך את היומן.")
    else:
        if remaining_cal > 50:
            lines.append(f"{greet}! אכלת {eaten_cal} קק\"ל היום — נשארו לך {remaining_cal} קק\"ל מתוך {budget}.")
        elif remaining_cal < -50:
            lines.append(f"{greet}! עברת את היעד היומי ב-{abs(remaining_cal)} קק\"ל ({eaten_cal} מתוך {budget}).")
        else:
            lines.append(f"{greet}! אתה בדיוק על היעד — {eaten_cal} מתוך {budget} קק\"ל. כל הכבוד!")

        if burned > 0:
            lines.append(f"שרפת היום {burned} קק\"ל באימון — הוספתי אותן לתקציב.")

        if remaining_prot > 25:
            lines.append(f"כדאי להוסיף חלבון — נשארו לך {remaining_prot}g מהיעד היומי.")
        elif remaining_prot <= 5 and eaten_prot > 0:
            lines.append(f"השלמת כמעט את כל יעד החלבון ({eaten_prot}/{target_prot}g) — מצוין.")

    return {
        "message": "\n".join(lines),
        "greeting": greet,
        "target_calories": target_cal,
        "eaten_calories": eaten_cal,
        "burned_calories": burned,
        "remaining_calories": remaining_cal,
        "remaining_protein": remaining_prot,
        "entries": count,
    }

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

@router.post("/")
def chat(body: ChatRequest, user=Depends(get_current_user)):
    """שולח הודעה ל-AI ומקבל תגובה + נתוני מזון."""
    import os
    from groq import Groq
    from nutrition_app.agents.agent_3_food import FoodCatalog
    from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
    from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        try:
            import tomllib
            secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".streamlit", "secrets.toml")
            with open(secrets_path, "rb") as f:
                api_key = tomllib.load(f).get("groq_api_key", "")
        except Exception:
            pass
    if not api_key:
        return {"reply": "שגיאה: Groq API key חסר", "food_data": None}

    client = Groq(api_key=api_key)

    inv_ctx = _inventory_context(user["id"])

    system = f"""You are Biti — a smart Israeli nutrition assistant. Always reply in Hebrew.

USER CONTEXT (live data — use it):
- Inventory (מלאי): {inv_ctx}

You can ACT for the user by returning a JSON object (inside a ```json block). Use it when relevant:

1. LOG food the user says they ate — include "foods":
   "foods":[{{"name_he":"שם בעברית","name_en":"english","grams":<total grams>,"calories":<total kcal>,"protein":<g>,"carbs":<g>,"fat":<g>}}]
   Estimate realistic portions (ביצה≈55g, פרוסת לחם≈30g, מנת אורז≈180g, חזה עוף≈170g, תפוח≈180g) and compute TOTAL nutrition for the portion described.

2. ADD or REMOVE inventory items when the user asks (e.g. "קניתי עגבניות תוסיף למלאי", "תוריד חלב מהמלאי") — include "actions":
   "actions":[{{"type":"add_inventory","name_he":"עגבניות","quantity":1,"unit":"יח׳","category":"produce"}}]
   type is "add_inventory" or "remove_inventory". category ∈ produce,meat,dairy,bakery,pantry,frozen,beverages,snacks,other.

The system REALLY performs the actions — so confirm it's done in your reply (e.g. "הוספתי עגבניות למלאי ✓"). Do NOT ask the user to add it himself.

Always include "reply": one short natural Hebrew sentence.
For plain questions just reply with normal Hebrew text (no JSON).
name_he must be in Hebrew, NEVER Arabic."""

    messages = [{"role": "system", "content": system}]
    for m in body.history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": body.message})

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()

        data = _extract_json(raw)
        reply = raw
        food_data = None
        actions_done = []

        if data:
            reply = (data.get("reply") or "").strip() or "בוצע ✓"
            if isinstance(data.get("foods"), list) and data["foods"]:
                food_data = {
                    "meal_type": data.get("meal_type", "lunch"),
                    "foods": [_enrich_food(f) for f in data["foods"]],
                }
            if isinstance(data.get("actions"), list) and data["actions"]:
                actions_done = _exec_actions(user["id"], data["actions"])

        return {"reply": reply, "food_data": food_data, "actions": actions_done}
    except Exception as e:
        return {"reply": f"שגיאה: {e}", "food_data": None}


def _extract_json(raw: str):
    """Pull the first JSON object out of the model reply (fenced or raw)."""
    import json
    text = raw
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def _inventory_context(user_id: str) -> str:
    try:
        from api.routers.inventory import _conn
        with _conn() as c:
            rows = c.execute(
                "SELECT name_he, quantity, unit FROM inventory WHERE user_id=? ORDER BY added_at DESC LIMIT 40",
                (user_id,),
            ).fetchall()
        if not rows:
            return "ריק (אין מוצרים)"
        return ", ".join(f"{r['name_he']} ({_fmt_q(r['quantity'])} {r['unit']})" for r in rows)
    except Exception:
        return "לא זמין"


def _fmt_q(q):
    try:
        q = float(q)
        return int(q) if q == int(q) else round(q, 1)
    except (TypeError, ValueError):
        return q


def _exec_actions(user_id: str, actions: list) -> list:
    """Execute inventory add/remove actions. Returns a list of (op, name)."""
    from api.routers.inventory import _conn, _insert
    done = []
    try:
        with _conn() as c:
            for a in actions:
                if not isinstance(a, dict):
                    continue
                t = (a.get("type") or "").lower().strip()
                name = (a.get("name_he") or a.get("name") or "").strip()
                if not name:
                    continue
                if t in ("add_inventory", "add"):
                    try:
                        qty = float(a.get("quantity") or 1)
                    except (TypeError, ValueError):
                        qty = 1
                    _insert(c, user_id, name, qty, a.get("unit") or "יח׳", a.get("category") or "other")
                    done.append({"op": "added", "name": name})
                elif t in ("remove_inventory", "remove", "delete"):
                    c.execute("DELETE FROM inventory WHERE user_id=? AND name_he LIKE ?",
                              (user_id, f"%{name}%"))
                    done.append({"op": "removed", "name": name})
            c.commit()
    except Exception:
        pass
    return done


def _enrich_food(food: dict) -> dict:
    """Guarantee a chat-detected food has grams + total calories/macros.

    The model is asked to provide them; if calories are missing or zero we
    resolve per-100g nutrition (AI estimator on the Hebrew name) and scale by
    the portion grams. Returns a normalized dict the client can log directly.
    """
    name_he = food.get("name_he") or food.get("name") or "מזון"
    name_en = food.get("name_en") or food.get("name") or name_he

    try:
        grams = float(food.get("grams") or 0)
    except (TypeError, ValueError):
        grams = 0.0
    if grams <= 0:
        grams = 100.0

    def _num(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    cal = _num(food.get("calories"))
    prot = _num(food.get("protein"))
    carbs = _num(food.get("carbs"))
    fat = _num(food.get("fat"))

    if cal <= 0:
        # Fallback: AI estimates per-100g, then scale to the portion.
        try:
            from api.nutrition_ai import estimate_nutrition_per_100g
            est = estimate_nutrition_per_100g(name_he)
        except Exception:
            est = None
        if est:
            f = grams / 100.0
            cal   = round(est["calories"] * f)
            prot  = round(est["protein"] * f, 1)
            carbs = round(est["carbs"] * f, 1)
            fat   = round(est["fat"] * f, 1)

    try:
        from api.food_image import get_food_image
        image_url = get_food_image(name_en, name_he)
    except Exception:
        image_url = None

    return {
        "name": name_en,
        "name_he": name_he,
        "grams": round(grams),
        "calories": round(cal),
        "protein": round(prot, 1),
        "carbs": round(carbs, 1),
        "fat": round(fat, 1),
        "image_url": image_url,
        # keep originals for display
        "quantity": food.get("quantity"),
        "unit": food.get("unit"),
    }
