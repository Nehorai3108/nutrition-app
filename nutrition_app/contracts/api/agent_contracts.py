"""
API Contracts — Formal input/output contracts for each agent.
Owner: Agent 1 (Domain & Contracts)

Each agent's contract defines:
- What it receives (input types)
- What it returns (output types)
- What it is NOT allowed to do (boundaries)
"""

from typing import Protocol, List

from nutrition_app.models.user import UserProfile
from nutrition_app.models.nutrition_targets import NutritionTargets
from nutrition_app.models.food_item import FoodItem
from nutrition_app.models.food_match import FoodMatchResult
from nutrition_app.models.inventory import InventoryState, InventoryChangeSet, InventorySnapshot
from nutrition_app.models.meal import MealPlan


# ─── Agent 2: Nutrition Engine ──────────────────────────────────────
class NutritionEngineContract(Protocol):
    """
    Input:  UserProfile
    Output: NutritionTargets
    Forbidden: food selection, inventory, meal planning, storage
    """
    def calculate_targets(self, user: UserProfile) -> NutritionTargets: ...


# ─── Agent 3: Food Catalog & Matching ───────────────────────────────
class FoodCatalogContract(Protocol):
    """
    Input:  food names (List[str]), optional custom entries
    Output: FoodMatchResult
    Forbidden: meal planning, nutrition targets, inventory, deduction
    """
    def match_foods(self, queries: List[str]) -> FoodMatchResult: ...
    def get_food_by_id(self, food_id: str) -> FoodItem | None: ...
    def add_custom_food(self, food: FoodItem) -> FoodItem: ...
    def search_foods(self, query: str, limit: int = 10) -> List[FoodItem]: ...


# ─── Agent 4: Inventory Manager ─────────────────────────────────────
class InventoryManagerContract(Protocol):
    """
    Input:  user actions, approved plan, food references
    Output: InventoryState, InventorySnapshot, InventoryChangeSet
    Forbidden: nutrition calculations, meal planning, food matching, performance policy
    """
    def get_state(self, user_id: str) -> InventoryState: ...
    def add_item(self, user_id: str, food_id: str, quantity: float, unit: str) -> InventoryState: ...
    def deduct_for_plan(self, user_id: str, plan: MealPlan, run_id: str) -> InventoryChangeSet: ...
    def take_snapshot(self, user_id: str, run_id: str) -> InventorySnapshot: ...
    def check_availability(self, user_id: str, food_id: str, quantity: float) -> bool: ...


# ─── Agent 5: Meal Planning Engine ──────────────────────────────────
class MealPlannerContract(Protocol):
    """
    Input:  NutritionTargets, FoodMatchResult, InventoryState
    Output: MealPlan
    Forbidden: modify inventory, modify targets, AI, DB writes
    """
    def generate_plan(
        self,
        targets: NutritionTargets,
        food_matches: FoodMatchResult,
        inventory: InventoryState,
        run_id: str,
    ) -> MealPlan: ...


# ─── Agent 6: AI Layer & Recommendation ─────────────────────────────
class AILayerContract(Protocol):
    """
    Input:  structured outputs from other agents
    Output: textual recommendations / user-facing explanations
    Forbidden: business decisions, schema changes, writes, calculations
    """
    def generate_plan_summary(self, plan: MealPlan) -> str: ...
    def suggest_alternatives(self, food_id: str, reason: str) -> List[str]: ...
    def generate_meal_name(self, meal_items: list) -> str: ...


# ─── Agent 7: Data & Performance ────────────────────────────────────
class DataPerformanceContract(Protocol):
    """
    Input:  contracts, outputs, workflow states
    Output: repositories, storage, artifacts, logs, performance metrics
    Forbidden: change business logic, formulas, matching rules, planning rules, UI
    """
    def persist_run_artifacts(self, run_id: str, artifacts: dict) -> None: ...
    def get_run_summary(self, run_id: str) -> dict: ...
    def cleanup_stale_artifacts(self, policy: dict) -> dict: ...
    def get_performance_metrics(self) -> dict: ...
