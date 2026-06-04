#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_database.py — builds the full nutrition.db from scratch.

Steps:
  1. Create / migrate schema (all tables)
  2. Seed foods from foods_extended.json (319 items)
  3. Ingest USDA FoodData Central SR Legacy (~8,700 foods)
  4. Ingest Open Food Facts — Israeli products (~15k)
  5. Migrate user data from JSON → SQLite
        users, profiles, food_log, water_log, workouts, daily_summaries

Run:
    python scripts/build_database.py

Requires:
    pip install requests tqdm
"""

import os, sys, json, sqlite3, time, hashlib, re
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DB_PATH    = ROOT / "storage" / "nutrition.db"
DATA_DIR   = ROOT / "nutrition_app" / "data"
AGENTS_DIR = ROOT / "storage_agents"

USDA_API_KEY = "T8prNHixUyhB6WSZXVMCuEeslJ1HdZlvkc42rrsL"

# ─────────────────────────────────────────────────────────────────────────────
# 1. SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ── Food catalog ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foods (
    food_id          TEXT PRIMARY KEY,
    name_he          TEXT NOT NULL,
    name_en          TEXT,
    category         TEXT,
    calories_kcal    REAL,
    protein_g        REAL,
    carbs_g          REAL,
    fat_g            REAL,
    fiber_g          REAL,
    sugar_g          REAL,
    sodium_mg        REAL,
    default_unit     TEXT DEFAULT 'gram',
    default_serving_g REAL DEFAULT 100,
    image_url        TEXT,
    barcode          TEXT,
    source           TEXT DEFAULT 'manual',
    aliases_he       TEXT,   -- JSON array
    aliases_en       TEXT,   -- JSON array
    is_custom        INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_foods_name_he  ON foods(name_he);
CREATE INDEX IF NOT EXISTS idx_foods_barcode  ON foods(barcode);
CREATE INDEX IF NOT EXISTS idx_foods_category ON foods(category);

-- ── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id    TEXT PRIMARY KEY,
    name       TEXT,
    email      TEXT UNIQUE,
    password_hash TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ── Profiles ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
    user_id          TEXT PRIMARY KEY REFERENCES users(user_id),
    name             TEXT,
    gender           TEXT,
    date_of_birth    TEXT,
    height_cm        REAL,
    weight_kg        REAL,
    activity_level   TEXT,
    goal             TEXT,
    pace             TEXT DEFAULT 'moderate',
    target_weight_kg REAL,
    weekly_change_kg REAL,
    weeks_to_goal    INTEGER,
    meal_preferences TEXT,  -- JSON
    notes            TEXT,
    updated_at       TEXT DEFAULT (datetime('now'))
);

-- ── Food log ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS food_log (
    entry_id   TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(user_id),
    date       TEXT NOT NULL,
    food_id    TEXT,
    food_name  TEXT NOT NULL,
    grams      REAL NOT NULL,
    calories   REAL,
    protein    REAL,
    carbs      REAL,
    fat        REAL,
    meal_type  TEXT,
    timestamp  TEXT
);
CREATE INDEX IF NOT EXISTS idx_food_log_user_date ON food_log(user_id, date);

-- ── Water log ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS water_log (
    entry_id   TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(user_id),
    date       TEXT NOT NULL,
    amount_ml  REAL NOT NULL,
    source     TEXT DEFAULT 'bottle',
    timestamp  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_water_log_user_date ON water_log(user_id, date);

-- ── Water goal ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS water_goals (
    user_id       TEXT PRIMARY KEY REFERENCES users(user_id),
    daily_goal_ml REAL DEFAULT 2000,
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- ── Workouts ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workout_log (
    entry_id          TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(user_id),
    date              TEXT NOT NULL,
    mode              TEXT,
    workout_type      TEXT,
    intensity         TEXT,
    duration_minutes  INTEGER,
    distance_km       REAL,
    calories_burned   REAL,
    timestamp         TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_workout_log_user_date ON workout_log(user_id, date);

-- ── Daily summaries ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_summaries (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL REFERENCES users(user_id),
    date                TEXT NOT NULL,
    calories_eaten      REAL DEFAULT 0,
    protein_eaten       REAL DEFAULT 0,
    carbs_eaten         REAL DEFAULT 0,
    fat_eaten           REAL DEFAULT 0,
    calories_target     REAL DEFAULT 0,
    protein_target      REAL DEFAULT 0,
    carbs_target        REAL DEFAULT 0,
    fat_target          REAL DEFAULT 0,
    calories_burned     REAL DEFAULT 0,
    water_ml            REAL DEFAULT 0,
    UNIQUE(user_id, date)
);

-- ── Meal preferences ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meal_preferences (
    user_id             TEXT PRIMARY KEY REFERENCES users(user_id),
    picks               TEXT,  -- JSON
    variants            TEXT,  -- JSON
    fixed_overrides     TEXT,  -- JSON
    is_onboarded        INTEGER DEFAULT 0,
    show_streaks        INTEGER DEFAULT 1,
    daily_notifications INTEGER DEFAULT 0,
    weekly_summary      INTEGER DEFAULT 1,
    updated_at          TEXT DEFAULT (datetime('now'))
);

-- ── Barcode cache ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS barcode_cache (
    barcode    TEXT PRIMARY KEY,
    food_id    TEXT REFERENCES foods(food_id),
    food_name  TEXT,
    source     TEXT,
    cached_at  TEXT DEFAULT (datetime('now'))
);
"""


def create_schema(conn: sqlite3.Connection):
    print("📐 Creating schema...")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    print("   ✓ Schema ready")


# ─────────────────────────────────────────────────────────────────────────────
# 2. SEED from foods_extended.json
# ─────────────────────────────────────────────────────────────────────────────

def seed_from_json(conn: sqlite3.Connection):
    json_path = DATA_DIR / "foods_extended.json"
    if not json_path.exists():
        print("⚠️  foods_extended.json not found, skipping")
        return

    with open(json_path, "rb") as f:
        foods = json.loads(f.read().decode("utf-8"))

    inserted = 0
    for item in foods:
        fid   = item.get("food_id", "")
        n     = item.get("nutrition_per_100g") or {}
        image = _spoonacular_url(item.get("name_en", "") or item.get("name_he", ""))
        try:
            conn.execute("""
                INSERT OR IGNORE INTO foods
                  (food_id, name_he, name_en, category,
                   calories_kcal, protein_g, carbs_g, fat_g,
                   fiber_g, sugar_g, sodium_mg,
                   default_serving_g, image_url, source,
                   aliases_he, aliases_en)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'json',?,?)
            """, (
                fid,
                item.get("name_he",""),
                item.get("name_en",""),
                item.get("category",""),
                n.get("calories_kcal"),
                n.get("protein_g"),
                n.get("carbs_g"),
                n.get("fat_g"),
                n.get("fiber_g"),
                n.get("sugar_g"),
                n.get("sodium_mg"),
                item.get("default_serving_g", 100),
                image,
                json.dumps(item.get("aliases_he") or [], ensure_ascii=False),
                json.dumps(item.get("aliases_en") or [], ensure_ascii=False),
            ))
            inserted += 1
        except Exception as e:
            print(f"   ⚠  {fid}: {e}")

    conn.commit()
    print(f"   ✓ Seeded {inserted} foods from foods_extended.json")


def _spoonacular_url(name_en: str) -> str:
    """Generate a Spoonacular CDN URL from an English food name (best-effort)."""
    if not name_en:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", name_en.lower()).strip("-")
    return f"https://spoonacular.com/cdn/ingredients_100x100/{slug}.png"


# ─────────────────────────────────────────────────────────────────────────────
# 3. USDA FoodData Central — SR Legacy
# ─────────────────────────────────────────────────────────────────────────────

USDA_BASE = "https://api.nal.usda.gov/fdc/v1"

USDA_CATEGORY_MAP = {
    "Beef Products":               "protein",
    "Poultry Products":            "protein",
    "Pork Products":               "protein",
    "Lamb, Veal, and Game Products": "protein",
    "Finfish and Shellfish Products": "protein",
    "Sausages and Luncheon Meats": "protein",
    "Legumes and Legume Products": "legume",
    "Nut and Seed Products":       "nut_seed",
    "Dairy and Egg Products":      "dairy",
    "Fruits and Fruit Juices":     "fruit",
    "Vegetables and Vegetable Products": "vegetable",
    "Cereal Grains and Pasta":     "grain",
    "Baked Products":              "carbohydrate",
    "Sweets":                      "sweet",
    "Fats and Oils":               "fat",
    "Beverages":                   "beverage",
    "Soups, Sauces, and Gravies":  "other",
    "Snacks":                      "snack",
    "Spices and Herbs":            "condiment",
    "Baby Foods":                  "other",
    "Fast Foods":                  "other",
    "Meals, Entrees, and Side Dishes": "other",
    "Restaurant Foods":            "other",
}


def _usda_nutrient(nutrients: list, nutrient_id: int) -> float | None:
    for n in nutrients:
        if n.get("nutrientId") == nutrient_id or n.get("nutrient", {}).get("id") == nutrient_id:
            return n.get("amount")
    return None


def ingest_usda(conn: sqlite3.Connection, max_pages: int = 50):
    """Download SR Legacy foods from USDA FoodData Central."""
    import urllib.request, urllib.parse

    print("\n🇺🇸 Downloading USDA SR Legacy foods...")
    page_size = 200
    inserted = 0
    skipped  = 0

    for page in range(1, max_pages + 1):
        url = (
            f"{USDA_BASE}/foods/list"
            f"?api_key={USDA_API_KEY}"
            f"&dataType=SR%20Legacy"
            f"&pageSize={page_size}"
            f"&pageNumber={page}"
        )
        try:
            req  = urllib.request.Request(url, headers={"User-Agent": "BiteFit/1.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            items = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"   ⚠  Page {page} error: {e}")
            break

        if not items:
            print(f"   ↳ No more items at page {page}")
            break

        for item in items:
            fdc_id   = item.get("fdcId", "")
            food_id  = f"usda_{fdc_id}"
            name_en  = item.get("description", "").title()
            category = USDA_CATEGORY_MAP.get(item.get("foodCategory", ""), "other")
            nutrients = item.get("foodNutrients", [])

            cal   = _usda_nutrient(nutrients, 1008)   # Energy
            prot  = _usda_nutrient(nutrients, 1003)   # Protein
            carbs = _usda_nutrient(nutrients, 1005)   # Carbohydrate
            fat   = _usda_nutrient(nutrients, 1004)   # Total Fat
            fiber = _usda_nutrient(nutrients, 1079)   # Fiber
            sugar = _usda_nutrient(nutrients, 2000)   # Sugars
            sodium= _usda_nutrient(nutrients, 1093)   # Sodium

            image = _spoonacular_url(name_en)

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO foods
                      (food_id, name_he, name_en, category,
                       calories_kcal, protein_g, carbs_g, fat_g,
                       fiber_g, sugar_g, sodium_mg,
                       image_url, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'usda')
                """, (
                    food_id, name_en, name_en, category,
                    cal, prot, carbs, fat,
                    fiber, sugar, sodium,
                    image,
                ))
                inserted += 1
            except Exception as e:
                skipped += 1

        conn.commit()
        total_so_far = page * page_size
        print(f"   Page {page:3d} — {total_so_far:,} processed | {inserted:,} inserted", end="\r")
        time.sleep(0.1)   # be polite

    print(f"\n   ✓ USDA done — {inserted:,} foods inserted, {skipped} skipped")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Open Food Facts — Israeli + popular products
# ─────────────────────────────────────────────────────────────────────────────

OFF_BASE = "https://world.openfoodfacts.org/cgi/search.pl"


def _off_nutrient(product: dict, key: str) -> float | None:
    val = product.get("nutriments", {}).get(key)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def ingest_off(conn: sqlite3.Connection, max_pages: int = 60):
    """Download Israeli products from Open Food Facts."""
    import urllib.request, urllib.parse

    print("\n🌍 Downloading Open Food Facts (Israeli products)...")
    page_size = 100
    inserted = 0
    skipped  = 0

    for page in range(1, max_pages + 1):
        params = urllib.parse.urlencode({
            "action":       "process",
            "tagtype_0":    "countries",
            "tag_contains_0": "contains",
            "tag_0":        "israel",
            "json":         1,
            "page_size":    page_size,
            "page":         page,
            "fields":       "code,product_name,product_name_he,product_name_en,"
                            "categories_tags,nutriments,image_url,image_small_url",
        })
        url = f"{OFF_BASE}?{params}"

        try:
            req  = urllib.request.Request(url, headers={"User-Agent": "BiteFit/1.0 (contact: dviryona8@gmail.com)"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"   ⚠  Page {page} error: {e}")
            time.sleep(2)
            continue

        products = data.get("products", [])
        if not products:
            print(f"   ↳ No more products at page {page}")
            break

        for p in products:
            barcode  = p.get("code", "")
            name_he  = (p.get("product_name_he") or p.get("product_name") or "").strip()
            name_en  = (p.get("product_name_en") or p.get("product_name") or "").strip()
            if not name_he and not name_en:
                skipped += 1
                continue

            food_id  = f"off_{barcode}" if barcode else f"off_{hashlib.md5(name_he.encode()).hexdigest()[:8]}"
            image    = p.get("image_small_url") or p.get("image_url") or _spoonacular_url(name_en)

            cal   = _off_nutrient(p, "energy-kcal_100g") or _off_nutrient(p, "energy_100g")
            if cal and cal > 900:   # energy_100g is sometimes kJ, convert
                cal = round(cal / 4.184, 1)
            prot  = _off_nutrient(p, "proteins_100g")
            carbs = _off_nutrient(p, "carbohydrates_100g")
            fat   = _off_nutrient(p, "fat_100g")
            fiber = _off_nutrient(p, "fiber_100g")
            sugar = _off_nutrient(p, "sugars_100g")
            sodium= _off_nutrient(p, "sodium_100g")
            if sodium:
                sodium = sodium * 1000   # kg → mg

            cats = p.get("categories_tags", [])
            category = _off_category(cats)

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO foods
                      (food_id, name_he, name_en, category,
                       calories_kcal, protein_g, carbs_g, fat_g,
                       fiber_g, sugar_g, sodium_mg,
                       image_url, barcode, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'off')
                """, (
                    food_id, name_he or name_en, name_en or name_he, category,
                    cal, prot, carbs, fat, fiber, sugar, sodium,
                    image, barcode,
                ))
                if barcode:
                    conn.execute("""
                        INSERT OR IGNORE INTO barcode_cache (barcode, food_id, food_name, source)
                        VALUES (?,?,?,'off')
                    """, (barcode, food_id, name_he or name_en))
                inserted += 1
            except Exception as e:
                skipped += 1

        conn.commit()
        print(f"   Page {page:3d} — {inserted:,} inserted", end="\r")
        time.sleep(0.3)

    # Also fetch popular global products (not country-specific)
    print(f"\n   ✓ OFF Israel done — {inserted:,} inserted")
    inserted += _off_global(conn, max_pages=40)
    print(f"   ✓ OFF total — {inserted:,} inserted")


def _off_global(conn: sqlite3.Connection, max_pages: int = 40) -> int:
    """Fetch popular worldwide products from Open Food Facts."""
    import urllib.request, urllib.parse

    print("\n🌐 Downloading Open Food Facts (popular worldwide)...")
    page_size = 100
    inserted = 0

    for page in range(1, max_pages + 1):
        params = urllib.parse.urlencode({
            "action":       "process",
            "sort_by":      "popularity_key",
            "json":         1,
            "page_size":    page_size,
            "page":         page,
            "fields":       "code,product_name,product_name_he,product_name_en,"
                            "categories_tags,nutriments,image_small_url",
        })
        url = f"{OFF_BASE}?{params}"
        try:
            req  = urllib.request.Request(url, headers={"User-Agent": "BiteFit/1.0 (contact: dviryona8@gmail.com)"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"   ⚠  Global page {page} error: {e}")
            time.sleep(2)
            continue

        products = data.get("products", [])
        if not products:
            break

        for p in products:
            barcode  = p.get("code", "")
            name_he  = (p.get("product_name_he") or "").strip()
            name_en  = (p.get("product_name_en") or p.get("product_name") or "").strip()
            if not name_en:
                continue

            food_id = f"off_{barcode}" if barcode else f"off_{hashlib.md5(name_en.encode()).hexdigest()[:8]}"
            image   = p.get("image_small_url") or _spoonacular_url(name_en)
            cal     = _off_nutrient(p, "energy-kcal_100g") or _off_nutrient(p, "energy_100g")
            if cal and cal > 900:
                cal = round(cal / 4.184, 1)
            prot  = _off_nutrient(p, "proteins_100g")
            carbs = _off_nutrient(p, "carbohydrates_100g")
            fat   = _off_nutrient(p, "fat_100g")
            fiber = _off_nutrient(p, "fiber_100g")
            sugar = _off_nutrient(p, "sugars_100g")
            sodium= _off_nutrient(p, "sodium_100g")
            if sodium:
                sodium = sodium * 1000
            cats = p.get("categories_tags", [])
            category = _off_category(cats)

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO foods
                      (food_id, name_he, name_en, category,
                       calories_kcal, protein_g, carbs_g, fat_g,
                       fiber_g, sugar_g, sodium_mg,
                       image_url, barcode, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'off')
                """, (
                    food_id, name_he or name_en, name_en, category,
                    cal, prot, carbs, fat, fiber, sugar, sodium,
                    image, barcode,
                ))
                if barcode:
                    conn.execute("""
                        INSERT OR IGNORE INTO barcode_cache (barcode, food_id, food_name, source)
                        VALUES (?,?,?,'off')
                    """, (barcode, food_id, name_he or name_en))
                inserted += 1
            except:
                pass

        conn.commit()
        print(f"   Global page {page:3d} — {inserted:,} inserted", end="\r")
        time.sleep(0.3)

    print(f"\n   ✓ OFF global done — {inserted:,} inserted")
    return inserted


def _off_category(tags: list) -> str:
    mapping = {
        "meat":        "protein",
        "poultry":     "protein",
        "fish":        "protein",
        "seafood":     "protein",
        "eggs":        "dairy",
        "dairy":       "dairy",
        "milk":        "dairy",
        "cheese":      "dairy",
        "yogurt":      "dairy",
        "vegetables":  "vegetable",
        "fruits":      "fruit",
        "cereals":     "grain",
        "bread":       "carbohydrate",
        "pasta":       "carbohydrate",
        "rice":        "carbohydrate",
        "legumes":     "legume",
        "nuts":        "nut_seed",
        "seeds":       "nut_seed",
        "beverages":   "beverage",
        "snacks":      "snack",
        "sweets":      "sweet",
        "chocolate":   "sweet",
        "oils":        "fat",
        "fats":        "fat",
        "condiments":  "condiment",
        "spices":      "condiment",
    }
    for tag in tags:
        tag_lower = tag.replace("en:", "").replace("-", " ")
        for k, v in mapping.items():
            if k in tag_lower:
                return v
    return "other"


# ─────────────────────────────────────────────────────────────────────────────
# 5. MIGRATE USER DATA from JSON → SQLite
# ─────────────────────────────────────────────────────────────────────────────

def migrate_users(conn: sqlite3.Connection):
    path = AGENTS_DIR / "users.json"
    if not path.exists():
        return
    with open(path, "rb") as f:
        users = json.loads(f.read().decode("utf-8"))
    for uid, info in users.items():
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, name, created_at)
            VALUES (?,?,?)
        """, (uid, info.get("name",""), info.get("created_at", datetime.now().isoformat())))
    conn.commit()
    print(f"   ✓ Migrated {len(users)} users")


def migrate_profiles(conn: sqlite3.Connection):
    profiles_dir = AGENTS_DIR / "profiles"
    if not profiles_dir.exists():
        return
    count = 0
    for f in profiles_dir.glob("*.json"):
        with open(f, "rb") as fh:
            p = json.loads(fh.read().decode("utf-8"))
        uid = p.get("user_id", f.stem)
        # ensure user row exists
        conn.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?,?)",
                     (uid, p.get("name","")))
        mp = p.get("meal_preferences")
        conn.execute("""
            INSERT OR REPLACE INTO profiles
              (user_id, name, gender, date_of_birth, height_cm, weight_kg,
               activity_level, goal, pace, target_weight_kg, weekly_change_kg,
               weeks_to_goal, meal_preferences, notes, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            uid, p.get("name"), p.get("gender"), p.get("date_of_birth"),
            p.get("height_cm"), p.get("weight_kg"), p.get("activity_level"),
            p.get("goal"), p.get("pace","moderate"), p.get("target_weight_kg"),
            p.get("weekly_change_kg"), p.get("weeks_to_goal"),
            json.dumps(mp, ensure_ascii=False) if isinstance(mp, dict) else mp,
            p.get("notes"), p.get("updated_at", datetime.now().isoformat()),
        ))
        count += 1
    conn.commit()
    print(f"   ✓ Migrated {count} profiles")


def migrate_food_log(conn: sqlite3.Connection):
    log_dir = AGENTS_DIR / "food_log"
    if not log_dir.exists():
        return
    total = 0
    for f in log_dir.glob("*.json"):
        uid = f.stem
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        with open(f, "rb") as fh:
            data = json.loads(fh.read().decode("utf-8"))
        for date_key, entries in data.items():
            for e in entries:
                conn.execute("""
                    INSERT OR IGNORE INTO food_log
                      (entry_id, user_id, date, food_id, food_name, grams,
                       calories, protein, carbs, fat, meal_type, timestamp)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    e.get("entry_id", hashlib.md5(json.dumps(e).encode()).hexdigest()[:16]),
                    uid, date_key,
                    e.get("food_id"), e.get("food_name",""),
                    e.get("grams",0), e.get("calories"), e.get("protein"),
                    e.get("carbs"), e.get("fat"), e.get("meal_type"),
                    e.get("timestamp"),
                ))
                total += 1
    conn.commit()
    print(f"   ✓ Migrated {total} food log entries")


def migrate_water(conn: sqlite3.Connection):
    water_dir = AGENTS_DIR / "water"
    if not water_dir.exists():
        return
    total = 0
    for f in water_dir.glob("*.json"):
        uid = f.stem
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        with open(f, "rb") as fh:
            data = json.loads(fh.read().decode("utf-8"))

        goal = None
        if isinstance(data, dict):
            goal = (data.get("goal") or {}).get("daily_goal_ml")
            intakes = data.get("intakes", {})
        else:
            intakes = {}

        if goal:
            conn.execute("""
                INSERT OR REPLACE INTO water_goals (user_id, daily_goal_ml) VALUES (?,?)
            """, (uid, goal))

        if isinstance(intakes, dict):
            for date_key, entries in intakes.items():
                if not isinstance(entries, list):
                    continue
                for e in entries:
                    conn.execute("""
                        INSERT OR IGNORE INTO water_log
                          (entry_id, user_id, date, amount_ml, source, timestamp)
                        VALUES (?,?,?,?,?,?)
                    """, (
                        e.get("intake_id", hashlib.md5(json.dumps(e).encode()).hexdigest()[:16]),
                        uid, date_key,
                        e.get("amount_ml", 0), e.get("source","bottle"),
                        e.get("timestamp"),
                    ))
                    total += 1

    conn.commit()
    print(f"   ✓ Migrated {total} water entries")


def migrate_daily_summaries(conn: sqlite3.Connection):
    ds_dir = AGENTS_DIR / "daily_summary"
    if not ds_dir.exists():
        return
    total = 0
    for f in ds_dir.glob("*.json"):
        uid = f.stem
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        with open(f, "rb") as fh:
            data = json.loads(fh.read().decode("utf-8"))
        items = data if isinstance(data, list) else data.get("summaries", [])
        for s in items:
            sid = hashlib.md5(f"{uid}{s.get('date','')}".encode()).hexdigest()[:16]
            conn.execute("""
                INSERT OR REPLACE INTO daily_summaries
                  (id, user_id, date, calories_eaten, protein_eaten, carbs_eaten,
                   fat_eaten, calories_target, protein_target, carbs_target,
                   fat_target, calories_burned, water_ml)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                sid, uid, s.get("date"),
                s.get("calories_eaten",0), s.get("protein_eaten",0),
                s.get("carbs_eaten",0), s.get("fat_eaten",0),
                s.get("calories_target",0), s.get("protein_target",0),
                s.get("carbs_target",0), s.get("fat_target",0),
                s.get("calories_burned",0), s.get("water_ml",0),
            ))
            total += 1
    conn.commit()
    print(f"   ✓ Migrated {total} daily summaries")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 60)
    print("  BiteFit Database Builder")
    print("=" * 60)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    # 1. Schema
    create_schema(conn)

    # 2. Seed local JSON
    print("\n📦 Seeding from local data...")
    seed_from_json(conn)

    # 3. Migrate user data
    print("\n👤 Migrating user data from JSON...")
    migrate_users(conn)
    migrate_profiles(conn)
    migrate_food_log(conn)
    migrate_water(conn)
    migrate_daily_summaries(conn)

    # 4. USDA
    ingest_usda(conn, max_pages=50)

    # 5. Open Food Facts
    ingest_off(conn, max_pages=60)

    # Summary
    rows = conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print(f"  ✅ DONE in {elapsed:.0f}s")
    print(f"  📊 Total foods in DB: {rows:,}")
    print(f"  💾 DB size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
