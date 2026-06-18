from fastapi import APIRouter, Depends, UploadFile, File
from api.deps import get_current_user
import sys, os, base64, json, requests, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_PHOTOS_DIR = os.path.join(_PROJECT_ROOT, "storage_agents", "food_photos")
_PUBLIC_BASE = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")


@router.post("/identify")
async def identify_food(file: UploadFile = File(...), user=Depends(get_current_user)):
    """מקבל תמונה, שומר אותה, ומחזיר זיהוי מזון + ערכי תזונה + image_url."""
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

    # Persist the photo so it can be shown next to the diary entry later.
    image_url = None
    try:
        os.makedirs(_PHOTOS_DIR, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.jpg"
        with open(os.path.join(_PHOTOS_DIR, fname), "wb") as fh:
            fh.write(image_bytes)
        image_url = f"{_PUBLIC_BASE}/food-photos/{fname}"
    except Exception:
        pass

    if not api_key:
        return {"items": [], "image_url": image_url, "error": "GROQ_API_KEY missing"}

    img_b64 = base64.b64encode(image_bytes).decode()

    prompt = """You are an expert food recognition and portion estimation AI.

TASK: Analyze the photo and for each food item:
1. Identify the food.
2. Visually estimate the ACTUAL PORTION SIZE in the image — look at plate/bowl size, food height, spread, and compare to standard reference objects. Do NOT default to 100g.
3. Calculate the total calories/macros for that specific estimated portion (not per 100g).

PORTION ESTIMATION RULES:
- A full plate of pasta ≈ 250-350g
- A typical grilled chicken breast ≈ 150-200g
- A bowl of salad ≈ 200-300g
- A sandwich ≈ 180-250g
- An egg ≈ 55g
- A cup of rice ≈ 180-200g cooked
- A medium fruit (apple/peach/orange) ≈ 130-180g
- Use visual size cues: if the food takes up half a large plate, estimate accordingly.
- If a reference object (fork, hand, bottle) is visible, use it for scale.

CRITICAL LANGUAGE RULE:
- "name_he" MUST be written in HEBREW (עברית) only — NEVER in Arabic.
- Examples: apple = "תפוח" (NOT "تفاح"), peach = "אפרסק", bread = "לחם", rice = "אורז", chicken = "עוף".
- If unsure of the Hebrew word, transliterate into Hebrew letters, but never output Arabic script.

ACCURACY — distinguish look-alike foods carefully before naming:
- Cucumber (מלפפון) vs melon (מלון): cucumber is long, thin, dark-green, uniform;
  melon is large, round, with netted/pale skin. A green vegetable on a salad plate
  is almost always cucumber, NOT melon.
- Zucchini (קישוא) vs cucumber; lemon (לימון) vs lime; sweet potato vs potato.
- When two foods look similar, prefer the one that fits the context of the dish
  (salad, plate, meal) rather than an exotic guess.
- If genuinely unsure, choose the more COMMON everyday food.

Return ONLY a JSON array (no markdown, no explanation):
[{"name": "food name in English", "name_he": "השם בעברית", "grams": <estimated portion grams>, "calories": <total calories for that portion>, "protein": <total protein g>, "carbs": <total carbs g>, "fat": <total fat g>}]

Be realistic. A photo of a full meal should show 400-800 total calories across all items."""

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
                "max_tokens": 800,
            },
            timeout=30,
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        items = json.loads(text.strip())
        # Safety net: strip any Arabic that slipped into Hebrew names.
        for it in items:
            it["name_he"] = _ensure_hebrew(it.get("name_he", ""), it.get("name", ""))
        return {"items": items, "image_url": image_url}
    except Exception as e:
        return {"items": [], "image_url": image_url, "error": str(e)}


def _ensure_hebrew(name_he: str, name_en: str) -> str:
    """If name_he contains Arabic characters, fall back to the English name."""
    # Arabic Unicode block U+0600–U+06FF
    if any("؀" <= ch <= "ۿ" for ch in name_he or ""):
        return name_en or name_he
    return name_he
