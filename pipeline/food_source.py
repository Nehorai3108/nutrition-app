"""
Food data sources for the ingestion pipeline.

Primary:   Curated dataset of 50 common Israeli/Mediterranean foods.
Secondary: Open Food Facts API (optional, network-dependent, graceful fallback).
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional
from pipeline.food_library import EXTENDED_FOODS
from pipeline.food_library_2 import EXTENDED_FOODS_2
from pipeline.food_library_3 import EXTENDED_FOODS_3
from pipeline.food_library_4 import EXTENDED_FOODS_4
from pipeline.food_library_5 import EXTENDED_FOODS_5


# ─── Curated Dataset ─────────────────────────────────────────────────────────
# IDs food_001–food_010 match the existing FoodCatalog to avoid conflicts.
# IDs food_011–food_050 are new additions.

CURATED_FOODS: List[Dict] = [
    # ── PROTEIN ──────────────────────────────────────────────────────────────
    {
        "food_id": "food_001", "name_he": "חזה עוף", "name_en": "Chicken Breast",
        "category": "protein",
        "calories_kcal": 165.0, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6,
        "fiber_g": 0.0, "default_serving_g": 150.0,
        "aliases_he": ["עוף", "חזה", "פילה עוף"],
        "aliases_en": ["chicken", "breast", "chicken fillet"],
        "source": "curated",
    },
    {
        "food_id": "food_003", "name_he": "ביצה", "name_en": "Egg",
        "category": "protein",
        "calories_kcal": 155.0, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0,
        "default_unit": "unit", "default_serving_g": 50.0,
        "aliases_he": ["ביצים", "ביצה קשה", "ביצה רכה"],
        "aliases_en": ["eggs", "boiled egg", "hard boiled egg"],
        "source": "curated",
    },
    {
        "food_id": "food_011", "name_he": "טונה בשימורים", "name_en": "Canned Tuna",
        "category": "protein",
        "calories_kcal": 116.0, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 1.0,
        "default_serving_g": 85.0,
        "aliases_he": ["טונה", "דג טונה"],
        "aliases_en": ["tuna", "tuna fish"],
        "source": "curated",
    },
    {
        "food_id": "food_012", "name_he": "סלמון", "name_en": "Salmon",
        "category": "protein",
        "calories_kcal": 208.0, "protein_g": 20.0, "carbs_g": 0.0, "fat_g": 13.0,
        "default_serving_g": 150.0,
        "aliases_he": ["דג סלמון", "פילה סלמון"],
        "aliases_en": ["salmon fillet", "atlantic salmon"],
        "source": "curated",
    },
    {
        "food_id": "food_013", "name_he": "חזה הודו", "name_en": "Turkey Breast",
        "category": "protein",
        "calories_kcal": 135.0, "protein_g": 30.0, "carbs_g": 0.0, "fat_g": 1.0,
        "default_serving_g": 150.0,
        "aliases_he": ["הודו", "פילה הודו", "שניצל הודו"],
        "aliases_en": ["turkey", "turkey fillet"],
        "source": "curated",
    },
    {
        "food_id": "food_014", "name_he": "בשר בקר רזה", "name_en": "Lean Ground Beef",
        "category": "protein",
        "calories_kcal": 215.0, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 12.0,
        "default_serving_g": 150.0,
        "aliases_he": ["בקר", "בשר טחון", "המבורגר"],
        "aliases_en": ["beef", "ground beef", "hamburger"],
        "source": "curated",
    },
    # ── DAIRY ─────────────────────────────────────────────────────────────────
    {
        "food_id": "food_010", "name_he": "גבינת קוטג׳", "name_en": "Cottage Cheese",
        "category": "dairy",
        "calories_kcal": 98.0, "protein_g": 11.0, "carbs_g": 3.4, "fat_g": 4.3,
        "default_serving_g": 100.0,
        "aliases_he": ["קוטג", "קוטג׳", "גבינה לבנה"],
        "aliases_en": ["cottage", "cottage cheese 5%"],
        "source": "curated",
    },
    {
        "food_id": "food_006", "name_he": "חלב", "name_en": "Milk 1%",
        "category": "dairy",
        "calories_kcal": 42.0, "protein_g": 3.4, "carbs_g": 5.0, "fat_g": 1.0,
        "default_unit": "cup", "default_serving_g": 250.0,
        "aliases_he": ["חלב רגיל", "חלב 1%"],
        "aliases_en": ["milk", "low fat milk"],
        "source": "curated",
    },
    {
        "food_id": "food_015", "name_he": "יוגורט יווני", "name_en": "Greek Yogurt",
        "category": "dairy",
        "calories_kcal": 59.0, "protein_g": 10.0, "carbs_g": 3.6, "fat_g": 0.4,
        "default_serving_g": 150.0,
        "aliases_he": ["יוגורט", "יוגורט 0%", "לבן"],
        "aliases_en": ["yogurt", "greek yogurt 0%", "plain yogurt"],
        "source": "curated",
    },
    {
        "food_id": "food_016", "name_he": "גבינה צהובה", "name_en": "Yellow Cheese",
        "category": "dairy",
        "calories_kcal": 400.0, "protein_g": 25.0, "carbs_g": 1.0, "fat_g": 33.0,
        "default_unit": "slice", "default_serving_g": 20.0,
        "aliases_he": ["גבינה", "גבינה עמוקה"],
        "aliases_en": ["cheese", "cheddar", "gouda"],
        "source": "curated",
    },
    {
        "food_id": "food_017", "name_he": "גבינה לבנה 5%", "name_en": "White Cheese 5%",
        "category": "dairy",
        "calories_kcal": 113.0, "protein_g": 8.0, "carbs_g": 3.5, "fat_g": 7.5,
        "default_serving_g": 100.0,
        "aliases_he": ["גבינה לבנה", "גבינת שמנת"],
        "aliases_en": ["white cheese", "soft cheese", "cream cheese"],
        "source": "curated",
    },
    # ── GRAIN ─────────────────────────────────────────────────────────────────
    {
        "food_id": "food_002", "name_he": "אורז לבן", "name_en": "White Rice",
        "category": "grain",
        "calories_kcal": 130.0, "protein_g": 2.7, "carbs_g": 28.0, "fat_g": 0.3,
        "fiber_g": 0.4, "default_serving_g": 150.0,
        "aliases_he": ["אורז", "אורז מבושל"],
        "aliases_en": ["rice", "cooked rice", "steamed rice"],
        "source": "curated",
    },
    {
        "food_id": "food_007", "name_he": "לחם מחיטה מלאה", "name_en": "Whole Wheat Bread",
        "category": "grain",
        "calories_kcal": 247.0, "protein_g": 13.0, "carbs_g": 41.0, "fat_g": 3.4,
        "fiber_g": 7.0, "default_unit": "slice", "default_serving_g": 30.0,
        "aliases_he": ["לחם", "לחם מלא", "פרוסת לחם"],
        "aliases_en": ["bread", "whole wheat", "wheat bread"],
        "source": "curated",
    },
    {
        "food_id": "food_018", "name_he": "קינואה", "name_en": "Quinoa",
        "category": "grain",
        "calories_kcal": 120.0, "protein_g": 4.4, "carbs_g": 21.0, "fat_g": 1.9,
        "fiber_g": 2.8, "default_serving_g": 100.0,
        "aliases_he": ["קינואה מבושלת"],
        "aliases_en": ["cooked quinoa"],
        "source": "curated",
    },
    {
        "food_id": "food_019", "name_he": "שיבולת שועל", "name_en": "Oatmeal",
        "category": "grain",
        "calories_kcal": 389.0, "protein_g": 17.0, "carbs_g": 66.0, "fat_g": 7.0,
        "fiber_g": 10.0, "default_serving_g": 50.0,
        "aliases_he": ["קוורקר", "דייסת שיבולת שועל", "אוטמיל"],
        "aliases_en": ["oats", "rolled oats", "porridge"],
        "source": "curated",
    },
    {
        "food_id": "food_020", "name_he": "פסטה מחיטה מלאה", "name_en": "Whole Wheat Pasta",
        "category": "grain",
        "calories_kcal": 131.0, "protein_g": 5.0, "carbs_g": 25.0, "fat_g": 1.1,
        "fiber_g": 3.2, "default_serving_g": 180.0,
        "aliases_he": ["פסטה", "ספגטי", "מקרוני"],
        "aliases_en": ["pasta", "spaghetti", "macaroni"],
        "source": "curated",
    },
    {
        "food_id": "food_021", "name_he": "פיתה", "name_en": "Pita Bread",
        "category": "grain",
        "calories_kcal": 275.0, "protein_g": 9.0, "carbs_g": 55.0, "fat_g": 1.2,
        "fiber_g": 2.5, "default_unit": "unit", "default_serving_g": 60.0,
        "aliases_he": ["לחם פיתה", "פיתה מחיטה מלאה"],
        "aliases_en": ["pita", "flatbread"],
        "source": "curated",
    },
    # ── VEGETABLE ─────────────────────────────────────────────────────────────
    {
        "food_id": "food_008", "name_he": "עגבנייה", "name_en": "Tomato",
        "category": "vegetable",
        "calories_kcal": 18.0, "protein_g": 0.9, "carbs_g": 3.9, "fat_g": 0.2,
        "fiber_g": 1.2, "default_unit": "unit", "default_serving_g": 120.0,
        "aliases_he": ["עגבניות", "עגבניה"],
        "aliases_en": ["tomatoes"],
        "source": "curated",
    },
    {
        "food_id": "food_009", "name_he": "מלפפון", "name_en": "Cucumber",
        "category": "vegetable",
        "calories_kcal": 15.0, "protein_g": 0.7, "carbs_g": 3.6, "fat_g": 0.1,
        "fiber_g": 0.5, "default_unit": "unit", "default_serving_g": 100.0,
        "aliases_he": ["מלפפונים"],
        "aliases_en": ["cucumbers"],
        "source": "curated",
    },
    {
        "food_id": "food_022", "name_he": "פלפל אדום", "name_en": "Red Bell Pepper",
        "category": "vegetable",
        "calories_kcal": 31.0, "protein_g": 1.0, "carbs_g": 6.0, "fat_g": 0.3,
        "fiber_g": 2.1, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["פלפל", "פלפל צהוב", "פלפל ירוק"],
        "aliases_en": ["bell pepper", "capsicum", "pepper"],
        "source": "curated",
    },
    {
        "food_id": "food_023", "name_he": "ברוקולי", "name_en": "Broccoli",
        "category": "vegetable",
        "calories_kcal": 34.0, "protein_g": 2.8, "carbs_g": 6.6, "fat_g": 0.4,
        "fiber_g": 2.6, "default_serving_g": 150.0,
        "aliases_he": ["ברוקולי מאודה", "ברוקולי מבושל"],
        "aliases_en": ["steamed broccoli"],
        "source": "curated",
    },
    {
        "food_id": "food_024", "name_he": "תרד", "name_en": "Spinach",
        "category": "vegetable",
        "calories_kcal": 23.0, "protein_g": 2.9, "carbs_g": 3.6, "fat_g": 0.4,
        "fiber_g": 2.2, "default_serving_g": 100.0,
        "aliases_he": ["עלי תרד", "תרד טרי"],
        "aliases_en": ["baby spinach", "spinach leaves"],
        "source": "curated",
    },
    {
        "food_id": "food_025", "name_he": "גזר", "name_en": "Carrot",
        "category": "vegetable",
        "calories_kcal": 41.0, "protein_g": 0.9, "carbs_g": 10.0, "fat_g": 0.2,
        "fiber_g": 2.8, "default_unit": "unit", "default_serving_g": 80.0,
        "aliases_he": ["גזרים"],
        "aliases_en": ["carrots"],
        "source": "curated",
    },
    {
        "food_id": "food_026", "name_he": "בצל", "name_en": "Onion",
        "category": "vegetable",
        "calories_kcal": 40.0, "protein_g": 1.1, "carbs_g": 9.3, "fat_g": 0.1,
        "fiber_g": 1.7, "default_unit": "unit", "default_serving_g": 100.0,
        "aliases_he": ["בצל לבן", "בצל ירוק", "בצלצלים"],
        "aliases_en": ["onions", "white onion"],
        "source": "curated",
    },
    {
        "food_id": "food_027", "name_he": "פטריות", "name_en": "Mushrooms",
        "category": "vegetable",
        "calories_kcal": 22.0, "protein_g": 3.1, "carbs_g": 3.3, "fat_g": 0.3,
        "fiber_g": 1.0, "default_serving_g": 100.0,
        "aliases_he": ["פטריות שמפיניון", "פטריות מבושלות"],
        "aliases_en": ["champignons", "button mushrooms"],
        "source": "curated",
    },
    {
        "food_id": "food_028", "name_he": "חסה", "name_en": "Lettuce",
        "category": "vegetable",
        "calories_kcal": 15.0, "protein_g": 1.4, "carbs_g": 2.9, "fat_g": 0.2,
        "fiber_g": 1.3, "default_serving_g": 50.0,
        "aliases_he": ["חסה ירוקה", "חסה רומנה"],
        "aliases_en": ["romaine lettuce", "iceberg lettuce", "salad leaves"],
        "source": "curated",
    },
    # ── FRUIT ─────────────────────────────────────────────────────────────────
    {
        "food_id": "food_004", "name_he": "בננה", "name_en": "Banana",
        "category": "fruit",
        "calories_kcal": 89.0, "protein_g": 1.1, "carbs_g": 22.8, "fat_g": 0.3,
        "fiber_g": 2.6, "sugar_g": 12.2, "default_unit": "unit", "default_serving_g": 120.0,
        "aliases_he": ["בננות"],
        "aliases_en": ["bananas"],
        "source": "curated",
    },
    {
        "food_id": "food_029", "name_he": "תפוח", "name_en": "Apple",
        "category": "fruit",
        "calories_kcal": 52.0, "protein_g": 0.3, "carbs_g": 14.0, "fat_g": 0.2,
        "fiber_g": 2.4, "sugar_g": 10.3, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["תפוחים", "תפוח עץ"],
        "aliases_en": ["apples"],
        "source": "curated",
    },
    {
        "food_id": "food_030", "name_he": "תפוז", "name_en": "Orange",
        "category": "fruit",
        "calories_kcal": 47.0, "protein_g": 0.9, "carbs_g": 12.0, "fat_g": 0.1,
        "fiber_g": 2.4, "sugar_g": 9.4, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["תפוזים"],
        "aliases_en": ["oranges", "citrus"],
        "source": "curated",
    },
    {
        "food_id": "food_031", "name_he": "אבוקדו", "name_en": "Avocado",
        "category": "fruit",
        "calories_kcal": 160.0, "protein_g": 2.0, "carbs_g": 9.0, "fat_g": 15.0,
        "fiber_g": 6.7, "default_unit": "unit", "default_serving_g": 100.0,
        "aliases_he": ["אבוקדו בשל"],
        "aliases_en": ["avocados", "hass avocado"],
        "source": "curated",
    },
    {
        "food_id": "food_032", "name_he": "תות שדה", "name_en": "Strawberry",
        "category": "fruit",
        "calories_kcal": 32.0, "protein_g": 0.7, "carbs_g": 7.7, "fat_g": 0.3,
        "fiber_g": 2.0, "sugar_g": 4.9, "default_serving_g": 100.0,
        "aliases_he": ["תותים", "תות"],
        "aliases_en": ["strawberries"],
        "source": "curated",
    },
    {
        "food_id": "food_033", "name_he": "ענבים", "name_en": "Grapes",
        "category": "fruit",
        "calories_kcal": 67.0, "protein_g": 0.6, "carbs_g": 17.0, "fat_g": 0.4,
        "fiber_g": 0.9, "sugar_g": 16.3, "default_serving_g": 100.0,
        "aliases_he": ["ענבים ירוקים", "ענבים אדומים"],
        "aliases_en": ["grapes red", "grapes green"],
        "source": "curated",
    },
    # ── FAT ───────────────────────────────────────────────────────────────────
    {
        "food_id": "food_005", "name_he": "שמן זית", "name_en": "Olive Oil",
        "category": "fat",
        "calories_kcal": 884.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0,
        "default_unit": "tablespoon", "default_serving_g": 14.0,
        "aliases_he": ["שמן", "זית"],
        "aliases_en": ["oil", "olive"],
        "source": "curated",
    },
    {
        "food_id": "food_034", "name_he": "טחינה גולמית", "name_en": "Tahini",
        "category": "fat",
        "calories_kcal": 595.0, "protein_g": 17.0, "carbs_g": 21.0, "fat_g": 54.0,
        "fiber_g": 9.3, "default_unit": "tablespoon", "default_serving_g": 15.0,
        "aliases_he": ["טחינה", "עיסת שומשום"],
        "aliases_en": ["sesame paste", "raw tahini"],
        "source": "curated",
    },
    {
        "food_id": "food_035", "name_he": "אגוזי מלך", "name_en": "Walnuts",
        "category": "fat",
        "calories_kcal": 654.0, "protein_g": 15.0, "carbs_g": 14.0, "fat_g": 65.0,
        "fiber_g": 6.7, "default_serving_g": 30.0,
        "aliases_he": ["אגוזים"],
        "aliases_en": ["nuts", "walnuts"],
        "source": "curated",
    },
    {
        "food_id": "food_036", "name_he": "שקדים", "name_en": "Almonds",
        "category": "fat",
        "calories_kcal": 579.0, "protein_g": 21.0, "carbs_g": 22.0, "fat_g": 50.0,
        "fiber_g": 12.5, "default_serving_g": 30.0,
        "aliases_he": ["שקד"],
        "aliases_en": ["almond"],
        "source": "curated",
    },
    # ── LEGUME ────────────────────────────────────────────────────────────────
    {
        "food_id": "food_037", "name_he": "עדשים מבושלות", "name_en": "Cooked Lentils",
        "category": "legume",
        "calories_kcal": 116.0, "protein_g": 9.0, "carbs_g": 20.0, "fat_g": 0.4,
        "fiber_g": 7.9, "default_serving_g": 150.0,
        "aliases_he": ["עדשים", "עדשים כתומות", "עדשים ירוקות"],
        "aliases_en": ["lentils", "red lentils", "green lentils"],
        "source": "curated",
    },
    {
        "food_id": "food_038", "name_he": "חומוס מבושל", "name_en": "Cooked Chickpeas",
        "category": "legume",
        "calories_kcal": 164.0, "protein_g": 8.9, "carbs_g": 27.0, "fat_g": 2.6,
        "fiber_g": 7.6, "default_serving_g": 150.0,
        "aliases_he": ["גרגרי חומוס", "חומוס"],
        "aliases_en": ["chickpeas", "garbanzo beans"],
        "source": "curated",
    },
    {
        "food_id": "food_039", "name_he": "שעועית שחורה", "name_en": "Black Beans",
        "category": "legume",
        "calories_kcal": 127.0, "protein_g": 8.7, "carbs_g": 23.0, "fat_g": 0.5,
        "fiber_g": 8.7, "default_serving_g": 150.0,
        "aliases_he": ["שעועית"],
        "aliases_en": ["beans"],
        "source": "curated",
    },
    {
        "food_id": "food_040", "name_he": "אפונה ירוקה", "name_en": "Green Peas",
        "category": "legume",
        "calories_kcal": 81.0, "protein_g": 5.4, "carbs_g": 14.0, "fat_g": 0.4,
        "fiber_g": 5.1, "default_serving_g": 100.0,
        "aliases_he": ["אפונה", "אפונה קפואה"],
        "aliases_en": ["peas", "frozen peas"],
        "source": "curated",
    },
    # ── CONDIMENT ─────────────────────────────────────────────────────────────
    {
        "food_id": "food_041", "name_he": "ממרח חומוס", "name_en": "Hummus",
        "category": "condiment",
        "calories_kcal": 166.0, "protein_g": 7.9, "carbs_g": 14.0, "fat_g": 9.6,
        "fiber_g": 6.0, "default_unit": "tablespoon", "default_serving_g": 30.0,
        "aliases_he": ["חומוס ממרח", "חומוס עם טחינה"],
        "aliases_en": ["hummus dip", "hummus spread"],
        "source": "curated",
    },
    {
        "food_id": "food_042", "name_he": "מיונז", "name_en": "Mayonnaise",
        "category": "condiment",
        "calories_kcal": 680.0, "protein_g": 1.0, "carbs_g": 0.6, "fat_g": 75.0,
        "default_unit": "tablespoon", "default_serving_g": 15.0,
        "aliases_he": ["מיו", "רוטב לבן"],
        "aliases_en": ["mayo"],
        "source": "curated",
    },
    {
        "food_id": "food_048", "name_he": "דבש", "name_en": "Honey",
        "category": "condiment",
        "calories_kcal": 304.0, "protein_g": 0.3, "carbs_g": 82.0, "fat_g": 0.0,
        "sugar_g": 82.0, "default_unit": "teaspoon", "default_serving_g": 7.0,
        "aliases_he": ["דבש טבעי", "דבש צמחים"],
        "aliases_en": ["natural honey", "raw honey"],
        "source": "curated",
    },
    # ── NUT_SEED ──────────────────────────────────────────────────────────────
    {
        "food_id": "food_043", "name_he": "גרעיני חמנייה", "name_en": "Sunflower Seeds",
        "category": "nut_seed",
        "calories_kcal": 584.0, "protein_g": 21.0, "carbs_g": 20.0, "fat_g": 51.0,
        "fiber_g": 8.6, "default_serving_g": 30.0,
        "aliases_he": ["גרעינים", "גרעיני חמנייה קלויים"],
        "aliases_en": ["seeds", "sunflower seeds roasted"],
        "source": "curated",
    },
    {
        "food_id": "food_044", "name_he": "חמאת בוטנים", "name_en": "Peanut Butter",
        "category": "nut_seed",
        "calories_kcal": 598.0, "protein_g": 25.0, "carbs_g": 20.0, "fat_g": 50.0,
        "fiber_g": 6.0, "default_unit": "tablespoon", "default_serving_g": 32.0,
        "aliases_he": ["חמאת בוטנים טבעית"],
        "aliases_en": ["peanut butter natural", "pb"],
        "source": "curated",
    },
    # ── BEVERAGE ──────────────────────────────────────────────────────────────
    {
        "food_id": "food_045", "name_he": "קפה שחור", "name_en": "Black Coffee",
        "category": "beverage",
        "calories_kcal": 2.0, "protein_g": 0.3, "carbs_g": 0.0, "fat_g": 0.0,
        "default_unit": "cup", "default_serving_g": 240.0,
        "aliases_he": ["קפה", "אספרסו", "אמריקנו"],
        "aliases_en": ["coffee", "espresso", "americano"],
        "source": "curated",
    },
    {
        "food_id": "food_046", "name_he": "תה ירוק", "name_en": "Green Tea",
        "category": "beverage",
        "calories_kcal": 1.0, "protein_g": 0.0, "carbs_g": 0.3, "fat_g": 0.0,
        "default_unit": "cup", "default_serving_g": 240.0,
        "aliases_he": ["תה", "תה ירוק בתיקיות"],
        "aliases_en": ["tea", "herbal tea"],
        "source": "curated",
    },
    {
        "food_id": "food_050", "name_he": "חלב שקדים", "name_en": "Almond Milk",
        "category": "beverage",
        "calories_kcal": 17.0, "protein_g": 0.4, "carbs_g": 1.5, "fat_g": 1.1,
        "default_unit": "cup", "default_serving_g": 240.0,
        "aliases_he": ["חלב שקדים ללא סוכר", "חלב צמחי"],
        "aliases_en": ["almond milk unsweetened", "plant milk"],
        "source": "curated",
    },
    # ── OTHER ─────────────────────────────────────────────────────────────────
    {
        "food_id": "food_047", "name_he": "שוקולד מריר", "name_en": "Dark Chocolate",
        "category": "other",
        "calories_kcal": 546.0, "protein_g": 5.0, "carbs_g": 60.0, "fat_g": 31.0,
        "fiber_g": 7.0, "default_serving_g": 30.0,
        "aliases_he": ["שוקולד", "שוקולד 70%", "שוקולד 85%"],
        "aliases_en": ["chocolate", "dark chocolate 70%"],
        "source": "curated",
    },
    {
        "food_id": "food_049", "name_he": "שמן קוקוס", "name_en": "Coconut Oil",
        "category": "fat",
        "calories_kcal": 892.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 99.0,
        "default_unit": "tablespoon", "default_serving_g": 14.0,
        "aliases_he": ["שמן קוקוס גולמי"],
        "aliases_en": ["virgin coconut oil"],
        "source": "curated",
    },

    # ── PROTEIN (extended) ────────────────────────────────────────────────────
    {
        "food_id": "food_051", "name_he": "שרימפס", "name_en": "Shrimp",
        "category": "protein",
        "calories_kcal": 99.0, "protein_g": 24.0, "carbs_g": 0.2, "fat_g": 0.3,
        "default_serving_g": 100.0,
        "aliases_he": ["קריל", "שרימפ מבושל"],
        "aliases_en": ["prawns", "cooked shrimp"],
        "source": "curated",
    },
    {
        "food_id": "food_052", "name_he": "סרדינים", "name_en": "Sardines",
        "category": "protein",
        "calories_kcal": 208.0, "protein_g": 25.0, "carbs_g": 0.0, "fat_g": 11.0,
        "default_serving_g": 85.0,
        "aliases_he": ["סרדין", "סרדינים בשמן"],
        "aliases_en": ["sardine", "canned sardines"],
        "source": "curated",
    },
    {
        "food_id": "food_053", "name_he": "טופו", "name_en": "Tofu",
        "category": "protein",
        "calories_kcal": 76.0, "protein_g": 8.0, "carbs_g": 2.0, "fat_g": 4.0,
        "default_serving_g": 150.0,
        "aliases_he": ["גבינת סויה", "טופו קשה", "טופו רך"],
        "aliases_en": ["firm tofu", "soft tofu", "bean curd"],
        "source": "curated",
    },
    {
        "food_id": "food_054", "name_he": "בקלה", "name_en": "Cod Fish",
        "category": "protein",
        "calories_kcal": 82.0, "protein_g": 18.0, "carbs_g": 0.0, "fat_g": 0.7,
        "default_serving_g": 150.0,
        "aliases_he": ["דג בקלה", "פילה בקלה"],
        "aliases_en": ["cod fillet", "white fish"],
        "source": "curated",
    },
    {
        "food_id": "food_055", "name_he": "כבש", "name_en": "Lamb",
        "category": "protein",
        "calories_kcal": 258.0, "protein_g": 25.0, "carbs_g": 0.0, "fat_g": 17.0,
        "default_serving_g": 150.0,
        "aliases_he": ["בשר כבש", "כבש טחון", "טלה"],
        "aliases_en": ["ground lamb", "lamb chop"],
        "source": "curated",
    },
    {
        "food_id": "food_056", "name_he": "חלבון ביצה", "name_en": "Egg White",
        "category": "protein",
        "calories_kcal": 52.0, "protein_g": 11.0, "carbs_g": 0.7, "fat_g": 0.2,
        "default_unit": "unit", "default_serving_g": 33.0,
        "aliases_he": ["חלבונים", "לבן ביצה"],
        "aliases_en": ["egg whites", "albumen"],
        "source": "curated",
    },

    # ── DAIRY (extended) ──────────────────────────────────────────────────────
    {
        "food_id": "food_057", "name_he": "לאבנה", "name_en": "Labneh",
        "category": "dairy",
        "calories_kcal": 150.0, "protein_g": 6.0, "carbs_g": 4.0, "fat_g": 12.0,
        "default_serving_g": 80.0,
        "aliases_he": ["לבנה", "גבינת לבנה עזים"],
        "aliases_en": ["labane", "strained yogurt", "yogurt cheese"],
        "source": "curated",
    },
    {
        "food_id": "food_058", "name_he": "גבינת פטה", "name_en": "Feta Cheese",
        "category": "dairy",
        "calories_kcal": 264.0, "protein_g": 14.0, "carbs_g": 4.0, "fat_g": 21.0,
        "default_serving_g": 40.0,
        "aliases_he": ["פטה", "גבינה יוונית"],
        "aliases_en": ["feta", "greek cheese"],
        "source": "curated",
    },
    {
        "food_id": "food_059", "name_he": "חמאה", "name_en": "Butter",
        "category": "dairy",
        "calories_kcal": 717.0, "protein_g": 0.9, "carbs_g": 0.1, "fat_g": 81.0,
        "default_unit": "tablespoon", "default_serving_g": 14.0,
        "aliases_he": ["חמאה רגילה", "חמאה מלוחה"],
        "aliases_en": ["unsalted butter", "salted butter"],
        "source": "curated",
    },
    {
        "food_id": "food_060", "name_he": "שמנת חמוצה", "name_en": "Sour Cream",
        "category": "dairy",
        "calories_kcal": 198.0, "protein_g": 3.0, "carbs_g": 4.6, "fat_g": 19.0,
        "default_unit": "tablespoon", "default_serving_g": 30.0,
        "aliases_he": ["שמנת", "שמנת 15%"],
        "aliases_en": ["cream", "creme fraiche"],
        "source": "curated",
    },
    {
        "food_id": "food_061", "name_he": "גבינה בולגרית", "name_en": "Bulgarian Cheese",
        "category": "dairy",
        "calories_kcal": 280.0, "protein_g": 18.0, "carbs_g": 1.0, "fat_g": 23.0,
        "default_serving_g": 40.0,
        "aliases_he": ["גבינה מלוחה", "גבינה בולגרית 5%"],
        "aliases_en": ["salty cheese", "brined cheese"],
        "source": "curated",
    },

    # ── GRAIN (extended) ──────────────────────────────────────────────────────
    {
        "food_id": "food_062", "name_he": "אורז מלא", "name_en": "Brown Rice",
        "category": "grain",
        "calories_kcal": 123.0, "protein_g": 2.7, "carbs_g": 26.0, "fat_g": 1.0,
        "fiber_g": 1.8, "default_serving_g": 150.0,
        "aliases_he": ["אורז חום", "אורז מחיטה מלאה"],
        "aliases_en": ["brown rice cooked", "whole grain rice"],
        "source": "curated",
    },
    {
        "food_id": "food_063", "name_he": "קוסקוס", "name_en": "Couscous",
        "category": "grain",
        "calories_kcal": 112.0, "protein_g": 3.8, "carbs_g": 23.0, "fat_g": 0.2,
        "fiber_g": 1.4, "default_serving_g": 150.0,
        "aliases_he": ["קוסקוס מבושל"],
        "aliases_en": ["cooked couscous"],
        "source": "curated",
    },
    {
        "food_id": "food_064", "name_he": "בורגול", "name_en": "Bulgur",
        "category": "grain",
        "calories_kcal": 83.0, "protein_g": 3.1, "carbs_g": 18.6, "fat_g": 0.2,
        "fiber_g": 4.5, "default_serving_g": 150.0,
        "aliases_he": ["בולגור", "חיטה גרוסה"],
        "aliases_en": ["bulgur wheat", "cracked wheat"],
        "source": "curated",
    },
    {
        "food_id": "food_065", "name_he": "כוסמת", "name_en": "Buckwheat",
        "category": "grain",
        "calories_kcal": 92.0, "protein_g": 3.4, "carbs_g": 20.0, "fat_g": 0.6,
        "fiber_g": 2.7, "default_serving_g": 150.0,
        "aliases_he": ["קשה כוסמת"],
        "aliases_en": ["buckwheat groats", "kasha"],
        "source": "curated",
    },
    {
        "food_id": "food_066", "name_he": "לחם קל", "name_en": "Crispbread",
        "category": "grain",
        "calories_kcal": 335.0, "protein_g": 10.0, "carbs_g": 72.0, "fat_g": 1.5,
        "fiber_g": 12.0, "default_unit": "slice", "default_serving_g": 10.0,
        "aliases_he": ["קרקר", "קרקרים", "לחם כוסמין"],
        "aliases_en": ["crackers", "rice cake", "ryvita"],
        "source": "curated",
    },
    {
        "food_id": "food_067", "name_he": "פנקייק", "name_en": "Pancake",
        "category": "grain",
        "calories_kcal": 227.0, "protein_g": 6.0, "carbs_g": 38.0, "fat_g": 6.3,
        "default_unit": "unit", "default_serving_g": 70.0,
        "aliases_he": ["פנקייק תוצרת בית"],
        "aliases_en": ["homemade pancake", "hotcake"],
        "source": "curated",
    },

    # ── VEGETABLE (extended) ──────────────────────────────────────────────────
    {
        "food_id": "food_068", "name_he": "חציל", "name_en": "Eggplant",
        "category": "vegetable",
        "calories_kcal": 25.0, "protein_g": 1.0, "carbs_g": 6.0, "fat_g": 0.2,
        "fiber_g": 3.0, "default_unit": "unit", "default_serving_g": 200.0,
        "aliases_he": ["חצילים", "חציל צלוי", "בבגנוש"],
        "aliases_en": ["aubergine", "eggplant grilled"],
        "source": "curated",
    },
    {
        "food_id": "food_069", "name_he": "קישואים", "name_en": "Zucchini",
        "category": "vegetable",
        "calories_kcal": 17.0, "protein_g": 1.2, "carbs_g": 3.1, "fat_g": 0.3,
        "fiber_g": 1.0, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["קישוא", "זוקיני"],
        "aliases_en": ["courgette", "summer squash"],
        "source": "curated",
    },
    {
        "food_id": "food_070", "name_he": "כרובית", "name_en": "Cauliflower",
        "category": "vegetable",
        "calories_kcal": 25.0, "protein_g": 1.9, "carbs_g": 5.0, "fat_g": 0.3,
        "fiber_g": 2.0, "default_serving_g": 150.0,
        "aliases_he": ["כרובית מאודה", "כרובית מבושלת"],
        "aliases_en": ["steamed cauliflower"],
        "source": "curated",
    },
    {
        "food_id": "food_071", "name_he": "בטטה", "name_en": "Sweet Potato",
        "category": "vegetable",
        "calories_kcal": 86.0, "protein_g": 1.6, "carbs_g": 20.0, "fat_g": 0.1,
        "fiber_g": 3.0, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["בטטות", "תפוח אדמה מתוק"],
        "aliases_en": ["sweet potato baked", "yam"],
        "source": "curated",
    },
    {
        "food_id": "food_072", "name_he": "תירס", "name_en": "Corn",
        "category": "vegetable",
        "calories_kcal": 86.0, "protein_g": 3.3, "carbs_g": 19.0, "fat_g": 1.4,
        "fiber_g": 2.0, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["תירס מבושל", "תירס קפוא", "גרגרי תירס"],
        "aliases_en": ["sweet corn", "corn kernels", "corn on the cob"],
        "source": "curated",
    },
    {
        "food_id": "food_073", "name_he": "שום", "name_en": "Garlic",
        "category": "vegetable",
        "calories_kcal": 149.0, "protein_g": 6.4, "carbs_g": 33.0, "fat_g": 0.5,
        "fiber_g": 2.1, "default_unit": "unit", "default_serving_g": 5.0,
        "aliases_he": ["שיני שום", "שום קצוץ"],
        "aliases_en": ["garlic clove", "minced garlic"],
        "source": "curated",
    },
    {
        "food_id": "food_074", "name_he": "כרוב", "name_en": "Cabbage",
        "category": "vegetable",
        "calories_kcal": 25.0, "protein_g": 1.3, "carbs_g": 5.8, "fat_g": 0.1,
        "fiber_g": 2.5, "default_serving_g": 100.0,
        "aliases_he": ["כרוב לבן", "כרוב סגול"],
        "aliases_en": ["white cabbage", "red cabbage"],
        "source": "curated",
    },
    {
        "food_id": "food_075", "name_he": "אספרגוס", "name_en": "Asparagus",
        "category": "vegetable",
        "calories_kcal": 20.0, "protein_g": 2.2, "carbs_g": 3.9, "fat_g": 0.1,
        "fiber_g": 2.1, "default_serving_g": 100.0,
        "aliases_he": ["אספרגוס מאודה"],
        "aliases_en": ["steamed asparagus", "asparagus spears"],
        "source": "curated",
    },
    {
        "food_id": "food_076", "name_he": "תפוח אדמה", "name_en": "Potato",
        "category": "vegetable",
        "calories_kcal": 77.0, "protein_g": 2.0, "carbs_g": 17.0, "fat_g": 0.1,
        "fiber_g": 2.2, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["תפוחי אדמה", "תפו\"א מבושל", "תפו\"א אפוי"],
        "aliases_en": ["boiled potato", "baked potato"],
        "source": "curated",
    },
    {
        "food_id": "food_077", "name_he": "עגבנייה שרי", "name_en": "Cherry Tomatoes",
        "category": "vegetable",
        "calories_kcal": 18.0, "protein_g": 0.9, "carbs_g": 3.9, "fat_g": 0.2,
        "fiber_g": 1.2, "default_serving_g": 100.0,
        "aliases_he": ["עגבניות שרי", "עגבניות מיניאטורי"],
        "aliases_en": ["baby tomatoes", "grape tomatoes"],
        "source": "curated",
    },

    # ── FRUIT (extended) ──────────────────────────────────────────────────────
    {
        "food_id": "food_078", "name_he": "מנגו", "name_en": "Mango",
        "category": "fruit",
        "calories_kcal": 60.0, "protein_g": 0.8, "carbs_g": 15.0, "fat_g": 0.4,
        "fiber_g": 1.6, "sugar_g": 13.7, "default_unit": "unit", "default_serving_g": 200.0,
        "aliases_he": ["מנגו בשל", "מנגו טרי"],
        "aliases_en": ["fresh mango", "ripe mango"],
        "source": "curated",
    },
    {
        "food_id": "food_079", "name_he": "אבטיח", "name_en": "Watermelon",
        "category": "fruit",
        "calories_kcal": 30.0, "protein_g": 0.6, "carbs_g": 7.6, "fat_g": 0.2,
        "fiber_g": 0.4, "sugar_g": 6.2, "default_serving_g": 300.0,
        "aliases_he": ["אבטיח קיץ"],
        "aliases_en": ["fresh watermelon"],
        "source": "curated",
    },
    {
        "food_id": "food_080", "name_he": "רימון", "name_en": "Pomegranate",
        "category": "fruit",
        "calories_kcal": 83.0, "protein_g": 1.7, "carbs_g": 19.0, "fat_g": 1.2,
        "fiber_g": 4.0, "sugar_g": 13.7, "default_unit": "unit", "default_serving_g": 200.0,
        "aliases_he": ["גרגרי רימון"],
        "aliases_en": ["pomegranate seeds", "pomegranate arils"],
        "source": "curated",
    },
    {
        "food_id": "food_081", "name_he": "תמרים", "name_en": "Dates",
        "category": "fruit",
        "calories_kcal": 282.0, "protein_g": 2.5, "carbs_g": 75.0, "fat_g": 0.4,
        "fiber_g": 8.0, "sugar_g": 63.4, "default_unit": "unit", "default_serving_g": 25.0,
        "aliases_he": ["תמר", "תמרים מדגלן", "תמרים שינוי"],
        "aliases_en": ["medjool dates", "dried dates"],
        "source": "curated",
    },
    {
        "food_id": "food_082", "name_he": "קיווי", "name_en": "Kiwi",
        "category": "fruit",
        "calories_kcal": 61.0, "protein_g": 1.1, "carbs_g": 15.0, "fat_g": 0.5,
        "fiber_g": 3.0, "sugar_g": 9.1, "default_unit": "unit", "default_serving_g": 80.0,
        "aliases_he": ["קיווי ירוק", "קיווי זהוב"],
        "aliases_en": ["green kiwi", "gold kiwi"],
        "source": "curated",
    },
    {
        "food_id": "food_083", "name_he": "אפרסק", "name_en": "Peach",
        "category": "fruit",
        "calories_kcal": 39.0, "protein_g": 0.9, "carbs_g": 10.0, "fat_g": 0.3,
        "fiber_g": 1.5, "sugar_g": 8.4, "default_unit": "unit", "default_serving_g": 150.0,
        "aliases_he": ["אפרסק בשל", "שזיף"],
        "aliases_en": ["fresh peach", "nectarine"],
        "source": "curated",
    },
    {
        "food_id": "food_084", "name_he": "אוכמניות", "name_en": "Blueberries",
        "category": "fruit",
        "calories_kcal": 57.0, "protein_g": 0.7, "carbs_g": 14.0, "fat_g": 0.3,
        "fiber_g": 2.4, "sugar_g": 10.0, "default_serving_g": 100.0,
        "aliases_he": ["בלוברי"],
        "aliases_en": ["blueberry", "wild blueberries"],
        "source": "curated",
    },
    {
        "food_id": "food_085", "name_he": "אגס", "name_en": "Pear",
        "category": "fruit",
        "calories_kcal": 57.0, "protein_g": 0.4, "carbs_g": 15.0, "fat_g": 0.1,
        "fiber_g": 3.1, "sugar_g": 9.8, "default_unit": "unit", "default_serving_g": 170.0,
        "aliases_he": ["אגסים"],
        "aliases_en": ["pears"],
        "source": "curated",
    },

    # ── FAT (extended) ────────────────────────────────────────────────────────
    {
        "food_id": "food_086", "name_he": "חמאת שקדים", "name_en": "Almond Butter",
        "category": "fat",
        "calories_kcal": 614.0, "protein_g": 21.0, "carbs_g": 22.0, "fat_g": 55.0,
        "fiber_g": 10.0, "default_unit": "tablespoon", "default_serving_g": 32.0,
        "aliases_he": ["ממרח שקדים"],
        "aliases_en": ["almond spread"],
        "source": "curated",
    },
    {
        "food_id": "food_087", "name_he": "זיתים", "name_en": "Olives",
        "category": "fat",
        "calories_kcal": 145.0, "protein_g": 1.0, "carbs_g": 3.8, "fat_g": 15.0,
        "fiber_g": 3.2, "default_serving_g": 30.0,
        "aliases_he": ["זיתים שחורים", "זיתים ירוקים", "זיתים מקופצים"],
        "aliases_en": ["black olives", "green olives", "kalamata"],
        "source": "curated",
    },
    {
        "food_id": "food_088", "name_he": "שמן קנולה", "name_en": "Canola Oil",
        "category": "fat",
        "calories_kcal": 884.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0,
        "default_unit": "tablespoon", "default_serving_g": 14.0,
        "aliases_he": ["שמן קנולה", "שמן צמחי"],
        "aliases_en": ["vegetable oil", "rapeseed oil"],
        "source": "curated",
    },

    # ── LEGUME (extended) ─────────────────────────────────────────────────────
    {
        "food_id": "food_089", "name_he": "פול", "name_en": "Fava Beans",
        "category": "legume",
        "calories_kcal": 88.0, "protein_g": 7.0, "carbs_g": 16.0, "fat_g": 0.5,
        "fiber_g": 5.4, "default_serving_g": 150.0,
        "aliases_he": ["פולים", "פול מבושל"],
        "aliases_en": ["broad beans", "cooked fava"],
        "source": "curated",
    },
    {
        "food_id": "food_090", "name_he": "אדממה", "name_en": "Edamame",
        "category": "legume",
        "calories_kcal": 122.0, "protein_g": 11.0, "carbs_g": 9.9, "fat_g": 5.2,
        "fiber_g": 5.2, "default_serving_g": 100.0,
        "aliases_he": ["פולי סויה", "אדממה מבושל"],
        "aliases_en": ["soybeans", "soy beans cooked"],
        "source": "curated",
    },
    {
        "food_id": "food_091", "name_he": "שעועית לבנה", "name_en": "White Beans",
        "category": "legume",
        "calories_kcal": 139.0, "protein_g": 9.0, "carbs_g": 25.0, "fat_g": 0.4,
        "fiber_g": 6.3, "default_serving_g": 150.0,
        "aliases_he": ["שעועית לבנה מבושלת", "שעועית"],
        "aliases_en": ["cannellini beans", "navy beans"],
        "source": "curated",
    },

    # ── NUT_SEED (extended) ───────────────────────────────────────────────────
    {
        "food_id": "food_092", "name_he": "גרעיני דלעת", "name_en": "Pumpkin Seeds",
        "category": "nut_seed",
        "calories_kcal": 559.0, "protein_g": 30.0, "carbs_g": 11.0, "fat_g": 49.0,
        "fiber_g": 6.0, "default_serving_g": 30.0,
        "aliases_he": ["פיפיטס", "גרעיני קישואים"],
        "aliases_en": ["pepitas", "pumpkin seed kernels"],
        "source": "curated",
    },
    {
        "food_id": "food_093", "name_he": "פיסטוקים", "name_en": "Pistachios",
        "category": "nut_seed",
        "calories_kcal": 562.0, "protein_g": 20.0, "carbs_g": 28.0, "fat_g": 45.0,
        "fiber_g": 10.0, "default_serving_g": 30.0,
        "aliases_he": ["פיסטוק", "אגוזי פיסטוק"],
        "aliases_en": ["pistachio nuts"],
        "source": "curated",
    },
    {
        "food_id": "food_094", "name_he": "קשיו", "name_en": "Cashews",
        "category": "nut_seed",
        "calories_kcal": 553.0, "protein_g": 18.0, "carbs_g": 30.0, "fat_g": 44.0,
        "fiber_g": 3.3, "default_serving_g": 30.0,
        "aliases_he": ["אגוזי קשיו"],
        "aliases_en": ["cashew nuts"],
        "source": "curated",
    },
    {
        "food_id": "food_095", "name_he": "גרעיני צ'יה", "name_en": "Chia Seeds",
        "category": "nut_seed",
        "calories_kcal": 486.0, "protein_g": 17.0, "carbs_g": 42.0, "fat_g": 31.0,
        "fiber_g": 34.4, "default_unit": "tablespoon", "default_serving_g": 15.0,
        "aliases_he": ["זרעי צ'יה"],
        "aliases_en": ["chia", "salvia seeds"],
        "source": "curated",
    },
    {
        "food_id": "food_096", "name_he": "גרעיני פשתן", "name_en": "Flaxseeds",
        "category": "nut_seed",
        "calories_kcal": 534.0, "protein_g": 18.0, "carbs_g": 29.0, "fat_g": 42.0,
        "fiber_g": 27.3, "default_unit": "tablespoon", "default_serving_g": 10.0,
        "aliases_he": ["פשתן", "זרעי פשתן טחונים"],
        "aliases_en": ["ground flaxseed", "linseed"],
        "source": "curated",
    },
    {
        "food_id": "food_097", "name_he": "שומשום", "name_en": "Sesame Seeds",
        "category": "nut_seed",
        "calories_kcal": 573.0, "protein_g": 17.0, "carbs_g": 23.0, "fat_g": 50.0,
        "fiber_g": 11.8, "default_unit": "tablespoon", "default_serving_g": 10.0,
        "aliases_he": ["זרעי שומשום", "שומשום לבן"],
        "aliases_en": ["white sesame", "sesame"],
        "source": "curated",
    },

    # ── CONDIMENT (extended) ──────────────────────────────────────────────────
    {
        "food_id": "food_098", "name_he": "רוטב סויה", "name_en": "Soy Sauce",
        "category": "condiment",
        "calories_kcal": 60.0, "protein_g": 10.0, "carbs_g": 6.0, "fat_g": 0.1,
        "sodium_mg": 5720.0, "default_unit": "tablespoon", "default_serving_g": 15.0,
        "aliases_he": ["שויו", "תמרי", "רוטב סויה מופחת נתרן"],
        "aliases_en": ["tamari", "shoyu", "light soy sauce"],
        "source": "curated",
    },
    {
        "food_id": "food_099", "name_he": "זעתר", "name_en": "Za'atar",
        "category": "condiment",
        "calories_kcal": 315.0, "protein_g": 10.0, "carbs_g": 45.0, "fat_g": 11.0,
        "fiber_g": 14.0, "default_unit": "teaspoon", "default_serving_g": 3.0,
        "aliases_he": ["זעתר ירושלמי", "תבלין זעתר"],
        "aliases_en": ["zaatar spice", "middle eastern thyme"],
        "source": "curated",
    },
    {
        "food_id": "food_100", "name_he": "סלסה", "name_en": "Salsa",
        "category": "condiment",
        "calories_kcal": 36.0, "protein_g": 1.8, "carbs_g": 7.0, "fat_g": 0.2,
        "fiber_g": 1.5, "default_unit": "tablespoon", "default_serving_g": 30.0,
        "aliases_he": ["סלסה עגבניות", "רוטב עגבניות"],
        "aliases_en": ["tomato salsa", "fresh salsa"],
        "source": "curated",
    },
    {
        "food_id": "food_101", "name_he": "חרדל", "name_en": "Mustard",
        "category": "condiment",
        "calories_kcal": 66.0, "protein_g": 4.4, "carbs_g": 5.8, "fat_g": 3.3,
        "default_unit": "teaspoon", "default_serving_g": 5.0,
        "aliases_he": ["חרדל צרפתי", "חרדל דיז'ון"],
        "aliases_en": ["dijon mustard", "yellow mustard"],
        "source": "curated",
    },

    # ── BEVERAGE (extended) ───────────────────────────────────────────────────
    {
        "food_id": "food_102", "name_he": "מיץ תפוזים טבעי", "name_en": "Fresh Orange Juice",
        "category": "beverage",
        "calories_kcal": 45.0, "protein_g": 0.7, "carbs_g": 10.0, "fat_g": 0.2,
        "sugar_g": 8.4, "default_unit": "cup", "default_serving_g": 240.0,
        "aliases_he": ["מיץ תפוזים סחוט", "מיץ תפוזים"],
        "aliases_en": ["orange juice", "OJ", "fresh squeezed orange juice"],
        "source": "curated",
    },
    {
        "food_id": "food_103", "name_he": "חלב שיבולת שועל", "name_en": "Oat Milk",
        "category": "beverage",
        "calories_kcal": 47.0, "protein_g": 1.0, "carbs_g": 9.0, "fat_g": 1.5,
        "default_unit": "cup", "default_serving_g": 240.0,
        "aliases_he": ["חלב קוורקר", "חלב צמחי שיבולת שועל"],
        "aliases_en": ["oat milk unsweetened", "plant-based milk"],
        "source": "curated",
    },
    {
        "food_id": "food_104", "name_he": "חלב סויה", "name_en": "Soy Milk",
        "category": "beverage",
        "calories_kcal": 33.0, "protein_g": 3.3, "carbs_g": 2.9, "fat_g": 1.8,
        "default_unit": "cup", "default_serving_g": 240.0,
        "aliases_he": ["חלב סויה ללא סוכר"],
        "aliases_en": ["soy milk unsweetened", "soymilk"],
        "source": "curated",
    },
    {
        "food_id": "food_105", "name_he": "מיץ תפוח", "name_en": "Apple Juice",
        "category": "beverage",
        "calories_kcal": 46.0, "protein_g": 0.1, "carbs_g": 11.4, "fat_g": 0.1,
        "sugar_g": 10.0, "default_unit": "cup", "default_serving_g": 240.0,
        "aliases_he": ["מיץ תפוחים"],
        "aliases_en": ["fresh apple juice"],
        "source": "curated",
    },

    # ── OTHER / PREPARED ──────────────────────────────────────────────────────
    {
        "food_id": "food_106", "name_he": "פלאפל", "name_en": "Falafel",
        "category": "other",
        "calories_kcal": 333.0, "protein_g": 13.0, "carbs_g": 32.0, "fat_g": 18.0,
        "fiber_g": 5.0, "default_unit": "unit", "default_serving_g": 17.0,
        "aliases_he": ["פלאפל מטוגן", "כדורי פלאפל"],
        "aliases_en": ["fried falafel", "falafel ball"],
        "source": "curated",
    },
    {
        "food_id": "food_107", "name_he": "שניצל עוף", "name_en": "Chicken Schnitzel",
        "category": "other",
        "calories_kcal": 259.0, "protein_g": 22.0, "carbs_g": 13.0, "fat_g": 13.0,
        "default_unit": "unit", "default_serving_g": 120.0,
        "aliases_he": ["שניצל", "שניצל מטוגן"],
        "aliases_en": ["breaded chicken", "fried chicken cutlet"],
        "source": "curated",
    },
    {
        "food_id": "food_108", "name_he": "גרנולה", "name_en": "Granola",
        "category": "other",
        "calories_kcal": 471.0, "protein_g": 10.0, "carbs_g": 64.0, "fat_g": 20.0,
        "fiber_g": 5.0, "default_serving_g": 50.0,
        "aliases_he": ["גרנולה תוצרת בית", "גרנולה עם יוגורט"],
        "aliases_en": ["homemade granola", "muesli"],
        "source": "curated",
    },
    {
        "food_id": "food_109", "name_he": "חלבה", "name_en": "Halva",
        "category": "other",
        "calories_kcal": 469.0, "protein_g": 9.0, "carbs_g": 58.0, "fat_g": 24.0,
        "fiber_g": 4.0, "default_serving_g": 30.0,
        "aliases_he": ["חלווה", "חלבה שומשום"],
        "aliases_en": ["sesame halva", "halvah"],
        "source": "curated",
    },
    {
        "food_id": "food_110", "name_he": "מוצרלה", "name_en": "Mozzarella",
        "category": "dairy",
        "calories_kcal": 280.0, "protein_g": 28.0, "carbs_g": 2.2, "fat_g": 17.0,
        "default_serving_g": 50.0,
        "aliases_he": ["גבינת מוצרלה", "מוצרלה טרי"],
        "aliases_en": ["fresh mozzarella", "mozzarella cheese"],
        "source": "curated",
    },
]


def fetch_curated() -> List[Dict]:
    """Return the full curated food dataset (always succeeds)."""
    return list(CURATED_FOODS) + list(EXTENDED_FOODS) + list(EXTENDED_FOODS_2) + list(EXTENDED_FOODS_3) + list(EXTENDED_FOODS_4) + list(EXTENDED_FOODS_5)


# ─── Open Food Facts API (optional) ──────────────────────────────────────────

_OFF_BASE = "https://world.openfoodfacts.org/cgi/search.pl"

# Foods to search for that supplement the curated set
# Israeli / Middle-Eastern / Mediterranean focus
_OFF_SEARCH_TERMS = [
    # Israeli classics
    "falafel",
    "shakshuka",
    "labneh",
    "hummus",
    "tahini",
    "pita bread",
    "burekas",
    "babaganoush",
    "tabbouleh",
    "halva",
    "zaatar",
    "knafeh",
    # Proteins
    "chicken breast",
    "salmon fillet",
    "canned tuna",
    "greek yogurt",
    "cottage cheese",
    "eggs",
    "turkey breast",
    "tofu",
    # Grains & carbs
    "whole wheat bread",
    "couscous",
    "bulgur",
    "quinoa",
    "oatmeal",
    "brown rice",
    # Dairy
    "feta cheese",
    "mozzarella",
    "cream cheese",
    # Vegetables
    "spinach",
    "broccoli",
    "sweet potato",
    "eggplant",
    # Fruits
    "mango",
    "avocado",
    "pomegranate",
    "dates medjool",
    # Nuts & seeds
    "almonds",
    "walnuts",
    "chia seeds",
    "peanut butter",
    # Legumes
    "lentils",
    "chickpeas",
    # Beef & pork
    "ribeye steak",
    "ground beef",
    "bacon",
    "pork chop",
    "hot dog",
    "salami",
    "pepperoni",
    "chorizo",
    # More fish
    "tilapia",
    "mackerel",
    "smoked salmon",
    "sardines",
    "trout",
    "herring",
    # More dairy
    "cheddar cheese",
    "parmesan",
    "brie cheese",
    "ricotta",
    "heavy cream",
    "cream cheese",
    # More grains
    "white bread",
    "sourdough",
    "bagel",
    "croissant",
    "rye bread",
    "naan",
    "polenta",
    "cornflakes",
    "muesli",
    "rice noodles",
    # More vegetables
    "kale",
    "brussels sprouts",
    "artichoke",
    "beetroot",
    "butternut squash",
    "kimchi",
    "leek",
    "green beans",
    "bok choy",
    # More fruits
    "pineapple",
    "papaya",
    "cantaloupe",
    "raspberries",
    "blackberries",
    "passion fruit",
    "cranberries",
    "raisins",
    "prunes",
    "coconut",
    # Fast food
    "french fries",
    "hamburger",
    "pizza",
    "chicken nuggets",
    "mac and cheese",
    "fried chicken",
    # Asian
    "pad thai",
    "fried rice",
    "miso paste",
    "nori",
    "ramen",
    "gyoza",
    "tempeh",
    # Mexican
    "tortilla",
    "guacamole",
    "salsa",
    "burrito",
    # Desserts
    "brownie",
    "cheesecake",
    "donut",
    "tiramisu",
    "chocolate chip cookie",
    # Condiments & oils
    "pesto",
    "bbq sauce",
    "sriracha",
    "teriyaki",
    "coconut milk",
    "ghee",
    "sesame oil",
    # Snacks
    "protein bar",
    "granola bar",
    "popcorn",
    "potato chips",
    "pretzels",
]


def fetch_from_open_food_facts(
    search_terms: List[str] = None,
    max_per_term: int = 8,
    timeout: int = 10,
) -> List[Dict]:
    """
    Fetch additional foods from Open Food Facts API.
    Returns normalized food dicts. Skips silently on network errors.
    Only returns foods with complete macro data.
    """
    if search_terms is None:
        search_terms = _OFF_SEARCH_TERMS

    results: List[Dict] = []
    seen_ids: set = set()

    for term in search_terms:
        try:
            params = urllib.parse.urlencode({
                "action": "process",
                "json": "1",
                "fields": "code,product_name,nutriments",
                "search_terms": term,
                "page_size": str(max_per_term),
                "page": "1",
            })
            url = f"{_OFF_BASE}?{params}"
            req = urllib.request.Request(
                url, headers={"User-Agent": "NutritionApp/1.0 (educational)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for product in data.get("products", []):
                normalized = _normalize_off_product(product)
                if normalized and normalized["food_id"] not in seen_ids:
                    seen_ids.add(normalized["food_id"])
                    results.append(normalized)
        except Exception:
            # Network unavailable, timeout, or bad JSON — skip gracefully
            pass

    return results


def _normalize_off_product(product: dict) -> Optional[Dict]:
    """Convert an Open Food Facts product to our food schema. Returns None if data incomplete."""
    n = product.get("nutriments", {})
    calories = n.get("energy-kcal_100g") or n.get("energy-kcal")
    protein = n.get("proteins_100g")
    carbs = n.get("carbohydrates_100g")
    fat = n.get("fat_100g")

    if not all(v is not None for v in [calories, protein, carbs, fat]):
        return None

    code = str(product.get("code", "")).strip()
    name = str(product.get("product_name", "")).strip()
    if not name or not code:
        return None

    return {
        "food_id": f"off_{code[:20]}",
        "name_he": name,
        "name_en": name,
        "category": "other",
        "calories_kcal": float(calories),
        "protein_g": float(protein),
        "carbs_g": float(carbs),
        "fat_g": float(fat),
        "fiber_g": float(n.get("fiber_100g") or 0),
        "sugar_g": float(n.get("sugars_100g") or 0),
        "sodium_mg": float(n.get("sodium_100g") or 0) * 1000,
        "aliases_he": [],
        "aliases_en": [],
        "source": "open_food_facts",
    }
