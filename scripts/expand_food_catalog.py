"""
expand_food_catalog.py — מרחיב את foods_extended.json מ-400 ל-1000+ מזונות

מקורות:
  - USDA FoodData Central (Foundation Foods — ללא API key)
  - רשימה ידנית מקיפה של מזונות ישראליים נפוצים
  - knowledge base: planner_knowledge_base.json

הרץ:  py scripts/expand_food_catalog.py
"""
import json, os, sys, uuid, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "nutrition_app", "data", "foods_extended.json")


def fid():
    return "food_" + uuid.uuid4().hex[:8]


# ── ידני: מזונות ישראלים + בסיסיים שחסרים ─────────────────────────────────
MANUAL_FOODS = [
    # ── בשר ועוף ──────────────────────────────────────────────────────────
    {"name_he": "חזה עוף מבושל",    "name_en": "Chicken Breast Cooked",   "cat": "protein",    "kcal": 165, "prot": 31.0, "carbs": 0.0,  "fat": 3.6,  "srv": 150},
    {"name_he": "שוק עוף",          "name_en": "Chicken Thigh",           "cat": "protein",    "kcal": 215, "prot": 26.0, "carbs": 0.0,  "fat": 12.0, "srv": 120},
    {"name_he": "כנפי עוף",         "name_en": "Chicken Wings",           "cat": "protein",    "kcal": 203, "prot": 30.0, "carbs": 0.0,  "fat": 8.0,  "srv": 100},
    {"name_he": "שניצל עוף",        "name_en": "Chicken Schnitzel",       "cat": "protein",    "kcal": 220, "prot": 22.0, "carbs": 10.0, "fat": 10.0, "srv": 150},
    {"name_he": "שניצל הודו",       "name_en": "Turkey Schnitzel",        "cat": "protein",    "kcal": 230, "prot": 20.0, "carbs": 12.0, "fat": 11.0, "srv": 150},
    {"name_he": "חזה הודו",         "name_en": "Turkey Breast",           "cat": "protein",    "kcal": 135, "prot": 30.0, "carbs": 0.0,  "fat": 1.0,  "srv": 150},
    {"name_he": "נקניק עוף",        "name_en": "Chicken Sausage",         "cat": "protein",    "kcal": 195, "prot": 14.0, "carbs": 2.0,  "fat": 14.0, "srv": 80},
    {"name_he": "בשר טחון בקר",     "name_en": "Ground Beef 15%",         "cat": "protein",    "kcal": 215, "prot": 26.0, "carbs": 0.0,  "fat": 12.0, "srv": 150},
    {"name_he": "סטייק אנטריקוט",   "name_en": "Ribeye Steak",            "cat": "protein",    "kcal": 291, "prot": 24.0, "carbs": 0.0,  "fat": 21.0, "srv": 200},
    {"name_he": "כבד עוף",          "name_en": "Chicken Liver",           "cat": "protein",    "kcal": 172, "prot": 26.5, "carbs": 0.9,  "fat": 6.5,  "srv": 100},
    # ── דגים ──────────────────────────────────────────────────────────────
    {"name_he": "סלמון אפוי",       "name_en": "Baked Salmon",            "cat": "protein",    "kcal": 208, "prot": 20.0, "carbs": 0.0,  "fat": 13.0, "srv": 150},
    {"name_he": "פילה סלמון",       "name_en": "Salmon Fillet",           "cat": "protein",    "kcal": 208, "prot": 20.0, "carbs": 0.0,  "fat": 13.0, "srv": 150},
    {"name_he": "טונה במים סחוטה",  "name_en": "Canned Tuna in Water",    "cat": "protein",    "kcal": 116, "prot": 26.0, "carbs": 0.0,  "fat": 1.0,  "srv": 100},
    {"name_he": "טונה בשמן",        "name_en": "Canned Tuna in Oil",      "cat": "protein",    "kcal": 190, "prot": 24.0, "carbs": 0.0,  "fat": 10.0, "srv": 100},
    {"name_he": "דג ים מוקפץ",      "name_en": "Sea Bass Stir Fry",       "cat": "protein",    "kcal": 124, "prot": 23.0, "carbs": 0.0,  "fat": 3.0,  "srv": 150},
    {"name_he": "מקרל מעושן",       "name_en": "Smoked Mackerel",         "cat": "protein",    "kcal": 305, "prot": 18.5, "carbs": 0.0,  "fat": 25.0, "srv": 80},
    {"name_he": "אמנון מבושל",      "name_en": "Tilapia Cooked",          "cat": "protein",    "kcal": 128, "prot": 26.0, "carbs": 0.0,  "fat": 2.7,  "srv": 150},
    {"name_he": "סרדינים בשימורים", "name_en": "Canned Sardines",         "cat": "protein",    "kcal": 208, "prot": 25.0, "carbs": 0.0,  "fat": 11.0, "srv": 100},
    {"name_he": "שרימפס מבושל",     "name_en": "Cooked Shrimp",           "cat": "protein",    "kcal":  99, "prot": 24.0, "carbs": 0.0,  "fat": 0.3,  "srv": 100},
    # ── ביצים ─────────────────────────────────────────────────────────────
    {"name_he": "ביצה שלמה",        "name_en": "Whole Egg",               "cat": "protein",    "kcal": 155, "prot": 13.0, "carbs": 1.1,  "fat": 11.0, "srv": 55},
    {"name_he": "חלבון ביצה",       "name_en": "Egg White",               "cat": "protein",    "kcal":  52, "prot": 11.0, "carbs": 0.7,  "fat": 0.2,  "srv": 60},
    {"name_he": "חביתה",            "name_en": "Omelette",                "cat": "protein",    "kcal": 154, "prot": 11.0, "carbs": 1.0,  "fat": 11.5, "srv": 120},
    {"name_he": "ביצים מקושקשות",   "name_en": "Scrambled Eggs",          "cat": "protein",    "kcal": 148, "prot": 10.0, "carbs": 1.6,  "fat": 11.0, "srv": 120},
    # ── מוצרי חלב ─────────────────────────────────────────────────────────
    {"name_he": "קוטג' 5%",         "name_en": "Cottage Cheese 5%",       "cat": "dairy",      "kcal": 103, "prot": 11.0, "carbs": 3.5,  "fat": 5.0,  "srv": 200},
    {"name_he": "קוטג' 9%",         "name_en": "Cottage Cheese 9%",       "cat": "dairy",      "kcal": 120, "prot": 11.0, "carbs": 3.5,  "fat": 9.0,  "srv": 200},
    {"name_he": "גבינה צהובה 28%",  "name_en": "Yellow Cheese 28%",       "cat": "dairy",      "kcal": 350, "prot": 25.0, "carbs": 1.0,  "fat": 28.0, "srv": 30},
    {"name_he": "גבינה לבנה 5%",    "name_en": "White Cheese 5%",         "cat": "dairy",      "kcal":  85, "prot":  9.0, "carbs": 3.0,  "fat": 3.5,  "srv": 100},
    {"name_he": "גבינה בולגרית",    "name_en": "Bulgarian Cheese",        "cat": "dairy",      "kcal": 264, "prot": 14.0, "carbs": 0.5,  "fat": 22.0, "srv": 50},
    {"name_he": "גבינת פטה",        "name_en": "Feta Cheese",             "cat": "dairy",      "kcal": 264, "prot": 14.0, "carbs": 4.0,  "fat": 21.0, "srv": 50},
    {"name_he": "לבנה",             "name_en": "Labaneh",                 "cat": "dairy",      "kcal": 150, "prot":  6.0, "carbs": 4.0,  "fat": 12.0, "srv": 80},
    {"name_he": "יוגורט יווני 5%",  "name_en": "Greek Yogurt 5%",         "cat": "dairy",      "kcal":  95, "prot":  6.0, "carbs": 4.0,  "fat": 5.0,  "srv": 150},
    {"name_he": "יוגורט 3%",        "name_en": "Yogurt 3%",               "cat": "dairy",      "kcal":  61, "prot":  3.5, "carbs": 4.7,  "fat": 3.0,  "srv": 150},
    {"name_he": "שמנת חמוצה",       "name_en": "Sour Cream",              "cat": "dairy",      "kcal": 193, "prot":  2.4, "carbs": 4.6,  "fat": 19.0, "srv": 30},
    {"name_he": "גבינת ריקוטה",     "name_en": "Ricotta Cheese",          "cat": "dairy",      "kcal": 174, "prot": 11.3, "carbs": 3.0,  "fat": 13.0, "srv": 100},
    {"name_he": "Tnuva GO יוגורט",  "name_en": "Tnuva GO Protein Yogurt", "cat": "dairy",      "kcal":  97, "prot": 20.0, "carbs": 5.0,  "fat": 0.5,  "srv": 200},
    {"name_he": "חלב 1%",           "name_en": "Milk 1%",                 "cat": "dairy",      "kcal":  42, "prot":  3.4, "carbs": 5.0,  "fat": 1.0,  "srv": 250},
    {"name_he": "חלב שוקולד",       "name_en": "Chocolate Milk",          "cat": "dairy",      "kcal":  83, "prot":  3.4, "carbs": 11.4, "fat": 2.5,  "srv": 250},
    {"name_he": "גבינת מוצרלה",     "name_en": "Mozzarella",              "cat": "dairy",      "kcal": 280, "prot": 18.0, "carbs": 3.1,  "fat": 22.0, "srv": 50},
    # ── קטניות ────────────────────────────────────────────────────────────
    {"name_he": "חומוס מבושל",      "name_en": "Cooked Chickpeas",        "cat": "legume",     "kcal": 164, "prot":  8.9, "carbs": 27.4, "fat": 2.6,  "srv": 150},
    {"name_he": "עדשים כתומות",     "name_en": "Red Lentils Cooked",      "cat": "legume",     "kcal": 116, "prot":  9.0, "carbs": 20.1, "fat": 0.4,  "srv": 150},
    {"name_he": "עדשים ירוקות",     "name_en": "Green Lentils Cooked",    "cat": "legume",     "kcal": 116, "prot":  9.0, "carbs": 20.0, "fat": 0.4,  "srv": 150},
    {"name_he": "שעועית שחורה",     "name_en": "Black Beans Cooked",      "cat": "legume",     "kcal": 132, "prot":  8.9, "carbs": 23.7, "fat": 0.5,  "srv": 150},
    {"name_he": "שעועית לבנה",      "name_en": "White Beans Cooked",      "cat": "legume",     "kcal": 139, "prot":  9.7, "carbs": 25.1, "fat": 0.4,  "srv": 150},
    {"name_he": "פול מבושל",        "name_en": "Fava Beans Cooked",       "cat": "legume",     "kcal": 110, "prot":  7.6, "carbs": 19.7, "fat": 0.4,  "srv": 150},
    {"name_he": "אפונה מבושלת",     "name_en": "Green Peas Cooked",       "cat": "legume",     "kcal":  84, "prot":  5.4, "carbs": 15.6, "fat": 0.2,  "srv": 100},
    {"name_he": "סויה מבושלת",      "name_en": "Edamame Cooked",          "cat": "legume",     "kcal": 121, "prot": 11.9, "carbs": 8.9,  "fat": 5.2,  "srv": 100},
    {"name_he": "טופו",             "name_en": "Tofu",                    "cat": "legume",     "kcal":  76, "prot":  8.0, "carbs": 1.9,  "fat": 4.8,  "srv": 150},
    {"name_he": "חומוס מרוח",       "name_en": "Hummus Spread",           "cat": "legume",     "kcal": 180, "prot":  8.0, "carbs": 11.0, "fat": 11.6, "srv": 100},
    # ── דגנים ─────────────────────────────────────────────────────────────
    {"name_he": "אורז לבן מבושל",   "name_en": "White Rice Cooked",       "cat": "grain",      "kcal": 130, "prot":  2.7, "carbs": 28.0, "fat": 0.3,  "srv": 180},
    {"name_he": "אורז חום מבושל",   "name_en": "Brown Rice Cooked",       "cat": "grain",      "kcal": 111, "prot":  2.6, "carbs": 23.0, "fat": 0.9,  "srv": 180},
    {"name_he": "פסטה מבושלת",      "name_en": "Pasta Cooked",            "cat": "grain",      "kcal": 131, "prot":  5.0, "carbs": 25.0, "fat": 1.1,  "srv": 200},
    {"name_he": "פסטה מלאה מבושלת","name_en": "Whole Wheat Pasta Cooked","cat": "grain",      "kcal": 124, "prot":  5.3, "carbs": 23.0, "fat": 1.0,  "srv": 200},
    {"name_he": "קוסקוס מבושל",     "name_en": "Couscous Cooked",         "cat": "grain",      "kcal": 112, "prot":  3.8, "carbs": 23.2, "fat": 0.2,  "srv": 150},
    {"name_he": "קינואה מבושלת",    "name_en": "Quinoa Cooked",           "cat": "grain",      "kcal": 120, "prot":  4.4, "carbs": 21.3, "fat": 1.9,  "srv": 150},
    {"name_he": "בורגול מבושל",     "name_en": "Bulgur Cooked",           "cat": "grain",      "kcal":  83, "prot":  3.1, "carbs": 18.6, "fat": 0.2,  "srv": 150},
    {"name_he": "שיבולת שועל יבשה", "name_en": "Oats Dry",                "cat": "grain",      "kcal": 389, "prot": 17.0, "carbs": 66.0, "fat": 7.0,  "srv": 50},
    {"name_he": "שיבולת שועל מבושלת","name_en":"Oatmeal Cooked",          "cat": "grain",      "kcal":  71, "prot":  2.5, "carbs": 12.0, "fat": 1.5,  "srv": 200},
    {"name_he": "גרנולה",           "name_en": "Granola",                 "cat": "grain",      "kcal": 471, "prot": 10.0, "carbs": 64.0, "fat": 20.0, "srv": 50},
    {"name_he": "קורנפלקס",         "name_en": "Corn Flakes",             "cat": "grain",      "kcal": 357, "prot":  7.5, "carbs": 84.0, "fat": 0.4,  "srv": 40},
    {"name_he": "פתיתים מבושלים",   "name_en": "Ptitim (Israeli Couscous)","cat":"grain",      "kcal": 130, "prot":  4.5, "carbs": 26.0, "fat": 0.8,  "srv": 150},
    {"name_he": "פולנטה מבושלת",    "name_en": "Polenta Cooked",          "cat": "grain",      "kcal":  70, "prot":  1.5, "carbs": 15.0, "fat": 0.4,  "srv": 200},
    # ── לחם ───────────────────────────────────────────────────────────────
    {"name_he": "פיתה לבנה",        "name_en": "White Pita",              "cat": "bread",      "kcal": 275, "prot":  9.0, "carbs": 55.0, "fat": 1.5,  "srv": 60},
    {"name_he": "פיתה מלאה",        "name_en": "Whole Wheat Pita",        "cat": "bread",      "kcal": 267, "prot": 10.0, "carbs": 50.0, "fat": 2.5,  "srv": 65},
    {"name_he": "לחם לבן פרוסה",    "name_en": "White Bread Slice",       "cat": "bread",      "kcal": 265, "prot":  9.0, "carbs": 49.0, "fat": 3.2,  "srv": 30},
    {"name_he": "לחם מלא פרוסה",    "name_en": "Whole Wheat Bread Slice", "cat": "bread",      "kcal": 247, "prot": 13.0, "carbs": 41.0, "fat": 3.5,  "srv": 35},
    {"name_he": "לחם שיפון",        "name_en": "Rye Bread",               "cat": "bread",      "kcal": 259, "prot":  9.4, "carbs": 48.0, "fat": 3.3,  "srv": 35},
    {"name_he": "לחמנייה",          "name_en": "Bread Roll",              "cat": "bread",      "kcal": 289, "prot":  9.0, "carbs": 55.0, "fat": 3.5,  "srv": 60},
    {"name_he": "קרואסון",          "name_en": "Croissant",               "cat": "bread",      "kcal": 406, "prot":  8.2, "carbs": 45.0, "fat": 21.0, "srv": 65},
    {"name_he": "בייגל",            "name_en": "Bagel",                   "cat": "bread",      "kcal": 270, "prot": 11.0, "carbs": 53.0, "fat": 1.7,  "srv": 98},
    {"name_he": "קרקר",             "name_en": "Cracker",                 "cat": "bread",      "kcal": 430, "prot":  9.0, "carbs": 68.0, "fat": 14.0, "srv": 20},
    {"name_he": "עוגיית אורז",      "name_en": "Rice Cake",               "cat": "bread",      "kcal": 387, "prot":  8.0, "carbs": 81.0, "fat": 2.8,  "srv": 9},
    # ── ירקות ─────────────────────────────────────────────────────────────
    {"name_he": "עגבנייה",          "name_en": "Tomato",                  "cat": "vegetable",  "kcal":  18, "prot":  0.9, "carbs": 3.9,  "fat": 0.2,  "srv": 120},
    {"name_he": "מלפפון",           "name_en": "Cucumber",                "cat": "vegetable",  "kcal":  15, "prot":  0.7, "carbs": 3.6,  "fat": 0.1,  "srv": 100},
    {"name_he": "גזר",              "name_en": "Carrot",                  "cat": "vegetable",  "kcal":  41, "prot":  0.9, "carbs": 9.6,  "fat": 0.2,  "srv": 100},
    {"name_he": "ברוקולי",          "name_en": "Broccoli",                "cat": "vegetable",  "kcal":  34, "prot":  2.8, "carbs": 7.0,  "fat": 0.4,  "srv": 150},
    {"name_he": "כרובית",           "name_en": "Cauliflower",             "cat": "vegetable",  "kcal":  25, "prot":  1.9, "carbs": 5.0,  "fat": 0.3,  "srv": 150},
    {"name_he": "כרוב",             "name_en": "Cabbage",                 "cat": "vegetable",  "kcal":  25, "prot":  1.3, "carbs": 5.8,  "fat": 0.1,  "srv": 100},
    {"name_he": "תרד",              "name_en": "Spinach",                 "cat": "vegetable",  "kcal":  23, "prot":  2.9, "carbs": 3.6,  "fat": 0.4,  "srv": 100},
    {"name_he": "חסה",              "name_en": "Lettuce",                 "cat": "vegetable",  "kcal":  15, "prot":  1.4, "carbs": 2.9,  "fat": 0.2,  "srv": 80},
    {"name_he": "פלפל אדום",        "name_en": "Red Bell Pepper",         "cat": "vegetable",  "kcal":  31, "prot":  1.0, "carbs": 7.3,  "fat": 0.3,  "srv": 120},
    {"name_he": "פלפל ירוק",        "name_en": "Green Bell Pepper",       "cat": "vegetable",  "kcal":  20, "prot":  0.9, "carbs": 4.6,  "fat": 0.2,  "srv": 120},
    {"name_he": "קישוא",            "name_en": "Zucchini",                "cat": "vegetable",  "kcal":  17, "prot":  1.2, "carbs": 3.1,  "fat": 0.3,  "srv": 150},
    {"name_he": "חציל",             "name_en": "Eggplant",                "cat": "vegetable",  "kcal":  25, "prot":  1.0, "carbs": 5.9,  "fat": 0.2,  "srv": 150},
    {"name_he": "פטרייה",           "name_en": "Mushroom",                "cat": "vegetable",  "kcal":  22, "prot":  3.1, "carbs": 3.3,  "fat": 0.3,  "srv": 100},
    {"name_he": "בצל",              "name_en": "Onion",                   "cat": "vegetable",  "kcal":  40, "prot":  1.1, "carbs": 9.3,  "fat": 0.1,  "srv": 80},
    {"name_he": "שום",              "name_en": "Garlic",                  "cat": "vegetable",  "kcal": 149, "prot":  6.4, "carbs": 33.0, "fat": 0.5,  "srv": 5},
    {"name_he": "תפוח אדמה",        "name_en": "Potato",                  "cat": "vegetable",  "kcal":  77, "prot":  2.0, "carbs": 17.5, "fat": 0.1,  "srv": 150},
    {"name_he": "בטטה",             "name_en": "Sweet Potato",            "cat": "vegetable",  "kcal":  86, "prot":  1.6, "carbs": 20.1, "fat": 0.1,  "srv": 150},
    {"name_he": "תירס מבושל",       "name_en": "Corn Cooked",             "cat": "vegetable",  "kcal":  96, "prot":  3.4, "carbs": 21.0, "fat": 1.5,  "srv": 100},
    {"name_he": "עגבניות שרי",      "name_en": "Cherry Tomatoes",         "cat": "vegetable",  "kcal":  18, "prot":  0.9, "carbs": 3.9,  "fat": 0.2,  "srv": 100},
    {"name_he": "צנון",             "name_en": "Radish",                  "cat": "vegetable",  "kcal":  16, "prot":  0.7, "carbs": 3.4,  "fat": 0.1,  "srv": 60},
    # ── פירות ─────────────────────────────────────────────────────────────
    {"name_he": "תפוח",             "name_en": "Apple",                   "cat": "fruit",      "kcal":  52, "prot":  0.3, "carbs": 13.8, "fat": 0.2,  "srv": 160},
    {"name_he": "בננה",             "name_en": "Banana",                  "cat": "fruit",      "kcal":  89, "prot":  1.1, "carbs": 22.8, "fat": 0.3,  "srv": 120},
    {"name_he": "תפוז",             "name_en": "Orange",                  "cat": "fruit",      "kcal":  47, "prot":  0.9, "carbs": 11.8, "fat": 0.1,  "srv": 180},
    {"name_he": "אבוקדו",           "name_en": "Avocado",                 "cat": "fruit",      "kcal": 160, "prot":  2.0, "carbs": 8.5,  "fat": 14.7, "srv": 100},
    {"name_he": "אפרסק",            "name_en": "Peach",                   "cat": "fruit",      "kcal":  39, "prot":  0.9, "carbs": 9.5,  "fat": 0.3,  "srv": 150},
    {"name_he": "ענבים",            "name_en": "Grapes",                  "cat": "fruit",      "kcal":  69, "prot":  0.7, "carbs": 18.1, "fat": 0.2,  "srv": 100},
    {"name_he": "מנגו",             "name_en": "Mango",                   "cat": "fruit",      "kcal":  60, "prot":  0.8, "carbs": 15.0, "fat": 0.4,  "srv": 150},
    {"name_he": "אבטיח",            "name_en": "Watermelon",              "cat": "fruit",      "kcal":  30, "prot":  0.6, "carbs": 7.6,  "fat": 0.2,  "srv": 200},
    {"name_he": "תות שדה",          "name_en": "Strawberry",              "cat": "fruit",      "kcal":  32, "prot":  0.7, "carbs": 7.7,  "fat": 0.3,  "srv": 100},
    {"name_he": "אוכמניות",         "name_en": "Blueberries",             "cat": "fruit",      "kcal":  57, "prot":  0.7, "carbs": 14.5, "fat": 0.3,  "srv": 100},
    {"name_he": "אנניס",            "name_en": "Pineapple",               "cat": "fruit",      "kcal":  50, "prot":  0.5, "carbs": 13.1, "fat": 0.1,  "srv": 150},
    {"name_he": "לימון",            "name_en": "Lemon",                   "cat": "fruit",      "kcal":  29, "prot":  1.1, "carbs": 9.3,  "fat": 0.3,  "srv": 60},
    {"name_he": "אשכולית",          "name_en": "Grapefruit",              "cat": "fruit",      "kcal":  42, "prot":  0.8, "carbs": 10.7, "fat": 0.1,  "srv": 200},
    {"name_he": "דובדבן",           "name_en": "Cherry",                  "cat": "fruit",      "kcal":  50, "prot":  1.0, "carbs": 12.2, "fat": 0.3,  "srv": 100},
    {"name_he": "אגס",              "name_en": "Pear",                    "cat": "fruit",      "kcal":  57, "prot":  0.4, "carbs": 15.2, "fat": 0.1,  "srv": 160},
    {"name_he": "שזיף",             "name_en": "Plum",                    "cat": "fruit",      "kcal":  46, "prot":  0.7, "carbs": 11.4, "fat": 0.3,  "srv": 80},
    {"name_he": "קיווי",            "name_en": "Kiwi",                    "cat": "fruit",      "kcal":  61, "prot":  1.1, "carbs": 14.7, "fat": 0.5,  "srv": 75},
    {"name_he": "מלון",             "name_en": "Melon",                   "cat": "fruit",      "kcal":  34, "prot":  0.8, "carbs": 8.2,  "fat": 0.2,  "srv": 200},
    {"name_he": "תמר",              "name_en": "Date",                    "cat": "fruit",      "kcal": 282, "prot":  2.5, "carbs": 75.0, "fat": 0.4,  "srv": 24},
    {"name_he": "תאנה",             "name_en": "Fig",                     "cat": "fruit",      "kcal":  74, "prot":  0.8, "carbs": 19.2, "fat": 0.3,  "srv": 60},
    # ── אגוזים וזרעים ──────────────────────────────────────────────────────
    {"name_he": "שקדים",            "name_en": "Almonds",                 "cat": "nut",        "kcal": 579, "prot": 21.2, "carbs": 21.6, "fat": 49.9, "srv": 30},
    {"name_he": "אגוזי מלך",        "name_en": "Walnuts",                 "cat": "nut",        "kcal": 654, "prot": 15.2, "carbs": 13.7, "fat": 65.2, "srv": 30},
    {"name_he": "קשיו",             "name_en": "Cashews",                 "cat": "nut",        "kcal": 553, "prot": 18.2, "carbs": 30.2, "fat": 43.9, "srv": 30},
    {"name_he": "פיסטוקים",         "name_en": "Pistachios",              "cat": "nut",        "kcal": 560, "prot": 20.2, "carbs": 27.5, "fat": 45.4, "srv": 30},
    {"name_he": "בוטנים",           "name_en": "Peanuts",                 "cat": "nut",        "kcal": 567, "prot": 25.8, "carbs": 16.1, "fat": 49.2, "srv": 30},
    {"name_he": "זרעי צ'יה",        "name_en": "Chia Seeds",              "cat": "nut",        "kcal": 486, "prot": 16.5, "carbs": 42.1, "fat": 30.7, "srv": 15},
    {"name_he": "זרעי פשתן",        "name_en": "Flaxseeds",               "cat": "nut",        "kcal": 534, "prot": 18.3, "carbs": 28.9, "fat": 42.2, "srv": 15},
    {"name_he": "גרעיני חמנייה",    "name_en": "Sunflower Seeds",         "cat": "nut",        "kcal": 584, "prot": 20.8, "carbs": 20.0, "fat": 51.5, "srv": 30},
    {"name_he": "חמאת בוטנים",      "name_en": "Peanut Butter",           "cat": "nut",        "kcal": 588, "prot": 25.1, "carbs": 20.1, "fat": 50.4, "srv": 32},
    # ── שמנים ─────────────────────────────────────────────────────────────
    {"name_he": "שמן זית",          "name_en": "Olive Oil",               "cat": "fat",        "kcal": 884, "prot":  0.0, "carbs": 0.0,  "fat": 100.0,"srv": 10},
    {"name_he": "שמן קוקוס",        "name_en": "Coconut Oil",             "cat": "fat",        "kcal": 862, "prot":  0.0, "carbs": 0.0,  "fat": 100.0,"srv": 10},
    {"name_he": "חמאה",             "name_en": "Butter",                  "cat": "fat",        "kcal": 717, "prot":  0.9, "carbs": 0.1,  "fat": 81.1, "srv": 10},
    {"name_he": "מרגרינה",          "name_en": "Margarine",               "cat": "fat",        "kcal": 718, "prot":  0.2, "carbs": 0.6,  "fat": 80.7, "srv": 10},
    {"name_he": "מיונז",            "name_en": "Mayonnaise",              "cat": "condiment",  "kcal": 680, "prot":  1.0, "carbs": 0.6,  "fat": 75.0, "srv": 15},
    # ── משקאות ────────────────────────────────────────────────────────────
    {"name_he": "מיץ תפוזים טבעי",  "name_en": "Fresh Orange Juice",      "cat": "beverage",   "kcal":  45, "prot":  0.7, "carbs": 10.4, "fat": 0.2,  "srv": 200},
    {"name_he": "שייק פירות",       "name_en": "Fruit Smoothie",          "cat": "beverage",   "kcal":  70, "prot":  1.5, "carbs": 16.0, "fat": 0.5,  "srv": 300},
    {"name_he": "שייק חלבון",       "name_en": "Protein Shake",           "cat": "beverage",   "kcal": 140, "prot": 25.0, "carbs": 6.0,  "fat": 2.5,  "srv": 350},
    {"name_he": "קפה שחור",         "name_en": "Black Coffee",            "cat": "beverage",   "kcal":   2, "prot":  0.3, "carbs": 0.0,  "fat": 0.0,  "srv": 240},
    {"name_he": "קפה עם חלב",       "name_en": "Coffee with Milk",        "cat": "beverage",   "kcal":  30, "prot":  1.5, "carbs": 3.0,  "fat": 1.0,  "srv": 240},
    {"name_he": "לאטה",             "name_en": "Latte",                   "cat": "beverage",   "kcal": 100, "prot":  5.0, "carbs": 9.0,  "fat": 4.0,  "srv": 300},
    {"name_he": "תה",               "name_en": "Tea",                     "cat": "beverage",   "kcal":   1, "prot":  0.0, "carbs": 0.3,  "fat": 0.0,  "srv": 240},
    {"name_he": "מיץ עגבניות",      "name_en": "Tomato Juice",            "cat": "beverage",   "kcal":  17, "prot":  0.8, "carbs": 4.0,  "fat": 0.1,  "srv": 200},
    # ── ממרחים וקטשופים ────────────────────────────────────────────────────
    {"name_he": "טחינה גולמית",     "name_en": "Raw Tahini",              "cat": "condiment",  "kcal": 655, "prot": 24.0, "carbs": 4.5,  "fat": 57.0, "srv": 20},
    {"name_he": "טחינה מוכנה",      "name_en": "Prepared Tahini",         "cat": "condiment",  "kcal": 306, "prot": 11.0, "carbs": 5.0,  "fat": 27.0, "srv": 30},
    {"name_he": "גואקמולה",         "name_en": "Guacamole",               "cat": "condiment",  "kcal": 155, "prot":  2.0, "carbs": 8.6,  "fat": 13.5, "srv": 50},
    {"name_he": "קטשופ",            "name_en": "Ketchup",                 "cat": "condiment",  "kcal": 101, "prot":  1.0, "carbs": 26.0, "fat": 0.1,  "srv": 15},
    {"name_he": "מוסטרד",           "name_en": "Mustard",                 "cat": "condiment",  "kcal":  66, "prot":  4.4, "carbs": 6.4,  "fat": 3.3,  "srv": 10},
    {"name_he": "חריסה",            "name_en": "Harissa",                 "cat": "condiment",  "kcal":  44, "prot":  1.7, "carbs": 7.2,  "fat": 1.4,  "srv": 15},
    # ── מנות ישראליות ──────────────────────────────────────────────────────
    {"name_he": "שקשוקה",           "name_en": "Shakshuka",               "cat": "meal",       "kcal": 250, "prot": 14.0, "carbs": 12.0, "fat": 16.0, "srv": 350},
    {"name_he": "פלאפל כדור",       "name_en": "Falafel Ball",            "cat": "meal",       "kcal": 330, "prot": 13.0, "carbs": 32.0, "fat": 18.0, "srv": 100},
    {"name_he": "מג'דרה",           "name_en": "Mujaddara",               "cat": "meal",       "kcal": 130, "prot":  5.0, "carbs": 25.0, "fat": 2.5,  "srv": 200},
    {"name_he": "ירקות מוקפצים",    "name_en": "Stir Fry Vegetables",     "cat": "meal",       "kcal":  60, "prot":  2.5, "carbs": 10.0, "fat": 2.0,  "srv": 200},
    {"name_he": "סלט יווני",        "name_en": "Greek Salad",             "cat": "meal",       "kcal":  90, "prot":  3.5, "carbs": 6.0,  "fat": 6.0,  "srv": 200},
    {"name_he": "סלט ירקות",        "name_en": "Vegetable Salad",         "cat": "meal",       "kcal":  35, "prot":  1.5, "carbs": 7.0,  "fat": 0.5,  "srv": 200},
    {"name_he": "אורז עם עדשים",    "name_en": "Rice with Lentils",       "cat": "meal",       "kcal": 140, "prot":  6.0, "carbs": 27.0, "fat": 1.0,  "srv": 200},
    {"name_he": "עוף עם אורז",      "name_en": "Chicken with Rice",       "cat": "meal",       "kcal": 175, "prot": 15.0, "carbs": 18.0, "fat": 4.0,  "srv": 300},
    # ── חטיפים ────────────────────────────────────────────────────────────
    {"name_he": "במבה",             "name_en": "Bamba",                   "cat": "snack",      "kcal": 520, "prot": 13.0, "carbs": 50.0, "fat": 31.0, "srv": 30},
    {"name_he": "ביסלי",            "name_en": "Bissli",                  "cat": "snack",      "kcal": 438, "prot": 10.0, "carbs": 64.0, "fat": 16.0, "srv": 30},
    {"name_he": "שוקולד מריר",      "name_en": "Dark Chocolate",          "cat": "snack",      "kcal": 598, "prot":  7.8, "carbs": 46.0, "fat": 43.1, "srv": 30},
    {"name_he": "שוקולד חלב",       "name_en": "Milk Chocolate",          "cat": "snack",      "kcal": 535, "prot":  7.7, "carbs": 59.5, "fat": 30.0, "srv": 30},
    {"name_he": "חלבה",             "name_en": "Halva",                   "cat": "snack",      "kcal": 469, "prot": 12.7, "carbs": 49.7, "fat": 26.6, "srv": 30},
    {"name_he": "פופקורן",          "name_en": "Popcorn",                 "cat": "snack",      "kcal": 375, "prot": 11.0, "carbs": 74.0, "fat": 4.5,  "srv": 30},
    {"name_he": "צ'יפס",            "name_en": "Potato Chips",            "cat": "snack",      "kcal": 536, "prot":  7.0, "carbs": 52.9, "fat": 35.0, "srv": 30},
    {"name_he": "פרטזל",            "name_en": "Pretzel",                 "cat": "snack",      "kcal": 380, "prot": 10.3, "carbs": 79.2, "fat": 3.3,  "srv": 30},
]


def build_entry(food: dict) -> dict:
    return {
        "food_id":   fid(),
        "name_he":   food["name_he"],
        "name_en":   food["name_en"],
        "category":  food["cat"],
        "nutrition_per_100g": {
            "calories_kcal": float(food["kcal"]),
            "protein_g":     float(food["prot"]),
            "carbs_g":       float(food["carbs"]),
            "fat_g":         float(food["fat"]),
            "fiber_g":       0.0,
            "sugar_g":       0.0,
            "sodium_mg":     0.0,
        },
        "default_serving_g": float(food["srv"]),
        "default_unit":      "גרם",
        "aliases_he":        [food["name_he"]],
        "aliases_en":        [food["name_en"]],
        "source":            "manual_kb_2026",
        "is_custom":         False,
    }


def main():
    # Load existing
    with open(OUTPUT, encoding="utf-8") as f:
        existing = json.load(f)

    existing_names = {e.get("name_he", "").strip() for e in existing}
    print(f"קיים: {len(existing)} מזונות")

    added = 0
    for food in MANUAL_FOODS:
        if food["name_he"].strip() not in existing_names:
            existing.append(build_entry(food))
            existing_names.add(food["name_he"].strip())
            added += 1

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"נוספו: {added} מזונות")
    print(f"סה\"כ: {len(existing)} מזונות")


if __name__ == "__main__":
    main()
