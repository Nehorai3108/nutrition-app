from fastapi import APIRouter, Depends, Query
from typing import Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.unit_converter import enrich_recipe_ingredients
from nutrition_app.repositories.profile_repository import ProfileRepository

router = APIRouter()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_IMAGES_DIR = os.path.join(_PROJECT_ROOT, "storage_agents", "recipe_images", "approved")
_PUBLIC_BASE = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = RecipeManager()
    return _manager

# Same curated map the recipes page / original Streamlit app uses as image fallback.
_recipe_image_map = None
def _get_recipe_image_map():
    global _recipe_image_map
    if _recipe_image_map is None:
        import json
        try:
            with open(os.path.join(_PROJECT_ROOT, "data", "recipe_images.json"), encoding="utf-8") as f:
                _recipe_image_map = json.load(f)
        except Exception:
            _recipe_image_map = {}
    return _recipe_image_map

def enrich_images(recipes):
    """Mirror the original app: local approved JPG → curated Unsplash map → none.
    Never keep the generic themealdb image_url (mismatched)."""
    img_map = _get_recipe_image_map()
    for r in recipes:
        rid = r.get("recipe_id", "")
        local = os.path.join(_IMAGES_DIR, f"{rid}.jpg")
        if os.path.exists(local):
            r["image_url"] = f"{_PUBLIC_BASE}/recipe-images/{rid}.jpg"
        else:
            mapped = img_map.get(rid) or ""
            r["image_url"] = mapped if "images.unsplash.com" in mapped else None
        # Add household-unit display strings (e.g. "4 ביצים") to each ingredient.
        enrich_recipe_ingredients(r)
    return recipes

MEAL_DISTRIBUTION = {
    "BREAKFAST":       0.25,
    "MORNING_SNACK":   0.10,
    "LUNCH":           0.35,
    "AFTERNOON_SNACK": 0.10,
    "DINNER":          0.20,
}

@router.get("/suggestions/{meal_type}")
def get_meal_suggestions(
    meal_type: str,
    target_calories: Optional[int] = None,
    seed: int = 0,
    user=Depends(get_current_user),
):
    """מחזיר 3 המלצות מתכון לארוחה ספציפית."""
    mgr  = get_manager()
    repo = ProfileRepository()
    prefs = repo.load(user["id"]).get("meal_preferences", {})
    allergens = prefs.get("allergies", [])
    disliked  = prefs.get("disliked_foods", [])

    if not target_calories:
        target_calories = 500

    results = mgr.recommend_meal(
        meal_type=meal_type.upper(),
        target_calories=float(target_calories),
        allergens=allergens or None,
        disliked_foods=disliked or None,
        variation_seed=seed,
    )
    enrich_images(results)
    return {"meal_type": meal_type, "recipes": results[:3]}

@router.get("/plan")
def get_daily_plan(user=Depends(get_current_user)):
    """מחזיר תוכנית יומית מלאה עם 3 הצעות לכל ארוחה."""
    from api.routers.profile import get_targets
    targets = get_targets(user)
    total_cal = targets["calories"]

    mgr  = get_manager()
    repo = ProfileRepository()
    prefs    = repo.load(user["id"]).get("meal_preferences", {})
    allergens = prefs.get("allergies", [])
    disliked  = prefs.get("disliked_foods", [])

    plan = {}
    for meal, ratio in MEAL_DISTRIBUTION.items():
        meal_cal = total_cal * ratio
        suggestions = mgr.recommend_meal(
            meal_type=meal,
            target_calories=meal_cal,
            allergens=allergens or None,
            disliked_foods=disliked or None,
        )
        plan[meal] = {
            "target_calories": round(meal_cal),
            "recipes": enrich_images(suggestions[:3]),
        }

    return {"plan": plan, "total_target": total_cal}
