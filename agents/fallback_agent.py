"""
Fallback Agent — resolves food queries through a tiered lookup chain:
  1. SQLite cache
  2. USDA FoodData Central
  3. Open Food Facts
  4. unknown_queue (if all fail)
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from food_cache import get_cached, save_to_cache
from food_data_agent import search_food as usda_search
from hebrew_resolver import resolve_hebrew, _is_hebrew
from unknown_queue import add_to_queue

_OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
_TIMEOUT_SEC = 8


# ── Public API ────────────────────────────────────────────────────────────────

def search_with_fallback(query: str) -> dict:
    """
    Resolve a food query using: cache → USDA → Open Food Facts → unknown_queue.

    Returns a result dict compatible with food_data_agent.search_food(),
    with an added "source" key: "cache" | "usda" | "off" | "unknown".
    """
    # 1. Cache (check original query first)
    cached = get_cached(query)
    if cached:
        print(f"[cache] HIT for '{query}'")
        return cached

    # 1b. Hebrew resolution — translate before hitting external APIs
    search_query = query
    if _is_hebrew(query):
        resolved = resolve_hebrew(query)
        if resolved != query:
            print(f"[hebrew] '{query}' -> '{resolved}'")
            # Also check cache for the resolved English term
            cached_en = get_cached(resolved)
            if cached_en:
                print(f"[cache] HIT for resolved '{resolved}'")
                save_to_cache(query, cached_en, cached_en.get("source", "cache"))
                return cached_en
            search_query = resolved

    # 2. USDA
    usda_result = usda_search(search_query)
    if usda_result.get("found"):
        print(f"[usda]  found '{search_query}' -> {usda_result['food_name']}")
        usda_result["source"] = "usda"
        save_to_cache(search_query, usda_result, "usda")
        # Also cache under original Hebrew key so future lookups are instant
        if search_query != query:
            save_to_cache(query, usda_result, "usda")
        return usda_result

    # 3. Open Food Facts
    off_result = _search_open_food_facts(search_query)
    if off_result.get("found"):
        print(f"[off]   found '{search_query}' -> {off_result['food_name']}")
        off_result["source"] = "off"
        save_to_cache(search_query, off_result, "off")
        if search_query != query:
            save_to_cache(query, off_result, "off")
        return off_result

    # 4. All sources failed — queue for manual review
    print(f"[queue] '{query}' not found in any source — added to unknown_queue")
    add_to_queue(query)
    return {
        "found":      False,
        "query":      query,
        "food_name":  None,
        "fdc_id":     None,
        "calories":   None,
        "protein":    None,
        "carbs":      None,
        "fat":        None,
        "fiber":      None,
        "source":     "unknown",
        "error":      f"'{query}' not found in USDA or Open Food Facts. Added to unknown_queue.",
    }


# ── Open Food Facts ───────────────────────────────────────────────────────────

def _search_open_food_facts(query: str) -> dict:
    """Query Open Food Facts and return a normalised result dict."""
    base = {
        "found": False, "query": query, "food_name": None, "fdc_id": None,
        "calories": None, "protein": None, "carbs": None, "fat": None,
        "fiber": None, "source": "off", "error": None,
    }

    params = urllib.parse.urlencode({
        "search_terms": query,
        "json":         1,
        "page_size":    5,
        "fields":       "product_name,nutriments",
    })
    url = f"{_OFF_SEARCH_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NutritionApp/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            body = json.loads(resp.read().decode())
    except Exception as exc:
        base["error"] = f"Open Food Facts error: {exc}"
        return base

    products = body.get("products", [])
    # Pick first product that has at least calorie data
    for product in products:
        nutriments = product.get("nutriments", {})
        calories = nutriments.get("energy-kcal_100g") or nutriments.get("energy_100g")
        if calories is None:
            continue

        base["found"]     = True
        base["food_name"] = product.get("product_name") or query
        base["calories"]  = float(calories)
        base["protein"]   = _safe_float(nutriments.get("proteins_100g"))
        base["carbs"]     = _safe_float(nutriments.get("carbohydrates_100g"))
        base["fat"]       = _safe_float(nutriments.get("fat_100g"))
        base["fiber"]     = _safe_float(nutriments.get("fiber_100g"))
        base["error"]     = None
        return base

    base["error"] = f"Open Food Facts: no usable results for '{query}'"
    return base


def _safe_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
