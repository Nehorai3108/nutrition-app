"""
User Repository — Persistence for UserProfile.
"""

from nutrition_app.repositories.base_repository import BaseRepository
from nutrition_app.models.user import UserProfile


class UserRepository(BaseRepository):
    def __init__(self, storage_dir: str = "storage/data"):
        super().__init__(storage_dir, "users")

    def save_user(self, user: UserProfile) -> None:
        self.save(user.user_id, user.to_dict())

    def get_user(self, user_id: str) -> UserProfile | None:
        data = self.get(user_id)
        if data is None:
            return None
        return UserProfile.from_dict(data)
