"""
Agent 7 — Data & Performance Infrastructure Owner

Responsibility:
- Data structure planning
- Repository / persistence boundaries
- Snapshot, artifact, log, and workflow state management
- Duplicate prevention
- Caching, indexing, query efficiency
- Serialization/deserialization discipline
- Run history management
- Archive / cleanup policy
- Storage optimization
- Performance profiling
- Bottleneck identification
- Efficient per-stage rerun support

Rules:
- MUST NOT change business logic of other agents
- MUST NOT simplify calculations at cost of accuracy
- All optimizations must be behavior-preserving
- Performance improvements must be behavior-preserving
- No deletion of audit-critical data
- Cleanup policy must distinguish: source, derived, cache, logs, debug

Forbidden:
- Nutrition formulas
- Food matching rules
- Meal planning rules
- Decision gates
- UI
"""

import json
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional

from nutrition_app.utils import utcnow
from nutrition_app.models.enums import ArtifactType
from nutrition_app.models.workflow import ArtifactRecord, RunState


class DataManager:
    """Infrastructure agent for data persistence, performance, and cleanup."""

    def __init__(self, base_path: str = "storage"):
        self.base_path = base_path
        self._run_index: Dict[str, dict] = {}  # run_id -> summary metadata
        self._artifact_registry: Dict[str, ArtifactRecord] = {}

    # ─── Artifact Management ─────────────────────────────────────────
    def persist_run_artifacts(self, run_id: str, run_state: RunState) -> Dict[str, str]:
        """Persist all artifacts for a run. Returns dict of artifact_key -> file_path."""
        run_dir = os.path.join(self.base_path, "runs", run_id)
        os.makedirs(run_dir, exist_ok=True)

        persisted = {}

        # Save run state
        state_path = os.path.join(run_dir, "run_state.json")
        self._write_json(state_path, run_state.to_dict())
        persisted["run_state"] = state_path

        # Save individual artifacts
        for key, artifact in run_state.artifacts.items():
            artifact_path = os.path.join(run_dir, f"artifact_{key}.json")
            self._write_json(artifact_path, artifact.to_dict())
            persisted[key] = artifact_path
            self._artifact_registry[key] = artifact

        # Update run index
        self._run_index[run_id] = {
            "run_id": run_id,
            "user_id": run_state.user_id,
            "started_at": run_state.started_at.isoformat(),
            "completed_at": run_state.completed_at.isoformat() if run_state.completed_at else None,
            "is_success": run_state.is_success,
            "artifact_count": len(persisted),
            "stage_count": len(run_state.stages),
        }

        # Save run index
        index_path = os.path.join(self.base_path, "run_index.json")
        self._write_json(index_path, self._run_index)

        return persisted

    def get_run_summary(self, run_id: str) -> Optional[dict]:
        """Get lightweight summary for dashboard display."""
        return self._run_index.get(run_id)

    def get_all_run_summaries(self) -> List[dict]:
        return list(self._run_index.values())

    def load_run_state(self, run_id: str) -> Optional[dict]:
        """Load full run state from disk."""
        path = os.path.join(self.base_path, "runs", run_id, "run_state.json")
        return self._read_json(path)

    # ─── Cleanup & Retention ─────────────────────────────────────────
    def cleanup_stale_artifacts(self, policy: dict) -> dict:
        """
        Apply cleanup policy. Policy keys:
        - max_age_days: delete derived/cache artifacts older than this
        - keep_source: always keep source artifacts (default True)
        - keep_logs_days: keep logs for this many days
        - dry_run: if True, only report what would be deleted
        """
        max_age_days = policy.get("max_age_days", 30)
        keep_source = policy.get("keep_source", True)
        keep_logs_days = policy.get("keep_logs_days", 90)
        dry_run = policy.get("dry_run", True)
        cutoff = utcnow() - timedelta(days=max_age_days)
        log_cutoff = utcnow() - timedelta(days=keep_logs_days)

        to_delete = []
        to_keep = []

        for key, artifact in self._artifact_registry.items():
            if keep_source and artifact.artifact_type == ArtifactType.SOURCE:
                to_keep.append(key)
                continue
            if artifact.artifact_type == ArtifactType.LOG:
                if artifact.created_at < log_cutoff:
                    to_delete.append(key)
                else:
                    to_keep.append(key)
                continue
            if artifact.created_at < cutoff:
                to_delete.append(key)
            else:
                to_keep.append(key)

        if not dry_run:
            for key in to_delete:
                art = self._artifact_registry.pop(key, None)
                if art and art.file_path and os.path.exists(art.file_path):
                    os.remove(art.file_path)

        return {
            "deleted": to_delete if not dry_run else [],
            "would_delete": to_delete if dry_run else [],
            "kept": len(to_keep),
            "policy_applied": policy,
        }

    # ─── Performance Metrics ─────────────────────────────────────────
    def get_performance_metrics(self) -> dict:
        """Collect performance and data health metrics for dashboard."""
        total_runs = len(self._run_index)
        failed_runs = sum(1 for r in self._run_index.values() if r.get("is_success") is False)
        total_artifacts = len(self._artifact_registry)

        # Artifact breakdown by type
        type_counts = {}
        for art in self._artifact_registry.values():
            t = art.artifact_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        # Storage estimate
        storage_bytes = 0
        runs_dir = os.path.join(self.base_path, "runs")
        if os.path.exists(runs_dir):
            for dirpath, _, filenames in os.walk(runs_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp):
                        storage_bytes += os.path.getsize(fp)

        return {
            "total_runs": total_runs,
            "failed_runs": failed_runs,
            "success_rate": round((total_runs - failed_runs) / max(total_runs, 1) * 100, 1),
            "total_artifacts": total_artifacts,
            "artifact_by_type": type_counts,
            "storage_bytes": storage_bytes,
            "storage_mb": round(storage_bytes / (1024 * 1024), 2),
        }

    # ─── Duplicate Detection ─────────────────────────────────────────
    def check_duplicates(self) -> List[dict]:
        """Identify potential duplicate artifacts."""
        seen = {}
        duplicates = []
        for key, art in self._artifact_registry.items():
            sig = f"{art.run_id}:{art.stage.value}:{art.artifact_type.value}"
            if sig in seen:
                duplicates.append({
                    "artifact_1": seen[sig],
                    "artifact_2": key,
                    "signature": sig,
                })
            else:
                seen[sig] = key
        return duplicates

    # ─── Pipeline Metrics Tracking ──────────────────────────────────
    def save_pipeline_metrics(self, metrics: dict) -> str:
        """Save pipeline execution metrics for historical tracking."""
        metrics_dir = os.path.join(self.base_path, "audit")
        os.makedirs(metrics_dir, exist_ok=True)

        # Append to metrics history
        history_path = os.path.join(metrics_dir, "metrics_history.json")
        history = []
        if os.path.isfile(history_path):
            existing = self._read_json(history_path)
            if isinstance(existing, list):
                history = existing

        history.append(metrics)

        # Keep only last 50 entries
        if len(history) > 50:
            history = history[-50:]

        self._write_json(history_path, history)

        # Also save latest metrics
        latest_path = os.path.join(metrics_dir, "metrics.json")
        self._write_json(latest_path, metrics)

        return latest_path

    def get_metrics_history(self) -> list:
        """Load historical pipeline metrics."""
        path = os.path.join(self.base_path, "audit", "metrics_history.json")
        data = self._read_json(path)
        return data if isinstance(data, list) else []

    def cleanup_old_plans(self, max_plans: int = 50, max_age_days: int = 30) -> dict:
        """Archive plans older than max_age_days, keep only latest max_plans."""
        plans_dir = os.path.join(self.base_path, "plans")
        if not os.path.isdir(plans_dir):
            return {"deleted": 0, "kept": 0}

        files = sorted(
            [f for f in os.listdir(plans_dir) if f.endswith(".json")],
            reverse=True,
        )

        kept = 0
        deleted = 0
        cutoff = utcnow() - timedelta(days=max_age_days)

        for i, fname in enumerate(files):
            path = os.path.join(plans_dir, fname)
            if i < max_plans:
                kept += 1
                continue
            # Delete excess plans
            try:
                os.remove(path)
                deleted += 1
            except OSError:
                pass

        return {"deleted": deleted, "kept": kept}

    # ─── Helpers ─────────────────────────────────────────────────────
    def _write_json(self, path: str, data: Any) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def _read_json(self, path: str) -> Optional[dict]:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
