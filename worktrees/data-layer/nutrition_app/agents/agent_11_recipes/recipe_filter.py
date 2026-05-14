"""Agent 11 -- Recipe Filter & Menu Recommendation Models"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class RecipeFilter:
    calorie_min: Optional[float] = None
    calorie_max: Optional[float] = None
    protein_min_g: Optional[float] = None
    carbs_max_g: Optional[float] = None
    fat_max_g: Optional[float] = None
    meal_types: Optional[List[str]] = None  # e.g. ["BREAKFAST", "LUNCH"]
    kashrut: Optional[str] = None  # "dairy", "meat", "parve", or None for any
    tags_include: Optional[List[str]] = None  # must have ALL of these
    tags_exclude: Optional[List[str]] = None  # must have NONE of these
    max_prep_time_minutes: Optional[int] = None
    search_text: Optional[str] = None  # fuzzy name search (Hebrew or English)
    max_results: int = 20


@dataclass
class MenuPreferences:
    kashrut_mode: str = "flexible"  # "strict_dairy", "strict_meat", "flexible", "parve_only"
    max_prep_time_total: Optional[int] = None
    exclude_recipe_ids: Set[str] = field(default_factory=set)
    preferred_tags: List[str] = field(default_factory=list)
    variety_weight: float = 0.5  # 0=pure nutrition, 1=max variety


@dataclass
class DailyMenu:
    date: str
    meals: Dict[str, dict]  # meal_type -> recipe dict
    total_nutrition: dict  # {calories, protein, carbs, fat}
    deviation_from_targets: dict  # {calories_pct, protein_pct, carbs_pct, fat_pct}
    total_prep_time: int
    kashrut_valid: bool
