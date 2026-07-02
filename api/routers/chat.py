from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), user=Depends(get_current_user)):
    """תמלול הקלטה קולית לעברית (Groq Whisper) — לדבר עם Biti במקום להקליד."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return {"text": "", "error": "GROQ_API_KEY missing"}
    try:
        from groq import Groq
        audio = await file.read()
        client = Groq(api_key=api_key)
        res = client.audio.transcriptions.create(
            file=(file.filename or "audio.m4a", audio),
            model="whisper-large-v3",  # most accurate for Hebrew
            language="he",
            temperature=0.0,
            # Domain hint improves spelling of nutrition terms.
            prompt="שיחה בעברית על תזונה: אכלתי, שתיתי, ארוחת בוקר, צהריים, ערב, "
                   "חלבון, פחמימות, שומן, קלוריות, חביתה, סלט, עוף, אורז, יוגורט.",
            response_format="text",
        )
        text = res if isinstance(res, str) else getattr(res, "text", "")
        text = (text or "").strip()
        return {"text": _clean_transcript(client, text) if text else ""}
    except Exception as e:
        return {"text": "", "error": str(e)}


def _clean_transcript(client, text: str) -> str:
    """Fix Hebrew spelling/typos from speech-to-text WITHOUT changing meaning."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content":
                 "אתה מתקן שגיאות כתיב ופיסוק בעברית של תמלול דיבור. החזר אך ורק את "
                 "הטקסט המתוקן, באותה משמעות בדיוק, בלי להוסיף או להשמיט מילים, בלי "
                 "הסברים. שמור על סגנון דיבור טבעי."},
                {"role": "user", "content": text},
            ],
            max_tokens=200, temperature=0.0,
        )
        cleaned = (resp.choices[0].message.content or "").strip()
        return cleaned or text
    except Exception:
        return text

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "storage", "nutrition.db")

_NOTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "storage_agents", "biti_notes")


def _notes_path(user_id: str) -> str:
    safe = "".join(c for c in str(user_id) if c.isalnum() or c in "-_") or "user"
    return os.path.join(_NOTES_DIR, f"{safe}.json")


def _load_notes(user_id: str) -> list:
    """Durable facts Biti has learned about the user."""
    try:
        import json as _json
        with open(_notes_path(user_id), encoding="utf-8") as f:
            data = _json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_note(user_id: str, note: str) -> None:
    note = (note or "").strip()
    if not note:
        return
    try:
        import json as _json
        notes = _load_notes(user_id)
        # de-dupe (case-insensitive) and cap to the 25 most recent facts
        if not any(note.lower() == n.lower() for n in notes):
            notes.append(note)
            notes = notes[-25:]
            os.makedirs(_NOTES_DIR, exist_ok=True)
            with open(_notes_path(user_id), "w", encoding="utf-8") as f:
                _json.dump(notes, f, ensure_ascii=False)
    except Exception:
        pass


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
def chat(body: ChatRequest, stream: bool = False, user=Depends(get_current_user)):
    """שולח הודעה ל-AI ומקבל תגובה + נתוני מזון. stream=true → זרם SSE."""
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

    # Free-tier daily message cap.
    from api.usage import check_and_consume, is_owner
    if not is_owner(user.get("email")):
        gate = check_and_consume(user["id"], "chat")
        if not gate["allowed"]:
            return {
                "reply": f"הגעת למכסת {gate['limit']} ההודעות היומית בצ'אט. "
                         f"שדרג ל-Pro לשיחה ללא הגבלה.",
                "food_data": None, "recipe": None, "limit_reached": True,
            }

    client = Groq(api_key=api_key)

    inv_ctx = _inventory_context(user["id"])
    nut_ctx = _nutrition_context(user["id"])
    notes   = _load_notes(user["id"])
    notes_ctx = ("\n".join(f"  • {n}" for n in notes)) if notes else "  (עדיין לא ידוע)"

    system = f"""You are Biti, the user's personal Israeli nutritionist. ALWAYS reply in correct, fully-spelled Hebrew (never Arabic, no truncated words).

What you remember about the user:
{notes_ctx}
When you learn a DURABLE fact (preference/diet style/goal/allergy) add "remember":"...(Hebrew)" — lasting facts only, not one-off meals. The CURRENT request always overrides a conflicting memory (you may briefly note the conflict).

Inventory: {inv_ctx}
Targets (use for quantities): {nut_ctx}
When asked what/how much to eat for a meal, give a concrete suggestion hitting that meal's calorie sub-target, with quantities.

Return a ```json block when relevant:

1. "foods" — ONLY when the user reports they ALREADY ate/drank (past tense: "אכלתי","שתיתי","היה לי"). Then you MUST return foods (not just text). NEVER for future/requests ("אני רוצה","מה לאכול","מה תמליץ","תן לי") → those are recipe.
   "foods":[{{"name_he":"..","name_en":"..","grams":<total>,"calories":<total>,"protein":<g>,"carbs":<g>,"fat":<g>}}]
   Counted items: grams = count × unit weight (preserves the count): strawberry=12, egg=55, banana=120, apple=180, apricot=35, plum=70, walnut=5, almond=1.2, olive=4, date=8, bread slice=30, cracker=8 ("10 תותים"→120g).
   Portions: cup of juice≈250ml, glass of milk≈240, can≈330.
   Light/diet/zero ("קל","לייט","דיאט","זירו","ללא סוכר") = far fewer calories (light juice≈half; diet≈0). Keep that word in name_he ("מיץ תפוזים קל").
   ALWAYS include "meal_type": breakfast(בוקר)/morning_snack(ביניים בוקר)/lunch(צהריים)/afternoon_snack(ביניים צהריים/אחה"צ)/dinner(ערב). Omit if unstated.

2. "actions" — inventory/workout:
   {{"type":"add_inventory"|"remove_inventory","name_he":"..","quantity":1,"unit":"יח׳","category":"produce|meat|dairy|bakery|pantry|frozen|beverages|snacks|other"}}
   {{"type":"add_workout","workout_type":"running|strength|cycling|swimming|yoga|hiit|walking|other","duration_minutes":30,"distance_km":4,"intensity":"low|moderate|high"}} (no calories — system computes).

3. "recipe" — when asked for a meal/recipe/what to eat. Build to the meal's calorie target:
   "recipe":{{"title":"..","meal_type":"..","to_menu":false,"instructions":["..",".."],"foods":[{{"name_he":"..","name_en":"..","grams":..,"calories":..,"protein":..,"carbs":..,"fat":..}}]}}
   to_menu:true ONLY if they explicitly ask to add it to the plan ("תכניס/תוסיף לתפריט").
   Rules: (a) OBEY the explicit request over memory — "בשרי"=must contain meat/chicken/fish, "צמחוני"=no meat.
   (b) Center the dish on what they asked. (c) breakfast/snack=light (חביתה/סלט/גבינה/כריך/יוגורט); lunch/dinner=real main course (protein+carb+vegetables), never a breakfast dish, no rice/pasta at breakfast.
   (d) A real coherent dish, NOT a random pile to hit calories — a snack = one idea, 2-4 matching ingredients; if short on calories use a bigger portion, don't tack on unrelated foods.
   (e) List every ingredient incl. cooking oil/butter.

The system really performs actions — confirm briefly ("הוספתי ✓"), don't ask the user to do it.

Output: when returning JSON, return ONLY the JSON object (no text before/after, no ```json fences). Your short Hebrew sentence goes in "reply" (user never sees raw JSON). Never put a double-quote (") inside any JSON string value — write "קלוריות" not קק"ל. For a plain question (no food/recipe/action) reply with plain Hebrew text only."""

    messages = [{"role": "system", "content": system}]
    for m in body.history[-6:]:   # keep context lean to conserve daily tokens
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": body.message})

    _model = "llama-3.3-70b-versatile"

    # ── Streaming path: emit the reply token-by-token via SSE, then a final
    #    "done" event with the processed food/recipe/actions payload. ──────────
    if stream:
        import json as _json

        def _gen():
            parts = []
            try:
                s = client.chat.completions.create(
                    model=_model, messages=messages, max_tokens=1500,
                    temperature=0.2, stream=True,
                )
                for chunk in s:
                    delta = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    if delta:
                        parts.append(delta)
                        yield "data: " + _json.dumps({"t": "c", "d": delta}, ensure_ascii=False) + "\n\n"
            except Exception as e:
                yield "data: " + _json.dumps({"t": "done", "reply": f"שגיאה: {e}",
                                              "food_data": None, "recipe": None}, ensure_ascii=False) + "\n\n"
                return
            raw = "".join(parts).strip()
            result = _process_model_output(raw, user["id"])
            if (not result.get("food_data") and not result.get("recipe")
                    and not result.get("actions") and _looks_like_ate(body.message)):
                foods = _extract_eaten_foods(client, _model, body.message)
                if foods:
                    result["food_data"] = {"meal_type": _guess_meal_type(body.message), "foods": _add_household_display(foods)}
                    result["reply"] = (result.get("reply") or "").strip() or "רשמתי ✓"
            yield "data: " + _json.dumps({"t": "done", **result}, ensure_ascii=False) + "\n\n"

        return StreamingResponse(_gen(), media_type="text/event-stream")

    import time as _t
    _t0 = _t.time()
    try:
        resp = client.chat.completions.create(
            model=_model,
            messages=messages,
            max_tokens=1500,   # recipe JSON + reply must fit, or it gets truncated
            temperature=0.2,
        )
        from api.llm_usage import log_llm_usage
        log_llm_usage(user["id"], "groq", _model, "chat_assistant",
                      getattr(resp, "usage", None),
                      latency_ms=(_t.time() - _t0) * 1000)
        raw = resp.choices[0].message.content.strip()
        result = _process_model_output(raw, user["id"])
        # Safety net: the user clearly reported eating something but the model
        # didn't structure it → a second focused call extracts the foods so the
        # client can log + sync them.
        if (not result.get("food_data") and not result.get("recipe")
                and not result.get("actions") and _looks_like_ate(body.message)):
            foods = _extract_eaten_foods(client, _model, body.message)
            if foods:
                result["food_data"] = {"meal_type": _guess_meal_type(body.message), "foods": _add_household_display(foods)}
                result["reply"] = (result.get("reply") or "").strip() or "רשמתי ✓"
        return result
    except Exception as e:
        from api.llm_usage import log_llm_usage
        log_llm_usage(user["id"], "groq", _model, "chat_assistant", None,
                      latency_ms=(_t.time() - _t0) * 1000, success=False, error=str(e))
        msg = str(e).lower()
        if "rate_limit" in msg or "429" in msg or "tokens per day" in msg:
            reply = "אני קצת עמוס כרגע 🙏 נסה שוב בעוד כמה דקות."
        else:
            reply = "משהו השתבש, נסה שוב בעוד רגע."
        return {"reply": reply, "food_data": None, "recipe": None}


def _auto_log_foods(user_id: str, meal_type: str, foods: list) -> bool:
    """Log chat-suggested foods to the food diary via the shared repository
    (routes to Supabase in production, SQLite locally). Returns True on success
    so the caller can tell the user it really happened."""
    try:
        from nutrition_app.repositories.food_log_repository import (
            FoodLogRepository, FoodLogEntry,
        )
        from api._tz import now_il_iso, today_il
        repo = FoodLogRepository()
        day = today_il()
        for f in foods:
            entry = FoodLogEntry(
                food_id=f.get("name_en") or "chat_food",
                food_name=f.get("name_he") or f.get("name_en") or "מזון",
                grams=float(f.get("grams") or 100),
                calories=round(float(f.get("calories") or 0), 1),
                protein=round(float(f.get("protein") or 0), 1),
                carbs=round(float(f.get("carbs") or 0), 1),
                fat=round(float(f.get("fat") or 0), 1),
                meal_type=meal_type,
                timestamp=now_il_iso(),
                image_url=f.get("image_url"),
            )
            repo.add_entry(user_id, day, entry)
        return True
    except Exception:
        return False


def _off_search(query: str) -> dict | None:
    """Text-search OpenFoodFacts for a branded product → real per-100g + image.
    Free, openly licensed (ODbL). Returns None if nothing usable is found."""
    q = (query or "").strip()
    if not q:
        return None
    try:
        import requests as _req
        r = _req.get(
            "https://world.openfoodfacts.org/cgi/search.pl",
            params={"search_terms": q, "search_simple": 1, "action": "process",
                    "json": 1, "page_size": 5,
                    "fields": "product_name,product_name_he,nutriments,image_url,brands"},
            timeout=6, headers={"User-Agent": "BiteFit/1.0 (nutrition app)"},
        )
        for p in (r.json().get("products", []) or []):
            n = p.get("nutriments", {}) or {}
            cal = n.get("energy-kcal_100g")
            if cal:
                return {
                    "name": p.get("product_name_he") or p.get("product_name") or q,
                    "cal": float(cal),
                    "protein": float(n.get("proteins_100g") or 0),
                    "carbs": float(n.get("carbohydrates_100g") or 0),
                    "fat": float(n.get("fat_100g") or 0),
                    "image": p.get("image_url"),
                }
    except Exception:
        pass
    return None


def _enrich_eaten(f: dict) -> dict:
    """Nutrition for a food the user ate, best source first:
    Israeli catalog (whole foods) → OpenFoodFacts (branded, +image) → model."""
    name_he = f.get("name_he") or f.get("name") or ""
    name_en = f.get("name_en") or f.get("name") or name_he
    light = _is_light_variant(name_he)
    in_catalog = (not light) and _resolve_per_100g(name_he, name_en) is not None
    if in_catalog:
        return _enrich_food(f, recompute=True)          # accurate whole-food data
    # Not a plain catalog food → try OpenFoodFacts for the real branded product.
    off = _off_search(name_he)
    ef = _enrich_food(f, recompute=False)               # base (keeps model numbers/light)
    if off:
        g = float(ef.get("grams") or 100)
        fac = g / 100.0
        ef["calories"] = round(off["cal"] * fac)
        ef["protein"] = round(off["protein"] * fac, 1)
        ef["carbs"] = round(off["carbs"] * fac, 1)
        ef["fat"] = round(off["fat"] * fac, 1)
        if off.get("image"):
            ef["image_url"] = off["image"]
    return ef


def _process_model_output(raw: str, user_id: str) -> dict:
    """Turn the raw model reply into the API response (reply + food/recipe/actions).

    Pure glue over _extract_json / _enrich_food / _build_recipe_data / _exec_actions
    — separated from the network call so it can be tested without hitting Groq.
    """
    data = _extract_json(raw)
    reply = _strip_json_artifacts(raw) or _reply_from_broken_json(_fix_hebrew_quotes(raw))
    food_data = None
    recipe_data = None
    actions_done = []

    if data:
        reply = (data.get("reply") or "").strip() or _strip_json_artifacts(raw) or _reply_from_broken_json(_fix_hebrew_quotes(raw)) or "בוצע ✓"
        if isinstance(data.get("foods"), list) and data["foods"]:
            meal_type = _normalize_meal_type(data.get("meal_type", "lunch"))
            # Best data source per food: catalog → OpenFoodFacts → model.
            enriched = _add_household_display([_enrich_eaten(f) for f in data["foods"]])
            food_data = {"meal_type": meal_type, "foods": enriched}
            # NOTE: the client logs these to the diary (reliable + refreshes the
            # home summary) and deducts them from the menu — no server auto-log.
        rec = data.get("recipe")
        if isinstance(rec, dict) and isinstance(rec.get("foods"), list) and rec["foods"]:
            meal_type = _normalize_meal_type(rec.get("meal_type", "lunch"))
            rec["meal_type"] = meal_type
            target_cal = _meal_target_calories(user_id, meal_type)
            recipe_data = _build_recipe_data(rec, target_cal)
        if isinstance(data.get("actions"), list) and data["actions"]:
            actions_done = _exec_actions(user_id, data["actions"])
        # Long-term memory: persist any durable fact Biti learned about the user.
        remember = data.get("remember")
        if isinstance(remember, str) and remember.strip():
            _save_note(user_id, remember)
        elif isinstance(remember, list):
            for r in remember:
                if isinstance(r, str):
                    _save_note(user_id, r)

    return {"reply": reply, "food_data": food_data,
            "recipe": recipe_data, "actions": actions_done}


_ATE_WORDS = ("אכלתי", "אכלנו", "אכלה", "אכלת", "שתיתי", "שתינו", "טעמתי",
              "היה לי", "כיווני", "נשנשתי", "זללתי")


def _looks_like_ate(message: str) -> bool:
    m = message or ""
    return any(w in m for w in _ATE_WORDS)


_LIGHT_WORDS = ("קל", "לייט", "light", "דיאט", "diet", "זירו", "zero",
                "ללא סוכר", "דל קלוריות", "דל שומן")


def _is_light_variant(name: str) -> bool:
    """True for reduced-calorie product variants where the generic catalog value
    would be misleading (light juice, diet soda, zero...)."""
    n = f" {name or ''} "
    return any(w in n for w in _LIGHT_WORDS)


def _guess_meal_type(message: str) -> str:
    m = message or ""
    snack = "ביניים" in m or "חטיף" in m
    if "בוקר" in m:
        return "morning_snack" if snack else "breakfast"
    if "צהר" in m or "אחה" in m:
        return "afternoon_snack" if snack else "lunch"
    if "ערב" in m or "דינר" in m:
        return "dinner"
    # default by current Israel hour
    try:
        from api._tz import now_il
        h = now_il().hour
    except Exception:
        h = 13
    if h < 11:
        return "breakfast"
    if h < 16:
        return "lunch"
    if h < 19:
        return "afternoon_snack"
    return "dinner"


def _extract_eaten_foods(client, model: str, message: str) -> list:
    """Focused second call: extract ONLY the foods the user said they ate."""
    sys = ("חלץ אך ורק מאכלים/משקאות ספציפיים שהמשתמש אמר במפורש שאכל או שתה. "
           "החזר מערך JSON בלבד, ללא טקסט. פורמט: "
           '[{"name_he":"שם בעברית מלא","grams":<גרם>,"calories":<קלוריות סהכ>,'
           '"protein":<גרם>,"carbs":<גרם>,"fat":<גרם>}]. '
           "חשוב מאוד: אל תמציא מאכלים. אם ההודעה לא מזכירה מאכל ספציפי (למשל "
           "'אכלתי הרבה', 'אכלתי את כל הקלוריות', 'אני רעב') — החזר [] ריק. "
           "שמות בעברית מלאה בלבד, לא ערבית.")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": message}],
            max_tokens=400, temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        import re as _re, json as _json
        mt = _re.search(r"\[.*\]", raw, _re.DOTALL)
        arr = _json.loads(mt.group(0) if mt else raw)
        if isinstance(arr, list) and arr:
            return [_enrich_eaten(f) for f in arr if isinstance(f, dict)]
    except Exception:
        pass
    return []


def _add_household_display(foods: list) -> list:
    """Add a `display_he` household-unit string (e.g. "3 כפות גרנולה", "4 תותים")
    to each chat food so the app never shows raw grams."""
    try:
        from nutrition_app.agents.agent_11_recipes.unit_converter import format_ingredient_display
        for f in foods:
            f["display_he"] = format_ingredient_display({
                "food_name": f.get("name_he", ""),
                # _enrich_food stores the English name under "name"; fall back to it.
                "food_name_en": f.get("name_en") or f.get("name") or "",
                "quantity": f.get("grams", 0),
                "unit": "grams",
            })
    except Exception:
        pass
    return foods


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
    _add_household_display(foods)
    return {
        "title":          (rec.get("title") or "מתכון").strip(),
        "meal_type":      rec.get("meal_type", "lunch"),
        "instructions":   instructions,
        "foods":          foods,
        "total_calories": round(sum(f.get("calories", 0) for f in foods)),
        "total_protein":  round(sum(f.get("protein", 0) for f in foods)),
        "meal_target":    round(target_cal) if target_cal else None,
        "to_menu":        bool(rec.get("to_menu")),
    }


def _strip_json_artifacts(text: str) -> str:
    """Never show raw JSON / code fences to the user.

    If the model emitted prose followed by a (possibly truncated) ```json block,
    keep only the human prose before it. Strips fenced blocks and any trailing
    naked JSON fragment so a parse failure can't leak ``` or {"recipe":...}.
    """
    if not text:
        return ""
    t = text
    # cut everything from the first code fence onward
    if "```" in t:
        t = t.split("```")[0]
    t = t.strip()
    # pure JSON (no prose) → nothing human to show
    if t[:1] in ("{", "["):
        return ""
    # cut a trailing naked JSON object/array that follows real prose
    for brace in ("{", "["):
        idx = t.find(brace)
        if idx > 0 and any(ch.isalpha() for ch in t[:idx]):
            t = t[:idx]
    return t.strip()


import re as _re

# A literal " between two Hebrew letters is a gershayim (קק"ל, ש"ח, ק"ג) — it
# breaks JSON string parsing. Swap it for the real gershayim char (U+05F4).
_HEB_QUOTE_RE = _re.compile(r"([֐-׿])\"([֐-׿])")


def _fix_hebrew_quotes(text: str) -> str:
    prev = None
    while prev != text:  # handle chains like ק"ג ל"ק
        prev = text
        text = _HEB_QUOTE_RE.sub("\\1״\\2", text)
    return text


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
        blob = text[start:end + 1]
        for candidate in (blob, _fix_hebrew_quotes(blob)):
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None


def _reply_from_broken_json(raw: str) -> str:
    """Last resort: pull the "reply" value out even when JSON won't parse."""
    m = _re.search(r'"reply"\s*:\s*"(.*?)"\s*(?:,\s*"|\}|$)', raw, _re.S)
    if m:
        return m.group(1).replace('\\"', '"').replace("\\n", " ").strip()
    return ""


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
    "ביניים בוקר": "morning_snack", "ביניים צהריים": "afternoon_snack",
    "ביניים אחהצ": "afternoon_snack", "אחהצ": "afternoon_snack",
    "dinner": "dinner", "evening": "dinner", "ערב": "dinner",
    "ארוחת ערב": "dinner", "ארוחתערב": "dinner",
    # No evening-snack slot in the plan → fold into dinner.
    "evening_snack": "dinner", "חטיף ערב": "dinner", "ביניים ערב": "dinner",
    "snack": "afternoon_snack", "חטיף": "afternoon_snack", "ביניים": "afternoon_snack",
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


# MET per workout type — calories computed server-side (don't trust the model).
_WORKOUT_MET = {
    "running": 9.0, "walking": 3.5, "strength": 4.5, "cycling": 6.8,
    "swimming": 6.0, "yoga": 3.0, "hiit": 8.0, "other": 4.5,
}


def _log_workout(user_id: str, a: dict) -> None:
    """Insert a workout from a chat action into the shared workout store."""
    import uuid
    from api.routers.workout import _use_sb as w_sb_on, _sb as w_sb, _conn as w_conn
    from api._tz import today_il, now_il_iso

    wtype = (a.get("workout_type") or "other").lower().strip()
    intensity = (a.get("intensity") or "moderate").lower().strip()
    try:
        mins = float(a.get("duration_minutes") or 30)
    except (TypeError, ValueError):
        mins = 30.0
    try:
        dist = float(a["distance_km"]) if a.get("distance_km") not in (None, "") else None
    except (TypeError, ValueError):
        dist = None
    calories = round((mins / 60.0) * _WORKOUT_MET.get(wtype, 4.5) * 75)

    row = {
        "entry_id": uuid.uuid4().hex, "user_id": user_id, "date": today_il().isoformat(),
        "mode": "type", "workout_type": wtype, "intensity": intensity,
        "duration_minutes": mins, "distance_km": dist, "calories_burned": calories,
        "timestamp": now_il_iso(),
    }
    if w_sb_on():
        w_sb().table("workout_log").insert(row).execute()
    else:
        with w_conn() as conn:
            conn.execute(
                """INSERT INTO workout_log
                     (entry_id, user_id, date, mode, workout_type, intensity,
                      duration_minutes, distance_km, calories_burned, timestamp)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                tuple(row[k] for k in ("entry_id", "user_id", "date", "mode",
                      "workout_type", "intensity", "duration_minutes",
                      "distance_km", "calories_burned", "timestamp")),
            )
            conn.commit()


def _exec_actions(user_id: str, actions: list) -> list:
    """Execute inventory add/remove actions via the shared inventory storage
    (Supabase in the cloud, SQLite locally) — same store the inventory list reads."""
    from api.routers.inventory import _add_item, _list_items, _use_sb, _sb, _conn
    done = []
    for a in actions:
        if not isinstance(a, dict):
            continue
        t = (a.get("type") or "").lower().strip()

        # Workout logging — no name needed; handle before the name guard.
        if t in ("add_workout", "workout", "log_workout"):
            try:
                _log_workout(user_id, a)
                done.append({"op": "workout", "type": a.get("workout_type", "other")})
            except Exception:
                pass
            continue

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
