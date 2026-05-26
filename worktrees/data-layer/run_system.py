#!/usr/bin/env python3
"""
Nutrition App — Operational Entrypoint

Phase 1 agents:
  A. Food Data Agent  — sync catalog, normalize, upsert, status
  B. Recipe Agent v1  — store recipes, resolve ingredients, calculate nutrition, scale
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import NutritionDB
from nutrition_app.agents.agent_food_data.food_data_agent import FoodDataAgent
from nutrition_app.agents.agent_recipe.recipe_agent import RecipeAgent


def main():
    db = NutritionDB()

    # ── A. Food Data Agent ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PHASE A — Food Data Agent")
    print("=" * 60)

    food_agent = FoodDataAgent(db=db)
    food_agent.sync(use_api=True)
    food_agent.print_status()

    # ── B. Recipe Agent v1 ────────────────────────────────────────────
    print("=" * 60)
    print("  PHASE B — Recipe Agent v1")
    print("=" * 60)

    recipe_agent = RecipeAgent(db=db)
    recipe_agent.print_status()

    # Demo: save a shakshuka recipe
    shakshuka = recipe_agent.save_recipe({
        "name": "שקשוקה",
        "servings": 2,
        "instructions": (
            "1. מחממים שמן זית במחבת.\n"
            "2. מוסיפים עגבניות ומבשלים 10 דקות.\n"
            "3. שוברים ביצים לתוך הרוטב, מכסים ומבשלים 5 דקות."
        ),
        "ingredients": [
            {"name_he": "ביצה",      "quantity_g": 150.0},   # ~3 eggs
            {"name_he": "עגבנייה",   "quantity_g": 300.0},
            {"name_he": "שמן זית",   "quantity_g": 15.0},
            {"name_he": "פלפל אדום", "quantity_g": 80.0},    # may be unresolved
        ],
    })
    recipe_agent.print_recipe(shakshuka)

    # Demo: scale to 4 servings
    print("  -- Scaled to 4 servings --")
    scaled = recipe_agent.scale_recipe(shakshuka.recipe_id, new_servings=4)
    if scaled:
        recipe_agent.print_recipe(scaled)

    # Demo: list all saved recipes
    all_recipes = recipe_agent.list_recipes()
    print(f"  Total recipes saved: {len(all_recipes)}")
    for r in all_recipes:
        print(f"    - [{r['recipe_id']}] {r['name']}  "
              f"({r['servings']} servings, {r['per_serving_calories_kcal']:.0f} kcal/serving)")

    print()


if __name__ == "__main__":
    main()
