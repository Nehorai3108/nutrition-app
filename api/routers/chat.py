from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

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

    # System prompt — when food is mentioned, the model must estimate the REAL
    # portion in grams and the TOTAL nutrition for that portion (not per 100g).
    system = """You are Biti — Israeli nutrition assistant. Always reply in Hebrew.
When the user mentions eating food, return JSON ONLY in this exact shape:
{"meal_type":"lunch","foods":[{"name_he":"שם בעברית","name_en":"english name","grams":<total grams of the portion>,"calories":<total kcal for that portion>,"protein":<g>,"carbs":<g>,"fat":<g>}],"reply":"short Hebrew reply"}
Estimate realistic portion sizes (e.g. ביצה≈55g, פרוסת לחם≈30g, מנת אורז≈180g, חזה עוף≈170g, תפוח≈180g) and compute the TOTAL nutrition for the whole portion the user described, multiplying by the count. name_he must be Hebrew, never Arabic.
Otherwise reply naturally in Hebrew without JSON."""

    messages = [{"role": "system", "content": system}]
    for m in body.history[-10:]:  # שמור 10 הודעות אחרונות
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": body.message})

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()

        # נסה לחלץ JSON
        import re, json
        food_data = None
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
        if m:
            try:
                food_data = json.loads(m.group(1))
                raw = food_data.get("reply", raw)
            except Exception:
                pass
        else:
            m2 = re.search(r'(\{[\s\S]*"meal_type"[\s\S]*"foods"[\s\S]*\})', raw)
            if m2:
                try:
                    food_data = json.loads(m2.group(1))
                    raw = food_data.get("reply", raw)
                except Exception:
                    pass

        if food_data and isinstance(food_data.get("foods"), list):
            food_data["foods"] = [_enrich_food(f) for f in food_data["foods"]]

        return {"reply": raw, "food_data": food_data}
    except Exception as e:
        return {"reply": f"שגיאה: {e}", "food_data": None}


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
