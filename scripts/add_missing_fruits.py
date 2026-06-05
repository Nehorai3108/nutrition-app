"""Add missing fruits & vegetables to foods DB."""
import sqlite3, sys, json
sys.stdout.reconfigure(encoding="utf-8")

DB = "storage/nutrition.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

foods = [
    # (food_id, name_he, name_en, category, cal, prot, carbs, fat, fiber, aliases_he, aliases_en)
    ("f_il_301", "אפרסק",     "Peach",       "fruit", 39,  0.9, 9.5,  0.3, 1.5, '["פרסיק"]',             '["peaches","fresh peach","nectarine"]'),
    ("f_il_302", "שזיף",      "Plum",        "fruit", 46,  0.7, 11.4, 0.3, 1.4, '["שזיפים"]',            '["plums","fresh plum"]'),
    ("f_il_303", "דובדבן",    "Cherry",      "fruit", 63,  1.1, 16.0, 0.2, 2.1, '["דובדבנים"]',          '["cherries","fresh cherry"]'),
    ("f_il_304", "ענב",       "Grape",       "fruit", 69,  0.7, 18.1, 0.2, 0.9, '["ענבים","צימוקים"]',   '["grapes","red grape","green grape","white grape"]'),
    ("f_il_305", "תאנה",      "Fig",         "fruit", 74,  0.8, 19.2, 0.3, 2.9, '["תאנים"]',             '["figs","fresh fig"]'),
    ("f_il_306", "קיווי",     "Kiwi",        "fruit", 61,  1.1, 14.7, 0.5, 3.0, '["קיוי"]',              '["kiwifruit","kiwi fruit"]'),
    ("f_il_307", "אננס",      "Pineapple",   "fruit", 50,  0.5, 13.1, 0.1, 1.4, '[]',                    '["fresh pineapple","pineapple chunks"]'),
    ("f_il_308", "אשכולית",   "Grapefruit",  "fruit", 32,  0.6,  8.0, 0.1, 1.1, '[]',                    '["pomelo","citrus"]'),
    ("f_il_309", "אוכמנית",   "Blueberry",   "fruit", 57,  0.7, 14.5, 0.3, 2.4, '["אוכמניות"]',          '["blueberries"]'),
    ("f_il_310", "פטל",       "Raspberry",   "fruit", 52,  1.2, 11.9, 0.7, 6.5, '[]',                    '["raspberries","red raspberry"]'),
    ("f_il_311", "מלון",      "Melon",       "fruit", 34,  0.8,  8.2, 0.2, 0.9, '["מלונים","קנטלופ"]',   '["cantaloupe","honeydew","muskmelon"]'),
    ("f_il_312", "פפאיה",     "Papaya",      "fruit", 43,  0.5, 11.0, 0.3, 1.7, '[]',                    '["pawpaw"]'),
    ("f_il_313", "אפרסמון",   "Persimmon",   "fruit", 70,  0.6, 18.6, 0.2, 3.6, '["חרמית"]',             '["kaki","sharon fruit"]'),
    ("f_il_314", "ליצ׳י",     "Lychee",      "fruit", 66,  0.8, 16.5, 0.4, 1.3, '[]',                    '["litchi","lichi"]'),
    ("f_il_315", "רימון",     "Pomegranate", "fruit", 83,  1.7, 18.7, 1.2, 4.0, '[]',                    '["pomegranate seeds","pomegranate arils"]'),
    ("f_il_316", "לימון",     "Lemon",       "fruit", 29,  1.1,  9.3, 0.3, 2.8, '["לימונים"]',           '["lemons","citrus lemon"]'),
    ("f_il_317", "ליים",      "Lime",        "fruit", 30,  0.7, 10.5, 0.2, 2.8, '[]',                    '["limes","key lime"]'),
    # ירקות חסרים
    ("f_il_320", "קולרבי",    "Kohlrabi",   "vegetable", 27, 1.7, 6.2, 0.1, 3.6, '[]', '["german turnip"]'),
    ("f_il_321", "שומר",      "Fennel",     "vegetable", 31, 1.2, 7.3, 0.2, 3.1, '[]', '["fennel bulb","anise"]'),
    ("f_il_322", "אספרגוס",   "Asparagus",  "vegetable", 20, 2.2, 3.9, 0.1, 2.1, '[]', '["asparagus spears"]'),
    ("f_il_323", "ארטישוק",   "Artichoke",  "vegetable", 47, 3.3, 10.5, 0.2, 5.4, '[]', '["globe artichoke"]'),
    ("f_il_324", "כרישה",     "Leek",       "vegetable", 61, 1.5, 14.2, 0.3, 1.8, '[]', '["leeks"]'),
    ("f_il_325", "צנון",      "Radish",     "vegetable", 16, 0.7, 3.4, 0.1, 1.6, '["צנוניות"]', '["radishes"]'),
]

added = 0
for f in foods:
    fid, name_he, name_en, cat, cal, prot, carbs, fat, fiber, ali_he, ali_en = f
    cur.execute("SELECT food_id FROM foods WHERE food_id=?", (fid,))
    if cur.fetchone():
        continue
    cur.execute("""
        INSERT INTO foods (food_id, name_he, name_en, category,
            calories_kcal, protein_g, carbs_g, fat_g, fiber_g,
            default_unit, default_serving_g, source,
            aliases_he, aliases_en, is_custom)
        VALUES (?,?,?,?,?,?,?,?,?,'gram',100,'manual',?,?,0)
    """, (fid, name_he, name_en, cat, cal, prot, carbs, fat, fiber, ali_he, ali_en))
    print(f"  ✅ נוסף: {name_he} ({name_en})")
    added += 1

conn.commit()
conn.close()
print(f"\nסה\"כ נוספו: {added} מוצרים")
