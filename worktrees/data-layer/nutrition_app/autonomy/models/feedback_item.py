"""FeedbackItem - tracks owner feedback through its lifecycle."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .autonomy_enums import AgentId, FeedbackStatus, FeedbackType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class FeedbackItem:
    """Owner feedback with automatic classification, routing, and lifecycle tracking."""
    feedback_id: str
    created_at: datetime
    updated_at: datetime
    feedback_type: FeedbackType
    status: FeedbackStatus
    description: str
    assigned_agent: Optional[AgentId] = None
    related_run_id: Optional[str] = None
    related_stage: Optional[str] = None
    linked_task_id: Optional[str] = None
    attachment_paths: List[str] = field(default_factory=list)
    resolution: Optional[str] = None
    status_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.status_history:
            self.status_history = [{
                "status": self.status.value,
                "timestamp": self.created_at.isoformat(),
                "reason": "feedback_received",
            }]

    def update_status(self, new_status: FeedbackStatus, reason: str) -> None:
        self.status = new_status
        self.updated_at = _utcnow()
        self.status_history.append({
            "status": new_status.value,
            "timestamp": self.updated_at.isoformat(),
            "reason": reason,
        })

    def to_dict(self) -> dict:
        return {
            "feedback_id": self.feedback_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "feedback_type": self.feedback_type.value,
            "status": self.status.value,
            "description": self.description,
            "assigned_agent": self.assigned_agent.value if self.assigned_agent else None,
            "related_run_id": self.related_run_id,
            "related_stage": self.related_stage,
            "linked_task_id": self.linked_task_id,
            "attachment_paths": self.attachment_paths,
            "resolution": self.resolution,
            "status_history": self.status_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackItem":
        return cls(
            feedback_id=data["feedback_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            feedback_type=FeedbackType(data["feedback_type"]),
            status=FeedbackStatus(data["status"]),
            description=data["description"],
            assigned_agent=AgentId(data["assigned_agent"]) if data.get("assigned_agent") else None,
            related_run_id=data.get("related_run_id"),
            related_stage=data.get("related_stage"),
            linked_task_id=data.get("linked_task_id"),
            attachment_paths=data.get("attachment_paths", []),
            resolution=data.get("resolution"),
            status_history=data.get("status_history", []),
        )

    @classmethod
    def create(
        cls,
        feedback_type: FeedbackType,
        description: str,
        related_run_id: Optional[str] = None,
        related_stage: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
    ) -> "FeedbackItem":
        now = _utcnow()
        return cls(
            feedback_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            feedback_type=feedback_type,
            status=FeedbackStatus.RECEIVED,
            description=description,
            related_run_id=related_run_id,
            related_stage=related_stage,
            attachment_paths=attachment_paths or [],
        )
