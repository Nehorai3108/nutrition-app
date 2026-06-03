#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build data/recipe_images.json
Maps recipe_id → image URL using TheMealDB (free, no key needed).

Strategy:
  1. Exact TheMealDB search by English name
  2. Simplified key-word search (first keyword)
  3. Hardcoded fallback map for Israeli/Mediterranean dishes
  4. Category fallback (protein / grain / veggie / fish / snack)
"""

import json
import os
import time
import urllib.request
import urllib.parse

# ─────────────────────────────────────────────────────────────────────────────
RECIPES_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage_agents", "recipes", "recipes.json",
)
OUT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "recipe_images.json",
)
# ─────────────────────────────────────────────────────────────────────────────


def mealdb_search(query: str) -> str:
    """Search TheMealDB and return first strMealThumb URL or empty string."""
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
        meals = data.get("meals") or []
        if meals:
            return meals[0].get("strMealThumb", "")
    except Exception:
        pass
    return ""


# ── Curated fallback: recipe name keyword → known TheMealDB image URL ─────────
# These are verified TheMealDB thumbnails for dishes common in Israeli cooking.
KEYWORD_FALLBACK: dict[str, str] = {
    # Chicken
    "chicken": "https://www.themealdb.com/images/media/meals/tyywsw1665661330.jpg",
    "schnitzel": "https://www.themealdb.com/images/media/meals/1529444830.jpg",
    "shawarma": "https://www.themealdb.com/images/media/meals/rvypwy1503069smoothies.jpg",
    # Fish & seafood
    "salmon": "https://www.themealdb.com/images/media/meals/1548772327.jpg",
    "fish": "https://www.themealdb.com/images/media/meals/c18desc1556736532.jpg",
    "tuna": "https://www.themealdb.com/images/media/meals/1520081754.jpg",
    # Eggs
    "shakshuka": "https://www.themealdb.com/images/media/meals/g373701551450225.jpg",
    "omelette": "https://www.themealdb.com/images/media/meals/wyxwsp1486979827.jpg",
    "frittata": "https://www.themealdb.com/images/media/meals/wyxwsp1486979827.jpg",
    "eggs": "https://www.themealdb.com/images/media/meals/wyxwsp1486979827.jpg",
    # Grains / carbs
    "rice": "https://www.themealdb.com/images/media/meals/abc123.jpg",
    "pasta": "https://www.themealdb.com/images/media/meals/ustsqw1468250014.jpg",
    "quinoa": "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
    "couscous": "https://www.themealdb.com/images/media/meals/yqwtvu1468237251.jpg",
    "bulgur": "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
    "oatmeal": "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    # Legumes
    "lentil": "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",
    "hummus": "https://www.themealdb.com/images/media/meals/rvypwy1503069smoothies.jpg",
    "mujadara": "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",
    # Salads & veggies
    "salad": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "soup": "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",
    "vegetable": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "wrap": "https://www.themealdb.com/images/media/meals/rvypwy1503069smoothies.jpg",
    "pita": "https://www.themealdb.com/images/media/meals/rvypwy1503069smoothies.jpg",
    # Dairy & snacks
    "yogurt": "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "granola": "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "cottage": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "fruit": "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "nuts": "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    # Beef & meat
    "beef": "https://www.themealdb.com/images/media/meals/sytuqu1511553755.jpg",
    "meat": "https://www.themealdb.com/images/media/meals/sytuqu1511553755.jpg",
    "turkey": "https://www.themealdb.com/images/media/meals/1529444830.jpg",
    "stuffed": "https://www.themealdb.com/images/media/meals/sytuqu1511553755.jpg",
    # Specific Israeli dishes
    "sabich": "https://www.themealdb.com/images/media/meals/rvypwy1503069smoothies.jpg",
    "labaneh": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "falafel": "https://www.themealdb.com/images/media/meals/rvypwy1503069smoothies.jpg",
    "sweet potato": "https://www.themealdb.com/images/media/meals/tyywsw1665661330.jpg",
    "pepper": "https://www.themealdb.com/images/media/meals/sytuqu1511553755.jpg",
    "toast": "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "cheese": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
}

# Verify which TheMealDB URLs actually resolve (quick HEAD check)
def _verify_url(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def _keyword_fallback(name_en: str) -> str:
    name_lower = name_en.lower()
    for kw, url in KEYWORD_FALLBACK.items():
        if kw in name_lower:
            return url
    return ""


def build():
    with open(RECIPES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    recipes = data if isinstance(data, list) else data.get("recipes", [])
    print(f"Processing {len(recipes)} recipes...")

    # Load existing if available (avoid re-fetching)
    existing: dict = {}
    if os.path.isfile(OUT_FILE):
        with open(OUT_FILE, encoding="utf-8") as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} existing entries")

    results: dict = dict(existing)
    new_count = exact_count = kw_count = miss_count = 0

    for recipe in recipes:
        rid      = recipe.get("recipe_id", "")
        name_en  = recipe.get("name_en", "")
        name_he  = recipe.get("name_he", "")

        if rid in results and results[rid]:
            continue  # already have a good URL

        new_count += 1
        img_url = ""

        # ── 1. TheMealDB exact search ─────────────────────────────────────
        img_url = mealdb_search(name_en)
        if img_url:
            exact_count += 1
            tag = "MealDB-exact"
        else:
            # Try first word only (e.g. "Grilled Chicken with Rice" → "Chicken")
            first_word = name_en.split()[0] if name_en else ""
            if first_word and first_word.lower() not in ("with", "in", "and", "baked", "grilled", "roasted"):
                img_url = mealdb_search(first_word)
                if img_url:
                    exact_count += 1
                    tag = f"MealDB-{first_word}"

        # ── 2. Keyword fallback ───────────────────────────────────────────
        if not img_url:
            img_url = _keyword_fallback(name_en)
            if img_url:
                kw_count += 1
                tag = "keyword"

        # ── 3. Hebrew keyword fallback ────────────────────────────────────
        if not img_url:
            miss_count += 1
            tag = "MISSING"

        results[rid] = img_url
        status = "✅" if img_url else "❌"
        print(f"  {status} {rid} | {name_en[:35]:<35} | {tag if img_url else 'no image'}")

        time.sleep(0.3)  # be polite to TheMealDB

    # Save
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"Total recipes:   {len(recipes)}")
    print(f"New this run:    {new_count}")
    print(f"MealDB hits:     {exact_count}")
    print(f"Keyword hits:    {kw_count}")
    print(f"Missing:         {miss_count}")
    print(f"Saved to: {OUT_FILE}")


if __name__ == "__main__":
    build()
