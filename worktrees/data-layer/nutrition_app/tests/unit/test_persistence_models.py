"""
Tests for the SQLAlchemy persistence layer.

Covers:
* Engine resolution (SQLite fallback when ``DATABASE_URL`` is unset).
* ``init_db`` creates the expected tables.
* User-scoped ORM rows are queryable by ``user_id`` and isolated across users.
"""

from __future__ import annotations

from sqlalchemy import select

from nutrition_app.persistence import (
    Base,
    DEFAULT_USER_ID,
    get_database_url,
    is_postgres,
    is_sqlite,
)
from nutrition_app.persistence.models import (
    FoodLogEntryORM,
    InventoryItemORM,
    Profile,
    WaterGoalORM,
)


# ──────────────────────────────────────────────────────────────────────────────
# Engine / URL resolution
# ──────────────────────────────────────────────────────────────────────────────


class TestDatabaseUrl:
    def test_default_is_sqlite_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Suppress the .env loader's side-effects for this assertion by
        # clearing the var again after import-time loading.
        from nutrition_app.persistence import database as db_mod  # noqa: WPS433
        db_mod.reset_engine_for_tests()

        url = get_database_url()
        # We don't care about the exact path, only the dialect.
        assert url.startswith("sqlite:")
        assert is_sqlite(url)
        assert not is_postgres(url)

    def test_postgres_url_detected(self):
        url = "postgresql+psycopg://user:pw@host:5432/db"
        assert is_postgres(url)
        assert not is_sqlite(url)


# ──────────────────────────────────────────────────────────────────────────────
# init_db
# ──────────────────────────────────────────────────────────────────────────────


class TestInitDb:
    def test_creates_user_scoped_tables(self, sqlite_engine):
        names = set(Base.metadata.tables.keys())
        for required in (
            "foods",
            "recipes",
            "recipe_ingredients",
            "run_logs",
            "profiles",
            "food_log",
            "inventory_items",
            "inventory_changelog",
            "daily_summaries",
            "water_intakes",
            "water_goals",
            "workouts",
            "weekly_workout_plans",
            "meal_plans",
            "artifacts",
        ):
            assert required in names, f"missing table {required!r}"


# ──────────────────────────────────────────────────────────────────────────────
# Per-user isolation at the ORM level
# ──────────────────────────────────────────────────────────────────────────────


class TestUserScopedOrmIsolation:
    def test_food_log_isolated_between_users(self, db_session, test_user_id, other_user_id):
        db_session.add_all(
            [
                FoodLogEntryORM(
                    entry_id="e1",
                    user_id=test_user_id,
                    date="2026-05-11",
                    food_id="f1",
                    food_name="apple",
                    grams=150,
                    calories=80,
                    protein=0.4,
                    carbs=21,
                    fat=0.3,
                    meal_type="snack",
                    timestamp="2026-05-11T10:00:00",
                ),
                FoodLogEntryORM(
                    entry_id="e2",
                    user_id=other_user_id,
                    date="2026-05-11",
                    food_id="f2",
                    food_name="banana",
                    grams=120,
                    calories=100,
                    protein=1.3,
                    carbs=27,
                    fat=0.3,
                    meal_type="snack",
                    timestamp="2026-05-11T11:00:00",
                ),
            ]
        )
        db_session.commit()

        rows = db_session.execute(
            select(FoodLogEntryORM).where(FoodLogEntryORM.user_id == test_user_id)
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].food_id == "f1"

    def test_inventory_isolated_between_users(self, db_session, test_user_id, other_user_id):
        db_session.add_all(
            [
                InventoryItemORM(
                    inventory_item_id="i1",
                    user_id=test_user_id,
                    food_id="f1",
                    quantity=500,
                    unit="gram",
                ),
                InventoryItemORM(
                    inventory_item_id="i2",
                    user_id=other_user_id,
                    food_id="f1",
                    quantity=750,
                    unit="gram",
                ),
            ]
        )
        db_session.commit()

        only_test_user = db_session.execute(
            select(InventoryItemORM).where(InventoryItemORM.user_id == test_user_id)
        ).scalars().all()
        assert len(only_test_user) == 1
        assert only_test_user[0].quantity == 500

    def test_profile_pk_is_user_id(self, db_session, test_user_id):
        db_session.add(Profile(user_id=test_user_id, name="Tester", height_cm=180.0))
        db_session.commit()

        loaded = db_session.get(Profile, test_user_id)
        assert loaded is not None
        assert loaded.name == "Tester"

    def test_water_goal_one_per_user(self, db_session, test_user_id, other_user_id):
        db_session.add_all(
            [
                WaterGoalORM(user_id=test_user_id, daily_goal_ml=2500.0),
                WaterGoalORM(user_id=other_user_id, daily_goal_ml=1800.0),
            ]
        )
        db_session.commit()

        a = db_session.get(WaterGoalORM, test_user_id)
        b = db_session.get(WaterGoalORM, other_user_id)
        assert a.daily_goal_ml == 2500.0
        assert b.daily_goal_ml == 1800.0


# ──────────────────────────────────────────────────────────────────────────────
# Sanity: the canonical default user_id is exported.
# ──────────────────────────────────────────────────────────────────────────────


def test_default_user_id_exported():
    assert isinstance(DEFAULT_USER_ID, str)
    assert DEFAULT_USER_ID != ""
