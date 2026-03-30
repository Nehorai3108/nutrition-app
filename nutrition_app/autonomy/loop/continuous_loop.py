"""ContinuousLoop - goal-aware, focused, anti-loop main engine.

The heart of the autonomous system. Runs continuously until:
    1. Goal reached (demo_ready=True) -> notify owner, pause
    2. System stuck (N cycles without progress) -> escalate summary
"""

import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ..models.autonomy_enums import (
    ActionCategory,
    AgentId,
    AuthorityLevel,
    TaskPriority,
    TaskStatus,
)
from ..models.system_metrics import SystemMetrics
from ..models.task_item import TaskItem
from ..orchestrator.autonomy_orchestrator import AutonomyOrchestrator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ContinuousLoop:
    """
    Main autonomous work loop. Drives the entire system.
    Goal-aware, anti-loop, focused execution.
    """

    def __init__(
        self,
        orchestrator: AutonomyOrchestrator,
        cycle_interval_seconds: float = 30.0,
        max_tasks_per_cycle: int = 5,
        scan_every_n_cycles: int = 10,
        stuck_threshold_cycles: int = 20,
    ):
        self._orchestrator = orchestrator
        self._cycle_interval = cycle_interval_seconds
        self._max_tasks_per_cycle = max_tasks_per_cycle
        self._scan_interval = scan_every_n_cycles
        self._stuck_threshold = stuck_threshold_cycles

        self.active = False
        self._cycle_count = 0
        self._cycles_without_progress = 0
        self._last_completed_count = 0
        self._on_goal_reached: Optional[Callable] = None
        self._on_stuck: Optional[Callable] = None
        self._cycle_log: List[Dict] = []

    # ─── Control API (Owner can call at any time) ─────────────────────────

    def start(self) -> None:
        """Start the continuous loop."""
        self.active = True
        self._cycle_count = 0
        self._cycles_without_progress = 0

    def stop(self) -> None:
        """Pause the loop. Can be resumed."""
        self.active = False

    def resume(self) -> None:
        """Resume after stop."""
        self.active = True

    def get_status(self) -> Dict:
        """Current loop status for owner."""
        metrics = self._orchestrator.collect_metrics()
        return {
            "active": self.active,
            "cycle_count": self._cycle_count,
            "cycles_without_progress": self._cycles_without_progress,
            "metrics": metrics.to_dict(),
            "goal_progress": self._orchestrator.goal_tracker.get_gap_summary(metrics),
            "pending_escalations": len(self._orchestrator.get_pending_escalations()),
            "blocking_reason": self._orchestrator.prioritizer.get_blocking_reason(metrics),
        }

    def set_on_goal_reached(self, callback: Callable) -> None:
        """Set callback for when goal is reached."""
        self._on_goal_reached = callback

    def set_on_stuck(self, callback: Callable) -> None:
        """Set callback for when system is stuck."""
        self._on_stuck = callback

    # ─── Main Loop ────────────────────────────────────────────────────────

    def run_single_cycle(self) -> Dict[str, Any]:
        """
        Execute one cycle of the loop. Can be called directly for testing
        or by run() for continuous operation.
        """
        self._cycle_count += 1
        cycle_result = {
            "cycle": self._cycle_count,
            "timestamp": _utcnow().isoformat(),
            "tasks_processed": 0,
            "tasks_verified": 0,
            "failures_handled": 0,
            "feedback_processed": 0,
            "improvements_detected": 0,
            "goal_reached": False,
            "stuck": False,
        }

        metrics = self._orchestrator.collect_metrics()

        # Step 0: Check if goal reached
        if self._orchestrator.goal_tracker.is_demo_ready(metrics):
            cycle_result["goal_reached"] = True
            if self._on_goal_reached:
                self._on_goal_reached(metrics)
            self.active = False
            self._log_cycle(cycle_result)
            return cycle_result

        # Step 1: Detect stuck system
        current_completed = metrics.completed_tasks
        if current_completed <= self._last_completed_count:
            self._cycles_without_progress += 1
        else:
            self._cycles_without_progress = 0
        self._last_completed_count = current_completed

        if self._cycles_without_progress >= self._stuck_threshold:
            cycle_result["stuck"] = True
            self._handle_stuck(metrics)

        # Step 2: Detect stuck tasks
        self._detect_stuck_tasks()

        # Step 3: Detect repeated failure patterns
        self._detect_repeated_failures()

        # Step 4: Process tasks by priority (focus mode)
        tasks_done = self._process_priority_tasks(metrics)
        cycle_result["tasks_processed"] = tasks_done

        # Step 5: Verify completed fixes
        verified = self._verify_completed_fixes()
        cycle_result["tasks_verified"] = verified

        # Step 6: Close verified tasks
        self._close_verified_tasks()

        # Step 7: Process new feedback
        feedback_done = self._process_feedback()
        cycle_result["feedback_processed"] = feedback_done

        # Step 8: Proactive scans (every N cycles)
        if self._cycle_count % self._scan_interval == 0:
            improvements = self._run_proactive_scans(metrics)
            cycle_result["improvements_detected"] = improvements

        # Step 9: Update metrics and log
        self._log_cycle(cycle_result)
        return cycle_result

    def run(self) -> None:
        """
        Run the continuous loop until goal reached or stopped.
        Blocks the calling thread.
        """
        self.start()
        while self.active:
            self.run_single_cycle()
            if self.active:  # May have been stopped by goal check
                time.sleep(self._cycle_interval)

    # ─── Step Implementations ─────────────────────────────────────────────

    def _process_priority_tasks(self, metrics: SystemMetrics) -> int:
        """Process tasks based on priority with focus mode."""
        all_tasks = self._orchestrator.tasks
        prioritized = self._orchestrator.prioritizer.prioritize(all_tasks, metrics)

        processed = 0
        for task in prioritized[:self._max_tasks_per_cycle]:
            result = self._orchestrator.process_task(task)
            processed += 1
            if not result.get("success") and not result.get("skipped"):
                break  # Stop on failure in focus mode

        return processed

    def _verify_completed_fixes(self) -> int:
        """Verify tasks that are in FIXED status."""
        verified = 0
        for task in self._orchestrator.tasks:
            if task.status == TaskStatus.FIXED:
                if self._orchestrator.verify_task(task):
                    verified += 1
        return verified

    def _close_verified_tasks(self) -> None:
        """Close tasks that have been verified."""
        for task in self._orchestrator.tasks:
            if task.status == TaskStatus.VERIFIED:
                self._orchestrator.close_task(task)

    def _process_feedback(self) -> int:
        """Process any new feedback items that don't have tasks yet."""
        pending = self._orchestrator.feedback_manager.get_pending()
        processed = 0
        for fb_dict in pending:
            if not fb_dict.get("linked_task_id"):
                processed += 1
        return processed

    def _run_proactive_scans(self, metrics: SystemMetrics) -> int:
        """Run proactive scans: self-healer + improvement engine."""
        # Self-healer proactive scan
        run_history = self._orchestrator._run_history
        heal_improvements = self._orchestrator.self_healer.run_proactive_scan(
            run_history, metrics
        )

        # Improvement engine gap detection
        evaluations = self._orchestrator.goal_tracker.evaluate_progress(metrics)
        engine_improvements = []
        for eval_result in evaluations.values():
            new_imps = self._orchestrator.improvement_engine.detect_gaps(
                metrics, eval_result
            )
            engine_improvements.extend(new_imps)

        # Create tasks for improvements
        all_improvements = heal_improvements + engine_improvements
        if all_improvements:
            tasks = self._orchestrator.improvement_engine.create_tasks_for_improvements(
                all_improvements
            )
            self._orchestrator.tasks.extend(tasks)

        # Data optimization
        self._orchestrator.data_optimizer.deduplicate_artifacts()

        return len(all_improvements)

    def _detect_stuck_tasks(self) -> None:
        """Mark tasks that have been IN_PROGRESS too long as STUCK."""
        stuck_threshold_minutes = 10
        now = _utcnow()
        for task in self._orchestrator.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                elapsed = (now - task.updated_at).total_seconds() / 60
                if elapsed > stuck_threshold_minutes:
                    task.mark_stuck()

    def _detect_repeated_failures(self) -> None:
        """Detect repeated failure patterns and escalate."""
        heal_history = self._orchestrator.self_healer.get_history()
        patterns = Counter(
            (h.get("detected_in_stage"), h.get("issue_type"))
            for h in heal_history
        )
        for (stage, issue), count in patterns.items():
            if count >= 3:
                # Check if already escalated for this pattern
                already = any(
                    e.get("what_happened", "").startswith(f"Repeated failure pattern")
                    for e in self._orchestrator.get_pending_escalations()
                )
                if not already:
                    self._orchestrator._escalations.append({
                        "what_happened": f"Repeated failure pattern: {issue} in {stage} ({count}x)",
                        "what_we_tried": [{"attempt": i + 1, "action": "auto_fix", "result": "failed"} for i in range(count)],
                        "why_it_failed": f"Same issue recurring {count} times",
                        "options": ["Investigate root cause", "Change approach", "Accept and skip"],
                        "impact_on_goal": f"Blocking: repeated {issue} in {stage}",
                    })

    def _handle_stuck(self, metrics: SystemMetrics) -> None:
        """Handle system stuck condition."""
        summary = {
            "what_happened": f"No progress for {self._cycles_without_progress} cycles",
            "what_we_tried": [
                {"attempt": 1, "action": "continued_processing", "result": "no_progress"}
            ],
            "why_it_failed": "System may be blocked on unresolvable issues",
            "options": ["Review pending escalations", "Reset stuck tasks", "Adjust goals"],
            "impact_on_goal": self._orchestrator.goal_tracker.get_gap_summary(metrics),
        }
        self._orchestrator._escalations.append(summary)
        if self._on_stuck:
            self._on_stuck(summary)

    def _log_cycle(self, result: Dict) -> None:
        """Log cycle summary to audit."""
        self._cycle_log.append(result)
        self._orchestrator.audit_log.log(
            actor=AgentId.AUTONOMY,
            trigger="continuous_loop_cycle",
            action_category=ActionCategory.DATA_PROCESSING,
            authority_level=AuthorityLevel.AUTO,
            description=f"Cycle {result['cycle']}: {result['tasks_processed']} tasks, {result['tasks_verified']} verified",
            before_state={"cycle": result["cycle"] - 1},
            after_state=result,
            result="success" if not result.get("stuck") else "stuck",
        )

    def get_cycle_history(self, limit: int = 20) -> List[Dict]:
        return self._cycle_log[-limit:]
