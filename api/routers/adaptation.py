"""
/adaptation  — Adaptation Engine API

Endpoints:
  GET  /adaptation/day-target          adjusted daily target (Layer 3a)
  GET  /adaptation/meal-subtargets     remaining meal sub-targets (Layer 1)
  POST /adaptation/record-day          write today's intake to weekly ledger
  GET  /adaptation/week-summary        weekly bank + ledger
  POST /adaptation/recalibrate-tdee    trigger Layer 3b TDEE recalibration
  GET  /adaptation/adherence           update + return logging adherence
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict
from api.deps import get_current_user

router = APIRouter()


def _get_user_profile(user_id: str):
    """Build a UserProfile domain object; returns None if no profile saved."""
    from nutrition_app.repositories.profile_repository import ProfileRepository
    from api.routers.profile import build_user_profile
    p = ProfileRepository().load(user_id)
    if not p.get("weight_kg"):
        return None
    return build_user_profile(p, user_id)


def _get_base_targets(profile):
    """Base targets honoring the user's target-weight + timeline (weekly rate)."""
    from api.routers.profile import compute_targets
    return compute_targets(profile.user_id)


# ── GET /adaptation/day-target ────────────────────────────────────────
@router.get("/day-target")
def get_day_target(user=Depends(get_current_user)):
    """
    Returns today's adjusted calorie + macro target after applying the weekly bank.
    Layer 3a of the Adaptation Engine.
    """
    from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
    profile = _get_user_profile(user["id"])
    if not profile:
        return {"error": "profile not found"}

    base = _get_base_targets(profile)
    engine = AdaptationEngine()
    target = engine.adjusted_day_target(profile, base)

    return {
        "calories":        target.calories,
        "protein_g":       target.protein_g,
        "carbs_g":         target.carbs_g,
        "fat_g":           target.fat_g,
        "base_calories":   target.base_calories,
        "bank_adjustment": target.bank_adjustment,
        "source":          target.source,
        "bmr":             round(base.bmr_kcal),
        "tdee":            round(base.tdee_kcal),
    }


# ── GET /adaptation/meal-subtargets ──────────────────────────────────
@router.get("/meal-subtargets")
def get_meal_subtargets(user=Depends(get_current_user)):
    """
    Layer 1: returns per-meal calorie + macro sub-targets for meals not yet logged today.
    """
    from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
    from nutrition_app.repositories.food_log_repository import FoodLogRepository
    from api._tz import today_il

    profile = _get_user_profile(user["id"])
    if not profile:
        return {"error": "profile not found"}

    base   = _get_base_targets(profile)
    engine = AdaptationEngine()
    target = engine.adjusted_day_target(profile, base)

    # What's already been eaten today, grouped by meal type
    entries = FoodLogRepository().get_log(user["id"], today_il())
    meals_logged: Dict[str, float] = {}
    for e in entries:
        mt = (e.meal_type or "lunch").lower()
        meals_logged[mt] = meals_logged.get(mt, 0.0) + (e.calories or 0)

    subtargets = engine.meal_subtargets(profile, base, target, meals_logged)

    return {
        "day_target":   target.calories,
        "eaten_so_far": round(sum(meals_logged.values())),
        "remaining":    round(target.calories - sum(meals_logged.values())),
        "subtargets": [
            {
                "meal_type":  s.meal_type,
                "calories":   s.calories,
                "protein_g":  s.protein_g,
                "carbs_g":    s.carbs_g,
                "fat_g":      s.fat_g,
            }
            for s in subtargets
        ],
    }


# ── POST /adaptation/record-day ───────────────────────────────────────
class RecordDayBody(BaseModel):
    consumed_calories: float

@router.post("/record-day")
def record_day(body: RecordDayBody, user=Depends(get_current_user)):
    """
    Write today's consumed calories into the weekly ledger.
    Call this at end-of-day (or on-demand from the app).
    """
    from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
    profile = _get_user_profile(user["id"])
    if not profile:
        return {"error": "profile not found"}

    base   = _get_base_targets(profile)
    engine = AdaptationEngine()
    target = engine.adjusted_day_target(profile, base)
    engine.record_today(user["id"], base.tdee_kcal, target.calories, body.consumed_calories)
    engine.update_adherence(user["id"], base.tdee_kcal)

    balance = target.calories - body.consumed_calories
    return {
        "recorded":    True,
        "target":      target.calories,
        "consumed":    round(body.consumed_calories),
        "balance":     round(balance),
        "note": "surplus" if balance < 0 else "deficit" if balance > 50 else "on_target",
    }


# ── GET /adaptation/week-summary ──────────────────────────────────────
@router.get("/week-summary")
def week_summary(user=Depends(get_current_user)):
    """
    Returns the weekly ledger, running bank balance, adaptive TDEE, and adherence.
    """
    from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
    profile = _get_user_profile(user["id"])
    if not profile:
        return {"error": "profile not found"}

    base = _get_base_targets(profile)
    engine = AdaptationEngine()
    return engine.get_week_summary(user["id"], base.tdee_kcal)


# ── POST /adaptation/recalibrate-tdee ────────────────────────────────
@router.post("/recalibrate-tdee")
def recalibrate_tdee(user=Depends(get_current_user)):
    """
    Layer 3b: compare predicted vs actual weight trend over ≥14d.
    Updates adaptive TDEE estimate if adherence ≥ 80%.
    """
    from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
    from nutrition_app.repositories.weight_repository import WeightRepository

    profile = _get_user_profile(user["id"])
    if not profile:
        return {"error": "profile not found"}

    base       = _get_base_targets(profile)
    weight_log = WeightRepository().get_log(user["id"])
    engine     = AdaptationEngine()
    result     = engine.recalibrate_tdee(profile, base.tdee_kcal, weight_log)

    if result is None:
        state = engine._store.get_or_init(user["id"], base.tdee_kcal)
        adh = state.get("adherence", {}).get("rate", 0)
        return {
            "updated": False,
            "reason": "insufficient data or low adherence" if adh < 0.80
                      else "TDEE estimate stable (diff < 50 kcal)",
            "adherence_rate": adh,
            "weight_entries": len(weight_log),
        }

    return {"updated": True, **result}


# ── GET /adaptation/adherence ─────────────────────────────────────────
@router.get("/adherence")
def get_adherence(user=Depends(get_current_user)):
    """Returns current logging adherence (trailing 14 days)."""
    from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
    profile = _get_user_profile(user["id"])
    if not profile:
        return {"error": "profile not found"}

    base   = _get_base_targets(profile)
    engine = AdaptationEngine()
    engine.update_adherence(user["id"], base.tdee_kcal)
    state  = engine._store.get_or_init(user["id"], base.tdee_kcal)
    return state.get("adherence", {})
