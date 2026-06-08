from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from api.deps import get_current_user
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter()

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
        return {"reply": "שגיאה: Groq API key חסר", "food_data": None}

    client = Groq(api_key=api_key)

    # System prompt מקוצר לAPI
    system = """You are Biti — Israeli nutrition assistant. Always reply in Hebrew.
When user mentions food, return JSON: {"meal_type":"lunch","foods":[{"name":"food name","quantity":1,"unit":"יחידה"}],"reply":"short Hebrew reply"}
Otherwise reply naturally in Hebrew without JSON."""

    messages = [{"role": "system", "content": system}]
    for m in body.history[-10:]:  # שמור 10 הודעות אחרונות
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": body.message})

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()

        # נסה לחלץ JSON
        import re, json
        food_data = None
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
        if m:
            try:
                food_data = json.loads(m.group(1))
                raw = food_data.get("reply", raw)
            except Exception:
                pass
        else:
            m2 = re.search(r'(\{[\s\S]*"meal_type"[\s\S]*"foods"[\s\S]*\})', raw)
            if m2:
                try:
                    food_data = json.loads(m2.group(1))
                    raw = food_data.get("reply", raw)
                except Exception:
                    pass

        return {"reply": raw, "food_data": food_data}
    except Exception as e:
        return {"reply": f"שגיאה: {e}", "food_data": None}
