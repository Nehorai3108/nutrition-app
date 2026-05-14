"""HealRecord - tracks self-healing attempts (reactive and proactive)."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .autonomy_enums import AgentId, HealStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class HealRecord:
    """Records a self-healing attempt from detection through resolution."""
    heal_id: str
    created_at: datetime
    updated_at: datetime
    status: HealStatus
    issue_type: str                     # e.g., "stage_failure", "validation_error", "deviation"
    issue_description: str
    detected_in_stage: Optional[str] = None
    detected_in_run_id: Optional[str] = None
    root_cause: Optional[str] = None
    responsible_agent: Optional[AgentId] = None
    fix_description: Optional[str] = None
    fix_confidence: float = 0.0         # 0.0-1.0, must be >= 0.7 for auto-fix
    fix_applied: bool = False
    verification_passed: Optional[bool] = None
    proactive: bool = False             # True if found by proactive scan, not failure
    rerun_run_id: Optional[str] = None
    escalation_reason: Optional[str] = None
    attempts_history: List[Dict[str, Any]] = field(default_factory=list)

    def record_attempt(self, action: str, result: str, confidence: float) -> None:
        self.attempts_history.append({
            "attempt": len(self.attempts_history) + 1,
            "action": action,
            "result": result,
            "confidence": confidence,
            "timestamp": _utcnow().isoformat(),
        })
        self.updated_at = _utcnow()

    def update_status(self, new_status: HealStatus) -> None:
        self.status = new_status
        self.updated_at = _utcnow()

    def to_dict(self) -> dict:
        return {
            "heal_id": self.heal_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "detected_in_stage": self.detected_in_stage,
            "detected_in_run_id": self.detected_in_run_id,
            "root_cause": self.root_cause,
            "responsible_agent": self.responsible_agent.value if self.responsible_agent else None,
            "fix_description": self.fix_description,
            "fix_confidence": self.fix_confidence,
            "fix_applied": self.fix_applied,
            "verification_passed": self.verification_passed,
            "proactive": self.proactive,
            "rerun_run_id": self.rerun_run_id,
            "escalation_reason": self.escalation_reason,
            "attempts_history": self.attempts_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HealRecord":
        return cls(
            heal_id=data["heal_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            status=HealStatus(data["status"]),
            issue_type=data["issue_type"],
            issue_description=data["issue_description"],
            detected_in_stage=data.get("detected_in_stage"),
            detected_in_run_id=data.get("detected_in_run_id"),
            root_cause=data.get("root_cause"),
            responsible_agent=(
                AgentId(data["responsible_agent"]) if data.get("responsible_agent") else None
            ),
            fix_description=data.get("fix_description"),
            fix_confidence=data.get("fix_confidence", 0.0),
            fix_applied=data.get("fix_applied", False),
            verification_passed=data.get("verification_passed"),
            proactive=data.get("proactive", False),
            rerun_run_id=data.get("rerun_run_id"),
            escalation_reason=data.get("escalation_reason"),
            attempts_history=data.get("attempts_history", []),
        )

    @classmethod
    def create(
        cls,
        issue_type: str,
        issue_description: str,
        detected_in_stage: Optional[str] = None,
        detected_in_run_id: Optional[str] = None,
        proactive: bool = False,
    ) -> "HealRecord":
        now = _utcnow()
        return cls(
            heal_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            status=HealStatus.DETECTED,
            issue_type=issue_type,
            issue_description=issue_description,
            detected_in_stage=detected_in_stage,
            detected_in_run_id=detected_in_run_id,
            proactive=proactive,
        )
