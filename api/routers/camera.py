from fastapi import APIRouter, Depends, UploadFile, File, Request
from api.deps import get_current_user
import sys, os, base64, json, requests, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_PHOTOS_DIR   = os.path.join(_PROJECT_ROOT, "storage_agents", "food_photos")
_PUBLIC_BASE  = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")

# ── Realistic portion bounds per food (grams) — prevents AI hallucinations ──
# (min_g, max_g) — AI estimate is clamped to this range if food is matched
_PORTION_BOUNDS: dict[str, tuple] = {
    "פיתה":         (45,  90),
    "לחם":          (20,  80),   # 1-2 פרוסות
    "קרואסון":      (50,  90),
    "בייגל":        (80, 130),
    "ביצה":         (45,  80),   # ביצה אחת
    "חביתה":        (80, 200),
    "בננה":         (80, 160),
    "תפוח":         (100, 220),
    "תפוז":         (130, 250),
    "אבוקדו":       (70, 200),   # חצי עד שלם
    "שוקולד":       (10,  60),
    "טחינה גולמית": (10,  40),   # כף-שתיים
    "שמן זית":      (5,   30),
    "חמאה":         (5,   25),
    "גבינה צהובה":  (15,  60),   # 1-2 פרוסות
    "כדור פלאפל":   (15,  25),   # כדור אחד
    "פלאפל":        (80, 200),   # מנה
}

# ── Israeli food reference: name variants → (kcal, protein, carbs, fat) per 100g ──
# Source: planner knowledge base + USDA/FoodsDictionary (verified 2026)
_IL_FOODS: dict[str, tuple] = {
    # (kcal, protein_g, carbs_g, fat_g) per 100g
    "חזה עוף":          (165, 31.0, 0.0,  3.6),
    "עוף":              (165, 31.0, 0.0,  3.6),
    "שוק עוף":          (215, 26.0, 0.0, 12.0),
    "הודו":             (135, 30.0, 0.0,  1.0),
    "שניצל הודו":       (230, 20.0, 12.0, 11.0),
    "סלמון":            (208, 20.0, 0.0, 13.0),
    "טונה במים":        (116, 26.0, 0.0,  1.0),
    "טונה בשמן":        (190, 24.0, 0.0, 10.0),
    "ביצה":             (155, 13.0, 1.1, 11.0),
    "חביתה":            (155, 11.0, 1.0, 11.0),
    "קוטג' 5%":         (103, 11.0, 3.5,  5.0),
    "קוטג'":            (103, 11.0, 3.5,  5.0),
    "גבינה צהובה":      (350, 25.0, 1.0, 28.0),
    "גבינה לבנה":       (100,  8.0, 3.0,  6.0),
    "לבנה":             (150,  6.0, 4.0, 12.0),
    "יוגורט":           ( 95,  6.0, 4.0,  5.0),
    "חלב 3%":           ( 62,  3.2, 4.8,  3.0),
    "חומוס מרוח":       (180,  8.0,11.0, 11.6),
    "עדשים מבושלות":    (116,  9.0,20.0,  0.4),
    "חומוס מבושל":      (164,  8.9,27.4,  2.6),
    "טחינה גולמית":     (655, 24.0, 4.5, 57.0),
    "טחינה מוכנה":      (306, 11.0, 5.0, 27.0),
    "פיתה לבנה":        (275,  9.0,55.0,  1.5),
    "פיתה מלאה":        (267, 10.0,50.0,  2.5),
    "לחם לבן":          (265,  9.0,49.0,  3.0),
    "לחם מלא":          (247, 13.0,41.0,  3.5),
    "אורז לבן מבושל":   (130,  2.7,28.0,  0.3),
    "אורז חום מבושל":   (111,  2.6,23.0,  0.9),
    "פסטה מבושלת":      (131,  5.0,25.0,  1.1),
    "קינואה מבושלת":    (120,  4.4,21.3,  1.9),
    "בורגול מבושל":     ( 83,  3.0,19.0,  0.2),
    "שיבולת שועל":      (389, 17.0,66.0,  7.0),
    "בננה":             ( 89,  1.1,23.0,  0.3),
    "תפוח":             ( 52,  0.3,14.0,  0.2),
    "אבוקדו":           (160,  2.0, 9.0, 15.0),
    "עגבנייה":          ( 18,  0.9, 3.9,  0.2),
    "מלפפון":           ( 15,  0.7, 3.6,  0.1),
    "גזר":              ( 41,  0.9, 9.6,  0.2),
    "ברוקולי":          ( 34,  2.8, 7.0,  0.4),
    "תרד":              ( 23,  2.9, 3.6,  0.4),
    "בטטה מבושלת":      ( 86,  1.6,20.1,  0.1),
    "תפוח אדמה מבושל":  ( 77,  2.0,17.0,  0.1),
    "פלאפל":            (330, 13.0,32.0, 18.0),
    "שקשוקה":           (250, 14.0,12.0, 16.0),
    "סלט ירקות":        ( 35,  1.5, 7.0,  0.5),
    "שמן זית":          (884,  0.0, 0.0,100.0),
    "אגוזי מלך":        (654, 15.0,14.0, 65.0),
    "שקדים":            (579, 21.0,22.0, 49.0),
    "במבה":             (520, 13.0,50.0, 31.0),
}

# ── Portion reference rules (embedded in prompt) ──────────────────────
_PORTION_RULES = """
PORTION ESTIMATION — CRITICAL RULES:

Visual anchors (use plate/bowl/hand as scale):
• Full dinner plate (26-28cm) of pasta/rice = 250-350g
• Half dinner plate of starch = 130-175g
• Full bowl (500ml) of salad = 200-350g
• Standard pita bread = 60g (white), 70g (whole wheat)
• Slice of bread = 30-35g
• Grilled chicken breast (full, visible) = 150-200g
• Grilled chicken thigh = 100-140g
• Fish fillet = 120-180g
• Egg = 55g (medium), 65g (large)
• Tablespoon of spread (hummus/tahini) = 15g
• Coffee mug = 240ml
• Glass = 200-250ml
• Small bowl of hummus restaurant portion = 100-150g
• Avocado half = 70-90g
• Medium banana = 120g, medium apple = 160g, orange = 200g

Israeli portion norms:
• Shakshuka serving (2 eggs in sauce) ≈ 350g total
• Falafel ball = 20g each (5 balls = 100g)
• Restaurant hummus plate = 150g hummus + pita + oil
• Schnitzel (turkey/chicken) = 120-180g
• Home rice portion = 180-220g cooked
• Salad plate = 200-300g

Cooking method adjustments:
• Fried adds ~15-25% calories vs raw weight
• Grilled/baked: use cooked weight (shrinks ~25%)
• If food is in a sauce, estimate sauce separately

NEVER default to 100g unless the portion IS literally 100g.
If multiple foods on one plate: identify and estimate EACH separately.
"""

# ── Accuracy rules ─────────────────────────────────────────────────────
_ACCURACY_RULES = """
ACCURACY — distinguish look-alike foods:
• Cucumber (מלפפון) vs melon (מלון): cucumber is long, thin, dark green; melon is large, round, pale netted skin. Salad context → cucumber.
• Zucchini (קישוא) vs cucumber: zucchini is thicker, lighter green, often cooked
• Tahini sauce (טחינה) vs yogurt: tahini is beige/golden; yogurt is white
• Hummus vs tahini spread: hummus is chunky beige; tahini is smooth pale
• Labaneh vs cream cheese: labaneh in Israeli context, usually with za'atar and oil
• When uncertain, choose the more common everyday food over the exotic option
• Sweet potato (בטטה) vs regular potato: sweet potato is orange inside
"""


@router.post("/identify")
async def identify_food(request: Request, file: UploadFile = File(...), user=Depends(get_current_user)):
    """מקבל תמונה → זיהוי מזון + הערכת כמות + ערכי תזונה מדויקים מהקטלוג."""
    # Free-tier rate limit (food-photo scan is the most expensive feature).
    from api.usage import check_and_consume, is_owner
    if not is_owner(user.get("email")):
        gate = check_and_consume(user["id"], "camera")
        if not gate["allowed"]:
            return {
                "items": [],
                "limit_reached": True,
                "remaining": 0,
                "limit": gate["limit"],
                "message": f"הגעת למכסת היומית של {gate['limit']} צילומים. "
                           f"שדרג ל-Pro לצילום ללא הגבלה.",
            }

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        try:
            import tomllib
            secrets_path = os.path.join(_PROJECT_ROOT, ".streamlit", "secrets.toml")
            with open(secrets_path, "rb") as f:
                api_key = tomllib.load(f).get("groq_api_key", "")
        except Exception:
            pass

    image_bytes = await file.read()

    # שמור תמונה
    image_url = None
    try:
        os.makedirs(_PHOTOS_DIR, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.jpg"
        with open(os.path.join(_PHOTOS_DIR, fname), "wb") as fh:
            fh.write(image_bytes)
        base = os.environ.get("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
        image_url = f"{base}/food-photos/{fname}"
    except Exception:
        pass

    if not api_key:
        return {"items": [], "image_url": image_url, "error": "GROQ_API_KEY missing"}

    img_b64 = base64.b64encode(image_bytes).decode()

    prompt = f"""You are an expert Israeli nutritionist and food recognition AI.

TASK: Analyze this food photo and return accurate nutrition data.

{_PORTION_RULES}

{_ACCURACY_RULES}

LANGUAGE RULE:
• "name_he" MUST be in HEBREW only — NEVER Arabic.
• Examples: apple="תפוח", chicken="עוף", bread="לחם", rice="אורז", egg="ביצה"

OUTPUT FORMAT — return ONLY a JSON array, no markdown, no text:
[{{"name": "English name", "name_he": "שם בעברית", "grams": <portion grams>, "calories": <total kcal for that portion>, "protein": <total protein g>, "carbs": <total carbs g>, "fat": <total fat g>, "confidence": <0.0-1.0>}}]

NUTRITION CALCULATION:
• calories = (calories_per_100g / 100) × grams
• protein  = (protein_per_100g  / 100) × grams
• etc.
• A typical full home-cooked meal = 500-800 kcal total
• A light salad plate = 150-300 kcal
• If multiple items visible, list EACH as a separate object

Be precise. Think step by step: 1) What is the food? 2) How large is the portion? 3) Calculate nutrition for THAT portion."""

    import time as _t
    _model = "meta-llama/llama-4-scout-17b-16e-instruct"
    _t0 = _t.time()
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": _model,
                "messages": [{"role": "user", "content": [
                    {"type": "text",      "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]}],
                "temperature": 0.1,
                "max_tokens": 1000,
            },
            timeout=35,
        )
        _body = resp.json()
        from api.llm_usage import log_llm_usage
        log_llm_usage(user["id"], "groq", _model, "food_photo", _body.get("usage"),
                      latency_ms=(_t.time() - _t0) * 1000)
        text = _body["choices"][0]["message"]["content"].strip()

        # נקה markdown אם יש
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.strip().startswith("json"):
                text = text.strip()[4:]

        # מצא את ה-JSON array
        start = text.find("[")
        end   = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end+1]

        items = json.loads(text.strip())

        # ── Cross-reference with food catalog for accurate macros ──
        enriched = []
        for it in items:
            item = _crossref_and_validate(it)
            enriched.append(item)

        return {"items": enriched, "image_url": image_url}

    except Exception as e:
        return {"items": [], "image_url": image_url, "error": str(e)}


def _crossref_and_validate(item: dict) -> dict:
    """
    1. Strip Arabic characters from name_he
    2. Cross-reference with our known Israeli food table for accurate macros
    3. Cross-reference with FoodCatalog as fallback
    4. Validate that calories = protein*4 + carbs*4 + fat*9 (±15%)
    """
    name_he = _ensure_hebrew(item.get("name_he", ""), item.get("name", ""))
    item["name_he"] = name_he

    try:
        grams = float(item.get("grams") or 100)
    except (TypeError, ValueError):
        grams = 100.0
    if grams <= 0:
        grams = 100.0
    item["grams"] = round(grams)

    # 1. Try our curated Israeli table first (most accurate)
    matched = _lookup_il_table(name_he, grams)
    if matched:
        item.update(matched)
        item["source"] = "catalog"
        return item

    # 2. Try FoodCatalog
    catalog_match = _lookup_catalog(name_he, item.get("name", ""), grams)
    if catalog_match:
        item.update(catalog_match)
        item["source"] = "catalog"
        return item

    # 3. AI estimate — validate macro consistency
    try:
        cal   = float(item.get("calories") or 0)
        prot  = float(item.get("protein")  or 0)
        carbs = float(item.get("carbs")    or 0)
        fat   = float(item.get("fat")      or 0)
        calc  = prot * 4 + carbs * 4 + fat * 9
        # If AI calories are wildly off from macro math, recalculate
        if cal > 0 and calc > 0 and abs(cal - calc) / max(cal, calc) > 0.20:
            item["calories"] = round(calc)
    except Exception:
        pass

    item["source"] = "ai_estimate"
    return item


def _clamp_grams(name_he: str, grams: float) -> float:
    """Clamp AI portion estimate to realistic bounds for the most specific known food."""
    name = name_he.strip()
    candidates = [k for k in _PORTION_BOUNDS if (k in name or name in k)]
    if not candidates:
        return grams
    lo, hi = _PORTION_BOUNDS[max(candidates, key=len)]
    return max(lo, min(hi, grams))


def _lookup_il_table(name_he: str, grams: float) -> dict | None:
    """
    Match against the curated Israeli food table.

    Picks the MOST SPECIFIC match: an exact name wins, otherwise the longest
    overlapping key. Prevents "פיתה לבנה" from matching the substring "לבנה"
    (labaneh) instead of "פיתה לבנה" (pita).
    """
    name = name_he.strip()
    if name in _IL_FOODS:
        best_key = name
    else:
        candidates = [k for k in _IL_FOODS if (k in name or name in k)]
        if not candidates:
            return None
        best_key = max(candidates, key=len)

    kcal100, prot100, carbs100, fat100 = _IL_FOODS[best_key]
    g = _clamp_grams(name, grams)
    f = g / 100.0
    return {
        "name_he":  best_key,   # canonical Hebrew name — never show English/Arabic
        "calories": round(kcal100  * f),
        "protein":  round(prot100  * f, 1),
        "carbs":    round(carbs100 * f, 1),
        "fat":      round(fat100   * f, 1),
        "grams":    round(g),
    }


def _lookup_catalog(name_he: str, name_en: str, grams: float) -> dict | None:
    """Fuzzy-match against FoodCatalog."""
    try:
        from nutrition_app.agents.agent_3_food import FoodCatalog
        cat   = FoodCatalog()
        foods = cat.get_all_foods()
        q     = name_he.lower().strip()

        best = None
        for food in foods:
            aliases = (food.aliases_he or []) + [food.name_he or ""]
            for alias in aliases:
                if q in alias.lower() or alias.lower() in q:
                    best = food
                    break
            if best:
                break

        # fallback: English
        if not best:
            q_en = name_en.lower().strip()
            for food in foods:
                if q_en in (food.name_en or "").lower() or (food.name_en or "").lower() in q_en:
                    best = food
                    break

        if best:
            g = _clamp_grams(name_he, grams)
            macros = best.macros_for_grams(g)
            out = {
                "calories": round(macros.get("calories_kcal", 0)),
                "protein":  round(macros.get("protein_g",     0), 1),
                "carbs":    round(macros.get("carbs_g",       0), 1),
                "fat":      round(macros.get("fat_g",         0), 1),
                "grams":    round(g),
            }
            if best.name_he:        # prefer the catalog's Hebrew name
                out["name_he"] = best.name_he
            return out
    except Exception:
        pass
    return None


def _ensure_hebrew(name_he: str, name_en: str) -> str:
    """Replace Arabic characters with English fallback."""
    if any("؀" <= ch <= "ۿ" for ch in (name_he or "")):
        return name_en or name_he
    return name_he or name_en
