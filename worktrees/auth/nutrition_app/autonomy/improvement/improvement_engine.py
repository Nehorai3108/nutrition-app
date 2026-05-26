"""ImprovementEngine - goal-gap detection only, creates tasks, NEVER fixes.

Key Rule:
    gap = target_state - current_state
    Only creates improvements that affect goals.
    No noise, no irrelevant improvements.
"""

from typing import Dict, List, Optional

from ..models.autonomy_enums import (
    AgentId,
    ImprovementType,
    TaskPriority,
    TaskStatus,
)
from ..models.goal import GoalEvaluation
from ..models.improvement_item import ImprovementItem
from ..models.system_metrics import SystemMetrics
from ..models.task_item import TaskItem


class ImprovementEngine:
    """
    Identifies gaps between current state and goal targets.
    Creates tasks for agents. NEVER executes fixes directly.
    Only creates improvements tied to goal metrics.
    """

    def __init__(self):
        self._improvements: List[ImprovementItem] = []

    # ─── Agent responsibility mapping per metric ──────────────────────────
    METRIC_AGENT_MAP: Dict[str, AgentId] = {
        "average_deviation": AgentId.PLANNER,
        "success_rate": AgentId.ORCHESTRATOR,
        "open_failures": AgentId.AUTONOMY,
        "stuck_tasks": AgentId.AUTONOMY,
        "auto_fix_rate": AgentId.AUTONOMY,
    }

    METRIC_IMPROVEMENT_TYPE: Dict[str, ImprovementType] = {
        "average_deviation": ImprovementType.DEVIATION_REDUCTION,
        "success_rate": ImprovementType.QUALITY_UPLIFT,
        "open_failures": ImprovementType.CONSISTENCY_FIX,
        "stuck_tasks": ImprovementType.CONSISTENCY_FIX,
        "auto_fix_rate": ImprovementType.QUALITY_UPLIFT,
    }

    def detect_gaps(
        self,
        metrics: SystemMetrics,
        goal_evaluation: GoalEvaluation,
    ) -> List[ImprovementItem]:
        """
        Detect gaps based on goal evaluation.
        Only creates improvements for metrics that FAIL the goal.
        """
        if goal_evaluation.demo_ready:
            return []  # No gaps when goal is met

        new_improvements = []

        for gap in goal_evaluation.not_achieved:
            metric = gap["metric"]
            current = gap["current"]
            target = gap["target"]

            # Skip if we already have an active improvement for this metric
            if self._has_active_improvement(metric):
                continue

            target_agent = self.METRIC_AGENT_MAP.get(metric, AgentId.AUTONOMY)
            imp_type = self.METRIC_IMPROVEMENT_TYPE.get(
                metric, ImprovementType.QUALITY_UPLIFT
            )

            # Determine priority based on gap magnitude
            priority = self._gap_priority(metric, current)

            improvement = ImprovementItem.create(
                improvement_type=imp_type,
                description=f"Goal gap: {metric} is {current}, target is {target}",
                detected_by=AgentId.AUTONOMY,
                target_agent=target_agent,
                expected_vs_actual={
                    "metric": metric,
                    "expected": target,
                    "actual": current,
                    "gap": abs(float(current) - self._parse_threshold(target)),
                },
                proposed_action=self._propose_action(metric, current, target),
                priority=priority,
            )

            self._improvements.append(improvement)
            new_improvements.append(improvement)

        return new_improvements

    def create_tasks_for_improvements(
        self, improvements: List[ImprovementItem]
    ) -> List[TaskItem]:
        """
        Create TaskItems for detected improvements.
        Each task has an owner agent and enters the normal lifecycle.
        """
        tasks = []
        for imp in improvements:
            task = TaskItem.create(
                owner=imp.target_agent,
                priority=imp.priority,
                description=f"[Improvement] {imp.description}: {imp.proposed_action}",
                source="improvement",
                related_improvement_id=imp.improvement_id,
            )
            imp.linked_task_id = task.task_id
            tasks.append(task)
        return tasks

    def mark_resolved(self, improvement_id: str) -> None:
        """Mark an improvement as resolved."""
        for imp in self._improvements:
            if imp.improvement_id == improvement_id:
                imp.resolved = True
                break

    def get_active_improvements(self) -> List[Dict]:
        """Get unresolved improvements for dashboard."""
        return [
            imp.to_dict() for imp in self._improvements
            if not imp.resolved
        ]

    def get_all_improvements(self) -> List[Dict]:
        return [imp.to_dict() for imp in self._improvements]

    # ─── Private Helpers ──────────────────────────────────────────────────

    def _has_active_improvement(self, metric: str) -> bool:
        """Check if there's already an unresolved improvement for this metric."""
        return any(
            imp.expected_vs_actual.get("metric") == metric and not imp.resolved
            for imp in self._improvements
        )

    def _gap_priority(self, metric: str, current_value: float) -> TaskPriority:
        """Determine priority based on how far off the metric is."""
        if metric == "open_failures" and current_value > 0:
            return TaskPriority.CRITICAL
        if metric == "stuck_tasks" and current_value > 0:
            return TaskPriority.HIGH
        if metric == "average_deviation" and current_value > 10:
            return TaskPriority.HIGH
        if metric == "success_rate" and current_value < 50:
            return TaskPriority.HIGH
        return TaskPriority.NORMAL

    def _propose_action(self, metric: str, current: float, target: str) -> str:
        """Suggest an action for closing the gap."""
        actions = {
            "average_deviation": "Optimize meal plan portion calculation to reduce deviation",
            "success_rate": "Investigate and fix failing pipeline stages",
            "open_failures": "Resolve open failures through self-healing",
            "stuck_tasks": "Investigate stuck tasks and escalate if needed",
            "auto_fix_rate": "Improve self-healing pattern coverage",
        }
        return actions.get(metric, f"Improve {metric} to meet target {target}")

    def _parse_threshold(self, target_str: str) -> float:
        """Parse threshold from target string like '>90.0' or '<5.0'."""
        cleaned = target_str.lstrip("<>=!").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
