"""
Workflow models — run state, stage tracking, decision gates, artifacts.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from nutrition_app.utils import utcnow
from .enums import (
    ArtifactType,
    DecisionType,
    StageStatus,
    WorkflowStage,
)


@dataclass
class StageResult:
    stage: WorkflowStage
    status: StageStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    output_artifact_key: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "output_artifact_key": self.output_artifact_key,
            "error_message": self.error_message,
        }


@dataclass
class DecisionGate:
    decision_id: str
    run_id: str
    stage: WorkflowStage
    decision_type: DecisionType
    reason: str
    related_artifact_keys: List[str] = field(default_factory=list)
    status: StageStatus = StageStatus.WAITING_APPROVAL
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    created_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "run_id": self.run_id,
            "stage": self.stage.value,
            "decision_type": self.decision_type.value,
            "reason": self.reason,
            "related_artifact_keys": self.related_artifact_keys,
            "status": self.status.value,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ArtifactRecord:
    artifact_key: str
    run_id: str
    stage: WorkflowStage
    artifact_type: ArtifactType
    description: str
    file_path: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "artifact_key": self.artifact_key,
            "run_id": self.run_id,
            "stage": self.stage.value,
            "artifact_type": self.artifact_type.value,
            "description": self.description,
            "file_path": self.file_path,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RunState:
    run_id: str
    user_id: str
    stages: Dict[str, StageResult] = field(default_factory=dict)
    decisions: List[DecisionGate] = field(default_factory=list)
    artifacts: Dict[str, ArtifactRecord] = field(default_factory=dict)
    started_at: datetime = field(default_factory=utcnow)
    completed_at: Optional[datetime] = None
    is_success: Optional[bool] = None
    error_message: Optional[str] = None

    def get_stage(self, stage: WorkflowStage) -> Optional[StageResult]:
        return self.stages.get(stage.value)

    def set_stage(self, result: StageResult) -> None:
        self.stages[result.stage.value] = result

    def add_decision(self, decision: DecisionGate) -> None:
        self.decisions.append(decision)

    def pending_decisions(self) -> List[DecisionGate]:
        return [d for d in self.decisions if d.status == StageStatus.WAITING_APPROVAL]

    def register_artifact(self, artifact: ArtifactRecord) -> None:
        self.artifacts[artifact.artifact_key] = artifact

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "user_id": self.user_id,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "decisions": [d.to_dict() for d in self.decisions],
            "artifacts": {k: v.to_dict() for k, v in self.artifacts.items()},
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_success": self.is_success,
            "error_message": self.error_message,
        }
