#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed common Israeli dishes into the food catalog (source='ai').

Runs the same Groq nutrition estimator used by the manual-search fallback over
a curated list of staple Hebrew dish names, so they resolve instantly (no API
round-trip) when users search them. Idempotent — re-running upserts.

Usage:  python scripts/seed_israeli_foods.py
"""
import os
import sys
import hashlib

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.nutrition_ai import estimate_nutrition_per_100g
from db.database import NutritionDB

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

# Common Israeli / Middle-Eastern staples that the curated Hebrew catalog
# tends to miss or only partially covers.
DISHES = [
    "סביח", "שווארמה עוף", "שווארמה הודו", "פלאפל", "חומוס מנה", "מסבחה",
    "שקשוקה", "מג'דרה", "מלאווח", "ג'חנון", "קובה סלק", "בורקס גבינה",
    "בורקס תפוחי אדמה", "סמבוסק", "פתיתים", "קוסקוס עם ירקות", "מרק עוף",
    "מרק עדשים", "שניצל עוף", "פרגית בגריל", "כבד עוף", "חמין", "מטבוחה",
    "חציל בטחינה", "לאפה", "פיתה פלאפל", "פיתה שווארמה", "סלט ישראלי",
    "אורז עם שעועית", "מאפה גבינה",
]


def main():
    db = NutritionDB(_DB_PATH)
    added = failed = 0
    for name in DISHES:
        est = estimate_nutrition_per_100g(name)
        if not est:
            print(f"  [x] {name} - estimation failed")
            failed += 1
            continue
        food_id = "ai_" + hashlib.md5(name.strip().encode("utf-8")).hexdigest()[:12]
        db.upsert_food({
            "food_id": food_id,
            "name_he": est["name_he"],
            "name_en": est["name_en"] or est["name_he"],
            "category": est["category"],
            "calories_kcal": est["calories"],
            "protein_g": est["protein"],
            "carbs_g": est["carbs"],
            "fat_g": est["fat"],
            "source": "ai",
            "is_custom": 1,
        })
        print(f"  [v] {name}: {est['calories']} kcal/100g  (P{est['protein']} C{est['carbs']} F{est['fat']})")
        added += 1
    print(f"\nDone. seeded={added}  failed={failed}")


if __name__ == "__main__":
    main()
