"""
AdaptationStore — persistence layer for the Adaptation Engine.

Stores per-user weekly ledger, learned TDEE, adherence stats, and
meal-distribution history in storage_agents/adaptation/{user_id}.json.
"""
from __future__ import annotations
import json, os
from datetime import date, timedelta
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_DIR  = os.path.join(_ROOT, "storage_agents", "adaptation")


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


class AdaptationStore:
    def _path(self, user_id: str) -> str:
        os.makedirs(_DIR, exist_ok=True)
        return os.path.join(_DIR, f"{user_id}.json")

    def load(self, user_id: str) -> dict:
        p = self._path(user_id)
        if not os.path.exists(p):
            return {}
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, user_id: str, state: dict):
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def get_or_init(self, user_id: str, base_tdee: float) -> dict:
        state = self.load(user_id)
        today = date.today()
        anchor = _monday(today).isoformat()

        # Re-anchor if new week
        if state.get("week_anchor") != anchor:
            state["week_anchor"] = anchor
            state["ledger"] = {}

        if "tdee_est" not in state:
            state["tdee_est"] = round(base_tdee)
        if "adherence" not in state:
            state["adherence"] = {"logged_days_14": 0, "rate": 0.0}
        if "learned_distribution" not in state:
            # Default: 25 / 10 / 35 / 10 / 20  (matches meal_planner.py)
            state["learned_distribution"] = {
                "breakfast": 0.25, "morning_snack": 0.10,
                "lunch": 0.35, "afternoon_snack": 0.10, "dinner": 0.20,
            }
        if "recalib_history" not in state:
            state["recalib_history"] = []
        return state

    def record_day(self, user_id: str, day: str, target: float, consumed: float, base_tdee: float):
        """Write today's entry into the weekly ledger."""
        state = self.get_or_init(user_id, base_tdee)
        state["ledger"][day] = {
            "target": round(target),
            "consumed": round(consumed),
            "balance": round(target - consumed),   # +surplus / -deficit
        }
        self.save(user_id, state)

    def update_learned_distribution(self, user_id: str, meal_type: str, actual_pct: float, base_tdee: float):
        """Smooth the learned meal distribution with EMA (alpha=0.2)."""
        state = self.get_or_init(user_id, base_tdee)
        dist = state["learned_distribution"]
        old = dist.get(meal_type, 0.20)
        dist[meal_type] = round(old * 0.8 + actual_pct * 0.2, 4)
        # Re-normalize
        total = sum(dist.values()) or 1
        state["learned_distribution"] = {k: round(v / total, 4) for k, v in dist.items()}
        self.save(user_id, state)
