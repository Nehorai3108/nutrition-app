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
    # Try OpenFoodFacts first, fallback to local search
    import requests as _req
    try:
        r = _req.get(
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
            timeout=5,
            headers={"User-Agent": "BiteFit/1.0 (nutrition app)"}
        )
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == 1:
                p = d["product"]
                n = p.get("nutriments", {})
                return {
                    "found": True,
                    "food": {
                        "food_id":   barcode,
                        "name_he":   p.get("product_name_he") or p.get("product_name", ""),
                        "name_en":   p.get("product_name_en") or p.get("product_name", ""),
                        "calories":  round(n.get("energy-kcal_100g", 0)),
                        "protein":   round(n.get("proteins_100g", 0), 1),
                        "carbs":     round(n.get("carbohydrates_100g", 0), 1),
                        "fat":       round(n.get("fat_100g", 0), 1),
                        "serving_g": round(n.get("serving_size", 100)),
                        "unit":      "גרם",
                    }
                }
    except Exception:
        pass
    return {"found": False}
