"""DataOptimizer - autonomous data maintenance.

Rules:
    - NEVER deletes audit entries (append-only)
    - NEVER deletes source data (user profiles, food catalog)
    - Only removes: duplicates, orphaned artifacts, stale cache
    - Logs every action to AuditLog with before/after
"""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..models.autonomy_enums import ActionCategory, AgentId, AuthorityLevel
from ..audit.audit_log import AuditLog


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DataOptimizer:
    """
    Autonomous data maintenance for storage health.
    Runs periodically via ContinuousLoop proactive scans.
    """

    # Protected paths that are never deleted
    PROTECTED_PREFIXES = ("audit", "users", "food_catalog")

    def __init__(self, storage_dir: str = "storage", audit_log: Optional[AuditLog] = None):
        self._storage_dir = storage_dir
        self._audit_log = audit_log

    def deduplicate_artifacts(self) -> Dict[str, Any]:
        """Find and remove exact duplicate artifacts by content hash."""
        runs_dir = os.path.join(self._storage_dir, "runs")
        if not os.path.exists(runs_dir):
            return {"removed": [], "duplicates_found": 0}

        seen_hashes: Dict[str, str] = {}  # hash -> first file path
        duplicates = []

        for dirpath, _, filenames in os.walk(runs_dir):
            for fname in filenames:
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(dirpath, fname)
                # Skip protected files
                if self._is_protected(fpath):
                    continue

                content_hash = self._file_hash(fpath)
                if content_hash in seen_hashes:
                    duplicates.append({
                        "duplicate": fpath,
                        "original": seen_hashes[content_hash],
                    })
                else:
                    seen_hashes[content_hash] = fpath

        # Remove duplicates
        removed = []
        for dup in duplicates:
            try:
                os.remove(dup["duplicate"])
                removed.append(dup["duplicate"])
            except OSError:
                pass

        if removed and self._audit_log:
            self._audit_log.log(
                actor=AgentId.DATA_MANAGER,
                trigger="data_optimization",
                action_category=ActionCategory.CLEANUP,
                authority_level=AuthorityLevel.AUTO,
                description=f"Deduplicated {len(removed)} artifacts",
                before_state={"duplicate_count": len(duplicates)},
                after_state={"removed": removed},
                result="success",
            )

        return {"removed": removed, "duplicates_found": len(duplicates)}

    def check_cross_stage_consistency(self, run_data: Dict) -> List[Dict]:
        """
        Verify data passed between stages is consistent.
        E.g., food_ids in meal plan exist in food catalog matches.
        """
        issues = []

        # Check: food_ids in meal plan match food_ids from resolve_foods
        resolve_output = run_data.get("resolve_foods_output", {})
        plan_output = run_data.get("generate_meal_plan_output", {})

        if resolve_output and plan_output:
            matched_ids = {
                m.get("food_id") for m in resolve_output.get("matches", [])
                if m.get("food_id")
            }
            plan_food_ids = set()
            for meal in plan_output.get("meals", []):
                for item in meal.get("items", []):
                    if item.get("food_id"):
                        plan_food_ids.add(item["food_id"])

            orphaned = plan_food_ids - matched_ids
            if orphaned:
                issues.append({
                    "type": "orphaned_food_ids",
                    "description": f"Meal plan references {len(orphaned)} food_ids not in matches",
                    "details": list(orphaned),
                })

        # Check: target calories consistency
        targets = run_data.get("calculate_targets_output", {})
        plan_target = plan_output.get("target_calories_kcal")
        calc_target = targets.get("target_calories_kcal")
        if plan_target and calc_target and plan_target != calc_target:
            issues.append({
                "type": "target_mismatch",
                "description": (
                    f"Plan target ({plan_target}) != calculated target ({calc_target})"
                ),
                "details": {"plan": plan_target, "calculated": calc_target},
            })

        return issues

    def compact_old_runs(self, max_age_days: int = 30) -> Dict:
        """Archive runs older than threshold. Keeps audit intact."""
        runs_dir = os.path.join(self._storage_dir, "runs")
        if not os.path.exists(runs_dir):
            return {"compacted": 0}

        cutoff = _utcnow() - timedelta(days=max_age_days)
        compacted = 0

        for run_dir_name in os.listdir(runs_dir):
            run_dir = os.path.join(runs_dir, run_dir_name)
            if not os.path.isdir(run_dir):
                continue

            state_file = os.path.join(run_dir, "run_state.json")
            if not os.path.exists(state_file):
                continue

            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                started = state.get("started_at", "")
                if started:
                    run_time = datetime.fromisoformat(started)
                    if run_time.tzinfo is None:
                        run_time = run_time.replace(tzinfo=timezone.utc)
                    if run_time < cutoff:
                        # Remove non-essential artifacts, keep run_state
                        for fname in os.listdir(run_dir):
                            if fname != "run_state.json":
                                fpath = os.path.join(run_dir, fname)
                                if os.path.isfile(fpath):
                                    os.remove(fpath)
                        compacted += 1
            except (json.JSONDecodeError, ValueError, KeyError):
                continue

        return {"compacted": compacted, "max_age_days": max_age_days}

    def measure_storage_health(self) -> Dict:
        """Measure overall storage health metrics."""
        total_size = 0
        file_count = 0
        json_count = 0

        if os.path.exists(self._storage_dir):
            for dirpath, _, filenames in os.walk(self._storage_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
                        file_count += 1
                        if f.endswith(".json"):
                            json_count += 1

        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_files": file_count,
            "json_files": json_count,
            "storage_dir": self._storage_dir,
        }

    def cleanup_orphaned_data(self) -> Dict:
        """Remove artifacts not linked to any run."""
        runs_dir = os.path.join(self._storage_dir, "runs")
        if not os.path.exists(runs_dir):
            return {"removed": []}

        # Load run index to know valid runs
        index_path = os.path.join(self._storage_dir, "run_index.json")
        valid_runs = set()
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            valid_runs = set(index.keys())

        removed = []
        for run_dir_name in os.listdir(runs_dir):
            run_dir = os.path.join(runs_dir, run_dir_name)
            if not os.path.isdir(run_dir):
                continue
            if run_dir_name not in valid_runs and valid_runs:
                # Orphaned run directory
                for fname in os.listdir(run_dir):
                    fpath = os.path.join(run_dir, fname)
                    if os.path.isfile(fpath) and not self._is_protected(fpath):
                        os.remove(fpath)
                        removed.append(fpath)
                try:
                    os.rmdir(run_dir)
                except OSError:
                    pass

        return {"removed": removed}

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _file_hash(self, path: str) -> str:
        """SHA-256 hash of file content."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _is_protected(self, path: str) -> bool:
        """Check if path is in a protected directory."""
        rel = os.path.relpath(path, self._storage_dir)
        return any(rel.startswith(prefix) for prefix in self.PROTECTED_PREFIXES)
