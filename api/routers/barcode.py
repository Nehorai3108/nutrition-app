from fastapi import APIRouter, Depends
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

@router.get("/{barcode}")
def lookup_barcode(barcode: str, user=Depends(get_current_user)):
    """חיפוש מוצר לפי ברקוד."""
    from nutrition_app.agents.agent_3_food import FoodCatalog
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                           "storage", "nutrition.db")
    cat = FoodCatalog(db_path=DB_PATH)
    food = cat.get_by_barcode(barcode)
    if not food:
        return {"found": False}
    n = food.nutrition_per_100g
    return {
        "found": True,
        "food": {
            "food_id":   food.food_id,
            "name_he":   food.name_he,
            "name_en":   food.name_en,
            "calories":  n.calories_kcal,
            "protein":   n.protein_g,
            "carbs":     n.carbs_g,
            "fat":       n.fat_g,
            "serving_g": food.default_serving_g,
            "unit":      food.default_unit,
        }
    }
