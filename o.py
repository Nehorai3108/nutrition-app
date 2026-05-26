"""
Meal Planner App — Agent 1 Handoff Package
==========================================
PRODUCED BY:  Agent 1 (Product Architect + Data Contracts)
HANDOFF TO:   Agents 2, 4, 5 (and downstream)

This file is the index of all deliverables from Agent 1.
It contains NO business logic, NO demo code, and NO calculations.
It verifies that all models can be imported and instantiated correctly.

--------------------------------------------------------------------
DELIVERABLES INDEX
--------------------------------------------------------------------

1. MODELS (app/models/)        — Final, authoritative, frozen
   user.py          User, ActivityLevel, Goal, DietaryRestriction, SubscriptionTier
   food_item.py     FoodItem, FoodCategory
   meal_plan.py     MealPlan, Meal, MealItem, MacroTotals, MealType
   inventory.py     Inventory, InventoryItem, InventoryUnit

2. JSON SCHEMAS (contracts/schemas/)  — Final, authoritative, frozen
   user.json
   food_item.json
   meal_plan.json
   inventory.json

3. ERD (contracts/ERD.md)     — Final, authoritative

4. API CONTRACTS (contracts/api/contracts.md)  — Final, authoritative
   Contract 1: User -> Nutrition Engine
   Contract 2: Nutrition Engine + Inventory -> Meal Planning Engine
   Contract 3: Meal Planning Engine -> AI Layer
   Contract 4: MealPlan -> Inventory Manager (deduction)
   Contract 5: Inventory Manager -> Meal Planning Engine (availability)

5. MODULE STUBS (app/modules/)  — NON-AUTHORITATIVE DRAFTS
   nutrition_engine.py    -> Agent 2 must implement
   inventory_manager.py   -> Agent 4 must implement
   meal_planning_engine.py -> Agent 5 must implement

--------------------------------------------------------------------
OWNERSHIP MAP
--------------------------------------------------------------------

  File / Component              Owner       Status
  ──────────────────────────────────────────────────────────────────
  app/models/user.py            Agent 1     FINAL
  app/models/food_item.py       Agent 1     FINAL
  app/models/meal_plan.py       Agent 1     FINAL
  app/models/inventory.py       Agent 1     FINAL
  contracts/schemas/*.json      Agent 1     FINAL
  contracts/ERD.md              Agent 1     FINAL
  contracts/api/contracts.md    Agent 1     FINAL
  app/modules/nutrition_engine.py    Agent 2     STUB (not implemented)
  app/modules/inventory_manager.py   Agent 4     STUB (not implemented)
  app/modules/meal_planning_engine.py Agent 5    STUB (not implemented)

--------------------------------------------------------------------
WHAT DOWNSTREAM AGENTS MUST NOT CHANGE
--------------------------------------------------------------------
  - Any model field name or type
  - Any enum value string
  - Any validation constraint in __post_init__
  - NutritionProfile field structure
  - AvailabilityReport field structure
  - generate() / calculate() method signatures
  - MealItem field names (calories, protein_g, carbs_g, fat_g)

--------------------------------------------------------------------
IMPORT VERIFICATION
--------------------------------------------------------------------
Running this file confirms all models are importable and valid.
No NotImplementedError from stubs is raised (stubs are not called).
"""

# ── Import verification ───────────────────────────────────────────────────────

from app.models.user import (
    User, ActivityLevel, Goal, DietaryRestriction, SubscriptionTier
)
from app.models.food_item import FoodItem, FoodCategory
from app.models.meal_plan import MealPlan, Meal, MealItem, MacroTotals, MealType
from app.models.inventory import Inventory, InventoryItem, InventoryUnit

from app.modules.nutrition_engine import NutritionEngine, NutritionProfile
from app.modules.inventory_manager import InventoryManager, AvailabilityReport
from app.modules.meal_planning_engine import MealPlanningEngine

# ── Structural smoke test ─────────────────────────────────────────────────────
# Confirms dataclasses, enums, and serialization work as defined.
# No business logic is called here.

from uuid import uuid4
from datetime import date, datetime

_uid = uuid4()

# 1. User
_user = User(
    name="Test User", email="test@example.com",
    age=30, gender="male", height_cm=175, weight_kg=75,
    activity_level=ActivityLevel.MODERATELY_ACTIVE,
    goal=Goal.LOSE_WEIGHT,
)
assert _user.to_dict()["activity_level"] == "moderately_active"
assert _user.to_dict()["goal"] == "lose_weight"

# 2. FoodItem
_food = FoodItem(
    name="Chicken Breast", calories_per_100g=165,
    protein_per_100g=31, carbs_per_100g=0, fat_per_100g=3.6,
    category=FoodCategory.PROTEIN,
)
assert _food.to_dict()["category"] == "protein"

# 3. MealItem + Meal + MealPlan
_item = MealItem(
    food_item_id=_food.id, quantity_g=150,
    calories=247.5, protein_g=46.5, carbs_g=0.0, fat_g=5.4,
)
_meal = Meal(meal_type=MealType.LUNCH, items=[_item])
assert _meal.totals.calories == 247.5

_plan = MealPlan(
    user_id=_user.id, date=date.today(),
    calorie_target=2000, meals=[_meal],
)
assert _plan.totals.calories == 247.5
assert _plan.calorie_gap == 1752.5

# 4. Inventory
_inv = Inventory(user_id=_user.id)
_inv.upsert(_food.id, 500, InventoryUnit.GRAMS)
assert _inv.has(_food.id)
assert len(_inv.available_food_ids()) == 1

# 5. NutritionProfile structure (no calculation — just validates the dataclass)
_profile = NutritionProfile(
    user_id=str(_user.id),
    bmr=1800.0, tdee=2790.0, calorie_target=2290,
    protein_target_g=200.0, carbs_target_g=200.0, fat_target_g=76.0,
)
assert _profile.to_dict()["calorie_target"] == 2290

# 6. AvailabilityReport structure
_report = AvailabilityReport(
    available_ids=[_food.id],
    missing_ids=[],
    shopping_list=[],
)
assert len(_report.available_ids) == 1

# ── All checks passed ─────────────────────────────────────────────────────────
print("Agent 1 handoff package OK — all models and contracts verified.")
print()
print("Pending implementation:")
print("  Agent 2 -> app/modules/nutrition_engine.py   (NutritionEngine)")
print("  Agent 4 -> app/modules/inventory_manager.py  (InventoryManager)")
print("  Agent 5 -> app/modules/meal_planning_engine.py (MealPlanningEngine)")
