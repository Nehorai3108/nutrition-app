#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tag_recipes_for_picker.py — add 'post_workout' and 'treat' tags to existing
recipes so the first-login meal picker can surface candidates for those
categories. Idempotent: re-running is safe.

Usage:
    python scripts/tag_recipes_for_picker.py
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RECIPES = os.path.join(_ROOT, "storage_agents", "recipes", "recipes.json")


# High-protein, quick, non-meat — surfaces for post-workout suggestions.
POST_WORKOUT_IDS = {
    "recipe_028",  # Cottage Cheese with Veggies
    "recipe_030",  # Yogurt with Nuts
    "recipe_074",  # Banana Peanut Butter Shake
    "recipe_088",  # Protein Pancakes
    "recipe_103",  # Egg White Omelette
    "recipe_111",  # Protein Smoothie
    "recipe_182",  # Protein Milkshake
    "recipe_196",  # Night Shake
    "recipe_197",  # Cottage Cheese with Vegetables
    "recipe_198",  # Yogurt with Nuts (duplicate set)
    "recipe_210",  # Protein Toast
    "recipe_211",  # Cheese Omelette with Vegetables
    "recipe_215",  # Banana Oat Shake
    "recipe_253",  # Soy Milk Banana Smoothie
}

# Sweet / dessert / snack — surfaces for treat suggestions.
TREAT_IDS = {
    "recipe_067",  # Oat Cookies
    "recipe_070",  # Healthy Chocolate Balls
    "recipe_086",  # Apple Cake
    "recipe_093",  # Chocolate Torte
    "recipe_099",  # Chocolate Oat Energy Bites
    "recipe_184",  # Banana Ice Cream
    "recipe_185",  # Chocolate Muffins
    "recipe_186",  # Oatmeal Cookies
    "recipe_187",  # Date Balls
    "recipe_189",  # Sweet Crepe
    "recipe_190",  # Chocolate Mousse
    "recipe_191",  # Tahini Cookie
    "recipe_229",  # Laban Bowl with Pistachios and Silan
    "recipe_230",  # Hot Sahlab with Pistachios and Cinnamon
    "recipe_235",  # Persimmon Yogurt Bowl with Honey
}


def _ensure_tag(recipe: dict, tag: str) -> bool:
    tags = recipe.setdefault("tags", [])
    if tag in tags:
        return False
    tags.append(tag)
    return True


def main() -> int:
    if not os.path.isfile(_RECIPES):
        print(f"recipes.json not found at {_RECIPES}", file=sys.stderr)
        return 1

    with open(_RECIPES, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    by_id = {r["recipe_id"]: r for r in recipes if "recipe_id" in r}
    pw_added = sum(1 for rid in POST_WORKOUT_IDS if rid in by_id and _ensure_tag(by_id[rid], "post_workout"))
    tr_added = sum(1 for rid in TREAT_IDS if rid in by_id and _ensure_tag(by_id[rid], "treat"))

    # Surface IDs that were requested but missing from the file (data drift).
    missing_pw = [rid for rid in POST_WORKOUT_IDS if rid not in by_id]
    missing_tr = [rid for rid in TREAT_IDS if rid not in by_id]

    with open(_RECIPES, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"Tagged {pw_added} new post_workout recipes (target set: {len(POST_WORKOUT_IDS)})")
    print(f"Tagged {tr_added} new treat recipes (target set: {len(TREAT_IDS)})")
    if missing_pw:
        print(f"  WARN: post_workout IDs not present in recipes.json: {missing_pw}")
    if missing_tr:
        print(f"  WARN: treat IDs not present in recipes.json: {missing_tr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
