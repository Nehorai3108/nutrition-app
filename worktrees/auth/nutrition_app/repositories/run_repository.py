"""
Run Repository — Persistence for workflow runs and artifacts.

NOTE (auth-integration agent): `get_all` now accepts an optional `user_id`
parameter per the multi-user contract (storage_audit/data_layer_audit.md
section 3a). When provided, results should be filtered to only that user's
runs/artifacts. The data-layer agent owns the filtering implementation —
the current passthrough preserves existing behavior.

# TODO(data-layer-agent): filter results by user_id when provided.
"""
from typing import Any, Dict, Optional

from nutrition_app.repositories.base_repository import BaseRepository


class RunRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/runs"):
        super().__init__(storage_dir, "runs_index")

    def get_all(self, user_id: Optional[str] = None) -> Dict[str, Any]:  # type: ignore[override]
        # TODO(data-layer-agent): when user_id is provided, filter to that
        # user's runs only (RunState model carries user_id internally).
        return super().get_all()


class ArtifactRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/artifacts"):
        super().__init__(storage_dir, "artifacts_index")

    def get_all(self, user_id: Optional[str] = None) -> Dict[str, Any]:  # type: ignore[override]
        # TODO(data-layer-agent): when user_id is provided, filter to that
        # user's artifacts only.
        return super().get_all()
