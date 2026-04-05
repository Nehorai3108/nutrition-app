"""
ui_helpers.py — Helper functions for the nutrition app dashboard.
Plan persistence, reconstruction, weekly generation, rendering.
"""

import json
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from nutrition_app.models.enums import MealType
from nutrition_app.models.food_item import FoodItem
from nutrition_app.models.food_match import FoodMatchResult
from nutrition_app.models.inventory import InventoryState
from nutrition_app.models.meal import Meal, MealItem, MealPlan
from nutrition_app.models.nutrition_targets import NutritionTargets
from nutrition_app.agents.agent_5_planner import MealPlanner

# ── Constants ────────────────────────────────────────────────────────────────

PLANS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_agents", "plans")

HEBREW_DAY_NAMES = {
    0: "יום שני",
    1: "יום שלישי",
    2: "יום רביעי",
    3: "יום חמישי",
    4: "יום שישי",
    5: "שבת",
    6: "יום ראשון",
}

MEAL_LABELS = {
    "breakfast":       "ארוחת בוקר",
    "morning_snack":   "חטיף בוקר",
    "lunch":           "ארוחת צהריים",
    "afternoon_snack": "חטיף אחה\"צ",
    "dinner":          "ארוחת ערב",
    "evening_snack":   "חטיף ערב",
}

MEAL_ICONS = {
    "breakfast":       "sunrise",
    "morning_snack":   "coffee",
    "lunch":           "utensils",
    "afternoon_snack": "apple-whole",
    "dinner":          "moon",
    "evening_snack":   "cloud-moon",
}


# ── Plan Persistence ─────────────────────────────────────────────────────────

def save_plan_to_disk(plan: MealPlan, suffix: str = "approved") -> str:
    """Save a MealPlan to storage_agents/plans/. Returns the filename."""
    os.makedirs(PLANS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{ts}_{suffix}.json"
    filepath = os.path.join(PLANS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2)
    return filename


def load_plan_from_file(filepath: str) -> dict:
    """Read a JSON plan file and return the raw dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def scan_history_plans(plans_dir: str = PLANS_DIR) -> List[dict]:
    """Scan plans directory and return summary list sorted by date desc."""
    if not os.path.isdir(plans_dir):
        return []

    entries = []
    for fname in os.listdir(plans_dir):
        if not fname.endswith(".json"):
            continue
        try:
            filepath = os.path.join(plans_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            totals = data.get("totals", {})
            entries.append({
                "filename": fname,
                "plan_date": data.get("plan_date", ""),
                "total_calories": totals.get("calories_kcal", 0),
                "total_protein": totals.get("protein_g", 0),
                "total_carbs": totals.get("carbs_g", 0),
                "total_fat": totals.get("fat_g", 0),
                "target_calories": data.get("target_calories_kcal", 0),
                "deviation": data.get("calorie_deviation_pct", 0),
                "created_at": data.get("created_at", ""),
            })
        except (json.JSONDecodeError, OSError, KeyError):
            continue

    entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    return entries[:100]


# ── MealPlan Reconstruction ──────────────────────────────────────────────────

def reconstruct_plan_from_dict(data: dict) -> MealPlan:
    """Rebuild a MealPlan from a saved JSON dict without modifying model code."""
    meals = []
    for meal_data in data.get("meals", []):
        items = [MealItem.from_dict(item) for item in meal_data.get("items", [])]
        meal_type = MealType(meal_data["meal_type"])
        meals.append(Meal(meal_type=meal_type, items=items))

    plan_date_str = data.get("plan_date", date.today().isoformat())
    plan_date = date.fromisoformat(plan_date_str)

    return MealPlan(
        plan_id=data.get("plan_id", str(uuid.uuid4())),
        user_id=data.get("user_id", ""),
        run_id=data.get("run_id", ""),
        plan_date=plan_date,
        meals=meals,
        target_calories_kcal=data.get("target_calories_kcal", 0),
    )


# ── Weekly Plan Generation ───────────────────────────────────────────────────

def generate_weekly_plans(
    targets: NutritionTargets,
    food_matches: FoodMatchResult,
    inventory: InventoryState,
    food_lookup: Dict[str, FoodItem],
    run_id_prefix: str,
) -> List[MealPlan]:
    """Generate 7 diverse daily plans (one per day starting today)."""
    plans = []
    today = date.today()

    for day in range(7):
        planner = MealPlanner()
        planner.set_food_lookup(dict(food_lookup))
        planner.load_extended_catalog()

        plan_run_id = f"{run_id_prefix}_day{day}"
        plan = planner.generate_plan(
            targets=targets,
            food_matches=food_matches,
            inventory=inventory,
            run_id=plan_run_id,
            seed_offset=day * 10,
        )
        plan.plan_date = today + timedelta(days=day)
        plans.append(plan)

        save_plan_to_disk(plan, suffix=f"week_{run_id_prefix}_day_{day}")

    return plans


# ── Rendering Helpers ────────────────────────────────────────────────────────

def render_meal_card_html(meal: Meal, show_items: bool = True) -> str:
    """Return styled HTML for a single meal card."""
    meal_type_val = meal.meal_type.value
    label = MEAL_LABELS.get(meal_type_val, meal_type_val)
    cal = meal.total_calories
    protein = meal.total_protein
    carbs = meal.total_carbs
    fat = meal.total_fat

    items_html = ""
    if show_items:
        for item in meal.items:
            inv_badge = '<span style="color:#66bb6a;font-size:0.75em;margin-right:6px">&#x2713; מלאי</span>' if item.from_inventory else ''
            items_html += (
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.88em">'
                f'<span style="color:#e0e0e0">{item.food_name} {inv_badge}</span>'
                f'<span style="color:#aaa;white-space:nowrap">'
                f'{item.quantity_g:.0f}g &middot; {item.calories_kcal:.0f} קק״ל'
                f'</span></div>'
            )

    return (
        f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);'
        f'border-radius:14px;padding:18px 20px;margin:10px 0;'
        f'border-right:4px solid #4caf50;direction:rtl">'
        # Header
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
        f'<span style="font-size:1.15em;font-weight:700;color:#e8e8ff">{label}</span>'
        f'<span style="color:#ffd54f;font-weight:600;font-size:0.95em">{cal:.0f} קק״ל</span>'
        f'</div>'
        # Macro chips
        f'<div style="display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap">'
        f'<span style="background:#1b5e20;color:#a5d6a7;padding:3px 10px;border-radius:20px;font-size:0.8em">'
        f'חלבון {protein:.0f}g</span>'
        f'<span style="background:#0d47a1;color:#90caf9;padding:3px 10px;border-radius:20px;font-size:0.8em">'
        f'פחמימות {carbs:.0f}g</span>'
        f'<span style="background:#b71c1c;color:#ef9a9a;padding:3px 10px;border-radius:20px;font-size:0.8em">'
        f'שומן {fat:.0f}g</span>'
        f'</div>'
        # Items
        f'{items_html}'
        f'</div>'
    )


def render_day_card_html(
    day_name: str,
    day_date: date,
    calories: float,
    deviation: float,
    protein: float,
    carbs: float,
    fat: float,
    is_selected: bool = False,
) -> str:
    """Return styled HTML for a day summary card in the weekly grid."""
    border_color = "#4caf50" if is_selected else "#333"
    bg = "rgba(76,175,80,0.08)" if is_selected else "transparent"
    dev_color = "#66bb6a" if abs(deviation) <= 5 else "#ffa726" if abs(deviation) <= 10 else "#ef5350"

    return (
        f'<div style="background:{bg};border:2px solid {border_color};border-radius:12px;'
        f'padding:14px 10px;text-align:center;min-height:140px">'
        f'<div style="font-weight:700;color:#e0e0e0;font-size:1em;margin-bottom:4px">{day_name}</div>'
        f'<div style="color:#888;font-size:0.82em;margin-bottom:8px">{day_date.strftime("%d/%m")}</div>'
        f'<div style="font-size:1.4em;font-weight:700;color:#ffd54f;margin-bottom:4px">{calories:.0f}</div>'
        f'<div style="color:#999;font-size:0.75em;margin-bottom:6px">קק״ל</div>'
        f'<div style="color:{dev_color};font-size:0.8em;font-weight:600">{deviation:+.1f}%</div>'
        f'<div style="margin-top:8px;font-size:0.72em;color:#777">'
        f'P:{protein:.0f} C:{carbs:.0f} F:{fat:.0f}</div>'
        f'</div>'
    )
