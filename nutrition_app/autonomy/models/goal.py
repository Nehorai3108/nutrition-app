"""Goal models - hard constraints only, logical conditions, gap measurement."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .autonomy_enums import GoalStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class GoalCondition:
    """A single measurable condition. Only logical operators, no fuzzy/descriptive."""
    metric: str                 # e.g., "average_deviation", "success_rate"
    operator: str               # One of: "<", ">", "<=", ">=", "==", "!="
    threshold: float            # Target value

    VALID_OPERATORS = ("<", ">", "<=", ">=", "==", "!=")

    def __post_init__(self):
        if self.operator not in self.VALID_OPERATORS:
            raise ValueError(f"Invalid operator: {self.operator}. Must be one of {self.VALID_OPERATORS}")

    def evaluate(self, current_value: float) -> bool:
        """Check if current value meets the condition."""
        ops = {
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
        }
        return ops[self.operator](current_value, self.threshold)

    def gap_description(self, current_value: float) -> Optional[str]:
        """Human-readable description of what's missing. None if condition is met."""
        if self.evaluate(current_value):
            return None
        return (
            f"{self.metric}: current={current_value}, "
            f"target {self.operator}{self.threshold}, "
            f"gap={abs(current_value - self.threshold):.2f}"
        )

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "operator": self.operator,
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GoalCondition":
        return cls(
            metric=data["metric"],
            operator=data["operator"],
            threshold=data["threshold"],
        )


@dataclass
class GoalEvaluation:
    """Result of evaluating all goal conditions against current metrics."""
    achieved: List[Dict[str, Any]]      # Conditions that PASS
    not_achieved: List[Dict[str, Any]]  # Conditions that FAIL
    missing_for_goal: List[str]         # Human-readable gap descriptions
    demo_ready: bool
    progress_pct: float                 # 0-100

    def to_dict(self) -> dict:
        return {
            "achieved": self.achieved,
            "not_achieved": self.not_achieved,
            "missing_for_goal": self.missing_for_goal,
            "demo_ready": self.demo_ready,
            "progress_pct": self.progress_pct,
        }


@dataclass
class GoalDefinition:
    """A goal with hard constraint conditions. No fuzzy/descriptive goals."""
    goal_id: str
    name: str
    conditions: List[GoalCondition]
    status: GoalStatus = GoalStatus.NOT_STARTED
    created_at: datetime = field(default_factory=_utcnow)

    def evaluate(self, metrics: Dict[str, float]) -> GoalEvaluation:
        """Evaluate all conditions against current metrics."""
        achieved = []
        not_achieved = []
        missing = []

        for cond in self.conditions:
            current = metrics.get(cond.metric, 0.0)
            if cond.evaluate(current):
                achieved.append({
                    "metric": cond.metric,
                    "current": current,
                    "target": f"{cond.operator}{cond.threshold}",
                    "status": "PASS",
                })
            else:
                not_achieved.append({
                    "metric": cond.metric,
                    "current": current,
                    "target": f"{cond.operator}{cond.threshold}",
                    "status": "FAIL",
                })
                gap_desc = cond.gap_description(current)
                if gap_desc:
                    missing.append(gap_desc)

        total = len(self.conditions)
        passed = len(achieved)
        progress = round((passed / total * 100) if total > 0 else 0.0, 1)
        demo_ready = len(not_achieved) == 0

        return GoalEvaluation(
            achieved=achieved,
            not_achieved=not_achieved,
            missing_for_goal=missing,
            demo_ready=demo_ready,
            progress_pct=progress,
        )

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "conditions": [c.to_dict() for c in self.conditions],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GoalDefinition":
        return cls(
            goal_id=data["goal_id"],
            name=data["name"],
            conditions=[GoalCondition.from_dict(c) for c in data["conditions"]],
            status=GoalStatus(data.get("status", "not_started")),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else _utcnow(),
        )

    @classmethod
    def create_demo_goal(cls) -> "GoalDefinition":
        """Default goal: working demo with acceptable quality."""
        return cls(
            goal_id=str(uuid.uuid4()),
            name="Demo Ready",
            conditions=[
                GoalCondition(metric="average_deviation", operator="<", threshold=5.0),
                GoalCondition(metric="success_rate", operator=">", threshold=90.0),
                GoalCondition(metric="open_failures", operator="==", threshold=0),
                GoalCondition(metric="stuck_tasks", operator="==", threshold=0),
            ],
        )
