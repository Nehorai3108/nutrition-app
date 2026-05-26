"""ImprovementItem - tracks detected gaps between current and target state."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .autonomy_enums import AgentId, ImprovementType, TaskPriority


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ImprovementItem:
    """
    Detected gap tied to a goal metric.
    ImprovementEngine creates these; it NEVER fixes them directly.
    A linked TaskItem handles the actual fix.
    """
    improvement_id: str
    created_at: datetime
    improvement_type: ImprovementType
    description: str
    detected_by: AgentId
    target_agent: AgentId
    expected_vs_actual: Dict[str, Any]  # {"metric": str, "expected": N, "actual": N, "gap": N}
    proposed_action: str
    linked_task_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    resolved: bool = False

    def to_dict(self) -> dict:
        return {
            "improvement_id": self.improvement_id,
            "created_at": self.created_at.isoformat(),
            "improvement_type": self.improvement_type.value,
            "description": self.description,
            "detected_by": self.detected_by.value,
            "target_agent": self.target_agent.value,
            "expected_vs_actual": self.expected_vs_actual,
            "proposed_action": self.proposed_action,
            "linked_task_id": self.linked_task_id,
            "priority": self.priority.value,
            "resolved": self.resolved,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImprovementItem":
        return cls(
            improvement_id=data["improvement_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            improvement_type=ImprovementType(data["improvement_type"]),
            description=data["description"],
            detected_by=AgentId(data["detected_by"]),
            target_agent=AgentId(data["target_agent"]),
            expected_vs_actual=data["expected_vs_actual"],
            proposed_action=data["proposed_action"],
            linked_task_id=data.get("linked_task_id"),
            priority=TaskPriority(data.get("priority", "normal")),
            resolved=data.get("resolved", False),
        )

    @classmethod
    def create(
        cls,
        improvement_type: ImprovementType,
        description: str,
        detected_by: AgentId,
        target_agent: AgentId,
        expected_vs_actual: Dict[str, Any],
        proposed_action: str,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> "ImprovementItem":
        return cls(
            improvement_id=str(uuid.uuid4()),
            created_at=_utcnow(),
            improvement_type=improvement_type,
            description=description,
            detected_by=detected_by,
            target_agent=target_agent,
            expected_vs_actual=expected_vs_actual,
            proposed_action=proposed_action,
            priority=priority,
        )
