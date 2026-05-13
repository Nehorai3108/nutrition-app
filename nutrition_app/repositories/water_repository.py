#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
water_repository.py — ניהול נתוני צריכת מים למשתמש

Supports two backends:
  • Supabase (cloud)  — when SUPABASE_URL / SUPABASE_ANON_KEY are in secrets
  • Local JSON files  — fallback for local development
"""

import os
import json
import re
from typing import Optional, List
from datetime import datetime, timedelta

from nutrition_app.models.water import WaterIntake, WaterGoal, UserWaterData


_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)


class WaterRepository:
    """
    Repository for managing user water intake data.

    Auto-selects backend:
      - Supabase when credentials present in st.secrets AND user_id is a UUID
      - Local JSON (storage_agents/water/{user_id}.json) otherwise
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "storage_agents",
                "water",
            )
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    # ── Backend selector ──────────────────────────────────────────────────────

    def _use_supabase(self, user_id: str = "") -> bool:
        if not _UUID_RE.match((user_id or "").lower()):
            return False
        try:
            from nutrition_app.db.supabase_client import is_supabase_configured
            return is_supabase_configured()
        except Exception:
            return False

    def _sb(self):
        from nutrition_app.db.supabase_client import get_supabase
        return get_supabase()

    # ── Supabase backend ──────────────────────────────────────────────────────

    def _sb_load(self, user_id: str) -> Optional[dict]:
        rows = (
            self._sb().table("water_data")
            .select("data").eq("user_id", user_id).limit(1).execute()
        ).data
        if rows:
            return rows[0]["data"]
        return None

    def _sb_save(self, user_id: str, data: dict) -> None:
        self._sb().table("water_data").upsert(
            {"user_id": user_id, "data": data, "updated_at": datetime.now().isoformat()},
            on_conflict="user_id"
        ).execute()

    # ── Local JSON backend ────────────────────────────────────────────────────

    def _get_filepath(self, user_id: str) -> str:
        return os.path.join(self.base_dir, f"{user_id}.json")

    def _load_file(self, user_id: str) -> Optional[dict]:
        filepath = self._get_filepath(user_id)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_file(self, user_id: str, data: dict) -> None:
        filepath = self._get_filepath(user_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_water_data(self, user_id: str) -> UserWaterData:
        if self._use_supabase(user_id):
            raw = self._sb_load(user_id)
        else:
            raw = self._load_file(user_id)

        if raw is None:
            return UserWaterData(
                user_id=user_id,
                daily_log={},
                goal=WaterGoal(user_id=user_id, daily_goal_ml=2000.0),
            )
        return UserWaterData.from_dict(raw)

    def save_water_data(self, water_data: UserWaterData) -> None:
        data_dict = water_data.to_dict()
        if self._use_supabase(water_data.user_id):
            self._sb_save(water_data.user_id, data_dict)
        else:
            self._save_file(water_data.user_id, data_dict)

    def save_water_goal(self, user_id: str, daily_goal_ml: float) -> WaterGoal:
        water_data = self.get_water_data(user_id)
        water_data.goal = WaterGoal(
            user_id=user_id,
            daily_goal_ml=daily_goal_ml,
            created_at=water_data.goal.created_at if water_data.goal else datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        self.save_water_data(water_data)
        return water_data.goal

    def add_water_intake(
        self,
        user_id: str,
        amount_ml: float,
        timestamp: Optional[str] = None,
        source: str = "water",
        notes: Optional[str] = None,
    ) -> WaterIntake:
        water_data = self.get_water_data(user_id)
        intake = WaterIntake.create(
            user_id=user_id,
            amount_ml=amount_ml,
            timestamp=timestamp,
            source=source,
            notes=notes,
        )
        water_data.add_intake(intake)
        self.save_water_data(water_data)
        return intake

    def remove_water_intake(self, user_id: str, water_id: str, date_str: str) -> bool:
        water_data = self.get_water_data(user_id)
        success = water_data.remove_intake(water_id, date_str)
        if success:
            self.save_water_data(water_data)
        return success

    def get_daily_total(self, user_id: str, date_obj) -> float:
        water_data = self.get_water_data(user_id)
        date_str = date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj)
        return water_data.get_daily_total(date_str)

    def get_week_total(self, user_id: str, end_date_obj) -> float:
        water_data = self.get_water_data(user_id)
        date_str = end_date_obj.isoformat() if hasattr(end_date_obj, "isoformat") else str(end_date_obj)
        return water_data.get_week_total(date_str)

    def get_water_intakes_for_date(self, user_id: str, date_obj) -> List[WaterIntake]:
        water_data = self.get_water_data(user_id)
        date_str = date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj)
        return water_data.get_intakes_for_date(date_str)

    def get_water_intakes_for_period(
        self, user_id: str, start_date_obj, end_date_obj
    ) -> List[WaterIntake]:
        water_data = self.get_water_data(user_id)
        intakes = []
        current_date = start_date_obj
        while current_date <= end_date_obj:
            date_str = current_date.isoformat() if hasattr(current_date, "isoformat") else str(current_date)
            intakes.extend(water_data.get_intakes_for_date(date_str))
            current_date += timedelta(days=1)
        intakes.sort(key=lambda x: x.timestamp, reverse=True)
        return intakes

    def get_water_goal(self, user_id: str) -> WaterGoal:
        water_data = self.get_water_data(user_id)
        return water_data.goal or WaterGoal(user_id=user_id, daily_goal_ml=2000.0)
