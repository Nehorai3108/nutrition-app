from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date
from api.deps import get_current_user
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
    """Hebrew words of length >= 2 in the query."""
    import re
    return {w for w in re.findall("[֐-׿]+", text or "") if len(w) >= 2}


def _catalog_covers_query(food, q: str) -> bool:
    """True if the matched food accounts for ALL Hebrew words in the query.

    Guards against a multi-word dish (e.g. "פיתה פלאפל") collapsing onto a
    single-word partial match ("פיתה"). Single-word queries that hit a
    catalog entry are always considered covered.
    """
    q_tokens = _hebrew_tokens(q)
    if len(q_tokens) <= 1:
        return True
    searchable = " ".join([food.name_he or "", " ".join(food.aliases_he or [])])
    food_tokens = _hebrew_tokens(searchable)
    return q_tokens.issubset(food_tokens)


@router.get("/search-food")
def search_food_nutrition(q: str, user=Depends(get_current_user)):
    """חיפוש ערכי תזונה לפי שם מזון.

    קטלוג קודם; אם אין התאמה טובה (חסרות קלוריות, או המאכל לא מכסה את כל
    מילות החיפוש) — Groq מעריך את הערכים והפריט נשמר למסד כמקור 'ai'
    כך שהקטלוג העברי גדל אורגנית.
    """
    from nutrition_app.agents.agent_3_food import FoodCatalog
    cat = FoodCatalog(db_path=_DB_PATH)
    # Get more candidates, then prefer entries with actual nutrition data
    candidates = cat.search_foods(q, limit=20)
    with_data = [f for f in candidates if f.nutrition_per_100g.calories_kcal]

    food = with_data[0] if with_data else None
    if food is not None and _catalog_covers_query(food, q):
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
        }

    # No good catalog match → AI estimate + persist for next time.
    ai = _ai_estimate_and_store(q)
    if ai:
        return ai

    # AI unavailable — fall back to whatever the catalog had, if anything.
    if food is not None:
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
        }
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
    }

@router.post("/")
def add_entry(body: AddFoodEntry, user=Depends(get_current_user)):
    from datetime import datetime
    d = date.fromisoformat(body.date) if body.date else date.today()
    entry = FoodLogEntry(
        food_id=body.food_id,
        food_name=body.food_name,
        grams=body.grams,
        calories=body.calories,
        protein=body.protein,
        carbs=body.carbs,
        fat=body.fat,
        meal_type=body.meal_type,
        timestamp=datetime.now().isoformat(),
        image_url=body.image_url,
    )
    repo.add_entry(user["id"], d, entry)
    return {"ok": True}

@router.get("/{date_str}")
def get_log(date_str: str, user=Depends(get_current_user)):
    """מחזיר יומן אכילה לתאריך, עם תמונה ממתכון אם קיימת."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = date.today()
    entries = repo.get_log(user["id"], d)
    # Enrich with recipe images for entries that came from a recipe card
    recipe_images = _load_recipe_images()
    result = []
    for e in entries:
        row = {k: v for k, v in e.__dict__.items()}
        row["image_url"] = row.get("image_url") or recipe_images.get(e.food_id)
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
    repo.remove_entry(user["id"], date.today(), entry_id)
    return {"ok": True}

@router.get("/{date_str}/summary")
def get_summary(date_str: str, user=Depends(get_current_user)):
    """סיכום קלורי יומי."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = date.today()
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
