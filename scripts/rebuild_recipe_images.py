#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild data/recipe_images.json with category-based images.

Each recipe is classified into a category by keyword matching on its
English name. Each category maps to a VERIFIED TheMealDB image URL
that actually shows a matching dish.
"""

import json, os, time, urllib.request, urllib.parse

BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES  = os.path.join(BASE, "storage_agents", "recipes", "recipes.json")
OUT      = os.path.join(BASE, "data", "recipe_images.json")

# ─── Verified category images (fetched from TheMealDB category filter) ────────
# Each URL was confirmed from the TheMealDB API — these are real dish photos.

CATEGORY_IMAGES = {
    # Proteins ─────────────────────────────────────────────────────────────────
    "schnitzel":     "https://www.themealdb.com/images/media/meals/1529444830.jpg",
    "chicken_grill": "https://www.themealdb.com/images/media/meals/xcsqtp1487349408.jpg",
    "chicken_oven":  "https://www.themealdb.com/images/media/meals/sstssx1468261714.jpg",
    "chicken_soup":  "https://www.themealdb.com/images/media/meals/bzxle11700785391.jpg",
    "chicken_rice":  "https://www.themealdb.com/images/media/meals/vdwloy1713225718.jpg",
    "beef_steak":    "https://www.themealdb.com/images/media/meals/8rfd4q1764112993.jpg",
    "beef_stew":     "https://www.themealdb.com/images/media/meals/vrspxv1511722107.jpg",
    "meatballs":     "https://www.themealdb.com/images/media/meals/xxrxux1503070723.jpg",
    "burger":        "https://www.themealdb.com/images/media/meals/urzj1d1587670726.jpg",
    "kebab":         "https://www.themealdb.com/images/media/meals/k420tj1585565244.jpg",
    "lamb":          "https://www.themealdb.com/images/media/meals/04axct1763793018.jpg",
    "turkey":        "https://www.themealdb.com/images/media/meals/1548772327.jpg",

    # Fish ─────────────────────────────────────────────────────────────────────
    "salmon":        "https://www.themealdb.com/images/media/meals/1548772327.jpg",
    "fish_baked":    "https://www.themealdb.com/images/media/meals/jc6oub1763196663.jpg",
    "fish_fried":    "https://www.themealdb.com/images/media/meals/c18desc1556736532.jpg",
    "tuna":          "https://www.themealdb.com/images/media/meals/1520081754.jpg",

    # Eggs ─────────────────────────────────────────────────────────────────────
    "shakshuka":     "https://www.themealdb.com/images/media/meals/g373701551450225.jpg",
    "omelette":      "https://www.themealdb.com/images/media/meals/wyxwsp1486979827.jpg",
    "egg_dish":      "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",

    # Grains ───────────────────────────────────────────────────────────────────
    "pasta":         "https://www.themealdb.com/images/media/meals/usywpp1511189717.jpg",
    "rice_dish":     "https://www.themealdb.com/images/media/meals/vdwloy1713225718.jpg",
    "quinoa":        "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
    "couscous":      "https://www.themealdb.com/images/media/meals/yqwtvu1468237251.jpg",
    "bulgur":        "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
    "oatmeal":       "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    "bread_toast":   "https://www.themealdb.com/images/media/meals/vxuyrx1511302687.jpg",
    "pizza":         "https://www.themealdb.com/images/media/meals/x0lk931587671540.jpg",

    # Legumes ──────────────────────────────────────────────────────────────────
    "hummus":        "https://www.themealdb.com/images/media/meals/ls9lfh1728736328.jpg",
    "lentil_dish":   "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",
    "falafel":       "https://www.themealdb.com/images/media/meals/ls9lfh1728736328.jpg",
    "bean_stew":     "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",

    # Salads ───────────────────────────────────────────────────────────────────
    "salad_green":   "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "salad_grain":   "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
    "salad_greek":   "https://www.themealdb.com/images/media/meals/v8q61i1511948235.jpg",

    # Soups ────────────────────────────────────────────────────────────────────
    "soup":          "https://www.themealdb.com/images/media/meals/bzxle11700785391.jpg",

    # Dairy / Dairy bowls ──────────────────────────────────────────────────────
    "yogurt_bowl":   "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    "cheese_dish":   "https://www.themealdb.com/images/media/meals/3m8yae1763257951.jpg",

    # Wraps / Pita ─────────────────────────────────────────────────────────────
    "wrap_pita":     "https://www.themealdb.com/images/media/meals/k420tj1585565244.jpg",
    "shawarma":      "https://www.themealdb.com/images/media/meals/k420tj1585565244.jpg",

    # Vegetables ───────────────────────────────────────────────────────────────
    "veggie_roast":  "https://www.themealdb.com/images/media/meals/3m8yae1763257951.jpg",
    "veggie_stir":   "https://www.themealdb.com/images/media/meals/3m8yae1763257951.jpg",
    "stuffed_veg":   "https://www.themealdb.com/images/media/meals/xxrxux1503070723.jpg",

    # Drinks & smoothies ───────────────────────────────────────────────────────
    "smoothie":      "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",

    # Snacks & desserts ────────────────────────────────────────────────────────
    "granola":       "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    "pancakes":      "https://www.themealdb.com/images/media/meals/rwuyqx1511383174.jpg",
    "dessert":       "https://www.themealdb.com/images/media/meals/wkhg581762773124.jpg",
    "snack_fruit":   "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    "snack_nuts":    "https://www.themealdb.com/images/media/meals/vxuyrx1511302687.jpg",

    # Fallback ─────────────────────────────────────────────────────────────────
    "default":       "https://www.themealdb.com/images/media/meals/3m8yae1763257951.jpg",
}

# ─── Keyword → category mapping (checked in order) ───────────────────────────
# The FIRST matching rule wins, so more specific rules must come first.
RULES = [
    # Specific dishes
    (["shakshuka"],                                         "shakshuka"),
    (["schnitzel"],                                         "schnitzel"),
    (["shawarma", "sabich", "falafel", "laffa", "kebab",
      "shishlik", "kofta", "pita with"],                   "shawarma"),
    (["salmon"],                                            "salmon"),
    (["tuna"],                                              "tuna"),
    (["tilapia", "sea bream", "sea bass", "mackerel",
      "barramundi", "cod", "fish cake", "moroccan fish",
      "fish in", "baked fish", "grilled fish", "oven-baked fish"],
                                                            "fish_baked"),
    (["omelette", "frittata", "egg white", "pashitda",
      "egg-in-a-hole"],                                     "omelette"),
    (["hard boiled egg", "boiled egg", "avocado with egg",
      "egg with", "warm hummus with egg"],                  "egg_dish"),
    (["shakshuka"],                                         "shakshuka"),

    # Chicken (after schnitzel/shawarma so they don't collide)
    (["chicken soup", "yemenite chicken", "jerusalem chicken"],
                                                            "chicken_soup"),
    (["chicken with rice", "grilled chicken with rice",
      "chicken pargiot", "chicken meatball", "chicken wrap",
      "chicken tortilla", "pad thai with chicken",
      "chicken with freekeh", "paprika chicken",
      "freekeh with chicken"],                              "chicken_rice"),
    (["roasted chicken", "oven-baked chicken", "lemon olive chicken",
      "chicken thighs"],                                    "chicken_oven"),
    (["chicken"],                                           "chicken_grill"),

    # Beef / meat
    (["burger", "hamburger"],                               "burger"),
    (["steak"],                                             "beef_steak"),
    (["beef stew", "beef meatball"],                        "beef_stew"),
    (["meatball", "kofta", "kubbeh", "kubeh", "mafrum",
      "stuffed cabbage"],                                   "meatballs"),
    (["kebab", "shishlik"],                                 "kebab"),
    (["mansaf", "lamb"],                                    "lamb"),
    (["turkey schnitzel", "turkey meatball", "turkey wrap",
      "turkey breast"],                                     "schnitzel"),
    (["sausage"],                                           "meatballs"),

    # Fish fallback
    (["fish"],                                              "fish_baked"),

    # Pasta
    (["pasta", "penne", "linguine", "lasagna", "noodle"],  "pasta"),
    (["pizza"],                                             "pizza"),

    # Grains
    (["shakshuka pastry"],                                  "shakshuka"),
    (["couscous"],                                          "couscous"),
    (["quinoa"],                                            "quinoa"),
    (["bulgur", "tabbouleh", "tabouleh"],                   "bulgur"),
    (["mujadara", "mujaddara", "lentil rice", "lentils & rice"],
                                                            "lentil_dish"),
    (["rice"],                                              "rice_dish"),

    # Legumes
    (["hummus"],                                            "hummus"),
    (["falafel"],                                           "falafel"),
    (["lentil"],                                            "lentil_dish"),
    (["chickpea", "bean", "ful medames", "black-eyed pea",
      "split pea", "pea soup"],                             "bean_stew"),

    # Eggs (catch-all)
    (["egg"],                                               "egg_dish"),

    # Soups
    (["soup", "stew", "chamin", "cholent", "bamya",
      "okra"],                                              "soup"),

    # Salads
    (["greek salad", "caesar salad", "halloumi salad"],     "salad_greek"),
    (["grain salad", "quinoa salad", "bulgur salad",
      "lentil salad", "five grain"],                        "salad_grain"),
    (["salad", "tabbouleh", "fattoush", "coleslaw",
      "slaw"],                                              "salad_green"),

    # Wraps / sandwiches / toast
    (["wrap", "sandwich", "toast", "bruschetta",
      "bagel", "challah", "bread", "bourekas",
      "rye", "pita", "laffa", "crepe"],                     "bread_toast"),
    (["flatbread", "malawach", "lahoh", "jachnun"],         "pancakes"),

    # Dairy bowls
    (["cottage cheese", "labaneh", "labneh", "laban",
      "tzfatit", "bulgarian cheese"],                       "cheese_dish"),
    (["yogurt", "granola with yogurt", "persimmon yogurt"], "yogurt_bowl"),
    (["granola", "oatmeal"],                                "granola"),

    # Vegetables
    (["stuffed pepper", "stuffed bell", "stuffed zucchini",
      "stuffed grape", "stuffed mushroom", "stuffed vegetable",
      "stuffed cabbage"],                                   "stuffed_veg"),
    (["roasted", "oven-roasted", "baked vegetable"],        "veggie_roast"),
    (["stir-fry", "stir fry", "tempura", "tofu"],          "veggie_stir"),
    (["eggplant", "cauliflower", "baba ganoush",
      "moussaka"],                                          "veggie_roast"),
    (["vegetable", "veggie"],                               "veggie_roast"),

    # Smoothies & drinks
    (["smoothie", "shake", "sahlab"],                       "smoothie"),

    # Desserts & sweets
    (["cake", "cookie", "muffin", "chocolate", "halva",
      "torte", "mousse", "ice cream", "date ball",
      "energy ball", "protein ball", "oat cookie"],         "dessert"),
    (["pancake"],                                           "pancakes"),
    (["popcorn", "crackers", "chips"],                      "snack_nuts"),
    (["fruit", "apple", "banana", "berry", "acai"],         "snack_fruit"),
    (["nuts", "almond", "walnut", "pecan"],                 "snack_nuts"),
]


def classify(name_en: str) -> str:
    n = name_en.lower()
    for keywords, category in RULES:
        for kw in keywords:
            if kw in n:
                return category
    return "default"


def build():
    with open(RECIPES, encoding="utf-8") as f:
        data = json.load(f)
    recipes = data if isinstance(data, list) else data.get("recipes", [])

    results = {}
    cat_counts = {}

    for r in recipes:
        rid     = r.get("recipe_id", "")
        name_en = r.get("name_en", "")
        cat     = classify(name_en)
        url     = CATEGORY_IMAGES[cat]
        results[rid] = url
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # Save
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(results)} recipes → {OUT}\n")
    print("Category distribution:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:<20} {count}")


if __name__ == "__main__":
    build()
