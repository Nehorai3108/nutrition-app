"""
Resolve a representative image URL for a food by name, using Wikipedia's
pageimages API (free, no key). Results are cached on disk so repeated foods
don't re-query.

Used by the chat and manual-search flows so every logged food can show a photo.
"""
import os
import json
import threading
import urllib.parse
import urllib.request

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_PATH = os.path.join(_PROJECT_ROOT, "storage_agents", "food_image_cache.json")

_lock = threading.Lock()
_cache = None


def _load_cache() -> dict:
    global _cache
    if _cache is None:
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    return _cache


def _save_cache() -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False)
    except Exception:
        pass


def _wiki_query(params: dict, lang: str) -> str | None:
    params = {**params, "format": "json", "prop": "pageimages", "pithumbsize": "500"}
    url = f"https://{lang}.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BiteFit/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=8).read())
        for page in data.get("query", {}).get("pages", {}).values():
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                return thumb
    except Exception:
        pass
    return None


# ── Hebrew → English search term for common foods ────────────────────────
# Used to (a) query Pexels for an appetising photo and (b) disambiguate names
# Wikipedia gets wrong (Hebrew "מלון" = melon AND hotel). Most-specific match.
_HE_TO_EN: dict[str, str] = {
    "מלון": "cantaloupe melon", "אבטיח": "watermelon", "בננה": "banana",
    "תפוח עץ": "apple fruit", "תפוז": "orange fruit", "מנגו": "mango",
    "תות": "strawberry", "אבוקדו": "avocado", "ענבים": "grapes", "אגס": "pear",
    "אפרסק": "peach", "קיווי": "kiwi fruit", "תמר": "dates fruit",
    "עגבניות שרי": "cherry tomatoes", "עגבנייה": "tomato", "עגבני": "tomato",
    "מלפפון": "cucumber", "ברוקולי": "broccoli", "גזר": "carrots", "בצל": "onion",
    "פלפל": "bell pepper", "בטטה": "sweet potato", "תפוח אדמה": "potato",
    "חסה": "lettuce", "כרוב": "cabbage",
    "טונה": "canned tuna", "סלמון": "salmon fillet", "חזה עוף": "grilled chicken breast",
    "עוף": "cooked chicken", "הודו": "turkey meat", "ביצים": "fried eggs",
    "ביצה": "fried egg", "פלאפל": "falafel", "שקשוקה": "shakshuka",
    "גבינה צהובה": "cheddar cheese", "גבינה לבנה": "white cheese", "קוטג": "cottage cheese",
    "יוגורט": "yogurt bowl", "חלב": "glass of milk",
    "אורז": "cooked white rice", "פסטה": "pasta", "קינואה": "quinoa",
    "פיתה": "pita bread", "לחם": "bread loaf", "שיבולת שועל": "oatmeal",
    "בורגול": "bulgur", "חומוס": "hummus", "עדשים": "cooked lentils",
    "שקדים": "almonds", "אגוזי מלך": "walnuts", "אגוזים": "mixed nuts",
    "שמן זית": "olive oil", "זיתים": "olives", "טחינה": "tahini",
    "ביצקיט": "biscuit cookie", "פתיבר": "petit beurre cookie",
    "עוגייה": "cookie", "עוגיות": "cookies", "קרקר": "crackers",
    "שוקולד": "chocolate bar", "גרנולה": "granola", "חטיף": "snack bar",
    "אפרסמון": "persimmon", "רימון": "pomegranate", "תאנה": "figs",
    "גבינה": "cheese", "חמאה": "butter", "שמנת": "sour cream",
    "קפה": "coffee cup", "תה": "tea cup", "מיץ": "fruit juice",
    # Common Israeli dishes — clean English so Pexels returns a real photo.
    "שניצל": "chicken schnitzel", "המבורגר": "hamburger", "פיצה": "pizza slice",
    "סושי": "sushi", "מרק": "bowl of soup", "טוסט": "grilled cheese toast",
    "כריך": "sandwich", "סנדוויץ": "sandwich", "בורקס": "bourekas pastry",
    "שווארמה": "shawarma", "נקניקיה": "hot dog", "פנקייק": "pancakes",
    "וופל": "waffle", "קרואסון": "croissant", "מאפין": "muffin",
    "גלידה": "ice cream", "עוגה": "cake slice", "עוגת גבינה": "cheesecake",
    "סלט ירקות": "vegetable salad", "סלט": "green salad", "פירה": "mashed potatoes",
    "צ'יפס": "french fries", "ציפס": "french fries", "פסטרמה": "pastrami",
    "נקניק": "sausage", "קורנפלקס": "corn flakes cereal", "דגני בוקר": "breakfast cereal",
    "בשר בקר": "cooked beef", "בשר טחון": "ground beef cooked",
    "סטייק": "grilled steak", "כבד": "cooked liver",
    "דג": "cooked fish fillet", "אורז מלא": "cooked brown rice",
    "פסטה ברוטב עגבניות": "pasta with tomato sauce", "לזניה": "lasagna",
    "מנקיש": "manakish", "לאפה": "laffa bread", "בגט": "baguette",
    "קוסקוס": "couscous", "פריכיות אורז": "rice cakes", "פופקורן": "popcorn",
    "סיגר בשר": "meat kofta", "סיגרים": "meat kofta", "סיגר": "meat kofta",
    "נקטרינה": "nectarine", "ליצי": "lychee fruit", "קלמנטינה": "clementine",
    "אשכולית": "grapefruit", "שזיף": "plum fruit", "משמש": "apricot fruit",
    "דובדבן": "cherries", "פטל": "raspberries", "אוכמניות": "blueberries",
    # More Israeli/Middle-Eastern dishes and staples.
    "סביח": "sabich pita", "מלווח": "malawach", "גחנון": "jachnun",
    "ג׳חנון": "jachnun", "קובה": "kubbeh", "מגדרה": "mujaddara", "מג׳דרה": "mujaddara",
    "אמבה": "amba mango sauce", "חציל": "eggplant", "במיה": "okra stew",
    "מולוחייה": "molokhia", "פריקה": "freekeh", "מפרום": "yemeni meat stew",
    "פרגית": "grilled chicken thigh", "כבד עוף": "chicken liver",
    "לבבות עוף": "chicken hearts", "קבב": "kebab", "קרעפלך": "kreplach dumplings",
    "גפילטע": "gefilte fish", "חלה": "challah", "רוגלך": "rugelach",
    "עוגת שמרים": "babka", "מלבי": "malabi pudding", "כנאפה": "kanafeh",
    "בקלאווה": "baklava", "קטשופ": "ketchup", "מיונז": "mayonnaise",
    "חרדל": "mustard", "חמוצים": "pickles", "זעתר": "zaatar",
    "ריבה": "fruit jam", "דבש": "honey jar", "חמאת בוטנים": "peanut butter",
    "ממרח שוקולד": "chocolate spread", "קוואקר": "oatmeal", "גרנולה": "granola",
}


def _en_term(name_he: str) -> str | None:
    """Most-specific English search term for a Hebrew food name."""
    nm = (name_he or "").strip()
    if not nm:
        return None
    cands = [k for k in _HE_TO_EN if k in nm or nm in k]
    return _HE_TO_EN[max(cands, key=len)] if cands else None


# Hand-verified DIRECT Wikimedia image URLs for common foods — load instantly in
# React Native, correct topic, no live lookup (so no rate-limits / stale cache).
_W = "https://upload.wikimedia.org/wikipedia/commons"
_CURATED_URLS: dict[str, str] = {
    "מלון": f"{_W}/thumb/a/ae/Meloen_vrucht_met_bloem.jpg/500px-Meloen_vrucht_met_bloem.jpg",
    "אבטיח": f"{_W}/thumb/4/47/Taiwan_2009_Tainan_City_Organic_Farm_Watermelon_FRD_7962.jpg/500px-Taiwan_2009_Tainan_City_Organic_Farm_Watermelon_FRD_7962.jpg",
    "בננה": f"{_W}/d/de/Bananavarieties.jpg",
    "תפוח עץ": f"{_W}/thumb/a/a6/Pink_lady_and_cross_section.jpg/500px-Pink_lady_and_cross_section.jpg",
    "תפוז": f"{_W}/thumb/e/e3/Oranges_-_whole-halved-segment.jpg/500px-Oranges_-_whole-halved-segment.jpg",
    "מנגו": f"{_W}/thumb/7/74/Mangos_-_single_and_halved.jpg/500px-Mangos_-_single_and_halved.jpg",
    "תות": f"{_W}/thumb/4/4c/Garden_strawberry_%28Fragaria_%C3%97_ananassa%29_single2.jpg/500px-Garden_strawberry_%28Fragaria_%C3%97_ananassa%29_single2.jpg",
    "אבוקדו": f"{_W}/thumb/f/f2/Persea_americana_fruit_2.JPG/500px-Persea_americana_fruit_2.JPG",
    "ענבים": f"{_W}/thumb/5/53/Grapes%2C_Rostov-on-Don%2C_Russia.jpg/500px-Grapes%2C_Rostov-on-Don%2C_Russia.jpg",
    "אגס": f"{_W}/thumb/c/cf/Pears.jpg/500px-Pears.jpg",
    "תמר": f"{_W}/thumb/4/45/Dates005.jpg/500px-Dates005.jpg",
    "עגבנייה": f"{_W}/thumb/8/89/Tomato_je.jpg/500px-Tomato_je.jpg",
    "עגבני": f"{_W}/thumb/8/89/Tomato_je.jpg/500px-Tomato_je.jpg",
    "מלפפון": f"{_W}/thumb/9/96/ARS_cucumber.jpg/500px-ARS_cucumber.jpg",
    "ברוקולי": f"{_W}/thumb/0/03/Broccoli_and_cross_section_edit.jpg/500px-Broccoli_and_cross_section_edit.jpg",
    "גזר": f"{_W}/thumb/a/a2/Vegetable-Carrot-Bundle-wStalks.jpg/500px-Vegetable-Carrot-Bundle-wStalks.jpg",
    "בצל": f"{_W}/thumb/a/a2/Mixed_onions.jpg/500px-Mixed_onions.jpg",
    "פלפל": f"{_W}/thumb/8/85/Green-Yellow-Red-Pepper-2009.jpg/500px-Green-Yellow-Red-Pepper-2009.jpg",
    "בטטה": f"{_W}/thumb/5/58/Ipomoea_batatas_006.JPG/500px-Ipomoea_batatas_006.JPG",
    "תפוח אדמה": f"{_W}/thumb/a/ab/Patates.jpg/500px-Patates.jpg",
    "חסה": f"{_W}/thumb/d/da/Iceberg_lettuce_in_SB.jpg/500px-Iceberg_lettuce_in_SB.jpg",
    "טונה": f"{_W}/2/21/Tuna_assortment.png",
    "סלמון": f"{_W}/thumb/3/39/Salmo_salar.jpg/500px-Salmo_salar.jpg",
    "ביצים": f"{_W}/thumb/f/f0/Fried_Egg_2.jpg/500px-Fried_Egg_2.jpg",
    "ביצה": f"{_W}/thumb/f/f0/Fried_Egg_2.jpg/500px-Fried_Egg_2.jpg",
    "הודו": f"{_W}/thumb/a/a3/Thanksgiving_Turkey.jpg/500px-Thanksgiving_Turkey.jpg",
    "יוגורט": f"{_W}/thumb/b/b8/Joghurt.jpg/500px-Joghurt.jpg",
    "חלב": f"{_W}/thumb/a/a5/Glass_of_Milk_%2833657535532%29.jpg/500px-Glass_of_Milk_%2833657535532%29.jpg",
    "גבינה צהובה": f"{_W}/thumb/a/a8/Cheese_platter.jpg/500px-Cheese_platter.jpg",
    "גבינה לבנה": f"{_W}/thumb/7/7b/Skimmed_milk_quark_on_spoon.jpg/500px-Skimmed_milk_quark_on_spoon.jpg",
    "קוטג": f"{_W}/thumb/1/16/Cottagecheese200px.jpg/500px-Cottagecheese200px.jpg",
    "אורז": f"{_W}/thumb/d/d6/Meshi_001.jpg/500px-Meshi_001.jpg",
    "פסטה": f"{_W}/thumb/3/3f/%28Pasta%29_by_David_Adam_Kess_%28pic.2%29.jpg/500px-%28Pasta%29_by_David_Adam_Kess_%28pic.2%29.jpg",
    "קינואה": f"{_W}/thumb/9/96/Reismelde.jpg/500px-Reismelde.jpg",
    "פיתה": f"{_W}/thumb/3/32/Pita_Bread.jpg/500px-Pita_Bread.jpg",
    "לחם": f"{_W}/thumb/2/2c/Wei%C3%9Fbrot-1.jpg/500px-Wei%C3%9Fbrot-1.jpg",
    "חומוס": f"{_W}/thumb/b/bf/Lebanese_style_hummus.jpg/500px-Lebanese_style_hummus.jpg",
    "עדשים": f"{_W}/thumb/f/f5/3_types_of_lentil.png/500px-3_types_of_lentil.png",
    "שקדים": f"{_W}/thumb/3/37/Almonds_-_in_shell%2C_shell_cracked_open%2C_shelled%2C_blanched.jpg/500px-Almonds_-_in_shell%2C_shell_cracked_open%2C_shelled%2C_blanched.jpg",
    "אגוזי מלך": f"{_W}/thumb/b/b2/Walnuts_-_whole_and_open_with_halved_kernel.jpg/500px-Walnuts_-_whole_and_open_with_halved_kernel.jpg",
    "זיתים": f"{_W}/8/84/Olivesfromjordan.jpg",
    "טחינה": f"{_W}/thumb/3/39/Tahina.JPG/500px-Tahina.JPG",
    "שקשוקה": f"{_W}/thumb/1/18/Shakshuka_by_Calliopejen1.jpg/500px-Shakshuka_by_Calliopejen1.jpg",
    "פלאפל": f"{_W}/thumb/5/57/Falafels_2.jpg/500px-Falafels_2.jpg",
    "לחמני": f"{_W}/thumb/1/1d/Kaisersemmel.jpg/500px-Kaisersemmel.jpg",
    "קפה": f"{_W}/thumb/4/45/A_small_cup_of_coffee.JPG/320px-A_small_cup_of_coffee.JPG",
    "סלט כרוב": f"{_W}/thumb/9/97/Coleslaw_%281%29.jpg/500px-Coleslaw_%281%29.jpg",
    "כרוב": f"{_W}/thumb/d/d0/Cabbage_and_cross_section_on_white.jpg/500px-Cabbage_and_cross_section_on_white.jpg",
}


def _curated_url(name_he: str) -> str | None:
    """Hand-verified direct image URL for a common food (most-specific match)."""
    nm = (name_he or "").strip()
    if not nm:
        return None
    cands = [k for k in _CURATED_URLS if k in nm or nm in k]
    return _CURATED_URLS[max(cands, key=len)] if cands else None


def _pexels_food_image(query: str) -> str | None:
    """Appetising food photo from Pexels (the same source as recipe images).
    Returns None when no PEXELS_API_KEY is configured — caller falls back."""
    if not query:
        return None
    try:
        from nutrition_app.agents.agent_recipe_images.image_fetcher import (
            _pexels_search, _get_api_key,
        )
        key = _get_api_key()
        if not key:
            return None
        photos = _pexels_search(query, per_page=1, api_key=key)
        if photos:
            src = photos[0].get("src", {}) or {}
            return src.get("medium") or src.get("large") or src.get("original")
    except Exception:
        pass
    return None


def _wiki_image(title: str, lang: str) -> str | None:
    """Exact-title lookup — accurate for simple foods (apple, pita...)."""
    if not title or not title.strip():
        return None
    return _wiki_query({"action": "query", "titles": title.strip(), "redirects": "1"}, lang)


def _wiki_search_image(query: str, lang: str) -> str | None:
    """Search the closest article and use its image — handles descriptive
    dish names like "toast with yellow cheese" that have no exact article."""
    if not query or not query.strip():
        return None
    return _wiki_query(
        {"action": "query", "generator": "search", "gsrsearch": query.strip(), "gsrlimit": "1"},
        lang,
    )


def get_food_image(name_en: str = "", name_he: str = "", allow_search: bool = True) -> str | None:
    """Return a food image URL (English Wikipedia first, then Hebrew). Cached.

    allow_search=False uses ONLY exact-title lookups (accurate), skipping the
    fuzzy search that can return a loosely-related photo — important for recipe
    names like "פיתה עם חומוס ואמבה" where search wrongly returned shawarma.
    Caches misses as "" so we don't repeatedly query foods with no page image.
    """
    # TRUSTED term = from our curated Hebrew→English food map. A raw catalog
    # name_en is UNTRUSTED — it can be a plain ambiguous word ("Cigar" for the
    # meat pastry "סיגר בשר", "Froop") that Wikipedia resolves to a NON-food
    # (a tobacco cigar). So Wikipedia only ever gets the trusted term; the noisy
    # name_en is used solely to seed a Pexels food-library query.
    trusted = _en_term(name_he)
    en_term = trusted or name_en

    # v4 cache prefix — invalidates entries where an untrusted English name hit
    # Wikipedia and returned a non-food image ("Cigar" → a tobacco cigar).
    key = ("s4:" if allow_search else "x4:") + (en_term or name_he or "").strip().lower()
    if key in ("s4:", "x4:"):
        return None

    with _lock:
        cache = _load_cache()
        if key in cache:
            return cache[key] or None

    # ACCURACY BEFORE PRETTINESS. Pexels returns appetising-but-wrong photos
    # (a fish steak for "tuna", a burger for "roll"), so it goes LAST — only for
    # foods with no accurate match.
    # 1. hand-verified direct Wikimedia URL (exact — e.g. tuna → a tin)
    img = _curated_url(name_he)
    # 2. Wikipedia exact title — ONLY the trusted food term (never a raw name_en,
    #    which risks resolving an ambiguous word to a non-food article).
    if not img and trusted:
        img = _wiki_image(trusted, "en")
    # 3. Pexels — last resort, only when nothing accurate was found. Query ONLY
    #    with a clean English term: a Hebrew query returns random unrelated
    #    photos, so no image (app shows a food icon) is better than a wrong one.
    if not img and allow_search and en_term and en_term.isascii():
        img = _pexels_food_image(en_term)

    with _lock:
        cache[key] = img or ""
        _save_cache()
    return img
