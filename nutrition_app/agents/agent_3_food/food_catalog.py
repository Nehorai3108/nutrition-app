"""
Agent 3 — Food Catalog & Matching Owner

Responsibility:
- Food database management
- Search and matching by name
- Hebrew/English aliases
- Normalization
- Custom food entries support
- Confidence scoring for matches

Input:  food names, scanned text (future), custom entries
Output: List[FoodItem] or FoodMatchResult

Rules:
- FoodItem is nutritional source of truth
- Consistent structure
- Low-confidence must be flagged

Forbidden:
- Meal plan construction
- Nutrition target calculation
- Inventory management
- Deduction
"""

import json
import os
import re
import unicodedata
from typing import Dict, List, Optional

from nutrition_app.models.food_item import FoodItem, NutritionPer100g
from nutrition_app.models.food_match import FoodMatch, FoodMatchResult
from nutrition_app.models.enums import ConfidenceLevel, FoodCategory, UnitType

# Path to extended catalog data
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data")


def _db_row_to_food_item(row: dict) -> FoodItem:
    """Convert a NutritionDB food row dict to a FoodItem."""
    return FoodItem(
        food_id=row["food_id"],
        name_he=row["name_he"],
        name_en=row["name_en"],
        category=FoodCategory(row["category"]),
        nutrition_per_100g=NutritionPer100g(
            calories_kcal=row["calories_kcal"],
            protein_g=row["protein_g"],
            carbs_g=row["carbs_g"],
            fat_g=row["fat_g"],
            fiber_g=row.get("fiber_g", 0.0),
            sugar_g=row.get("sugar_g", 0.0),
            sodium_mg=row.get("sodium_mg", 0.0),
        ),
        default_unit=UnitType(row.get("default_unit", "gram")),
        default_serving_g=row.get("default_serving_g", 100.0),
        aliases_he=row.get("aliases_he", []),
        aliases_en=row.get("aliases_en", []),
        is_custom=bool(row.get("is_custom", 0)),
        source=row.get("source", "catalog"),
    )


class FoodCatalog:
    """Food database with search, matching, and alias support."""

    def __init__(self, load_extended: bool = True, db_path: Optional[str] = None):
        self._foods: Dict[str, FoodItem] = {}
        if db_path is not None:
            loaded = self.load_from_db(db_path)
            if loaded == 0:
                # DB exists but is empty — fall back to static catalog
                self._load_default_catalog()
                if load_extended:
                    self.load_extended_catalog()
        else:
            self._load_default_catalog()
            if load_extended:
                self.load_extended_catalog()

    def load_from_db(self, db_path: str) -> int:
        """Load all foods from NutritionDB into the catalog.

        Returns the number of foods loaded. On any error returns 0 and
        leaves self._foods unchanged so callers can fall back gracefully.
        """
        try:
            from db.database import NutritionDB
            db = NutritionDB(db_path)
            rows = db.get_all_foods()
        except Exception:
            return 0

        count = 0
        for row in rows:
            try:
                food = _db_row_to_food_item(row)
                self._foods[food.food_id] = food
                count += 1
            except Exception:
                pass
        return count

    def _load_default_catalog(self):
        """Load built-in food catalog. In production, this reads from data/."""
        default_foods = [
            FoodItem(
                food_id="food_001", name_he="חזה עוף", name_en="Chicken Breast",
                category=FoodCategory.PROTEIN,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=165.0, protein_g=31.0, carbs_g=0.0, fat_g=3.6
                ),
                default_serving_g=150.0,
                aliases_he=["עוף", "חזה", "פילה עוף"],
                aliases_en=["chicken", "breast", "chicken fillet"],
            ),
            FoodItem(
                food_id="food_002", name_he="אורז לבן", name_en="White Rice",
                category=FoodCategory.GRAIN,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=130.0, protein_g=2.7, carbs_g=28.0, fat_g=0.3,
                    fiber_g=0.4
                ),
                default_serving_g=150.0,
                aliases_he=["אורז", "אורז מבושל"],
                aliases_en=["rice", "cooked rice", "steamed rice"],
            ),
            FoodItem(
                food_id="food_003", name_he="ביצה", name_en="Egg",
                category=FoodCategory.PROTEIN,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=155.0, protein_g=13.0, carbs_g=1.1, fat_g=11.0
                ),
                default_unit=UnitType.UNIT,
                default_serving_g=50.0,
                aliases_he=["ביצים", "ביצה קשה", "ביצה רכה"],
                aliases_en=["eggs", "boiled egg", "hard boiled egg"],
            ),
            FoodItem(
                food_id="food_004", name_he="בננה", name_en="Banana",
                category=FoodCategory.FRUIT,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=89.0, protein_g=1.1, carbs_g=22.8, fat_g=0.3,
                    fiber_g=2.6, sugar_g=12.2
                ),
                default_unit=UnitType.UNIT,
                default_serving_g=120.0,
                aliases_he=["בננות"],
                aliases_en=["bananas"],
            ),
            FoodItem(
                food_id="food_005", name_he="שמן זית", name_en="Olive Oil",
                category=FoodCategory.FAT,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=884.0, protein_g=0.0, carbs_g=0.0, fat_g=100.0
                ),
                default_unit=UnitType.TABLESPOON,
                default_serving_g=14.0,
                aliases_he=["שמן", "זית"],
                aliases_en=["oil", "olive"],
            ),
            FoodItem(
                food_id="food_006", name_he="חלב", name_en="Milk",
                category=FoodCategory.DAIRY,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=42.0, protein_g=3.4, carbs_g=5.0, fat_g=1.0
                ),
                default_unit=UnitType.CUP,
                default_serving_g=250.0,
                aliases_he=["חלב רגיל", "חלב 1%"],
                aliases_en=["milk 1%", "low fat milk"],
            ),
            FoodItem(
                food_id="food_007", name_he="לחם מחיטה מלאה", name_en="Whole Wheat Bread",
                category=FoodCategory.GRAIN,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=247.0, protein_g=13.0, carbs_g=41.0, fat_g=3.4,
                    fiber_g=7.0
                ),
                default_unit=UnitType.SLICE,
                default_serving_g=30.0,
                aliases_he=["לחם", "לחם מלא", "פרוסת לחם"],
                aliases_en=["bread", "whole wheat", "wheat bread"],
            ),
            FoodItem(
                food_id="food_008", name_he="עגבנייה", name_en="Tomato",
                category=FoodCategory.VEGETABLE,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=18.0, protein_g=0.9, carbs_g=3.9, fat_g=0.2,
                    fiber_g=1.2
                ),
                default_unit=UnitType.UNIT,
                default_serving_g=120.0,
                aliases_he=["עגבניות", "עגבניה"],
                aliases_en=["tomatoes"],
            ),
            FoodItem(
                food_id="food_009", name_he="מלפפון", name_en="Cucumber",
                category=FoodCategory.VEGETABLE,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=15.0, protein_g=0.7, carbs_g=3.6, fat_g=0.1,
                    fiber_g=0.5
                ),
                default_unit=UnitType.UNIT,
                default_serving_g=100.0,
                aliases_he=["מלפפונים"],
                aliases_en=["cucumbers"],
            ),
            FoodItem(
                food_id="food_010", name_he="גבינת קוטג׳", name_en="Cottage Cheese",
                category=FoodCategory.DAIRY,
                nutrition_per_100g=NutritionPer100g(
                    calories_kcal=98.0, protein_g=11.0, carbs_g=3.4, fat_g=4.3
                ),
                default_serving_g=100.0,
                aliases_he=["קוטג", "קוטג׳", "גבינה לבנה"],
                aliases_en=["cottage", "cottage cheese 5%"],
            ),
        ]
        for food in default_foods:
            self._foods[food.food_id] = food

    def load_extended_catalog(self):
        """Load extended food catalog from data/foods_extended.json."""
        ext_path = os.path.join(_DATA_DIR, "foods_extended.json")
        if not os.path.isfile(ext_path):
            return
        try:
            with open(ext_path, "r", encoding="utf-8") as f:
                foods_data = json.load(f)
            for fd in foods_data:
                try:
                    food = FoodItem.from_dict(fd)
                    if food.food_id not in self._foods:
                        self._foods[food.food_id] = food
                except Exception:
                    pass  # Skip individual bad entries without crashing
        except (json.JSONDecodeError, OSError, KeyError, Exception):
            pass

    def _normalize(self, text: str) -> str:
        text = text.strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[^\w\s\u0590-\u05FF]", "", text)
        return text

    def get_food_by_id(self, food_id: str) -> Optional[FoodItem]:
        return self._foods.get(food_id)

    def search_foods(self, query: str, limit: int = 10) -> List[FoodItem]:
        """Return top-N foods ranked by relevance score.

        Priority order:
          1. Exact Hebrew name match  (score 1.0)
          2. Exact English / alias match (score 0.95)
          3. Partial match, scored by position & length
          4. Foods from 'json' source (Hebrew DB) rank above USDA/OFF
          5. Foods with valid calorie data rank above NULL-calorie entries
        """
        if not query:
            # No query — return foods from our Hebrew catalog first
            scored = []
            for food in self._foods.values():
                has_cal = food.nutrition_per_100g.calories_kcal is not None
                src_rank = 0 if food.source == "json" else (1 if food.source == "off" else 2)
                scored.append((src_rank, 0 if has_cal else 1, food.name_he, food))
            scored.sort(key=lambda x: x[:3])
            return [x[3] for x in scored[:limit]]

        nq = self._normalize(query)
        scored: list[tuple] = []

        for food in self._foods.values():
            score = self._score_match_extended(nq, food)
            if score > 0:
                scored.append((score, food))

        # Sort: highest score first; break ties by source (json > off > usda)
        SOURCE_RANK = {"json": 0, "off": 1, "usda": 2, "manual": 0}
        scored.sort(
            key=lambda x: (
                -x[0],                                          # higher score first
                SOURCE_RANK.get(x[1].source or "", 3),         # Hebrew DB first
                0 if x[1].nutrition_per_100g.calories_kcal else 1,  # has calories
                x[1].name_he,
            )
        )
        return [f for _, f in scored[:limit]]

    def _score_match_extended(self, nq: str, food: FoodItem) -> float:
        """Extended scoring: exact > alias > starts-with > contains."""
        if not nq:
            return 0.5

        name_he = self._normalize(food.name_he or "")
        name_en = self._normalize(food.name_en or "")

        # Exact match
        if nq == name_he or nq == name_en:
            return 1.0

        # Alias exact match
        for alias in (food.aliases_he or []) + (food.aliases_en or []):
            if nq == self._normalize(alias):
                return 0.95

        # Starts-with (Hebrew preferred)
        if name_he.startswith(nq):
            return 0.85
        if name_en.startswith(nq):
            return 0.80

        # Query is inside name
        if nq in name_he:
            # Longer name → less specific match → lower score
            return max(0.4, 0.75 - len(name_he) * 0.005)
        if nq in name_en:
            return max(0.3, 0.65 - len(name_en) * 0.005)

        # Name is inside query (e.g. query="חזה עוף מבושל", name="חזה עוף")
        if name_he and name_he in nq:
            return 0.55
        if name_en and name_en in nq:
            return 0.45

        # Alias partial
        for alias in (food.aliases_he or []) + (food.aliases_en or []):
            na = self._normalize(alias)
            if nq in na or na in nq:
                return 0.40

        return 0.0

    def _matches(self, normalized_query: str, food: FoodItem) -> bool:
        targets = [
            food.name_he, food.name_en,
            *food.aliases_he, *food.aliases_en,
        ]
        for target in targets:
            if normalized_query in self._normalize(target):
                return True
        return False

    def _score_match(self, query: str, food: FoodItem) -> float:
        nq = self._normalize(query)
        # Exact name match
        if nq == self._normalize(food.name_he) or nq == self._normalize(food.name_en):
            return 1.0
        # Exact alias match
        for alias in food.aliases_he + food.aliases_en:
            if nq == self._normalize(alias):
                return 0.95
        # Partial match
        all_names = [food.name_he, food.name_en] + food.aliases_he + food.aliases_en
        for name in all_names:
            if nq in self._normalize(name) or self._normalize(name) in nq:
                return 0.7
        return 0.0

    def _to_confidence_level(self, score: float) -> ConfidenceLevel:
        if score >= 0.85:
            return ConfidenceLevel.HIGH
        elif score >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def match_foods(self, queries: List[str]) -> FoodMatchResult:
        matches = []
        unmatched = []
        low_confidence = []

        for query in queries:
            best_score = 0.0
            best_food = None
            match_type = ""

            for food in self._foods.values():
                score = self._score_match(query, food)
                if score > best_score:
                    best_score = score
                    best_food = food
                    if score >= 0.95:
                        match_type = "exact"
                    elif score >= 0.85:
                        match_type = "alias"
                    else:
                        match_type = "fuzzy"

            if best_food is None or best_score < 0.3:
                unmatched.append(query)
            else:
                fm = FoodMatch(
                    query=query,
                    food_id=best_food.food_id,
                    food_name=best_food.name_he,
                    confidence_score=best_score,
                    confidence_level=self._to_confidence_level(best_score),
                    matched_by=match_type,
                )
                if fm.confidence_level == ConfidenceLevel.LOW:
                    low_confidence.append(fm)
                else:
                    matches.append(fm)

        return FoodMatchResult(
            matches=matches,
            unmatched=unmatched,
            low_confidence=low_confidence,
        )

    def add_custom_food(self, food: FoodItem) -> FoodItem:
        food.is_custom = True
        food.source = "user_custom"
        self._foods[food.food_id] = food
        return food

    def get_all_foods(self) -> List[FoodItem]:
        return list(self._foods.values())
