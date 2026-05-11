"""
Recipe Agent v1 — Operational agent for structured recipe management.

Responsibility:
- Store structured recipes (name, ingredients, gram amounts, servings, instructions)
- Map ingredients to food_ids in the DB
- Calculate total nutrition and per-serving nutrition from DB food values
- Support recipe scaling (returns a scaled copy, does not overwrite)
- Save recipe results persistently to SQLite
- Expose agent status summary

Input:  recipe dicts (from user or other agents)
Output: Recipe objects with computed nutrition, status summary

Forbidden:
- Meal plan construction (that is Agent 5)
- Inventory management (that is Agent 4)
- Nutrition target calculation (that is Agent 2)
- Fetching external food data (that is FoodDataAgent)

Prerequisites:
- FoodDataAgent must be ready (foods in DB) before nutrition can be calculated.
"""

import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from db.database import NutritionDB
from nutrition_app.models.recipe import Recipe, RecipeIngredient, RecipeNutrition


class RecipeAgent:
    """
    Manages the full recipe lifecycle:
    ingest → resolve ingredients → calculate nutrition → persist.
    """

    AGENT_ID = "agent_recipe"
    VERSION = "1.0.0"

    def __init__(self, db: Optional[NutritionDB] = None):
        self._db = db or NutritionDB()

    # ─── Public API ───────────────────────────────────────────────────

    def save_recipe(self, recipe_input: dict) -> Recipe:
        """
        Validate, resolve ingredients, calculate nutrition, and persist.

        recipe_input fields:
          name         (str, required)
          servings     (int, required, >= 1)
          ingredients  (list of {name_he, quantity_g, food_id (optional)})
          instructions (str, optional)
          source       (str, optional, default 'user')

        Returns the saved Recipe with computed nutrition.
        Raises ValueError for invalid input.
        """
        _validate_recipe_input(recipe_input)

        recipe_id = recipe_input.get("recipe_id") or f"recipe_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()

        ingredients, unresolved = self._resolve_ingredients(recipe_input["ingredients"])
        total_nutrition, per_serving_nutrition = self._calculate_nutrition(
            ingredients, recipe_input["servings"]
        )

        recipe = Recipe(
            recipe_id=recipe_id,
            name=recipe_input["name"].strip(),
            servings=int(recipe_input["servings"]),
            ingredients=ingredients,
            instructions=recipe_input.get("instructions", "").strip(),
            total_nutrition=total_nutrition,
            per_serving_nutrition=per_serving_nutrition,
            unresolved_ingredients=unresolved,
            source=recipe_input.get("source", "user"),
            created_at=now,
            updated_at=now,
        )

        db_record = _recipe_to_db_dict(recipe)
        self._db.save_recipe(db_record)
        return recipe

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Retrieve a recipe by ID with full ingredient and nutrition data."""
        row = self._db.get_recipe(recipe_id)
        if not row:
            return None
        return _db_row_to_recipe(row)

    def list_recipes(self) -> List[Dict]:
        """Return summary list of all saved recipes (no ingredient detail)."""
        return self._db.list_recipes()

    def scale_recipe(self, recipe_id: str, new_servings: int) -> Optional[Recipe]:
        """
        Return a scaled copy of the recipe for new_servings.
        The original is not modified. The scaled copy is not saved.

        Returns None if recipe not found.
        Raises ValueError if new_servings < 1.
        """
        if new_servings < 1:
            raise ValueError(f"new_servings must be >= 1, got {new_servings}")

        original = self.get_recipe(recipe_id)
        if not original:
            return None

        factor = new_servings / original.servings

        scaled_ingredients = [
            RecipeIngredient(
                ingredient_id=i.ingredient_id,
                name_he=i.name_he,
                name_en=i.name_en,
                food_id=i.food_id,
                quantity_g=round(i.quantity_g * factor, 1),
            )
            for i in original.ingredients
        ]

        scaled_total, scaled_per_serving = self._calculate_nutrition(
            scaled_ingredients, new_servings
        )

        return Recipe(
            recipe_id=original.recipe_id,
            name=original.name,
            servings=new_servings,
            ingredients=scaled_ingredients,
            instructions=original.instructions,
            total_nutrition=scaled_total,
            per_serving_nutrition=scaled_per_serving,
            unresolved_ingredients=original.unresolved_ingredients,
            source=original.source,
            created_at=original.created_at,
            updated_at=original.updated_at,
        )

    def status(self) -> Dict:
        """Return structured agent status summary."""
        return {
            "agent_id": self.AGENT_ID,
            "version": self.VERSION,
            "recipe_count": self._db.get_recipe_count(),
            "food_catalog_ready": self._db.get_food_count() > 0,
            "food_count": self._db.get_food_count(),
        }

    def print_status(self) -> None:
        """Print a formatted status report to stdout."""
        s = self.status()
        sep = "-" * 50
        print()
        print(sep)
        print("  RECIPE AGENT STATUS")
        print(sep)
        print(f"  Agent ID     : {s['agent_id']} v{s['version']}")
        print(f"  Recipes saved: {s['recipe_count']}")
        print(f"  Food catalog : {'READY' if s['food_catalog_ready'] else 'EMPTY — sync food data first'} "
              f"({s['food_count']} foods)")
        print(sep)
        print()

    def print_recipe(self, recipe: Recipe) -> None:
        """Print a human-readable recipe card to stdout."""
        sep = "-" * 50
        print()
        print(sep)
        print(f"  RECIPE: {recipe.name}")
        print(sep)
        print(f"  ID       : {recipe.recipe_id}")
        print(f"  Servings : {recipe.servings}")
        print()
        print("  Ingredients:")
        for ing in recipe.ingredients:
            resolved = f"[{ing.food_id}]" if ing.food_id else "[UNRESOLVED]"
            print(f"    {ing.name_he:<20} {ing.quantity_g:>7.1f}g  {resolved}")

        if recipe.unresolved_ingredients:
            print()
            print(f"  WARNING: {len(recipe.unresolved_ingredients)} unresolved ingredient(s):")
            for u in recipe.unresolved_ingredients:
                print(f"    - {u}")

        if recipe.instructions:
            print()
            print("  Instructions:")
            for line in recipe.instructions.split("\n"):
                print(f"    {line}")

        if recipe.total_nutrition:
            t = recipe.total_nutrition
            p = recipe.per_serving_nutrition
            print()
            print(f"  {'':20} {'Total':>10}  {'Per Serving':>12}")
            print(f"  {'Calories':20} {t.calories_kcal:>10.1f}  {p.calories_kcal:>12.1f} kcal")
            print(f"  {'Protein':20} {t.protein_g:>10.1f}  {p.protein_g:>12.1f} g")
            print(f"  {'Carbs':20} {t.carbs_g:>10.1f}  {p.carbs_g:>12.1f} g")
            print(f"  {'Fat':20} {t.fat_g:>10.1f}  {p.fat_g:>12.1f} g")
            print(f"  {'Fiber':20} {t.fiber_g:>10.1f}  {p.fiber_g:>12.1f} g")
        print(sep)
        print()

    # ─── Internal Logic ───────────────────────────────────────────────

    def _resolve_ingredients(
        self, raw_ingredients: List[dict]
    ) -> Tuple[List[RecipeIngredient], List[str]]:
        """
        For each ingredient:
        1. Use food_id directly if provided and found in DB.
        2. Otherwise, search by name (Hebrew or English).
        3. If still not found, mark as unresolved.

        Returns (resolved_ingredients, unresolved_names).
        """
        resolved: List[RecipeIngredient] = []
        unresolved: List[str] = []

        for idx, raw in enumerate(raw_ingredients):
            name_he = raw.get("name_he", "").strip()
            name_en = raw.get("name_en", "")
            quantity_g = float(raw.get("quantity_g", 0.0))
            explicit_id = raw.get("food_id")
            ingredient_id = raw.get("ingredient_id") or f"ing_{uuid.uuid4().hex[:8]}"

            food_id = None

            # 1. Try explicit food_id
            if explicit_id:
                food = self._db.get_food_by_id(explicit_id)
                if food:
                    food_id = explicit_id
                    name_en = name_en or food.get("name_en", "")

            # 2. Try search by Hebrew name, then English name
            if food_id is None and name_he:
                matches = self._db.search_foods(name_he, limit=1)
                if matches:
                    food_id = matches[0]["food_id"]
                    name_en = name_en or matches[0].get("name_en", "")

            if food_id is None and name_en:
                matches = self._db.search_foods(name_en, limit=1)
                if matches:
                    food_id = matches[0]["food_id"]

            if food_id is None:
                unresolved.append(name_he or name_en or f"ingredient_{idx}")

            resolved.append(RecipeIngredient(
                ingredient_id=ingredient_id,
                name_he=name_he,
                name_en=name_en or None,
                food_id=food_id,
                quantity_g=quantity_g,
            ))

        return resolved, unresolved

    def _calculate_nutrition(
        self,
        ingredients: List[RecipeIngredient],
        servings: int,
    ) -> Tuple[RecipeNutrition, RecipeNutrition]:
        """
        Sum per-100g DB values × (quantity_g / 100) for all resolved ingredients.
        Returns (total_nutrition, per_serving_nutrition).
        """
        totals = {"calories_kcal": 0.0, "protein_g": 0.0,
                  "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}

        for ing in ingredients:
            if ing.food_id is None:
                continue  # unresolved — skip
            food = self._db.get_food_by_id(ing.food_id)
            if food is None:
                continue
            factor = ing.quantity_g / 100.0
            totals["calories_kcal"] += food["calories_kcal"] * factor
            totals["protein_g"] += food["protein_g"] * factor
            totals["carbs_g"] += food["carbs_g"] * factor
            totals["fat_g"] += food["fat_g"] * factor
            totals["fiber_g"] += food.get("fiber_g", 0.0) * factor

        total = RecipeNutrition(**{k: round(v, 1) for k, v in totals.items()})
        s = max(servings, 1)
        per_serving = RecipeNutrition(
            calories_kcal=round(total.calories_kcal / s, 1),
            protein_g=round(total.protein_g / s, 1),
            carbs_g=round(total.carbs_g / s, 1),
            fat_g=round(total.fat_g / s, 1),
            fiber_g=round(total.fiber_g / s, 1),
        )
        return total, per_serving


# ─── Validation ───────────────────────────────────────────────────────────────

def _validate_recipe_input(data: dict) -> None:
    if not data.get("name", "").strip():
        raise ValueError("Recipe 'name' is required and cannot be empty.")
    servings = data.get("servings")
    if servings is None or int(servings) < 1:
        raise ValueError("Recipe 'servings' must be an integer >= 1.")
    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list) or len(ingredients) == 0:
        raise ValueError("Recipe 'ingredients' must be a non-empty list.")
    for i, ing in enumerate(ingredients):
        if not ing.get("name_he", "").strip():
            raise ValueError(f"Ingredient {i} missing 'name_he'.")
        qty = ing.get("quantity_g")
        if qty is None or float(qty) <= 0:
            raise ValueError(f"Ingredient {i} 'quantity_g' must be > 0.")


# ─── DB Serialization ─────────────────────────────────────────────────────────

def _recipe_to_db_dict(recipe: Recipe) -> dict:
    d = recipe.to_dict()
    if recipe.total_nutrition:
        d.update({
            "total_calories_kcal": recipe.total_nutrition.calories_kcal,
            "total_protein_g": recipe.total_nutrition.protein_g,
            "total_carbs_g": recipe.total_nutrition.carbs_g,
            "total_fat_g": recipe.total_nutrition.fat_g,
            "total_fiber_g": recipe.total_nutrition.fiber_g,
        })
    if recipe.per_serving_nutrition:
        d.update({
            "per_serving_calories_kcal": recipe.per_serving_nutrition.calories_kcal,
            "per_serving_protein_g": recipe.per_serving_nutrition.protein_g,
            "per_serving_carbs_g": recipe.per_serving_nutrition.carbs_g,
            "per_serving_fat_g": recipe.per_serving_nutrition.fat_g,
            "per_serving_fiber_g": recipe.per_serving_nutrition.fiber_g,
        })
    return d


def _db_row_to_recipe(row: dict) -> Recipe:
    ingredients = [
        RecipeIngredient(
            ingredient_id=i["ingredient_id"],
            name_he=i["name_he"],
            name_en=i.get("name_en") or None,
            food_id=i.get("food_id"),
            quantity_g=i["quantity_g"],
        )
        for i in row.get("ingredients", [])
    ]
    total = RecipeNutrition(
        calories_kcal=row.get("total_calories_kcal", 0.0),
        protein_g=row.get("total_protein_g", 0.0),
        carbs_g=row.get("total_carbs_g", 0.0),
        fat_g=row.get("total_fat_g", 0.0),
        fiber_g=row.get("total_fiber_g", 0.0),
    )
    per_serving = RecipeNutrition(
        calories_kcal=row.get("per_serving_calories_kcal", 0.0),
        protein_g=row.get("per_serving_protein_g", 0.0),
        carbs_g=row.get("per_serving_carbs_g", 0.0),
        fat_g=row.get("per_serving_fat_g", 0.0),
        fiber_g=row.get("per_serving_fiber_g", 0.0),
    )
    return Recipe(
        recipe_id=row["recipe_id"],
        name=row["name"],
        servings=row["servings"],
        ingredients=ingredients,
        instructions=row.get("instructions", ""),
        total_nutrition=total,
        per_serving_nutrition=per_serving,
        unresolved_ingredients=row.get("unresolved_ingredients", []),
        source=row.get("source", "user"),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )
