"""
Shared Groq helpers — API key loading + AI nutrition estimation.

Used by the manual food search (food_log router) as a fallback when a food
is not found in the catalog, and reusable by other routers.
"""
import os
import json
import requests

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Disk + memory cache so repeated foods don't re-hit Groq (per-call ~0.7s).
_NUT_CACHE_PATH = os.path.join(_PROJECT_ROOT, "storage_agents", "nutrition_ai_cache.json")
_nut_cache = None


def _load_nut_cache() -> dict:
    global _nut_cache
    if _nut_cache is None:
        try:
            with open(_NUT_CACHE_PATH, encoding="utf-8") as f:
                _nut_cache = json.load(f)
        except Exception:
            _nut_cache = {}
    return _nut_cache


def _save_nut_cache() -> None:
    try:
        os.makedirs(os.path.dirname(_NUT_CACHE_PATH), exist_ok=True)
        with open(_NUT_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_nut_cache, f, ensure_ascii=False)
    except Exception:
        pass

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
    if not food_name_he.strip():
        return None

    key = food_name_he.strip()
    cache = _load_nut_cache()
    if key in cache:
        return cache[key]

    api_key = get_groq_key()
    if not api_key:
        return None

    prompt = f"""אתה מומחה תזונה. עבור המאכל "{food_name_he}" החזר את הערכים התזונתיים ל-100 גרם.
אם זו מנה מורכבת (למשל "פיתה פלאפל", "סביח", "שווארמה בלאפה") — חשב את הממוצע המשוקלל של כל המנה ל-100 גרם.

כללים מחייבים (ל-100 גרם מזון):
- חלבון + פחמימות + שומן ביחד לא יכולים לעלות על 100 גרם.
- הקלוריות חייבות להיות עקביות עם המקרו: קלוריות ≈ 4×חלבון + 4×פחמימות + 9×שומן.
- ערכים ריאליים: קלוריות 0–900, כל מקרו 0–100 גרם.
- אם אינך בטוח — תן הערכה סבירה של מאכל דומה, לעולם אל תמציא ערכים קיצוניים.

החזר אך ורק JSON אחד בפורמט הבא, ללא טקסט נוסף:
{{"name_en": "english name", "category": "<one of: protein, carbohydrate, fat, vegetable, fruit, dairy, grain, legume, nut_seed, condiment, beverage, snack, sweet, other>", "calories": <kcal per 100g>, "protein": <g>, "carbs": <g>, "fat": <g>}}"""

    import time as _t
    _t0 = _t.time()
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
        _body = resp.json()
        try:
            from api.llm_usage import log_llm_usage
            # utility — no user context; logged as "anon"
            log_llm_usage("anon", "groq", _MODEL, "nutrition_estimate",
                          _body.get("usage"), latency_ms=(_t.time() - _t0) * 1000)
        except Exception:
            pass
        text = _body["choices"][0]["message"]["content"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        # Grab the first {...} block to be robust against stray prose.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
        data = json.loads(text.strip())

        vals = _sanitize_macros(data)
        if vals is None:
            return None  # implausible estimate — caller falls back to catalog
        cal, protein, carbs, fat = vals

        category = str(data.get("category", "other")).lower().strip()
        if category not in _VALID_CATEGORIES:
            category = "other"

        result = {
            "name_he": food_name_he.strip(),
            "name_en": str(data.get("name_en", "")).strip(),
            "category": category,
            "calories": round(cal, 1),
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1),
        }
        cache[key] = result
        _save_nut_cache()
        return result
    except Exception:
        return None


def _sanitize_macros(data: dict):
    """Validate/repair a per-100g estimate. Returns (cal, protein, carbs, fat)
    or None when the numbers are implausible (so the caller falls back to the
    catalog instead of logging a bogus value).

    Guardrails:
      • each value within a physical per-100g range,
      • protein+carbs+fat ≤ 100g (per 100g of food — can't exceed its mass),
      • calories consistent with the Atwater estimate (4·protein + 4·carbs +
        9·fat); if the model's calorie number disagrees by >25%, trust the
        macros and recompute calories from them.
    """
    try:
        cal = float(data.get("calories", 0) or 0)
        protein = float(data.get("protein", 0) or 0)
        carbs = float(data.get("carbs", 0) or 0)
        fat = float(data.get("fat", 0) or 0)
    except (TypeError, ValueError):
        return None

    # Reject negatives / out-of-range values outright.
    if min(cal, protein, carbs, fat) < 0:
        return None
    if protein > 100 or carbs > 100 or fat > 100 or cal > 900:
        return None
    # Macros can't weigh more than the 100g of food they came from (small slack
    # for rounding). A sum well over 100 means the estimate is inflated.
    if protein + carbs + fat > 105:
        return None

    atwater = 4 * protein + 4 * carbs + 9 * fat
    # If the model gave essentially no calories but real macros, use Atwater.
    if cal <= 0:
        cal = atwater
    # Disagreement > 25% → the macros are usually the more reliable signal.
    elif atwater > 0 and abs(cal - atwater) / atwater > 0.25:
        cal = atwater

    if cal <= 0:
        return None
    return cal, protein, carbs, fat
