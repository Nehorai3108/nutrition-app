from fastapi import APIRouter, Depends, UploadFile, File
from api.deps import get_current_user
import sys, os, base64, json, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

@router.post("/identify")
async def identify_food(file: UploadFile = File(...), user=Depends(get_current_user)):
    """מקבל תמונה ומחזיר זיהוי מזון + ערכי תזונה."""
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
        return {"items": [], "error": "GROQ_API_KEY missing"}

    image_bytes = await file.read()
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
- Use visual size cues: if the food takes up half a large plate, estimate accordingly.
- If a reference object (fork, hand, bottle) is visible, use it for scale.

Return ONLY a JSON array (no markdown, no explanation):
[{"name": "food name in English", "name_he": "שם בעברית", "grams": <estimated portion grams>, "calories": <total calories for that portion>, "protein": <total protein g>, "carbs": <total carbs g>, "fat": <total fat g>}]

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
        return {"items": items}
    except Exception as e:
        return {"items": [], "error": str(e)}
