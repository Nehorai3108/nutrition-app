"""
Base Repository — Abstract persistence layer.
Owner: Agent 7 (Data & Performance)

This module provides two abstractions:

* ``BaseRepository``: legacy flat-JSON store keyed by an opaque string.
  Retained for shared / system data (e.g. global recipe catalog, run index).
* ``UserScopedRepository``: file-per-user JSON store. Every public method
  takes ``user_id`` as its first parameter. The on-disk layout is
  ``{storage_dir}/{entity_name}/{user_id}.json`` so different users can never
  read or write each other's data.

NOTE on the dual inventory system: this codebase has two parallel inventory
implementations -- the ``InventoryRepository`` (this package) and
``user_manager.py``. The audit (storage_audit/data_layer_audit.md, migration
notes) calls this out. ``user_manager.py`` is the one currently wired into the
UI and is left untouched by this branch; ``InventoryRepository`` here is
refactored to be correctly user-scoped so the eventual consolidation has a
correct target to merge to.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class BaseRepository:
    """Flat-JSON repository keyed by an opaque string (shared / system data)."""

    def __init__(self, storage_dir: str, entity_name: str):
        self.storage_dir = storage_dir
        self.entity_name = entity_name
        self._data_file = os.path.join(storage_dir, f"{entity_name}.json")
        os.makedirs(storage_dir, exist_ok=True)

    def _load_all(self) -> Dict[str, Any]:
        if not os.path.exists(self._data_file):
            return {}
        with open(self._data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_all(self, data: Dict[str, Any]) -> None:
        with open(self._data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def get(self, key: str) -> Optional[dict]:
        data = self._load_all()
        return data.get(key)

    def get_all(self) -> Dict[str, Any]:
        return self._load_all()

    def save(self, key: str, value: dict) -> None:
        data = self._load_all()
        data[key] = value
        self._save_all(data)

    def delete(self, key: str) -> bool:
        data = self._load_all()
        if key in data:
            del data[key]
            self._save_all(data)
            return True
        return False

    def count(self) -> int:
        return len(self._load_all())

    def exists(self, key: str) -> bool:
        data = self._load_all()
        return key in data


class UserScopedRepository:
    """File-per-user JSON repository.

    Layout::

        {storage_dir}/{entity_name}/{user_id}.json

    Every public method requires ``user_id`` as its first argument. The
    stored ``user_id`` is also written into each record (defense in depth
    against a future shared-file mode).
    """

    def __init__(self, storage_dir: str, entity_name: str):
        self.storage_dir = storage_dir
        self.entity_name = entity_name
        self._dir = os.path.join(storage_dir, entity_name)
        os.makedirs(self._dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        if not user_id:
            raise ValueError("user_id is required for user-scoped repository access")
        return os.path.join(self._dir, f"{user_id}.json")

    def _load_user(self, user_id: str) -> Dict[str, Any]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_user(self, user_id: str, data: Dict[str, Any]) -> None:
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    # -- Public, user-scoped API --

    def get(self, user_id: str, key: str) -> Optional[dict]:
        return self._load_user(user_id).get(key)

    def get_all(self, user_id: str) -> Dict[str, Any]:
        return self._load_user(user_id)

    def save(self, user_id: str, key: str, value: dict) -> None:
        # Defense against ID guessing: stamp the owning user onto every record.
        if isinstance(value, dict):
            value = {**value, "user_id": user_id}
        data = self._load_user(user_id)
        data[key] = value
        self._save_user(user_id, data)

    def delete(self, user_id: str, key: str) -> bool:
        data = self._load_user(user_id)
        if key in data:
            # Belt-and-suspenders: only delete if the row's stamped user_id
            # matches (or is missing -- legacy rows).
            stored = data[key]
            if isinstance(stored, dict) and stored.get("user_id") not in (None, user_id):
                return False
            del data[key]
            self._save_user(user_id, data)
            return True
        return False

    def count(self, user_id: str) -> int:
        return len(self._load_user(user_id))

    def exists(self, user_id: str, key: str) -> bool:
        return key in self._load_user(user_id)
