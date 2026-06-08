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

@router.get("/targets")
def get_targets(user=Depends(get_current_user)):
    """מחזיר יעדי קלוריות ומאקרו מחושבים."""
    from nutrition_app.agents.agent_2_nutrition import NutritionEngine
    from nutrition_app.models.user import UserProfile
    from nutrition_app.models.enums import Gender, ActivityLevel, Goal
    from datetime import date

    repo = ProfileRepository()
    p = repo.load(user["id"])
    if not p.get("weight_kg"):
        return {"calories": 2000, "protein": 150, "carbs": 250, "fat": 67}

    try:
        profile = UserProfile(
            user_id=user["id"],
            name=p.get("name",""),
            gender=Gender(p.get("gender","male")),
            date_of_birth=date.fromisoformat(p.get("date_of_birth","1990-01-01")),
            height_cm=float(p.get("height_cm",170)),
            weight_kg=float(p.get("weight_kg",70)),
            activity_level=ActivityLevel(p.get("activity_level","moderately_active")),
            goal=Goal(p.get("goal","maintain")),
        )
        engine = NutritionEngine()
        targets = engine.calculate_targets(profile)
        return {
            "calories": round(targets.calories_kcal),
            "protein":  round(targets.protein_g),
            "carbs":    round(targets.carbs_g),
            "fat":      round(targets.fat_g),
        }
    except Exception:
        return {"calories": 2000, "protein": 150, "carbs": 250, "fat": 67}
