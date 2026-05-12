"""
Unit tests — Dashboard
"""

import pytest
import tempfile
from nutrition_app.orchestrator.workflow_engine import WorkflowEngine
from nutrition_app.agents.agent_7_data_performance.data_manager import DataManager
from nutrition_app.dashboard.app import Dashboard
from nutrition_app.models.enums import WorkflowStage


@pytest.fixture
def dashboard():
    engine = WorkflowEngine()
    with tempfile.TemporaryDirectory() as tmpdir:
        data_mgr = DataManager(base_path=tmpdir)
        yield Dashboard(engine, data_mgr)


class TestDashboardViews:
    def test_empty_pipeline(self, dashboard):
        views = dashboard.get_pipeline_view()
        assert views == []

    def test_empty_decision_queue(self, dashboard):
        queue = dashboard.get_decision_queue()
        assert queue == []

    def test_health_panel(self, dashboard):
        health = dashboard.get_health_panel()
        assert "total_runs" in health
        assert "total_artifacts" in health
        assert "duplicate_warnings" in health

    def test_full_state(self, dashboard):
        state = dashboard.get_full_state()
        assert "pipeline" in state
        assert "decision_queue" in state
        assert "health" in state
        assert "timestamp" in state


class TestManualOverride:
    def test_rerun_nonexistent_run(self, dashboard):
        with pytest.raises(ValueError):
            dashboard.rerun_stage("nonexistent", "create_user_profile")
