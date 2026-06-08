from fastapi import APIRouter, Depends, Query
from typing import Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.repositories.profile_repository import ProfileRepository

router = APIRouter()

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = RecipeManager()
    return _manager

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
            "recipes": suggestions[:3],
        }

    return {"plan": plan, "total_target": total_cal}
