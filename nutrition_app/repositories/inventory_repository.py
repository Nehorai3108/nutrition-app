"""
Inventory Repository — Persistence for inventory state and change log.
"""

from nutrition_app.repositories.base_repository import BaseRepository


class InventoryRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "inventory")


class InventoryChangeLogRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "inventory_changelog")
