"""
Food Data Agent — Agent 1
Queries USDA FoodData Central API and returns normalized nutrition data.

API docs: https://fdc.nal.usda.gov/api-guide.html
Free key: https://fdc.nal.usda.gov/api-key-signup.html
Set USDA_API_KEY in .env (or environment) before use.

For cache + fallback behaviour use fallback_agent.search_with_fallback() instead
of calling search_food() directly.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional


# ── Config ────────────────────────────────────────────────────────────────────

_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
_SEARCH_ENDPOINT = f"{_BASE_URL}/foods/search"
_TIMEOUT_SEC = 8

# Nutrient IDs in USDA FoodData Central
_NUTRIENT_IDS = {
    "calories": 1008,   # Energy (kcal)
    "protein":  1003,   # Protein
    "carbs":    1005,   # Carbohydrate, by difference
    "fat":      1004,   # Total lipid (fat)
    "fiber":    1079,   # Fiber, total dietary
}


# ── Public API ────────────────────────────────────────────────────────────────

def search_food(name: str) -> dict:
    """
    Search USDA FoodData Central for a food by name.

    Returns a dict:
      {
        "found":        bool,
        "query":        str,
        "food_name":    str | None,
        "fdc_id":       int | None,
        "data_type":    str | None,
        "serving_size": float | None,   # grams
        "calories":     float | None,   # kcal per 100g
        "protein":      float | None,   # g per 100g
        "carbs":        float | None,   # g per 100g
        "fat":          float | None,   # g per 100g
        "fiber":        float | None,   # g per 100g
        "error":        str | None,
      }

    All nutrition values are per 100g.
    If not found or an error occurs, "found" is False and "error" explains why.
    """
    result = _empty_result(name)

    api_key = _load_api_key()
    if not api_key:
        result["error"] = (
            "USDA_API_KEY not set. Add it to .env or set it as an environment variable."
        )
        return result

    params = urllib.parse.urlencode({
        "query":    name,
        "api_key":  api_key,
        "pageSize": 5,
        "dataType": "Foundation,SR Legacy,Survey (FNDDS)",
    })
    url = f"{_SEARCH_ENDPOINT}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SEC) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}: {exc.reason}"
        return result
    except urllib.error.URLError as exc:
        result["error"] = f"Network error: {exc.reason}"
        return result
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"
        return result

    foods = body.get("foods", [])
    if not foods:
        result["error"] = f"No results found for '{name}'"
        return result

    best = foods[0]
    nutrients = {n["nutrientId"]: n["value"] for n in best.get("foodNutrients", [])}

    result["found"]      = True
    result["food_name"]  = best.get("description")
    result["fdc_id"]     = best.get("fdcId")
    result["data_type"]  = best.get("dataType")
    result["serving_size"] = _serving_size(best)
    result["calories"]   = nutrients.get(_NUTRIENT_IDS["calories"])
    result["protein"]    = nutrients.get(_NUTRIENT_IDS["protein"])
    result["carbs"]      = nutrients.get(_NUTRIENT_IDS["carbs"])
    result["fat"]        = nutrients.get(_NUTRIENT_IDS["fat"])
    result["fiber"]      = nutrients.get(_NUTRIENT_IDS["fiber"])
    result["error"]      = None

    return result


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _empty_result(query: str) -> dict:
    return {
        "found":        False,
        "query":        query,
        "food_name":    None,
        "fdc_id":       None,
        "data_type":    None,
        "serving_size": None,
        "calories":     None,
        "protein":      None,
        "carbs":        None,
        "fat":          None,
        "fiber":        None,
        "error":        None,
    }


def _load_api_key() -> Optional[str]:
    """Read API key from environment, then fall back to .env file."""
    key = os.environ.get("USDA_API_KEY", "").strip()
    if key:
        return key

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("USDA_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "DEMO_KEY":
                        return key
    except FileNotFoundError:
        pass
    # DEMO_KEY is accepted as-is (rate-limited but functional for testing)
    if key == "DEMO_KEY":
        return key
    return None


def _serving_size(food: dict) -> Optional[float]:
    """Extract default serving size in grams, if available."""
    measures = food.get("finalFoodInputFoods") or food.get("foodMeasures") or []
    for m in measures:
        grams = m.get("gramWeight")
        if grams:
            return float(grams)
    return None
