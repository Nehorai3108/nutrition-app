#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill gaps in data/recipe_images.json using targeted TheMealDB searches."""

import json, os, time, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(BASE, "data", "recipe_images.json")
RECIPES = os.path.join(BASE, "storage_agents", "recipes", "recipes.json")

def mealdb(q):
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={urllib.parse.quote(q)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            meals = json.loads(r.read()).get("meals") or []
        return meals[0]["strMealThumb"] if meals else ""
    except Exception:
        return ""

# Targeted search terms for each missing recipe
TARGETED = {
    "recipe_034": "Tabbouleh",
    "recipe_050": "Lentil Rice",
    "recipe_059": "Flatbread",
    "recipe_060": "Pancakes",
    "recipe_070": "Chocolate Truffles",
    "recipe_081": "Pancakes",
    "recipe_088": "Pancakes",
    "recipe_091": "Quiche",
    "recipe_092": "Okra",
    "recipe_101": "Pancakes",
    "recipe_111": "Smoothie",
    "recipe_114": "Breakfast",
    "recipe_121": "Kebab",
    "recipe_140": "Baked Fish",
    "recipe_141": "Tilapia",
    "recipe_142": "Sea Bass",
    "recipe_147": "Jambalaya",
    "recipe_149": "Salmon Bowl",
    "recipe_150": "Lamb Rice",
    "recipe_158": "Roasted Cauliflower",
    "recipe_176": "Energy Balls",
    "recipe_177": "Protein Balls",
    "recipe_179": "Bruschetta",
    "recipe_182": "Milkshake",
    "recipe_183": "Smoothie Bowl",
    "recipe_195": "Chips",
    "recipe_196": "Smoothie",
    "recipe_202": "Cucumber Salad",
    "recipe_203": "Crackers",
    "recipe_229": "Yogurt Bowl",
    "recipe_238": "Baked Tilapia",
    "recipe_242": "Okra Stew",
    "recipe_248": "Baked Mackerel",
    "recipe_249": "Flatbread Egg",
    "recipe_250": "Fruit Bowl",
    "recipe_251": "Bean Stew",
    "recipe_260": "Banana Smoothie",
    "recipe_266": "Cholent",
}

# Curated fallbacks from TheMealDB (guaranteed to exist)
CURATED_FALLBACK = {
    "Tabbouleh":        "https://www.themealdb.com/images/media/meals/g373701551450225.jpg",   # salad
    "Flatbread":        "https://www.themealdb.com/images/media/meals/rvypwy1503069smoothies.jpg",
    "Pancakes":         "https://www.themealdb.com/images/media/meals/rwuyqx1511383174.jpg",
    "Smoothie":         "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Smoothie Bowl":    "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Baked Fish":       "https://www.themealdb.com/images/media/meals/c18desc1556736532.jpg",
    "Breakfast":        "https://www.themealdb.com/images/media/meals/wyxwsp1486979827.jpg",
    "Kebab":            "https://www.themealdb.com/images/media/meals/sytuqu1511553755.jpg",
    "Lamb Rice":        "https://www.themealdb.com/images/media/meals/sytuqu1511553755.jpg",
    "Salmon Bowl":      "https://www.themealdb.com/images/media/meals/1548772327.jpg",
    "Fruit Bowl":       "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Yogurt Bowl":      "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Bean Stew":        "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",
    "Chips":            "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "Crackers":         "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "Milkshake":        "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Banana Smoothie":  "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Energy Balls":     "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Protein Balls":    "https://www.themealdb.com/images/media/meals/1550441882.jpg",
    "Cucumber Salad":   "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "Chocolate Truffles":"https://www.themealdb.com/images/media/meals/1550441882.jpg",
}


def main():
    with open(OUT, encoding="utf-8") as f:
        images = json.load(f)
    with open(RECIPES, encoding="utf-8") as f:
        data = json.load(f)
    recipes = {r["recipe_id"]: r for r in (data if isinstance(data, list) else data.get("recipes", []))}

    missing = {rid for rid, url in images.items() if not url}
    print(f"Missing: {len(missing)}")

    for rid, search_term in TARGETED.items():
        if rid not in missing:
            continue
        # Try exact TheMealDB search first
        url = mealdb(search_term)
        if not url:
            # Fall back to curated
            url = CURATED_FALLBACK.get(search_term, "")
        if url:
            images[rid] = url
            print(f"  ✅ {rid} | {recipes.get(rid,{}).get('name_en','')[:35]:<35} | {search_term}")
        else:
            print(f"  ❌ {rid} | {recipes.get(rid,{}).get('name_en','')[:35]}")
        time.sleep(0.3)

    # Final check
    still_missing = [rid for rid, url in images.items() if not url]
    print(f"\nStill missing: {len(still_missing)}")
    if still_missing:
        # Apply generic category fallback
        generic = "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg"
        for rid in still_missing:
            images[rid] = generic
            print(f"  ⚠️  {rid} → generic fallback")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=2)

    with_img = sum(1 for v in images.values() if v)
    print(f"\nFinal: {with_img}/{len(images)} have images ✅")


if __name__ == "__main__":
    main()
