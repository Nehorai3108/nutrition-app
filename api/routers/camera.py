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
        return {"items": [], "error": "GROQ_API_KEY missing"}

    image_bytes = await file.read()
    img_b64 = base64.b64encode(image_bytes).decode()

    prompt = """You are an expert food recognition AI.
For each food item visible, return JSON:
[{"name": "exact food name", "name_he": "שם בעברית", "grams": 150, "calories": 200, "protein": 15, "carbs": 20, "fat": 8}]
Return ONLY the JSON array."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/llama-4-maverick-17b-128e-instruct",
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]}],
                "temperature": 0.0,
                "max_tokens": 500,
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
