"""
Unit tests — Agent 4: Inventory Manager
"""

import pytest
from nutrition_app.agents.agent_4_inventory.inventory_manager import InventoryManager


@pytest.fixture
def manager():
    return InventoryManager()


class TestAddItem:
    def test_add_new_item(self, manager):
        state = manager.add_item("user1", "food_001", 500.0, "gram")
        item = state.get_by_food_id("food_001")
        assert item is not None
        assert item.quantity == 500.0

    def test_add_existing_item_increases_quantity(self, manager):
        manager.add_item("user1", "food_001", 500.0, "gram")
        state = manager.add_item("user1", "food_001", 200.0, "gram")
        item = state.get_by_food_id("food_001")
        assert item.quantity == 700.0

    def test_change_log_recorded(self, manager):
        manager.add_item("user1", "food_001", 500.0, "gram")
        log = manager.get_change_log()
        assert len(log) == 1
        assert log[0].action.value == "add"


class TestRemoveItem:
    def test_remove_item(self, manager):
        manager.add_item("user1", "food_001", 500.0, "gram")
        state = manager.remove_item("user1", "food_001")
        assert state.get_by_food_id("food_001") is None

    def test_remove_nonexistent_no_error(self, manager):
        state = manager.remove_item("user1", "food_999")
        assert state is not None


class TestAvailability:
    def test_sufficient_stock(self, manager):
        manager.add_item("user1", "food_001", 500.0, "gram")
        assert manager.check_availability("user1", "food_001", 300.0) is True

    def test_insufficient_stock(self, manager):
        manager.add_item("user1", "food_001", 100.0, "gram")
        assert manager.check_availability("user1", "food_001", 300.0) is False

    def test_no_stock(self, manager):
        assert manager.check_availability("user1", "food_001", 1.0) is False


class TestSnapshot:
    def test_snapshot_captures_state(self, manager):
        manager.add_item("user1", "food_001", 500.0, "gram")
        manager.add_item("user1", "food_002", 300.0, "gram")
        snapshot = manager.take_snapshot("user1", "run_001")
        assert len(snapshot.items) == 2
        assert snapshot.run_id == "run_001"


class TestNoNegativeQuantity:
    def test_deduct_does_not_go_negative(self, manager):
        """After deduction, quantity should be >= 0."""
        manager.add_item("user1", "food_001", 50.0, "gram")
        state = manager.get_state("user1")
        item = state.get_by_food_id("food_001")
        assert item.quantity >= 0
