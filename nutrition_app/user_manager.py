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
    return user


def delete_user(user_id: str):
    data = _load()
    data.pop(user_id, None)
    _save(data)
    inv_file = _inventory_path(user_id)
    if os.path.exists(inv_file):
        os.remove(inv_file)


# ── Inventory per user ────────────────────────────────────────────────────────

def _inventory_path(user_id: str) -> str:
    folder = os.path.join(os.path.dirname(__file__), "..", "storage_agents", "inventories")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}.json")


def load_inventory(user_id: str) -> list[dict]:
    path = _inventory_path(user_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_inventory(user_id: str, items: list[dict]):
    with open(_inventory_path(user_id), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_inventory_item(user_id: str, food_id: str, name_he: str, quantity_g: float):
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
    items = load_inventory(user_id)
    for item in items:
        if item["food_id"] == food_id:
            item["quantity_g"] = quantity_g
            break
    save_inventory(user_id, items)


def remove_inventory_item(user_id: str, food_id: str):
    items = [i for i in load_inventory(user_id) if i["food_id"] != food_id]
    save_inventory(user_id, items)
