"""
Inventory Repository — Persistence for inventory state and change log.

NOTE (auth-integration agent): the public method signatures below now accept
`user_id: str` as the FIRST positional argument, matching the multi-user
contract in storage_audit/data_layer_audit.md (section 3a). The data-layer
agent (branch feat/data-layer-multi-user) is responsible for the actual
file-per-user namespacing — these wrappers currently pass through to the
existing BaseRepository implementation so signatures are stable for callers.

# TODO(data-layer-agent): namespace storage by user_id (separate file or
# user_id-keyed envelope). Until then, get_all returns the same shared data
# for every user_id, which is the existing — broken — behavior.
"""
from typing import Any, Dict, Optional

from nutrition_app.repositories.base_repository import BaseRepository


class InventoryRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "inventory")

    # ── user-scoped signatures (contract) ────────────────────────────────────
    def get(self, user_id: str, key: str) -> Optional[dict]:  # type: ignore[override]
        # TODO(data-layer-agent): filter by user_id
        return super().get(key)

    def get_all(self, user_id: str) -> Dict[str, Any]:  # type: ignore[override]
        # TODO(data-layer-agent): filter by user_id
        return super().get_all()

    def save(self, user_id: str, key: str, value: dict) -> None:  # type: ignore[override]
        # TODO(data-layer-agent): namespace by user_id
        super().save(key, value)

    def delete(self, user_id: str, key: str) -> bool:  # type: ignore[override]
        # TODO(data-layer-agent): namespace by user_id
        return super().delete(key)


class InventoryChangeLogRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "inventory_changelog")

    # ── user-scoped signatures (contract) ────────────────────────────────────
    def get(self, user_id: str, key: str) -> Optional[dict]:  # type: ignore[override]
        # TODO(data-layer-agent): filter by user_id
        return super().get(key)

    def get_all(self, user_id: str) -> Dict[str, Any]:  # type: ignore[override]
        # TODO(data-layer-agent): filter by user_id
        return super().get_all()

    def save(self, user_id: str, key: str, value: dict) -> None:  # type: ignore[override]
        # TODO(data-layer-agent): namespace by user_id
        super().save(key, value)
