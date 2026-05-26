"""
Unit tests — Agent 7: Data & Performance
"""

import pytest
import tempfile
import os
from nutrition_app.agents.agent_7_data_performance.data_manager import DataManager
from nutrition_app.models.workflow import RunState


@pytest.fixture
def data_mgr():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield DataManager(base_path=tmpdir)


class TestPerformanceMetrics:
    def test_empty_metrics(self, data_mgr):
        metrics = data_mgr.get_performance_metrics()
        assert metrics["total_runs"] == 0
        assert metrics["total_artifacts"] == 0

    def test_no_duplicates_initially(self, data_mgr):
        dups = data_mgr.check_duplicates()
        assert dups == []


class TestCleanup:
    def test_dry_run_cleanup(self, data_mgr):
        result = data_mgr.cleanup_stale_artifacts({"dry_run": True, "max_age_days": 30})
        assert "would_delete" in result
        assert "policy_applied" in result


class TestRunPersistence:
    def test_persist_and_retrieve(self, data_mgr):
        run = RunState(run_id="run_001", user_id="user_001")
        data_mgr.persist_run_artifacts("run_001", run)
        summary = data_mgr.get_run_summary("run_001")
        assert summary is not None
        assert summary["run_id"] == "run_001"
