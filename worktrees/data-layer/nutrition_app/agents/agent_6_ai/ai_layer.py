"""
Agent 6 — AI Layer & Recommendation Owner

Responsibility:
- Format text for users
- Meal naming
- Alternative suggestions
- Conversational UX
- Future: OCR/vision normalization output

Input:  structured outputs from other agents
Output: textual recommendations / user-facing explanations

Rules:
- NOT a source of truth
- Does NOT calculate calories
- Does NOT modify targets
- Does NOT modify inventory
- Does NOT perform DB writes

Forbidden:
- Business decisions
- Schema changes
- Performance/storage changes
"""

from typing import List, Optional
from nutrition_app.models.meal import MealPlan, Meal
from nutrition_app.models.nutrition_targets import NutritionTargets


class AILayer:
    """User-facing text generation. Placeholder for AI integration."""

    def generate_plan_summary(self, plan: MealPlan) -> str:
        """Generate a human-readable summary of the meal plan."""
        lines = []
        lines.append(f"תפריט יומי ל-{plan.plan_date.isoformat()}")
        lines.append(f"יעד קלורי: {plan.target_calories_kcal} קק\"ל")
        lines.append("")

        for meal in plan.meals:
            meal_name = self._meal_type_hebrew(meal.meal_type.value)
            lines.append(f"── {meal_name} ──")
            for item in meal.items:
                inv_mark = " (מהמלאי)" if item.from_inventory else ""
                lines.append(
                    f"  • {item.food_name}: {item.quantity_g}g "
                    f"({item.calories_kcal} קק\"ל){inv_mark}"
                )
            lines.append(
                f"  סה\"כ: {meal.total_calories} קק\"ל | "
                f"ח: {meal.total_protein}g | פ: {meal.total_carbs}g | ש: {meal.total_fat}g"
            )
            lines.append("")

        lines.append(f"סה\"כ יומי: {plan.total_calories} קק\"ל")
        lines.append(
            f"חלבון: {plan.total_protein}g | פחמימות: {plan.total_carbs}g | שומן: {plan.total_fat}g"
        )
        deviation = plan.calorie_deviation_pct
        if abs(deviation) > 0.1:
            lines.append(f"סטייה מהיעד: {deviation:+.1f}%")

        return "\n".join(lines)

    def generate_meal_name(self, meal_items: list) -> str:
        """Generate a friendly name for a meal based on its items."""
        if not meal_items:
            return "ארוחה ריקה"
        main_items = sorted(meal_items, key=lambda x: x.get("calories_kcal", 0), reverse=True)
        top = main_items[:2]
        names = [item.get("food_name", "?") for item in top]
        return " עם ".join(names)

    def suggest_alternatives(self, food_id: str, reason: str) -> List[str]:
        """Suggest alternative foods. Placeholder — returns template messages."""
        return [
            f"אפשר להחליף את המזון ({food_id}) בגלל: {reason}",
            "נסה לבחור מזון דומה מאותה קטגוריה",
            "בדוק את המלאי לחלופות זמינות",
        ]

    def format_targets_explanation(self, targets: NutritionTargets) -> str:
        """Explain nutrition targets in user-friendly Hebrew."""
        lines = [
            f"BMR (מטבוליזם בסיסי): {targets.bmr_kcal} קק\"ל",
            f"TDEE (צריכה יומית כוללת): {targets.tdee_kcal} קק\"ל",
            f"יעד קלורי: {targets.target_calories_kcal} קק\"ל",
            "",
            f"חלבון: {targets.protein_g}g ({targets.protein_pct}%)",
            f"פחמימות: {targets.carbs_g}g ({targets.carbs_pct}%)",
            f"שומן: {targets.fat_g}g ({targets.fat_pct}%)",
        ]
        return "\n".join(lines)

    def _meal_type_hebrew(self, meal_type: str) -> str:
        mapping = {
            "breakfast": "ארוחת בוקר",
            "morning_snack": "חטיף בוקר",
            "lunch": "ארוחת צהריים",
            "afternoon_snack": "חטיף אחה\"צ",
            "dinner": "ארוחת ערב",
            "evening_snack": "חטיף ערב",
        }
        return mapping.get(meal_type, meal_type)
