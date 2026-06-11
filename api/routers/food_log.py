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

@router.get("/{date_str}")
def get_log(date_str: str, user=Depends(get_current_user)):
    """מחזיר יומן אכילה לתאריך."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = date.today()
    entries = repo.get_entries(user["id"], d)
    return {"entries": [e.__dict__ for e in entries]}

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
    )
    repo.add_entry(user["id"], d, entry)
    return {"ok": True}

@router.get("/search-food")
def search_food_nutrition(q: str, user=Depends(get_current_user)):
    """חיפוש ערכי תזונה לפי שם מזון."""
    from nutrition_app.agents.agent_3_food import FoodCatalog
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                           "storage", "nutrition.db")
    cat = FoodCatalog(db_path=DB_PATH)
    results = cat.search_foods(q, limit=3)
    if not results:
        return {"found": False}
    food = results[0]
    n = food.nutrition_per_100g
    return {
        "found": True,
        "food_id": food.food_id,
        "name_he": food.name_he,
        "calories_per_100g": n.calories_kcal,
        "protein_per_100g": n.protein_g,
        "carbs_per_100g": n.carbs_g,
        "fat_per_100g": n.fat_g,
    }

@router.delete("/{entry_id}")
def delete_entry(entry_id: str, user=Depends(get_current_user)):
    repo.delete_entry(user["id"], entry_id)
    return {"ok": True}

@router.get("/{date_str}/summary")
def get_summary(date_str: str, user=Depends(get_current_user)):
    """סיכום קלורי יומי."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = date.today()
    entries = repo.get_entries(user["id"], d)
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
