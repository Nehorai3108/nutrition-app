"""
Dashboard — Internal management dashboard (minimal Phase 1).

This is an internal tool, NOT a user app.

Required views:
- Pipeline View: stages, status, duration, run_id, last updated
- Decision Queue: pending approvals with reason and artifacts
- Artifacts Viewer: input/output per stage, source vs derived
- Logs View: by run, by agent, errors/warnings/notes
- Manual Override: approve/reject, rerun step, retry, inspect
- Performance & Data Health: metrics, warnings, storage
"""

from typing import Dict, List, Optional

from nutrition_app.utils import utcnow
from nutrition_app.models.enums import WorkflowStage
from nutrition_app.orchestrator.workflow_engine import WorkflowEngine
from nutrition_app.agents.agent_7_data_performance.data_manager import DataManager


class Dashboard:
    """Internal management dashboard. Reads from orchestrator and data manager."""

    def __init__(self, engine: WorkflowEngine, data_manager: DataManager):
        self.engine = engine
        self.data_manager = data_manager

    # ─── Pipeline View ───────────────────────────────────────────────
    def get_pipeline_view(self, run_id: str = None) -> List[dict]:
        """Get pipeline stage overview for one or all runs."""
        runs = [self.engine.get_run(run_id)] if run_id else self.engine.get_all_runs()
        views = []
        for run in runs:
            if run is None:
                continue
            stages = []
            for stage_key, stage_result in run.stages.items():
                stages.append({
                    "stage": stage_result.stage.value,
                    "status": stage_result.status.value,
                    "duration_ms": stage_result.duration_ms,
                    "started_at": stage_result.started_at.isoformat() if stage_result.started_at else None,
                    "completed_at": stage_result.completed_at.isoformat() if stage_result.completed_at else None,
                    "error": stage_result.error_message,
                })
            views.append({
                "run_id": run.run_id,
                "user_id": run.user_id,
                "is_success": run.is_success,
                "started_at": run.started_at.isoformat(),
                "stages": stages,
            })
        return views

    # ─── Decision Queue ──────────────────────────────────────────────
    def get_decision_queue(self) -> List[dict]:
        """Get all pending decisions across all runs."""
        queue = []
        for run in self.engine.get_all_runs():
            for decision in run.pending_decisions():
                queue.append({
                    "decision_id": decision.decision_id,
                    "run_id": decision.run_id,
                    "stage": decision.stage.value,
                    "decision_type": decision.decision_type.value,
                    "reason": decision.reason,
                    "related_artifacts": decision.related_artifact_keys,
                    "created_at": decision.created_at.isoformat(),
                })
        return queue

    # ─── Artifacts Viewer ────────────────────────────────────────────
    def get_artifacts_view(self, run_id: str) -> dict:
        """Get all artifacts for a run, split by source vs derived."""
        run = self.engine.get_run(run_id)
        if run is None:
            return {"error": "Run not found"}

        source = []
        derived = []
        for key, artifact in run.artifacts.items():
            entry = {
                "key": key,
                "stage": artifact.stage.value,
                "type": artifact.artifact_type.value,
                "description": artifact.description,
                "created_at": artifact.created_at.isoformat(),
            }
            if artifact.artifact_type.value == "source":
                source.append(entry)
            else:
                derived.append(entry)

        return {"run_id": run_id, "source": source, "derived": derived}

    # ─── Logs View ───────────────────────────────────────────────────
    def get_logs_view(self, run_id: str = None) -> List[dict]:
        """Get log entries. If run_id given, filter to that run."""
        logs = []
        runs = [self.engine.get_run(run_id)] if run_id else self.engine.get_all_runs()
        for run in runs:
            if run is None:
                continue
            for stage_key, stage_result in run.stages.items():
                if stage_result.error_message:
                    logs.append({
                        "run_id": run.run_id,
                        "stage": stage_result.stage.value,
                        "level": "error",
                        "message": stage_result.error_message,
                        "timestamp": stage_result.completed_at.isoformat() if stage_result.completed_at else None,
                    })
        return logs

    # ─── Manual Override ─────────────────────────────────────────────
    def approve_decision(self, run_id: str, decision_id: str, resolution: str = "") -> dict:
        run = self.engine.resolve_decision(run_id, decision_id, approved=True, resolution=resolution)
        return {"status": "approved", "run_id": run_id, "decision_id": decision_id}

    def reject_decision(self, run_id: str, decision_id: str, resolution: str = "") -> dict:
        run = self.engine.resolve_decision(run_id, decision_id, approved=False, resolution=resolution)
        return {"status": "rejected", "run_id": run_id, "decision_id": decision_id}

    def rerun_stage(self, run_id: str, stage: str, context: dict = None) -> dict:
        ws = WorkflowStage(stage)
        run = self.engine.rerun_stage(run_id, ws, context)
        stage_result = run.get_stage(ws)
        return {
            "run_id": run_id,
            "stage": stage,
            "new_status": stage_result.status.value if stage_result else "unknown",
        }

    # ─── Performance & Data Health Panel ─────────────────────────────
    def get_health_panel(self) -> dict:
        """Get system health metrics."""
        metrics = self.data_manager.get_performance_metrics()
        duplicates = self.data_manager.check_duplicates()

        # Add run-level stats
        all_runs = self.engine.get_all_runs()
        slowest_stages = []
        for run in all_runs:
            for stage_key, sr in run.stages.items():
                if sr.duration_ms is not None:
                    slowest_stages.append({
                        "run_id": run.run_id,
                        "stage": sr.stage.value,
                        "duration_ms": sr.duration_ms,
                    })
        slowest_stages.sort(key=lambda x: x["duration_ms"], reverse=True)

        metrics["duplicate_warnings"] = len(duplicates)
        metrics["duplicates"] = duplicates[:10]
        metrics["slowest_stages"] = slowest_stages[:10]
        metrics["total_pending_decisions"] = len(self.get_decision_queue())

        return metrics

    # ─── Full Dashboard State ────────────────────────────────────────
    def get_full_state(self) -> dict:
        """Get complete dashboard state for rendering."""
        return {
            "pipeline": self.get_pipeline_view(),
            "decision_queue": self.get_decision_queue(),
            "logs": self.get_logs_view(),
            "health": self.get_health_panel(),
            "timestamp": utcnow().isoformat(),
        }
