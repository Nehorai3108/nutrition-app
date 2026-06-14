from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter
from nutrition_app.agents.agent_11_recipes.unit_converter import enrich_recipe_ingredients

router = APIRouter()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# Base URL the CLIENT uses to reach this server. On a phone "localhost" is the phone
# itself, so when serving to devices we set PUBLIC_BASE_URL to the PC's LAN IP.
_PUBLIC_BASE = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = RecipeManager()
    return _manager

# Curated recipe_id → image URL map (same source the original Streamlit app uses
# as fallback after the local approved JPG: data/recipe_images.json — Unsplash URLs).
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

@router.get("/")
def search_recipes(
    q: Optional[str] = None,
    meal_type: Optional[str] = None,
    kashrut: Optional[str] = None,
    max_calories: Optional[int] = None,
    limit: int = Query(300, le=500),
    user=Depends(get_current_user),
):
    mgr = get_manager()
    f = RecipeFilter(
        search_text=q,
        meal_types=[meal_type] if meal_type else None,
        kashrut=kashrut,
        calorie_max=max_calories,
        max_results=limit,
    )
    results = mgr.search_recipes(f)
    # Mirror the original Streamlit app's image priority exactly:
    #   1. Local curated approved JPG  (best — actually matches the recipe)
    #   2. data/recipe_images.json     (curated Unsplash URL per recipe_id)
    # Never use the generic themealdb image_url baked into recipes.json — those are
    # mismatched. No image at all → client shows a clean placeholder.
    images_dir = os.path.join(_PROJECT_ROOT, "storage_agents", "recipe_images", "approved")
    img_map = _get_recipe_image_map()
    for r in results:
        rid = r.get("recipe_id", "")
        local = os.path.join(images_dir, f"{rid}.jpg")
        if os.path.exists(local):
            r["image_url"] = f"{_PUBLIC_BASE}/recipe-images/{rid}.jpg"
        else:
            mapped = img_map.get(rid) or ""
            # Only keep sources that actually load & look relevant. Skip the dead
            # source.unsplash.com service and the generic/mismatched themealdb photos.
            r["image_url"] = mapped if "images.unsplash.com" in mapped else None
        enrich_recipe_ingredients(r)
    return {"recipes": results, "total": len(results)}

@router.get("/{recipe_id}")
def get_recipe(recipe_id: str, user=Depends(get_current_user)):
    mgr = get_manager()
    recipe = mgr.get_recipe(recipe_id)
    if not recipe:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Recipe not found")
    enrich_recipe_ingredients(recipe)
    return recipe
