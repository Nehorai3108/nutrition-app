"""AuditEntry - immutable record of every autonomous action."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any

from .autonomy_enums import AgentId, ActionCategory, AuthorityLevel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEntry:
    """Every autonomous action produces one of these. Never deleted."""
    entry_id: str
    timestamp: datetime
    actor: AgentId
    trigger: str                    # What caused this action
    action_category: ActionCategory
    authority_level: AuthorityLevel
    description: str
    what_changed: Dict[str, Any]    # MUST contain "before" and "after" keys
    result: str                     # "success", "failed", "escalated"

    def __post_init__(self):
        if "before" not in self.what_changed or "after" not in self.what_changed:
            raise ValueError("what_changed must contain 'before' and 'after' keys")

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor.value,
            "trigger": self.trigger,
            "action_category": self.action_category.value,
            "authority_level": self.authority_level.value,
            "description": self.description,
            "what_changed": self.what_changed,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(
            entry_id=data["entry_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=AgentId(data["actor"]),
            trigger=data["trigger"],
            action_category=ActionCategory(data["action_category"]),
            authority_level=AuthorityLevel(data["authority_level"]),
            description=data["description"],
            what_changed=data["what_changed"],
            result=data["result"],
        )

    @classmethod
    def create(
        cls,
        actor: AgentId,
        trigger: str,
        action_category: ActionCategory,
        authority_level: AuthorityLevel,
        description: str,
        before_state: Any,
        after_state: Any,
        result: str,
    ) -> "AuditEntry":
        return cls(
            entry_id=str(uuid.uuid4()),
            timestamp=_utcnow(),
            actor=actor,
            trigger=trigger,
            action_category=action_category,
            authority_level=authority_level,
            description=description,
            what_changed={"before": before_state, "after": after_state},
            result=result,
        )
