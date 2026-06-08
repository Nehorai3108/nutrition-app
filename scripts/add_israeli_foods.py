"""
add_israeli_foods.py — מוסיף מזונות ישראליים נפוצים ל-DB עם שמות עבריים מלאים
הרץ: python scripts/add_israeli_foods.py
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "nutrition.db")

# מזונות ישראליים נפוצים — (food_id, name_he, name_en, category, cal, prot, carbs, fat, fiber, srv_g, unit)
FOODS = [
    # פיצה
    ("il_pizza_001", "פיצה", "Pizza", "CARBOHYDRATE", 266, 11, 33, 10, 2, 150, "פרוסה"),
    ("il_pizza_002", "פיצה מרגריטה", "Pizza Margherita", "CARBOHYDRATE", 250, 10, 31, 9, 2, 150, "פרוסה"),
    ("il_pizza_003", "פיצה פטריות", "Pizza Mushrooms", "CARBOHYDRATE", 245, 10, 30, 9, 2, 150, "פרוסה"),
    ("il_pizza_004", "פיצה טונה", "Pizza Tuna", "CARBOHYDRATE", 255, 12, 30, 10, 2, 150, "פרוסה"),
    ("il_pizza_005", "פיצה ירקות", "Pizza Vegetables", "CARBOHYDRATE", 235, 9, 31, 8, 3, 150, "פרוסה"),
    # סושי
    ("il_sushi_001", "סושי", "Sushi", "CARBOHYDRATE", 145, 6, 27, 2, 1, 200, "מנה"),
    ("il_sushi_002", "מאקי", "Maki Roll", "CARBOHYDRATE", 140, 5, 28, 1, 1, 30, "יחידה"),
    ("il_sushi_003", "ניגירי", "Nigiri", "PROTEIN", 130, 7, 18, 2, 0, 30, "יחידה"),
    ("il_sushi_004", "קליפורניה רול", "California Roll", "CARBOHYDRATE", 155, 5, 25, 4, 1, 200, "מנה"),
    ("il_sushi_005", "סשימי", "Sashimi", "PROTEIN", 130, 22, 0, 4, 0, 100, "מנה"),
    # פסטה מנות
    ("il_pasta_001", "פסטה בולונז", "Pasta Bolognese", "CARBOHYDRATE", 150, 9, 18, 5, 2, 300, "מנה"),
    ("il_pasta_002", "פסטה קרבונרה", "Pasta Carbonara", "CARBOHYDRATE", 200, 10, 20, 10, 1, 300, "מנה"),
    ("il_pasta_003", "פסטה פסטו", "Pasta Pesto", "CARBOHYDRATE", 170, 6, 22, 7, 2, 300, "מנה"),
    ("il_pasta_004", "פסטה ארביאטה", "Pasta Arrabbiata", "CARBOHYDRATE", 140, 5, 25, 4, 2, 300, "מנה"),
    ("il_pasta_005", "לזניה", "Lasagna", "CARBOHYDRATE", 160, 10, 16, 7, 2, 300, "מנה"),
    # מאפים
    ("il_bake_001", "קרואסון", "Croissant", "CARBOHYDRATE", 406, 9, 46, 21, 2, 80, "יחידה"),
    ("il_bake_002", "וופל", "Waffle", "CARBOHYDRATE", 310, 7, 42, 13, 1, 75, "יחידה"),
    ("il_bake_003", "בייגל", "Bagel", "CARBOHYDRATE", 270, 10, 53, 2, 2, 100, "יחידה"),
    ("il_bake_004", "מאפין", "Muffin", "CARBOHYDRATE", 380, 5, 55, 15, 2, 100, "יחידה"),
    ("il_bake_005", "פרנץ טוסט", "French Toast", "CARBOHYDRATE", 230, 8, 28, 10, 1, 120, "מנה"),
    ("il_bake_006", "לחמנייה", "Bread Roll", "CARBOHYDRATE", 280, 9, 50, 4, 2, 60, "יחידה"),
    ("il_bake_007", "חלה", "Challah", "CARBOHYDRATE", 290, 9, 48, 7, 2, 50, "פרוסה"),
    ("il_bake_008", "פיתה לבנה", "White Pita", "CARBOHYDRATE", 255, 9, 52, 1, 2, 60, "יחידה"),
    # קינוחים
    ("il_sweet_001", "גלידה", "Ice Cream", "OTHER", 207, 4, 26, 11, 0, 100, "כדור"),
    ("il_sweet_002", "גלידה שוקולד", "Chocolate Ice Cream", "OTHER", 215, 4, 28, 11, 1, 100, "כדור"),
    ("il_sweet_003", "גלידה וניל", "Vanilla Ice Cream", "OTHER", 200, 4, 24, 11, 0, 100, "כדור"),
    ("il_sweet_004", "עוגת שוקולד", "Chocolate Cake", "OTHER", 370, 5, 52, 17, 2, 100, "פרוסה"),
    ("il_sweet_005", "בראוניז", "Brownies", "OTHER", 420, 5, 58, 20, 2, 60, "יחידה"),
    ("il_sweet_006", "קנאפה", "Knafeh", "OTHER", 380, 7, 50, 18, 1, 150, "מנה"),
    ("il_sweet_007", "בקלאווה", "Baklava", "OTHER", 430, 5, 45, 25, 2, 60, "יחידה"),
    ("il_sweet_008", "חלבה", "Halvah", "OTHER", 510, 12, 57, 29, 3, 30, "כף"),
    ("il_sweet_009", "עוגיית שוקולד צ'יפס", "Chocolate Chip Cookie", "OTHER", 490, 6, 65, 24, 2, 30, "יחידה"),
    ("il_sweet_010", "שוקולד חלב", "Milk Chocolate", "OTHER", 535, 8, 60, 30, 1, 25, "קוביות"),
    # בשר ועוף מנות
    ("il_meat_001", "אנטריקוט", "Entrecote", "PROTEIN", 250, 26, 0, 16, 0, 200, "מנה"),
    ("il_meat_002", "צלעות", "Ribs", "PROTEIN", 290, 24, 0, 21, 0, 200, "מנה"),
    ("il_meat_003", "כבד עוף", "Chicken Liver", "PROTEIN", 165, 25, 1, 6, 0, 100, "מנה"),
    ("il_meat_004", "נקניקיה", "Sausage", "PROTEIN", 290, 11, 3, 26, 0, 60, "יחידה"),
    ("il_meat_005", "כנפי עוף", "Chicken Wings", "PROTEIN", 200, 19, 0, 13, 0, 150, "מנה"),
    # שתייה
    ("il_drink_001", "מיץ תפוחים", "Apple Juice", "BEVERAGE", 46, 0, 11, 0, 0, 200, "כוס"),
    ("il_drink_002", "מיץ ענבים", "Grape Juice", "BEVERAGE", 60, 1, 15, 0, 0, 200, "כוס"),
    ("il_drink_003", "לימונדה", "Lemonade", "BEVERAGE", 40, 0, 10, 0, 0, 300, "כוס"),
    ("il_drink_004", "שייק פירות", "Fruit Shake", "BEVERAGE", 100, 3, 22, 1, 2, 300, "כוס"),
    ("il_drink_005", "שייק חלבון", "Protein Shake", "BEVERAGE", 120, 25, 5, 2, 1, 300, "כוס"),
    ("il_drink_006", "קפה קר", "Iced Coffee", "BEVERAGE", 80, 2, 15, 2, 0, 300, "כוס"),
    ("il_drink_007", "אנרגטיק", "Energy Drink", "BEVERAGE", 45, 0, 11, 0, 0, 250, "פחית"),
    ("il_drink_008", "קוקטייל", "Cocktail", "BEVERAGE", 150, 0, 15, 0, 0, 200, "כוס"),
    ("il_drink_009", "בירה", "Beer", "BEVERAGE", 43, 0, 4, 0, 0, 330, "פחית"),
    ("il_drink_010", "יין אדום", "Red Wine", "BEVERAGE", 85, 0, 3, 0, 0, 150, "כוס"),
    # חטיפים
    ("il_snack_001", "פופקורן", "Popcorn", "OTHER", 375, 11, 74, 4, 14, 30, "קערה"),
    ("il_snack_002", "נאצ'וס", "Nachos", "OTHER", 490, 7, 66, 23, 4, 50, "מנה"),
    ("il_snack_003", "גרנולה בר", "Granola Bar", "OTHER", 400, 7, 60, 14, 3, 40, "יחידה"),
    ("il_snack_004", "חטיף אנרגיה", "Energy Bar", "OTHER", 380, 10, 55, 12, 3, 45, "יחידה"),
    ("il_snack_005", "אגוזי קשיו", "Cashews", "NUT_SEED", 553, 18, 30, 44, 3, 30, "כף"),
    ("il_snack_006", "פיסטוקים", "Pistachios", "NUT_SEED", 562, 20, 28, 45, 10, 30, "כף"),
    # אוכל אסייתי
    ("il_asian_001", "פד תאי", "Pad Thai", "CARBOHYDRATE", 180, 12, 26, 5, 2, 300, "מנה"),
    ("il_asian_002", "אורז מטוגן", "Fried Rice", "CARBOHYDRATE", 160, 5, 28, 4, 1, 250, "מנה"),
    ("il_asian_003", "קארי עוף", "Chicken Curry", "PROTEIN", 150, 14, 10, 6, 2, 300, "מנה"),
    ("il_asian_004", "ריזוטו", "Risotto", "CARBOHYDRATE", 140, 5, 22, 5, 1, 250, "מנה"),
    # ארוחת בוקר
    ("il_bkfst_001", "קוואקר עם חלב", "Oatmeal with Milk", "GRAIN", 145, 6, 24, 3, 4, 250, "קערה"),
    ("il_bkfst_002", "גרנולה עם יוגורט", "Granola with Yogurt", "GRAIN", 200, 8, 30, 6, 3, 200, "קערה"),
    ("il_bkfst_003", "פנקייק", "Pancakes", "CARBOHYDRATE", 227, 6, 34, 8, 1, 150, "מנה"),
    # מזון ים תיכוני
    ("il_med_001", "מוסקה", "Moussaka", "PROTEIN", 160, 9, 12, 9, 2, 300, "מנה"),
    ("il_med_002", "דולמה", "Dolma", "CARBOHYDRATE", 120, 5, 15, 5, 2, 100, "יחידה"),
    ("il_med_003", "כיש", "Quiche", "PROTEIN", 280, 9, 20, 18, 1, 150, "פרוסה"),
    ("il_med_004", "פריחה", "Frittata", "PROTEIN", 190, 12, 5, 14, 1, 200, "מנה"),
    ("il_med_005", "גספאצ'ו", "Gazpacho", "VEGETABLE", 50, 2, 8, 2, 2, 250, "כוס"),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    added = 0
    skipped = 0

    for row in FOODS:
        fid, name_he, name_en, cat, cal, prot, carbs, fat, fiber, srv, unit = row
        # בדוק אם כבר קיים
        c.execute("SELECT food_id FROM foods WHERE food_id = ?", (fid,))
        if c.fetchone():
            skipped += 1
            continue
        c.execute("""
            INSERT INTO foods
            (food_id, name_he, name_en, category, calories_kcal, protein_g, carbs_g, fat_g,
             fiber_g, default_serving_g, default_unit, source, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,'israeli_db',?,?)
        """, (fid, name_he, name_en, cat, cal, prot, carbs, fat, fiber, srv, unit, now, now))
        added += 1

    conn.commit()
    conn.close()
    print(f"Done. Added: {added}, Skipped (already exist): {skipped}")

if __name__ == "__main__":
    main()
