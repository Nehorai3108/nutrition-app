"""GoalTracker - hard constraints, logical conditions, gap measurement."""

from typing import Dict, List, Optional

from ..models.autonomy_enums import GoalStatus
from ..models.goal import GoalCondition, GoalDefinition, GoalEvaluation
from ..models.system_metrics import SystemMetrics


class GoalTracker:
    """
    Tracks measurable goals with hard constraints.
    Every goal is a set of logical conditions (metric operator threshold).
    No fuzzy or descriptive goals allowed.
    """

    def __init__(self):
        self._goals: Dict[str, GoalDefinition] = {}
        # Create default demo goal
        demo_goal = GoalDefinition.create_demo_goal()
        self._goals[demo_goal.goal_id] = demo_goal

    def define_goal(
        self,
        name: str,
        conditions: List[Dict],
    ) -> GoalDefinition:
        """
        Define a new goal with hard constraint conditions.
        Each condition: {"metric": str, "operator": str, "threshold": float}
        """
        goal_conditions = [GoalCondition.from_dict(c) for c in conditions]
        goal = GoalDefinition(
            goal_id=f"goal_{len(self._goals) + 1}",
            name=name,
            conditions=goal_conditions,
            status=GoalStatus.NOT_STARTED,
        )
        self._goals[goal.goal_id] = goal
        return goal

    def evaluate_progress(self, metrics: SystemMetrics) -> Dict[str, GoalEvaluation]:
        """Evaluate all goals against current metrics."""
        metrics_dict = metrics.as_dict_for_goals()
        results = {}
        for goal_id, goal in self._goals.items():
            evaluation = goal.evaluate(metrics_dict)
            # Update goal status
            if evaluation.demo_ready:
                goal.status = GoalStatus.ACHIEVED
            elif any(True for _ in evaluation.not_achieved):
                goal.status = GoalStatus.IN_PROGRESS
            results[goal_id] = evaluation
        return results

    def is_demo_ready(self, metrics: SystemMetrics) -> bool:
        """The key question: are all goals met?"""
        metrics_dict = metrics.as_dict_for_goals()
        for goal in self._goals.values():
            evaluation = goal.evaluate(metrics_dict)
            if not evaluation.demo_ready:
                return False
        return True

    def get_gap_summary(self, metrics: SystemMetrics) -> Dict:
        """What's missing to reach the goal. Used by ImprovementEngine."""
        metrics_dict = metrics.as_dict_for_goals()
        all_gaps = []
        all_achieved = []
        overall_progress = 0.0

        for goal in self._goals.values():
            evaluation = goal.evaluate(metrics_dict)
            all_gaps.extend(evaluation.not_achieved)
            all_achieved.extend(evaluation.achieved)
            overall_progress += evaluation.progress_pct

        total_goals = len(self._goals) or 1
        return {
            "demo_ready": self.is_demo_ready(metrics),
            "overall_progress_pct": round(overall_progress / total_goals, 1),
            "achieved": all_achieved,
            "not_achieved": all_gaps,
            "gap_descriptions": [
                gap.get("metric", "") + f": current={gap.get('current')}, target={gap.get('target')}"
                for gap in all_gaps
            ],
        }

    def get_goals(self) -> List[Dict]:
        """Get all goals as dicts for dashboard."""
        return [g.to_dict() for g in self._goals.values()]
