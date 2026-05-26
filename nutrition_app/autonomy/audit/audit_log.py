"""AuditLog - immutable, append-only log of all autonomous actions."""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models.autonomy_enums import ActionCategory, AgentId, AuthorityLevel
from ..models.audit_entry import AuditEntry


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog:
    """
    Append-only audit log. Entries are NEVER deleted or modified.
    Persisted to storage/audit/audit_YYYY-MM-DD.json by date.
    """

    def __init__(self, storage_dir: str = "storage/audit"):
        self._storage_dir = storage_dir
        self._entries: List[AuditEntry] = []
        os.makedirs(self._storage_dir, exist_ok=True)

    def log(
        self,
        actor: AgentId,
        trigger: str,
        action_category: ActionCategory,
        authority_level: AuthorityLevel,
        description: str,
        before_state: Any,
        after_state: Any,
        result: str,
    ) -> AuditEntry:
        """
        Log an action. before_state and after_state are MANDATORY.
        Returns the created AuditEntry.
        """
        entry = AuditEntry.create(
            actor=actor,
            trigger=trigger,
            action_category=action_category,
            authority_level=authority_level,
            description=description,
            before_state=before_state,
            after_state=after_state,
            result=result,
        )
        self._entries.append(entry)
        self._persist(entry)
        return entry

    def get_entries(
        self,
        actor: Optional[AgentId] = None,
        action_category: Optional[ActionCategory] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Get entries with optional filtering."""
        results = self._entries
        if actor:
            results = [e for e in results if e.actor == actor]
        if action_category:
            results = [e for e in results if e.action_category == action_category]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """Summary for dashboard: counts by actor, category, result."""
        by_actor: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        by_result: Dict[str, int] = {}

        for entry in self._entries:
            by_actor[entry.actor.value] = by_actor.get(entry.actor.value, 0) + 1
            by_category[entry.action_category.value] = (
                by_category.get(entry.action_category.value, 0) + 1
            )
            by_result[entry.result] = by_result.get(entry.result, 0) + 1

        return {
            "total_entries": len(self._entries),
            "by_actor": by_actor,
            "by_category": by_category,
            "by_result": by_result,
        }

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent entries as dicts for dashboard display."""
        return [e.to_dict() for e in self._entries[-limit:]]

    def _persist(self, entry: AuditEntry) -> None:
        """Persist entry to date-specific JSON file."""
        date_str = entry.timestamp.strftime("%Y-%m-%d")
        file_path = os.path.join(self._storage_dir, f"audit_{date_str}.json")

        existing = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)

        existing.append(entry.to_dict())

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2, default=str)

    def load_from_disk(self, days_back: int = 7) -> None:
        """Load recent entries from disk into memory."""
        if not os.path.exists(self._storage_dir):
            return
        for fname in sorted(os.listdir(self._storage_dir)):
            if not fname.startswith("audit_") or not fname.endswith(".json"):
                continue
            file_path = os.path.join(self._storage_dir, fname)
            with open(file_path, "r", encoding="utf-8") as f:
                entries_data = json.load(f)
            for data in entries_data:
                entry = AuditEntry.from_dict(data)
                if entry not in self._entries:
                    self._entries.append(entry)
