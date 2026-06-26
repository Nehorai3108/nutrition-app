from fastapi import APIRouter, Depends, Query
from typing import Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter
from nutrition_app.agents.agent_11_recipes.unit_converter import enrich_recipe_ingredients
from nutrition_app.repositories.profile_repository import ProfileRepository

router = APIRouter()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_IMAGES_DIR = os.path.join(_PROJECT_ROOT, "storage_agents", "recipe_images", "approved")
_PUBLIC_BASE = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")

_manager = None
def get_manager():
    global _manager
    if _manager is None:
        _manager = RecipeManager()
    return _manager

# Curated Unsplash map + a pre-resolved Wikipedia map (built offline by
# scripts/resolve_recipe_images.py). Both are plain dict lookups — NO network
# calls happen during a request, so meal endpoints stay fast.
_recipe_image_map = None
_recipe_wiki_map = None

def _load_json(rel_path):
    import json
    try:
        with open(os.path.join(_PROJECT_ROOT, rel_path), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _get_recipe_image_map():
    global _recipe_image_map
    if _recipe_image_map is None:
        _recipe_image_map = _load_json(os.path.join("data", "recipe_images.json"))
    return _recipe_image_map

def _get_recipe_wiki_map():
    global _recipe_wiki_map
    if _recipe_wiki_map is None:
        _recipe_wiki_map = _load_json(os.path.join("data", "recipe_wiki_images.json"))
    return _recipe_wiki_map

def enrich_images(recipes):
    """Local approved JPG → curated Unsplash map → pre-resolved Wikipedia map →
    none. All dict/file lookups; no per-request network calls."""
    img_map = _get_recipe_image_map()
    wiki_map = _get_recipe_wiki_map()
    for r in recipes:
        rid = r.get("recipe_id", "")
        local = os.path.join(_IMAGES_DIR, f"{rid}.jpg")
        if os.path.exists(local):
            r["image_url"] = f"{_PUBLIC_BASE}/recipe-images/{rid}.jpg"
        else:
            mapped = img_map.get(rid) or ""
            r["image_url"] = mapped if "images.unsplash.com" in mapped else None
        # Pre-resolved Wikipedia image (offline) — instant dict lookup.
        if not r.get("image_url"):
            r["image_url"] = wiki_map.get(rid) or None
        # Add household-unit display strings (e.g. "4 ביצים") to each ingredient.
        enrich_recipe_ingredients(r)
    return recipes

MEAL_DISTRIBUTION = {
    "BREAKFAST":       0.25,
    "MORNING_SNACK":   0.10,
    "LUNCH":           0.35,
    "AFTERNOON_SNACK": 0.10,
    "DINNER":          0.20,
}

# Breakfast & snacks should be quick/simple (חביתה, סלט, כריך) — cap prep time
# so heavy dishes (ג'חנון, מלאווח, בורקס) aren't suggested for them.
_QUICK_MEALS = {"BREAKFAST", "MORNING_SNACK", "AFTERNOON_SNACK", "EVENING_SNACK"}

# Heavy / labor-intensive dishes that shouldn't be offered as a simple
# breakfast or snack (the user wants חביתה / סלט / כריך, not these).
_HEAVY_DISHES = [
    "סביח", "פלאפל", "ג'חנון", "ג׳חנון", "מלאווח", "מלווח", "לאפה",
    "לחוח", "בורקס", "קובה", "שווארמה", "חמין", "סמבוסק", "ג'ובן",
]

# Real breakfast/snack foods (stems, to catch חביתה/חביתת, גבינה/גבינות, ביצה/ביצים).
_BREAKFAST_FOODS = [
    "חבית", "אומלט", "ביצ", "טוסט", "כריך", "סנדוויץ", "אבוקדו", "יוגורט",
    "גרנולה", "שיבולת שועל", "קוואקר", "דייסה", "שייק", "סמוז", "סמוד",
    "סלט", "גבינ", "קוטג", "לבנה", "פנקייק", "וופל", "לחם", "טונה",
    "שקשוק", "פרי", "קרקר", "חלה", "דגנים", "קורנפלקס", "בייגל", "פריטטה",
]

def _prep_cap(meal_type: str):
    return 20 if meal_type.upper() in _QUICK_MEALS else None

def _exclude_kw(meal_type: str):
    return _HEAVY_DISHES if meal_type.upper() in _QUICK_MEALS else None

def _include_kw(meal_type: str):
    return _BREAKFAST_FOODS if meal_type.upper() in _QUICK_MEALS else None

@router.get("/suggestions/{meal_type}")
def get_meal_suggestions(
    meal_type: str,
    target_calories: Optional[int] = None,
    seed: int = 0,
    user=Depends(get_current_user),
):
    """מחזיר 3 המלצות מתכון לארוחה ספציפית."""
    mgr  = get_manager()
    repo = ProfileRepository()
    prefs = repo.load(user["id"]).get("meal_preferences", {})
    allergens = prefs.get("allergies", [])
    disliked  = prefs.get("disliked_foods", [])

    if not target_calories:
        target_calories = 500

    results = mgr.recommend_meal(
        meal_type=meal_type.upper(),
        target_calories=float(target_calories),
        allergens=allergens or None,
        disliked_foods=disliked or None,
        variation_seed=seed,
        max_prep_minutes=_prep_cap(meal_type),
        exclude_name_keywords=_exclude_kw(meal_type),
        include_name_keywords=_include_kw(meal_type),
    )
    # Build a GOOD pool: composed meals (≥3 ingredients) whose natural calories
    # are already close to the target (gentle scaling → realistic portions).
    tc = float(target_calories)
    def _meal_score(r):
        n = r.get("total_nutrition", {}) or {}
        cal = n.get("calories", 0) or 0
        proximity = abs(cal - tc) / tc if tc else 1.0      # 0 = perfect match
        composed  = -0.20 if len(r.get("ingredients", []) or []) >= 3 else 0.20
        return proximity + composed
    pool = sorted(results, key=_meal_score)[:7]   # the 7 best candidates

    # Rotate WITHIN the good pool by the seed so the picks change day to day
    # (the deterministic sort alone would always show the same 3).
    import random as _random
    rng = _random.Random(seed)
    rng.shuffle(pool)

    out = [_scale_recipe(r, target_calories) for r in pool[:3]]
    enrich_images(out)
    return {"meal_type": meal_type, "recipes": out}

@router.get("/search")
def search_recipes_for_meal(
    q: str,
    target_calories: Optional[int] = None,
    user=Depends(get_current_user),
):
    """חיפוש מתכון לפי שם (מכל הארוחות), מותאם ליעד הקלורי של הארוחה.

    לדוגמה: מחפשים 'שקשוקה' ל-759 קק"ל — מקבלים את השקשוקה כשהכמויות והערכים
    מותאמים בדיוק ליעד.
    """
    mgr = get_manager()
    results = mgr.search_recipes(RecipeFilter(search_text=q, max_results=20))
    out = [_scale_recipe(r, target_calories) for r in results[:10]]
    enrich_images(out)  # also recomputes household-unit displays on scaled amounts
    return {"recipes": out}


def _scale_recipe(recipe: dict, target_calories: Optional[int]) -> dict:
    """Scale a recipe's nutrition + ingredient quantities to a calorie target.

    Clamped tightly (0.7×–1.4×) so portions stay realistic — better to be a bit
    off the target than to tell someone to eat 8 eggs. Never mutates the cache.
    """
    import copy
    rec = copy.deepcopy(recipe)
    n = rec.get("total_nutrition", {}) or {}
    cal = n.get("calories", 0) or 0
    if not target_calories or cal <= 0:
        return rec
    factor = max(0.6, min(1.6, float(target_calories) / cal))
    for k in ("calories", "protein", "carbs", "fat"):
        if n.get(k) is not None:
            n[k] = round(n[k] * factor, 1)
    for ing in rec.get("ingredients", []) or []:
        if ing.get("quantity"):
            ing["quantity"] = round(ing["quantity"] * factor)
    rec["scaled_to_calories"] = round(n.get("calories", 0))
    return rec

@router.get("/plan")
def get_daily_plan(user=Depends(get_current_user)):
    """מחזיר תוכנית יומית מלאה עם 3 הצעות לכל ארוחה."""
    from api.routers.profile import get_targets
    targets = get_targets(user)
    total_cal = targets["calories"]

    mgr  = get_manager()
    repo = ProfileRepository()
    prefs    = repo.load(user["id"]).get("meal_preferences", {})
    allergens = prefs.get("allergies", [])
    disliked  = prefs.get("disliked_foods", [])

    plan = {}
    for meal, ratio in MEAL_DISTRIBUTION.items():
        meal_cal = total_cal * ratio
        suggestions = mgr.recommend_meal(
            meal_type=meal,
            target_calories=meal_cal,
            allergens=allergens or None,
            disliked_foods=disliked or None,
            max_prep_minutes=_prep_cap(meal),
            exclude_name_keywords=_exclude_kw(meal),
            include_name_keywords=_include_kw(meal),
        )
        plan[meal] = {
            "target_calories": round(meal_cal),
            "recipes": enrich_images(suggestions[:3]),
        }

    return {"plan": plan, "total_target": total_cal}


# ── Full-day plan: one recipe per meal, optimized to hit the DAY's macros ──────

def _nutri(rec: dict) -> dict:
    n = rec.get("total_nutrition", {}) or {}
    return {
        "calories": float(n.get("calories") or 0),
        "protein":  float(n.get("protein")  or 0),
        "carbs":    float(n.get("carbs")    or 0),
        "fat":      float(n.get("fat")      or 0),
    }


def _scale_recipe_by_factor(recipe: dict, factor: float) -> dict:
    """Multiply a recipe's nutrition + ingredient quantities by `factor`
    (used to normalize the whole day to the exact calorie target)."""
    import copy
    rec = copy.deepcopy(recipe)
    n = rec.get("total_nutrition", {}) or {}
    for k in ("calories", "protein", "carbs", "fat"):
        if n.get(k) is not None:
            n[k] = round(n[k] * factor, 1)
    for ing in rec.get("ingredients", []) or []:
        if ing.get("quantity"):
            ing["quantity"] = round(ing["quantity"] * factor)
    rec["scaled_to_calories"] = round(n.get("calories", 0))
    return rec


def _combo_norm(combo, target_cal: float):
    """Day totals for a combo AFTER normalizing to the exact calorie target.

    Returns (normalized_totals, factor). The factor is clamped so portions stay
    sane; any residual calorie gap after clamping is reflected in the totals."""
    raw = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for rec in combo:
        n = _nutri(rec)
        for k in raw:
            raw[k] += n[k]
    if raw["calories"] <= 0:
        return raw, 1.0
    factor = max(0.6, min(1.8, target_cal / raw["calories"]))
    return {k: v * factor for k, v in raw.items()}, factor


def _combo_cost(combo, targets) -> float:
    """Lower = better. Encodes the user's priorities on the normalized day:
    hit calories exactly, never undershoot protein, never overshoot fat."""
    tcal  = float(targets.get("calories") or 0) or 1.0
    tprot = float(targets.get("protein")  or 0) or 1.0
    tcarb = float(targets.get("carbs")    or 0) or 1.0
    tfat  = float(targets.get("fat")      or 0) or 1.0
    tot, _ = _combo_norm(combo, tcal)
    cal_dev    = abs(tot["calories"] - tcal) / tcal       # residual after clamp
    prot_under = max(0.0, tprot - tot["protein"]) / tprot  # below protein = bad
    fat_over   = max(0.0, tot["fat"] - tfat) / tfat        # above fat = bad
    carb_dev   = abs(tot["carbs"] - tcarb) / tcarb
    return 4.0 * cal_dev + 2.0 * prot_under + 3.0 * fat_over + 0.4 * carb_dev


@router.get("/full-day-plan")
def get_full_day_plan(seed: int = 0, user=Depends(get_current_user)):
    """תפריט יום שלם בלחיצה — מנה אחת לכל ארוחה, מותאם כך שסך היום פוגע
    ביעדי המאקרו (חלבון/פחמימות/שומן), לא רק בקלוריות. מותאם לאלרגיות
    ולמאכלים שהמשתמש לא אוהב. seed שונה → תפריט אחר (גיוון)."""
    import itertools, random
    from api.routers.profile import get_targets

    targets = get_targets(user)
    total_cal = targets["calories"]

    mgr  = get_manager()
    repo = ProfileRepository()
    prefs     = repo.load(user["id"]).get("meal_preferences", {})
    allergens = prefs.get("allergies", [])
    disliked  = prefs.get("disliked_foods", [])

    # 1. Build a candidate pool per meal — each recipe scaled to that meal's
    #    calorie sub-target (so total calories stay on target automatically).
    K = 4  # candidates per meal kept for the macro search
    meal_candidates = {}
    for meal, ratio in MEAL_DISTRIBUTION.items():
        meal_cal = total_cal * ratio
        suggestions = mgr.recommend_meal(
            meal_type=meal,
            target_calories=meal_cal,
            allergens=allergens or None,
            disliked_foods=disliked or None,
            variation_seed=seed,
            max_prep_minutes=_prep_cap(meal),
            exclude_name_keywords=_exclude_kw(meal),
            include_name_keywords=_include_kw(meal),
        )
        scaled = [_scale_recipe(r, round(meal_cal)) for r in suggestions]
        # Prefer composed meals close to the meal's calorie target.
        def _score(r):
            n = _nutri(r)
            prox = abs(n["calories"] - meal_cal) / meal_cal if meal_cal else 1.0
            composed = -0.2 if len(r.get("ingredients", []) or []) >= 3 else 0.2
            return prox + composed
        pool = sorted(scaled, key=_score)[:K]
        rng = random.Random(seed + hash(meal) % 1000)
        rng.shuffle(pool)
        meal_candidates[meal] = pool or scaled[:1]

    meals = list(meal_candidates.keys())
    pools = [meal_candidates[m] for m in meals]

    # 2. Search combinations (bounded: ≤4^5) for the lowest-cost day (hits
    #    calories, protein floor, fat ceiling). Pick among near-best for variety.
    combos = list(itertools.product(*pools))
    scored = sorted(combos, key=lambda c: _combo_cost(c, targets))
    if scored:
        best = _combo_cost(scored[0], targets)
        near_best = [c for c in scored if _combo_cost(c, targets) <= best + 0.15] or scored[:1]
        chosen = random.Random(seed).choice(near_best)
    else:
        chosen = ()

    # 3. Normalize the chosen day to the EXACT calorie target, then assemble the
    #    response with per-meal precise quantities + the day's totals.
    _, factor = _combo_norm(chosen, float(total_cal))
    plan = {}
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for meal, rec in zip(meals, chosen):
        rec = _scale_recipe_by_factor(rec, factor)
        enrich_images([rec])  # image + household-unit ingredient strings
        n = _nutri(rec)
        for k in totals:
            totals[k] += n[k]
        plan[meal] = {
            "target_calories": round(total_cal * MEAL_DISTRIBUTION[meal]),
            "recipe": rec,
        }

    return {
        "plan": plan,
        "targets": targets,
        "totals": {k: round(v, 1) for k, v in totals.items()},
        "seed": seed,
    }


@router.get("/swap-meal/{meal_type}")
def swap_meal(
    meal_type: str,
    target_calories: int,
    exclude_recipe_id: Optional[str] = None,
    seed: int = 0,
    user=Depends(get_current_user),
):
    """החלפת מנה בודדת — מחזיר מתכון חלופי לארוחה אחת, מותאם לאותו יעד קלורי,
    מכבד אלרגיות/לא-אוהב, ושונה מהמנה הנוכחית (exclude_recipe_id)."""
    mgr  = get_manager()
    repo = ProfileRepository()
    prefs     = repo.load(user["id"]).get("meal_preferences", {})
    allergens = prefs.get("allergies", [])
    disliked  = prefs.get("disliked_foods", [])

    mt = meal_type.upper()
    suggestions = mgr.recommend_meal(
        meal_type=mt,
        target_calories=float(target_calories),
        allergens=allergens or None,
        disliked_foods=disliked or None,
        variation_seed=seed,
        max_prep_minutes=_prep_cap(mt),
        exclude_name_keywords=_exclude_kw(mt),
        include_name_keywords=_include_kw(mt),
    )
    # Drop the current recipe so the swap always changes something.
    pool = [r for r in suggestions if r.get("recipe_id") != exclude_recipe_id]
    pool = pool or suggestions
    if not pool:
        return {"recipe": None}

    scaled = [_scale_recipe(r, target_calories) for r in pool]
    # Closest to the meal's calorie target, prefer composed dishes.
    def _score(r):
        n = _nutri(r)
        prox = abs(n["calories"] - target_calories) / target_calories if target_calories else 1.0
        composed = -0.2 if len(r.get("ingredients", []) or []) >= 3 else 0.2
        return prox + composed
    best_pool = sorted(scaled, key=_score)[:5]
    import random as _random
    rec = _random.Random(seed).choice(best_pool)
    enrich_images([rec])
    return {"recipe": rec, "meal_type": mt}
