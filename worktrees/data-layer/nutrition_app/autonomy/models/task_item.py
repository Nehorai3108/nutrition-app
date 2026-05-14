"""TaskItem - full lifecycle with ownership and anti-loop enforcement."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .autonomy_enums import AgentId, TaskPriority, TaskStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TaskItem:
    """
    Every task has an owner agent and full lifecycle.
    Anti-loop rules enforced at the dataclass level.
    """
    task_id: str
    created_at: datetime
    updated_at: datetime
    owner: AgentId
    status: TaskStatus
    priority: TaskPriority
    description: str
    source: str                             # "feedback", "self_heal", "improvement", "backlog", "owner"
    related_feedback_id: Optional[str] = None
    related_heal_id: Optional[str] = None
    related_improvement_id: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    cooldown_until: Optional[datetime] = None
    verification_result: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    status_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.status_history:
            self.status_history = [{
                "status": self.status.value,
                "timestamp": self.created_at.isoformat(),
                "reason": "task_created",
            }]

    def can_retry(self) -> bool:
        """Anti-loop: hard enforcement of retry limits."""
        if self.attempts >= self.max_attempts:
            return False
        if self.cooldown_until and _utcnow() < self.cooldown_until:
            return False
        if self.status == TaskStatus.STUCK:
            return False  # STUCK is terminal
        if self.status == TaskStatus.ESCALATED:
            return False
        if self.status == TaskStatus.CLOSED:
            return False
        return True

    def record_failure(self) -> None:
        """Record a failed attempt with exponential cooldown."""
        self.attempts += 1
        if self.attempts >= self.max_attempts:
            self.update_status(TaskStatus.ESCALATED, "max_attempts_reached")
        else:
            cooldown_minutes = 2 * self.attempts
            self.cooldown_until = _utcnow() + timedelta(minutes=cooldown_minutes)
            self.update_status(
                TaskStatus.FAILED,
                f"attempt_{self.attempts}_failed_cooldown_{cooldown_minutes}min",
            )

    def mark_stuck(self) -> None:
        """Mark as STUCK - terminal status, never returns to IN_PROGRESS."""
        self.update_status(TaskStatus.STUCK, "no_progress_detected")

    def update_status(self, new_status: TaskStatus, reason: str) -> None:
        """Transition status with history tracking and rule enforcement."""
        # STUCK is terminal
        if self.status == TaskStatus.STUCK:
            return
        # CLOSED is terminal
        if self.status == TaskStatus.CLOSED:
            return
        # Cannot close without verification
        if new_status == TaskStatus.CLOSED and self.verification_result is None:
            raise ValueError("Cannot close task without verification_result")
        self.status = new_status
        self.updated_at = _utcnow()
        self.status_history.append({
            "status": new_status.value,
            "timestamp": self.updated_at.isoformat(),
            "reason": reason,
        })

    def set_verification(self, result: Dict[str, Any]) -> None:
        """Set verification result. Required before CLOSED."""
        self.verification_result = result
        self.updated_at = _utcnow()

    def __lt__(self, other: "TaskItem") -> bool:
        """Priority-based sorting."""
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
        }
        return priority_order.get(self.priority, 99) < priority_order.get(other.priority, 99)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "owner": self.owner.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "description": self.description,
            "source": self.source,
            "related_feedback_id": self.related_feedback_id,
            "related_heal_id": self.related_heal_id,
            "related_improvement_id": self.related_improvement_id,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "verification_result": self.verification_result,
            "result": self.result,
            "status_history": self.status_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskItem":
        return cls(
            task_id=data["task_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            owner=AgentId(data["owner"]),
            status=TaskStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            description=data["description"],
            source=data["source"],
            related_feedback_id=data.get("related_feedback_id"),
            related_heal_id=data.get("related_heal_id"),
            related_improvement_id=data.get("related_improvement_id"),
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 3),
            cooldown_until=(
                datetime.fromisoformat(data["cooldown_until"])
                if data.get("cooldown_until") else None
            ),
            verification_result=data.get("verification_result"),
            result=data.get("result"),
            status_history=data.get("status_history", []),
        )

    @classmethod
    def create(
        cls,
        owner: AgentId,
        priority: TaskPriority,
        description: str,
        source: str,
        related_feedback_id: Optional[str] = None,
        related_heal_id: Optional[str] = None,
        related_improvement_id: Optional[str] = None,
    ) -> "TaskItem":
        now = _utcnow()
        return cls(
            task_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            owner=owner,
            status=TaskStatus.CREATED,
            priority=priority,
            description=description,
            source=source,
            related_feedback_id=related_feedback_id,
            related_heal_id=related_heal_id,
            related_improvement_id=related_improvement_id,
        )
