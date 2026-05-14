"""
Orchestrator — Workflow Engine (Dumb Executor Only)

Responsibility:
- Manage workflow execution order
- State transitions
- Decision gates (stop and wait for approval)
- Retries
- Run ID management
- Artifact registry
- Failure logging
- Resume / rerun support

Rules:
- NO business logic
- NO AI logic
- NO output modification
- Only manages execution order, state, transitions, retries, and decision stops
"""

import uuid
import time
from typing import Any, Callable, Dict, List, Optional

from nutrition_app.utils import utcnow
from nutrition_app.models.enums import (
    ArtifactType,
    DecisionType,
    StageStatus,
    WorkflowStage,
)
from nutrition_app.models.workflow import (
    ArtifactRecord,
    DecisionGate,
    RunState,
    StageResult,
)
from nutrition_app.contracts.workflows.workflow_definition import (
    PIPELINE_STAGES,
    STAGE_MAP,
    STAGE_ORDER,
    StageDefinition,
)


class WorkflowEngine:
    """
    Dumb workflow engine. Executes stages in order, manages state,
    handles decision gates and retries. Contains ZERO business logic.
    """

    def __init__(self):
        self._runs: Dict[str, RunState] = {}
        self._stage_handlers: Dict[WorkflowStage, Callable] = {}

    def register_handler(self, stage: WorkflowStage, handler: Callable) -> None:
        """Register an execution handler for a stage."""
        self._stage_handlers[stage] = handler

    def create_run(self, user_id: str) -> RunState:
        """Create a new workflow run."""
        run_id = str(uuid.uuid4())
        run = RunState(run_id=run_id, user_id=user_id)

        # Initialize all stages as pending
        for stage_def in PIPELINE_STAGES:
            run.set_stage(StageResult(
                stage=stage_def.stage,
                status=StageStatus.PENDING,
            ))

        self._runs[run_id] = run
        return run

    def execute_run(self, run_id: str, context: Dict[str, Any] = None) -> RunState:
        """Execute all stages of a run sequentially."""
        run = self._runs.get(run_id)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")

        context = context or {}
        context["run_id"] = run_id

        for stage in STAGE_ORDER:
            stage_result = run.get_stage(stage)
            if stage_result and stage_result.status == StageStatus.COMPLETED:
                continue  # Already done (rerun support)
            if stage_result and stage_result.status == StageStatus.SKIPPED:
                continue

            result = self._execute_stage(run, stage, context)

            if result.status == StageStatus.WAITING_APPROVAL:
                break  # Stop and wait for decision
            if result.status == StageStatus.FAILED:
                run.is_success = False
                run.error_message = result.error_message
                run.completed_at = utcnow()
                break

        # Check if all stages completed
        all_done = all(
            run.get_stage(s).status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
            for s in STAGE_ORDER
            if run.get_stage(s) is not None
        )
        if all_done:
            run.is_success = True
            run.completed_at = utcnow()

        return run

    def _execute_stage(
        self, run: RunState, stage: WorkflowStage, context: Dict[str, Any]
    ) -> StageResult:
        """Execute a single stage with retry support."""
        stage_def = STAGE_MAP[stage]
        handler = self._stage_handlers.get(stage)

        result = StageResult(
            stage=stage,
            status=StageStatus.RUNNING,
            started_at=utcnow(),
        )
        run.set_stage(result)

        if handler is None:
            result.status = StageStatus.FAILED
            result.error_message = f"No handler registered for stage: {stage.value}"
            result.completed_at = utcnow()
            run.set_stage(result)
            return result

        retries = 0
        max_retries = stage_def.max_retries if stage_def.can_retry else 0

        while retries <= max_retries:
            try:
                start_time = time.time()
                output = handler(context)
                elapsed_ms = int((time.time() - start_time) * 1000)

                result.status = StageStatus.COMPLETED
                result.completed_at = utcnow()
                result.duration_ms = elapsed_ms

                # Register output as artifact
                if output is not None:
                    artifact_key = f"{run.run_id}:{stage.value}:output"
                    artifact = ArtifactRecord(
                        artifact_key=artifact_key,
                        run_id=run.run_id,
                        stage=stage,
                        artifact_type=ArtifactType.DERIVED,
                        description=f"Output of {stage.value}",
                        data=output if isinstance(output, dict) else {"result": str(output)},
                    )
                    run.register_artifact(artifact)
                    result.output_artifact_key = artifact_key
                    context[f"{stage.value}_output"] = output

                run.set_stage(result)
                return result

            except DecisionRequired as e:
                decision = DecisionGate(
                    decision_id=str(uuid.uuid4()),
                    run_id=run.run_id,
                    stage=stage,
                    decision_type=e.decision_type,
                    reason=e.reason,
                    related_artifact_keys=e.related_artifacts,
                )
                run.add_decision(decision)
                result.status = StageStatus.WAITING_APPROVAL
                result.completed_at = utcnow()
                run.set_stage(result)
                return result

            except Exception as e:
                retries += 1
                if retries > max_retries:
                    result.status = StageStatus.FAILED
                    result.error_message = str(e)
                    result.completed_at = utcnow()
                    run.set_stage(result)
                    return result

        return result

    def resolve_decision(
        self, run_id: str, decision_id: str, approved: bool, resolution: str = ""
    ) -> RunState:
        """Resolve a pending decision gate."""
        run = self._runs.get(run_id)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")

        for decision in run.decisions:
            if decision.decision_id == decision_id:
                decision.status = StageStatus.APPROVED if approved else StageStatus.REJECTED
                decision.resolution = resolution
                decision.resolved_at = utcnow()

                if approved:
                    # Mark the stage as completed so execution can continue
                    stage_result = run.get_stage(decision.stage)
                    if stage_result:
                        stage_result.status = StageStatus.COMPLETED
                        run.set_stage(stage_result)
                break

        return run

    def resume_run(self, run_id: str, context: Dict[str, Any] = None) -> RunState:
        """Resume a paused run after decision resolution."""
        return self.execute_run(run_id, context)

    def rerun_stage(
        self, run_id: str, stage: WorkflowStage, context: Dict[str, Any] = None
    ) -> RunState:
        """Rerun a specific stage without rerunning the whole pipeline."""
        run = self._runs.get(run_id)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")

        # Reset stage to pending
        run.set_stage(StageResult(stage=stage, status=StageStatus.PENDING))

        context = context or {}
        context["run_id"] = run_id
        self._execute_stage(run, stage, context)
        return run

    def get_run(self, run_id: str) -> Optional[RunState]:
        return self._runs.get(run_id)

    def get_all_runs(self) -> List[RunState]:
        return list(self._runs.values())


class DecisionRequired(Exception):
    """Raised by stage handlers when a decision gate is needed."""

    def __init__(
        self,
        decision_type: DecisionType,
        reason: str,
        related_artifacts: List[str] = None,
    ):
        self.decision_type = decision_type
        self.reason = reason
        self.related_artifacts = related_artifacts or []
        super().__init__(reason)
