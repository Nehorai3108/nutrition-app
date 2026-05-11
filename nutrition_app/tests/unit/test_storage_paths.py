"""
Unit tests — storage_paths.py helpers.
Uses tmp_path fixture so no real storage is touched.
"""

import os
from pathlib import Path

import pytest

from nutrition_app.storage_paths import (
    user_dir,
    user_plans_dir,
    user_profile_file,
    user_inventory_file,
    user_food_log_file,
    user_daily_summaries_file,
    user_water_file,
    user_workouts_file,
    user_weekly_plan_file,
    users_dir,
    system_dir,
    system_tasks_dir,
    system_audit_dir,
    system_director_reports_dir,
    system_director_log,
    system_critic_log,
    system_audit_log,
    system_recipes_dir,
    system_templates_dir,
    system_recipe_images_dir,
    system_users_file,
    legacy_plans_dir,
    legacy_users_file,
)


class TestUserPaths:
    def test_user_dir_created(self, tmp_path):
        d = user_dir("alice", root=tmp_path)
        assert d.exists()
        assert d == tmp_path / "users" / "alice"

    def test_user_plans_dir_created(self, tmp_path):
        d = user_plans_dir("alice", root=tmp_path)
        assert d.exists()
        assert d == tmp_path / "users" / "alice" / "plans"

    def test_user_profile_file_path(self, tmp_path):
        p = user_profile_file("alice", root=tmp_path)
        assert p == tmp_path / "users" / "alice" / "profile.json"
        assert p.parent.exists()

    def test_user_inventory_file_path(self, tmp_path):
        p = user_inventory_file("alice", root=tmp_path)
        assert p == tmp_path / "users" / "alice" / "inventory.json"

    def test_user_food_log_file_path(self, tmp_path):
        p = user_food_log_file("alice", root=tmp_path)
        assert p == tmp_path / "users" / "alice" / "food_log.json"

    def test_user_daily_summaries_file_path(self, tmp_path):
        p = user_daily_summaries_file("alice", root=tmp_path)
        assert p == tmp_path / "users" / "alice" / "daily_summaries.json"

    def test_user_water_file_path(self, tmp_path):
        p = user_water_file("alice", root=tmp_path)
        assert p == tmp_path / "users" / "alice" / "water.json"

    def test_user_workouts_file_path(self, tmp_path):
        p = user_workouts_file("alice", root=tmp_path)
        assert p == tmp_path / "users" / "alice" / "workouts.json"

    def test_user_weekly_plan_file_path(self, tmp_path):
        p = user_weekly_plan_file("alice", root=tmp_path)
        assert p == tmp_path / "users" / "alice" / "weekly_plan.json"

    def test_users_dir_created(self, tmp_path):
        d = users_dir(root=tmp_path)
        assert d.exists()
        assert d == tmp_path / "users"

    def test_different_users_isolated(self, tmp_path):
        a = user_plans_dir("alice", root=tmp_path)
        b = user_plans_dir("bob", root=tmp_path)
        assert a != b
        assert "alice" in str(a)
        assert "bob" in str(b)


class TestSystemPaths:
    def test_system_dir_created(self, tmp_path):
        d = system_dir(root=tmp_path)
        assert d.exists()
        assert d == tmp_path / "system"

    def test_system_tasks_dir(self, tmp_path):
        d = system_tasks_dir(root=tmp_path)
        assert d == tmp_path / "system" / "tasks"
        assert d.exists()

    def test_system_audit_dir(self, tmp_path):
        d = system_audit_dir(root=tmp_path)
        assert d == tmp_path / "system" / "audit"
        assert d.exists()

    def test_system_director_reports_dir(self, tmp_path):
        d = system_director_reports_dir(root=tmp_path)
        assert d == tmp_path / "system" / "audit" / "director_reports"
        assert d.exists()

    def test_system_director_log(self, tmp_path):
        p = system_director_log(root=tmp_path)
        assert p == tmp_path / "system" / "audit" / "director_log.txt"
        assert p.parent.exists()

    def test_system_critic_log(self, tmp_path):
        p = system_critic_log(root=tmp_path)
        assert p == tmp_path / "system" / "audit" / "critic_log.txt"

    def test_system_audit_log(self, tmp_path):
        p = system_audit_log(root=tmp_path)
        assert p == tmp_path / "system" / "audit" / "audit.log"

    def test_system_recipes_dir(self, tmp_path):
        d = system_recipes_dir(root=tmp_path)
        assert d == tmp_path / "system" / "recipes"
        assert d.exists()

    def test_system_templates_dir(self, tmp_path):
        d = system_templates_dir(root=tmp_path)
        assert d == tmp_path / "system" / "templates"
        assert d.exists()

    def test_system_recipe_images_dir(self, tmp_path):
        d = system_recipe_images_dir(root=tmp_path)
        assert d == tmp_path / "system" / "recipe_images"
        assert d.exists()

    def test_system_users_file(self, tmp_path):
        p = system_users_file(root=tmp_path)
        assert p == tmp_path / "system" / "users.json"
        assert p.parent.exists()


class TestLegacyPaths:
    def test_legacy_plans_dir(self, tmp_path):
        d = legacy_plans_dir(root=tmp_path)
        assert d == tmp_path / "plans"
        assert d.exists()

    def test_legacy_users_file(self, tmp_path):
        p = legacy_users_file(root=tmp_path)
        assert p == tmp_path / "users.json"


class TestEnvOverride:
    def test_env_var_overrides_root(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STORAGE_AGENTS_ROOT", str(tmp_path))
        from nutrition_app import storage_paths
        # Force re-evaluation
        d = storage_paths._get_root()
        assert d == tmp_path


class TestRepositoriesUsePaths:
    """Smoke tests ensuring repository classes route to per-user dirs."""

    def test_profile_repo_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STORAGE_AGENTS_ROOT", str(tmp_path))
        from nutrition_app.repositories.profile_repository import ProfileRepository
        repo = ProfileRepository()
        path = repo._path("test_user")
        assert "test_user" in path
        assert "profile.json" in path

    def test_food_log_repo_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STORAGE_AGENTS_ROOT", str(tmp_path))
        from nutrition_app.repositories.food_log_repository import FoodLogRepository
        repo = FoodLogRepository()
        path = repo._path("test_user")
        assert "test_user" in path
        assert "food_log.json" in path

    def test_water_repo_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STORAGE_AGENTS_ROOT", str(tmp_path))
        from nutrition_app.repositories.water_repository import WaterRepository
        repo = WaterRepository()
        path = repo._get_filepath("test_user")
        assert "test_user" in path
        assert "water.json" in path

    def test_workout_repo_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STORAGE_AGENTS_ROOT", str(tmp_path))
        from nutrition_app.repositories import workout_repository
        # Reload to pick up env change
        import importlib
        importlib.reload(workout_repository)
        path = workout_repository._path("test_user")
        assert "test_user" in path
        assert "workouts.json" in path

    def test_daily_summary_repo_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STORAGE_AGENTS_ROOT", str(tmp_path))
        from nutrition_app.repositories.daily_summary_repository import DailySummaryRepository
        repo = DailySummaryRepository()
        path = repo._path("test_user")
        assert "test_user" in path
        assert "daily_summaries.json" in path
