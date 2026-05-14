"""
Meal Planning Engine — Interface Contract (Agent 1 handoff to Agent 5)
=======================================================================
!! NON-AUTHORITATIVE DRAFT — FOR STRUCTURAL REFERENCE ONLY !!

OWNED BY:     Agent 5
WRITTEN BY:   Agent 1 (interface stub only)
PURPOSE:      Define the input contract, output contract, and method
              signatures that Agent 5 must satisfy.
              Agent 5 must replace this file's implementation entirely.
              Agent 1 does NOT define meal selection logic, calorie
              distribution strategy, food prioritization rules, or
              any portion-sizing algorithms.

--------------------------------------------------------------------
WHAT AGENT 5 MUST IMPLEMENT (not defined here):
  - Calorie distribution across meals (e.g. 25/35/30/10 or any other split)
  - Food item selection and prioritization strategy
  - Portion sizing algorithm
  - How inventory preference is applied
  - How dietary restrictions filter food items
  - Number of meals per day (3, 4, or variable)
  - Any variation / substitution logic
--------------------------------------------------------------------
WHAT THIS FILE DEFINES (Agent 1 authority):
  - generate() method signature
  - Required inputs (types + constraints)
  - Required output type (MealPlan)
  - Dependency on NutritionEngine.compute_item_macros() for all MealItem macros
  - Module isolation rules
--------------------------------------------------------------------
"""

from __future__ import annotations
from typing import List, Dict, TYPE_CHECKING
from uuid import UUID
from datetime import date

if TYPE_CHECKING:
    from app.models.food_item import FoodItem
    from app.models.meal_plan import MealPlan
    from app.modules.nutrition_engine import NutritionProfile


class MealPlanningEngine:
    """
    !! STUB ONLY — Agent 5 must replace this implementation !!

    METHOD CONTRACT:

    generate(profile, food_db, available_ids, plan_date) -> MealPlan
    ────────────────────────────────────────────────────────────────
    INPUT CONTRACT (frozen by Agent 1):

    profile : NutritionProfile
        Produced by Agent 2 (NutritionEngine.calculate()).
        Required field: profile.calorie_target (int)
        Agent 5 must use this as the authoritative daily calorie target.

    food_db : Dict[UUID, FoodItem]
        The full set of available food items.
        Agent 5 selects from this pool.

    available_ids : List[UUID]
        Produced by Agent 4 (InventoryManager.get_available_ids()).
        Food items the user has at home.
        Agent 5 should prefer these but is not required to use only these.

    plan_date : date
        The calendar date for which the plan is generated (ISO date).

    OUTPUT CONTRACT (frozen by Agent 1):

    Returns: MealPlan
        - MealPlan.user_id          = UUID(profile.user_id)
        - MealPlan.date             = plan_date
        - MealPlan.calorie_target   = profile.calorie_target
        - MealPlan.status           = "draft"
        - MealPlan.meals            = List[Meal], 1–6 items

    For every MealItem in every Meal:
        - MealItem.calories, protein_g, carbs_g, fat_g MUST be computed
          using NutritionEngine.compute_item_macros(food_item, quantity_g)
        - Agent 5 must NEVER compute these values independently

    ISOLATION RULES:
      - Must NOT call NutritionEngine.calculate()
          (only NutritionEngine.compute_item_macros() is allowed)
      - Must NOT read or write Inventory directly
          (receives available_ids as a pre-computed list)
      - Must NOT call any AI service
      - Must NOT modify NutritionProfile values
      - Output MealPlan.calorie_target must equal profile.calorie_target exactly
    """

    def generate(
        self,
        profile:        "NutritionProfile",
        food_db:        Dict[UUID, "FoodItem"],
        available_ids:  List[UUID],
        plan_date:      date,
    ) -> "MealPlan":
        raise NotImplementedError(
            "MealPlanningEngine.generate() must be implemented by Agent 5. "
            "This is a contract stub only."
        )
