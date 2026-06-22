from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "storage", "nutrition.db")


@router.get("/insight")
def daily_insight(user=Depends(get_current_user)):
    """תובנה פרואקטיבית של Biti — מבוססת נתוני היום של המשתמש.

    הקוד מחשב את המספרים (יעד, נאכל, נשרף, מה שנותר); הניסוח בעברית
    דטרמיניסטי וטבעי — תלוי במצב בפועל.
    """
    from datetime import date, datetime
    from api._tz import now_il, today_il
    import sqlite3

    # Targets
    try:
        from api.routers.profile import get_targets
        t = get_targets(user)
    except Exception:
        t = {"calories": 2000, "protein": 150, "carbs": 250, "fat": 67}

    # Eaten today
    try:
        from nutrition_app.repositories.food_log_repository import FoodLogRepository
        totals = FoodLogRepository().get_totals(user["id"], today_il())
    except Exception:
        totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "count": 0}

    # Burned today
    burned = 0
    try:
        conn = sqlite3.connect(_DB_PATH)
        row = conn.execute(
            "SELECT COALESCE(SUM(calories_burned),0) FROM workout_log WHERE user_id=? AND date=?",
            (user["id"], today_il().isoformat()),
        ).fetchone()
        burned = round(row[0] or 0)
        conn.close()
    except Exception:
        pass

    eaten_cal = round(totals.get("calories", 0))
    eaten_prot = round(totals.get("protein", 0))
    target_cal = round(t.get("calories", 2000))
    target_prot = round(t.get("protein", 150))
    budget = target_cal + burned
    remaining_cal = budget - eaten_cal
    remaining_prot = target_prot - eaten_prot
    count = totals.get("count", 0)

    hour = now_il().hour
    if hour < 11:
        greet = "בוקר טוב"
    elif hour < 16:
        greet = "צהריים טובים"
    elif hour < 21:
        greet = "ערב טוב"
    else:
        greet = "לילה טוב"

    lines = []
    if count == 0:
        lines.append(f"{greet}! עוד לא רשמת ארוחות היום. היעד שלך הוא {target_cal} קק\"ל.")
        lines.append("ספר לי מה אכלת או צלם ארוחה ואעדכן לך את היומן.")
    else:
        if remaining_cal > 50:
            lines.append(f"{greet}! אכלת {eaten_cal} קק\"ל היום — נשארו לך {remaining_cal} קק\"ל מתוך {budget}.")
        elif remaining_cal < -50:
            lines.append(f"{greet}! עברת את היעד היומי ב-{abs(remaining_cal)} קק\"ל ({eaten_cal} מתוך {budget}).")
        else:
            lines.append(f"{greet}! אתה בדיוק על היעד — {eaten_cal} מתוך {budget} קק\"ל. כל הכבוד!")

        if burned > 0:
            lines.append(f"שרפת היום {burned} קק\"ל באימון — הוספתי אותן לתקציב.")

        if remaining_prot > 25:
            lines.append(f"כדאי להוסיף חלבון — נשארו לך {remaining_prot}g מהיעד היומי.")
        elif remaining_prot <= 5 and eaten_prot > 0:
            lines.append(f"השלמת כמעט את כל יעד החלבון ({eaten_prot}/{target_prot}g) — מצוין.")

    return {
        "message": "\n".join(lines),
        "greeting": greet,
        "target_calories": target_cal,
        "eaten_calories": eaten_cal,
        "burned_calories": burned,
        "remaining_calories": remaining_cal,
        "remaining_protein": remaining_prot,
        "entries": count,
    }

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

@router.post("/")
def chat(body: ChatRequest, user=Depends(get_current_user)):
    """שולח הודעה ל-AI ומקבל תגובה + נתוני מזון."""
    import os
    from groq import Groq
    from nutrition_app.agents.agent_3_food import FoodCatalog
    from nutrition_app.agents.agent_11_recipes.recipe_manager import RecipeManager
    from nutrition_app.agents.agent_11_recipes.recipe_filter import RecipeFilter

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        try:
            import tomllib
            secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".streamlit", "secrets.toml")
            with open(secrets_path, "rb") as f:
                api_key = tomllib.load(f).get("groq_api_key", "")
        except Exception:
            pass
    if not api_key:
        return {"reply": "שגיאה: Groq API key חסר", "food_data": None}

    client = Groq(api_key=api_key)

    inv_ctx = _inventory_context(user["id"])
    nut_ctx = _nutrition_context(user["id"])

    system = f"""You are Biti — a smart Israeli nutrition assistant. Always reply in Hebrew.

USER CONTEXT (live data — use it):
- Inventory (מלאי): {inv_ctx}
- Nutrition targets (יעדים) — USE THESE when suggesting how much to eat:
{nut_ctx}

When the user asks what/how much to eat for a meal (e.g. "כמה ביצים לארוחת בוקר"),
look at that meal's calorie sub-target above and build a concrete suggestion that
roughly hits it. State the meal budget and how your suggestion fits it
(e.g. "יעד ארוחת בוקר ~640 קק\"ל — שקשוקה עם 3 ביצים (~470) + פיתה (~165) ≈ 635").
Be specific with quantities. Never give a generic answer that ignores the budget.

You can ACT for the user by returning a JSON object (inside a ```json block). Use it when relevant:

1. LOG food the user says they ate — include "foods":
   "foods":[{{"name_he":"שם בעברית","name_en":"english","grams":<total grams>,"calories":<total kcal>,"protein":<g>,"carbs":<g>,"fat":<g>}}]
   Estimate realistic portions (ביצה≈55g, פרוסת לחם≈30g, מנת אורז≈180g, חזה עוף≈170g, תפוח≈180g) and compute TOTAL nutrition for the portion described.

2. ADD or REMOVE inventory items when the user asks (e.g. "קניתי עגבניות תוסיף למלאי", "תוריד חלב מהמלאי") — include "actions":
   "actions":[{{"type":"add_inventory","name_he":"עגבניות","quantity":1,"unit":"יח׳","category":"produce"}}]
   type is "add_inventory" or "remove_inventory". category ∈ produce,meat,dairy,bakery,pantry,frozen,beverages,snacks,other.

3. SUGGEST A MEAL / RECIPE — when the user asks for a meal, a recipe, or what to
   cook/eat (e.g. "תכין לי מתכון", "תן לי ארוחת בוקר", "מה לאכול לצהריים") —
   return a STRUCTURED recipe via "recipe". Build it to fit that meal's calorie
   sub-target from the context above:
   "recipe":{{
     "title":"חביתת ירקות עם טונה",
     "meal_type":"breakfast",
     "instructions":["מטגנים בצל וירקות","מוסיפים ביצים טרופות","מערבבים טונה ומגישים"],
     "foods":[{{"name_he":"ביצה","name_en":"egg","grams":110,"calories":160,"protein":13,"carbs":1,"fat":11}},
              {{"name_he":"טונה","name_en":"tuna","grams":100,"calories":116,"protein":26,"carbs":0,"fat":1}}]
   }}
   The "foods" must sum to roughly the meal budget. Keep instructions short (2-5 steps).
   Use realistic portions and compute TOTAL nutrition per food.
   RECIPE RULES (important):
   • List EVERY ingredient the instructions use — including cooking oil/fat
     (שמן זית/חמאה), spices, and anything fried/sautéed in. A fried/sautéed dish
     MUST include שמן זית.
   • Spell every Hebrew food name FULLY and correctly — e.g. "תפוח אדמה" (not
     "תפוח אדם"), "עגבנייה", "מלפפון", "חזה עוף", "שמן זית". No truncated words.

The system REALLY performs the actions — so confirm it's done in your reply (e.g. "הוספתי עגבניות למלאי ✓"). Do NOT ask the user to add it himself.

Always include "reply": one short natural Hebrew sentence.
For plain questions just reply with normal Hebrew text (no JSON).
Hebrew must be spelled fully and correctly — no typos, no truncated words.
name_he must be in Hebrew, NEVER Arabic."""

    messages = [{"role": "system", "content": system}]
    for m in body.history[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": body.message})

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        return _process_model_output(raw, user["id"])
    except Exception as e:
        return {"reply": f"שגיאה: {e}", "food_data": None, "recipe": None}


def _process_model_output(raw: str, user_id: str) -> dict:
    """Turn the raw model reply into the API response (reply + food/recipe/actions).

    Pure glue over _extract_json / _enrich_food / _build_recipe_data / _exec_actions
    — separated from the network call so it can be tested without hitting Groq.
    """
    data = _extract_json(raw)
    reply = raw
    food_data = None
    recipe_data = None
    actions_done = []

    if data:
        reply = (data.get("reply") or "").strip() or "בוצע ✓"
        if isinstance(data.get("foods"), list) and data["foods"]:
            food_data = {
                "meal_type": _normalize_meal_type(data.get("meal_type", "lunch")),
                "foods": [_enrich_food(f) for f in data["foods"]],
            }
        rec = data.get("recipe")
        if isinstance(rec, dict) and isinstance(rec.get("foods"), list) and rec["foods"]:
            meal_type = _normalize_meal_type(rec.get("meal_type", "lunch"))
            rec["meal_type"] = meal_type
            target_cal = _meal_target_calories(user_id, meal_type)
            recipe_data = _build_recipe_data(rec, target_cal)
        if isinstance(data.get("actions"), list) and data["actions"]:
            actions_done = _exec_actions(user_id, data["actions"])

    return {"reply": reply, "food_data": food_data,
            "recipe": recipe_data, "actions": actions_done}


def _build_recipe_data(rec: dict, target_cal: float | None) -> dict:
    """Turn a model recipe into a clean, accurate recipe card.

    - every ingredient recomputed from real per-100g data × grams
    - cooking fat added when the recipe fries/sautés but lists none
    - scaled to the meal's calorie sub-target
    - Hebrew names normalized
    """
    instructions = [s for s in (rec.get("instructions") or []) if s]
    # recompute=True: never trust the model's per-item calories.
    # fetch_image=False: recipe cards show no images — avoid N×8s of latency.
    foods = [_enrich_food(f, recompute=True, fetch_image=False) for f in rec["foods"]]
    foods = _ensure_recipe_has_fat(foods, instructions)
    if target_cal:
        foods = _scale_recipe_to_target(foods, target_cal)
    return {
        "title":          (rec.get("title") or "מתכון").strip(),
        "meal_type":      rec.get("meal_type", "lunch"),
        "instructions":   instructions,
        "foods":          foods,
        "total_calories": round(sum(f.get("calories", 0) for f in foods)),
        "total_protein":  round(sum(f.get("protein", 0) for f in foods)),
        "meal_target":    round(target_cal) if target_cal else None,
    }


def _extract_json(raw: str):
    """Pull the first JSON object out of the model reply (fenced or raw)."""
    import json
    text = raw
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


_MEAL_HE = {
    "breakfast": "ארוחת בוקר",
    "morning_snack": "חטיף בוקר",
    "lunch": "ארוחת צהריים",
    "afternoon_snack": "חטיף צהריים",
    "dinner": "ארוחת ערב",
    "evening_snack": "חטיף ערב",
    "snack": "חטיף",
}


_MEAL_ALIASES = {
    "breakfast": "breakfast", "morning": "breakfast", "בוקר": "breakfast",
    "ארוחת בוקר": "breakfast", "ארוחתבוקר": "breakfast",
    "morning_snack": "morning_snack", "חטיף בוקר": "morning_snack",
    "lunch": "lunch", "noon": "lunch", "צהריים": "lunch",
    "ארוחת צהריים": "lunch", "ארוחתצהריים": "lunch",
    "afternoon_snack": "afternoon_snack", "חטיף צהריים": "afternoon_snack",
    "dinner": "dinner", "evening": "dinner", "ערב": "dinner",
    "ארוחת ערב": "dinner", "ארוחתערב": "dinner",
    "evening_snack": "evening_snack", "חטיף ערב": "evening_snack",
    "snack": "snack", "חטיף": "snack",
}


def _normalize_meal_type(meal_type: str) -> str:
    """Map any meal label (English caps, Hebrew, spaced) to a canonical key."""
    if not meal_type:
        return "lunch"
    mt = meal_type.strip().lower()
    if mt in _MEAL_ALIASES:
        return _MEAL_ALIASES[mt]
    # substring fallback (e.g. "ארוחת בוקר קלה")
    for alias, canon in _MEAL_ALIASES.items():
        if alias in mt or mt in alias:
            return canon
    return "lunch"


def _meal_target_calories(user_id: str, meal_type: str) -> float | None:
    """Calorie sub-target for a given meal today (remaining budget aware)."""
    try:
        from api.routers.profile import compute_targets, build_user_profile
        from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
        from nutrition_app.repositories.food_log_repository import FoodLogRepository
        from nutrition_app.repositories.profile_repository import ProfileRepository
        from api._tz import today_il

        p = ProfileRepository().load(user_id)
        if not p.get("weight_kg"):
            return None
        base = compute_targets(user_id)
        if base is None:
            return None
        profile = build_user_profile(p, user_id)
        engine = AdaptationEngine()
        day = engine.adjusted_day_target(profile, base)

        entries = FoodLogRepository().get_log(user_id, today_il())
        meals_logged = {}
        for e in entries:
            mt = (e.meal_type or "lunch").lower()
            meals_logged[mt] = meals_logged.get(mt, 0.0) + (e.calories or 0)

        subs = engine.meal_subtargets(profile, base, day, meals_logged)
        mt = _normalize_meal_type(meal_type)
        for s in subs:
            if s.meal_type == mt:
                return float(s.calories)
        return None
    except Exception:
        return None


def _scale_recipe_to_target(foods: list, target_cal: float) -> list:
    """Scale every ingredient proportionally so the recipe hits the meal budget."""
    current = sum(f.get("calories", 0) for f in foods)
    if current <= 0 or not target_cal or target_cal <= 0:
        return foods
    factor = target_cal / current
    # ignore tiny corrections; only rescale when meaningfully off
    if abs(factor - 1.0) < 0.08:
        return foods
    for f in foods:
        for k in ("grams", "calories", "protein", "carbs", "fat"):
            if f.get(k) is not None:
                f[k] = round(f[k] * factor, 1)
        if f.get("grams") is not None:
            f["grams"] = round(f["grams"])
        if f.get("calories") is not None:
            f["calories"] = round(f["calories"])
    return foods


def _nutrition_context(user_id: str) -> str:
    """
    Build a live nutrition briefing for the chat model: today's adjusted target,
    what's been eaten, what remains, and per-meal calorie/protein budgets.
    """
    try:
        from api.routers.profile import compute_targets
        from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine
        from nutrition_app.repositories.food_log_repository import FoodLogRepository
        from api.routers.profile import build_user_profile
        from nutrition_app.repositories.profile_repository import ProfileRepository
        from api._tz import today_il

        p = ProfileRepository().load(user_id)
        if not p.get("weight_kg"):
            return "  (פרופיל לא הוגדר — אין יעדים)"

        base = compute_targets(user_id)
        if base is None:
            return "  (אין יעדים זמינים)"

        profile = build_user_profile(p, user_id)
        engine = AdaptationEngine()
        day = engine.adjusted_day_target(profile, base)

        # eaten so far, grouped by meal
        entries = FoodLogRepository().get_log(user_id, today_il())
        meals_logged = {}
        for e in entries:
            mt = (e.meal_type or "lunch").lower()
            meals_logged[mt] = meals_logged.get(mt, 0.0) + (e.calories or 0)

        subs = engine.meal_subtargets(profile, base, day, meals_logged)
        eaten = round(sum(meals_logged.values()))
        remaining = round(day.calories - eaten)

        lines = [
            f"  יעד יומי: {day.calories} קק\"ל · חלבון {round(day.protein_g)}g · "
            f"פחמ' {round(day.carbs_g)}g · שומן {round(day.fat_g)}g",
            f"  נאכל היום: {eaten} קק\"ל · נותרו: {remaining} קק\"ל",
        ]
        if subs:
            lines.append("  יעד לכל ארוחה שעוד לא נאכלה:")
            for s in subs:
                name = _MEAL_HE.get(s.meal_type, s.meal_type)
                lines.append(f"    • {name}: ~{s.calories} קק\"ל (חלבון {round(s.protein_g)}g)")
        return "\n".join(lines)
    except Exception:
        return "  (לא זמין)"


def _inventory_context(user_id: str) -> str:
    try:
        from api.routers.inventory import _list_items
        rows = _list_items(user_id)[:40]
        if not rows:
            return "ריק (אין מוצרים)"
        return ", ".join(f"{r.get('name_he')} ({_fmt_q(r.get('quantity'))} {r.get('unit')})" for r in rows)
    except Exception:
        return "לא זמין"


def _fmt_q(q):
    try:
        q = float(q)
        return int(q) if q == int(q) else round(q, 1)
    except (TypeError, ValueError):
        return q


def _exec_actions(user_id: str, actions: list) -> list:
    """Execute inventory add/remove actions via the shared inventory storage
    (Supabase in the cloud, SQLite locally) — same store the inventory list reads."""
    from api.routers.inventory import _add_item, _list_items, _use_sb, _sb, _conn
    done = []
    for a in actions:
        if not isinstance(a, dict):
            continue
        t = (a.get("type") or "").lower().strip()
        name = (a.get("name_he") or a.get("name") or "").strip()
        if not name:
            continue
        try:
            if t in ("add_inventory", "add"):
                try:
                    qty = float(a.get("quantity") or 1)
                except (TypeError, ValueError):
                    qty = 1
                _add_item(user_id, name, qty, a.get("unit") or "יח׳", a.get("category") or "other")
                done.append({"op": "added", "name": name})
            elif t in ("remove_inventory", "remove", "delete"):
                if _use_sb():
                    # מצא פריטים תואמים ומחק לפי item_id (אין LIKE ב-PostgREST פשוט)
                    for it in _list_items(user_id):
                        if name in (it.get("name_he") or ""):
                            _sb().table("inventory").delete().eq("item_id", it["item_id"]).execute()
                else:
                    with _conn() as c:
                        c.execute("DELETE FROM inventory WHERE user_id=? AND name_he LIKE ?",
                                  (user_id, f"%{name}%"))
                        c.commit()
                done.append({"op": "removed", "name": name})
        except Exception:
            pass
    return done


# ── Hebrew food-name normalization ───────────────────────────────────────
# Common typos / truncations the model produces → canonical Hebrew spelling.
_NAME_FIXES = {
    "תפוח אדם": "תפוח אדמה",
    "תפוח אדמ": "תפוח אדמה",
    "תפוחי אדמ": "תפוחי אדמה",
    "בטטה מתוקה": "בטטה",
    "חזה עו": "חזה עוף",
    "שמן זי": "שמן זית",
    "גבינה צהוב": "גבינה צהובה",
    "גבינה לבנ": "גבינה לבנה",
    "עגבני": "עגבנייה",
    "עגבניה": "עגבנייה",
    "מלפפו": "מלפפון",
    "פטריו": "פטריות",
    "פטרי": "פטרייה",
    "בצ": "בצל",
    "אבוקד": "אבוקדו",
    "קינוא": "קינואה",
    "עדשי": "עדשים",
    "שקדי": "שקדים",
    "אגוז": "אגוזים",
    "ביצי": "ביצים",
    "פלפ": "פלפל",
    "ברוקול": "ברוקולי",
    "טחינ": "טחינה",
    "חומו": "חומוס",
    "יוגור": "יוגורט",
    "סלמו": "סלמון",
    "טונ": "טונה",
    "בטט": "בטטה",
    "פסט": "פסטה",
    "פסט'": "פסטה",
    "גזר": "גזר",
    "לח": "לחם",
    "אור": "אורז",
    "במב": "במבה",
    "חלב": "חלב",
    "תפו": "תפוח",
    "בננ": "בננה",
    "תמר": "תמר",
    "פיתה לבנ": "פיתה לבנה",
    "טופ": "טופו",
    "קוטג": "קוטג'",
}

_canonical_names_cache: list | None = None


def _canonical_names() -> list:
    """All known canonical Hebrew food names (IL table + catalog), cached."""
    global _canonical_names_cache
    if _canonical_names_cache is not None:
        return _canonical_names_cache
    names = set()
    try:
        from api.routers.camera import _IL_FOODS
        names.update(_IL_FOODS.keys())
    except Exception:
        pass
    try:
        from nutrition_app.agents.agent_3_food import FoodCatalog
        for fd in FoodCatalog().get_all_foods():
            if fd.name_he:
                names.add(fd.name_he.strip())
            for a in (fd.aliases_he or []):
                if a:
                    names.add(a.strip())
    except Exception:
        pass
    _canonical_names_cache = sorted(names, key=len, reverse=True)
    return _canonical_names_cache


def _normalize_food_name(name_he: str) -> str:
    """Fix typos/truncations and snap to a canonical Hebrew food name."""
    name = (name_he or "").strip()
    if not name:
        return name
    # 1. explicit typo/truncation fixes
    if name in _NAME_FIXES:
        return _NAME_FIXES[name]
    # 2. already canonical
    canon = _canonical_names()
    if name in canon:
        return name
    # 3. prefix/truncation snap: the model dropped trailing letters
    #    (e.g. "תפוח אדמ" → "תפוח אדמה"). Only when unambiguous & close.
    matches = [c for c in canon if c.startswith(name) and 0 < len(c) - len(name) <= 2]
    if len(matches) == 1:
        return matches[0]
    # 4. the model added a trailing letter (rare): name⊃canon
    matches = [c for c in canon if name.startswith(c) and 0 < len(name) - len(c) <= 2]
    if len(matches) == 1:
        return matches[0]
    return name


# ── Recipe completeness: ensure cooking fat is present ────────────────────
_COOK_VERBS = ("מטגנ", "מטוגן", "מוקפצ", "מקפיצ", "צולי", "צלוי", "אופ", "מאדים",
               "מבשל", "טיגון", "קפיצ", "מזהיב")
_FAT_HINTS = ("שמן", "חמאה", "מרגרינה", "טחינה", "מיונז")


def _ensure_recipe_has_fat(foods: list, instructions: list) -> list:
    """If the recipe involves cooking but lists no fat, add olive oil so the
    calorie count reflects reality (frying/sautéing always adds oil)."""
    text = " ".join(instructions or [])
    cooks = any(v in text for v in _COOK_VERBS)
    has_fat = any(any(h in (f.get("name_he") or "") for h in _FAT_HINTS) for f in foods)
    if cooks and not has_fat:
        foods.append(_enrich_food(
            {"name_he": "שמן זית", "name_en": "olive oil", "grams": 10},
            recompute=True, fetch_image=False,
        ))
    return foods


def _resolve_per_100g(name_he: str, name_en: str) -> dict | None:
    """Resolve trustworthy per-100g nutrition for a food name.

    Order: curated Israeli table → FoodCatalog → AI estimator. Used to compute
    ingredient calories from grams instead of trusting the model's arithmetic.
    """
    # 1. curated Israeli table (most reliable for common foods).
    #    Read _IL_FOODS directly for TRUE per-100g values — _lookup_il_table
    #    clamps to portion bounds, which would corrupt a per-100g lookup.
    try:
        from api.routers.camera import _IL_FOODS
        nm = (name_he or "").strip()
        best = None
        if nm in _IL_FOODS:
            best = nm
        else:
            cands = [k for k in _IL_FOODS if (k in nm or nm in k)]
            if cands:
                best = max(cands, key=len)
        if best:
            kcal, prot, carbs, fat = _IL_FOODS[best]
            return {"calories": kcal, "protein": prot, "carbs": carbs, "fat": fat}
    except Exception:
        pass
    # 2. FoodCatalog
    try:
        from nutrition_app.agents.agent_3_food import FoodCatalog
        cat = FoodCatalog()
        q = (name_he or "").lower().strip()
        for fd in cat.get_all_foods():
            aliases = (fd.aliases_he or []) + [fd.name_he or ""]
            if any(q and (q in a.lower() or a.lower() in q) for a in aliases if a):
                m = fd.macros_for_grams(100.0)
                return {"calories": round(m.get("calories_kcal", 0)),
                        "protein": round(m.get("protein_g", 0), 1),
                        "carbs": round(m.get("carbs_g", 0), 1),
                        "fat": round(m.get("fat_g", 0), 1)}
    except Exception:
        pass
    # 3. AI estimator
    try:
        from api.nutrition_ai import estimate_nutrition_per_100g
        est = estimate_nutrition_per_100g(name_he)
        if est:
            return {"calories": est["calories"], "protein": est["protein"],
                    "carbs": est["carbs"], "fat": est["fat"]}
    except Exception:
        pass
    return None


def _enrich_food(food: dict, recompute: bool = False, fetch_image: bool = True) -> dict:
    """Guarantee a chat-detected food has grams + total calories/macros.

    When recompute=True (recipe ingredients), calories/macros are ALWAYS derived
    from resolved per-100g nutrition × grams — the model's per-item numbers are
    discarded (it routinely hallucinates, e.g. 665 kcal for 200g of vegetables).
    When False (logging what the user said they ate), the model's numbers are
    trusted and only filled in if missing.

    fetch_image=False skips the (per-food, up-to-8s) Wikipedia image lookup —
    used for recipe ingredients, where the card shows no images anyway.
    """
    name_he = food.get("name_he") or food.get("name") or "מזון"
    name_en = food.get("name_en") or food.get("name") or name_he
    # Block Arabic leaking into name_he — fall back to the English name.
    if any("؀" <= ch <= "ۿ" for ch in name_he):
        name_he = name_en
    name_he = _normalize_food_name(name_he)

    try:
        grams = float(food.get("grams") or 0)
    except (TypeError, ValueError):
        grams = 0.0
    if grams <= 0:
        grams = 100.0

    def _num(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    cal = _num(food.get("calories"))
    prot = _num(food.get("protein"))
    carbs = _num(food.get("carbs"))
    fat = _num(food.get("fat"))

    # Sanity guard: implausible energy density (>9 kcal/g is impossible — pure
    # fat is 9). Forces a recompute for any food the model wildly over-counted.
    implausible = grams > 0 and cal / grams > 6.0

    if recompute or cal <= 0 or implausible:
        per100 = _resolve_per_100g(name_he, name_en)
        if per100:
            f = grams / 100.0
            cal   = round(per100["calories"] * f)
            prot  = round(per100["protein"] * f, 1)
            carbs = round(per100["carbs"] * f, 1)
            fat   = round(per100["fat"] * f, 1)

    image_url = None
    if fetch_image:
        try:
            from api.food_image import get_food_image
            image_url = get_food_image(name_en, name_he)
        except Exception:
            image_url = None

    return {
        "name": name_en,
        "name_he": name_he,
        "grams": round(grams),
        "calories": round(cal),
        "protein": round(prot, 1),
        "carbs": round(carbs, 1),
        "fat": round(fat, 1),
        "image_url": image_url,
        # keep originals for display
        "quantity": food.get("quantity"),
        "unit": food.get("unit"),
    }
