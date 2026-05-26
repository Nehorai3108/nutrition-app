"""
Unit tests — Orchestrator: Workflow state transitions.
"""

import pytest
from nutrition_app.models.enums import StageStatus, WorkflowStage, DecisionType
from nutrition_app.orchestrator.workflow_engine import WorkflowEngine, DecisionRequired


@pytest.fixture
def engine():
    return WorkflowEngine()


class TestRunCreation:
    def test_create_run(self, engine):
        run = engine.create_run("user_001")
        assert run.run_id is not None
        assert run.user_id == "user_001"
        assert len(run.stages) > 0

    def test_all_stages_pending(self, engine):
        run = engine.create_run("user_001")
        for stage_result in run.stages.values():
            assert stage_result.status == StageStatus.PENDING


class TestStageExecution:
    def test_stage_completes(self, engine):
        engine.register_handler(
            WorkflowStage.CREATE_USER_PROFILE,
            lambda ctx: {"user_id": ctx.get("user_id", "test")}
        )
        run = engine.create_run("user_001")
        run = engine.execute_run(run.run_id, {"user_id": "user_001"})
        stage = run.get_stage(WorkflowStage.CREATE_USER_PROFILE)
        assert stage.status == StageStatus.COMPLETED

    def test_missing_handler_fails(self, engine):
        run = engine.create_run("user_001")
        run = engine.execute_run(run.run_id)
        stage = run.get_stage(WorkflowStage.CREATE_USER_PROFILE)
        assert stage.status == StageStatus.FAILED


class TestDecisionGates:
    def test_decision_stops_pipeline(self, engine):
        def handler_with_decision(ctx):
            raise DecisionRequired(
                decision_type=DecisionType.FOOD_NOT_RECOGNIZED,
                reason="Unknown food item",
            )

        engine.register_handler(WorkflowStage.CREATE_USER_PROFILE, handler_with_decision)
        run = engine.create_run("user_001")
        run = engine.execute_run(run.run_id)

        assert len(run.pending_decisions()) == 1
        stage = run.get_stage(WorkflowStage.CREATE_USER_PROFILE)
        assert stage.status == StageStatus.WAITING_APPROVAL

    def test_resolve_decision(self, engine):
        def handler_with_decision(ctx):
            raise DecisionRequired(
                decision_type=DecisionType.FOOD_NOT_RECOGNIZED,
                reason="Unknown food",
            )

        engine.register_handler(WorkflowStage.CREATE_USER_PROFILE, handler_with_decision)
        run = engine.create_run("user_001")
        run = engine.execute_run(run.run_id)

        decision = run.pending_decisions()[0]
        run = engine.resolve_decision(run.run_id, decision.decision_id, approved=True)
        assert len(run.pending_decisions()) == 0


class TestRerunSupport:
    def test_rerun_single_stage(self, engine):
        call_count = {"n": 0}

        def handler(ctx):
            call_count["n"] += 1
            return {"count": call_count["n"]}

        engine.register_handler(WorkflowStage.CREATE_USER_PROFILE, handler)
        run = engine.create_run("user_001")
        engine.execute_run(run.run_id)
        assert call_count["n"] == 1

        engine.rerun_stage(run.run_id, WorkflowStage.CREATE_USER_PROFILE)
        assert call_count["n"] == 2
