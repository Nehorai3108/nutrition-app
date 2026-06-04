"""Tool definitions and dispatcher for the Grok chatbot."""

import json
import os
import uuid
from datetime import date

import streamlit as st

from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_3_food import FoodCatalog
from nutrition_app.agents.agent_4_inventory import InventoryManager
from nutrition_app.agents.agent_5_planner import MealPlanner
from nutrition_app.models.enums import MealType
from nutrition_app.models.meal import MealItem
from ui.user_auth import get_user_id

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "nutrition.db")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_foods",
            "description": "Search the food catalog by name (Hebrew or English). Returns matching food items with nutrition info per 100g.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Food name to search for"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_food_by_id",
            "description": "Get detailed nutrition info for a specific food item by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "food_id": {"type": "string", "description": "The food ID (e.g. 'food_001')"},
                },
                "required": ["food_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_meal_plan",
            "description": "Get the current daily meal plan including all meals, items, calories, and macros.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_meal_item",
            "description": "Modify an item in a specific meal. Actions: swap (replace food), adjust_quantity, remove, add.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "morning_snack", "lunch", "afternoon_snack", "dinner", "evening_snack"],
                        "description": "Which meal to modify",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["swap", "adjust_quantity", "remove", "add"],
                        "description": "What to do",
                    },
                    "food_id": {
                        "type": "string",
                        "description": "Current food_id (for swap/adjust/remove) or new food_id (for add)",
                    },
                    "new_food_id": {
                        "type": "string",
                        "description": "Replacement food_id (for swap only)",
                    },
                    "new_quantity_g": {
                        "type": "number",
                        "description": "New quantity in grams (for adjust/add/swap)",
                    },
                },
                "required": ["meal_type", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Get the current user profile (name, gender, age, height, weight, activity level, goal).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": "Update user profile fields. Only provided fields are changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "weight_kg": {"type": "number"},
                    "height_cm": {"type": "number"},
                    "activity_level": {
                        "type": "string",
                        "enum": ["sedentary", "lightly_active", "moderately_active", "very_active", "extra_active"],
                    },
                    "goal": {"type": "string", "enum": ["lose_weight", "maintain", "gain_weight"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nutrition_targets",
            "description": "Get current nutrition targets (BMR, TDEE, calories, protein, carbs, fat, percentages).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recalculate_targets",
            "description": "Recalculate nutrition targets based on current user profile. Call after updating the profile.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Get the current food inventory with item names and quantities in grams.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_inventory",
            "description": "Add, remove, or set quantity for a food item in inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "food_id": {"type": "string", "description": "Food ID to update"},
                    "action": {"type": "string", "enum": ["add", "remove", "set_quantity"]},
                    "quantity_g": {"type": "number", "description": "Quantity in grams (for add/set_quantity)"},
                },
                "required": ["food_id", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_new_meal_plan",
            "description": "Generate a completely new meal plan using the current profile, targets, and inventory. Returns the new plan summary.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _get_catalog() -> FoodCatalog:
    if "chatbot_catalog" not in st.session_state:
        st.session_state["chatbot_catalog"] = FoodCatalog()
    return st.session_state["chatbot_catalog"]


def _get_inventory_manager() -> InventoryManager:
    if "chatbot_inventory_mgr" not in st.session_state:
        st.session_state["chatbot_inventory_mgr"] = InventoryManager()
    return st.session_state["chatbot_inventory_mgr"]


def execute_tool(tool_name: str, arguments: dict) -> str:
    """Dispatch a tool call to the appropriate agent. Returns a JSON string."""
    try:
        if tool_name == "search_foods":
            return _search_foods(arguments)
        elif tool_name == "get_food_by_id":
            return _get_food_by_id(arguments)
        elif tool_name == "get_current_meal_plan":
            return _get_current_meal_plan()
        elif tool_name == "modify_meal_item":
            return _modify_meal_item(arguments)
        elif tool_name == "get_user_profile":
            return _get_user_profile()
        elif tool_name == "update_user_profile":
            return _update_user_profile(arguments)
        elif tool_name == "get_nutrition_targets":
            return _get_nutrition_targets()
        elif tool_name == "recalculate_targets":
            return _recalculate_targets()
        elif tool_name == "get_inventory":
            return _get_inventory()
        elif tool_name == "update_inventory":
            return _update_inventory(arguments)
        elif tool_name == "generate_new_meal_plan":
            return _generate_new_meal_plan()
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


#  Tool implementations 


def _search_foods(args: dict) -> str:
    catalog = _get_catalog()
    query = args["query"]
    limit = args.get("limit", 5)
    results = catalog.search_foods(query, limit=limit)
    return json.dumps(
        [
            {
                "food_id": f.food_id,
                "name_he": f.name_he,
                "name_en": f.name_en,
                "category": f.category.value,
                "calories_per_100g": f.nutrition_per_100g.calories_kcal,
                "protein_per_100g": f.nutrition_per_100g.protein_g,
                "carbs_per_100g": f.nutrition_per_100g.carbs_g,
                "fat_per_100g": f.nutrition_per_100g.fat_g,
                "default_serving_g": f.default_serving_g,
            }
            for f in results
        ],
        ensure_ascii=False,
    )


def _get_food_by_id(args: dict) -> str:
    catalog = _get_catalog()
    food = catalog.get_food_by_id(args["food_id"])
    if not food:
        return json.dumps({"error": f"Food not found: {args['food_id']}"})
    return json.dumps(food.to_dict(), ensure_ascii=False)


def _get_current_meal_plan() -> str:
    data = st.session_state.get("last_plan")
    if not data or "plan" not in data:
        return json.dumps({"error": "לא נוצר תפריט עדיין. לחץ על 'הפק תפריט יומי' תחילה."})
    return json.dumps(data["plan"].to_dict(), ensure_ascii=False)


def _modify_meal_item(args: dict) -> str:
    data = st.session_state.get("last_plan")
    if not data or "plan" not in data:
        return json.dumps({"error": "לא נוצר תפריט עדיין."})

    plan = data["plan"]
    meal_type_str = args["meal_type"]
    action = args["action"]
    catalog = _get_catalog()

    # Find the target meal
    target_meal = None
    for meal in plan.meals:
        if meal.meal_type.value == meal_type_str:
            target_meal = meal
            break

    if target_meal is None:
        return json.dumps({"error": f"ארוחה לא נמצאה: {meal_type_str}"})

    if action == "remove":
        food_id = args.get("food_id")
        if not food_id:
            return json.dumps({"error": "food_id is required for remove"})
        before_len = len(target_meal.items)
        target_meal.items = [i for i in target_meal.items if i.food_id != food_id]
        if len(target_meal.items) == before_len:
            return json.dumps({"error": f"פריט {food_id} לא נמצא בארוחה {meal_type_str}"})

    elif action == "add":
        food_id = args.get("food_id")
        if not food_id:
            return json.dumps({"error": "food_id is required for add"})
        food = catalog.get_food_by_id(food_id)
        if not food:
            return json.dumps({"error": f"מזון לא נמצא בקטלוג: {food_id}"})
        qty = args.get("new_quantity_g", food.default_serving_g)
        macros = food.macros_for_grams(qty)
        new_item = MealItem(
            food_id=food.food_id,
            food_name=food.name_he,
            quantity_g=qty,
            calories_kcal=macros["calories_kcal"],
            protein_g=macros["protein_g"],
            carbs_g=macros["carbs_g"],
            fat_g=macros["fat_g"],
        )
        target_meal.items.append(new_item)

    elif action == "adjust_quantity":
        food_id = args.get("food_id")
        new_qty = args.get("new_quantity_g")
        if not food_id or new_qty is None:
            return json.dumps({"error": "food_id and new_quantity_g are required for adjust_quantity"})
        item = next((i for i in target_meal.items if i.food_id == food_id), None)
        if not item:
            return json.dumps({"error": f"פריט {food_id} לא נמצא בארוחה {meal_type_str}"})
        food = catalog.get_food_by_id(food_id)
        if not food:
            return json.dumps({"error": f"מזון לא נמצא בקטלוג: {food_id}"})
        macros = food.macros_for_grams(new_qty)
        item.quantity_g = new_qty
        item.calories_kcal = macros["calories_kcal"]
        item.protein_g = macros["protein_g"]
        item.carbs_g = macros["carbs_g"]
        item.fat_g = macros["fat_g"]

    elif action == "swap":
        food_id = args.get("food_id")
        new_food_id = args.get("new_food_id")
        if not food_id or not new_food_id:
            return json.dumps({"error": "food_id and new_food_id are required for swap"})
        item = next((i for i in target_meal.items if i.food_id == food_id), None)
        if not item:
            return json.dumps({"error": f"פריט {food_id} לא נמצא בארוחה {meal_type_str}"})
        new_food = catalog.get_food_by_id(new_food_id)
        if not new_food:
            return json.dumps({"error": f"מזון חלופי לא נמצא: {new_food_id}"})
        qty = args.get("new_quantity_g", item.quantity_g)
        macros = new_food.macros_for_grams(qty)
        item.food_id = new_food.food_id
        item.food_name = new_food.name_he
        item.quantity_g = qty
        item.calories_kcal = macros["calories_kcal"]
        item.protein_g = macros["protein_g"]
        item.carbs_g = macros["carbs_g"]
        item.fat_g = macros["fat_g"]
        item.from_inventory = False
        item.inventory_item_id = None

    else:
        return json.dumps({"error": f"Unknown action: {action}"})

    return json.dumps(
        {
            "success": True,
            "meal_totals": {
                "calories_kcal": target_meal.total_calories,
                "protein_g": target_meal.total_protein,
                "carbs_g": target_meal.total_carbs,
                "fat_g": target_meal.total_fat,
            },
            "plan_totals": {
                "calories_kcal": plan.total_calories,
                "target_calories_kcal": plan.target_calories_kcal,
                "deviation_pct": plan.calorie_deviation_pct,
            },
        },
        ensure_ascii=False,
    )


def _get_user_profile() -> str:
    data = st.session_state.get("last_plan")
    if not data or "user" not in data:
        return json.dumps({"error": "לא נוצר פרופיל עדיין. הפק תפריט יומי תחילה."})
    user = data["user"]
    d = user.to_dict()
    d["age"] = user.age
    return json.dumps(d, ensure_ascii=False)


def _update_user_profile(args: dict) -> str:
    data = st.session_state.get("last_plan")
    if not data or "user" not in data:
        return json.dumps({"error": "לא נוצר פרופיל עדיין."})

    user = data["user"]
    from nutrition_app.models.enums import ActivityLevel, Goal
    from nutrition_app.utils import utcnow

    if "name" in args:
        user.name = args["name"]
    if "weight_kg" in args:
        user.weight_kg = args["weight_kg"]
    if "height_cm" in args:
        user.height_cm = args["height_cm"]
    if "activity_level" in args:
        user.activity_level = ActivityLevel(args["activity_level"])
    if "goal" in args:
        user.goal = Goal(args["goal"])
    user.updated_at = utcnow()

    d = user.to_dict()
    d["age"] = user.age
    return json.dumps({"success": True, "profile": d}, ensure_ascii=False)


def _get_nutrition_targets() -> str:
    data = st.session_state.get("last_plan")
    if not data or "targets" not in data:
        return json.dumps({"error": "לא חושבו יעדים עדיין."})
    return json.dumps(data["targets"].to_dict(), ensure_ascii=False)


def _recalculate_targets() -> str:
    data = st.session_state.get("last_plan")
    if not data or "user" not in data:
        return json.dumps({"error": "לא נוצר פרופיל עדיין."})

    engine = NutritionEngine()
    targets = engine.calculate_targets(data["user"])
    data["targets"] = targets
    return json.dumps({"success": True, "targets": targets.to_dict()}, ensure_ascii=False)


def _get_inventory() -> str:
    mgr = _get_inventory_manager()
    state = mgr.get_state(get_user_id())
    catalog = _get_catalog()

    items = []
    for inv_item in state.items.values():
        food = catalog.get_food_by_id(inv_item.food_id)
        food_name = food.name_he if food else inv_item.food_id
        items.append({
            "food_id": inv_item.food_id,
            "food_name": food_name,
            "quantity_g": inv_item.quantity,
            "unit": inv_item.unit.value,
        })

    return json.dumps(items, ensure_ascii=False)


def _update_inventory(args: dict) -> str:
    food_id = args["food_id"]
    action = args["action"]
    catalog = _get_catalog()
    mgr = _get_inventory_manager()

    food = catalog.get_food_by_id(food_id)
    if not food:
        return json.dumps({"error": f"מזון לא נמצא בקטלוג: {food_id}"})

    user_id = get_user_id()
    if action == "add":
        qty = args.get("quantity_g", food.default_serving_g)
        mgr.add_item(user_id, food_id, qty, "gram")
    elif action == "remove":
        mgr.remove_item(user_id, food_id)
    elif action == "set_quantity":
        qty = args.get("quantity_g", 0)
        state = mgr.get_state(user_id)
        existing = state.get_by_food_id(food_id)
        if existing:
            mgr.remove_item(user_id, food_id)
        if qty > 0:
            mgr.add_item(user_id, food_id, qty, "gram")
    else:
        return json.dumps({"error": f"Unknown action: {action}"})

    return json.dumps({"success": True, "food_name": food.name_he}, ensure_ascii=False)


def _generate_new_meal_plan() -> str:
    data = st.session_state.get("last_plan")
    if not data or "user" not in data:
        return json.dumps({"error": "לא נוצר פרופיל עדיין. הפק תפריט יומי תחילה."})

    user = data["user"]
    catalog = _get_catalog()
    mgr = _get_inventory_manager()

    # Recalculate targets
    engine = NutritionEngine()
    targets = engine.calculate_targets(user)
    data["targets"] = targets

    # Match all foods in catalog as high-confidence matches
    all_foods = catalog.get_all_foods()
    food_names = [f.name_he for f in all_foods]
    match_result = catalog.match_foods(food_names)

    # Build inventory state
    inv_state = mgr.get_state(get_user_id())

    # Generate plan
    run_id = str(uuid.uuid4())
    planner = MealPlanner(catalog)
    plan = planner.generate_plan(
        targets=targets,
        food_matches=match_result,
        inventory=inv_state,
        run_id=run_id,
    )

    data["plan"] = plan
    return json.dumps(
        {
            "success": True,
            "plan_summary": {
                "total_calories": plan.total_calories,
                "target_calories": plan.target_calories_kcal,
                "deviation_pct": plan.calorie_deviation_pct,
                "meals_count": len(plan.meals),
            },
        },
        ensure_ascii=False,
    )
