#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
water_repository.py — ניהול נתוני צריכת מים למשתמש
"""

import os
import json
from typing import Optional, List
from datetime import datetime, timedelta

from nutrition_app.models.water import WaterIntake, WaterGoal, UserWaterData


class WaterRepository:
    """
    Repository for managing user water intake data.

    Stores per-user water data in JSON files:
    `storage_agents/water/{user_id}.json`

    Follows the same pattern as WorkoutRepository.
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the water repository.

        Args:
            base_dir: Base directory for water storage (default: storage_agents/users/<id>/water.json)
        """
        if base_dir is None:
            self.base_dir = None
            self._use_per_user_dirs = True
        else:
            self.base_dir = base_dir
            self._use_per_user_dirs = False
            os.makedirs(self.base_dir, exist_ok=True)

    def _get_filepath(self, user_id: str) -> str:
        """Get the file path for a user's water data."""
        if self._use_per_user_dirs:
            from nutrition_app.storage_paths import user_water_file
            return str(user_water_file(user_id))
        return os.path.join(self.base_dir, f"{user_id}.json")

    def _load_file(self, user_id: str) -> Optional[dict]:
        """Load water data from file."""
        filepath = self._get_filepath(user_id)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_file(self, user_id: str, data: dict) -> None:
        """Save water data to file."""
        filepath = self._get_filepath(user_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_water_data(self, user_id: str) -> UserWaterData:
        """
        Get complete water data for a user.

        If no data exists, creates default with 2L daily goal.

        Args:
            user_id: User identifier

        Returns:
            UserWaterData object with all water intake history and goal
        """
        data = self._load_file(user_id)

        if data is None:
            # Create default water data
            return UserWaterData(
                user_id=user_id,
                daily_log={},
                goal=WaterGoal(user_id=user_id, daily_goal_ml=2000.0),
            )

        return UserWaterData.from_dict(data)

    def save_water_data(self, water_data: UserWaterData) -> None:
        """Save complete water data for a user."""
        self._save_file(water_data.user_id, water_data.to_dict())

    def save_water_goal(self, user_id: str, daily_goal_ml: float) -> WaterGoal:
        """
        Update or create a water goal.

        Args:
            user_id: User identifier
            daily_goal_ml: Daily water goal in milliliters

        Returns:
            Updated WaterGoal
        """
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
        """
        Add a water intake entry.

        Args:
            user_id: User identifier
            amount_ml: Amount in milliliters
            timestamp: ISO 8601 timestamp (default: now)
            source: Source of water (e.g., "bottle", "cup")
            notes: Optional notes

        Returns:
            Created WaterIntake object
        """
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
        """
        Remove a water intake entry.

        Args:
            user_id: User identifier
            water_id: Water intake ID to remove
            date_str: Date in format YYYY-MM-DD

        Returns:
            True if removed, False if not found
        """
        water_data = self.get_water_data(user_id)
        success = water_data.remove_intake(water_id, date_str)
        if success:
            self.save_water_data(water_data)
        return success

    def get_daily_total(self, user_id: str, date_obj) -> float:
        """
        Get total water intake for a specific date.

        Args:
            user_id: User identifier
            date_obj: datetime.date object

        Returns:
            Total water in milliliters for the day
        """
        water_data = self.get_water_data(user_id)
        date_str = date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj)
        return water_data.get_daily_total(date_str)

    def get_week_total(self, user_id: str, end_date_obj) -> float:
        """
        Get total water intake for the week ending on end_date.

        Args:
            user_id: User identifier
            end_date_obj: datetime.date object (end of week, inclusive)

        Returns:
            Total water in milliliters for the 7-day period
        """
        water_data = self.get_water_data(user_id)
        date_str = end_date_obj.isoformat() if hasattr(end_date_obj, "isoformat") else str(end_date_obj)
        return water_data.get_week_total(date_str)

    def get_water_intakes_for_date(self, user_id: str, date_obj) -> List[WaterIntake]:
        """
        Get all water intakes for a specific date.

        Args:
            user_id: User identifier
            date_obj: datetime.date object

        Returns:
            List of WaterIntake objects for the day (sorted by timestamp)
        """
        water_data = self.get_water_data(user_id)
        date_str = date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj)
        return water_data.get_intakes_for_date(date_str)

    def get_water_intakes_for_period(
        self, user_id: str, start_date_obj, end_date_obj
    ) -> List[WaterIntake]:
        """
        Get all water intakes for a date range.

        Args:
            user_id: User identifier
            start_date_obj: Start date (datetime.date)
            end_date_obj: End date (datetime.date, inclusive)

        Returns:
            List of WaterIntake objects, sorted by timestamp (newest first)
        """
        water_data = self.get_water_data(user_id)
        intakes = []

        current_date = start_date_obj
        while current_date <= end_date_obj:
            date_str = current_date.isoformat() if hasattr(current_date, "isoformat") else str(current_date)
            intakes.extend(water_data.get_intakes_for_date(date_str))
            current_date += timedelta(days=1)

        # Sort by timestamp, newest first
        intakes.sort(key=lambda x: x.timestamp, reverse=True)
        return intakes

    def get_water_goal(self, user_id: str) -> WaterGoal:
        """
        Get the current water goal for a user.

        Args:
            user_id: User identifier

        Returns:
            WaterGoal object
        """
        water_data = self.g