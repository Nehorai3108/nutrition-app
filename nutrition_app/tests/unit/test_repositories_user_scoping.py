"""
Tests for the multi-user repository contract.

Every method that the data-layer audit marks as user-scoped MUST:

* accept ``user_id: str`` as its first parameter,
* read/write only that user's data,
* be unable to clobber another user's data even when given the same key.

These tests cover the JSON-file repositories (the runtime ones today). The
ORM models are covered by ``test_persistence_models.py``.
"""

from __future__ import annotations

from nutrition_app.repositories import (
    BaseRepository,
    InventoryChangeLogRepository,
    InventoryRepository,
    RunRepository,
    UserScopedRepository,
)


# ──────────────────────────────────────────────────────────────────────────────
# InventoryRepository
# ──────────────────────────────────────────────────────────────────────────────


class TestInventoryRepositoryUserScoping:
    def test_save_and_get_round_trip(self, tmp_storage_dir, test_user_id):
        repo = InventoryRepository(storage_dir=tmp_storage_dir)
        repo.save(test_user_id, "item_1", {"food_id": "f1", "quantity": 500.0})

        got = repo.get(test_user_id, "item_1")
        assert got is not None
        assert got["food_id"] == "f1"
        assert got["quantity"] == 500.0
        # Defense-in-depth: user_id is stamped onto the record.
        assert got["user_id"] == test_user_id

    def test_users_cannot_see_each_other(self, tmp_storage_dir, test_user_id, other_user_id):
        repo = InventoryRepository(storage_dir=tmp_storage_dir)
        repo.save(test_user_id, "item_1", {"food_id": "f1", "quantity": 100.0})
        repo.save(other_user_id, "item_2", {"food_id": "f2", "quantity": 200.0})

        assert repo.get(test_user_id, "item_2") is None
        assert repo.get(other_user_id, "item_1") is None
        assert "item_1" in repo.get_all(test_user_id)
        assert "item_1" not in repo.get_all(other_user_id)

    def test_delete_only_affects_caller(
        self, tmp_storage_dir, test_user_id, other_user_id
    ):
        repo = InventoryRepository(storage_dir=tmp_storage_dir)
        repo.save(test_user_id, "item_1", {"food_id": "f1"})
        repo.save(other_user_id, "item_1", {"food_id": "f2"})

        assert repo.delete(test_user_id, "item_1") is True
        # The other user's item with the same key must still be present.
        assert repo.get(other_user_id, "item_1") is not None

    def test_get_returns_none_for_unknown_key(self, tmp_storage_dir, test_user_id):
        repo = InventoryRepository(storage_dir=tmp_storage_dir)
        assert repo.get(test_user_id, "missing") is None

    def test_get_all_empty_for_new_user(self, tmp_storage_dir, test_user_id):
        repo = InventoryRepository(storage_dir=tmp_storage_dir)
        assert repo.get_all(test_user_id) == {}


# ──────────────────────────────────────────────────────────────────────────────
# InventoryChangeLogRepository
# ──────────────────────────────────────────────────────────────────────────────


class TestInventoryChangeLogRepositoryUserScoping:
    def test_save_get_round_trip(self, tmp_storage_dir, test_user_id):
        repo = InventoryChangeLogRepository(storage_dir=tmp_storage_dir)
        repo.save(test_user_id, "chg_1", {"action": "add", "quantity_delta": 50.0})
        got = repo.get(test_user_id, "chg_1")
        assert got is not None
        assert got["action"] == "add"

    def test_logs_isolated_between_users(
        self, tmp_storage_dir, test_user_id, other_user_id
    ):
        repo = InventoryChangeLogRepository(storage_dir=tmp_storage_dir)
        repo.save(test_user_id, "chg_1", {"action": "add"})
        repo.save(other_user_id, "chg_2", {"action": "remove"})

        assert list(repo.get_all(test_user_id).keys()) == ["chg_1"]
        assert list(repo.get_all(other_user_id).keys()) == ["chg_2"]


# ──────────────────────────────────────────────────────────────────────────────
# RunRepository / ArtifactRepository — optional user filter on get_all
# ──────────────────────────────────────────────────────────────────────────────


class TestRunRepositoryUserFilter:
    def test_get_all_without_user_returns_everything(self, tmp_storage_dir):
        repo = RunRepository(storage_dir=tmp_storage_dir)
        repo.save("run_1", {"user_id": "alice", "status": "ok"})
        repo.save("run_2", {"user_id": "bob", "status": "ok"})

        everything = repo.get_all()
        assert set(everything.keys()) == {"run_1", "run_2"}

    def test_get_all_filters_by_user(self, tmp_storage_dir):
        repo = RunRepository(storage_dir=tmp_storage_dir)
        repo.save("run_1", {"user_id": "alice", "status": "ok"})
        repo.save("run_2", {"user_id": "bob", "status": "ok"})

        only_alice = repo.get_all(user_id="alice")
        assert set(only_alice.keys()) == {"run_1"}


# ──────────────────────────────────────────────────────────────────────────────
# UserScopedRepository — guards
# ──────────────────────────────────────────────────────────────────────────────


class TestUserScopedRepositoryGuards:
    def test_empty_user_id_rejected(self, tmp_storage_dir):
        repo = UserScopedRepository(tmp_storage_dir, "thing")
        try:
            repo.get("", "k")
        except ValueError:
            return
        raise AssertionError("expected ValueError for empty user_id")


# ──────────────────────────────────────────────────────────────────────────────
# BaseRepository — unchanged behaviour (shared / system stores still work)
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseRepositoryShared:
    def test_save_get(self, tmp_storage_dir):
        repo = BaseRepository(tmp_storage_dir, "shared_thing")
        repo.save("k1", {"v": 1})
        assert repo.get("k1") == {"v": 1}
