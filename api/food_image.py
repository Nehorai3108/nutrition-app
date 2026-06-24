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
}


def _en_term(name_he: str) -> str | None:
    """Most-specific English search term for a Hebrew food name."""
    nm = (name_he or "").strip()
    if not nm:
        return None
    cands = [k for k in _HE_TO_EN if k in nm or nm in k]
    return _HE_TO_EN[max(cands, key=len)] if cands else None


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
        photos = _pexels_search(f"{query} food", per_page=1, api_key=key)
        if photos:
            src = photos[0].get("src", {}) or {}
            return src.get("large") or src.get("medium") or src.get("original")
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
    # A curated English term both drives the Pexels query and disambiguates
    # names Wikipedia gets wrong (melon→hotel).
    en_term = name_en or _en_term(name_he)

    key = ("s:" if allow_search else "x:") + (en_term or name_he or "").strip().lower()
    if key in ("s:", "x:"):
        return None

    with _lock:
        cache = _load_cache()
        if key in cache:
            return cache[key] or None

    # 1. Pexels — appetising photo (same source as recipe images), if a key is set
    img = _pexels_food_image(en_term or name_he)
    # 2. exact Wikipedia title (English term first), then 3. fuzzy search
    if not img:
        img = _wiki_image(en_term, "en") or _wiki_image(name_he, "he")
    if not img and allow_search:
        img = _wiki_search_image(en_term, "en") or _wiki_search_image(name_he, "he")

    with _lock:
        cache[key] = img or ""
        _save_cache()
    return img
