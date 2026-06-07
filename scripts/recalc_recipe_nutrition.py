"""
Recalculates total_nutrition for all recipes based on actual ingredient
quantities matched against the foods DB (storage/nutrition.db).

Run: python scripts/recalc_recipe_nutrition.py
"""

import json
import sqlite3
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RECIPES_PATH = Path("storage_agents/recipes/recipes.json")
DB_PATH = Path("storage/nutrition.db")

# ─── manual nutrition overrides (per 100g) ────────────────────────────────────
# For ingredients not found in the DB.
# Values: (calories, protein_g, carbs_g, fat_g)
MANUAL_NUTRITION: dict[str, tuple] = {
    # spices / condiments
    "hawaij spice":           (300, 10, 45, 10),
    "amba (mango pickle sauce)":(80,  0,  20,  0),
    "raw tahini (whole)":     (595, 17, 21, 53),
    "date syrup (silan)":     (310,  1, 76,  0),
    "roasted eggplant dip":   ( 80,  2,  8,  5),
    "tomato sauce":           ( 35,  2,  8,  0),
    "bechamel sauce":         (100,  3, 10,  5),
    "vegetable salad":        ( 30,  1,  6,  0),

    # dairy / eggs
    "egg whites":             ( 52, 11,  1,  0),
    "heavy cream":            (340,  2,  3, 36),
    "laban (fermented milk)": ( 61,  3,  5,  3),
    "casein protein powder":  (370, 80,  5,  2),

    # grains / dough / bread
    "shortcrust pastry":      (450,  6, 50, 26),
    "pizza dough":            (250,  8, 50,  2),
    "lasagna sheets":         (350, 12, 70,  2),
    "arborio rice":           (130,  3, 28,  0),
    "sushi rice":             (130,  3, 28,  0),
    "ciabatta bread":         (270,  9, 50,  4),
    "laffa bread":            (265,  8, 52,  3),
    "popcorn kernels":        (375, 11, 74,  4),
    "sahlab (hot milk drink)":(120,  3, 25,  1),

    # meat / fish
    "beef chunks":            (250, 26,  0, 16),
    "barramundi fillet":      ( 90, 19,  0,  1),
    "cod fillet":             ( 82, 18,  0,  1),
    "fresh salmon":           (208, 20,  0, 13),

    # nuts / seeds
    "ground almonds":         (579, 21, 22, 50),
    "pistachios":             (562, 20, 28, 45),
    "dried fruits":           (250,  2, 66,  0),

    # vegetables (unusual names)
    "cabbage leaves":         ( 25,  1,  6,  0),
    "portobello mushrooms":   ( 22,  2,  4,  0),
    "cold water":             (  0,  0,  0,  0),
    "frying oil":             (884,  0,  0,100),
    "red onion":              ( 40,  1,  9,  0),
    "black lentils (beluga)": (116,  9, 20,  0),
    "red bell pepper":        ( 31,  1,  6,  0),

    # other
    "acai puree":             ( 70,  1,  4,  5),
    "frozen banana":          ( 89,  1, 23,  0),
    "linguine pasta":         (350, 12, 70,  2),
    "almond milk":            ( 15,  0,  1,  1),
    "soy milk":               ( 33,  3,  2,  2),
    "falafel balls":          (333, 13, 32, 17),
    "pita bread":             (275,  9, 56,  1),
    "hummus":                 (177,  8, 20, 10),
    "pickles":                ( 11,  1,  2,  0),
    "portobello mushroom":    ( 22,  2,  4,  0),
    "black lentils (beluga)": (116,  9, 20,  0),
    "red bell pepper":        ( 31,  1,  6,  0),
    "manaqish":               (280,  8, 42, 10),
    "kousa":                  ( 17,  1,  4,  0),
    "makdoush":               (150,  3, 12, 10),
    "knafeh":                 (350,  7, 45, 16),
    "vegetarian ground meat": (160, 18,  6,  7),
    "vegan meatballs":        (170, 14, 12,  7),

    # ── מרכיבי אפייה / בישול ────────────────────────────────────────────────
    "flour":                  (364, 10, 76,  1),
    "all purpose flour":      (364, 10, 76,  1),
    "whole wheat flour":      (340, 13, 72,  2),
    "sugar":                  (387,  0,100,  0),
    "brown sugar":            (377,  0, 97,  0),
    "powdered sugar":         (389,  0,100,  0),
    "oil":                    (884,  0,  0,100),
    "vegetable oil":          (884,  0,  0,100),
    "sunflower oil":          (884,  0,  0,100),
    "coconut oil":            (862,  0,  0,100),
    "baking powder":          ( 53,  0, 28,  0),
    "baking soda":            (  0,  0,  0,  0),
    "salt":                   (  0,  0,  0,  0),
    "black pepper":           (255, 10, 64,  3),
    "turmeric":               (312,  9, 67,  3),
    "cumin":                  (375, 18, 44, 22),
    "paprika":                (282, 14, 54, 13),
    "sweet paprika":          (282, 14, 54, 13),
    "cinnamon":               (247,  4, 81,  1),
    "oregano":                (265,  9, 69,  4),
    "thyme":                  (101,  6, 24,  2),
    "dill":                   ( 43,  3,  7,  1),
    "basil":                  ( 23,  3,  3,  1),
    "cocoa powder":           (228, 20, 58, 14),
    "dark chocolate":         (546,  5, 60, 31),
    "chocolate chips":        (500,  5, 59, 30),
    "vanilla extract":        (288,  0, 13,  0),
    "yeast":                  (325, 38, 41,  7),

    # ── בשר / עוף ────────────────────────────────────────────────────────────
    "ground chicken":         (143, 17,  0,  8),
    "ground turkey":          (135, 20,  0,  5),
    "chicken pieces":         (165, 25,  0,  7),
    "chicken drumsticks":     (172, 23,  0,  8),
    "chicken thighs":         (209, 20,  0, 14),
    "chicken pargiot":        (209, 20,  0, 14),
    "ground meat":            (250, 26,  0, 16),
    "lamb":                   (258, 25,  0, 17),
    "lamb meat":              (258, 25,  0, 17),
    "veal":                   (172, 26,  0,  7),

    # ── מוצרי חלב ────────────────────────────────────────────────────────────
    "parmesan cheese":        (431, 38,  4, 29),
    "mozzarella cheese":      (280, 28,  2, 17),
    "feta cheese":            (264, 14,  4, 21),
    "cream cheese":           (342,  6,  4, 34),
    "sour cream":             (193,  3,  4, 19),
    "whipped cream":          (340,  2,  3, 36),
    "condensed milk":         (321,  8, 54,  9),

    # ── דגים / פירות ים ──────────────────────────────────────────────────────
    "sushi rice":             (130,  3, 28,  0),

    # ── לחמים / בצקים ────────────────────────────────────────────────────────
    "waffles":                (291,  8, 37, 12),
    "crepe":                  (210,  6, 28,  8),
    "pancake":                (227,  5, 28, 10),
    "puff pastry":            (558,  8, 46, 40),
    "phyllo dough":           (347,  9, 55, 10),
    "breadcrumbs":            (395, 13, 72,  5),
    "croutons":               (407, 11, 57, 16),
    "tortilla":               (218,  6, 33,  8),
    "jachnun":                (400,  8, 45, 21),

    # ── שונות ────────────────────────────────────────────────────────────────
    "jam":                    (278,  0, 69,  0),
    "maple syrup":            (260,  0, 67,  0),
    "nutella":                (539,  6, 58, 31),
    "mayonnaise":             (680,  1,  1, 75),
    "ketchup":                (101,  1, 27,  0),
    "soy sauce":              ( 53,  8,  5,  0),
    "worcestershire sauce":   ( 78,  3, 19,  0),
    "tahini sauce":           (595, 17, 21, 53),
    "caesar dressing":        (329,  4, 11, 32),
    "pistachio":              (562, 20, 28, 45),
    "pine nuts":              (673, 14, 13, 68),
    "sesame seeds":           (573, 18, 23, 50),
    "chia seeds":             (486, 17, 42, 31),
    "flaxseeds":              (534, 18, 29, 42),
    "romaine lettuce":        ( 17,  1,  3,  0),
    "iceberg lettuce":        ( 14,  1,  2,  0),
    "baby spinach":           ( 23,  3,  4,  0),
    "arugula":                ( 25,  2,  4,  0),
    "edamame":                (122, 11,  9,  5),
    "tofu firm":              ( 76,  8,  2,  5),
    "tempeh":                 (195, 20, 10, 11),
}

# ─── load data ────────────────────────────────────────────────────────────────

with open(RECIPES_PATH, encoding="utf-8") as f:
    recipes = json.load(f)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT food_id, name_he, name_en, calories_kcal,
           protein_g, carbs_g, fat_g, aliases_he, aliases_en
    FROM foods
    WHERE calories_kcal IS NOT NULL
""")
foods_rows = cur.fetchall()


# ─── build lookup index ───────────────────────────────────────────────────────

def _tokens(s: str) -> set:
    return set(re.findall(r"[a-zא-ת0-9]+", s.lower())) if s else set()


food_index: list[dict] = []
for row in foods_rows:
    aliases_en, aliases_he = [], []
    try:
        aliases_en = json.loads(row["aliases_en"]) if row["aliases_en"] else []
    except Exception:
        pass
    try:
        aliases_he = json.loads(row["aliases_he"]) if row["aliases_he"] else []
    except Exception:
        pass

    all_names_en = [row["name_en"]] + aliases_en
    all_names_he = [row["name_he"]] + aliases_he

    food_index.append({
        "name_en": row["name_en"],
        "name_he": row["name_he"],
        "cal":     row["calories_kcal"],
        "protein": row["protein_g"],
        "carbs":   row["carbs_g"],
        "fat":     row["fat_g"],
        "en_tokens": [_tokens(n) for n in all_names_en],
        "he_tokens": [_tokens(n) for n in all_names_he],
    })


def find_food(food_name_en: str, food_name_he: str = "") -> dict | None:
    q_en = food_name_en.lower().strip()
    q_he = (food_name_he or "").strip()
    q_en_tokens = _tokens(q_en)
    q_he_tokens = _tokens(q_he)

    # check manual overrides first (case-insensitive)
    for key, vals in MANUAL_NUTRITION.items():
        if key == q_en or key == q_en.lower():
            return {"cal": vals[0], "protein": vals[1], "carbs": vals[2], "fat": vals[3]}

    # exact en name
    for food in food_index:
        if food["name_en"].lower() == q_en:
            return food

    # exact alias en token match
    for food in food_index:
        for alias_t in food["en_tokens"]:
            if alias_t and q_en_tokens and alias_t == q_en_tokens:
                return food

    # exact he
    for food in food_index:
        if food["name_he"] == q_he and q_he:
            return food
        for alias_t in food["he_tokens"]:
            if alias_t and q_he_tokens and alias_t == q_he_tokens:
                return food

    # token subset match (en)
    if q_en_tokens:
        candidates = []
        for food in food_index:
            for alias_t in food["en_tokens"]:
                if q_en_tokens and q_en_tokens.issubset(alias_t):
                    candidates.append((len(alias_t) - len(q_en_tokens), food))
                    break
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

    # token subset match (he)
    if q_he_tokens:
        candidates = []
        for food in food_index:
            for alias_t in food["he_tokens"]:
                if q_he_tokens and q_he_tokens.issubset(alias_t):
                    candidates.append((len(alias_t) - len(q_he_tokens), food))
                    break
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

    return None


# ─── unit conversion helpers ──────────────────────────────────────────────────

ML_TO_G = {
    "water": 1.0, "milk": 1.03, "almond milk": 1.0, "soy milk": 1.03,
    "olive oil": 0.92, "oil": 0.92, "cream": 1.01, "juice": 1.04,
}

def qty_to_grams(qty: float, unit: str, food_name_en: str) -> float | None:
    unit = unit.lower().strip()
    if unit == "grams":
        return qty
    if unit in ("milliliters", "ml"):
        key = food_name_en.lower().strip()
        density = ML_TO_G.get(key, ML_TO_G.get("water", 1.0))
        return qty * density
    return None  # unsupported unit


# ─── recalculate ──────────────────────────────────────────────────────────────

unmatched_log: dict[str, list[str]] = {}
updated = 0
skipped = 0

# build food_id → nutrition lookup
food_by_id: dict[str, dict] = {}
for row in foods_rows:
    food_by_id[row["food_id"]] = {
        "cal": row["calories_kcal"], "protein": row["protein_g"],
        "carbs": row["carbs_g"], "fat": row["fat_g"],
    }

for recipe in recipes:
    rid = recipe.get("recipe_id", "?")
    ingredients = recipe.get("ingredients", [])

    total_cal = total_pro = total_carb = total_fat = 0.0
    all_matched = True
    missing = []

    for ing in ingredients:
        # support both schema variants
        food_id = ing.get("food_id")
        en = ing.get("food_name_en", "")
        he = ing.get("food_name", "")
        qty_raw = float(ing.get("quantity_g") or ing.get("quantity") or 0)
        unit = ing.get("unit", "grams") if not ing.get("quantity_g") else "grams"

        qty_g = qty_to_grams(qty_raw, unit, en)
        if qty_g is None:
            all_matched = False
            missing.append(f"{en} (unit={unit})")
            continue

        # prefer direct food_id lookup
        if food_id and food_id in food_by_id:
            food = food_by_id[food_id]
        else:
            food = find_food(en, he)

        if food is None:
            all_matched = False
            missing.append(en or he)
            continue

        factor = qty_g / 100.0
        total_cal  += food["cal"]     * factor
        total_pro  += food["protein"] * factor
        total_carb += food["carbs"]   * factor
        total_fat  += food["fat"]     * factor

    if not all_matched:
        unmatched_log[rid] = missing
        skipped += 1
        continue

    old = recipe.get("total_nutrition", {})
    recipe["total_nutrition"] = {
        "calories": round(total_cal),
        "protein":  round(total_pro, 1),
        "carbs":    round(total_carb, 1),
        "fat":      round(total_fat, 1),
    }
    updated += 1

    cal_diff = round(total_cal) - (old.get("calories") or 0)
    if abs(cal_diff) > 50:
        print(f"  ⚠  {rid} {recipe.get('name_he','')} | ישן: {old.get('calories')} → חדש: {round(total_cal)}  (Δ{cal_diff:+d})")


# ─── save ─────────────────────────────────────────────────────────────────────

with open(RECIPES_PATH, "w", encoding="utf-8") as f:
    json.dump(recipes, f, ensure_ascii=False, indent=2)

print()
print(f"✅ עודכן: {updated} מתכונים")
print(f"⏭  דולג (לא הותאם במלואו): {skipped} מתכונים")
print()

if unmatched_log:
    print("── עדיין לא הותאם ──")
    for rid, items in unmatched_log.items():
        print(f"  {rid}: {', '.join(items)}")
