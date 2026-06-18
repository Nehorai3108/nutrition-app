from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.repositories.water_repository import WaterRepository

router = APIRouter()
repo = WaterRepository()

class AddWater(BaseModel):
    amount_ml: int
    date: str = None

@router.get("/{date_str}")
def get_water(date_str: str, user=Depends(get_current_user)):
    d = date.fromisoformat(date_str)
    total = repo.get_daily_total(user["id"], d)
    goal  = repo.get_water_goal(user["id"]).daily_goal_ml
    return {"date": date_str, "total_ml": round(total), "goal_ml": round(goal)}

@router.post("/")
def add_water(body: AddWater, user=Depends(get_current_user)):
    from datetime import datetime
    repo.add_water_intake(user["id"], body.amount_ml)
    return {"ok": True}
