from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date
from api.deps import get_current_user
from api._tz import now_il_iso, today_il
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry

router = APIRouter()
repo = FoodLogRepository()

class AddFoodEntry(BaseModel):
    food_id: str
    food_name: str
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    meal_type: str
    date: Optional[str] = None
    image_url: Optional[str] = None

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "storage", "nutrition.db")


def _hebrew_tokens(text: str) -> set:
    """Hebrew words of length >= 2 in the text (the geresh ׳ stays attached)."""
    import re
    return {w for w in re.findall("[֐-׿]+", text or "") if len(w) >= 2}


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _catalog_covers_query(food, q: str) -> bool:
    """True only if the food accounts for EVERY Hebrew word in the query.

    Word-token based (not substring): query "סושי" is NOT covered by
    "אורז עגול קלרוז לסושי" because "לסושי" ≠ "סושי". Non-Hebrew queries
    (no Hebrew tokens) are treated as covered so English search still hits
    the catalog. This is what stops a multi-word dish ("פיתה פלאפל") or a
    bare term ("סושי") from collapsing onto an irrelevant partial match.
    """
    q_tokens = _hebrew_tokens(q)
    if not q_tokens:
        return True
    searchable = " ".join([food.name_he or "", " ".join(food.aliases_he or [])])
    return q_tokens.issubset(_hebrew_tokens(searchable))


def _is_trusted_match(food, q: str) -> bool:
    """Whether a catalog hit is reliable enough to show without AI.

    Trust the curated Hebrew catalog (json), manual entries, and AI-estimated
    foods when they cover the query. For the noisy USDA/Open-Food-Facts rows,
    trust only an exact Hebrew-name match — otherwise defer to the AI estimator,
    which is far more reliable for free-text dish names than a random product.
    """
    if not _catalog_covers_query(food, q):
        return False
    src = (food.source or "").lower()
    if src in ("json", "manual", "ai", "catalog", "user_custom"):
        return True
    return bool(_hebrew_tokens(q)) and _norm(food.name_he) == _norm(q)


def _household_display(food_name: str, grams: float, name_en: str = "") -> Optional[str]:
    """Household-unit string for a logged food (e.g. "4 תותים", "3 כפות אורז").
    name_en drives the conversion table; without it most foods fall back to
    grams. Returns None on failure so the app uses its own gram display."""
    try:
        from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
        disp = format_ingredient_display({
            "food_name": food_name or "",
            "food_name_en": name_en or "",
            "quantity": grams or 0,
            "unit": "grams",
        })
        return disp or None
    except Exception:
        return None


def _name_en_lookup():
    """A cached food_id/name_he → name_en resolver backed by the catalog."""
    try:
        from nutrition_app.agents.agent_3_food import FoodCatalog
        cat = FoodCatalog(db_path=_DB_PATH)
    except Exception:
        return lambda fid, name_he: ""

    cache: dict = {}

    def resolve(fid: str, name_he: str) -> str:
        key = fid or name_he or ""
        if key in cache:
            return cache[key]
        en = ""
        try:
            food = cat.get_food_by_id(fid) if fid else None
            en = getattr(food, "name_en", "") if food else ""
        except Exception:
            en = ""
        cache[key] = en or ""
        return cache[key]

    return resolve


def _serving(name_he: str, name_en: str) -> Optional[dict]:
    """Household serving info for the manual-add unit picker, or None → grams.
    e.g. {"unit_he": "ביצה", "unit_he_plural": "ביצים", "grams_per_unit": 50}."""
    try:
        from nutrition_app.agents.agent_11_recipes.unit_converter import household_unit_for
        e = household_unit_for(name_he or "", name_en or "")
        if not e:
            return None
        return {
            "unit_he": e["unit_he"],
            "unit_he_plural": e.get("unit_he_plural", e["unit_he"]),
            "grams_per_unit": e["grams_per_unit"],
        }
    except Exception:
        return None


def _food_image(name_en: str, name_he: str):
    try:
        from api.food_image import get_food_image
        return get_food_image(name_en or "", name_he or "")
    except Exception:
        return None


def _food_response(food) -> dict:
    n = food.nutrition_per_100g
    return {
        "found": True,
        "source": food.source or "catalog",
        "food_id": food.food_id,
        "name_he": food.name_he,
        "calories_per_100g": n.calories_kcal,
        "protein_per_100g": n.protein_g,
        "carbs_per_100g": n.carbs_g,
        "fat_per_100g": n.fat_g,
        "image_url": _food_image(getattr(food, "name_en", ""), food.name_he),
        "serving": _serving(food.name_he, getattr(food, "name_en", "")),
    }


@router.get("/search-food")
def search_food_nutrition(q: str, user=Depends(get_current_user)):
    """חיפוש ערכי תזונה לפי שם מזון.

    מחזיר נתון רק כשאפשר לסמוך עליו: התאמה חזקה בקטלוג העברי המוקפד / AI /
    התאמה מדויקת. כל השאר (התאמות חלקיות, נתוני OFF/USDA רועשים) → Groq מעריך
    את הערכים, והפריט נשמר כמקור 'ai' כך שהקטלוג העברי גדל אורגנית.
    """
    from nutrition_app.agents.agent_3_food import FoodCatalog
    cat = FoodCatalog(db_path=_DB_PATH)
    candidates = cat.search_foods(q, limit=20)
    with_data = [f for f in candidates if f.nutrition_per_100g.calories_kcal]

    # 1. First reliable catalog match wins.
    for food in with_data:
        if _is_trusted_match(food, q):
            return _food_response(food)

    # 2. Nothing trustworthy → AI estimate + persist for next time.
    ai = _ai_estimate_and_store(q)
    if ai:
        return ai

    # 3. AI unavailable — return the best catalog hit rather than nothing.
    if with_data:
        return _food_response(with_data[0])
    return {"found": False}


def _ai_estimate_and_store(q: str) -> Optional[dict]:
    """Estimate nutrition via Groq and persist as a new 'ai'-sourced food."""
    from api.nutrition_ai import estimate_nutrition_per_100g
    est = estimate_nutrition_per_100g(q)
    if not est:
        return None

    import hashlib
    food_id = "ai_" + hashlib.md5(q.strip().encode("utf-8")).hexdigest()[:12]
    try:
        from db.database import NutritionDB
        NutritionDB(_DB_PATH).upsert_food({
            "food_id": food_id,
            "name_he": est["name_he"],
            "name_en": est["name_en"] or est["name_he"],
            "category": est["category"],
            "calories_kcal": est["calories"],
            "protein_g": est["protein"],
            "carbs_g": est["carbs"],
            "fat_g": est["fat"],
            "source": "ai",
            "is_custom": 1,
        })
    except Exception:
        pass  # Estimation still returned even if persistence fails.

    return {
        "found": True,
        "source": "ai",
        "food_id": food_id,
        "name_he": est["name_he"],
        "calories_per_100g": est["calories"],
        "protein_per_100g": est["protein"],
        "carbs_per_100g": est["carbs"],
        "fat_per_100g": est["fat"],
        "image_url": _food_image(est.get("name_en", ""), est["name_he"]),
        "serving": _serving(est["name_he"], est.get("name_en", "")),
    }

@router.post("/")
def add_entry(body: AddFoodEntry, user=Depends(get_current_user)):
    d = date.fromisoformat(body.date) if body.date else today_il()
    entry = FoodLogEntry(
        food_id=body.food_id,
        food_name=body.food_name,
        grams=body.grams,
        calories=body.calories,
        protein=body.protein,
        carbs=body.carbs,
        fat=body.fat,
        meal_type=body.meal_type,
        timestamp=now_il_iso(),
        image_url=body.image_url,
    )
    repo.add_entry(user["id"], d, entry)
    return {"ok": True}

@router.get("/history")
def get_history(days: int = 35, user=Depends(get_current_user)):
    """סיכום קלורי לכל יום ב-N הימים האחרונים (לתצוגת לוח שנה)."""
    from datetime import timedelta
    end = today_il()
    start = end - timedelta(days=max(1, min(days, 366)))
    return {"days": repo.get_history(user["id"], start, end)}

@router.get("/recents")
def get_recents(limit: int = 12, user=Depends(get_current_user)):
    """מאכלים אחרונים ייחודיים — לרישום חוזר בלחיצה אחת."""
    return {"foods": repo.get_recent_foods(user["id"], limit=max(1, min(limit, 50)))}

@router.get("/{date_str}")
def get_log(date_str: str, user=Depends(get_current_user)):
    """מחזיר יומן אכילה לתאריך, עם תמונה ממתכון אם קיימת."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = today_il()
    entries = repo.get_log(user["id"], d)
    # Enrich with recipe images for entries that came from a recipe card
    recipe_images = _load_recipe_images()
    name_en_of = _name_en_lookup()
    result = []
    for e in entries:
        row = {k: v for k, v in e.__dict__.items()}
        row["image_url"] = row.get("image_url") or recipe_images.get(e.food_id)
        # Last resort: resolve an image by the food name (disk-cached, so fast
        # after the first lookup). Makes manually-added foods show a thumbnail
        # even if none was stored on the entry.
        if not row.get("image_url") and e.food_name and e.food_id != "camera_food":
            row["image_url"] = _food_image("", e.food_name)
        # Household-unit display so the diary shows physical units, not grams.
        if not row.get("display_he"):
            row["display_he"] = _household_display(
                e.food_name, e.grams, name_en_of(e.food_id, e.food_name))
        result.append(row)
    return {"entries": result}

def _load_recipe_images() -> dict:
    """Returns {recipe_id: image_url} from recipes.json."""
    try:
        recipes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "storage_agents", "recipes", "recipes.json",
        )
        import json
        with open(recipes_path, encoding="utf-8") as f:
            recipes = json.load(f)
        return {
            r["recipe_id"]: r.get("image_url")
            for r in recipes
            if r.get("recipe_id") and r.get("image_url")
        }
    except Exception:
        return {}

@router.delete("/{entry_id}")
def delete_entry(entry_id: str, user=Depends(get_current_user)):
    repo.remove_entry(user["id"], today_il(), entry_id)
    return {"ok": True}

@router.get("/{date_str}/summary")
def get_summary(date_str: str, user=Depends(get_current_user)):
    """סיכום קלורי יומי."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = today_il()
    entries = repo.get_log(user["id"], d)
    total_cal  = sum(e.calories for e in entries)
    total_prot = sum(e.protein  for e in entries)
    total_carb = sum(e.carbs    for e in entries)
    total_fat  = sum(e.fat      for e in entries)
    return {
        "date":     date_str,
        "calories": round(total_cal),
        "protein":  round(total_prot, 1),
        "carbs":    round(total_carb, 1),
        "fat":      round(total_fat, 1),
        "entries":  len(entries),
    }
