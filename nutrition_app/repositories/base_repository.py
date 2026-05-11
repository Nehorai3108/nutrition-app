"""
Base Repository — Abstract persistence layer.
Owner: Agent 7 (Data & Performance)
"""

import json
import os
from typing import Any, Dict, List, Optional


class BaseRepository:
    """Base class for JSON-file-based repositories."""

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
