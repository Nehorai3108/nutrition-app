"""
Agent 11 -- Recipe Manager

Responsibility:
- Manage recipe database (load, save, search, filter)
- Recommend daily menus matching nutritional targets
- Resolve recipe ingredients against food catalog
- Seed built-in recipes on first run

Input:  NutritionTargets, RecipeFilter, MenuPreferences
Output: Filtered recipe lists, DailyMenu recommendations

Rules:
- Read-only against food catalog
- Writes only to storage_agents/recipes/recipes.json
- Deterministic recommendations (no randomness except date-based seed)
- Kashrut compliance enforced

Forbidden:
- AI generation
- Inventory modification
- Target calculation
- Contract changes
"""

import hashlib
import json
import os
from typing import Dict, List, Optional, Set

from nutrition_app.agents.agent_11_recipes.recipe_filter import (
    DailyMenu,
    MenuPreferences,
    RecipeFilter,
)

# ---- Meal distribution (same values as Agent 5, duplicated to avoid circular deps) ----
MEAL_DISTRIBUTION: Dict[str, float] = {
    "breakfast": 0.25,
    "morning_snack": 0.10,
    "lunch": 0.35,
    "afternoon_snack": 0.10,
    "dinner": 0.20,
}

# ---- Project root resolution ----
_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_AGENT_DIR)))
_DEFAULT_STORAGE = os.path.join(_PROJECT_ROOT, "storage_agents", "recipes")
_RECIPES_FILE = "recipes.json"


class RecipeManager:
    """Deterministic recipe database and menu recommendation engine."""

    def __init__(self, storage_dir: Optional[str] = None):
        self._storage_dir = storage_dir or _DEFAULT_STORAGE
        self._recipes_path = os.path.join(self._storage_dir, _RECIPES_FILE)

        # Internal state
        self._recipes: List[dict] = []
        self._by_id: Dict[str, dict] = {}
        self._by_meal_type: Dict[str, List[dict]] = {}
        self._by_kashrut: Dict[str, List[dict]] = {}
        self._by_tag: Dict[str, List[dict]] = {}

        # Load existing recipes
        self._recipes = self.load_recipes()
        self._build_indexes()

        # Seed built-in recipes if the database is empty
        if not self._recipes:
            self.seed_builtin_recipes()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load_recipes(self) -> List[dict]:
        """Load recipes from storage_agents/recipes/recipes.json."""
        if not os.path.isfile(self._recipes_path):
            return []
        try:
            with open(self._recipes_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, OSError):
            return []

    def save_recipes(self) -> None:
        """Persist current recipe list to JSON."""
        os.makedirs(self._storage_dir, exist_ok=True)
        with open(self._recipes_path, "w", encoding="utf-8") as fh:
            json.dump(self._recipes, fh, ensure_ascii=False, indent=2)

    def set_recipe_image(
        self,
        recipe_id: str,
        image_path: str,
        image_credit: Optional[str] = None,
    ) -> bool:
        """Assign an approved image path to a recipe and persist.

        Re-reads from disk before writing to avoid clobbering concurrent
        changes (the dashboard may edit recipes.json from another path).
        Returns True on success.
        """
        disk = self.load_recipes()
        found = False
        for rec in disk:
            if rec.get("recipe_id") == recipe_id:
                rec["image_path"] = image_path
                if image_credit is not None:
                    rec["image_credit"] = image_credit
                found = True
                break
        if not found:
            return False
        os.makedirs(self._storage_dir, exist_ok=True)
        with open(self._recipes_path, "w", encoding="utf-8") as fh:
            json.dump(disk, fh, ensure_ascii=False, indent=2)
        # Refresh in-memory state so subsequent lookups reflect the change.
        self._recipes = disk
        self._build_indexes()
        return True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def seed_builtin_recipes(self) -> None:
        """Import built-in recipes from the Agent 10 knowledge base.

        Only adds recipes whose recipe_id is not already present.
        """
        try:
            from nutrition_app.agents.agent_10_recipes.data_collector import (
                RECIPE_KNOWLEDGE_BASE,
            )
            builtin = RECIPE_KNOWLEDGE_BASE
        except (ImportError, AttributeError):
            builtin = []

        if not builtin:
            return

        existing_ids = {r["recipe_id"] for r in self._recipes}
        added = 0
        for recipe in builtin:
            if recipe.get("recipe_id") and recipe["recipe_id"] not in existing_ids:
                self._recipes.append(recipe)
                existing_ids.add(recipe["recipe_id"])
                added += 1

        if added:
            self._build_indexes()
            self.save_recipes()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_recipes(self, new_recipes: List[dict]) -> int:
        """Add recipes, deduplicate by recipe_id, rebuild indexes, save.

        Returns the count of newly added recipes.
        """
        existing_ids = {r["recipe_id"] for r in self._recipes}
        added = 0
        for recipe in new_recipes:
            rid = recipe.get("recipe_id")
            if rid and rid not in existing_ids:
                self._recipes.append(recipe)
                existing_ids.add(rid)
                added += 1

        if added:
            self._build_indexes()
            self.save_recipes()

        return added

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        """Look up a single recipe by its ID."""
        return self._by_id.get(recipe_id)

    # ------------------------------------------------------------------
    # Search / Filter
    # ------------------------------------------------------------------

    def search_recipes(self, recipe_filter: RecipeFilter) -> List[dict]:
        """Main query method: apply all filter criteria and return matches."""
        results: List[dict] = []

        for recipe in self._recipes:
            if not self._matches_filter(recipe, recipe_filter):
                continue
            results.append(recipe)
            if len(results) >= recipe_filter.max_results:
                break

        return results

    def _matches_filter(self, recipe: dict, f: RecipeFilter) -> bool:
        """Return True if *recipe* passes every criterion in *f*."""
        portions = max(recipe.get("portions", 1), 1)
        nut = recipe.get("total_nutrition", {})
        cal_per_portion = nut.get("calories", 0) / portions
        protein_per_portion = nut.get("protein", 0) / portions
        carbs_per_portion = nut.get("carbs", 0) / portions
        fat_per_portion = nut.get("fat", 0) / portions

        # Calorie range
        if f.calorie_min is not None and cal_per_portion < f.calorie_min:
            return False
        if f.calorie_max is not None and cal_per_portion > f.calorie_max:
            return False

        # Macro thresholds
        if f.protein_min_g is not None and protein_per_portion < f.protein_min_g:
            return False
        if f.carbs_max_g is not None and carbs_per_portion > f.carbs_max_g:
            return False
        if f.fat_max_g is not None and fat_per_portion > f.fat_max_g:
            return False

        # Meal types
        if f.meal_types:
            upper_types = {mt.upper() for mt in f.meal_types}
            recipe_types = {mt.upper() for mt in recipe.get("meal_types", [])}
            if not upper_types & recipe_types:
                return False

        # Kashrut
        if f.kashrut is not None:
            if recipe.get("kashrut", "parve").lower() != f.kashrut.lower():
                return False

        # Tags include (must have ALL)
        if f.tags_include:
            recipe_tags = {t.lower() for t in recipe.get("tags", [])}
            for tag in f.tags_include:
                if tag.lower() not in recipe_tags:
                    return False

        # Tags exclude (must have NONE)
        if f.tags_exclude:
            recipe_tags = {t.lower() for t in recipe.get("tags", [])}
            for tag in f.tags_exclude:
                if tag.lower() in recipe_tags:
                    return False

        # Prep time
        if f.max_prep_time_minutes is not None:
            if recipe.get("prep_time_minutes", 0) > f.max_prep_time_minutes:
                return False

        # Search text (case-insensitive substring against name_he and name_en)
        # Also checks Hebrew root prefix: "חביתה" matches "חביתת" (construct state)
        if f.search_text:
            query = f.search_text.lower().strip()
            name_he = recipe.get("name_he", "").lower()
            name_en = recipe.get("name_en", "").lower()
            tags = " ".join(recipe.get("tags", [])).lower()
            # Direct substring match
            if query in name_he or query in name_en or query in tags:
                pass  # match
            else:
                # Hebrew morphology: try stripping last char for construct state
                root = query[:-1] if len(query) > 2 else query
                if root not in name_he and root not in name_en:
                    return False

        return True

    # ------------------------------------------------------------------
    # Menu Recommendation
    # ------------------------------------------------------------------

    def recommend_daily_menu(
        self,
        targets,
        preferences: Optional[MenuPreferences] = None,
    ) -> DailyMenu:
        """Build a daily menu that matches nutritional targets.

        Args:
            targets: NutritionTargets (or any object / dict with
                     target_calories_kcal, protein_g, carbs_g, fat_g).
            preferences: Optional MenuPreferences for kashrut, variety, etc.

        Returns:
            A DailyMenu dataclass.
        """
        if preferences is None:
            preferences = MenuPreferences()

        # Extract target values -- support both NutritionTargets objects and dicts
        if isinstance(targets, dict):
            total_cal = targets.get("target_calories_kcal", 2000)
            total_protein = targets.get("protein_g", 120)
            total_carbs = targets.get("carbs_g", 250)
            total_fat = targets.get("fat_g", 65)
        else:
            total_cal = getattr(targets, "target_calories_kcal", 2000)
            total_protein = getattr(targets, "protein_g", 120)
            total_carbs = getattr(targets, "carbs_g", 250)
            total_fat = getattr(targets, "fat_g", 65)

        # Date-based seed for deterministic variety rotation
        today = _today_str()
        day_hash = int(hashlib.md5(today.encode()).hexdigest(), 16)

        meals: Dict[str, dict] = {}
        used_ids: Set[str] = set(preferences.exclude_recipe_ids)
        total_prep = 0
        sum_cal = 0.0
        sum_protein = 0.0
        sum_carbs = 0.0
        sum_fat = 0.0
        kashrut_valid = True

        # Track kashrut state for the day
        day_has_meat = False
        day_has_dairy = False

        for meal_type, fraction in MEAL_DISTRIBUTION.items():
            slot_cal = total_cal * fraction
            slot_protein = total_protein * fraction
            slot_carbs = total_carbs * fraction
            slot_fat = total_fat * fraction

            # Map meal_type string to uppercase key used in recipe data
            meal_key = meal_type.upper()

            # Get candidate recipes for this meal type
            candidates = self._by_meal_type.get(meal_key, [])

            # Apply kashrut filtering based on preferences
            candidates = self._filter_kashrut(
                candidates, preferences.kashrut_mode, day_has_meat, day_has_dairy
            )

            # Score and rank
            scored: List[tuple] = []
            for idx, recipe in enumerate(candidates):
                rid = recipe.get("recipe_id", "")
                if rid in used_ids:
                    continue
                score = self._score_recipe(
                    recipe,
                    slot_cal,
                    slot_protein,
                    slot_carbs,
                    slot_fat,
                    preferences,
                    used_ids,
                )
                # Apply day-hash rotation for variety
                rotation_bonus = ((day_hash + idx) % 100) / 1000.0
                scored.append((score + rotation_bonus, recipe))

            scored.sort(key=lambda x: x[0], reverse=True)

            if scored:
                best_recipe = scored[0][1]
                rid = best_recipe.get("recipe_id", "")
                used_ids.add(rid)

                portions = max(best_recipe.get("portions", 1), 1)
                nut = best_recipe.get("total_nutrition", {})
                r_cal = nut.get("calories", 0) / portions
                r_protein = nut.get("protein", 0) / portions
                r_carbs = nut.get("carbs", 0) / portions
                r_fat = nut.get("fat", 0) / portions

                sum_cal += r_cal
                sum_protein += r_protein
                sum_carbs += r_carbs
                sum_fat += r_fat
                total_prep += best_recipe.get("prep_time_minutes", 0)

                # Update kashrut state
                rk = best_recipe.get("kashrut", "parve").lower()
                if rk == "meat":
                    day_has_meat = True
                elif rk == "dairy":
                    day_has_dairy = True

                meals[meal_type] = best_recipe
            else:
                meals[meal_type] = {}

        # Check kashrut validity
        if day_has_meat and day_has_dairy:
            if preferences.kashrut_mode in ("strict_dairy", "strict_meat"):
                kashrut_valid = False
            # In flexible mode, meat + dairy in different meals is flagged but tolerated
            if preferences.kashrut_mode == "flexible":
                kashrut_valid = True
            if preferences.kashrut_mode == "parve_only":
                kashrut_valid = False

        # Prep time constraint
        if preferences.max_prep_time_total and total_prep > preferences.max_prep_time_total:
            # Still return the menu but it exceeds the time budget
            pass

        # Deviation calculation
        def _pct_dev(actual: float, target: float) -> float:
            if target == 0:
                return 0.0
            return round(((actual - target) / target) * 100, 1)

        deviation = {
            "calories_pct": _pct_dev(sum_cal, total_cal),
            "protein_pct": _pct_dev(sum_protein, total_protein),
            "carbs_pct": _pct_dev(sum_carbs, total_carbs),
            "fat_pct": _pct_dev(sum_fat, total_fat),
        }

        total_nutrition = {
            "calories": round(sum_cal, 1),
            "protein": round(sum_protein, 1),
            "carbs": round(sum_carbs, 1),
            "fat": round(sum_fat, 1),
        }

        return DailyMenu(
            date=today,
            meals=meals,
            total_nutrition=total_nutrition,
            deviation_from_targets=deviation,
            total_prep_time=total_prep,
            kashrut_valid=kashrut_valid,
        )

    # Mapping from Hebrew allergy name → English ingredient keywords to exclude
    ALLERGEN_INGREDIENT_KEYWORDS: Dict[str, List[str]] = {
        "לקטוז": ["milk", "cheese", "cream", "yogurt", "butter", "dairy",
                  "whey", "lactose", "mozzarella", "parmesan", "cottage",
                  "ricotta", "brie", "feta", "cheddar", "gouda"],
        "גלוטן": ["wheat", "flour", "bread", "pasta", "barley", "rye",
                  "gluten", "couscous", "bulgur", "semolina", "oat",
                  "noodle", "pita", "cracker", "biscuit"],
        "בוטנים": ["peanut", "peanuts", "groundnut"],
        "אגוזים": ["almond", "cashew", "walnut", "pecan", "hazelnut",
                   "pistachio", "macadamia", "nut", "nuts"],
        "ביצים": ["egg", "eggs"],
        "דגים":  ["fish", "salmon", "tuna", "cod", "tilapia", "trout",
                  "herring", "anchovy", "sardine", "halibut", "sea bass"],
        "סויה":  ["soy", "tofu", "tempeh", "edamame", "miso", "soybean"],
        "שומשום": ["sesame", "tahini"],
    }

    def _recipe_contains_allergen(self, recipe: dict, allergens: List[str]) -> bool:
        """Return True if the recipe likely contains any of the given allergens."""
        # Check kashrut: dairy recipes contain lactose
        if "לקטוז" in allergens and recipe.get("kashrut", "").lower() == "dairy":
            return True

        # Build a set of all ingredient name_en values (lowercase)
        ing_names_en = set()
        for ing in recipe.get("ingredients", []):
            name_en = ing.get("food_name_en", "").lower()
            if name_en:
                ing_names_en.add(name_en)
                # also check individual words
                for word in name_en.split():
                    ing_names_en.add(word)

        for allergen in allergens:
            keywords = self.ALLERGEN_INGREDIENT_KEYWORDS.get(allergen, [])
            for kw in keywords:
                if any(kw in ing for ing in ing_names_en):
                    return True
        return False

    def _recipe_contains_disliked(self, recipe: dict, disliked: List[str]) -> bool:
        """Return True if the recipe name or ingredients contain any disliked food."""
        if not disliked:
            return False
        # Build searchable text: Hebrew name + all ingredient names
        name_he = recipe.get("name_he", "").lower()
        name_en = recipe.get("name_en", "").lower()
        ing_text = " ".join(
            (ing.get("food_name_he", "") + " " + ing.get("food_name_en", "")).lower()
            for ing in recipe.get("ingredients", [])
        )
        full_text = f"{name_he} {name_en} {ing_text}"
        for food in disliked:
            if food.strip().lower() in full_text:
                return True
        return False

    def recommend_meal(
        self,
        meal_type: str,
        target_calories: float,
        kashrut: Optional[str] = None,
        inventory_names: Optional[Set[str]] = None,
        allergens: Optional[List[str]] = None,
        disliked_foods: Optional[List[str]] = None,
        variation_seed: int = 0,
    ) -> List[dict]:
        """Find top 5 recipes for a specific meal slot.

        Args:
            meal_type: e.g. "BREAKFAST", "LUNCH"
            target_calories: calorie target for this slot
            kashrut: optional kashrut filter ("dairy", "meat", "parve")
            allergens: list of Hebrew allergy names to exclude (e.g. ["לקטוז", "גלוטן"])
            disliked_foods: list of Hebrew food names to avoid (e.g. ["אורז", "עוף"])

        Returns:
            Up to 5 best-matching recipes sorted by fit score.
        """
        meal_key = meal_type.upper()
        candidates = self._by_meal_type.get(meal_key, [])

        if kashrut is not None:
            candidates = [
                r for r in candidates
                if r.get("kashrut", "parve").lower() == kashrut.lower()
            ]

        # Filter out recipes containing user allergens
        if allergens:
            candidates = [
                r for r in candidates
                if not self._recipe_contains_allergen(r, allergens)
            ]

        # Filter out recipes containing disliked foods
        if disliked_foods:
            candidates = [
                r for r in candidates
                if not self._recipe_contains_disliked(r, disliked_foods)
            ]

        # Estimate macro targets from calorie target using typical ratios
        est_protein = target_calories * 0.30 / 4.0  # 30% from protein
        est_carbs = target_calories * 0.45 / 4.0  # 45% from carbs
        est_fat = target_calories * 0.25 / 9.0  # 25% from fat

        scored: List[tuple] = []
        for recipe in candidates:
            score = self._score_recipe(
                recipe,
                target_calories,
                est_protein,
                est_carbs,
                est_fat,
                MenuPreferences(),
                set(),
                inventory_names=inventory_names,
            )
            scored.append((score, recipe))

        scored.sort(key=lambda x: x[0], reverse=True)
        # קח את 15 המתכונים הטובים ביותר, ואז ערבב לפי seed לוריאציה
        import random as _random
        top_pool = scored[:15]
        if variation_seed != 0:
            _random.seed(variation_seed)
            _random.shuffle(top_pool)
            _random.seed()  # reset seed
        return [r for _, r in top_pool[:5]]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return recipe counts by meal_type, kashrut, total count, etc."""
        meal_type_counts: Dict[str, int] = {}
        for mt, recipes in self._by_meal_type.items():
            meal_type_counts[mt] = len(recipes)

        kashrut_counts: Dict[str, int] = {}
        for k, recipes in self._by_kashrut.items():
            kashrut_counts[k] = len(recipes)

        tag_counts: Dict[str, int] = {}
        for t, recipes in self._by_tag.items():
            tag_counts[t] = len(recipes)

        return {
            "total_recipes": len(self._recipes),
            "by_meal_type": meal_type_counts,
            "by_kashrut": kashrut_counts,
            "by_tag": tag_counts,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:
        """Build internal lookup dicts: by_id, by_meal_type, by_kashrut, by_tag."""
        self._by_id = {}
        self._by_meal_type = {}
        self._by_kashrut = {}
        self._by_tag = {}

        for recipe in self._recipes:
            rid = recipe.get("recipe_id", "")
            if rid:
                self._by_id[rid] = recipe

            for mt in recipe.get("meal_types", []):
                key = mt.upper()
                self._by_meal_type.setdefault(key, []).append(recipe)

            k = recipe.get("kashrut", "parve").lower()
            self._by_kashrut.setdefault(k, []).append(recipe)

            for tag in recipe.get("tags", []):
                tag_lower = tag.lower()
                self._by_tag.setdefault(tag_lower, []).append(recipe)

    def _score_recipe(
        self,
        recipe: dict,
        target_calories: float,
        target_protein: float,
        target_carbs: float,
        target_fat: float,
        preferences: MenuPreferences,
        used_ids: Set[str],
        inventory_names: Optional[Set[str]] = None,
    ) -> float:
        """Score a recipe for a meal slot. Higher = better fit.

        Weights (without inventory):
          - calorie deviation: 0.4
          - protein match:     0.2
          - macro balance:     0.2
          - variety:           0.1
          - tag preference:    0.1

        When inventory_names provided, weights shift to include:
          - inventory match:   0.2  (rescaled from calorie/protein/macro)
          - calorie deviation: 0.3
          - protein match:     0.15
          - macro balance:     0.15
          - variety:           0.1
          - tag preference:    0.1
        """
        portions = max(recipe.get("portions", 1), 1)
        nut = recipe.get("total_nutrition", {})
        cal = nut.get("calories", 0) / portions
        protein = nut.get("protein", 0) / portions
        carbs = nut.get("carbs", 0) / portions
        fat = nut.get("fat", 0) / portions

        use_inventory = inventory_names is not None and len(inventory_names) > 0

        cal_w     = 0.30 if use_inventory else 0.40
        prot_w    = 0.15 if use_inventory else 0.20
        macro_w   = 0.15 if use_inventory else 0.20

        # --- Calorie proximity ---
        if target_calories > 0:
            cal_dev = abs(cal - target_calories) / target_calories
        else:
            cal_dev = 0.0
        cal_score = max(0.0, 1.0 - cal_dev) * cal_w

        # --- Protein match ---
        if target_protein > 0:
            prot_dev = abs(protein - target_protein) / target_protein
        else:
            prot_dev = 0.0
        protein_score = max(0.0, 1.0 - prot_dev) * prot_w

        # --- Macro balance ---
        if target_carbs > 0:
            carbs_dev = abs(carbs - target_carbs) / target_carbs
        else:
            carbs_dev = 0.0
        if target_fat > 0:
            fat_dev = abs(fat - target_fat) / target_fat
        else:
            fat_dev = 0.0
        macro_score = max(0.0, 1.0 - (carbs_dev + fat_dev) / 2.0) * macro_w

        # --- Variety (weight 0.1) ---
        rid = recipe.get("recipe_id", "")
        variety_score = 0.1 if rid not in used_ids else 0.0
        variety_score *= preferences.variety_weight

        # --- Tag preference (weight 0.1) ---
        tag_score = 0.0
        if preferences.preferred_tags:
            recipe_tags = {t.lower() for t in recipe.get("tags", [])}
            matching = sum(
                1 for pt in preferences.preferred_tags if pt.lower() in recipe_tags
            )
            tag_score = (matching / len(preferences.preferred_tags)) * 0.1

        # --- Inventory match (weight 0.2, only when inventory provided) ---
        inventory_score = 0.0
        if use_inventory:
            ingredients = recipe.get("ingredients", [])
            if ingredients:
                matched = sum(
                    1 for ing in ingredients
                    if _ingredient_in_inventory(ing, inventory_names)
                )
                inventory_score = (matched / len(ingredients)) * 0.2

        return cal_score + protein_score + macro_score + variety_score + tag_score + inventory_score

    def _filter_kashrut(
        self,
        candidates: List[dict],
        mode: str,
        day_has_meat: bool,
        day_has_dairy: bool,
    ) -> List[dict]:
        """Filter candidates based on kashrut mode and current day state."""
        if mode == "strict_meat":
            # Only meat and parve allowed
            return [
                r for r in candidates
                if r.get("kashrut", "parve").lower() in ("meat", "parve")
            ]
        elif mode == "strict_dairy":
            # Only dairy and parve allowed
            return [
                r for r in candidates
                if r.get("kashrut", "parve").lower() in ("dairy", "parve")
            ]
        elif mode == "parve_only":
            return [
                r for r in candidates
                if r.get("kashrut", "parve").lower() == "parve"
            ]
        elif mode == "flexible":
            # In flexible mode, avoid mixing meat + dairy in the same day
            if day_has_meat:
                return [
                    r for r in candidates
                    if r.get("kashrut", "parve").lower() != "dairy"
                ]
            if day_has_dairy:
                return [
                    r for r in candidates
                    if r.get("kashrut", "parve").lower() != "meat"
                ]
            return candidates
        return candidates


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------

def _today_str() -> str:
    """Return today's date as YYYY-MM-DD (no external deps)."""
    import datetime as _dt

    return _dt.date.today().isoformat()


def _ingredient_in_inventory(ingredient: dict, inventory_names: Set[str]) -> bool:
    """Check if a recipe ingredient matches any item in the user's inventory.

    Matches by English food name (case-insensitive substring), so
    "olive oil" in inventory matches ingredient food_name_en="olive oil".
    """
    food_name_en = ingredient.get("food_name_en", "").lower().strip()
    food_name_he = ingredient.get("food_name", "").lower().strip()
    if not food_name_en and not food_name_he:
        return False
    for inv_name in inventory_names:
        inv = inv_name.lower()
        if food_name_en and (food_name_en in inv or inv in food_name_en):
            return True
        if food_name_he and (food_name_he in inv or inv in food_name_he):
            return True
    return False


def get_recipe_inventory_match(recipe: dict, inventory_names: Set[str]) -> dict:
    """Return per-ingredient availability info for a recipe.

    Returns:
        {
            "available": [{"food_name": ..., "food_name_en": ...}, ...],
            "missing":   [{"food_name": ..., "food_name_en": ...}, ...],
            "match_pct": 0-100,
        }
    """
    ingredients = recipe.get("ingredients", [])
    if not ingredients:
        return {"available": [], "missing": [], "match_pct": 100}

    available = []
    missing = []
    for ing in ingredients:
        if _ingredient_in_inventory(ing, inventory_names):
            available.append(ing)
        else:
            missing.append(ing)

    match_pct = round(len(available) / len(ingredients) * 100)
    return {"available": available, "missing": missing, "match_pct": match_pct}
