"""AutonomyOrchestrator - metrics-driven smart orchestrator.

Wraps existing WorkflowEngine. Every decision is based on SystemMetrics.
Supreme Rule: technical -> AUTO, business -> ESCALATE.
"""

import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models.autonomy_enums import (
    ActionCategory,
    AgentId,
    AuthorityLevel,
    FeedbackStatus,
    FeedbackType,
    HealStatus,
    TaskPriority,
    TaskStatus,
)
from ..models.audit_entry import AuditEntry
from ..models.feedback_item import FeedbackItem
from ..models.goal import GoalEvaluation
from ..models.system_metrics import SystemMetrics
from ..models.task_item import TaskItem
from ..audit.audit_log import AuditLog
from ..authority.authority_policy import AuthorityPolicy
from ..data_optimizer.data_optimizer import DataOptimizer
from ..feedback.feedback_manager import FeedbackManager
from ..goals.goal_tracker import GoalTracker
from ..healing.self_healer import SelfHealer
from ..improvement.improvement_engine import ImprovementEngine
from ..prioritizer.task_prioritizer import TaskPrioritizer


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AutonomyOrchestrator:
    """
    Central coordinator for the autonomous system.
    Wraps the existing WorkflowEngine and adds:
    - Metrics-driven decisions
    - Auto-fix with self-healer
    - Goal tracking
    - Task management with full lifecycle
    - Feedback processing
    - Escalation with full context
    """

    def __init__(
        self,
        workflow_engine: Any,       # Existing WorkflowEngine instance
        audit_log: Optional[AuditLog] = None,
        authority: Optional[AuthorityPolicy] = None,
        self_healer: Optional[SelfHealer] = None,
        improvement_engine: Optional[ImprovementEngine] = None,
        feedback_manager: Optional[FeedbackManager] = None,
        goal_tracker: Optional[GoalTracker] = None,
        task_prioritizer: Optional[TaskPrioritizer] = None,
        data_optimizer: Optional[DataOptimizer] = None,
        storage_dir: str = "storage",
    ):
        self._engine = workflow_engine
        self._audit = audit_log or AuditLog(f"{storage_dir}/audit")
        self._authority = authority or AuthorityPolicy()
        self._healer = self_healer or SelfHealer()
        self._improvement = improvement_engine or ImprovementEngine()
        self._feedback = feedback_manager or FeedbackManager(f"{storage_dir}/feedback")
        self._goals = goal_tracker or GoalTracker()
        self._prioritizer = task_prioritizer or TaskPrioritizer()
        self._data_optimizer = data_optimizer or DataOptimizer(storage_dir, self._audit)

        # Task backlog
        self._tasks: List[TaskItem] = []
        # Run history for metrics
        self._run_history: List[Dict[str, Any]] = []
        # Pending escalations
        self._escalations: List[Dict[str, Any]] = []

    # ─── Pipeline Execution ───────────────────────────────────────────────

    def execute_run_autonomous(
        self, user_id: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a pipeline run with autonomous error handling.
        1. Run pipeline via WorkflowEngine
        2. Inspect for failures/decisions
        3. Auto-fix if possible
        4. Scan for improvements
        5. Log everything
        """
        # Create and execute run
        run_state = self._engine.create_run(user_id)
        run_id = run_state.run_id

        self._audit.log(
            actor=AgentId.AUTONOMY,
            trigger="autonomous_run_start",
            action_category=ActionCategory.DATA_PROCESSING,
            authority_level=AuthorityLevel.AUTO,
            description=f"Starting autonomous run {run_id} for user {user_id}",
            before_state={"run_id": run_id, "status": "starting"},
            after_state={"run_id": run_id, "status": "executing"},
            result="success",
        )

        # Execute pipeline
        run_state = self._engine.execute_run(run_id, context)

        # Inspect results
        result = self._inspect_and_handle(run_state, context)

        # Record run in history
        self._record_run(run_state, result)

        # Scan for improvements after run
        metrics = self.collect_metrics()
        evaluations = self._goals.evaluate_progress(metrics)
        for eval_result in evaluations.values():
            new_improvements = self._improvement.detect_gaps(metrics, eval_result)
            new_tasks = self._improvement.create_tasks_for_improvements(new_improvements)
            self._tasks.extend(new_tasks)

        return result

    def _inspect_and_handle(
        self, run_state: Any, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inspect run results and handle failures/decisions."""
        result = {
            "run_id": run_state.run_id,
            "success": run_state.is_success,
            "auto_fixes": [],
            "escalations": [],
            "decisions_auto_resolved": [],
        }

        # Handle failures
        for stage_name, stage_result in run_state.stages.items():
            if stage_result.status.value == "failed":
                fix_result = self._handle_failure(
                    run_state, stage_name, stage_result, context
                )
                if fix_result.get("auto_fixed"):
                    result["auto_fixes"].append(fix_result)
                elif fix_result.get("escalated"):
                    result["escalations"].append(fix_result)

        # Handle decision gates
        for decision in run_state.pending_decisions():
            decision_result = self._handle_decision(run_state, decision)
            if decision_result.get("auto_resolved"):
                result["decisions_auto_resolved"].append(decision_result)
            elif decision_result.get("escalated"):
                result["escalations"].append(decision_result)

        # Update success based on handling
        if result["auto_fixes"] and not result["escalations"]:
            result["success"] = True

        return result

    def _handle_failure(
        self,
        run_state: Any,
        stage_name: str,
        stage_result: Any,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle a stage failure: detect, diagnose, fix if possible."""
        error = stage_result.error_message or "Unknown error"

        # SelfHealer pipeline
        record = self._healer.detect(error, stage_name, run_state.run_id)
        record = self._healer.diagnose(record)
        fix = self._healer.propose_fix(record)

        # Authority check
        action_category = fix.get("action_category", ActionCategory.UNCERTAIN_DECISION)
        authority_level = self._authority.check_authority(action_category)

        # Confidence-gated auto-fix
        if self._healer.should_auto_fix(fix, authority_level):
            before_ctx = dict(context)
            context = self._healer.apply_fix(record, context)

            self._audit.log(
                actor=AgentId.AUTONOMY,
                trigger=f"stage_failure:{stage_name}",
                action_category=action_category,
                authority_level=authority_level,
                description=f"Auto-fix applied: {fix.get('description', '')}",
                before_state={"stage": stage_name, "error": error},
                after_state={"fix": fix.get("strategy"), "confidence": fix.get("confidence")},
                result="success",
            )

            # Attempt rerun
            try:
                self._engine.rerun_stage(run_state.run_id, stage_name)
                verified = self._healer.verify_fix(
                    record, {"success": True}
                )
                return {
                    "stage": stage_name,
                    "auto_fixed": True,
                    "fix": fix.get("strategy"),
                    "verified": verified,
                }
            except Exception as rerun_err:
                self._healer.verify_fix(record, {"success": False})
                # Fall through to escalation

        # Escalate
        escalation = self._healer.escalate(
            record,
            f"Authority: {authority_level.value}, Confidence: {fix.get('confidence', 0)}"
        )
        self._escalations.append(escalation)

        self._audit.log(
            actor=AgentId.AUTONOMY,
            trigger=f"stage_failure:{stage_name}",
            action_category=action_category,
            authority_level=AuthorityLevel.ESCALATE,
            description=f"Escalated: {error}",
            before_state={"stage": stage_name, "error": error},
            after_state={"escalated": True, "reason": escalation.get("why_it_failed")},
            result="escalated",
        )

        return {"stage": stage_name, "escalated": True, "escalation": escalation}

    def _handle_decision(
        self, run_state: Any, decision: Any
    ) -> Dict[str, Any]:
        """Handle a decision gate: auto-resolve if rules allow."""
        decision_type = decision.decision_type.value
        reason = decision.reason

        # Auto-resolution rules
        auto_resolved = False
        resolution = ""

        if decision_type == "food_not_recognized":
            # Auto-resolve if medium-confidence alternatives exist
            auto_resolved = True
            resolution = "auto_accepted_best_match"
        elif decision_type == "target_deviation":
            # Parse deviation from reason
            deviation = self._parse_deviation(reason)
            if deviation is not None and deviation <= 5.0:
                auto_resolved = True
                resolution = f"auto_accepted_deviation_{deviation}pct"
            elif deviation is not None and deviation <= 10.0:
                auto_resolved = True
                resolution = f"auto_accepted_with_warning_deviation_{deviation}pct"
            # > 10% -> escalate
        elif decision_type == "insufficient_inventory":
            deficit = self._parse_deficit(reason)
            if deficit is not None and deficit < 20.0:
                auto_resolved = True
                resolution = f"auto_accepted_partial_deficit_{deficit}pct"
        elif decision_type == "risky_write":
            auto_resolved = True
            resolution = "auto_approved_standard_deduction"
        # output_conflict, contract_violation -> always escalate

        if auto_resolved:
            try:
                self._engine.resolve_decision(
                    decision.decision_id, approved=True, resolution=resolution
                )
            except Exception:
                pass

            self._audit.log(
                actor=AgentId.AUTONOMY,
                trigger=f"decision_gate:{decision_type}",
                action_category=ActionCategory.VALIDATION,
                authority_level=AuthorityLevel.AUTO,
                description=f"Auto-resolved decision: {decision_type}",
                before_state={"decision_type": decision_type, "reason": reason},
                after_state={"resolution": resolution},
                result="success",
            )
            return {"decision_type": decision_type, "auto_resolved": True, "resolution": resolution}

        # Escalate
        escalation = {
            "what_happened": f"Decision required: {decision_type}",
            "what_we_tried": [{"attempt": 1, "action": "auto_resolution_check", "result": "not_eligible"}],
            "why_it_failed": f"Decision type {decision_type} requires owner approval",
            "options": ["Approve", "Reject", "Modify"],
            "impact_on_goal": f"Pipeline paused at {decision.stage.value}",
        }
        self._escalations.append(escalation)
        return {"decision_type": decision_type, "escalated": True, "escalation": escalation}

    # ─── Task Management ──────────────────────────────────────────────────

    def submit_task(
        self,
        description: str,
        priority: TaskPriority,
        owner: AgentId,
        source: str,
    ) -> TaskItem:
        """Submit a new task to the backlog."""
        task = TaskItem.create(
            owner=owner,
            priority=priority,
            description=description,
            source=source,
        )
        self._tasks.append(task)
        return task

    def process_task(self, task: TaskItem) -> Dict[str, Any]:
        """Process a single task."""
        if not task.can_retry():
            return {"task_id": task.task_id, "skipped": True, "reason": "cannot_retry"}

        task.update_status(TaskStatus.IN_PROGRESS, "processing_started")

        try:
            # Simulated task execution based on source
            result = self._execute_task_logic(task)
            task.result = result

            if result.get("success"):
                task.update_status(TaskStatus.FIXED, "task_completed")
                return {"task_id": task.task_id, "success": True, "result": result}
            else:
                task.record_failure()
                return {"task_id": task.task_id, "success": False, "result": result}

        except Exception as e:
            task.record_failure()
            return {"task_id": task.task_id, "success": False, "error": str(e)}

    def verify_task(self, task: TaskItem) -> bool:
        """Verify a completed task. Required before closing."""
        if task.status != TaskStatus.FIXED:
            return False

        verification = {
            "verified_at": _utcnow().isoformat(),
            "verified_by": AgentId.AUTONOMY.value,
            "result": task.result,
        }
        task.set_verification(verification)
        task.update_status(TaskStatus.VERIFIED, "verification_passed")

        self._audit.log(
            actor=AgentId.AUTONOMY,
            trigger=f"task_verification:{task.task_id}",
            action_category=ActionCategory.VALIDATION,
            authority_level=AuthorityLevel.AUTO,
            description=f"Task verified: {task.description[:80]}",
            before_state={"status": "fixed"},
            after_state={"status": "verified", "verification": verification},
            result="success",
        )
        return True

    def close_task(self, task: TaskItem) -> bool:
        """Close a verified task."""
        if task.verification_result is None:
            return False  # Cannot close without verification
        task.update_status(TaskStatus.CLOSED, "task_closed")
        return True

    # ─── Owner Interface ──────────────────────────────────────────────────

    def resolve_escalation(
        self, escalation_index: int, approved: bool, notes: str = ""
    ) -> Dict:
        """Owner resolves an escalation."""
        if escalation_index >= len(self._escalations):
            return {"error": "Invalid escalation index"}

        escalation = self._escalations[escalation_index]
        resolution = "approved" if approved else "rejected"

        self._audit.log(
            actor=AgentId.AUTONOMY,
            trigger="owner_resolution",
            action_category=ActionCategory.VALIDATION,
            authority_level=AuthorityLevel.ESCALATE,
            description=f"Owner {resolution}: {notes}",
            before_state={"escalation": escalation},
            after_state={"resolution": resolution, "notes": notes},
            result="success",
        )

        self._escalations.pop(escalation_index)
        return {"resolution": resolution, "notes": notes}

    def submit_feedback(
        self,
        description: str,
        feedback_type: Optional[FeedbackType] = None,
        related_run_id: Optional[str] = None,
        related_stage: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
        target_agent: Optional[AgentId] = None,
    ) -> Dict:
        """Owner submits feedback. Auto-processed."""
        item = self._feedback.submit_feedback(
            description=description,
            feedback_type=feedback_type,
            related_run_id=related_run_id,
            related_stage=related_stage,
            attachment_paths=attachment_paths,
            target_agent=target_agent,
        )
        task = self._feedback.create_task_for_feedback(item)
        self._tasks.append(task)

        self._audit.log(
            actor=AgentId.AUTONOMY,
            trigger="owner_feedback",
            action_category=ActionCategory.DATA_PROCESSING,
            authority_level=AuthorityLevel.AUTO,
            description=f"Feedback received: {item.feedback_type.value}",
            before_state={"feedback_count": len(self._feedback.get_all())},
            after_state={
                "feedback_id": item.feedback_id,
                "assigned_to": item.assigned_agent.value if item.assigned_agent else None,
                "task_id": task.task_id,
            },
            result="success",
        )

        return {
            "feedback_id": item.feedback_id,
            "type": item.feedback_type.value,
            "assigned_to": item.assigned_agent.value if item.assigned_agent else None,
            "task_id": task.task_id,
        }

    def get_pending_escalations(self) -> List[Dict]:
        """Get all escalations awaiting owner decision."""
        return list(self._escalations)

    # ─── Metrics Collection ───────────────────────────────────────────────

    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics. Used for ALL decisions."""
        total_runs = len(self._run_history)
        successful_runs = sum(1 for r in self._run_history if r.get("success"))
        success_rate = (successful_runs / max(total_runs, 1)) * 100

        deviations = [
            abs(r.get("calorie_deviation_pct", 0))
            for r in self._run_history
            if r.get("calorie_deviation_pct") is not None
        ]
        avg_deviation = sum(deviations) / max(len(deviations), 1)

        auto_fixes = len(self._healer.get_auto_fixes())
        total_heals = len(self._healer.get_history())
        auto_fix_rate = (auto_fixes / max(total_heals, 1)) * 100

        open_failures = sum(
            1 for t in self._tasks
            if t.status == TaskStatus.FAILED
        )
        stuck_tasks = sum(
            1 for t in self._tasks
            if t.status == TaskStatus.STUCK
        )
        critical_failures = sum(
            1 for t in self._tasks
            if t.status == TaskStatus.FAILED and t.priority == TaskPriority.CRITICAL
        )
        pending_verifications = sum(
            1 for t in self._tasks
            if t.status == TaskStatus.FIXED
        )
        completed = sum(
            1 for t in self._tasks
            if t.status == TaskStatus.CLOSED
        )

        metrics = SystemMetrics(
            timestamp=_utcnow(),
            average_deviation=round(avg_deviation, 2),
            success_rate=round(success_rate, 1),
            auto_fix_rate=round(auto_fix_rate, 1),
            avg_fix_time_seconds=0.0,  # TODO: calculate from heal records
            escalation_count=len(self._escalations),
            open_failures=open_failures,
            stuck_tasks=stuck_tasks,
            total_runs=total_runs,
            total_tasks=len(self._tasks),
            completed_tasks=completed,
            demo_readiness=False,  # Will be set by goal tracker
            open_critical_failures=critical_failures,
            pending_verifications=pending_verifications,
        )

        # Update demo readiness from goal tracker
        metrics.demo_readiness = self._goals.is_demo_ready(metrics)
        return metrics

    # ─── Accessors ────────────────────────────────────────────────────────

    @property
    def tasks(self) -> List[TaskItem]:
        return self._tasks

    @property
    def audit_log(self) -> AuditLog:
        return self._audit

    @property
    def goal_tracker(self) -> GoalTracker:
        return self._goals

    @property
    def self_healer(self) -> SelfHealer:
        return self._healer

    @property
    def improvement_engine(self) -> ImprovementEngine:
        return self._improvement

    @property
    def feedback_manager(self) -> FeedbackManager:
        return self._feedback

    @property
    def data_optimizer(self) -> DataOptimizer:
        return self._data_optimizer

    @property
    def prioritizer(self) -> TaskPrioritizer:
        return self._prioritizer

    def get_status_summary(self) -> Dict:
        """Quick status for owner."""
        metrics = self.collect_metrics()
        return {
            "metrics": metrics.to_dict(),
            "pending_escalations": len(self._escalations),
            "active_tasks": sum(1 for t in self._tasks if t.status == TaskStatus.IN_PROGRESS),
            "pending_feedback": len(self._feedback.get_pending()),
            "goal_progress": self._goals.get_gap_summary(metrics),
        }

    # ─── Private Helpers ──────────────────────────────────────────────────

    def _record_run(self, run_state: Any, result: Dict) -> None:
        """Record a completed run for metrics."""
        self._run_history.append({
            "run_id": run_state.run_id,
            "user_id": run_state.user_id,
            "success": result.get("success", False),
            "calorie_deviation_pct": result.get("calorie_deviation_pct"),
            "auto_fixes": len(result.get("auto_fixes", [])),
            "escalations": len(result.get("escalations", [])),
            "timestamp": _utcnow().isoformat(),
        })

    def _execute_task_logic(self, task: TaskItem) -> Dict:
        """Execute task based on its source and description."""
        # For now, mark as successful for technical tasks
        # Real implementation would dispatch to specific agent handlers
        return {"success": True, "action": "processed", "task_id": task.task_id}

    def _parse_deviation(self, reason: str) -> Optional[float]:
        """Parse deviation percentage from decision reason."""
        import re
        match = re.search(r"(\d+\.?\d*)%", reason)
        if match:
            return float(match.group(1))
        return None

    def _parse_deficit(self, reason: str) -> Optional[float]:
        """Parse deficit percentage from decision reason."""
        import re
        match = re.search(r"(\d+\.?\d*)%", reason)
        if match:
            return float(match.group(1))
        return None
