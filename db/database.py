"""
SQLite persistence layer — Agent 7 responsibility.
Tables: foods, run_logs, recipes, recipe_ingredients.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional


_DEFAULT_DB = os.path.join("storage", "nutrition.db")

_CREATE_FOODS = """
CREATE TABLE IF NOT EXISTS foods (
    food_id           TEXT PRIMARY KEY,
    name_he           TEXT NOT NULL,
    name_en           TEXT NOT NULL,
    category          TEXT NOT NULL,
    calories_kcal     REAL NOT NULL,
    protein_g         REAL NOT NULL,
    carbs_g           REAL NOT NULL,
    fat_g             REAL NOT NULL,
    fiber_g           REAL DEFAULT 0.0,
    sugar_g           REAL DEFAULT 0.0,
    sodium_mg         REAL DEFAULT 0.0,
    default_unit      TEXT DEFAULT 'gram',
    default_serving_g REAL DEFAULT 100.0,
    aliases_he        TEXT DEFAULT '[]',
    aliases_en        TEXT DEFAULT '[]',
    is_custom         INTEGER DEFAULT 0,
    source            TEXT DEFAULT 'catalog',
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
)
"""

_CREATE_RUN_LOGS = """
CREATE TABLE IF NOT EXISTS run_logs (
    run_id        TEXT PRIMARY KEY,
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    items_fetched INTEGER DEFAULT 0,
    items_saved   INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_failed  INTEGER DEFAULT 0,
    errors        TEXT DEFAULT '[]',
    status        TEXT DEFAULT 'running'
)
"""

_CREATE_RECIPES = """
CREATE TABLE IF NOT EXISTS recipes (
    recipe_id                  TEXT PRIMARY KEY,
    name                       TEXT NOT NULL,
    servings                   INTEGER NOT NULL DEFAULT 1,
    instructions               TEXT DEFAULT '',
    total_calories_kcal        REAL DEFAULT 0.0,
    total_protein_g            REAL DEFAULT 0.0,
    total_carbs_g              REAL DEFAULT 0.0,
    total_fat_g                REAL DEFAULT 0.0,
    total_fiber_g              REAL DEFAULT 0.0,
    per_serving_calories_kcal  REAL DEFAULT 0.0,
    per_serving_protein_g      REAL DEFAULT 0.0,
    per_serving_carbs_g        REAL DEFAULT 0.0,
    per_serving_fat_g          REAL DEFAULT 0.0,
    per_serving_fiber_g        REAL DEFAULT 0.0,
    unresolved_ingredients     TEXT DEFAULT '[]',
    source                     TEXT DEFAULT 'user',
    created_at                 TEXT NOT NULL,
    updated_at                 TEXT NOT NULL
)
"""

_CREATE_RECIPE_INGREDIENTS = """
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    ingredient_id  TEXT PRIMARY KEY,
    recipe_id      TEXT NOT NULL,
    food_id        TEXT,
    name_he        TEXT NOT NULL,
    name_en        TEXT DEFAULT '',
    quantity_g     REAL NOT NULL,
    FOREIGN KEY(recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NutritionDB:
    def __init__(self, db_path: str = _DEFAULT_DB):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute(_CREATE_FOODS)
            conn.execute(_CREATE_RUN_LOGS)
            conn.execute(_CREATE_RECIPES)
            conn.execute(_CREATE_RECIPE_INGREDIENTS)
            conn.commit()

    # ─── Foods ───────────────────────────────────────────────────────

    def upsert_food(self, food: dict) -> str:
        """Insert or update a food. Returns 'inserted' or 'updated'."""
        now = _now()
        aliases_he = json.dumps(food.get("aliases_he", []), ensure_ascii=False)
        aliases_en = json.dumps(food.get("aliases_en", []), ensure_ascii=False)

        with self._conn() as conn:
            exists = conn.execute(
                "SELECT food_id FROM foods WHERE food_id = ?", (food["food_id"],)
            ).fetchone()

            if exists:
                conn.execute(
                    """UPDATE foods SET
                        name_he=?, name_en=?, category=?,
                        calories_kcal=?, protein_g=?, carbs_g=?, fat_g=?,
                        fiber_g=?, sugar_g=?, sodium_mg=?,
                        default_unit=?, default_serving_g=?,
                        aliases_he=?, aliases_en=?, source=?, updated_at=?
                    WHERE food_id=?""",
                    (
                        food["name_he"], food["name_en"], food["category"],
                        food["calories_kcal"], food["protein_g"],
                        food["carbs_g"], food["fat_g"],
                        food.get("fiber_g", 0.0), food.get("sugar_g", 0.0),
                        food.get("sodium_mg", 0.0),
                        food.get("default_unit", "gram"),
                        food.get("default_serving_g", 100.0),
                        aliases_he, aliases_en,
                        food.get("source", "catalog"),
                        now, food["food_id"],
                    ),
                )
                conn.commit()
                return "updated"
            else:
                conn.execute(
                    """INSERT INTO foods (
                        food_id, name_he, name_en, category,
                        calories_kcal, protein_g, carbs_g, fat_g,
                        fiber_g, sugar_g, sodium_mg,
                        default_unit, default_serving_g,
                        aliases_he, aliases_en,
                        is_custom, source, created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        food["food_id"], food["name_he"], food["name_en"],
                        food["category"],
                        food["calories_kcal"], food["protein_g"],
                        food["carbs_g"], food["fat_g"],
                        food.get("fiber_g", 0.0), food.get("sugar_g", 0.0),
                        food.get("sodium_mg", 0.0),
                        food.get("default_unit", "gram"),
                        food.get("default_serving_g", 100.0),
                        aliases_he, aliases_en,
                        1 if food.get("is_custom") else 0,
                        food.get("source", "catalog"),
                        now, now,
                    ),
                )
                conn.commit()
                return "inserted"

    def get_food_by_id(self, food_id: str) -> Optional[Dict]:
        """Return a food row as dict, or None if not found."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM foods WHERE food_id = ?", (food_id,)
            ).fetchone()
            return _row_to_food(row) if row else None

    def search_foods(self, query: str, limit: int = 10) -> List[Dict]:
        """Case-insensitive search across Hebrew/English names and aliases."""
        q = f"%{query.lower()}%"
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM foods
                   WHERE lower(name_he) LIKE ?
                      OR lower(name_en) LIKE ?
                      OR lower(aliases_he) LIKE ?
                      OR lower(aliases_en) LIKE ?
                   LIMIT ?""",
                (q, q, q, q, limit),
            ).fetchall()
        return [_row_to_food(r) for r in rows]

    def get_all_foods(self, category: Optional[str] = None) -> List[Dict]:
        """Return all foods, optionally filtered by category."""
        with self._conn() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM foods WHERE category = ? ORDER BY name_en",
                    (category,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM foods ORDER BY name_en"
                ).fetchall()
        return [_row_to_food(r) for r in rows]

    def get_food_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0]

    def get_db_size_kb(self) -> float:
        try:
            return round(os.path.getsize(self.db_path) / 1024, 1)
        except OSError:
            return 0.0

    def get_last_sync(self) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT ended_at FROM run_logs WHERE status='success' "
                "ORDER BY ended_at DESC LIMIT 1"
            ).fetchone()
            return row[0] if row else None

    def get_total_failed_items(self) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(items_failed), 0) FROM run_logs"
            ).fetchone()
            return int(row[0])

    def get_recent_run_logs(self, limit: int = 5) -> List[Dict]:
        """Return the most recent run log entries."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM run_logs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ─── Run Logs ─────────────────────────────────────────────────────

    def create_run_log(self, run_id: str, started_at: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO run_logs (run_id, started_at) VALUES (?, ?)",
                (run_id, started_at),
            )
            conn.commit()

    def update_run_log(self, run_id: str, **kwargs) -> None:
        if not kwargs:
            return
        for k, v in list(kwargs.items()):
            if isinstance(v, list):
                kwargs[k] = json.dumps(v, ensure_ascii=False)
        fields = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [run_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE run_logs SET {fields} WHERE run_id=?", values)
            conn.commit()

    # ─── Recipes ──────────────────────────────────────────────────────

    def save_recipe(self, recipe: dict) -> str:
        """Insert or replace a full recipe + its ingredients. Returns recipe_id."""
        now = _now()
        recipe_id = recipe["recipe_id"]
        unresolved = json.dumps(recipe.get("unresolved_ingredients", []), ensure_ascii=False)

        with self._conn() as conn:
            conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
            conn.execute(
                """INSERT OR REPLACE INTO recipes (
                    recipe_id, name, servings, instructions,
                    total_calories_kcal, total_protein_g, total_carbs_g, total_fat_g, total_fiber_g,
                    per_serving_calories_kcal, per_serving_protein_g, per_serving_carbs_g,
                    per_serving_fat_g, per_serving_fiber_g,
                    unresolved_ingredients, source, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    recipe_id,
                    recipe["name"],
                    recipe.get("servings", 1),
                    recipe.get("instructions", ""),
                    recipe.get("total_calories_kcal", 0.0),
                    recipe.get("total_protein_g", 0.0),
                    recipe.get("total_carbs_g", 0.0),
                    recipe.get("total_fat_g", 0.0),
                    recipe.get("total_fiber_g", 0.0),
                    recipe.get("per_serving_calories_kcal", 0.0),
                    recipe.get("per_serving_protein_g", 0.0),
                    recipe.get("per_serving_carbs_g", 0.0),
                    recipe.get("per_serving_fat_g", 0.0),
                    recipe.get("per_serving_fiber_g", 0.0),
                    unresolved,
                    recipe.get("source", "user"),
                    recipe.get("created_at", now),
                    now,
                ),
            )
            for ing in recipe.get("ingredients", []):
                conn.execute(
                    """INSERT INTO recipe_ingredients
                       (ingredient_id, recipe_id, food_id, name_he, name_en, quantity_g)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        ing["ingredient_id"],
                        recipe_id,
                        ing.get("food_id"),
                        ing["name_he"],
                        ing.get("name_en", ""),
                        ing["quantity_g"],
                    ),
                )
            conn.commit()
        return recipe_id

    def get_recipe(self, recipe_id: str) -> Optional[Dict]:
        """Return full recipe with ingredients, or None."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,)
            ).fetchone()
            if not row:
                return None
            recipe = dict(row)
            recipe["unresolved_ingredients"] = json.loads(recipe.get("unresolved_ingredients") or "[]")
            ingredients = conn.execute(
                "SELECT * FROM recipe_ingredients WHERE recipe_id = ? ORDER BY ingredient_id",
                (recipe_id,),
            ).fetchall()
            recipe["ingredients"] = [dict(i) for i in ingredients]
        return recipe

    def list_recipes(self) -> List[Dict]:
        """Return all recipes (without ingredient detail)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT recipe_id, name, servings, total_calories_kcal, "
                "per_serving_calories_kcal, per_serving_protein_g, source, created_at "
                "FROM recipes ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_recipe_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete recipe and its ingredients. Returns True if deleted."""
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM recipes WHERE recipe_id = ?", (recipe_id,))
            conn.commit()
            return cur.rowcount > 0


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _row_to_food(row: sqlite3.Row) -> Dict:
    d = dict(row)
    d["aliases_he"] = json.loads(d.get("aliases_he") or "[]")
    d["aliases_en"] = json.loads(d.get("aliases_en") or "[]")
    return d
