"""TaskPrioritizer - priority ordering with blocking rules (focus mode).

Focus Mode Rules:
    1. Critical failure open -> ONLY critical tasks execute
    2. Tasks awaiting verification -> finish them FIRST
    3. Then feedback tasks
    4. Then goal-relevant improvements
    5. Then regular backlog
"""

from datetime import datetime, timezone
from typing import List

from ..models.autonomy_enums import TaskPriority, TaskStatus
from ..models.system_metrics import SystemMetrics
from ..models.task_item import TaskItem


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskPrioritizer:
    """
    Not just ordering - also blocking.
    System works FOCUSED: never starts new work while critical items are pending.
    """

    # Priority ordering for sorting
    _PRIORITY_ORDER = {
        TaskPriority.CRITICAL: 0,
        TaskPriority.HIGH: 1,
        TaskPriority.NORMAL: 2,
        TaskPriority.LOW: 3,
    }

    # Source ordering (within same priority)
    _SOURCE_ORDER = {
        "self_heal": 0,     # Healing tasks first
        "feedback": 1,      # Owner feedback next
        "improvement": 2,   # Goal-gap improvements
        "backlog": 3,       # Regular backlog
        "owner": 1,         # Owner-submitted same as feedback
    }

    def prioritize(
        self, tasks: List[TaskItem], metrics: SystemMetrics
    ) -> List[TaskItem]:
        """
        Returns tasks sorted by priority with blocking rules applied.
        Filters out tasks that shouldn't execute right now.
        """
        # Filter out non-actionable tasks
        actionable = [
            t for t in tasks
            if t.status in (TaskStatus.CREATED, TaskStatus.FAILED, TaskStatus.FIXED)
            and not self._is_in_cooldown(t)
            and t.status != TaskStatus.STUCK
            and t.status != TaskStatus.ESCALATED
            and t.status != TaskStatus.CLOSED
        ]

        # BLOCKING RULE 1: Critical failure open -> ONLY critical tasks
        if metrics.open_critical_failures > 0:
            critical_only = [
                t for t in actionable
                if t.priority == TaskPriority.CRITICAL
            ]
            if critical_only:
                return sorted(critical_only, key=self._sort_key)

        # BLOCKING RULE 2: Tasks awaiting verification -> finish them FIRST
        verification_pending = [
            t for t in actionable
            if t.status == TaskStatus.FIXED
        ]
        if verification_pending:
            return sorted(verification_pending, key=self._sort_key)

        # Normal priority sorting
        return sorted(actionable, key=self._sort_key)

    def _sort_key(self, task: TaskItem) -> tuple:
        """Sort key: priority first, then source, then age (oldest first)."""
        return (
            self._PRIORITY_ORDER.get(task.priority, 99),
            self._SOURCE_ORDER.get(task.source, 99),
            task.created_at,  # Oldest first within same priority
        )

    def _is_in_cooldown(self, task: TaskItem) -> bool:
        """Check if task is in cooldown period after failure."""
        if task.cooldown_until is None:
            return False
        return _utcnow() < task.cooldown_until

    def get_blocking_reason(self, metrics: SystemMetrics) -> str:
        """Explain why certain tasks are blocked. For dashboard display."""
        if metrics.open_critical_failures > 0:
            return (
                f"Focus Mode: {metrics.open_critical_failures} critical failure(s) open. "
                f"Only critical tasks will execute."
            )
        if metrics.pending_verifications > 0:
            return (
                f"Focus Mode: {metrics.pending_verifications} task(s) awaiting verification. "
                f"Completing verifications before new work."
            )
        return "Normal mode: executing by priority order."
