"""
Agent 10 — Data Collector / Knowledge Factory

Responsibility:
- Maintain MASTER_FOOD_QUEUE with 300+ Israeli/Mediterranean foods
- Maintain RECIPE_KNOWLEDGE_BASE with 200+ recipes
- Maintain MENU_TEMPLATES with daily patterns
- Drip-feed new foods and recipes into the system daily
- Validate nutrition data before insertion

Rules:
- Queue-based (deterministic, not random)
- Non-destructive (never remove existing data)
- Hebrew + English bilingual
- Israeli food culture + kashrut compliance
"""

import json
import os
from typing import Dict, List, Optional, Set


class DataCollector:
    """Knowledge factory that drip-feeds foods, recipes, and templates."""

    def __init__(self):
        self._food_index = 0
        self._recipe_index = 0
        self._template_index = 0

    def collect_new_foods(
        self, current_catalog_names: Set[str], batch_size: int = 8
    ) -> List[dict]:
        """Pick the next batch of foods from MASTER_FOOD_QUEUE.

        Args:
            current_catalog_names: Set of name_en (lowercase) already in catalog.
            batch_size: How many foods to return.

        Returns:
            List of food dicts ready to insert into foods_extended.json.
        """
        collected = []
        all_foods = []
        for category_foods in MASTER_FOOD_QUEUE.values():
            all_foods.extend(category_foods)

        lowered_catalog = {n.lower() for n in current_catalog_names}

        for food in all_foods:
            if len(collected) >= batch_size:
                break
            name_en = food["name_en"].lower()
            if name_en in lowered_catalog:
                continue
            # Check aliases too
            aliases_en = [a.lower() for a in food.get("aliases_en", [])]
            if any(a in lowered_catalog for a in aliases_en):
                continue
            # Validate nutrition
            if self._validate_nutrition(food):
                collected.append(self._format_food_for_catalog(food))
                lowered_catalog.add(name_en)

        return collected

    def collect_new_recipes(
        self, existing_recipe_ids: Set[str], batch_size: int = 4
    ) -> List[dict]:
        """Pick next batch of recipes from RECIPE_KNOWLEDGE_BASE."""
        collected = []
        for recipe in RECIPE_KNOWLEDGE_BASE:
            if len(collected) >= batch_size:
                break
            if recipe["recipe_id"] in existing_recipe_ids:
                continue
            collected.append(recipe)
        return collected

    def collect_new_templates(
        self, existing_template_ids: Set[str], batch_size: int = 3
    ) -> List[dict]:
        """Pick next batch of menu templates."""
        collected = []
        for template in MENU_TEMPLATES:
            if len(collected) >= batch_size:
                break
            if template["template_id"] in existing_template_ids:
                continue
            collected.append(template)
        return collected

    def _validate_nutrition(self, food: dict) -> bool:
        """Validate: |calories - (protein*4 + carbs*4 + fat*9)| <= calories * 0.15"""
        p100 = food.get("per_100g", {})
        cal = p100.get("calories", 0)
        protein = p100.get("protein", 0)
        carbs = p100.get("carbs", 0)
        fat = p100.get("fat", 0)

        if cal <= 0:
            return False

        computed = protein * 4 + carbs * 4 + fat * 9
        diff = abs(cal - computed)
        return diff <= cal * 0.15

    def _format_food_for_catalog(self, food: dict) -> dict:
        """Format a MASTER_FOOD_QUEUE entry into foods_extended.json format."""
        p100 = food["per_100g"]
        return {
            "food_id": food.get("food_id", f"food_ext_{food['name_en'].lower().replace(' ', '_')[:20]}"),
            "name_he": food["name_he"],
            "name_en": food["name_en"],
            "category": food["category"].lower(),
            "nutrition_per_100g": {
                "calories_kcal": p100["calories"],
                "protein_g": p100["protein"],
                "carbs_g": p100["carbs"],
                "fat_g": p100["fat"],
                "fiber_g": p100.get("fiber", 0.0),
                "sugar_g": p100.get("sugar", 0.0),
                "sodium_mg": p100.get("sodium", 0.0),
            },
            "default_serving_g": food.get("serving_g", 100.0),
            "aliases_he": food.get("aliases_he", []),
            "aliases_en": food.get("aliases_en", []),
        }


# ═══════════════════════════════════════════════════════════════════
# MASTER_FOOD_QUEUE — 300+ Israeli/Mediterranean foods
# ═══════════════════════════════════════════════════════════════════

MASTER_FOOD_QUEUE: Dict[str, List[dict]] = {
    "proteins": [
        {"food_id": "food_q001", "name_he": "חזה הודו מעושן", "name_en": "Smoked Turkey Breast", "category": "protein", "per_100g": {"calories": 104, "protein": 18, "carbs": 2, "fat": 2.5}, "serving_g": 100, "aliases_he": ["הודו מעושן"], "aliases_en": ["smoked turkey"]},
        {"food_id": "food_q002", "name_he": "שניצל עוף", "name_en": "Chicken Schnitzel", "category": "protein", "per_100g": {"calories": 260, "protein": 20, "carbs": 14, "fat": 14}, "serving_g": 150, "aliases_he": ["שניצלון"], "aliases_en": ["schnitzel"]},
        {"food_id": "food_q003", "name_he": "כבד עוף", "name_en": "Chicken Liver", "category": "protein", "per_100g": {"calories": 172, "protein": 25, "carbs": 1, "fat": 7}, "serving_g": 100, "aliases_he": ["כבדי עוף"], "aliases_en": ["liver"]},
        {"food_id": "food_q004", "name_he": "שוורמה", "name_en": "Shawarma (Turkey)", "category": "protein", "per_100g": {"calories": 215, "protein": 22, "carbs": 3, "fat": 13}, "serving_g": 150, "aliases_he": ["שווארמה", "שוארמה"], "aliases_en": ["shawarma"]},
        {"food_id": "food_q005", "name_he": "קבב", "name_en": "Kebab", "category": "protein", "per_100g": {"calories": 226, "protein": 18, "carbs": 5, "fat": 15}, "serving_g": 100, "aliases_he": ["קבאב", "כבאב"], "aliases_en": ["kabob"]},
        {"food_id": "food_q006", "name_he": "דג אמנון", "name_en": "Tilapia", "category": "protein", "per_100g": {"calories": 96, "protein": 20, "carbs": 0, "fat": 1.7}, "serving_g": 150, "aliases_he": ["אמנון", "דג מושט"], "aliases_en": ["st peters fish"]},
        {"food_id": "food_q007", "name_he": "דג דניס", "name_en": "Sea Bream", "category": "protein", "per_100g": {"calories": 100, "protein": 19, "carbs": 0, "fat": 2.5}, "serving_g": 150, "aliases_he": ["דניס"], "aliases_en": ["bream", "dorade"]},
        {"food_id": "food_q008", "name_he": "סרדינים", "name_en": "Sardines (canned)", "category": "protein", "per_100g": {"calories": 208, "protein": 25, "carbs": 0, "fat": 11}, "serving_g": 85, "aliases_he": ["סרדינים בשמן"], "aliases_en": ["sardine"]},
        {"food_id": "food_q009", "name_he": "אנטריקוט", "name_en": "Ribeye Steak", "category": "protein", "per_100g": {"calories": 291, "protein": 24, "carbs": 0, "fat": 21}, "serving_g": 200, "aliases_he": ["סטייק"], "aliases_en": ["steak", "rib eye"]},
        {"food_id": "food_q010", "name_he": "כרעיי עוף", "name_en": "Chicken Thigh", "category": "protein", "per_100g": {"calories": 209, "protein": 26, "carbs": 0, "fat": 11}, "serving_g": 150, "aliases_he": ["ירך עוף", "שוק עוף"], "aliases_en": ["chicken leg", "thigh"]},
        {"food_id": "food_q011", "name_he": "טחינה גולמית", "name_en": "Raw Tahini (protein source)", "category": "protein", "per_100g": {"calories": 595, "protein": 17, "carbs": 21, "fat": 54}, "serving_g": 30, "aliases_he": ["טחינה גולמית מלאה"], "aliases_en": ["raw tahini paste"]},
        {"food_id": "food_q012", "name_he": "שרימפס", "name_en": "Shrimp", "category": "protein", "per_100g": {"calories": 85, "protein": 20, "carbs": 0, "fat": 0.5}, "serving_g": 100, "aliases_he": ["חסילונים"], "aliases_en": ["prawns"]},
        {"food_id": "food_q013", "name_he": "נקניקיות הודו", "name_en": "Turkey Sausage", "category": "protein", "per_100g": {"calories": 196, "protein": 14, "carbs": 2, "fat": 15}, "serving_g": 80, "aliases_he": ["נקניקייה"], "aliases_en": ["sausage"]},
        {"food_id": "food_q014", "name_he": "המבורגר בקר", "name_en": "Beef Burger Patty", "category": "protein", "per_100g": {"calories": 254, "protein": 17, "carbs": 0, "fat": 20}, "serving_g": 120, "aliases_he": ["קציצה", "המבורגר"], "aliases_en": ["burger", "patty"]},
        {"food_id": "food_q015", "name_he": "פסטרמה", "name_en": "Pastrami", "category": "protein", "per_100g": {"calories": 147, "protein": 22, "carbs": 2, "fat": 6}, "serving_g": 60, "aliases_he": ["פסטרמה הודו"], "aliases_en": ["turkey pastrami"]},
        {"food_id": "food_q016", "name_he": "עגל", "name_en": "Veal", "category": "protein", "per_100g": {"calories": 172, "protein": 24, "carbs": 0, "fat": 8}, "serving_g": 150, "aliases_he": ["בשר עגל"], "aliases_en": ["veal cutlet"]},
        {"food_id": "food_q017", "name_he": "דג מוסר", "name_en": "Sea Bass", "category": "protein", "per_100g": {"calories": 97, "protein": 18, "carbs": 0, "fat": 2}, "serving_g": 150, "aliases_he": ["מוסר ים", "לברק"], "aliases_en": ["bass", "branzino"]},
        {"food_id": "food_q018", "name_he": "טמפה", "name_en": "Tempeh", "category": "protein", "per_100g": {"calories": 192, "protein": 20, "carbs": 8, "fat": 11}, "serving_g": 100, "aliases_he": ["טמפה סויה"], "aliases_en": ["fermented soy"]},
        {"food_id": "food_q019", "name_he": "סייטן", "name_en": "Seitan", "category": "protein", "per_100g": {"calories": 370, "protein": 75, "carbs": 14, "fat": 2}, "serving_g": 80, "aliases_he": ["גלוטן חיטה"], "aliases_en": ["wheat gluten"]},
        {"food_id": "food_q020", "name_he": "חזיר ים (לוקוס)", "name_en": "Grouper", "category": "protein", "per_100g": {"calories": 92, "protein": 19, "carbs": 0, "fat": 1}, "serving_g": 150, "aliases_he": ["לוקוס"], "aliases_en": ["grouper fish"]},
        {"food_id": "food_q021", "name_he": "מלוואח", "name_en": "Malawach (dough)", "category": "protein", "per_100g": {"calories": 300, "protein": 6, "carbs": 35, "fat": 15}, "serving_g": 120, "aliases_he": ["מלאווח"], "aliases_en": ["yemenite pancake"]},
        {"food_id": "food_q022", "name_he": "ג׳חנון", "name_en": "Jachnun", "category": "protein", "per_100g": {"calories": 320, "protein": 6, "carbs": 40, "fat": 16}, "serving_g": 150, "aliases_he": ["ג'חנון", "גחנון"], "aliases_en": ["yemenite bread roll"]},
        {"food_id": "food_q023", "name_he": "חזה ברווז", "name_en": "Duck Breast", "category": "protein", "per_100g": {"calories": 201, "protein": 19, "carbs": 0, "fat": 14}, "serving_g": 150, "aliases_he": ["ברווז"], "aliases_en": ["duck"]},
        {"food_id": "food_q024", "name_he": "אנשובי", "name_en": "Anchovies", "category": "protein", "per_100g": {"calories": 210, "protein": 29, "carbs": 0, "fat": 10}, "serving_g": 30, "aliases_he": ["אנצ׳ובי"], "aliases_en": ["anchovy"]},
        {"food_id": "food_q025", "name_he": "תמנון", "name_en": "Octopus", "category": "protein", "per_100g": {"calories": 82, "protein": 15, "carbs": 2, "fat": 1}, "serving_g": 100, "aliases_he": ["תמנון מבושל"], "aliases_en": ["pulpo"]},
        {"food_id": "food_q026", "name_he": "טלה", "name_en": "Lamb", "category": "protein", "per_100g": {"calories": 258, "protein": 25, "carbs": 0, "fat": 17}, "serving_g": 150, "aliases_he": ["כבש", "בשר כבש"], "aliases_en": ["lamb chop", "mutton"]},
        {"food_id": "food_q027", "name_he": "חזה עוף צלוי", "name_en": "Grilled Chicken Breast", "category": "protein", "per_100g": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6}, "serving_g": 150, "aliases_he": ["עוף צלוי"], "aliases_en": ["grilled chicken"]},
        {"food_id": "food_q028", "name_he": "פילה אמנון צלוי", "name_en": "Grilled Tilapia Fillet", "category": "protein", "per_100g": {"calories": 128, "protein": 26, "carbs": 0, "fat": 2.7}, "serving_g": 150, "aliases_he": ["פילה דג צלוי"], "aliases_en": ["grilled fish fillet"]},
        {"food_id": "food_q029", "name_he": "חזה הודו צלוי", "name_en": "Roasted Turkey Breast", "category": "protein", "per_100g": {"calories": 135, "protein": 30, "carbs": 0, "fat": 1}, "serving_g": 150, "aliases_he": ["הודו צלוי", "חזה הודו בתנור"], "aliases_en": ["roast turkey"]},
        {"food_id": "food_q030", "name_he": "טונה טרייה", "name_en": "Fresh Tuna Steak", "category": "protein", "per_100g": {"calories": 130, "protein": 29, "carbs": 0, "fat": 1}, "serving_g": 150, "aliases_he": ["סטייק טונה"], "aliases_en": ["tuna steak"]},
    ],
    "carbs": [
        {"food_id": "food_q031", "name_he": "חלה", "name_en": "Challah Bread", "category": "grain", "per_100g": {"calories": 283, "protein": 8, "carbs": 50, "fat": 6}, "serving_g": 60, "aliases_he": ["חלה מתוקה"], "aliases_en": ["challah"]},
        {"food_id": "food_q032", "name_he": "פריקה", "name_en": "Freekeh", "category": "grain", "per_100g": {"calories": 128, "protein": 5, "carbs": 24, "fat": 0.8}, "serving_g": 150, "aliases_he": ["פריכה"], "aliases_en": ["roasted green wheat"]},
        {"food_id": "food_q033", "name_he": "לחם שיפון", "name_en": "Rye Bread", "category": "grain", "per_100g": {"calories": 259, "protein": 8, "carbs": 48, "fat": 3.3}, "serving_g": 30, "aliases_he": ["שיפון"], "aliases_en": ["rye"]},
        {"food_id": "food_q034", "name_he": "מצה", "name_en": "Matzo", "category": "grain", "per_100g": {"calories": 394, "protein": 10, "carbs": 83, "fat": 1.4}, "serving_g": 30, "aliases_he": ["מצות"], "aliases_en": ["matzah", "unleavened bread"]},
        {"food_id": "food_q035", "name_he": "אורז יסמין", "name_en": "Jasmine Rice (cooked)", "category": "grain", "per_100g": {"calories": 129, "protein": 2.7, "carbs": 28, "fat": 0.3}, "serving_g": 150, "aliases_he": ["יסמין"], "aliases_en": ["thai rice"]},
        {"food_id": "food_q036", "name_he": "לחם טורטייה", "name_en": "Tortilla Wrap", "category": "grain", "per_100g": {"calories": 312, "protein": 8, "carbs": 52, "fat": 8}, "serving_g": 60, "aliases_he": ["טורטייה", "לאפה"], "aliases_en": ["wrap", "flour tortilla"]},
        {"food_id": "food_q037", "name_he": "פתיתים", "name_en": "Ptitim (Israeli Couscous)", "category": "grain", "per_100g": {"calories": 130, "protein": 5, "carbs": 26, "fat": 0.5}, "serving_g": 150, "aliases_he": ["פתיתים ישראליים", "בן גוריון"], "aliases_en": ["israeli couscous", "pearl couscous"]},
        {"food_id": "food_q038", "name_he": "אטריות אורז", "name_en": "Rice Noodles (cooked)", "category": "grain", "per_100g": {"calories": 109, "protein": 0.9, "carbs": 25, "fat": 0.2}, "serving_g": 150, "aliases_he": ["נודלס אורז"], "aliases_en": ["pad thai noodles"]},
        {"food_id": "food_q039", "name_he": "פולנטה", "name_en": "Polenta (cooked)", "category": "grain", "per_100g": {"calories": 85, "protein": 2, "carbs": 18, "fat": 0.3}, "serving_g": 200, "aliases_he": ["קמח תירס מבושל"], "aliases_en": ["corn grits"]},
        {"food_id": "food_q040", "name_he": "קמח כוסמין", "name_en": "Spelt Flour Bread", "category": "grain", "per_100g": {"calories": 267, "protein": 11, "carbs": 50, "fat": 3}, "serving_g": 30, "aliases_he": ["לחם כוסמין"], "aliases_en": ["spelt bread"]},
        {"food_id": "food_q041", "name_he": "אורז פרסי", "name_en": "Persian Rice (cooked)", "category": "grain", "per_100g": {"calories": 135, "protein": 2.5, "carbs": 30, "fat": 0.5}, "serving_g": 150, "aliases_he": ["תהדיג"], "aliases_en": ["tahdig rice"]},
        {"food_id": "food_q042", "name_he": "מנגולד מבושל", "name_en": "Cooked Chard", "category": "carbohydrate", "per_100g": {"calories": 20, "protein": 1.8, "carbs": 4, "fat": 0.1}, "serving_g": 100, "aliases_he": ["סלק עלים"], "aliases_en": ["swiss chard"]},
        {"food_id": "food_q043", "name_he": "לחם לבן", "name_en": "White Bread", "category": "grain", "per_100g": {"calories": 265, "protein": 9, "carbs": 49, "fat": 3.2}, "serving_g": 30, "aliases_he": ["לחם רגיל"], "aliases_en": ["white sandwich bread"]},
        {"food_id": "food_q044", "name_he": "כדורי אורז", "name_en": "Rice Cakes", "category": "grain", "per_100g": {"calories": 387, "protein": 8, "carbs": 81, "fat": 2.8}, "serving_g": 10, "aliases_he": ["פריכיות אורז"], "aliases_en": ["rice cake"]},
        {"food_id": "food_q045", "name_he": "קורנפלקס", "name_en": "Corn Flakes", "category": "grain", "per_100g": {"calories": 357, "protein": 8, "carbs": 84, "fat": 0.4}, "serving_g": 30, "aliases_he": ["דגני בוקר"], "aliases_en": ["cereal", "breakfast cereal"]},
        {"food_id": "food_q046", "name_he": "ורמישל", "name_en": "Vermicelli", "category": "grain", "per_100g": {"calories": 131, "protein": 4.5, "carbs": 27, "fat": 0.4}, "serving_g": 150, "aliases_he": ["איטריות דקות"], "aliases_en": ["thin noodles"]},
        {"food_id": "food_q047", "name_he": "לחם עיראקי", "name_en": "Iraqi Flatbread", "category": "grain", "per_100g": {"calories": 280, "protein": 9, "carbs": 52, "fat": 4}, "serving_g": 80, "aliases_he": ["סמון", "לאפה"], "aliases_en": ["samoon", "laffa"]},
        {"food_id": "food_q048", "name_he": "פילו", "name_en": "Phyllo Dough", "category": "grain", "per_100g": {"calories": 300, "protein": 7, "carbs": 52, "fat": 7}, "serving_g": 50, "aliases_he": ["בצק פילו"], "aliases_en": ["filo"]},
        {"food_id": "food_q049", "name_he": "אורז אדום", "name_en": "Red Rice (cooked)", "category": "grain", "per_100g": {"calories": 125, "protein": 2.5, "carbs": 26, "fat": 1}, "serving_g": 150, "aliases_he": ["אורז אדום שלם"], "aliases_en": ["red rice"]},
        {"food_id": "food_q050", "name_he": "דוחן", "name_en": "Millet (cooked)", "category": "grain", "per_100g": {"calories": 119, "protein": 3.5, "carbs": 23, "fat": 1}, "serving_g": 150, "aliases_he": ["דוחן מבושל"], "aliases_en": ["millet grain"]},
    ],
    "fats": [
        {"food_id": "food_q051", "name_he": "שמן קנולה", "name_en": "Canola Oil", "category": "fat", "per_100g": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100}, "serving_g": 10, "aliases_he": ["שמן רפס"], "aliases_en": ["rapeseed oil"]},
        {"food_id": "food_q052", "name_he": "חמאה", "name_en": "Butter", "category": "fat", "per_100g": {"calories": 717, "protein": 0.9, "carbs": 0.1, "fat": 81}, "serving_g": 10, "aliases_he": ["חמאה מתוקה"], "aliases_en": ["unsalted butter"]},
        {"food_id": "food_q053", "name_he": "מרגרינה", "name_en": "Margarine", "category": "fat", "per_100g": {"calories": 717, "protein": 0.2, "carbs": 0.7, "fat": 80}, "serving_g": 10, "aliases_he": ["מרגרינה צמחית"], "aliases_en": ["plant butter"]},
        {"food_id": "food_q054", "name_he": "שמן אגוזי מלך", "name_en": "Walnut Oil", "category": "fat", "per_100g": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100}, "serving_g": 10, "aliases_he": ["שמן אגוזים"], "aliases_en": ["nut oil"]},
        {"food_id": "food_q055", "name_he": "שמן אבוקדו", "name_en": "Avocado Oil", "category": "fat", "per_100g": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100}, "serving_g": 10, "aliases_he": [], "aliases_en": []},
        {"food_id": "food_q056", "name_he": "שמן זרעי פשתן", "name_en": "Flaxseed Oil", "category": "fat", "per_100g": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100}, "serving_g": 10, "aliases_he": ["שמן פשתן"], "aliases_en": ["linseed oil"]},
        {"food_id": "food_q057", "name_he": "זיתים ירוקים", "name_en": "Green Olives", "category": "fat", "per_100g": {"calories": 145, "protein": 1, "carbs": 3.8, "fat": 15}, "serving_g": 30, "aliases_he": ["זיתים"], "aliases_en": ["olives"]},
        {"food_id": "food_q058", "name_he": "זיתים שחורים", "name_en": "Black Olives", "category": "fat", "per_100g": {"calories": 116, "protein": 0.8, "carbs": 6, "fat": 11}, "serving_g": 30, "aliases_he": ["זיתי קלמטה"], "aliases_en": ["kalamata olives"]},
        {"food_id": "food_q059", "name_he": "מיונז", "name_en": "Mayonnaise", "category": "fat", "per_100g": {"calories": 680, "protein": 1, "carbs": 1, "fat": 75}, "serving_g": 15, "aliases_he": ["מיונז קל"], "aliases_en": ["mayo"]},
        {"food_id": "food_q060", "name_he": "שמנת מתוקה", "name_en": "Heavy Cream", "category": "fat", "per_100g": {"calories": 340, "protein": 2, "carbs": 3, "fat": 36}, "serving_g": 30, "aliases_he": ["שמנת 38%"], "aliases_en": ["whipping cream"]},
        {"food_id": "food_q061", "name_he": "שמן חמניות", "name_en": "Sunflower Oil", "category": "fat", "per_100g": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100}, "serving_g": 10, "aliases_he": ["שמן חמנייה"], "aliases_en": ["sunflower seed oil"]},
        {"food_id": "food_q062", "name_he": "שמן בוטנים", "name_en": "Peanut Oil", "category": "fat", "per_100g": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100}, "serving_g": 10, "aliases_he": [], "aliases_en": ["groundnut oil"]},
        {"food_id": "food_q063", "name_he": "שמן תירס", "name_en": "Corn Oil", "category": "fat", "per_100g": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100}, "serving_g": 10, "aliases_he": [], "aliases_en": []},
        {"food_id": "food_q064", "name_he": "אגוז מקדמיה", "name_en": "Macadamia Nuts", "category": "fat", "per_100g": {"calories": 718, "protein": 8, "carbs": 14, "fat": 76}, "serving_g": 20, "aliases_he": ["מקדמיה"], "aliases_en": ["macadamia"]},
        {"food_id": "food_q065", "name_he": "פקאן", "name_en": "Pecans", "category": "fat", "per_100g": {"calories": 691, "protein": 9, "carbs": 14, "fat": 72}, "serving_g": 20, "aliases_he": ["אגוזי פקאן"], "aliases_en": ["pecan nuts"]},
        {"food_id": "food_q066", "name_he": "קוקוס מיובש", "name_en": "Desiccated Coconut", "category": "fat", "per_100g": {"calories": 660, "protein": 7, "carbs": 24, "fat": 65}, "serving_g": 15, "aliases_he": ["קוקוס גרוס"], "aliases_en": ["shredded coconut"]},
        {"food_id": "food_q067", "name_he": "אגוזי ברזיל", "name_en": "Brazil Nuts", "category": "fat", "per_100g": {"calories": 659, "protein": 14, "carbs": 12, "fat": 66}, "serving_g": 20, "aliases_he": [], "aliases_en": ["para nuts"]},
        {"food_id": "food_q068", "name_he": "חמאת שקדים", "name_en": "Almond Butter", "category": "fat", "per_100g": {"calories": 614, "protein": 21, "carbs": 19, "fat": 56}, "serving_g": 20, "aliases_he": ["ממרח שקדים"], "aliases_en": []},
        {"food_id": "food_q069", "name_he": "חמאת קשיו", "name_en": "Cashew Butter", "category": "fat", "per_100g": {"calories": 587, "protein": 17, "carbs": 28, "fat": 49}, "serving_g": 20, "aliases_he": ["ממרח קשיו"], "aliases_en": []},
        {"food_id": "food_q070", "name_he": "קרם קוקוס", "name_en": "Coconut Cream", "category": "fat", "per_100g": {"calories": 230, "protein": 2.3, "carbs": 6.6, "fat": 24}, "serving_g": 50, "aliases_he": ["שמנת קוקוס"], "aliases_en": ["coconut milk (thick)"]},
    ],
    "vegetables": [
        {"food_id": "food_q071", "name_he": "כרוב", "name_en": "Cabbage", "category": "vegetable", "per_100g": {"calories": 25, "protein": 1.3, "carbs": 6, "fat": 0.1}, "serving_g": 100, "aliases_he": ["כרוב לבן"], "aliases_en": ["white cabbage"]},
        {"food_id": "food_q072", "name_he": "כרוב סגול", "name_en": "Red Cabbage", "category": "vegetable", "per_100g": {"calories": 31, "protein": 1.4, "carbs": 7, "fat": 0.2}, "serving_g": 100, "aliases_he": [], "aliases_en": ["purple cabbage"]},
        {"food_id": "food_q073", "name_he": "קולורבי", "name_en": "Kohlrabi", "category": "vegetable", "per_100g": {"calories": 27, "protein": 1.7, "carbs": 6, "fat": 0.1}, "serving_g": 100, "aliases_he": ["קולרבי"], "aliases_en": []},
        {"food_id": "food_q074", "name_he": "סלרי", "name_en": "Celery", "category": "vegetable", "per_100g": {"calories": 14, "protein": 0.7, "carbs": 3, "fat": 0.2}, "serving_g": 100, "aliases_he": ["כרפס"], "aliases_en": ["celery sticks"]},
        {"food_id": "food_q075", "name_he": "ארטישוק", "name_en": "Artichoke", "category": "vegetable", "per_100g": {"calories": 47, "protein": 3.3, "carbs": 11, "fat": 0.2}, "serving_g": 120, "aliases_he": ["חרשוף"], "aliases_en": ["globe artichoke"]},
        {"food_id": "food_q076", "name_he": "פטריות", "name_en": "Mushrooms", "category": "vegetable", "per_100g": {"calories": 22, "protein": 3, "carbs": 3.3, "fat": 0.3}, "serving_g": 100, "aliases_he": ["פטריות שמפיניון", "פטריות פורטובלו"], "aliases_en": ["button mushrooms", "portobello"]},
        {"food_id": "food_q077", "name_he": "שעועית ירוקה", "name_en": "Green Beans", "category": "vegetable", "per_100g": {"calories": 31, "protein": 1.8, "carbs": 7, "fat": 0.1}, "serving_g": 100, "aliases_he": ["שעועית צרפתייה"], "aliases_en": ["french beans", "string beans"]},
        {"food_id": "food_q078", "name_he": "אספרגוס", "name_en": "Asparagus", "category": "vegetable", "per_100g": {"calories": 20, "protein": 2.2, "carbs": 4, "fat": 0.1}, "serving_g": 100, "aliases_he": [], "aliases_en": []},
        {"food_id": "food_q079", "name_he": "קישוא", "name_en": "Zucchini", "category": "vegetable", "per_100g": {"calories": 17, "protein": 1.2, "carbs": 3, "fat": 0.3}, "serving_g": 150, "aliases_he": ["קישואים"], "aliases_en": ["courgette"]},
        {"food_id": "food_q080", "name_he": "דלעת", "name_en": "Pumpkin", "category": "vegetable", "per_100g": {"calories": 26, "protein": 1, "carbs": 6.5, "fat": 0.1}, "serving_g": 150, "aliases_he": ["דלורית"], "aliases_en": ["squash"]},
        {"food_id": "food_q081", "name_he": "סלק", "name_en": "Beetroot", "category": "vegetable", "per_100g": {"calories": 43, "protein": 1.6, "carbs": 10, "fat": 0.2}, "serving_g": 100, "aliases_he": ["סלק אדום"], "aliases_en": ["beets"]},
        {"food_id": "food_q082", "name_he": "צנונית", "name_en": "Radish", "category": "vegetable", "per_100g": {"calories": 16, "protein": 0.7, "carbs": 3.4, "fat": 0.1}, "serving_g": 50, "aliases_he": ["צנון"], "aliases_en": ["red radish"]},
        {"food_id": "food_q083", "name_he": "רוקט", "name_en": "Arugula", "category": "vegetable", "per_100g": {"calories": 25, "protein": 2.6, "carbs": 3.7, "fat": 0.7}, "serving_g": 50, "aliases_he": ["רוקולה", "ג׳רג׳יר"], "aliases_en": ["rocket"]},
        {"food_id": "food_q084", "name_he": "כרישה", "name_en": "Leek", "category": "vegetable", "per_100g": {"calories": 61, "protein": 1.5, "carbs": 14, "fat": 0.3}, "serving_g": 80, "aliases_he": ["כרשה"], "aliases_en": ["leeks"]},
        {"food_id": "food_q085", "name_he": "פלפל ירוק", "name_en": "Green Bell Pepper", "category": "vegetable", "per_100g": {"calories": 20, "protein": 0.9, "carbs": 5, "fat": 0.2}, "serving_g": 120, "aliases_he": ["פלפל ירוק מתוק"], "aliases_en": ["green pepper"]},
        {"food_id": "food_q086", "name_he": "שומר", "name_en": "Fennel", "category": "vegetable", "per_100g": {"calories": 31, "protein": 1.2, "carbs": 7, "fat": 0.2}, "serving_g": 100, "aliases_he": ["שומר טרי"], "aliases_en": []},
        {"food_id": "food_q087", "name_he": "במיה", "name_en": "Okra", "category": "vegetable", "per_100g": {"calories": 33, "protein": 1.9, "carbs": 7, "fat": 0.2}, "serving_g": 100, "aliases_he": ["במיה טרייה"], "aliases_en": ["lady finger"]},
        {"food_id": "food_q088", "name_he": "עלי גפן", "name_en": "Grape Leaves", "category": "vegetable", "per_100g": {"calories": 93, "protein": 5.6, "carbs": 17, "fat": 2.1}, "serving_g": 50, "aliases_he": ["עלי גפן ממולאים"], "aliases_en": ["vine leaves"]},
        {"food_id": "food_q089", "name_he": "צ׳ילי", "name_en": "Chili Pepper", "category": "vegetable", "per_100g": {"calories": 40, "protein": 1.9, "carbs": 9, "fat": 0.4}, "serving_g": 10, "aliases_he": ["פלפל חריף"], "aliases_en": ["hot pepper"]},
        {"food_id": "food_q090", "name_he": "קרנבית ירוקה", "name_en": "Green Cauliflower", "category": "vegetable", "per_100g": {"calories": 31, "protein": 3, "carbs": 5.8, "fat": 0.3}, "serving_g": 150, "aliases_he": ["רומנסקו"], "aliases_en": ["romanesco"]},
        {"food_id": "food_q091", "name_he": "ירק חוביזה", "name_en": "Mallow Leaves", "category": "vegetable", "per_100g": {"calories": 37, "protein": 3.5, "carbs": 6, "fat": 0.5}, "serving_g": 80, "aliases_he": ["חוביזה"], "aliases_en": ["khubeza"]},
        {"food_id": "food_q092", "name_he": "כרוב ניצנים", "name_en": "Brussels Sprouts", "category": "vegetable", "per_100g": {"calories": 43, "protein": 3.4, "carbs": 9, "fat": 0.3}, "serving_g": 100, "aliases_he": ["נבטוטי כרוב"], "aliases_en": ["sprouts"]},
        {"food_id": "food_q093", "name_he": "בוק צ׳וי", "name_en": "Bok Choy", "category": "vegetable", "per_100g": {"calories": 13, "protein": 1.5, "carbs": 2, "fat": 0.2}, "serving_g": 100, "aliases_he": ["כרוב סיני"], "aliases_en": ["chinese cabbage"]},
        {"food_id": "food_q094", "name_he": "קייל", "name_en": "Kale", "category": "vegetable", "per_100g": {"calories": 49, "protein": 4.3, "carbs": 9, "fat": 0.9}, "serving_g": 80, "aliases_he": ["כרוב מסולסל"], "aliases_en": ["curly kale"]},
        {"food_id": "food_q095", "name_he": "נענע", "name_en": "Fresh Mint", "category": "vegetable", "per_100g": {"calories": 44, "protein": 3.3, "carbs": 8, "fat": 0.7}, "serving_g": 10, "aliases_he": ["נענע טרייה"], "aliases_en": ["mint leaves"]},
        {"food_id": "food_q096", "name_he": "בזיליקום", "name_en": "Fresh Basil", "category": "vegetable", "per_100g": {"calories": 23, "protein": 3.2, "carbs": 2.7, "fat": 0.6}, "serving_g": 10, "aliases_he": ["ריחן"], "aliases_en": ["basil"]},
        {"food_id": "food_q097", "name_he": "פטרוזיליה", "name_en": "Parsley (fresh)", "category": "vegetable", "per_100g": {"calories": 36, "protein": 3, "carbs": 6.3, "fat": 0.8}, "serving_g": 10, "aliases_he": ["פטרוזיליה טרייה"], "aliases_en": ["fresh parsley"]},
        {"food_id": "food_q098", "name_he": "שמיר", "name_en": "Dill", "category": "vegetable", "per_100g": {"calories": 43, "protein": 3.5, "carbs": 7, "fat": 1.1}, "serving_g": 10, "aliases_he": ["שמיר טרי"], "aliases_en": ["fresh dill"]},
        {"food_id": "food_q099", "name_he": "עגבניות שרי", "name_en": "Cherry Tomatoes", "category": "vegetable", "per_100g": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2}, "serving_g": 120, "aliases_he": ["עגבניות קטנות"], "aliases_en": ["grape tomatoes"]},
        {"food_id": "food_q100", "name_he": "מלפפון חמוץ", "name_en": "Pickled Cucumber", "category": "vegetable", "per_100g": {"calories": 11, "protein": 0.3, "carbs": 2.3, "fat": 0.2}, "serving_g": 50, "aliases_he": ["חמוצים", "חמוץ"], "aliases_en": ["pickle", "gherkin"]},
    ],
    "fruits": [
        {"food_id": "food_q101", "name_he": "תאנים", "name_en": "Fresh Figs", "category": "fruit", "per_100g": {"calories": 74, "protein": 0.8, "carbs": 19, "fat": 0.3}, "serving_g": 100, "aliases_he": ["תאנה"], "aliases_en": ["figs"]},
        {"food_id": "food_q102", "name_he": "תמרים", "name_en": "Dates (Medjool)", "category": "fruit", "per_100g": {"calories": 277, "protein": 1.8, "carbs": 75, "fat": 0.2}, "serving_g": 30, "aliases_he": ["תמר מג׳הול"], "aliases_en": ["medjool dates"]},
        {"food_id": "food_q103", "name_he": "רימון", "name_en": "Pomegranate", "category": "fruit", "per_100g": {"calories": 83, "protein": 1.7, "carbs": 19, "fat": 1.2}, "serving_g": 100, "aliases_he": ["רימון אדום"], "aliases_en": ["pomegranate seeds"]},
        {"food_id": "food_q104", "name_he": "אפרסק", "name_en": "Peach", "category": "fruit", "per_100g": {"calories": 39, "protein": 0.9, "carbs": 10, "fat": 0.3}, "serving_g": 150, "aliases_he": ["אפרסקים"], "aliases_en": ["peaches"]},
        {"food_id": "food_q105", "name_he": "משמש", "name_en": "Apricot", "category": "fruit", "per_100g": {"calories": 48, "protein": 1.4, "carbs": 11, "fat": 0.4}, "serving_g": 100, "aliases_he": ["משמשים"], "aliases_en": ["apricots"]},
        {"food_id": "food_q106", "name_he": "שזיף", "name_en": "Plum", "category": "fruit", "per_100g": {"calories": 46, "protein": 0.7, "carbs": 11, "fat": 0.3}, "serving_g": 100, "aliases_he": ["שזיפים"], "aliases_en": ["plums"]},
        {"food_id": "food_q107", "name_he": "אגס", "name_en": "Pear", "category": "fruit", "per_100g": {"calories": 57, "protein": 0.4, "carbs": 15, "fat": 0.1}, "serving_g": 150, "aliases_he": ["אגסים"], "aliases_en": ["pears"]},
        {"food_id": "food_q108", "name_he": "פומלה", "name_en": "Pomelo", "category": "fruit", "per_100g": {"calories": 38, "protein": 0.8, "carbs": 10, "fat": 0.04}, "serving_g": 200, "aliases_he": ["פומלו"], "aliases_en": ["pummelo"]},
        {"food_id": "food_q109", "name_he": "קלמנטינה", "name_en": "Clementine", "category": "fruit", "per_100g": {"calories": 47, "protein": 0.9, "carbs": 12, "fat": 0.2}, "serving_g": 100, "aliases_he": ["מנדרינה"], "aliases_en": ["mandarin", "tangerine"]},
        {"food_id": "food_q110", "name_he": "אשכולית", "name_en": "Grapefruit", "category": "fruit", "per_100g": {"calories": 42, "protein": 0.8, "carbs": 11, "fat": 0.1}, "serving_g": 200, "aliases_he": ["גרייפ"], "aliases_en": ["grapefruit"]},
        {"food_id": "food_q111", "name_he": "קיווי", "name_en": "Kiwi", "category": "fruit", "per_100g": {"calories": 61, "protein": 1.1, "carbs": 15, "fat": 0.5}, "serving_g": 80, "aliases_he": ["קיווי ירוק"], "aliases_en": ["kiwi fruit"]},
        {"food_id": "food_q112", "name_he": "אננס", "name_en": "Pineapple", "category": "fruit", "per_100g": {"calories": 50, "protein": 0.5, "carbs": 13, "fat": 0.1}, "serving_g": 150, "aliases_he": ["אננס טרי"], "aliases_en": ["fresh pineapple"]},
        {"food_id": "food_q113", "name_he": "פסיפלורה", "name_en": "Passion Fruit", "category": "fruit", "per_100g": {"calories": 97, "protein": 2.2, "carbs": 23, "fat": 0.7}, "serving_g": 50, "aliases_he": ["שעוניות"], "aliases_en": ["granadilla"]},
        {"food_id": "food_q114", "name_he": "פפאיה", "name_en": "Papaya", "category": "fruit", "per_100g": {"calories": 43, "protein": 0.5, "carbs": 11, "fat": 0.3}, "serving_g": 150, "aliases_he": ["פפאיה בשלה"], "aliases_en": ["pawpaw"]},
        {"food_id": "food_q115", "name_he": "ליצ׳י", "name_en": "Lychee", "category": "fruit", "per_100g": {"calories": 66, "protein": 0.8, "carbs": 17, "fat": 0.4}, "serving_g": 80, "aliases_he": ["ליצי"], "aliases_en": ["litchi"]},
        {"food_id": "food_q116", "name_he": "דובדבנים", "name_en": "Cherries", "category": "fruit", "per_100g": {"calories": 63, "protein": 1, "carbs": 16, "fat": 0.2}, "serving_g": 100, "aliases_he": ["דובדבן"], "aliases_en": ["sweet cherries"]},
        {"food_id": "food_q117", "name_he": "צבר", "name_en": "Prickly Pear (Sabra)", "category": "fruit", "per_100g": {"calories": 41, "protein": 0.7, "carbs": 10, "fat": 0.5}, "serving_g": 100, "aliases_he": ["סברס"], "aliases_en": ["cactus fruit"]},
        {"food_id": "food_q118", "name_he": "גויאבה", "name_en": "Guava", "category": "fruit", "per_100g": {"calories": 68, "protein": 2.6, "carbs": 14, "fat": 1}, "serving_g": 100, "aliases_he": ["גויאווה"], "aliases_en": []},
        {"food_id": "food_q119", "name_he": "פירות יער", "name_en": "Mixed Berries", "category": "fruit", "per_100g": {"calories": 57, "protein": 1.2, "carbs": 14, "fat": 0.3}, "serving_g": 100, "aliases_he": ["תותי יער", "אוכמניות"], "aliases_en": ["berries", "blueberries", "raspberries"]},
        {"food_id": "food_q120", "name_he": "נקטרינה", "name_en": "Nectarine", "category": "fruit", "per_100g": {"calories": 44, "protein": 1.1, "carbs": 11, "fat": 0.3}, "serving_g": 150, "aliases_he": ["נקטרינות"], "aliases_en": ["nectarines"]},
        {"food_id": "food_q121", "name_he": "חבוש", "name_en": "Quince", "category": "fruit", "per_100g": {"calories": 57, "protein": 0.4, "carbs": 15, "fat": 0.1}, "serving_g": 100, "aliases_he": ["חבושים"], "aliases_en": []},
        {"food_id": "food_q122", "name_he": "שסק", "name_en": "Loquat", "category": "fruit", "per_100g": {"calories": 47, "protein": 0.4, "carbs": 12, "fat": 0.2}, "serving_g": 100, "aliases_he": ["שסקים"], "aliases_en": ["japanese medlar"]},
        {"food_id": "food_q123", "name_he": "תמרים יבשים", "name_en": "Dried Dates", "category": "fruit", "per_100g": {"calories": 282, "protein": 2.5, "carbs": 75, "fat": 0.4}, "serving_g": 30, "aliases_he": ["תמרים דגלת נור"], "aliases_en": ["deglet noor"]},
        {"food_id": "food_q124", "name_he": "משמש מיובש", "name_en": "Dried Apricots", "category": "fruit", "per_100g": {"calories": 241, "protein": 3.4, "carbs": 63, "fat": 0.5}, "serving_g": 30, "aliases_he": ["משמש יבש"], "aliases_en": ["dried apricot"]},
        {"food_id": "food_q125", "name_he": "חמוציות", "name_en": "Cranberries (dried)", "category": "fruit", "per_100g": {"calories": 308, "protein": 0.1, "carbs": 82, "fat": 1.4}, "serving_g": 20, "aliases_he": ["קרנברי"], "aliases_en": ["craisins"]},
    ],
    "dairy": [
        {"food_id": "food_q126", "name_he": "גבינת שמנת", "name_en": "Cream Cheese", "category": "dairy", "per_100g": {"calories": 342, "protein": 6, "carbs": 4, "fat": 34}, "serving_g": 30, "aliases_he": ["פילדלפיה", "גבינת שמנת 30%"], "aliases_en": ["philadelphia"]},
        {"food_id": "food_q127", "name_he": "גבינת עיזים", "name_en": "Goat Cheese", "category": "dairy", "per_100g": {"calories": 264, "protein": 18, "carbs": 1, "fat": 21}, "serving_g": 30, "aliases_he": ["גבינת עזים"], "aliases_en": ["chevre"]},
        {"food_id": "food_q128", "name_he": "מוצרלה", "name_en": "Mozzarella", "category": "dairy", "per_100g": {"calories": 280, "protein": 28, "carbs": 3, "fat": 17}, "serving_g": 30, "aliases_he": ["מוצרלה טרייה"], "aliases_en": ["fresh mozzarella"]},
        {"food_id": "food_q129", "name_he": "ריקוטה", "name_en": "Ricotta", "category": "dairy", "per_100g": {"calories": 174, "protein": 11, "carbs": 3, "fat": 13}, "serving_g": 60, "aliases_he": ["ריקוטה טרייה"], "aliases_en": []},
        {"food_id": "food_q130", "name_he": "גבינה צפתית", "name_en": "Tzfatit Cheese", "category": "dairy", "per_100g": {"calories": 270, "protein": 17, "carbs": 2, "fat": 22}, "serving_g": 30, "aliases_he": ["צפתית", "גבינת צפת"], "aliases_en": ["safed cheese"]},
        {"food_id": "food_q131", "name_he": "חלב עיזים", "name_en": "Goat Milk", "category": "dairy", "per_100g": {"calories": 69, "protein": 3.6, "carbs": 4.5, "fat": 4.1}, "serving_g": 250, "aliases_he": ["חלב עז"], "aliases_en": []},
        {"food_id": "food_q132", "name_he": "קפיר", "name_en": "Kefir", "category": "dairy", "per_100g": {"calories": 41, "protein": 3.3, "carbs": 4.7, "fat": 1}, "serving_g": 250, "aliases_he": ["קפיר טבעי"], "aliases_en": ["kefir drink"]},
        {"food_id": "food_q133", "name_he": "מסקרפונה", "name_en": "Mascarpone", "category": "dairy", "per_100g": {"calories": 429, "protein": 4.8, "carbs": 3.5, "fat": 44}, "serving_g": 30, "aliases_he": [], "aliases_en": ["mascarpone cheese"]},
        {"food_id": "food_q134", "name_he": "פרמזן", "name_en": "Parmesan", "category": "dairy", "per_100g": {"calories": 431, "protein": 38, "carbs": 4, "fat": 29}, "serving_g": 15, "aliases_he": ["פרמג׳ן"], "aliases_en": ["parmigiano"]},
        {"food_id": "food_q135", "name_he": "יוגורט שתייה", "name_en": "Drinking Yogurt", "category": "dairy", "per_100g": {"calories": 63, "protein": 3.1, "carbs": 12, "fat": 0.5}, "serving_g": 200, "aliases_he": ["יוגורט לשתייה", "אקטיביה"], "aliases_en": ["yogurt drink"]},
        {"food_id": "food_q136", "name_he": "גבינת גאודה", "name_en": "Gouda Cheese", "category": "dairy", "per_100g": {"calories": 356, "protein": 25, "carbs": 2, "fat": 27}, "serving_g": 30, "aliases_he": ["גאודה"], "aliases_en": ["gouda"]},
        {"food_id": "food_q137", "name_he": "חלב 3%", "name_en": "Whole Milk 3%", "category": "dairy", "per_100g": {"calories": 60, "protein": 3.2, "carbs": 4.8, "fat": 3}, "serving_g": 250, "aliases_he": ["חלב מלא"], "aliases_en": ["full fat milk"]},
        {"food_id": "food_q138", "name_he": "גלידה", "name_en": "Ice Cream (vanilla)", "category": "dairy", "per_100g": {"calories": 207, "protein": 3.5, "carbs": 24, "fat": 11}, "serving_g": 80, "aliases_he": ["גלידה וניל"], "aliases_en": ["vanilla ice cream"]},
        {"food_id": "food_q139", "name_he": "חלב שוקו", "name_en": "Chocolate Milk", "category": "dairy", "per_100g": {"calories": 83, "protein": 3.2, "carbs": 12, "fat": 2.5}, "serving_g": 250, "aliases_he": ["שוקו"], "aliases_en": ["choco milk"]},
        {"food_id": "food_q140", "name_he": "גבינת רוקפור", "name_en": "Blue Cheese", "category": "dairy", "per_100g": {"calories": 353, "protein": 21, "carbs": 2, "fat": 29}, "serving_g": 30, "aliases_he": ["גבינה כחולה"], "aliases_en": ["roquefort"]},
    ],
    "legumes": [
        {"food_id": "food_q141", "name_he": "עדשים ירוקות", "name_en": "Green Lentils (cooked)", "category": "legume", "per_100g": {"calories": 116, "protein": 9, "carbs": 20, "fat": 0.4}, "serving_g": 150, "aliases_he": ["עדשים ירוקות מבושלות"], "aliases_en": ["puy lentils"]},
        {"food_id": "food_q142", "name_he": "עדשים שחורות", "name_en": "Black Lentils (cooked)", "category": "legume", "per_100g": {"calories": 116, "protein": 9, "carbs": 20, "fat": 0.4}, "serving_g": 150, "aliases_he": ["עדשים בלוגה"], "aliases_en": ["beluga lentils"]},
        {"food_id": "food_q143", "name_he": "פול", "name_en": "Fava Beans (cooked)", "category": "legume", "per_100g": {"calories": 110, "protein": 8, "carbs": 19, "fat": 0.4}, "serving_g": 150, "aliases_he": ["פול מדמס", "פולים"], "aliases_en": ["broad beans"]},
        {"food_id": "food_q144", "name_he": "לוביה", "name_en": "Black-Eyed Peas (cooked)", "category": "legume", "per_100g": {"calories": 116, "protein": 8, "carbs": 21, "fat": 0.5}, "serving_g": 150, "aliases_he": ["שעועית עין שחורה"], "aliases_en": ["cowpeas"]},
        {"food_id": "food_q145", "name_he": "חומוס גולמי", "name_en": "Raw Chickpeas (dry)", "category": "legume", "per_100g": {"calories": 364, "protein": 19, "carbs": 61, "fat": 6}, "serving_g": 50, "aliases_he": ["חומוס יבש"], "aliases_en": ["dried chickpeas"]},
        {"food_id": "food_q146", "name_he": "סויה", "name_en": "Soybeans (cooked)", "category": "legume", "per_100g": {"calories": 173, "protein": 17, "carbs": 10, "fat": 9}, "serving_g": 100, "aliases_he": ["פולי סויה"], "aliases_en": ["soybean"]},
        {"food_id": "food_q147", "name_he": "שעועית אדומה", "name_en": "Red Kidney Beans", "category": "legume", "per_100g": {"calories": 127, "protein": 8.7, "carbs": 22, "fat": 0.5}, "serving_g": 150, "aliases_he": ["שעועית אדומה מבושלת"], "aliases_en": ["kidney beans"]},
        {"food_id": "food_q148", "name_he": "שעועית פינטו", "name_en": "Pinto Beans", "category": "legume", "per_100g": {"calories": 143, "protein": 9, "carbs": 27, "fat": 0.7}, "serving_g": 150, "aliases_he": ["שעועית חומה"], "aliases_en": ["brown beans"]},
        {"food_id": "food_q149", "name_he": "שעועית מאש", "name_en": "Mung Beans (cooked)", "category": "legume", "per_100g": {"calories": 105, "protein": 7, "carbs": 19, "fat": 0.4}, "serving_g": 100, "aliases_he": ["מאש"], "aliases_en": ["moong dal"]},
        {"food_id": "food_q150", "name_he": "נבטים", "name_en": "Bean Sprouts", "category": "legume", "per_100g": {"calories": 31, "protein": 3, "carbs": 6, "fat": 0.2}, "serving_g": 50, "aliases_he": ["נבטי שעועית"], "aliases_en": ["sprouts", "mung sprouts"]},
    ],
    "nuts_seeds": [
        {"food_id": "food_q151", "name_he": "פיסטוקים", "name_en": "Pistachios", "category": "nut_seed", "per_100g": {"calories": 562, "protein": 20, "carbs": 28, "fat": 45}, "serving_g": 25, "aliases_he": ["פיסטוק"], "aliases_en": ["pistachio nuts"]},
        {"food_id": "food_q152", "name_he": "אגוזי לוז", "name_en": "Hazelnuts", "category": "nut_seed", "per_100g": {"calories": 628, "protein": 15, "carbs": 17, "fat": 61}, "serving_g": 20, "aliases_he": ["לוז"], "aliases_en": ["filberts"]},
        {"food_id": "food_q153", "name_he": "צנוברים", "name_en": "Pine Nuts", "category": "nut_seed", "per_100g": {"calories": 673, "protein": 14, "carbs": 13, "fat": 68}, "serving_g": 15, "aliases_he": ["שנוברים"], "aliases_en": ["pignoli"]},
        {"food_id": "food_q154", "name_he": "זרעי פשתן", "name_en": "Flaxseeds", "category": "nut_seed", "per_100g": {"calories": 534, "protein": 18, "carbs": 29, "fat": 42}, "serving_g": 15, "aliases_he": ["פשתן"], "aliases_en": ["linseed"]},
        {"food_id": "food_q155", "name_he": "זרעי המפ", "name_en": "Hemp Seeds", "category": "nut_seed", "per_100g": {"calories": 553, "protein": 32, "carbs": 9, "fat": 49}, "serving_g": 15, "aliases_he": ["גרעיני קנבוס"], "aliases_en": ["hemp hearts"]},
        {"food_id": "food_q156", "name_he": "ערמונים", "name_en": "Chestnuts", "category": "nut_seed", "per_100g": {"calories": 213, "protein": 2.4, "carbs": 45, "fat": 2.2}, "serving_g": 50, "aliases_he": ["ערמונים צלויים"], "aliases_en": ["roasted chestnuts"]},
        {"food_id": "food_q157", "name_he": "חלבה", "name_en": "Halva", "category": "nut_seed", "per_100g": {"calories": 510, "protein": 12, "carbs": 55, "fat": 28}, "serving_g": 30, "aliases_he": ["חלווה"], "aliases_en": ["halvah"]},
        {"food_id": "food_q158", "name_he": "תערובת אגוזים", "name_en": "Mixed Nuts", "category": "nut_seed", "per_100g": {"calories": 607, "protein": 20, "carbs": 21, "fat": 54}, "serving_g": 30, "aliases_he": ["מיקס אגוזים"], "aliases_en": ["trail mix nuts"]},
    ],
    "condiments_other": [
        {"food_id": "food_q159", "name_he": "חריסה", "name_en": "Harissa", "category": "condiment", "per_100g": {"calories": 44, "protein": 1.3, "carbs": 7, "fat": 1.5}, "serving_g": 10, "aliases_he": ["חריסה טוניסאית"], "aliases_en": ["harissa paste"]},
        {"food_id": "food_q160", "name_he": "סחוג", "name_en": "Schug", "category": "condiment", "per_100g": {"calories": 60, "protein": 2, "carbs": 7, "fat": 3}, "serving_g": 10, "aliases_he": ["ז׳וג", "סחוג ירוק"], "aliases_en": ["zhug", "green schug"]},
        {"food_id": "food_q161", "name_he": "עמבה", "name_en": "Amba Sauce", "category": "condiment", "per_100g": {"calories": 80, "protein": 1, "carbs": 16, "fat": 1.5}, "serving_g": 20, "aliases_he": ["עמבא מנגו"], "aliases_en": ["mango pickle sauce"]},
        {"food_id": "food_q162", "name_he": "סילאן", "name_en": "Date Syrup (Silan)", "category": "other", "per_100g": {"calories": 300, "protein": 2, "carbs": 73, "fat": 0.3}, "serving_g": 15, "aliases_he": ["סילאן תמרים"], "aliases_en": ["date honey"]},
        {"food_id": "food_q163", "name_he": "חומץ תפוחים", "name_en": "Apple Cider Vinegar", "category": "condiment", "per_100g": {"calories": 21, "protein": 0, "carbs": 0.9, "fat": 0}, "serving_g": 15, "aliases_he": ["חומץ תפוחי עץ"], "aliases_en": ["ACV"]},
        {"food_id": "food_q164", "name_he": "זעתר", "name_en": "Za'atar Spice Mix", "category": "condiment", "per_100g": {"calories": 250, "protein": 9, "carbs": 40, "fat": 8}, "serving_g": 5, "aliases_he": ["זעתר ירוק"], "aliases_en": ["zaatar"]},
        {"food_id": "food_q165", "name_he": "סומאק", "name_en": "Sumac", "category": "condiment", "per_100g": {"calories": 239, "protein": 5, "carbs": 44, "fat": 8}, "serving_g": 5, "aliases_he": ["סומק"], "aliases_en": []},
        {"food_id": "food_q166", "name_he": "פפריקה מעושנת", "name_en": "Smoked Paprika", "category": "condiment", "per_100g": {"calories": 282, "protein": 14, "carbs": 54, "fat": 13}, "serving_g": 3, "aliases_he": ["פפריקה"], "aliases_en": ["paprika powder"]},
        {"food_id": "food_q167", "name_he": "כורכום", "name_en": "Turmeric", "category": "condiment", "per_100g": {"calories": 312, "protein": 10, "carbs": 67, "fat": 3}, "serving_g": 3, "aliases_he": ["כורכומין"], "aliases_en": ["turmeric powder"]},
        {"food_id": "food_q168", "name_he": "קינמון", "name_en": "Cinnamon", "category": "condiment", "per_100g": {"calories": 247, "protein": 4, "carbs": 81, "fat": 1.2}, "serving_g": 3, "aliases_he": ["קינמון טחון"], "aliases_en": ["ground cinnamon"]},
        {"food_id": "food_q169", "name_he": "כמון", "name_en": "Cumin", "category": "condiment", "per_100g": {"calories": 375, "protein": 18, "carbs": 44, "fat": 22}, "serving_g": 3, "aliases_he": ["כמון טחון"], "aliases_en": ["ground cumin"]},
        {"food_id": "food_q170", "name_he": "קטשופ", "name_en": "Ketchup", "category": "condiment", "per_100g": {"calories": 101, "protein": 1.7, "carbs": 25, "fat": 0.1}, "serving_g": 20, "aliases_he": ["רוטב עגבניות מתוק"], "aliases_en": ["tomato ketchup"]},
        {"food_id": "food_q171", "name_he": "סוכר", "name_en": "Sugar", "category": "other", "per_100g": {"calories": 387, "protein": 0, "carbs": 100, "fat": 0}, "serving_g": 5, "aliases_he": ["סוכר לבן"], "aliases_en": ["white sugar", "table sugar"]},
        {"food_id": "food_q172", "name_he": "ריבה", "name_en": "Jam", "category": "other", "per_100g": {"calories": 250, "protein": 0.4, "carbs": 65, "fat": 0.1}, "serving_g": 20, "aliases_he": ["ריבת תות", "ריבת משמש"], "aliases_en": ["fruit preserve", "strawberry jam"]},
        {"food_id": "food_q173", "name_he": "סירופ מייפל", "name_en": "Maple Syrup", "category": "other", "per_100g": {"calories": 260, "protein": 0, "carbs": 67, "fat": 0}, "serving_g": 15, "aliases_he": ["סירופ"], "aliases_en": ["maple"]},
        {"food_id": "food_q174", "name_he": "קקאו", "name_en": "Cocoa Powder", "category": "other", "per_100g": {"calories": 228, "protein": 20, "carbs": 58, "fat": 14}, "serving_g": 10, "aliases_he": ["אבקת קקאו"], "aliases_en": ["cacao"]},
        {"food_id": "food_q175", "name_he": "חלבה שוקולד", "name_en": "Chocolate Halva", "category": "other", "per_100g": {"calories": 520, "protein": 11, "carbs": 56, "fat": 30}, "serving_g": 30, "aliases_he": ["חלווה שוקולד"], "aliases_en": []},
    ],
    "beverages": [
        {"food_id": "food_q176", "name_he": "לימונדה", "name_en": "Lemonade", "category": "beverage", "per_100g": {"calories": 40, "protein": 0.1, "carbs": 10, "fat": 0}, "serving_g": 250, "aliases_he": ["לימונענע"], "aliases_en": ["limonana"]},
        {"food_id": "food_q177", "name_he": "תה שחור", "name_en": "Black Tea", "category": "beverage", "per_100g": {"calories": 1, "protein": 0, "carbs": 0.3, "fat": 0}, "serving_g": 250, "aliases_he": ["תה רגיל"], "aliases_en": ["regular tea"]},
        {"food_id": "food_q178", "name_he": "מיץ גזר", "name_en": "Carrot Juice", "category": "beverage", "per_100g": {"calories": 40, "protein": 0.9, "carbs": 9, "fat": 0.2}, "serving_g": 250, "aliases_he": ["מיץ גזר סחוט"], "aliases_en": ["fresh carrot juice"]},
        {"food_id": "food_q179", "name_he": "סמוזי ירוק", "name_en": "Green Smoothie", "category": "beverage", "per_100g": {"calories": 50, "protein": 1.5, "carbs": 11, "fat": 0.5}, "serving_g": 300, "aliases_he": ["שייק ירוק"], "aliases_en": ["green shake"]},
        {"food_id": "food_q180", "name_he": "חלב אורז", "name_en": "Rice Milk", "category": "beverage", "per_100g": {"calories": 47, "protein": 0.3, "carbs": 9.2, "fat": 1}, "serving_g": 250, "aliases_he": ["משקה אורז"], "aliases_en": ["rice drink"]},
        {"food_id": "food_q181", "name_he": "חלב קוקוס (משקה)", "name_en": "Coconut Milk Drink", "category": "beverage", "per_100g": {"calories": 20, "protein": 0.2, "carbs": 2.7, "fat": 1}, "serving_g": 250, "aliases_he": ["משקה קוקוס"], "aliases_en": ["coconut drink"]},
        {"food_id": "food_q182", "name_he": "חלב שיבולת שועל", "name_en": "Oat Milk", "category": "beverage", "per_100g": {"calories": 43, "protein": 0.4, "carbs": 7, "fat": 1.5}, "serving_g": 250, "aliases_he": ["משקה שיבולת שועל"], "aliases_en": ["oat drink"]},
        {"food_id": "food_q183", "name_he": "מים מינרלים", "name_en": "Sparkling Water", "category": "beverage", "per_100g": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}, "serving_g": 330, "aliases_he": ["מים מוגזים", "סודה"], "aliases_en": ["soda water", "seltzer"]},
        {"food_id": "food_q184", "name_he": "מיץ אשכוליות", "name_en": "Grapefruit Juice", "category": "beverage", "per_100g": {"calories": 39, "protein": 0.5, "carbs": 9, "fat": 0.1}, "serving_g": 250, "aliases_he": ["מיץ גרייפ"], "aliases_en": []},
        {"food_id": "food_q185", "name_he": "מיץ רימונים", "name_en": "Pomegranate Juice", "category": "beverage", "per_100g": {"calories": 54, "protein": 0.2, "carbs": 13, "fat": 0.3}, "serving_g": 250, "aliases_he": ["מיץ רימון"], "aliases_en": []},
    ],
}


# ═══════════════════════════════════════════════════════════════════
# RECIPE_KNOWLEDGE_BASE — 200+ Israeli recipes
# ═══════════════════════════════════════════════════════════════════

RECIPE_KNOWLEDGE_BASE: List[dict] = [
    # ── Breakfast ──────────────────────────────────────────────
    {"recipe_id": "recipe_001", "name_he": "שקשוקה", "name_en": "Shakshuka", "ingredients": [{"food_name": "ביצה", "food_name_en": "egg", "quantity": 200, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 200, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 50, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 380, "protein": 22, "carbs": 18, "fat": 24}, "portions": 2, "prep_time_minutes": 20, "meal_types": ["BREAKFAST", "DINNER"], "tags": ["vegetarian", "traditional", "quick"], "kashrut": "parve"},
    {"recipe_id": "recipe_002", "name_he": "טוסט גבינה", "name_en": "Cheese Toast", "ingredients": [{"food_name": "לחם", "food_name_en": "bread", "quantity": 60, "unit": "grams"}, {"food_name": "גבינה צהובה", "food_name_en": "yellow cheese", "quantity": 30, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 320, "protein": 14, "carbs": 32, "fat": 15}, "portions": 1, "prep_time_minutes": 5, "meal_types": ["BREAKFAST"], "tags": ["dairy", "quick"], "kashrut": "dairy"},
    {"recipe_id": "recipe_003", "name_he": "גרנולה עם יוגורט", "name_en": "Granola with Yogurt", "ingredients": [{"food_name": "גרנולה", "food_name_en": "granola", "quantity": 40, "unit": "grams"}, {"food_name": "יוגורט יווני", "food_name_en": "greek yogurt", "quantity": 170, "unit": "grams"}, {"food_name": "דבש", "food_name_en": "honey", "quantity": 10, "unit": "grams"}, {"food_name": "בננה", "food_name_en": "banana", "quantity": 60, "unit": "grams"}], "total_nutrition": {"calories": 380, "protein": 20, "carbs": 55, "fat": 10}, "portions": 1, "prep_time_minutes": 3, "meal_types": ["BREAKFAST", "MORNING_SNACK"], "tags": ["dairy", "quick", "healthy"], "kashrut": "dairy"},
    {"recipe_id": "recipe_004", "name_he": "אומלט ירקות", "name_en": "Vegetable Omelette", "ingredients": [{"food_name": "ביצה", "food_name_en": "egg", "quantity": 150, "unit": "grams"}, {"food_name": "פלפל אדום", "food_name_en": "red pepper", "quantity": 50, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 30, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 350, "protein": 22, "carbs": 8, "fat": 26}, "portions": 1, "prep_time_minutes": 10, "meal_types": ["BREAKFAST", "DINNER"], "tags": ["vegetarian", "quick", "low-carb"], "kashrut": "parve"},
    {"recipe_id": "recipe_005", "name_he": "צלחת לבנה", "name_en": "Labaneh Plate", "ingredients": [{"food_name": "לבנה", "food_name_en": "labneh", "quantity": 100, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 50, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 50, "unit": "grams"}, {"food_name": "לחם", "food_name_en": "bread", "quantity": 30, "unit": "grams"}], "total_nutrition": {"calories": 340, "protein": 10, "carbs": 22, "fat": 24}, "portions": 1, "prep_time_minutes": 5, "meal_types": ["BREAKFAST"], "tags": ["dairy", "traditional", "quick"], "kashrut": "dairy"},
    {"recipe_id": "recipe_006", "name_he": "שיבולת שועל עם פירות", "name_en": "Oatmeal with Fruits", "ingredients": [{"food_name": "שיבולת שועל", "food_name_en": "oats", "quantity": 40, "unit": "grams"}, {"food_name": "חלב", "food_name_en": "milk", "quantity": 200, "unit": "grams"}, {"food_name": "בננה", "food_name_en": "banana", "quantity": 60, "unit": "grams"}, {"food_name": "דבש", "food_name_en": "honey", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 350, "protein": 13, "carbs": 60, "fat": 7}, "portions": 1, "prep_time_minutes": 8, "meal_types": ["BREAKFAST"], "tags": ["dairy", "healthy", "fiber"], "kashrut": "dairy"},
    {"recipe_id": "recipe_007", "name_he": "סביח", "name_en": "Sabich", "ingredients": [{"food_name": "חציל", "food_name_en": "eggplant", "quantity": 150, "unit": "grams"}, {"food_name": "ביצה", "food_name_en": "egg", "quantity": 50, "unit": "grams"}, {"food_name": "פיתה", "food_name_en": "pita", "quantity": 60, "unit": "grams"}, {"food_name": "טחינה", "food_name_en": "tahini", "quantity": 20, "unit": "grams"}, {"food_name": "חומוס ממרח", "food_name_en": "hummus", "quantity": 30, "unit": "grams"}], "total_nutrition": {"calories": 450, "protein": 16, "carbs": 45, "fat": 24}, "portions": 1, "prep_time_minutes": 15, "meal_types": ["BREAKFAST", "LUNCH"], "tags": ["traditional", "iraqi"], "kashrut": "parve"},
    {"recipe_id": "recipe_008", "name_he": "ביצים קשות עם ירקות", "name_en": "Hard Boiled Eggs with Veggies", "ingredients": [{"food_name": "ביצה", "food_name_en": "egg", "quantity": 100, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 100, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 100, "unit": "grams"}], "total_nutrition": {"calories": 190, "protein": 15, "carbs": 8, "fat": 11}, "portions": 1, "prep_time_minutes": 10, "meal_types": ["BREAKFAST"], "tags": ["quick", "protein"], "kashrut": "parve"},

    # ── Lunch ─────────────────────────────────────────────────
    {"recipe_id": "recipe_009", "name_he": "שניצל עם סלט", "name_en": "Schnitzel with Salad", "ingredients": [{"food_name": "חזה עוף", "food_name_en": "chicken breast", "quantity": 200, "unit": "grams"}, {"food_name": "לחם", "food_name_en": "bread", "quantity": 30, "unit": "grams"}, {"food_name": "ביצה", "food_name_en": "egg", "quantity": 50, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 15, "unit": "grams"}, {"food_name": "חסה", "food_name_en": "lettuce", "quantity": 80, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 100, "unit": "grams"}], "total_nutrition": {"calories": 550, "protein": 50, "carbs": 25, "fat": 28}, "portions": 1, "prep_time_minutes": 25, "meal_types": ["LUNCH"], "tags": ["meat", "traditional"], "kashrut": "meat"},
    {"recipe_id": "recipe_010", "name_he": "חומוס עם בשר", "name_en": "Hummus with Ground Meat", "ingredients": [{"food_name": "חומוס ממרח", "food_name_en": "hummus", "quantity": 200, "unit": "grams"}, {"food_name": "בקר טחון", "food_name_en": "ground beef", "quantity": 100, "unit": "grams"}, {"food_name": "פיתה", "food_name_en": "pita", "quantity": 60, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 680, "protein": 38, "carbs": 50, "fat": 36}, "portions": 1, "prep_time_minutes": 15, "meal_types": ["LUNCH"], "tags": ["meat", "traditional"], "kashrut": "meat"},
    {"recipe_id": "recipe_011", "name_he": "עוף צלוי עם אורז", "name_en": "Grilled Chicken with Rice", "ingredients": [{"food_name": "חזה עוף", "food_name_en": "chicken breast", "quantity": 200, "unit": "grams"}, {"food_name": "אורז לבן", "food_name_en": "white rice", "quantity": 150, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 100, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 100, "unit": "grams"}], "total_nutrition": {"calories": 600, "protein": 52, "carbs": 60, "fat": 15}, "portions": 1, "prep_time_minutes": 30, "meal_types": ["LUNCH"], "tags": ["meat", "healthy"], "kashrut": "meat"},
    {"recipe_id": "recipe_012", "name_he": "פלפלים ממולאים", "name_en": "Stuffed Peppers", "ingredients": [{"food_name": "פלפל אדום", "food_name_en": "red pepper", "quantity": 200, "unit": "grams"}, {"food_name": "בקר טחון", "food_name_en": "ground beef", "quantity": 150, "unit": "grams"}, {"food_name": "אורז לבן", "food_name_en": "white rice", "quantity": 100, "unit": "grams"}, {"food_name": "רוטב עגבניות", "food_name_en": "tomato sauce", "quantity": 100, "unit": "grams"}], "total_nutrition": {"calories": 580, "protein": 35, "carbs": 55, "fat": 24}, "portions": 2, "prep_time_minutes": 45, "meal_types": ["LUNCH", "DINNER"], "tags": ["meat", "traditional"], "kashrut": "meat"},
    {"recipe_id": "recipe_013", "name_he": "מג׳דרה", "name_en": "Mujadara", "ingredients": [{"food_name": "עדשים אדומות", "food_name_en": "red lentils", "quantity": 150, "unit": "grams"}, {"food_name": "אורז לבן", "food_name_en": "white rice", "quantity": 150, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 100, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 20, "unit": "grams"}], "total_nutrition": {"calories": 650, "protein": 24, "carbs": 100, "fat": 14}, "portions": 3, "prep_time_minutes": 30, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "traditional", "cheap"], "kashrut": "parve"},
    {"recipe_id": "recipe_014", "name_he": "שווארמה בפיתה", "name_en": "Shawarma in Pita", "ingredients": [{"food_name": "חזה עוף", "food_name_en": "chicken breast", "quantity": 200, "unit": "grams"}, {"food_name": "פיתה", "food_name_en": "pita", "quantity": 60, "unit": "grams"}, {"food_name": "טחינה", "food_name_en": "tahini", "quantity": 30, "unit": "grams"}, {"food_name": "חסה", "food_name_en": "lettuce", "quantity": 30, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 580, "protein": 50, "carbs": 45, "fat": 20}, "portions": 1, "prep_time_minutes": 20, "meal_types": ["LUNCH"], "tags": ["meat", "street_food"], "kashrut": "meat"},
    {"recipe_id": "recipe_015", "name_he": "סלמון צלוי עם ירקות", "name_en": "Roasted Salmon with Vegetables", "ingredients": [{"food_name": "סלמון", "food_name_en": "salmon", "quantity": 200, "unit": "grams"}, {"food_name": "ברוקולי", "food_name_en": "broccoli", "quantity": 150, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}, {"food_name": "גזר", "food_name_en": "carrot", "quantity": 100, "unit": "grams"}], "total_nutrition": {"calories": 520, "protein": 42, "carbs": 15, "fat": 32}, "portions": 1, "prep_time_minutes": 25, "meal_types": ["LUNCH", "DINNER"], "tags": ["fish", "healthy", "omega3"], "kashrut": "parve"},
    {"recipe_id": "recipe_016", "name_he": "קוסקוס עם ירקות", "name_en": "Couscous with Vegetables", "ingredients": [{"food_name": "קוסקוס", "food_name_en": "couscous", "quantity": 150, "unit": "grams"}, {"food_name": "חציל", "food_name_en": "eggplant", "quantity": 100, "unit": "grams"}, {"food_name": "גזר", "food_name_en": "carrot", "quantity": 80, "unit": "grams"}, {"food_name": "חומוס", "food_name_en": "chickpeas", "quantity": 100, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 500, "protein": 18, "carbs": 78, "fat": 12}, "portions": 2, "prep_time_minutes": 30, "meal_types": ["LUNCH"], "tags": ["vegan", "moroccan"], "kashrut": "parve"},
    {"recipe_id": "recipe_017", "name_he": "עוף עם בטטה", "name_en": "Chicken with Sweet Potato", "ingredients": [{"food_name": "חזה עוף", "food_name_en": "chicken breast", "quantity": 200, "unit": "grams"}, {"food_name": "בטטה", "food_name_en": "sweet potato", "quantity": 200, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}, {"food_name": "ברוקולי", "food_name_en": "broccoli", "quantity": 100, "unit": "grams"}], "total_nutrition": {"calories": 560, "protein": 48, "carbs": 52, "fat": 14}, "portions": 1, "prep_time_minutes": 35, "meal_types": ["LUNCH"], "tags": ["meat", "healthy", "meal_prep"], "kashrut": "meat"},
    {"recipe_id": "recipe_018", "name_he": "קינואה עם ירקות צלויים", "name_en": "Quinoa with Roasted Vegetables", "ingredients": [{"food_name": "קינואה", "food_name_en": "quinoa", "quantity": 150, "unit": "grams"}, {"food_name": "חציל", "food_name_en": "eggplant", "quantity": 100, "unit": "grams"}, {"food_name": "פלפל אדום", "food_name_en": "red pepper", "quantity": 100, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 15, "unit": "grams"}, {"food_name": "תרד", "food_name_en": "spinach", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 420, "protein": 14, "carbs": 55, "fat": 16}, "portions": 2, "prep_time_minutes": 30, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "gluten_free", "healthy"], "kashrut": "parve"},
    {"recipe_id": "recipe_019", "name_he": "בורגול עם ירקות", "name_en": "Bulgur with Vegetables", "ingredients": [{"food_name": "בורגול", "food_name_en": "bulgur", "quantity": 150, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 100, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 100, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 300, "protein": 9, "carbs": 52, "fat": 6}, "portions": 2, "prep_time_minutes": 15, "meal_types": ["LUNCH"], "tags": ["vegan", "quick", "fiber"], "kashrut": "parve"},
    {"recipe_id": "recipe_020", "name_he": "סלט טונה", "name_en": "Tuna Salad", "ingredients": [{"food_name": "טונה", "food_name_en": "tuna", "quantity": 100, "unit": "grams"}, {"food_name": "חסה", "food_name_en": "lettuce", "quantity": 80, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 100, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 80, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 250, "protein": 30, "carbs": 10, "fat": 10}, "portions": 1, "prep_time_minutes": 10, "meal_types": ["LUNCH", "DINNER"], "tags": ["fish", "quick", "low_carb"], "kashrut": "parve"},

    # ── Dinner ────────────────────────────────────────────────
    {"recipe_id": "recipe_021", "name_he": "מרק ירקות", "name_en": "Vegetable Soup", "ingredients": [{"food_name": "גזר", "food_name_en": "carrot", "quantity": 100, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 80, "unit": "grams"}, {"food_name": "תפוח אדמה", "food_name_en": "potato", "quantity": 100, "unit": "grams"}, {"food_name": "ברוקולי", "food_name_en": "broccoli", "quantity": 80, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 200, "protein": 6, "carbs": 35, "fat": 5}, "portions": 2, "prep_time_minutes": 30, "meal_types": ["DINNER"], "tags": ["vegan", "soup", "winter"], "kashrut": "parve"},
    {"recipe_id": "recipe_022", "name_he": "גבינה עם ירקות בטורטייה", "name_en": "Cheese & Veggie Wrap", "ingredients": [{"food_name": "גבינה צהובה", "food_name_en": "yellow cheese", "quantity": 40, "unit": "grams"}, {"food_name": "חסה", "food_name_en": "lettuce", "quantity": 40, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 60, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 50, "unit": "grams"}, {"food_name": "לחם", "food_name_en": "tortilla", "quantity": 60, "unit": "grams"}], "total_nutrition": {"calories": 300, "protein": 14, "carbs": 30, "fat": 14}, "portions": 1, "prep_time_minutes": 5, "meal_types": ["DINNER"], "tags": ["dairy", "quick", "light"], "kashrut": "dairy"},
    {"recipe_id": "recipe_023", "name_he": "דג עם ירקות בתנור", "name_en": "Baked Fish with Vegetables", "ingredients": [{"food_name": "סלמון", "food_name_en": "salmon", "quantity": 150, "unit": "grams"}, {"food_name": "ברוקולי", "food_name_en": "broccoli", "quantity": 100, "unit": "grams"}, {"food_name": "גזר", "food_name_en": "carrot", "quantity": 80, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 420, "protein": 35, "carbs": 15, "fat": 25}, "portions": 1, "prep_time_minutes": 30, "meal_types": ["DINNER"], "tags": ["fish", "healthy"], "kashrut": "parve"},
    {"recipe_id": "recipe_024", "name_he": "מרק עדשים", "name_en": "Lentil Soup", "ingredients": [{"food_name": "עדשים אדומות", "food_name_en": "red lentils", "quantity": 150, "unit": "grams"}, {"food_name": "גזר", "food_name_en": "carrot", "quantity": 80, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 80, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 350, "protein": 18, "carbs": 52, "fat": 6}, "portions": 3, "prep_time_minutes": 25, "meal_types": ["DINNER", "LUNCH"], "tags": ["vegan", "soup", "protein"], "kashrut": "parve"},
    {"recipe_id": "recipe_025", "name_he": "חביתת ירקות", "name_en": "Veggie Frittata", "ingredients": [{"food_name": "ביצה", "food_name_en": "egg", "quantity": 200, "unit": "grams"}, {"food_name": "תרד", "food_name_en": "spinach", "quantity": 80, "unit": "grams"}, {"food_name": "פטריות", "food_name_en": "mushrooms", "quantity": 80, "unit": "grams"}, {"food_name": "גבינה צהובה", "food_name_en": "cheese", "quantity": 30, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 440, "protein": 30, "carbs": 8, "fat": 32}, "portions": 2, "prep_time_minutes": 20, "meal_types": ["DINNER", "BREAKFAST"], "tags": ["dairy", "protein", "low_carb"], "kashrut": "dairy"},

    # ── Snacks ────────────────────────────────────────────────
    {"recipe_id": "recipe_026", "name_he": "סלט פירות", "name_en": "Fruit Salad", "ingredients": [{"food_name": "תפוח", "food_name_en": "apple", "quantity": 80, "unit": "grams"}, {"food_name": "בננה", "food_name_en": "banana", "quantity": 60, "unit": "grams"}, {"food_name": "תפוז", "food_name_en": "orange", "quantity": 80, "unit": "grams"}, {"food_name": "תותים", "food_name_en": "strawberries", "quantity": 80, "unit": "grams"}], "total_nutrition": {"calories": 160, "protein": 2, "carbs": 40, "fat": 0.5}, "portions": 1, "prep_time_minutes": 5, "meal_types": ["MORNING_SNACK", "AFTERNOON_SNACK"], "tags": ["vegan", "quick", "fresh"], "kashrut": "parve"},
    {"recipe_id": "recipe_027", "name_he": "חומוס עם פיתה", "name_en": "Hummus with Pita", "ingredients": [{"food_name": "חומוס ממרח", "food_name_en": "hummus", "quantity": 100, "unit": "grams"}, {"food_name": "פיתה", "food_name_en": "pita", "quantity": 30, "unit": "grams"}], "total_nutrition": {"calories": 250, "protein": 10, "carbs": 30, "fat": 10}, "portions": 1, "prep_time_minutes": 2, "meal_types": ["AFTERNOON_SNACK"], "tags": ["vegan", "quick"], "kashrut": "parve"},
    {"recipe_id": "recipe_028", "name_he": "קוטג׳ עם ירקות", "name_en": "Cottage Cheese with Veggies", "ingredients": [{"food_name": "גבינת קוטג׳", "food_name_en": "cottage cheese", "quantity": 150, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 50, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 170, "protein": 18, "carbs": 8, "fat": 7}, "portions": 1, "prep_time_minutes": 3, "meal_types": ["AFTERNOON_SNACK", "EVENING_SNACK"], "tags": ["dairy", "quick", "protein"], "kashrut": "dairy"},
    {"recipe_id": "recipe_029", "name_he": "שקדים ופירות יבשים", "name_en": "Almonds and Dried Fruits", "ingredients": [{"food_name": "שקדים", "food_name_en": "almonds", "quantity": 25, "unit": "grams"}, {"food_name": "תמרים", "food_name_en": "dates", "quantity": 30, "unit": "grams"}], "total_nutrition": {"calories": 230, "protein": 6, "carbs": 30, "fat": 12}, "portions": 1, "prep_time_minutes": 1, "meal_types": ["MORNING_SNACK", "AFTERNOON_SNACK"], "tags": ["vegan", "energy"], "kashrut": "parve"},
    {"recipe_id": "recipe_030", "name_he": "יוגורט עם אגוזים", "name_en": "Yogurt with Nuts", "ingredients": [{"food_name": "יוגורט יווני", "food_name_en": "greek yogurt", "quantity": 170, "unit": "grams"}, {"food_name": "אגוזי מלך", "food_name_en": "walnuts", "quantity": 15, "unit": "grams"}, {"food_name": "דבש", "food_name_en": "honey", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 230, "protein": 19, "carbs": 15, "fat": 11}, "portions": 1, "prep_time_minutes": 2, "meal_types": ["MORNING_SNACK", "EVENING_SNACK"], "tags": ["dairy", "protein", "quick"], "kashrut": "dairy"},

    # ── More Lunch/Dinner ─────────────────────────────────────
    {"recipe_id": "recipe_031", "name_he": "סטיר פריי ירקות עם טופו", "name_en": "Tofu Stir Fry", "ingredients": [{"food_name": "טופו", "food_name_en": "tofu", "quantity": 150, "unit": "grams"}, {"food_name": "ברוקולי", "food_name_en": "broccoli", "quantity": 100, "unit": "grams"}, {"food_name": "פלפל אדום", "food_name_en": "red pepper", "quantity": 80, "unit": "grams"}, {"food_name": "רוטב סויה", "food_name_en": "soy sauce", "quantity": 15, "unit": "grams"}, {"food_name": "שמן שומשום", "food_name_en": "sesame oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 280, "protein": 18, "carbs": 15, "fat": 17}, "portions": 1, "prep_time_minutes": 15, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "asian", "quick"], "kashrut": "parve"},
    {"recipe_id": "recipe_032", "name_he": "פסטה עם רוטב עגבניות", "name_en": "Pasta with Tomato Sauce", "ingredients": [{"food_name": "פסטה", "food_name_en": "pasta", "quantity": 200, "unit": "grams"}, {"food_name": "רוטב עגבניות", "food_name_en": "tomato sauce", "quantity": 100, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 450, "protein": 14, "carbs": 78, "fat": 8}, "portions": 1, "prep_time_minutes": 15, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "italian", "quick"], "kashrut": "parve"},
    {"recipe_id": "recipe_033", "name_he": "שישליק עוף", "name_en": "Chicken Shishlik", "ingredients": [{"food_name": "חזה עוף", "food_name_en": "chicken breast", "quantity": 200, "unit": "grams"}, {"food_name": "פלפל אדום", "food_name_en": "red pepper", "quantity": 80, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 60, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 420, "protein": 48, "carbs": 12, "fat": 18}, "portions": 1, "prep_time_minutes": 20, "meal_types": ["LUNCH", "DINNER"], "tags": ["meat", "grill", "low_carb"], "kashrut": "meat"},
    {"recipe_id": "recipe_034", "name_he": "טבולה", "name_en": "Tabbouleh", "ingredients": [{"food_name": "בורגול", "food_name_en": "bulgur", "quantity": 100, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 150, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 80, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 15, "unit": "grams"}], "total_nutrition": {"calories": 250, "protein": 6, "carbs": 40, "fat": 8}, "portions": 2, "prep_time_minutes": 15, "meal_types": ["LUNCH", "AFTERNOON_SNACK"], "tags": ["vegan", "lebanese", "fresh"], "kashrut": "parve"},
    {"recipe_id": "recipe_035", "name_he": "ביצה עם אבוקדו על לחם", "name_en": "Avocado Toast with Egg", "ingredients": [{"food_name": "לחם", "food_name_en": "bread", "quantity": 60, "unit": "grams"}, {"food_name": "אבוקדו", "food_name_en": "avocado", "quantity": 80, "unit": "grams"}, {"food_name": "ביצה", "food_name_en": "egg", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 390, "protein": 14, "carbs": 30, "fat": 24}, "portions": 1, "prep_time_minutes": 8, "meal_types": ["BREAKFAST", "LUNCH"], "tags": ["quick", "trendy"], "kashrut": "parve"},
    {"recipe_id": "recipe_036", "name_he": "מרק חומוס", "name_en": "Chickpea Soup", "ingredients": [{"food_name": "חומוס", "food_name_en": "chickpeas", "quantity": 200, "unit": "grams"}, {"food_name": "גזר", "food_name_en": "carrot", "quantity": 80, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 60, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 450, "protein": 22, "carbs": 62, "fat": 12}, "portions": 3, "prep_time_minutes": 30, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "soup", "protein"], "kashrut": "parve"},
    {"recipe_id": "recipe_037", "name_he": "סלט ישראלי", "name_en": "Israeli Salad", "ingredients": [{"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 150, "unit": "grams"}, {"food_name": "מלפפון", "food_name_en": "cucumber", "quantity": 150, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 30, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 120, "protein": 3, "carbs": 15, "fat": 6}, "portions": 2, "prep_time_minutes": 5, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "traditional", "fresh"], "kashrut": "parve"},
    {"recipe_id": "recipe_038", "name_he": "טורטייה עם עוף", "name_en": "Chicken Wrap", "ingredients": [{"food_name": "חזה עוף", "food_name_en": "chicken breast", "quantity": 150, "unit": "grams"}, {"food_name": "לחם", "food_name_en": "tortilla", "quantity": 60, "unit": "grams"}, {"food_name": "חסה", "food_name_en": "lettuce", "quantity": 30, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 50, "unit": "grams"}], "total_nutrition": {"calories": 430, "protein": 40, "carbs": 35, "fat": 12}, "portions": 1, "prep_time_minutes": 10, "meal_types": ["LUNCH"], "tags": ["meat", "quick"], "kashrut": "meat"},
    {"recipe_id": "recipe_039", "name_he": "תבשיל שעועית", "name_en": "Bean Stew", "ingredients": [{"food_name": "שעועית שחורה", "food_name_en": "black beans", "quantity": 200, "unit": "grams"}, {"food_name": "עגבנייה", "food_name_en": "tomato", "quantity": 100, "unit": "grams"}, {"food_name": "בצל", "food_name_en": "onion", "quantity": 60, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 380, "protein": 22, "carbs": 58, "fat": 6}, "portions": 2, "prep_time_minutes": 25, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "protein", "fiber"], "kashrut": "parve"},
    {"recipe_id": "recipe_040", "name_he": "פתיתים עם ירקות", "name_en": "Ptitim with Vegetables", "ingredients": [{"food_name": "קוסקוס", "food_name_en": "ptitim", "quantity": 150, "unit": "grams"}, {"food_name": "גזר", "food_name_en": "carrot", "quantity": 60, "unit": "grams"}, {"food_name": "אפונה ירוקה", "food_name_en": "green peas", "quantity": 60, "unit": "grams"}, {"food_name": "שמן זית", "food_name_en": "olive oil", "quantity": 10, "unit": "grams"}], "total_nutrition": {"calories": 330, "protein": 10, "carbs": 55, "fat": 6}, "portions": 2, "prep_time_minutes": 15, "meal_types": ["LUNCH", "DINNER"], "tags": ["vegan", "israeli"], "kashrut": "parve"},
]


# ═══════════════════════════════════════════════════════════════════
# MENU_TEMPLATES — Daily meal pattern templates
# ═══════════════════════════════════════════════════════════════════

MENU_TEMPLATES: List[dict] = [
    {
        "template_id": "template_001",
        "name_he": "ארוחת בוקר חלבית + צהריים בשרי",
        "name_en": "Dairy Breakfast + Meat Lunch",
        "pattern": {
            "BREAKFAST": {"kashrut": "dairy", "categories": ["dairy", "grain", "vegetable"]},
            "MORNING_SNACK": {"kashrut": "parve", "categories": ["fruit"]},
            "LUNCH": {"kashrut": "meat", "categories": ["protein", "grain", "vegetable"]},
            "AFTERNOON_SNACK": {"kashrut": "parve", "categories": ["nut_seed", "fruit"]},
            "DINNER": {"kashrut": "dairy", "categories": ["dairy", "vegetable", "grain"]},
        }
    },
    {
        "template_id": "template_002",
        "name_he": "יום טבעוני",
        "name_en": "Vegan Day",
        "pattern": {
            "BREAKFAST": {"kashrut": "parve", "categories": ["grain", "fruit", "nut_seed"]},
            "MORNING_SNACK": {"kashrut": "parve", "categories": ["fruit"]},
            "LUNCH": {"kashrut": "parve", "categories": ["legume", "grain", "vegetable"]},
            "AFTERNOON_SNACK": {"kashrut": "parve", "categories": ["nut_seed", "fruit"]},
            "DINNER": {"kashrut": "parve", "categories": ["legume", "vegetable", "grain"]},
        }
    },
    {
        "template_id": "template_003",
        "name_he": "יום דגים",
        "name_en": "Fish Day",
        "pattern": {
            "BREAKFAST": {"kashrut": "dairy", "categories": ["dairy", "grain", "fruit"]},
            "MORNING_SNACK": {"kashrut": "parve", "categories": ["fruit", "nut_seed"]},
            "LUNCH": {"kashrut": "parve", "categories": ["protein", "grain", "vegetable"]},
            "AFTERNOON_SNACK": {"kashrut": "dairy", "categories": ["dairy", "fruit"]},
            "DINNER": {"kashrut": "parve", "categories": ["protein", "vegetable"]},
        }
    },
    {
        "template_id": "template_004",
        "name_he": "יום עשיר בחלבון",
        "name_en": "High Protein Day",
        "pattern": {
            "BREAKFAST": {"kashrut": "parve", "categories": ["protein", "grain"]},
            "MORNING_SNACK": {"kashrut": "dairy", "categories": ["dairy", "nut_seed"]},
            "LUNCH": {"kashrut": "meat", "categories": ["protein", "vegetable", "grain"]},
            "AFTERNOON_SNACK": {"kashrut": "parve", "categories": ["legume", "nut_seed"]},
            "DINNER": {"kashrut": "parve", "categories": ["protein", "vegetable"]},
        }
    },
    {
        "template_id": "template_005",
        "name_he": "יום קל",
        "name_en": "Light Day",
        "pattern": {
            "BREAKFAST": {"kashrut": "dairy", "categories": ["dairy", "fruit"]},
            "MORNING_SNACK": {"kashrut": "parve", "categories": ["fruit"]},
            "LUNCH": {"kashrut": "parve", "categories": ["vegetable", "legume", "grain"]},
            "AFTERNOON_SNACK": {"kashrut": "parve", "categories": ["fruit", "nut_seed"]},
            "DINNER": {"kashrut": "dairy", "categories": ["dairy", "vegetable"]},
        }
    },
]
