"""ActiveDashboard - control panel (not report board).

Wraps existing Dashboard, adds autonomy-aware views and owner actions.
"""

from typing import Any, Dict, List, Optional

from ..models.autonomy_enums import AgentId, FeedbackType, TaskStatus
from ..models.system_metrics import SystemMetrics
from ..orchestrator.autonomy_orchestrator import AutonomyOrchestrator
from ..loop.continuous_loop import ContinuousLoop


class ActiveDashboard:
    """
    Operational control panel for the autonomous system.
    Not a passive report board - an active command center.
    """

    def __init__(
        self,
        orchestrator: AutonomyOrchestrator,
        loop: Optional[ContinuousLoop] = None,
        base_dashboard: Any = None,  # Existing Dashboard instance
    ):
        self._orchestrator = orchestrator
        self._loop = loop
        self._base = base_dashboard

    # ─── Status Views ─────────────────────────────────────────────────────

    def get_goal_progress(self) -> Dict:
        """Goal conditions: achieved/not + what's missing."""
        metrics = self._orchestrator.collect_metrics()
        return self._orchestrator.goal_tracker.get_gap_summary(metrics)

    def get_running_now(self) -> Dict:
        """Current cycle status and active tasks."""
        active_tasks = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "owner": t.owner.value,
                "status": t.status.value,
                "attempts": t.attempts,
            }
            for t in self._orchestrator.tasks
            if t.status == TaskStatus.IN_PROGRESS
        ]
        loop_status = self._loop.get_status() if self._loop else {"active": False}
        return {
            "loop": loop_status,
            "active_tasks": active_tasks,
            "active_count": len(active_tasks),
        }

    def get_auto_fixes(self, limit: int = 20) -> List[Dict]:
        """Recent self-healing actions with before/after."""
        return self._orchestrator.self_healer.get_auto_fixes(limit)

    def get_open_failures(self) -> List[Dict]:
        """Unresolved failures with attempt history."""
        return [
            {
                "task_id": t.task_id,
                "description": t.description,
                "owner": t.owner.value,
                "attempts": t.attempts,
                "max_attempts": t.max_attempts,
                "status": t.status.value,
                "status_history": t.status_history,
            }
            for t in self._orchestrator.tasks
            if t.status in (TaskStatus.FAILED, TaskStatus.STUCK)
        ]

    def get_pending_escalations(self) -> List[Dict]:
        """Escalations with full context: what happened, what was tried, why it failed."""
        return self._orchestrator.get_pending_escalations()

    # ─── Owner Actions ────────────────────────────────────────────────────

    def submit_feedback(
        self,
        description: str,
        feedback_type: Optional[FeedbackType] = None,
        attachment_paths: Optional[List[str]] = None,
        target_agent: Optional[AgentId] = None,
        related_run_id: Optional[str] = None,
        related_stage: Optional[str] = None,
    ) -> Dict:
        """Submit feedback. Auto-classified, routed, and processed."""
        return self._orchestrator.submit_feedback(
            description=description,
            feedback_type=feedback_type,
            related_run_id=related_run_id,
            related_stage=related_stage,
            attachment_paths=attachment_paths,
            target_agent=target_agent,
        )

    def resolve_escalation(
        self, index: int, approved: bool, notes: str = ""
    ) -> Dict:
        """Resolve a pending escalation."""
        return self._orchestrator.resolve_escalation(index, approved, notes)

    # ─── System Health ────────────────────────────────────────────────────

    def get_quality_metrics(self) -> Dict:
        """Full SystemMetrics snapshot."""
        return self._orchestrator.collect_metrics().to_dict()

    def get_data_health(self) -> Dict:
        """DataOptimizer storage health."""
        return self._orchestrator.data_optimizer.measure_storage_health()

    def get_demo_readiness(self) -> Dict:
        """GoalTracker status + what's missing."""
        metrics = self._orchestrator.collect_metrics()
        gap = self._orchestrator.goal_tracker.get_gap_summary(metrics)
        return {
            "ready": gap.get("demo_ready", False),
            "progress_pct": gap.get("overall_progress_pct", 0),
            "achieved": gap.get("achieved", []),
            "missing": gap.get("not_achieved", []),
            "gap_descriptions": gap.get("gap_descriptions", []),
        }

    def get_feedback_status(self) -> Dict:
        """All feedback items and their lifecycle state."""
        all_feedback = self._orchestrator.feedback_manager.get_all()
        pending = self._orchestrator.feedback_manager.get_pending()
        return {
            "total": len(all_feedback),
            "pending": len(pending),
            "items": all_feedback,
        }

    def get_agent_map(self) -> List[Dict]:
        """Per-agent view: tasks, permissions, recent actions."""
        agents = {}
        for agent in AgentId:
            agents[agent.value] = {
                "agent": agent.value,
                "active_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
            }

        for task in self._orchestrator.tasks:
            key = task.owner.value
            if key in agents:
                if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.CREATED):
                    agents[key]["active_tasks"] += 1
                elif task.status == TaskStatus.CLOSED:
                    agents[key]["completed_tasks"] += 1
                elif task.status in (TaskStatus.FAILED, TaskStatus.STUCK):
                    agents[key]["failed_tasks"] += 1

        return list(agents.values())

    def get_improvement_backlog(self) -> List[Dict]:
        """Active improvement items from the engine."""
        return self._orchestrator.improvement_engine.get_active_improvements()

    def get_audit_summary(self) -> Dict:
        """Audit log summary."""
        return self._orchestrator.audit_log.get_summary()

    # ─── Full State ───────────────────────────────────────────────────────

    def get_full_state(self) -> Dict:
        """Complete dashboard state in one call."""
        return {
            "timestamp": self._orchestrator.collect_metrics().timestamp.isoformat(),
            "goal_progress": self.get_goal_progress(),
            "running_now": self.get_running_now(),
            "quality_metrics": self.get_quality_metrics(),
            "demo_readiness": self.get_demo_readiness(),
            "open_failures": self.get_open_failures(),
            "pending_escalations": self.get_pending_escalations(),
            "auto_fixes": self.get_auto_fixes(10),
            "feedback": self.get_feedback_status(),
            "agents": self.get_agent_map(),
            "improvements": self.get_improvement_backlog(),
            "data_health": self.get_data_health(),
            "audit": self.get_audit_summary(),
        }
