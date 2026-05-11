"""
Run Repository — Persistence for workflow runs and artifacts.
"""

from nutrition_app.repositories.base_repository import BaseRepository


class RunRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/runs"):
        super().__init__(storage_dir, "runs_index")


class ArtifactRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/artifacts"):
        super().__init__(storage_dir, "artifacts_index")
