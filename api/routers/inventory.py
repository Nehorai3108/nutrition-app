from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from api.deps import get_current_user
from api._tz import now_il_iso
import sys, os, uuid, sqlite3, base64, json, requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, "storage", "nutrition.db")

_VALID_CATEGORIES = {
    "produce", "meat", "dairy", "bakery", "pantry",
    "frozen", "beverages", "snacks", "other",
}

_CREATE = """
CREATE TABLE IF NOT EXISTS inventory (
    item_id    TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    name_he    TEXT NOT NULL,
    quantity   REAL DEFAULT 1,
    unit       TEXT DEFAULT 'יח׳',
    category   TEXT DEFAULT 'other',
    added_at   TEXT NOT NULL
)
"""


def _conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE)
    return conn


def _norm_category(c: str) -> str:
    c = (c or "other").lower().strip()
    return c if c in _VALID_CATEGORIES else "other"


# ── Storage: Supabase בענן (נשמר לאורך זמן), SQLite בפיתוח מקומי ──
def _use_sb() -> bool:
    return bool(os.environ.get("SUPABASE_URL"))


def _sb():
    from nutrition_app.db.supabase_client import get_supabase
    return get_supabase()


def _list_items(user_id: str) -> list:
    if _use_sb():
        return (_sb().table("inventory").select("*")
                .eq("user_id", user_id).order("added_at", desc=True).execute()).data or []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM inventory WHERE user_id=? ORDER BY category, added_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def _add_item(user_id: str, name_he: str, quantity, unit: str, category: str) -> dict:
    """מוסיף פריט — ממזג עם פריט קיים בעל אותו שם+יחידה (סוכם כמויות)."""
    cat = _norm_category(category)
    now = now_il_iso()
    if _use_sb():
        existing = (_sb().table("inventory").select("item_id,quantity")
                    .eq("user_id", user_id).eq("name_he", name_he).eq("unit", unit)
                    .limit(1).execute()).data
        if existing:
            new_q = (existing[0].get("quantity") or 0) + (quantity or 0)
            _sb().table("inventory").update(
                {"quantity": new_q, "category": cat, "added_at": now}
            ).eq("item_id", existing[0]["item_id"]).execute()
            return {"item_id": existing[0]["item_id"], "name_he": name_he,
                    "quantity": new_q, "unit": unit, "category": cat}
        item_id = uuid.uuid4().hex
        _sb().table("inventory").insert(
            {"item_id": item_id, "user_id": user_id, "name_he": name_he,
             "quantity": quantity, "unit": unit, "category": cat, "added_at": now}
        ).execute()
        return {"item_id": item_id, "name_he": name_he, "quantity": quantity,
                "unit": unit, "category": cat}
    with _conn() as conn:
        item = _insert(conn, user_id, name_he, quantity, unit, cat)
        conn.commit()
        return item


def _has_arabic(text: str) -> bool:
    # Arabic Unicode block U+0600–U+06FF
    return any("؀" <= ch <= "ۿ" for ch in text or "")


def _clean_name(name_he: str, name_en: str) -> Optional[str]:
    """Reject Arabic-script names; fall back to the English name if needed."""
    name_he = (name_he or "").strip()
    if name_he and not _has_arabic(name_he):
        return name_he
    name_en = (name_en or "").strip()
    if name_en and not _has_arabic(name_en):
        return name_en
    return None  # drop items we can't render in a sane language


def _groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key
    try:
        import tomllib
        with open(os.path.join(_PROJECT_ROOT, ".streamlit", "secrets.toml"), "rb") as f:
            return tomllib.load(f).get("groq_api_key", "")
    except Exception:
        return ""


class AddItem(BaseModel):
    name_he: str
    quantity: float = 1
    unit: str = "יח׳"
    category: str = "other"


class BulkItems(BaseModel):
    items: list[AddItem]


def _insert(conn, user_id: str, name_he: str, quantity, unit: str, category: str) -> dict:
    """Add an item — merging into an existing one of the same name+unit
    (so "5 מלפפונים" + "5 מלפפונים" becomes 10, not two rows)."""
    cat = _norm_category(category)
    now = now_il_iso()
    existing = conn.execute(
        "SELECT item_id, quantity FROM inventory WHERE user_id=? AND name_he=? AND unit=?",
        (user_id, name_he, unit),
    ).fetchone()
    if existing:
        new_q = (existing["quantity"] or 0) + (quantity or 0)
        conn.execute(
            "UPDATE inventory SET quantity=?, category=?, added_at=? WHERE item_id=?",
            (new_q, cat, now, existing["item_id"]),
        )
        return {"item_id": existing["item_id"], "name_he": name_he,
                "quantity": new_q, "unit": unit, "category": cat}

    item_id = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO inventory (item_id, user_id, name_he, quantity, unit, category, added_at)
           VALUES (?,?,?,?,?,?,?)""",
        (item_id, user_id, name_he, quantity, unit, cat, now),
    )
    return {"item_id": item_id, "name_he": name_he, "quantity": quantity,
            "unit": unit, "category": cat}


@router.get("/")
def list_inventory(user=Depends(get_current_user)):
    return {"items": _list_items(user["id"])}


@router.post("/")
def add_item(body: AddItem, user=Depends(get_current_user)):
    item = _add_item(user["id"], body.name_he.strip(), body.quantity,
                     body.unit, body.category)
    return {"ok": True, "item": item}


@router.post("/bulk")
def add_bulk(body: BulkItems, user=Depends(get_current_user)):
    """שמירה מרוכזת — אחרי שהמשתמש אישר/ערך את רשימת הקבלה."""
    added = []
    for it in body.items:
        name = (it.name_he or "").strip()
        if not name:
            continue
        added.append(_add_item(user["id"], name, it.quantity, it.unit, it.category))
    return {"ok": True, "count": len(added), "items": added}


@router.delete("/{item_id}")
def delete_item(item_id: str, user=Depends(get_current_user)):
    if _use_sb():
        _sb().table("inventory").delete().eq("user_id", user["id"]).eq("item_id", item_id).execute()
    else:
        with _conn() as conn:
            conn.execute("DELETE FROM inventory WHERE user_id=? AND item_id=?",
                         (user["id"], item_id))
            conn.commit()
    return {"ok": True}


@router.delete("/")
def clear_inventory(user=Depends(get_current_user)):
    if _use_sb():
        _sb().table("inventory").delete().eq("user_id", user["id"]).execute()
    else:
        with _conn() as conn:
            conn.execute("DELETE FROM inventory WHERE user_id=?", (user["id"],))
            conn.commit()
    return {"ok": True}


@router.post("/scan-receipt")
async def scan_receipt(file: UploadFile = File(...), user=Depends(get_current_user)):
    """קולט תמונת קבלה, מחלץ מוצרי מזון עם Groq, ומוסיף למלאי."""
    api_key = _groq_key()
    if not api_key:
        return {"items": [], "error": "GROQ_API_KEY missing"}

    img_b64 = base64.b64encode(await file.read()).decode()

    prompt = """You are reading an Israeli supermarket receipt (חשבונית סופרמרקט).
Extract EVERY food / grocery PRODUCT line. IGNORE prices, totals (סה""כ), store
name, address, dates, cashier, payment, VAT (מע""מ), and any non-food item.

For each product return:
- name_he: the product name in HEBREW only (clean, generic — e.g. "עגבניות", "חלב 3%", "לחם פרוס")
- name_en: the same product name in English (e.g. "tomatoes", "milk", "bread")
- category: one of produce, meat, dairy, bakery, pantry, frozen, beverages, snacks, other
- quantity: number (default 1)
- unit: one of יח׳, ק"ג, גרם, חבילה, בקבוק

CRITICAL LANGUAGE RULE: name_he MUST be written in HEBREW letters (עברית) only —
NEVER in Arabic script. Examples: tomatoes = "עגבניות" (NOT "عغبنيوت"),
milk = "חלב", bread = "לחם", cucumber = "מלפפון", chicken = "עוף".

Return ONLY a JSON array, no markdown:
[{"name_he":"עגבניות","name_en":"tomatoes","category":"produce","quantity":1,"unit":"ק\\"ג"}]"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]}],
                "temperature": 0.0,
                "max_tokens": 1500,
            },
            timeout=45,
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end + 1]
        parsed = json.loads(text.strip())
    except Exception as e:
        return {"items": [], "error": str(e)}

    # Parse only — return the items for the user to review/edit before saving.
    items = []
    for p in parsed:
        name = _clean_name(p.get("name_he"), p.get("name_en"))
        if not name:
            continue
        try:
            qty = float(p.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1
        items.append({
            "name_he": name,
            "quantity": qty,
            "unit": p.get("unit") or "יח׳",
            "category": _norm_category(p.get("category")),
        })
    return {"items": items, "count": len(items)}


@router.get("/cook")
def cook_from_inventory(user=Depends(get_current_user)):
    """מתכונים שאפשר להכין ממה שיש במלאי — מדורגים לפי כמה מרכיבים יש לך."""
    inv_names = {it.get("name_he") for it in _list_items(user["id"]) if it.get("name_he")}
    if not inv_names:
        return {"recipes": [], "inventory_count": 0}

    from nutrition_app.agents.agent_11_recipes.recipe_manager import get_recipe_inventory_match
    from nutrition_app.agents.agent_11_recipes.unit_converter import enrich_recipe_ingredients
    from api.routers.daily_menu import enrich_images, get_manager

    mgr = get_manager()  # shared singleton — don't reload all recipes per request
    scored = []
    for r in mgr._recipes:
        ings = r.get("ingredients", [])
        if not ings:
            continue
        match = get_recipe_inventory_match(r, inv_names)
        if match["match_pct"] <= 0:
            continue
        scored.append((match["match_pct"], len(match["available"]), r, match))

    # Best coverage first, then most matched ingredients.
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    results = []
    for pct, _, recipe, match in scored[:10]:
        rec = dict(recipe)
        enrich_recipe_ingredients(rec)
        results.append({
            **rec,
            "match_pct": pct,
            "available": [i.get("food_name") for i in match["available"]],
            "missing": [i.get("food_name") for i in match["missing"]],
        })
    enrich_images(results)
    return {"recipes": results, "inventory_count": len(inv_names)}
