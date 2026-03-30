#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_product_demo.py
===================
לחיצה אחת → תוצאה אחת ברורה.

RUNBOOK:
  1. User Profile      — הגדרת המשתמש (גיל, מגדר, גובה, משקל, פעילות, מטרה)
  2. Nutrition Targets — חישוב BMR / TDEE / קלוריות יעד + מאקרו
  3. Food Resolution   — התאמת מזונות לקטלוג עם ציון ביטחון
  4. Inventory         — בדיקת זמינות מלאי
  5. Meal Plan         — בניית תפריט יומי לפי יעדים ומלאי
  6. Summary           — תדפיס מוצרי מוכן להצגה

Usage:
  python run_product_demo.py

Exit codes:
  0 — הצלחה מלאה
  1 — כשל בשלב כלשהו
"""

import io
import sys
import os
from datetime import date, datetime

# ── Windows Hebrew encoding fix ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Imports ──────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender, ActivityLevel, Goal
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.agents.agent_6_ai import AILayer

# ── Helpers ───────────────────────────────────────────────────────────────────

WIDTH = 62

def header(text: str) -> None:
    print()
    print("─" * WIDTH)
    print(f"  {text}")
    print("─" * WIDTH)

def ok(text: str) -> None:
    print(f"  ✓  {text}")

def info(label: str, value: str) -> None:
    label_w = 22
    print(f"  {label:<{label_w}} {value}")

def fail(text: str) -> None:
    print(f"  ✗  {text}", file=sys.stderr)

def divider() -> None:
    print("─" * WIDTH)

# ── Demo Input Data ───────────────────────────────────────────────────────────
# ניתן לשנות כאן את נתוני המשתמש וסל המזון לדמו
DEMO_USER = dict(
    user_id       = "demo_product_001",
    name          = "ישראל ישראלי",
    gender        = Gender.MALE,
    date_of_birth = date(1990, 5, 15),
    height_cm     = 178.0,
    weight_kg     = 82.0,
    activity_level= ActivityLevel.MODERATELY_ACTIVE,
    goal          = Goal.LOSE_WEIGHT,
)

# מזונות שהמשתמש מזין — נבדק מול הקטלוג
DEMO_FOOD_QUERIES = [
    "חזה עוף", "אורז", "ביצה", "בננה",
    "שמן זית", "לחם", "עגבנייה", "קוטג׳", "מלפפון",
]

# כמויות מלאי ראשוני (גרם)
DEMO_INVENTORY = {
    "food_001": 600.0,   # חזה עוף
    "food_002": 1000.0,  # אורז
    "food_003": 400.0,   # ביצים
    "food_004": 360.0,   # בננות
    "food_007": 500.0,   # לחם
    "food_008": 300.0,   # עגבניות
}

# ── Main Pipeline ─────────────────────────────────────────────────────────────

def run() -> int:
    """
    מריץ את כל ה-pipeline ומחזיר 0 (הצלחה) או 1 (כשל).
    אין state גלובלי — כל ריצה עצמאית לחלוטין.
    """
    print()
    print("=" * WIDTH)
    print("  מערכת תזונה חכמה  —  הפקת תפריט יומי")
    print(f"  {datetime.now().strftime('%Y-%m-%d  %H:%M')}")
    print("=" * WIDTH)

    # ────────────────────────────────────────────────────────────
    # שלב 1: פרופיל משתמש
    # ────────────────────────────────────────────────────────────
    header("שלב 1 / 5  —  פרופיל משתמש")

    user = UserProfile(**DEMO_USER)
    info("שם:",          user.name)
    info("גיל:",         f"{user.age} שנים")
    info("גובה / משקל:", f"{user.height_cm} ס\"מ  /  {user.weight_kg} ק\"ג")
    info("רמת פעילות:",  user.activity_level.value)
    info("מטרה:",        user.goal.value)
    ok("פרופיל נטען")

    # ────────────────────────────────────────────────────────────
    # שלב 2: חישוב יעדים תזונתיים
    # ────────────────────────────────────────────────────────────
    header("שלב 2 / 5  —  חישוב יעדים תזונתיים")

    engine = NutritionEngine()
    targets = engine.calculate_targets(user)
    errors = engine.validate_targets(targets)

    if errors:
        for e in errors:
            fail(e)
        return 1

    info("BMR (מנוחה):",      f"{targets.bmr_kcal:.0f} קק\"ל / יום")
    info("TDEE (פעיל):",      f"{targets.tdee_kcal:.0f} קק\"ל / יום")
    info("יעד קלורי:",        f"{targets.target_calories_kcal:.0f} קק\"ל / יום")
    info("חלבון:",            f"{targets.protein_g:.0f}ג  ({targets.protein_pct:.0f}%)")
    info("פחמימות:",          f"{targets.carbs_g:.0f}ג  ({targets.carbs_pct:.0f}%)")
    info("שומן:",             f"{targets.fat_g:.0f}ג  ({targets.fat_pct:.0f}%)")
    info("שיטת חישוב:",       targets.calculation_method)
    ok("יעדים תקינים — ולידציה עברה")

    # ────────────────────────────────────────────────────────────
    # שלב 3: התאמת מזונות לקטלוג
    # ────────────────────────────────────────────────────────────
    header("שלב 3 / 5  —  זיהוי מזונות")

    catalog = FoodCatalog()
    match_result = catalog.match_foods(DEMO_FOOD_QUERIES)

    total_q = len(DEMO_FOOD_QUERIES)
    matched  = len(match_result.matches)
    low_conf = len(match_result.low_confidence)
    unmatched = len(match_result.unmatched)

    for m in match_result.matches:
        badge = "●" if m.confidence_level.value == "high" else "◑"
        info(f"  {m.query}", f"{badge} {m.food_name}  ({m.confidence_score:.0%})")

    if match_result.low_confidence:
        for m in match_result.low_confidence:
            info(f"  {m.query}", f"⚠ {m.food_name}  ({m.confidence_score:.0%})  — ביטחון נמוך")

    if match_result.unmatched:
        for q in match_result.unmatched:
            info(f"  {q}", "✗ לא זוהה")

    info("תוצאה:", f"{matched} זוהו  |  {low_conf} ביטחון נמוך  |  {unmatched} לא זוהו  (מתוך {total_q})")

    if unmatched == total_q:
        fail("אף מזון לא זוהה — עצירה")
        return 1

    ok("זיהוי מזונות הושלם")

    # ────────────────────────────────────────────────────────────
    # שלב 4: מלאי
    # ────────────────────────────────────────────────────────────
    header("שלב 4 / 5  —  בדיקת מלאי")

    inv_manager = InventoryManager()
    for food_id, qty in DEMO_INVENTORY.items():
        inv_manager.add_item(DEMO_USER["user_id"], food_id, qty, "gram")

    state = inv_manager.get_state(DEMO_USER["user_id"])
    food_lookup = {f.food_id: f for f in catalog.get_all_foods()}

    for item in state.items.values():
        food = food_lookup.get(item.food_id)
        name = food.name_he if food else item.food_id
        info(f"  {name}", f"{item.quantity:.0f}ג")

    ok(f"{len(state.items)} פריטים במלאי")

    # ────────────────────────────────────────────────────────────
    # שלב 5: הפקת תפריט
    # ────────────────────────────────────────────────────────────
    header("שלב 5 / 5  —  הפקת תפריט יומי")

    planner = MealPlanner()
    planner.set_food_lookup(food_lookup)

    plan = planner.generate_plan(
        targets   = targets,
        food_matches = match_result,
        inventory = state,
        run_id    = f"prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )

    plan_errors = planner.validate_plan(plan)
    if plan_errors:
        for e in plan_errors:
            fail(e)
        return 1

    info("סה\"כ קלוריות:", f"{plan.total_calories:.0f} קק\"ל")
    info("סטייה מהיעד:",  f"{plan.calorie_deviation_pct:+.1f}%")
    info("ארוחות:",        str(len(plan.meals)))
    ok("תפריט תקין — ולידציה עברה")

    # ────────────────────────────────────────────────────────────
    # פלט מוצרי — תדפיס מלא
    # ────────────────────────────────────────────────────────────
    print()
    print("=" * WIDTH)
    print("  תפריט יומי מוכן להצגה")
    print("=" * WIDTH)

    ai = AILayer()
    target_expl = ai.format_targets_explanation(targets)

    print()
    print(f"  שם: {user.name}   |   תאריך: {plan.plan_date}")
    print()

    # Nutrition box
    divider()
    print("  יעדים תזונתיים")
    divider()
    print(f"  {target_expl}")
    print()

    # Meal plan
    MEAL_LABELS = {
        "breakfast":       "ארוחת בוקר",
        "morning_snack":   "חטיף בוקר",
        "lunch":           "ארוחת צהריים",
        "afternoon_snack": "חטיף אחה\"צ",
        "dinner":          "ארוחת ערב",
        "evening_snack":   "חטיף ערב",
    }

    for meal in plan.meals:
        label = MEAL_LABELS.get(meal.meal_type.value, meal.meal_type.value)
        divider()
        print(f"  {label}")
        divider()
        for item in meal.items:
            inv_tag = "  ✓ מלאי" if item.from_inventory else ""
            print(
                f"  • {item.food_name:<18} {item.quantity_g:>6.0f}ג   "
                f"{item.calories_kcal:>5.0f} קק\"ל"
                f"{inv_tag}"
            )
        print(
            f"  {'סה\"כ ארוחה:':<18} {'':>6}   "
            f"{meal.total_calories:>5.0f} קק\"ל  |  "
            f"ח {meal.total_protein:.0f}ג  פ {meal.total_carbs:.0f}ג  ש {meal.total_fat:.0f}ג"
        )

    # Daily summary
    print()
    divider()
    print("  סיכום יומי")
    divider()
    print(
        f"  {'קלוריות:':<20} {plan.total_calories:>6.0f} קק\"ל  "
        f"(יעד: {targets.target_calories_kcal:.0f},  סטייה: {plan.calorie_deviation_pct:+.1f}%)"
    )
    print(
        f"  {'חלבון:':<20} {plan.total_protein:>6.0f}ג  "
        f"(יעד: {targets.protein_g:.0f}ג)"
    )
    print(
        f"  {'פחמימות:':<20} {plan.total_carbs:>6.0f}ג  "
        f"(יעד: {targets.carbs_g:.0f}ג)"
    )
    print(
        f"  {'שומן:':<20} {plan.total_fat:>6.0f}ג  "
        f"(יעד: {targets.fat_g:.0f}ג)"
    )

    # Inventory deduction
    print()
    divider()
    print("  ניכוי מלאי")
    divider()
    changeset = inv_manager.deduct_for_plan(
        DEMO_USER["user_id"], plan, plan.run_id
    )
    for change in changeset.changes:
        food = food_lookup.get(change.food_id)
        name = food.name_he if food else change.food_id
        print(
            f"  {name:<20} "
            f"{change.quantity_before:>6.0f}ג → {change.quantity_after:>6.0f}ג  "
            f"({change.quantity_delta:+.0f}ג)"
        )
    ok(f"{len(changeset.changes)} פריטים עודכנו במלאי")

    # Final status
    print()
    print("=" * WIDTH)
    print("  ✓  PIPELINE הושלם בהצלחה")
    print("=" * WIDTH)
    print()

    return 0


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(run())
