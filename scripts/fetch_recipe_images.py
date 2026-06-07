"""
fetch_recipe_images.py — מוסיף image_url מ-TheMealDB לכל מתכון ב-recipes.json
הרץ פעם אחת: python scripts/fetch_recipe_images.py
"""
import json, time, requests, os

RECIPES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "storage_agents", "recipes", "recipes.json")

def search_meal(name: str) -> str:
    """מחפש מתכון ב-TheMealDB ומחזיר URL של תמונה."""
    try:
        r = requests.get(
            "https://www.themealdb.com/api/json/v1/1/search.php",
            params={"s": name}, timeout=10
        )
        if r.status_code == 200:
            meals = r.json().get("meals") or []
            if meals:
                return meals[0].get("strMealThumb", "")
    except Exception:
        pass
    return ""

def search_by_category(category: str) -> str:
    """מחזיר תמונה של מתכון אקראי מהקטגוריה."""
    cat_map = {
        "chicken": "Chicken", "beef": "Beef", "seafood": "Seafood",
        "pasta": "Pasta", "vegetarian": "Vegetarian", "vegan": "Vegan",
        "breakfast": "Breakfast", "dessert": "Dessert", "lamb": "Lamb",
        "pork": "Pork", "side": "Side", "starter": "Starter",
        "soup": "Soup", "salad": "Salad",
    }
    for key, cat in cat_map.items():
        if key in category.lower():
            try:
                r = requests.get(
                    "https://www.themealdb.com/api/json/v1/1/filter.php",
                    params={"c": cat}, timeout=10
                )
                meals = (r.json().get("meals") or []) if r.status_code == 200 else []
                if meals:
                    import random
                    meal = random.choice(meals[:10])
                    r2 = requests.get(
                        "https://www.themealdb.com/api/json/v1/1/lookup.php",
                        params={"i": meal["idMeal"]}, timeout=10
                    )
                    m = (r2.json().get("meals") or [None])[0]
                    if m:
                        return m.get("strMealThumb", "")
            except Exception:
                pass
    return ""

def guess_category(name_en: str, name_he: str) -> str:
    n = (name_en + " " + name_he).lower()
    if any(w in n for w in ["chicken","עוף","schnitzel","שניצל"]):
        return "chicken"
    if any(w in n for w in ["beef","בקר","steak","meatball","hamburger"]):
        return "beef"
    if any(w in n for w in ["salmon","tuna","fish","sea","דג","סלמון"]):
        return "seafood"
    if any(w in n for w in ["pasta","pesto","lasagna","spaghetti","פסטה"]):
        return "pasta"
    if any(w in n for w in ["cake","chocolate","dessert","cookie","עוגה","שוקולד"]):
        return "dessert"
    if any(w in n for w in ["pancake","waffle","oat","smoothie","breakfast","בוקר"]):
        return "breakfast"
    if any(w in n for w in ["soup","מרק"]):
        return "soup"
    if any(w in n for w in ["salad","סלט"]):
        return "salad"
    if any(w in n for w in ["tofu","vegan","טופו","טבעוני"]):
        return "vegan"
    return "vegetarian"

def main():
    with open(RECIPES_PATH, encoding="utf-8") as f:
        recipes = json.load(f)

    updated = 0
    for i, recipe in enumerate(recipes):
        if recipe.get("image_url") or recipe.get("image_path"):
            continue

        name_en = recipe.get("name_en", "") or ""
        name_he = recipe.get("name_he", "") or ""

        print(f"[{i+1}/{len(recipes)}] {name_en[:40]}", end=" ... ", flush=True)

        url = search_meal(name_en) if name_en else ""
        if not url:
            cat = guess_category(name_en, name_he)
            url = search_by_category(cat)

        if url:
            recipe["image_url"] = url
            updated += 1
            print("OK")
        else:
            print("SKIP")

        time.sleep(0.3)

        if updated % 30 == 0 and updated > 0:
            with open(RECIPES_PATH, "w", encoding="utf-8") as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
            print(f"  >> saved {updated} so far")

    with open(RECIPES_PATH, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    print(f"\nDone. Added {updated} image URLs.")

if __name__ == "__main__":
    main()
