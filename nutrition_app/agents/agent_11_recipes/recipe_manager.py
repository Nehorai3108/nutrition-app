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
        if f.search_text:
            query = f.search_text.lower()
            name_he = recipe.get("name_he", "").lower()
            name_en = recipe.get("name_en", "").lower()
            if query not in name_he and query not in name_en:
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

    def recommend_meal(
        self,
        meal_type: str,
        target_calories: float,
        kashrut: Optional[str] = None,
    ) -> List[dict]:
        """Find top 5 recipes for a specific meal slot.

        Args:
            meal_type: e.g. "BREAKFAST", "LUNCH"
            target_calories: calorie target for this slot
            kashrut: optional kashrut filter ("dairy", "meat", "parve")

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
            )
            scored.append((score, recipe))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:5]]

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
    ) -> float:
        """Score a recipe for a meal slot. Higher = better fit.

        Weights:
          - calorie deviation: 0.4
          - protein match:     0.2
          - macro balance:     0.2
          - variety:           0.1
          - tag preference:    0.1
        """
        portions = max(recipe.get("portions", 1), 1)
        nut = recipe.get("total_nutrition", {})
        cal = nut.get("calories", 0) / portions
        protein = nut.get("protein", 0) / portions
        carbs = nut.get("carbs", 0) / portions
        fat = nut.get("fat", 0) / portions

        # --- Calorie proximity (weight 0.4) ---
        if target_calories > 0:
            cal_dev = abs(cal - target_calories) / target_calories
        else:
            cal_dev = 0.0
        cal_score = max(0.0, 1.0 - cal_dev) * 0.4

        # --- Protein match (weight 0.2) ---
        if target_protein > 0:
            prot_dev = abs(protein - target_protein) / target_protein
        else:
            prot_dev = 0.0
        protein_score = max(0.0, 1.0 - prot_dev) * 0.2

        # --- Macro balance (weight 0.2) ---
        if target_carbs > 0:
            carbs_dev = abs(carbs - target_carbs) / target_carbs
        else:
            carbs_dev = 0.0
        if target_fat > 0:
            fat_dev = abs(fat - target_fat) / target_fat
        else:
            fat_dev = 0.0
        macro_score = max(0.0, 1.0 - (carbs_dev + fat_dev) / 2.0) * 0.2

        # --- Variety (weight 0.1) ---
        rid = recipe.get("recipe_id", "")
        variety_score = 0.1 if rid not in used_ids else 0.0
        # Scale by preference weight
        variety_score *= preferences.variety_weight

        # --- Tag preference (weight 0.1) ---
        tag_score = 0.0
        if preferences.preferred_tags:
            recipe_tags = {t.lower() for t in recipe.get("tags", [])}
            matching = sum(
                1 for pt in preferences.preferred_tags if pt.lower() in recipe_tags
            )
            tag_score = (matching / len(preferences.preferred_tags)) * 0.1

        return cal_score + protein_score + macro_score + variety_score + tag_score

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
