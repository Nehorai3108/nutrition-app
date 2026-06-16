#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Offline: resolve an accurate Wikipedia image (exact-title only) for every recipe
that lacks a local approved JPG and a curated Unsplash entry, and write the
results to data/recipe_wiki_images.json. The API then reads that map as a plain
dict lookup — no per-request network calls (keeps meal endpoints fast).

Usage:  python scripts/resolve_recipe_images.py
"""
import os
import sys
import json

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from api.food_image import get_food_image

_RECIPES = os.path.join(_ROOT, "storage_agents", "recipes", "recipes.json")
_IMAGES_DIR = os.path.join(_ROOT, "storage_agents", "recipe_images", "approved")
_UNSPLASH = os.path.join(_ROOT, "data", "recipe_images.json")
_OUT = os.path.join(_ROOT, "data", "recipe_wiki_images.json")


def main():
    with open(_RECIPES, encoding="utf-8") as f:
        recipes = json.load(f)
    try:
        with open(_UNSPLASH, encoding="utf-8") as f:
            unsplash = json.load(f)
    except Exception:
        unsplash = {}
    try:
        with open(_OUT, encoding="utf-8") as f:
            out = json.load(f)
    except Exception:
        out = {}

    resolved = skipped = missed = 0
    for r in recipes:
        rid = r.get("recipe_id", "")
        if not rid or rid in out:
            continue
        # Already covered by a local JPG or curated Unsplash entry?
        if os.path.exists(os.path.join(_IMAGES_DIR, f"{rid}.jpg")):
            continue
        if "images.unsplash.com" in (unsplash.get(rid) or ""):
            continue

        img = get_food_image(r.get("name_en", ""), r.get("name_he", ""), allow_search=False)
        if img:
            out[rid] = img
            resolved += 1
            print(f"  [v] {r.get('name_he')} -> ok")
        else:
            missed += 1

    os.makedirs(os.path.dirname(_OUT), exist_ok=True)
    with open(_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nDone. resolved={resolved}  no-image={missed}  total_map={len(out)}")


if __name__ == "__main__":
    main()
