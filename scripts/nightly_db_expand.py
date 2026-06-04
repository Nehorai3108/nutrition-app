#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nightly_db_expand.py — מריץ כל לילה ומוסיף מזונות חדשים ל-DB

מקורות:
  1. USDA FoodData Central  — עד 200 מוצרים חדשים/לילה
  2. Open Food Facts Israel  — עד 100 מוצרים ישראליים/לילה

מנגנון:
  - שומר סמן (cursor) בקובץ data/expand_cursor.json
  - כל ריצה ממשיכה מאיפה שעצרה
  - מדלג על מזונות שכבר קיימים (לפי food_id)
  - מוסיף רק מזונות עם ערכי קלוריות תקינים
"""

import json
import os
import sqlite3
import time
import urllib.request
import urllib.parse
import logging
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH    = os.path.join(BASE_DIR, "storage", "nutrition.db")
CURSOR_FILE = os.path.join(BASE_DIR, "data", "expand_cursor.json")
LOG_FILE   = os.path.join(BASE_DIR, "data", "nightly_expand.log")

def _load_usda_key() -> str:
    key = os.environ.get("USDA_API_KEY", "")
    if key:
        return key
    # Fall back to .streamlit/secrets.toml
    secrets_path = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")
    if os.path.isfile(secrets_path):
        import re
        with open(secrets_path, encoding="utf-8") as f:
            m = re.search(r'USDA_API_KEY\s*=\s*["\']([^"\']+)["\']', f.read())
            if m:
                return m.group(1)
    return ""

USDA_API_KEY = _load_usda_key()

# ── Nutrient number → DB column ────────────────────────────────────────────────
NUTRIENT_MAP = {
    "208": "calories_kcal",
    "203": "protein_g",
    "205": "carbs_g",
    "204": "fat_g",
    "291": "fiber_g",
    "269": "sugar_g",
    "307": "sodium_mg",
}

# ── Setup logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nightly_expand")


# ── Cursor helpers ─────────────────────────────────────────────────────────────
def load_cursor() -> dict:
    if os.path.isfile(CURSOR_FILE):
        try:
            with open(CURSOR_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Default: start Branded Foods from page 1, OFF from page 2
    return {"usda_page": 1, "usda_type": "Branded", "off_page": 2}


def save_cursor(cursor: dict):
    os.makedirs(os.path.dirname(CURSOR_FILE), exist_ok=True)
    with open(CURSOR_FILE, "w", encoding="utf-8") as f:
        json.dump(cursor, f)


# ── DB helpers ─────────────────────────────────────────────────────────────────
def get_existing_ids(conn: sqlite3.Connection) -> set:
    rows = conn.execute("SELECT food_id FROM foods").fetchall()
    return {r[0] for r in rows}


def insert_food(conn: sqlite3.Connection, food: dict) -> bool:
    try:
        conn.execute("""
            INSERT OR IGNORE INTO foods
            (food_id, name_he, name_en, category,
             calories_kcal, protein_g, carbs_g, fat_g,
             fiber_g, sugar_g, sodium_mg,
             default_unit, default_serving_g,
             aliases_he, aliases_en, is_custom, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            food["food_id"],
            food.get("name_he", ""),
            food.get("name_en", ""),
            food.get("category", "other"),
            food.get("calories_kcal"),
            food.get("protein_g", 0.0),
            food.get("carbs_g", 0.0),
            food.get("fat_g", 0.0),
            food.get("fiber_g", 0.0),
            food.get("sugar_g", 0.0),
            food.get("sodium_mg", 0.0),
            food.get("default_unit", "gram"),
            food.get("default_serving_g", 100.0),
            json.dumps(food.get("aliases_he", []), ensure_ascii=False),
            json.dumps(food.get("aliases_en", []), ensure_ascii=False),
            0,
            food.get("source", "usda"),
        ))
        return conn.execute("SELECT changes()").fetchone()[0] > 0
    except Exception as e:
        log.warning(f"Insert failed for {food.get('food_id')}: {e}")
        return False


# ── USDA fetcher ───────────────────────────────────────────────────────────────
def fetch_usda_page(page: int, page_size: int = 200, data_type: str = "Branded") -> list:
    url = (
        f"https://api.nal.usda.gov/fdc/v1/foods/list"
        f"?api_key={USDA_API_KEY}"
        f"&dataType={urllib.parse.quote(data_type)}"
        f"&pageSize={page_size}"
        f"&pageNumber={page}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f"USDA page {page} fetch failed: {e}")
        return []


def enrich_usda_nutrients(fdc_ids: list) -> dict:
    """Batch-fetch nutrients for a list of FDC IDs. Returns {fdcId: nutrients}."""
    if not fdc_ids:
        return {}
    url = f"https://api.nal.usda.gov/fdc/v1/foods?api_key={USDA_API_KEY}"
    payload = json.dumps({"fdcIds": fdc_ids, "format": "abridged"}).encode()
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            foods = json.loads(r.read())
        result = {}
        for f in foods:
            nmap = {}
            for n in f.get("foodNutrients", []):
                num = str(n.get("number", ""))
                if num in NUTRIENT_MAP:
                    nmap[NUTRIENT_MAP[num]] = n.get("amount", 0.0)
            result[f["fdcId"]] = nmap
        return result
    except Exception as e:
        log.error(f"USDA nutrient batch failed: {e}")
        return {}


def categorize_by_name(name: str) -> str:
    n = name.lower()
    if any(w in n for w in ["chicken","beef","pork","turkey","lamb","fish","salmon","tuna","shrimp","meat","veal"]): return "protein"
    if any(w in n for w in ["milk","cheese","yogurt","cream","butter","dairy"]): return "dairy"
    if any(w in n for w in ["bread","rice","pasta","wheat","oat","grain","flour","cereal","corn"]): return "grain"
    if any(w in n for w in ["apple","banana","orange","berry","fruit","grape","mango","peach"]): return "fruit"
    if any(w in n for w in ["carrot","broccoli","spinach","tomato","lettuce","vegetable","pepper","onion","garlic"]): return "vegetable"
    if any(w in n for w in ["oil","fat","butter","lard","margarine"]): return "fat"
    if any(w in n for w in ["bean","lentil","chickpea","pea","legume","soy"]): return "legume"
    return "other"


def process_usda(conn: sqlite3.Connection, existing_ids: set, page: int, limit: int = 200, data_type: str = "Branded") -> tuple[int, int]:
    """Fetch one USDA page, enrich nutrients, insert new foods. Returns (added, next_page)."""
    items = fetch_usda_page(page, data_type=data_type)
    if not items:
        return 0, page  # no more pages

    # Filter out already existing
    new_items = [i for i in items if f"usda_{i['fdcId']}" not in existing_ids]
    if not new_items:
        return 0, page + 1

    # Batch enrich (API limit = 20 per call)
    all_nutrients = {}
    fdc_ids = [i["fdcId"] for i in new_items]
    for chunk_start in range(0, len(fdc_ids), 20):
        chunk = fdc_ids[chunk_start:chunk_start + 20]
        all_nutrients.update(enrich_usda_nutrients(chunk))
        time.sleep(0.3)

    added = 0
    for item in new_items[:limit]:
        fdc_id = item["fdcId"]
        name_en = item.get("description", "").strip()
        if not name_en:
            continue

        nutrients = all_nutrients.get(fdc_id, {})
        calories = nutrients.get("calories_kcal")
        if not calories or calories <= 0:
            continue  # skip foods with no calorie data

        food = {
            "food_id": f"usda_{fdc_id}",
            "name_he": "",
            "name_en": name_en,
            "category": categorize_by_name(name_en),
            "calories_kcal": round(calories, 1),
            "protein_g": round(nutrients.get("protein_g", 0), 1),
            "carbs_g": round(nutrients.get("carbs_g", 0), 1),
            "fat_g": round(nutrients.get("fat_g", 0), 1),
            "fiber_g": round(nutrients.get("fiber_g", 0), 1),
            "sugar_g": round(nutrients.get("sugar_g", 0), 1),
            "sodium_mg": round(nutrients.get("sodium_mg", 0), 1),
            "default_unit": "gram",
            "default_serving_g": 100.0,
            "source": "usda",
        }
        if insert_food(conn, food):
            existing_ids.add(food["food_id"])
            added += 1

    return added, page + 1


# ── Open Food Facts fetcher ────────────────────────────────────────────────────
def fetch_off_page(page: int, page_size: int = 50) -> list:
    url = (
        f"https://world.openfoodfacts.org/cgi/search.pl"
        f"?action=process&tagtype_0=countries&tag_contains_0=contains&tag_0=israel"
        f"&json=1&page={page}&page_size={page_size}&fields="
        f"code,product_name,product_name_he,nutriments,categories_tags"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BiteFit/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data.get("products", [])
    except Exception as e:
        log.error(f"OFF page {page} failed: {e}")
        return []


def process_off(conn: sqlite3.Connection, existing_ids: set, page: int) -> tuple[int, int]:
    """Fetch one OFF page, insert new Israeli products. Returns (added, next_page)."""
    products = fetch_off_page(page)
    if not products:
        return 0, 1  # wrap around

    added = 0
    for p in products:
        code = p.get("code", "")
        if not code:
            continue
        food_id = f"off_{code}"
        if food_id in existing_ids:
            continue

        name_he = (p.get("product_name_he") or "").strip()
        name_en = (p.get("product_name") or "").strip()
        if not name_he and not name_en:
            continue

        n = p.get("nutriments", {})
        calories = n.get("energy-kcal_100g") or n.get("energy_100g", 0)
        if calories:
            calories = calories / 4.184 if n.get("energy_100g") and not n.get("energy-kcal_100g") else calories
        if not calories or float(calories) <= 0:
            continue

        food = {
            "food_id": food_id,
            "name_he": name_he,
            "name_en": name_en,
            "category": "other",
            "calories_kcal": round(float(calories), 1),
            "protein_g": round(float(n.get("proteins_100g", 0) or 0), 1),
            "carbs_g": round(float(n.get("carbohydrates_100g", 0) or 0), 1),
            "fat_g": round(float(n.get("fat_100g", 0) or 0), 1),
            "fiber_g": round(float(n.get("fiber_100g", 0) or 0), 1),
            "sugar_g": round(float(n.get("sugars_100g", 0) or 0), 1),
            "sodium_mg": round(float(n.get("sodium_100g", 0) or 0) * 1000, 1),
            "default_unit": "gram",
            "default_serving_g": 100.0,
            "source": "off",
        }
        if insert_food(conn, food):
            existing_ids.add(food_id)
            added += 1

    return added, page + 1


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    start = datetime.now()
    log.info(f"=== Nightly expand started ===")

    cursor = load_cursor()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    existing_ids = get_existing_ids(conn)
    before = len(existing_ids)
    log.info(f"Foods before: {before}")

    # ── 1. USDA Branded Foods ─────────────────────────────────────────────────
    usda_type = cursor.get("usda_type", "Branded")
    usda_added, next_usda_page = process_usda(
        conn, existing_ids, cursor["usda_page"], limit=200, data_type=usda_type
    )
    conn.commit()
    cursor["usda_page"] = next_usda_page
    cursor["usda_type"] = usda_type
    log.info(f"USDA {usda_type}: +{usda_added} foods (next page: {next_usda_page})")
    time.sleep(1)

    # ── 2. Open Food Facts ────────────────────────────────────────────────────
    off_added, next_off_page = process_off(conn, existing_ids, cursor["off_page"])
    conn.commit()
    cursor["off_page"] = next_off_page
    log.info(f"OFF: +{off_added} foods (next page: {next_off_page})")

    # ── Summary ───────────────────────────────────────────────────────────────
    after = conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
    conn.close()
    save_cursor(cursor)

    duration = (datetime.now() - start).seconds
    log.info(f"Done: {after} total foods (+{after - before} new) in {duration}s")
    print(f"✅ Nightly expand complete: +{after - before} foods → {after} total ({duration}s)")


if __name__ == "__main__":
    main()
