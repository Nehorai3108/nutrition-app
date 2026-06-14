"""
Shared Groq helpers — API key loading + AI nutrition estimation.

Used by the manual food search (food_log router) as a fallback when a food
is not found in the catalog, and reusable by other routers.
"""
import os
import json
import requests

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Reuse the vision-capable model already proven to work for the camera feature;
# it handles plain text estimation fine too.
_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Valid FoodCategory values (mirror of nutrition_app.models.enums.FoodCategory)
_VALID_CATEGORIES = {
    "protein", "carbohydrate", "fat", "vegetable", "fruit", "dairy",
    "grain", "legume", "nut_seed", "condiment", "beverage", "snack",
    "sweet", "other",
}


def get_groq_key() -> str:
    """Load the Groq API key from env or .streamlit/secrets.toml."""
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key
    try:
        import tomllib
        secrets_path = os.path.join(_PROJECT_ROOT, ".streamlit", "secrets.toml")
        with open(secrets_path, "rb") as f:
            return tomllib.load(f).get("groq_api_key", "")
    except Exception:
        return ""


def estimate_nutrition_per_100g(food_name_he: str) -> dict | None:
    """Ask Groq for per-100g nutrition of a Hebrew food/dish name.

    Returns a dict with keys: name_he, name_en, category, calories, protein,
    carbs, fat (all per 100g). Returns None on any failure so callers can
    fall back gracefully.
    """
    api_key = get_groq_key()
    if not api_key or not food_name_he.strip():
        return None

    prompt = f"""אתה מומחה תזונה. עבור המאכל "{food_name_he}" החזר את הערכים התזונתיים ל-100 גרם.
אם זו מנה מורכבת (למשל "פיתה פלאפל", "סביח", "שווארמה בלאפה") — חשב את הממוצע המשוקלל של כל המנה ל-100 גרם.

החזר אך ורק JSON אחד בפורמט הבא, ללא טקסט נוסף:
{{"name_en": "english name", "category": "<one of: protein, carbohydrate, fat, vegetable, fruit, dairy, grain, legume, nut_seed, condiment, beverage, snack, sweet, other>", "calories": <kcal per 100g>, "protein": <g>, "carbs": <g>, "fat": <g>}}"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": _MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 300,
            },
            timeout=20,
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        # Grab the first {...} block to be robust against stray prose.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
        data = json.loads(text.strip())

        cal = float(data.get("calories", 0) or 0)
        if cal <= 0:
            return None
        category = str(data.get("category", "other")).lower().strip()
        if category not in _VALID_CATEGORIES:
            category = "other"

        return {
            "name_he": food_name_he.strip(),
            "name_en": str(data.get("name_en", "")).strip(),
            "category": category,
            "calories": round(cal, 1),
            "protein": round(float(data.get("protein", 0) or 0), 1),
            "carbs": round(float(data.get("carbs", 0) or 0), 1),
            "fat": round(float(data.get("fat", 0) or 0), 1),
        }
    except Exception:
        return None
