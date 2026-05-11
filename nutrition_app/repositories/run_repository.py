"""
Run Repository -- Persistence for workflow runs and artifacts.

These are system-level stores (the run_id is the primary key, not the
user_id). The contract requires ``get_all`` to optionally filter by user so
multi-user installations can list "my runs" / "my artifacts".

Records are expected to embed ``user_id`` in their payload -- the system
agents (Agent 7) already write it into ``RunState``/``ArtifactRecord``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from nutrition_app.repositories.base_repository import BaseRepository


class RunRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/runs"):
        super().__init__(storage_dir, "runs_index")

    def get_all(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Return all runs, optionally filtered to a single user.

        ``user_id=None`` preserves the legacy "list everything" behaviour
        used by admin dashboards. When a ``user_id`` is provided, only rows
        whose payload's ``user_id`` matches are returned.
        """
        data = super().get_all()
        if user_id is None:
            return data
        return {k: v for k, v in data.items() if isinstance(v, dict) and v.get("user_id") == user_id}


class ArtifactRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/artifacts"):
        super().__init__(storage_dir, "artifacts_index")

    def get_all(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Return all artifacts, optionally filtered to a single user."""
        data = super().get_all()
        if user_id is None:
            return data
        return {k: v for k, v in data.items() if isinstance(v, dict) and v.get("user_id") == user_id}
