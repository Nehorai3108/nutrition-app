#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_autonomous_loop.py
======================
Production-grade autonomous runner for the nutrition planning system.

Flow:
1. Load or create user profile
2. Initialize all agents + task executor
3. LOOP (max 20 iterations):
   a. Director analyzes system -> creates tasks
   b. Executor runs tasks
   c. Critic reviews results
   d. Run full pipeline: Profile -> Targets -> Foods -> Inventory -> Plan
   e. Validate plan against exit criteria
   f. If valid -> save, present, exit
   g. If invalid -> log issues, continue loop
4. Save final metrics and audit trail
5. Output result summary

Exit Criteria (ALL must be true):
- At least 3 meals with food items
- Daily calories within +/-15% of TDEE target
- Protein >= 25% of calories
- Carbs <= 60% of calories
- No meal-timing category violations
- At least 8 unique foods used
- Director health score >= 70

Usage:
  python run_autonomous_loop.py
"""

import io
import json
import os
import sys
import time
from datetime import date, datetime, timezone

# Fix Windows console encoding for Hebrew
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nutrition_app.models.enums import (
    ActivityLevel, Gender, Goal, MealType,
)
from nutrition_app.models.user import UserProfile
from nutrition_app.models.inventory import InventoryState
from nutrition_app.agents.agent_2_nutrition.nutrition_engine import NutritionEngine
from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog
from nutrition_app.agents.agent_4_inventory.inventory_manager import InventoryManager
from nutrition_app.agents.agent_5_planner.meal_planner import MealPlanner
from nutrition_app.agents.agent_6_ai.ai_layer import AILayer
from nutrition_app.agents.agent_7_data_performance.data_manager import DataManager
from nutrition_app.agents.agent_8_director.director_agent import DirectorAgent
from nutrition_app.agents.agent_9_critic.critic_agent import CriticAgent
from nutrition_app.agents.task_executor.task_executor import TaskExecutor


# ─── Configuration ─────────────────────────────────────────────────
MAX_ITERATIONS = 20
STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_agents")

WIDTH = 62

# ─── Helpers ───────────────────────────────────────────────────────

def header(text: str) -> None:
    print()
    print("=" * WIDTH)
    print(f"  {text}")
    print("=" * WIDTH)


def section(text: str) -> None:
    print(f"\n  --- {text} ---")


def ok(text: str) -> None:
    print(f"  [OK] {text}")


def warn(text: str) -> None:
    print(f"  [!!] {text}")


def fail(text: str) -> None:
    print(f"  [FAIL] {text}")


def info(label: str, value: str) -> None:
    print(f"  {label:<22} {value}")


MEAL_LABELS = {
    "breakfast": "ארוחת בוקר",
    "morning_snack": "חטיף בוקר",
    "lunch": "ארוחת צהריים",
    "afternoon_snack": "חטיף אחה\"צ",
    "dinner": "ארוחת ערב",
    "evening_snack": "חטיף ערב",
}


# ─── Validation ────────────────────────────────────────────────────

def validate_plan_full(plan, targets, planner, director_health) -> list:
    """Validate plan against all exit criteria. Returns list of issues."""
    issues = []

    # 1. At least 3 meals with food items
    meals_with_items = sum(1 for m in plan.meals if m.items)
    if meals_with_items < 3:
        issues.append(f"Only {meals_with_items} meals have items (need >= 3)")

    # 2. Calories within +/-15%
    dev = abs(plan.calorie_deviation_pct)
    if dev > 15:
        issues.append(f"Calorie deviation {plan.calorie_deviation_pct:+.1f}% exceeds +/-15%")

    # 3-4. Macro targets
    total_protein = plan.total_protein
    total_carbs = plan.total_carbs
    total_fat = plan.total_fat
    protein_cal = total_protein * 4
    carbs_cal = total_carbs * 4
    fat_cal = total_fat * 9
    macro_total = protein_cal + carbs_cal + fat_cal

    if macro_total > 0:
        protein_pct = (protein_cal / macro_total) * 100
        carbs_pct = (carbs_cal / macro_total) * 100
        if protein_pct < 25:
            issues.append(f"Protein {protein_pct:.1f}% < 25%")
        if carbs_pct > 60:
            issues.append(f"Carbs {carbs_pct:.1f}% > 60%")
    else:
        issues.append("Plan has zero macro calories")

    # 5. No meal timing violations
    timing_violations = planner._check_timing_violations(plan)
    if timing_violations:
        issues.append(f"{len(timing_violations)} meal timing violations")

    # 6. At least 8 unique foods
    unique_foods = set()
    for meal in plan.meals:
        for item in meal.items:
            unique_foods.add(item.food_id)
    if len(unique_foods) < 8:
        issues.append(f"Only {len(unique_foods)} unique foods (need >= 8)")

    # 7. Director health score >= 70
    if director_health < 70:
        issues.append(f"Director health {director_health}/100 < 70")

    return issues


# ─── Main Loop ─────────────────────────────────────────────────────

def main() -> int:
    start_time = time.time()

    header("מערכת תזונה אוטונומית — הפעלה")
    print(f"  {datetime.now().strftime('%Y-%m-%d  %H:%M')}")
    print(f"  מקסימום איטרציות: {MAX_ITERATIONS}")

    # ── Initialize Agents ──────────────────────────────────────────
    section("אתחול סוכנים")

    engine = NutritionEngine()
    catalog = FoodCatalog(load_extended=True)
    inventory_mgr = InventoryManager()
    planner = MealPlanner()
    ai_layer = AILayer()
    data_manager = DataManager(base_path=STORAGE_DIR)
    director = DirectorAgent(storage_dir=STORAGE_DIR)
    critic = CriticAgent(storage_dir=STORAGE_DIR)
    executor = TaskExecutor(storage_dir=STORAGE_DIR)

    all_foods = catalog.get_all_foods()
    food_lookup = {f.food_id: f for f in all_foods}
    planner.set_food_lookup(food_lookup)
    planner.load_extended_catalog()

    ok(f"9 סוכנים אותחלו | {len(food_lookup)} מזונות בקטלוג")

    # ── User Profile ───────────────────────────────────────────────
    section("פרופיל משתמש")

    user = UserProfile(
        user_id="auto_001",
        name="ישראל ישראלי",
        gender=Gender.MALE,
        date_of_birth=date(1990, 5, 15),
        height_cm=178.0,
        weight_kg=82.0,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=Goal.LOSE_WEIGHT,
    )
    info("שם:", user.name)
    info("מטרה:", user.goal.value)

    # ── Calculate Targets ──────────────────────────────────────────
    targets = engine.calculate_targets(user)
    info("יעד קלורי:", f"{targets.target_calories_kcal:.0f} קק\"ל")
    info("חלבון:", f"{targets.protein_g:.0f}ג ({targets.protein_pct:.0f}%)")
    info("פחמימות:", f"{targets.carbs_g:.0f}ג ({targets.carbs_pct:.0f}%)")

    # ── Food Matching ──────────────────────────────────────────────
    food_queries = [
        "חזה עוף", "אורז", "ביצה", "בננה", "שמן זית",
        "לחם", "עגבנייה", "קוטג׳", "מלפפון", "יוגורט",
        "סלמון", "קינואה", "שקדים", "תפוח", "ברוקולי",
    ]
    match_result = catalog.match_foods(food_queries)
    ok(f"{len(match_result.matches)} מזונות זוהו")

    # ── Inventory ──────────────────────────────────────────────────
    demo_inventory = {
        "food_001": 600.0, "food_002": 1000.0, "food_003": 400.0,
        "food_004": 360.0, "food_007": 500.0, "food_008": 300.0,
        "food_010": 200.0, "food_013": 300.0,
    }
    for food_id, qty in demo_inventory.items():
        inventory_mgr.add_item(user.user_id, food_id, qty, "gram")
    inv_state = inventory_mgr.get_state(user.user_id)
    ok(f"{len(inv_state.items)} פריטים במלאי")

    # ── Autonomous Loop ────────────────────────────────────────────
    best_plan = None
    best_score = -1
    best_issues = []
    director_health = 0
    critic_approved = 0
    critic_total = 0

    for iteration in range(1, MAX_ITERATIONS + 1):
        header(f"איטרציה {iteration}/{MAX_ITERATIONS}")

        # Step A: Director analysis
        section("ניתוח מנהל (Agent 8)")
        report = director.run_analysis()
        director_health = report.system_health_score
        info("ציון בריאות:", f"{director_health}/100")
        info("משימות חדשות:", str(len(report.tasks_created)))

        # Step B: Execute tasks
        section("ביצוע משימות")
        completed = executor.execute_pending_tasks()
        succeeded = sum(1 for t in completed if t.get("result", {}).get("success"))
        info("בוצעו:", f"{len(completed)} ({succeeded} הצליחו)")

        # Step C: Critic review
        section("סקירת ביקורת (Agent 9)")
        verdicts = critic.review_completed_tasks()
        approved = sum(1 for v in verdicts if v["verdict"] == "APPROVED")
        rejected = sum(1 for v in verdicts if v["verdict"] == "REJECTED")
        critic_total += len(verdicts)
        critic_approved += approved
        info("אושרו:", str(approved))
        info("נדחו:", str(rejected))

        # Step D: Generate meal plan
        section("הפקת תפריט")

        # Refresh catalog and planner with latest data
        catalog_fresh = FoodCatalog(load_extended=True)
        all_foods_fresh = catalog_fresh.get_all_foods()
        food_lookup_fresh = {f.food_id: f for f in all_foods_fresh}

        planner_fresh = MealPlanner(food_catalog_lookup=food_lookup_fresh)
        planner_fresh.load_extended_catalog()

        match_result_fresh = catalog_fresh.match_foods(food_queries)

        plan = planner_fresh.generate_plan(
            targets=targets,
            food_matches=match_result_fresh,
            inventory=inv_state,
            run_id=f"auto_run_{iteration:03d}",
            seed_offset=iteration,
        )

        info("ארוחות:", str(len(plan.meals)))
        info("קלוריות:", f"{plan.total_calories:.0f}")
        info("סטייה:", f"{plan.calorie_deviation_pct:+.1f}%")

        # Count unique foods
        unique_foods = set()
        for meal in plan.meals:
            for item in meal.items:
                unique_foods.add(item.food_id)
        info("מזונות ייחודיים:", str(len(unique_foods)))

        # Macro percentages
        total_p = plan.total_protein
        total_c = plan.total_carbs
        total_f = plan.total_fat
        p_cal = total_p * 4
        c_cal = total_c * 4
        f_cal = total_f * 9
        m_total = p_cal + c_cal + f_cal
        if m_total > 0:
            info("חלבון:", f"{total_p:.0f}ג ({p_cal/m_total*100:.1f}%)")
            info("פחמימות:", f"{total_c:.0f}ג ({c_cal/m_total*100:.1f}%)")
            info("שומן:", f"{total_f:.0f}ג ({f_cal/m_total*100:.1f}%)")

        # Step E: Validate
        section("ולידציה")
        issues = validate_plan_full(plan, targets, planner_fresh, director_health)

        if not issues:
            ok("כל הקריטריונים עברו!")

            # Save the plan
            plan_path = os.path.join(
                STORAGE_DIR, "plans",
                f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_approved.json"
            )
            os.makedirs(os.path.dirname(plan_path), exist_ok=True)
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2, default=str)

            best_plan = plan
            best_issues = []
            break
        else:
            for issue in issues:
                warn(issue)

            # Track best plan so far
            score = len(plan.meals) * 10 + len(unique_foods) + director_health
            if score > best_score:
                best_score = score
                best_plan = plan
                best_issues = issues

            # Save intermediate plan for rotation tracking
            plan_path = os.path.join(
                STORAGE_DIR, "plans",
                f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_iter_{iteration}.json"
            )
            os.makedirs(os.path.dirname(plan_path), exist_ok=True)
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2, default=str)

    # ── Results ────────────────────────────────────────────────────
    elapsed = time.time() - start_time

    header("תוצאות")

    if best_plan is None:
        fail("לא הצליח להפיק תפריט תקין")
        return 1

    if not best_issues:
        ok("תפריט אושר!")
    else:
        warn(f"תפריט הטוב ביותר עם {len(best_issues)} בעיות")

    # Print the plan
    print()
    print("=" * WIDTH)
    print("  תפריט יומי")
    print("=" * WIDTH)

    for meal in best_plan.meals:
        label = MEAL_LABELS.get(meal.meal_type.value, meal.meal_type.value)
        print(f"\n  {label}:")
        for item in meal.items:
            inv_tag = " (מלאי)" if item.from_inventory else ""
            print(f"    {item.food_name:<18} {item.quantity_g:>6.0f}ג  {item.calories_kcal:>5.0f} קק\"ל{inv_tag}")
        total_label = 'סה"כ:'
        print(f"    {total_label:<18} {'':>6}  {meal.total_calories:>5.0f} קק\"ל")

    print()
    print("-" * WIDTH)
    info("סה\"כ קלוריות:", f"{best_plan.total_calories:.0f} / {targets.target_calories_kcal:.0f} קק\"ל")
    info("סטייה:", f"{best_plan.calorie_deviation_pct:+.1f}%")
    info("חלבון:", f"{best_plan.total_protein:.0f}ג")
    info("פחמימות:", f"{best_plan.total_carbs:.0f}ג")
    info("שומן:", f"{best_plan.total_fat:.0f}ג")

    unique_count = len(set(item.food_id for m in best_plan.meals for item in m.items))
    info("מזונות ייחודיים:", str(unique_count))
    info("ציון בריאות:", f"{director_health}/100")
    if critic_total > 0:
        info("אחוז אישור ביקורת:", f"{critic_approved/critic_total*100:.0f}%")
    info("זמן ריצה:", f"{elapsed:.1f} שניות")

    # ── Metrics ────────────────────────────────────────────────────
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "iterations": iteration if 'iteration' in dir() else MAX_ITERATIONS,
        "director_health": director_health,
        "critic_approval_rate": (critic_approved / max(critic_total, 1)) * 100,
        "total_calories": best_plan.total_calories,
        "calorie_deviation_pct": best_plan.calorie_deviation_pct,
        "unique_foods": unique_count,
        "elapsed_seconds": elapsed,
        "success": len(best_issues) == 0,
        "remaining_issues": best_issues,
    }

    metrics_path = os.path.join(STORAGE_DIR, "audit", "metrics.json")
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=str)

    print()
    if not best_issues:
        print("=" * WIDTH)
        print("  PIPELINE הושלם בהצלחה")
        print("=" * WIDTH)
        return 0
    else:
        print("=" * WIDTH)
        print("  PIPELINE הושלם עם בעיות")
        print("=" * WIDTH)
        return 1


if __name__ == "__main__":
    sys.exit(main())
