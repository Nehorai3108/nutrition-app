"""
Inventory Repository -- Persistence for inventory state and change log.

This file was previously *user-unscoped*: every user wrote into one shared
``storage/data/inventory.json``. After the multi-user refactor each user gets
their own file under ``storage/data/inventory/{user_id}.json`` (and the
matching path for the changelog).

Dual-system note: ``nutrition_app/user_manager.py`` also has its own per-user
inventory functions backed by ``storage_agents/inventories/{user_id}.json``.
That parallel system is the one currently wired into the Streamlit UI and is
left untouched on this branch -- see ``storage_audit/data_layer_audit.md``
migration notes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from nutrition_app.repositories.base_repository import UserScopedRepository


class InventoryRepository(UserScopedRepository):
    """Per-user inventory items, keyed by ``inventory_item_id``."""

    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "inventory")

    def get(self, user_id: str, key: str) -> Optional[dict]:
        return super().get(user_id, key)

    def get_all(self, user_id: str) -> Dict[str, Any]:
        return super().get_all(user_id)

    def save(self, user_id: str, key: str, value: dict) -> None:
        super().save(user_id, key, value)

    def delete(self, user_id: str, key: str) -> bool:
        return super().delete(user_id, key)


class InventoryChangeLogRepository(UserScopedRepository):
    """Per-user inventory changelog, keyed by ``change_id``."""

    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "inventory_changelog")

    def get(self, user_id: str, key: str) -> Optional[dict]:
        return super().get(user_id, key)

    def get_all(self, user_id: str) -> Dict[str, Any]:
        return super().get_all(user_id)

    def save(self, user_id: str, key: str, value: dict) -> None:
        super().save(user_id, key, value)
