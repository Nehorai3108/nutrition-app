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
    key = ("s:" if allow_search else "x:") + (name_en or name_he or "").strip().lower()
    if key in ("s:", "x:"):
        return None

    with _lock:
        cache = _load_cache()
        if key in cache:
            return cache[key] or None

    img = _wiki_image(name_en, "en") or _wiki_image(name_he, "he")
    if not img and allow_search:
        img = _wiki_search_image(name_en, "en") or _wiki_search_image(name_he, "he")

    with _lock:
        cache[key] = img or ""
        _save_cache()
    return img
