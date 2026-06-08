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
    total = repo.get_total(user["id"], d)
    goal  = repo.get_goal(user["id"])
    return {"date": date_str, "total_ml": total, "goal_ml": goal}

@router.post("/")
def add_water(body: AddWater, user=Depends(get_current_user)):
    from datetime import datetime
    d = date.fromisoformat(body.date) if body.date else date.today()
    repo.add_entry(user["id"], d, body.amount_ml)
    return {"ok": True}
