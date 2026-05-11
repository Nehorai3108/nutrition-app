"""
NutritionTargets model — calculated daily targets for a user.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NutritionTargets:
    user_id: str
    bmr_kcal: float
    tdee_kcal: float
    target_calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g_min: float = 25.0
    fiber_g_max: float = 38.0
    calculation_method: str = "mifflin_st_jeor"
    notes: Optional[str] = None

    @property
    def macro_total_kcal(self) -> float:
        return round(
            self.protein_g * 4.0 + self.carbs_g * 4.0 + self.fat_g * 9.0, 1
        )

    @property
    def protein_pct(self) -> float:
        if self.target_calories_kcal == 0:
            return 0.0
        return round((self.protein_g * 4.0 / self.target_calories_kcal) * 100, 1)

    @property
    def carbs_pct(self) -> float:
        if self.target_calories_kcal == 0:
            return 0.0
        return round((self.carbs_g * 4.0 / self.target_calories_kcal) * 100, 1)

    @property
    def fat_pct(self) -> float:
        if self.target_calories_kcal == 0:
            return 0.0
        return round((self.fat_g * 9.0 / self.target_calories_kcal) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "bmr_kcal": self.bmr_kcal,
            "tdee_kcal": self.tdee_kcal,
            "target_calories_kcal": self.target_calories_kcal,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "fiber_g_min": self.fiber_g_min,
            "fiber_g_max": self.fiber_g_max,
            "calculation_method": self.calculation_method,
            "macro_total_kcal": self.macro_total_kcal,
            "protein_pct": self.protein_pct,
            "carbs_pct": self.carbs_pct,
            "fat_pct": self.fat_pct,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NutritionTargets":
        return cls(
            user_id=data["user_id"],
            bmr_kcal=data["bmr_kcal"],
            tdee_kcal=data["tdee_kcal"],
            target_calories_kcal=data["target_calories_kcal"],
            protein_g=data["protein_g"],
            carbs_g=data["carbs_g"],
            fat_g=data["fat_g"],
            fiber_g_min=data.get("fiber_g_min", 25.0),
            fiber_g_max=data.get("fiber_g_max", 38.0),
            calculation_method=data.get("calculation_method", "mifflin_st_jeor"),
            notes=data.get("notes"),
        )
