"""
SQLAlchemy ORM models — destination schema for the Supabase Postgres
migration.

Multi-user contract (from ``storage_audit/data_layer_audit.md``):

* User-scoped tables carry a ``user_id`` string column. It is **indexed** and
  **NOT NULL** for tables that are exclusively per-user (inventory, food log,
  daily summaries, water, workouts, plans, profiles).
* The shared catalog tables (``foods``, ``recipes``, ``recipe_ingredients``)
  add a **nullable** ``user_id`` — a NULL value means "global catalog row";
  a non-null value means "this user's custom override".
* ``run_logs`` is a system table; it has no ``user_id`` filter requirement
  but the actual user that triggered the run is recorded for traceability.
* No SQL foreign key is declared against ``auth.users`` — that table lives in
  Supabase's ``auth`` schema, not in ``public``, so a public-schema FK would
  fail at create time.

All datetimes are timezone-aware (UTC) on Postgres. SQLite stores them as
ISO strings transparently.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# ──────────────────────────────────────────────────────────────────────────────
# Shared catalog tables (user_id nullable: NULL = global, non-null = custom)
# ──────────────────────────────────────────────────────────────────────────────


class Food(Base):
    __tablename__ = "foods"

    food_id: Mapped[str] = mapped_column(String, primary_key=True)
    name_he: Mapped[str] = mapped_column(String, nullable=False)
    name_en: Mapped[str] = mapped_column(String, nullable=False, default="")
    category: Mapped[str] = mapped_column(String, nullable=False, default="other")
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sugar_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sodium_mg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    default_unit: Mapped[str] = mapped_column(String, nullable=False, default="gram")
    default_serving_g: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    aliases_he: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aliases_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="catalog")
    # NULL = shared catalog; non-NULL = user's custom food.
    user_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Recipe(Base):
    __tablename__ = "recipes"

    recipe_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_calories_kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    per_serving_calories_kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    per_serving_protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    per_serving_carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    per_serving_fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    per_serving_fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unresolved_ingredients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="catalog")
    # NULL = shared catalog; non-NULL = user's recipe.
    user_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    ingredient_id: Mapped[str] = mapped_column(String, primary_key=True)
    recipe_id: Mapped[str] = mapped_column(
        String, ForeignKey("recipes.recipe_id", ondelete="CASCADE"), index=True
    )
    food_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name_he: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name_en: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    # No user_id: scoping inherits via recipe_id → recipes.user_id.


# ──────────────────────────────────────────────────────────────────────────────
# System table (run metadata) — no user filter requirement
# ──────────────────────────────────────────────────────────────────────────────


class RunLog(Base):
    __tablename__ = "run_logs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_saved: Mapped[int] = mapped_column(Integer, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")


# ──────────────────────────────────────────────────────────────────────────────
# User-scoped tables (user_id NOT NULL, indexed)
# ──────────────────────────────────────────────────────────────────────────────


class Profile(Base):
    __tablename__ = "profiles"

    # user_id is both the PK and the scoping column for this table.
    user_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    activity_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    goal: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meal_preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class FoodLogEntryORM(Base):
    __tablename__ = "food_log"

    entry_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    date: Mapped[str] = mapped_column(String, index=True, nullable=False)
    food_id: Mapped[str] = mapped_column(String, nullable=False)
    food_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    grams: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    meal_type: Mapped[str] = mapped_column(String, nullable=False, default="lunch")
    timestamp: Mapped[str] = mapped_column(String, nullable=False, default="")

    __table_args__ = (
        Index("ix_food_log_user_date", "user_id", "date"),
    )


class InventoryItemORM(Base):
    __tablename__ = "inventory_items"

    inventory_item_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    food_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String, nullable=False, default="gram")
    expiry_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class InventoryChangeORM(Base):
    __tablename__ = "inventory_changelog"

    change_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    inventory_item_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    food_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    quantity_before: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quantity_after: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quantity_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    run_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailySummaryORM(Base):
    __tablename__ = "daily_summaries"

    summary_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    date: Mapped[str] = mapped_column(String, index=True, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_daily_summary_user_date", "user_id", "date", unique=True),
    )


class WaterIntakeORM(Base):
    __tablename__ = "water_intakes"

    water_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, index=True, nullable=False)
    amount_ml: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String, nullable=False, default="water")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WaterGoalORM(Base):
    __tablename__ = "water_goals"

    # One goal per user.
    user_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    daily_goal_ml: Mapped[float] = mapped_column(Float, nullable=False, default=2000.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WorkoutEntryORM(Base):
    __tablename__ = "workouts"

    workout_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    date: Mapped[str] = mapped_column(String, index=True, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mode: Mapped[str] = mapped_column(String, nullable=False, default="intensity")
    intensity: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    workout_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_calories_burned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WeeklyWorkoutPlanORM(Base):
    __tablename__ = "weekly_workout_plans"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserORM(Base):
    """Lightweight user registry (mirrors ``storage_agents/users.json``).

    Note: real authentication lives in Supabase's ``auth.users`` table. This
    table is the application-side mirror so we can list users in admin views
    without a cross-schema query.
    """

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MealPlanORM(Base):
    """Saved meal plans, segregated by user_id.

    Previously stored as flat timestamped files in ``storage_agents/plans/``
    — see the audit's "plans/ directory not namespaced" migration note.
    """

    __tablename__ = "meal_plans"

    plan_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ArtifactORM(Base):
    """Per-user artifact metadata (counterpart to ``storage/artifacts/``)."""

    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    run_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
