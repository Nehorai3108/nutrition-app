"""
Agent 12 — Adaptation Engine

Reads the food log and weight log to produce an adjusted daily target
and per-meal sub-targets. Implements the hybrid model from the spec:

  Layer 1 — Intra-day redistribution (remaining budget → meals left)
  Layer 3a — Weekly bank (carryover spread across remaining days)
  Layer 3b — Adaptive TDEE (weight trend recalibration, ≥14d)

Knowledge base source: planner_knowledge_base.json (June 2026)

Guardrails (NEVER negotiable):
  DAILY_FLOOR  = max(BMR, 1200F / 1500M)
  SWING        = ±15%   — max day flex from base
  CARRY_CAP    = 1× base day target  — beyond this, surplus is forgiven
  PROTEIN_FLOOR = profile target   — protected before carb/fat trim
  TDEE_STEP    = ±100 kcal/day per recalibration cycle
  TDEE_MAX_DRIFT = ±20% of formula TDEE
  ADH_MIN      = 0.80  (80% of days logged in window)
  MEAL_MIN     = 100 kcal   MEAL_MAX = 1100 kcal
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional

from nutrition_app.agents.agent_12_adaptation.adaptation_store import AdaptationStore, _monday
from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, Goal

# ── Guardrail constants ────────────────────────────────────────────────
SWING        = 0.15
CARRY_CAP_FACTOR = 1.0     # fraction of base daily target
MEAL_MIN     = 100.0
MEAL_MAX     = 1100.0
ADH_MIN      = 0.80
TDEE_STEP    = 100.0
TDEE_MAX_DRIFT = 0.20
LEARN_RATE   = 0.5
RECALIB_WINDOW = 14        # days


@dataclass
class DayTarget:
    """Adjusted daily nutrition target for today."""
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    base_calories: float
    bank_adjustment: float   # negative = we carry a surplus (eat less today)
    source: str              # "cold_start" | "weekly_bank" | "adaptive_tdee"


@dataclass
class MealSubtarget:
    meal_type: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class AdaptationEngine:

    def __init__(self):
        self._store = AdaptationStore()

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────

    def adjusted_day_target(
        self,
        user: UserProfile,
        base_targets,           # NutritionTargets from NutritionEngine
        day: Optional[date] = None,
    ) -> DayTarget:
        """
        Layer 3a: compute today's calorie target after applying the weekly bank.
        Returns a DayTarget with adjusted macros, clamped to guardrails.
        """
        day = day or date.today()
        state = self._store.get_or_init(user.user_id, base_targets.tdee_kcal)

        base_cal   = base_targets.target_calories_kcal
        floor      = self._daily_floor(user, base_targets.bmr_kcal)
        carry_cap  = base_cal * CARRY_CAP_FACTOR

        ledger = state.get("ledger", {})
        monday = _monday(day)
        elapsed_days = [
            (monday + timedelta(days=i)).isoformat()
            for i in range(day.weekday())          # days before today
        ]

        # Weekly bank: sum of (target − consumed) for elapsed days
        if not elapsed_days:
            bank_balance = 0.0
            source = "cold_start"
        else:
            bank_balance = sum(
                ledger.get(d, {}).get("balance", 0)
                for d in elapsed_days
            )
            source = "weekly_bank"

        # Cap: don't punish beyond one day's target
        bank_balance = max(-carry_cap, min(carry_cap, bank_balance))

        days_left = 7 - day.weekday()   # today + remaining days of week
        if days_left < 1:
            days_left = 1

        # Spread the residual: surplus → eat a bit less; deficit → eat a bit more
        daily_adj = -bank_balance / days_left
        today_cal = base_cal + daily_adj

        # Clamp within ±SWING and never below floor
        today_cal = max(base_cal * (1 - SWING), min(base_cal * (1 + SWING), today_cal))
        today_cal = max(floor, today_cal)

        # Use adaptive TDEE if available
        adaptive_tdee = state.get("tdee_est")
        if adaptive_tdee and abs(adaptive_tdee - base_targets.tdee_kcal) > 50:
            source = "adaptive_tdee"

        # Recompute macros preserving protein floor
        protein_g, carbs_g, fat_g = self._split_macros(
            today_cal, base_targets.protein_g, base_targets.fat_g, user.goal.value
        )

        self._store.save(user.user_id, state)
        return DayTarget(
            calories=round(today_cal),
            protein_g=round(protein_g, 1),
            carbs_g=round(carbs_g, 1),
            fat_g=round(fat_g, 1),
            base_calories=round(base_cal),
            bank_adjustment=round(daily_adj),
            source=source,
        )

    def meal_subtargets(
        self,
        user: UserProfile,
        base_targets,
        day_target: DayTarget,
        meals_logged: Dict[str, float],   # {meal_type: calories_eaten}
    ) -> List[MealSubtarget]:
        """
        Layer 1: split remaining calorie budget across meals not yet logged.
        Protein is held constant per meal; carbs/fat flex to fill the gap.
        """
        state = self._store.get_or_init(user.user_id, base_targets.tdee_kcal)
        dist  = state["learned_distribution"]

        all_meals = list(dist.keys())
        logged_meals = set(meals_logged.keys())
        remaining_meals = [m for m in all_meals if m not in logged_meals]

        eaten_so_far = sum(meals_logged.values())
        remaining_cal = max(0.0, day_target.calories - eaten_so_far)

        if not remaining_meals:
            return []

        # Relative weight of remaining meals
        remaining_weight = {m: dist.get(m, 0.20) for m in remaining_meals}
        total_weight = sum(remaining_weight.values()) or 1.0

        subtargets = []
        for meal in remaining_meals:
            share = remaining_weight[meal] / total_weight
            m_cal = remaining_cal * share

            # Clamp to realistic per-meal bounds
            m_cal = max(MEAL_MIN, min(MEAL_MAX, m_cal))

            # Protein: proportional share of day target (never trimmed)
            protein_share = dist.get(meal, 0.20)
            m_protein = day_target.protein_g * protein_share

            # Remaining calories go to carbs then fat (per goal ratio)
            rest_cal = max(0.0, m_cal - m_protein * 4)
            goal = user.goal.value
            fat_ratio = 0.30 if goal == "gain_weight" else 0.25
            m_fat   = (rest_cal * fat_ratio) / 9
            m_carbs = (rest_cal * (1 - fat_ratio)) / 4

            subtargets.append(MealSubtarget(
                meal_type=meal,
                calories=round(m_cal),
                protein_g=round(m_protein, 1),
                carbs_g=round(m_carbs, 1),
                fat_g=round(m_fat, 1),
            ))

        return subtargets

    def recalibrate_tdee(
        self,
        user: UserProfile,
        base_tdee: float,
        weight_log: List,    # List[WeightEntry]
    ) -> Optional[dict]:
        """
        Layer 3b: compare predicted vs actual weight change over ≥14 days.
        Only runs if adherence ≥ 80%. Nudges TDEE estimate by ≤±100 kcal/cycle.

        Knowledge base ref: MF-03, adaptive_tdee formula
        """
        state = self._store.get_or_init(user.user_id, base_tdee)
        adherence = state.get("adherence", {}).get("rate", 0.0)

        if adherence < ADH_MIN:
            return None

        # Need at least RECALIB_WINDOW days of weight data
        if len(weight_log) < 2:
            return None

        # Use 7-day moving average endpoints to kill water noise (KB: AT-05)
        sorted_entries = sorted(weight_log, key=lambda e: e.date)
        if len(sorted_entries) < RECALIB_WINDOW:
            return None

        # Window: last RECALIB_WINDOW days
        window = sorted_entries[-RECALIB_WINDOW:]
        n_days = RECALIB_WINDOW

        # Discard first week after any macro change (KB: discard_first_week_after_change)
        start_weight = _moving_avg(window[:7])
        end_weight   = _moving_avg(window[-7:])
        actual_delta_kg = end_weight - start_weight   # negative = lost weight

        # Pull food log totals for same window
        try:
            from nutrition_app.repositories.food_log_repository import FoodLogRepository
            repo = FoodLogRepository()
            start_date = date.fromisoformat(window[0].date)
            end_date   = date.fromisoformat(window[-1].date)
            total_consumed = 0.0
            logged_days = 0
            d = start_date
            while d <= end_date:
                totals = repo.get_totals(user.user_id, d)
                if totals.get("count", 0) > 0:
                    total_consumed += totals.get("calories", 0)
                    logged_days += 1
                d += timedelta(days=1)
        except Exception:
            return None

        if logged_days < int(n_days * ADH_MIN):
            return None

        mean_daily_intake = total_consumed / logged_days

        # Adaptive TDEE formula (KB: adaptive_tdee)
        # TDEE_est = mean_intake + (weight_change_kg * 7700 / n_days)
        tdee_empirical = mean_daily_intake + (actual_delta_kg * 7700 / n_days)
        tdee_empirical = round(tdee_empirical)

        current_est = state.get("tdee_est", base_tdee)
        diff = tdee_empirical - current_est

        if abs(diff) < 50:
            return None   # noise — don't move

        # Clamp nudge to ±TDEE_STEP per cycle (KB: TDEE_STEP)
        nudge = max(-TDEE_STEP, min(TDEE_STEP, diff * LEARN_RATE))
        new_est = current_est + nudge

        # Hard bounds: ±20% of formula TDEE (KB: TDEE_MAX_DRIFT)
        new_est = max(base_tdee * (1 - TDEE_MAX_DRIFT), min(base_tdee * (1 + TDEE_MAX_DRIFT), new_est))
        new_est = round(new_est)

        if new_est == current_est:
            return None

        # Persist
        state["tdee_est"] = new_est
        state.setdefault("recalib_history", []).append({
            "date": date.today().isoformat(),
            "old_tdee": current_est,
            "new_tdee": new_est,
            "empirical_tdee": tdee_empirical,
            "mean_intake": round(mean_daily_intake),
            "actual_delta_kg": round(actual_delta_kg, 2),
            "logged_days": logged_days,
        })
        self._store.save(user.user_id, state)

        return {
            "old_tdee": current_est,
            "new_tdee": new_est,
            "reason": f"Weight trend: {round(actual_delta_kg, 2)} kg over {n_days}d, empirical TDEE {tdee_empirical}",
        }

    def update_adherence(self, user_id: str, base_tdee: float):
        """
        Count logged days in trailing 14 days and update adherence rate.
        Call once per day when a food entry is saved.
        """
        from nutrition_app.repositories.food_log_repository import FoodLogRepository
        repo = FoodLogRepository()
        today = date.today()
        logged = 0
        for i in range(14):
            d = today - timedelta(days=i)
            t = repo.get_totals(user_id, d)
            if t.get("count", 0) > 0:
                logged += 1
        state = self._store.get_or_init(user_id, base_tdee)
        state["adherence"] = {
            "logged_days_14": logged,
            "rate": round(logged / 14, 2),
        }
        self._store.save(user_id, state)

    def record_today(self, user_id: str, base_tdee: float, target_cal: float, consumed_cal: float):
        """Persist today's entry in the weekly ledger."""
        self._store.record_day(
            user_id, date.today().isoformat(), target_cal, consumed_cal, base_tdee
        )

    def get_week_summary(self, user_id: str, base_tdee: float) -> dict:
        """Return the weekly ledger + running bank balance for display."""
        state = self._store.get_or_init(user_id, base_tdee)
        ledger = state.get("ledger", {})
        bank = sum(e.get("balance", 0) for e in ledger.values())
        return {
            "ledger": ledger,
            "bank_balance": round(bank),
            "tdee_est": state.get("tdee_est"),
            "adherence": state.get("adherence", {}),
        }

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _daily_floor(self, user: UserProfile, bmr: float) -> float:
        """DAILY_FLOOR = max(BMR, sex-based absolute floor). KB: safety_floors"""
        sex_floor = 1500.0 if user.gender.value == "male" else 1200.0
        return max(bmr, sex_floor)

    def _split_macros(
        self,
        total_cal: float,
        protein_g_target: float,
        fat_g_target: float,
        goal: str,
    ) -> tuple[float, float, float]:
        """
        Distribute total_cal into protein/carbs/fat.
        Order of priority (KB: MA-01, MA-06):
          1. Protein (floor, never trimmed)
          2. Fat (≥20% kcal hormonal floor)
          3. Carbs (remainder)
        """
        protein_kcal = protein_g_target * 4
        # Fat floor: max of profile target and 20% of total (KB: MA-06)
        fat_floor_g  = (total_cal * 0.20) / 9
        fat_g = max(fat_g_target, fat_floor_g)
        fat_kcal = fat_g * 9

        remaining = total_cal - protein_kcal - fat_kcal
        # If budget is tight, trim fat before protein
        if remaining < 0:
            fat_g = max(fat_floor_g, (total_cal - protein_kcal) / 9 * 0.5)
            fat_kcal = fat_g * 9
            remaining = max(0.0, total_cal - protein_kcal - fat_kcal)

        carbs_g = remaining / 4
        return protein_g_target, max(0.0, carbs_g), fat_g


def _moving_avg(entries) -> float:
    if not entries:
        return 0.0
    return sum(e.weight_kg for e in entries) / len(entries)
