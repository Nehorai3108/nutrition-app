"""
Unit tests — Task Executor.
Verifies all task types execute correctly.
"""

import json
import os
import pytest
import shutil
import tempfile

from nutrition_app.agents.task_executor.task_executor import TaskExecutor


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for tests."""
    tmpdir = tempfile.mkdtemp(prefix="test_executor_")
    os.makedirs(os.path.join(tmpdir, "tasks"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "plans"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "audit"), exist_ok=True)
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def executor(temp_storage):
    return TaskExecutor(storage_dir=temp_storage)


class TestExpandCatalog:
    def test_expand_catalog_succeeds(self, executor):
        task = {
            "task_id": "test_001",
            "type": "expand_catalog",
            "agent": "agent_3_food",
            "priority": "high",
            "details": "Category protein has only 1 foods. Add at least 5 more.",
        }
        result = executor._execute_task(task)
        assert result["success"], f"Expected success: {result}"

    def test_expand_catalog_checks_category(self, executor):
        task = {
            "task_id": "test_002",
            "type": "expand_catalog",
            "agent": "agent_3_food",
            "priority": "high",
            "details": "Category grain has only 2 foods.",
        }
        result = executor._execute_task(task)
        assert result["success"]


class TestFixMealTiming:
    def test_fix_meal_timing_succeeds(self, executor):
        task = {
            "task_id": "test_003",
            "type": "fix_meal_timing",
            "agent": "agent_5_planner",
            "priority": "high",
            "details": "BREAKFAST contains PROTEIN category item",
        }
        result = executor._execute_task(task)
        assert result["success"], f"Meal timing fix failed: {result}"


class TestImproveVariety:
    def test_improve_variety_succeeds(self, executor):
        task = {
            "task_id": "test_004",
            "type": "improve_variety",
            "agent": "agent_5_planner",
            "priority": "medium",
            "details": "food_id food_001 appears in 5/5 plans.",
        }
        result = executor._execute_task(task)
        assert result["success"], f"Variety improvement failed: {result}"


class TestRebalanceMacros:
    def test_rebalance_macros_succeeds(self, executor):
        task = {
            "task_id": "test_005",
            "type": "rebalance_macros",
            "agent": "agent_2_nutrition",
            "priority": "medium",
            "details": "Current: protein 18.0%, carbs 62.0%",
        }
        result = executor._execute_task(task)
        assert result["success"], f"Macro rebalance failed: {result}"


class TestUnknownTaskType:
    def test_unknown_type_fails(self, executor):
        task = {
            "task_id": "test_006",
            "type": "unknown_task",
            "details": "Something",
        }
        result = executor._execute_task(task)
        assert not result["success"]


class TestPendingTaskExecution:
    def test_executes_pending_tasks(self, executor, temp_storage):
        pending = [
            {
                "task_id": "pend_001",
                "type": "expand_catalog",
                "agent": "agent_3_food",
                "priority": "high",
                "details": "Category vegetable has only 2 foods.",
            }
        ]
        pending_path = os.path.join(temp_storage, "tasks", "pending_tasks.json")
        with open(pending_path, "w") as f:
            json.dump(pending, f)

        completed = executor.execute_pending_tasks()
        assert len(completed) == 1
        assert completed[0].get("result", {}).get("success")

        # Pending should be empty now
        with open(pending_path) as f:
            remaining = json.load(f)
        assert len(remaining) == 0
