"""
user_manager.py — ניהול משתמשים עם שמירה מקומית ב-JSON
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "storage_agents", "users.json")


def _load() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_users() -> list[dict]:
    data = _load()
    return list(data.values())


def get_user(user_id: str) -> Optional[dict]:
    return _load().get(user_id)


def create_user(name: str) -> dict:
    data = _load()
    user_id = str(uuid.uuid4())[:8]
    user = {
        "user_id": user_id,
        "name": name,
        "created_at": datetime.now().isoformat(),
    }
    data[user_id] = user
    _save(data)
    # Initialize water data for new user
    initialize_water(user_id)
    return user


def delete_user(user_id: str):
    data = _load()
    data.pop(user_id, None)
    _save(data)
    inv_file = _inventory_path(user_id)
    if os.path.exists(inv_file):
        os.remove(inv_file)


# ── Inventory per user ────────────────────────────────────────────────────────
# Dual backend: Supabase `inventory` table when configured, else local JSON.

def _use_supabase() -> bool:
    try:
        from nutrition_app.db.supabase_client import is_supabase_configured
        return is_supabase_configured()
    except Exception:
        return False


def _sb():
    from nutrition_app.db.supabase_client import get_supabase
    return get_supabase()


def _inventory_path(user_id: str) -> str:
    folder = os.path.join(os.path.dirname(__file__), "..", "storage_agents", "inventories")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}.json")


def load_inventory(user_id: str) -> list[dict]:
    if _use_supabase():
        rows = (
            _sb().table("inventory")
            .select("food_id, name_he, quantity_g, updated_at")
            .eq("user_id", user_id)
            .execute()
        ).data or []
        return [
            {
                "food_id":    r.get("food_id"),
                "name_he":    r.get("name_he"),
                "quantity_g": float(r.get("quantity_g") or 0),
                "added_at":   r.get("updated_at"),
            }
            for r in rows
        ]
    path = _inventory_path(user_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_inventory(user_id: str, items: list[dict]):
    if _use_supabase():
        # Full-replace strategy: delete then bulk insert. Simpler than diffing
        # and the inventory list is small.
        _sb().table("inventory").delete().eq("user_id", user_id).execute()
        if items:
            payload = [
                {
                    "user_id":    user_id,
                    "food_id":    it["food_id"],
                    "name_he":    it.get("name_he", ""),
                    "quantity_g": float(it.get("quantity_g", 0)),
                    "updated_at": datetime.now().isoformat(),
                }
                for it in items
            ]
            _sb().table("inventory").insert(payload).execute()
        return
    with open(_inventory_path(user_id), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_inventory_item(user_id: str, food_id: str, name_he: str, quantity_g: float):
    if _use_supabase():
        # Upsert: if (user_id, food_id) exists, add to its quantity; else insert.
        existing = (
            _sb().table("inventory")
            .select("quantity_g")
            .eq("user_id", user_id).eq("food_id", food_id)
            .limit(1).execute()
        ).data
        new_qty = float(existing[0]["quantity_g"]) + quantity_g if existing else quantity_g
        _sb().table("inventory").upsert({
            "user_id":    user_id,
            "food_id":    food_id,
            "name_he":    name_he,
            "quantity_g": new_qty,
            "updated_at": datetime.now().isoformat(),
        }, on_conflict="user_id,food_id").execute()
        return
    items = load_inventory(user_id)
    for item in items:
        if item["food_id"] == food_id:
            item["quantity_g"] += quantity_g
            save_inventory(user_id, items)
            return
    items.append({
        "food_id": food_id,
        "name_he": name_he,
        "quantity_g": quantity_g,
        "added_at": datetime.now().isoformat(),
    })
    save_inventory(user_id, items)


def update_inventory_item(user_id: str, food_id: str, quantity_g: float):
    if _use_supabase():
        _sb().table("inventory").update({
            "quantity_g": quantity_g,
            "updated_at": datetime.now().isoformat(),
        }).eq("user_id", user_id).eq("food_id", food_id).execute()
        return
    items = load_inventory(user_id)
    for item in items:
        if item["food_id"] == food_id:
            item["quantity_g"] = quantity_g
            break
    save_inventory(user_id, items)


def remove_inventory_item(user_id: str, food_id: str):
    if _use_supabase():
        _sb().table("inventory").delete().eq("user_id", user_id).eq("food_id", food_id).execute()
        return
    items = [i for i in load_inventory(user_id) if i["food_id"] != food_id]
    save_inventory(user_id, items)


# ── Workouts per user ─────────────────────────────────────────────────────────

def _workouts_path(user_id: str) -> str:
    folder = os.path.join(os.path.dirname(__file__), "..", "storage_agents", "workouts")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}.json")


def load_workouts(user_id: str) -> list[dict]:
    path = _workouts_path(user_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_workout(user_id: str, workout: dict) -> dict:
    """Add a new workout entry. Adds workout_id and logged_at if missing."""
    workouts = load_workouts(user_id)
    if "workout_id" not in workout:
        workout["workout_id"] = str(uuid.uuid4())[:8]
    if "logged_at" not in workout:
        workout["logged_at"] = datetime.now().isoformat()
    workouts.append(workout)
    with open(_workouts_path(user_id), "w", encoding="utf-8") as f:
        json.dump(workouts, f, ensure_ascii=False, indent=2)
    return workout


def delete_workout(user_id: str, workout_id: str):
    workouts = [w for w in load_workouts(user_id) if w.get("workout_id") != workout_id]
    with open(_workouts_path(user_id), "w", encoding="utf-8") as f:
        json.dump(workouts, f, ensure_ascii=False, indent=2)


# ── Water tracking per user ───────────────────────────────────────────────────

def _water_path(user_id: str) -> str:
    folder = os.path.join(os.path.dirname(__file__), "..", "storage_agents", "water")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}.json")


def initialize_water(user_id: str, daily_goal_ml: float = 2000.0) -> dict:
    """Initialize water data for a user with default goal."""
    from nutrition_app.models.water import UserWaterData, WaterGoal

    water_data = UserWaterData(
        user_id=user_id,
        daily_log={},
        goal=WaterGoal(user_id=user_id, daily_goal_ml=daily_goal_ml),
    )
    with open(_water_path(user_id), "w", encoding="utf-8") as f:
        json.dump(water_data.to_dict(), f, ensure_ascii=False, indent=2)
    return water_data.to_dict()


def load_water(user_id: str) -> dict:
    """Load water data for a user."""
    path = _water_path(user_id)
    if not os.path.exists(path):
        # Auto-initialize if not exists
        return initialize_water(user_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
