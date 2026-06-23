from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.repositories.profile_repository import ProfileRepository

router = APIRouter()

@router.get("/")
def get_profile(user=Depends(get_current_user)):
    repo = ProfileRepository()
    return repo.load(user["id"])

@router.put("/")
def save_profile(data: dict, user=Depends(get_current_user)):
    repo = ProfileRepository()
    data["user_id"] = user["id"]
    repo.save(data)
    return {"ok": True}

@router.get("/usage")
def get_usage(user=Depends(get_current_user)):
    """מצב מכסת השימוש היומית (לתצוגה באפליקציה) — צילומים וצ'אט."""
    from api.usage import check, get_tier
    return {
        "tier":   get_tier(user["id"]),
        "camera": check(user["id"], "camera"),
        "chat":   check(user["id"], "chat"),
    }

def build_user_profile(p: dict, user_id: str):
    """Build a UserProfile domain object from a raw profile dict."""
    from nutrition_app.models.user import UserProfile
    from nutrition_app.models.enums import Gender, ActivityLevel, Goal
    from datetime import date
    return UserProfile(
        user_id=user_id,
        name=p.get("name", ""),
        gender=Gender(p.get("gender", "male")),
        date_of_birth=date.fromisoformat(p.get("date_of_birth", "1990-01-01")),
        height_cm=float(p.get("height_cm", 170)),
        weight_kg=float(p.get("weight_kg", 70)),
        activity_level=ActivityLevel(p.get("activity_level", "moderately_active")),
        goal=Goal(p.get("goal", "maintain")),
    )


def derive_weekly_change_kg(p: dict):
    """
    From target weight + timeline, derive kg/week so the deficit/surplus
    reflects the user's actual plan (not a fixed pace). Returns None if not set.
    """
    target_weight = p.get("target_weight") or p.get("target_weight_kg")
    weeks = p.get("weeks_to_goal")
    try:
        if target_weight and weeks and float(weeks) > 0:
            delta = abs(float(target_weight) - float(p.get("weight_kg") or 0))
            if delta > 0:
                return delta / float(weeks)
    except (TypeError, ValueError):
        pass
    return None


def compute_targets(user_id: str):
    """
    Shared base-target computation used by /profile/targets, /daily-menu, and
    the adaptation engine. Returns a NutritionTargets object (or None).
    """
    from nutrition_app.agents.agent_2_nutrition import NutritionEngine
    repo = ProfileRepository()
    p = repo.load(user_id)
    if not p.get("weight_kg"):
        return None

    profile = build_user_profile(p, user_id)
    weekly_change_kg = derive_weekly_change_kg(p)
    target_weight = p.get("target_weight") or p.get("target_weight_kg")

    return NutritionEngine().calculate_targets(
        profile,
        weekly_change_kg=weekly_change_kg,
        target_weight_kg=float(target_weight) if target_weight else None,
    )


@router.get("/targets")
def get_targets(user=Depends(get_current_user)):
    """מחזיר יעדי קלוריות ומאקרו מחושבים."""
    try:
        targets = compute_targets(user["id"])
        if targets is None:
            return {"calories": 2000, "protein": 150, "carbs": 250, "fat": 67}
        # echo the planning inputs so the client/diagnostics can confirm the
        # target weight + timeline were actually picked up
        p = ProfileRepository().load(user["id"])
        return {
            "calories": round(targets.target_calories_kcal),
            "protein":  round(targets.protein_g),
            "carbs":    round(targets.carbs_g),
            "fat":      round(targets.fat_g),
            "tdee":     round(targets.tdee_kcal),
            "bmr":      round(targets.bmr_kcal),
            "target_weight": p.get("target_weight") or p.get("target_weight_kg"),
            "weeks_to_goal": p.get("weeks_to_goal"),
            "weekly_change_kg": round(derive_weekly_change_kg(p), 3) if derive_weekly_change_kg(p) else None,
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"calories": 2000, "protein": 150, "carbs": 250, "fat": 67, "error": str(e)}
