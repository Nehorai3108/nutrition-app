from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter

router = APIRouter()

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = RecipeManager()
    return _manager

@router.get("/")
def search_recipes(
    q: Optional[str] = None,
    meal_type: Optional[str] = None,
    kashrut: Optional[str] = None,
    max_calories: Optional[int] = None,
    limit: int = Query(20, le=100),
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
    return {"recipes": results, "total": len(results)}

@router.get("/{recipe_id}")
def get_recipe(recipe_id: str, user=Depends(get_current_user)):
    mgr = get_manager()
    recipe = mgr.get_recipe(recipe_id)
    if not recipe:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe
