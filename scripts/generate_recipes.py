"""
Generate new recipes using Groq API and add to recipes.json
Run: python scripts/generate_recipes.py
"""
import json, os, sys, time, re
sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES_FILE = os.path.join(ROOT, "storage_agents", "recipes", "recipes.json")
SECRETS_FILE = os.path.join(ROOT, ".streamlit", "secrets.toml")

def _read_secret(key):
    with open(SECRETS_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith(key):
                return line.split("=")[1].strip().strip('"')
    return ""

GROQ_KEY = _read_secret("groq_api_key")

BATCHES = [
    {"meal_type": "BREAKFAST",       "topic": "ארוחות בוקר - דייסות, שייקים, ביצים, טוסטים, פנקייקים", "n": 8},
    {"meal_type": "BREAKFAST",       "topic": "ארוחות בוקר - גרנולה, וופלים, חביתות, מאפים, קוואקר", "n": 8},
    {"meal_type": "BREAKFAST",       "topic": "ארוחות בוקר ים תיכוניות - גבינות, ירקות, לחם, ביצים קשות", "n": 8},
    {"meal_type": "LUNCH",           "topic": "ארוחות צהריים - עוף בתנור, קציצות, שניצל, בשר טחון", "n": 8},
    {"meal_type": "LUNCH",           "topic": "ארוחות צהריים - דגים, סלמון, טונה, אנשובי", "n": 8},
    {"meal_type": "LUNCH",           "topic": "ארוחות צהריים צמחוניות - עדשים, חומוס, טופו, קינואה", "n": 8},
    {"meal_type": "LUNCH",           "topic": "ארוחות צהריים - פסטה, אורז, קוסקוס, בורגול עם חלבון", "n": 8},
    {"meal_type": "DINNER",          "topic": "ארוחות ערב - מרקים, תבשילים קלים, ירקות מוקפצים", "n": 8},
    {"meal_type": "DINNER",          "topic": "ארוחות ערב - סלטים עשירים, חביתה, ביצים, גבינה", "n": 8},
    {"meal_type": "MORNING_SNACK",   "topic": "חטיפי בוקר - פירות, יוגורט, אגוזים, גרנולה", "n": 8},
    {"meal_type": "AFTERNOON_SNACK", "topic": "חטיפי צהריים - חומוס, ירקות, גבינה, פירות", "n": 8},
    {"meal_type": "EVENING_SNACK",   "topic": "חטיפי ערב - יוגורט, פירות, קוטג', אגוזים", "n": 8},
]

PROMPT_TEMPLATE = """צור {n} מתכונים ייחודיים לסוג ארוחה: {meal_type}
נושא: {topic}

חוקים:
- כל מתכון חייב להיות שונה מהאחר
- כמויות ריאליות בגרמים
- מתכונים ישראליים/ים-תיכוניים בעיקר
- כולל גם אפשרויות טבעוניות/צמחוניות

החזר JSON בלבד (ללא טקסט אחר):
{{
  "recipes": [
    {{
      "name_he": "שם בעברית",
      "name_en": "Name in English",
      "meal_types": ["{meal_type}"],
      "prep_time_minutes": 15,
      "portions": 1,
      "kashrut": "dairy|meat|parve",
      "tags": ["tag1", "tag2"],
      "ingredients": [
        {{"food_name": "שם עברית", "food_name_en": "english", "quantity": 100, "unit": "grams"}}
      ],
      "total_nutrition": {{
        "calories": 350,
        "protein": 25,
        "carbs": 30,
        "fat": 10,
        "fiber": 5
      }}
    }}
  ]
}}"""

def call_groq(prompt: str) -> dict:
    import requests
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 2500, "temperature": 0.9},
        timeout=30
    )
    data = resp.json()
    if "choices" not in data:
        raise Exception(f"API error: {data}")
    content = data["choices"][0]["message"]["content"]
    # Try to extract JSON even if truncated
    try:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        # Try to fix truncated JSON by finding last complete recipe
        try:
            partial = content[:content.rfind('},')+1] + ']}'
            match2 = re.search(r'\{.*\}', partial, re.DOTALL)
            if match2:
                return json.loads(match2.group())
        except: pass
    return {}

# Load existing recipes
recipes = json.load(open(RECIPES_FILE, encoding="utf-8"))
existing_names = {r.get("name_en", "").lower() for r in recipes}
next_id = int(recipes[-1]["recipe_id"].replace("recipe_", "")) + 1

print(f"Starting from recipe_{next_id}, existing: {len(recipes)}")
added = 0

for batch in BATCHES:
    print(f"\n--- {batch['meal_type']} ({batch['n']} recipes) ---")
    prompt = PROMPT_TEMPLATE.format(**batch)

    try:
        result = call_groq(prompt)
        new_recipes = result.get("recipes", [])

        for rec in new_recipes:
            name_en = rec.get("name_en", "").lower()
            if name_en in existing_names:
                print(f"  skip (duplicate): {name_en}")
                continue

            rec["recipe_id"] = f"recipe_{next_id:03d}"
            rec["image_path"] = ""
            rec["image_credit"] = ""
            recipes.append(rec)
            existing_names.add(name_en)
            print(f"  + recipe_{next_id:03d}: {rec.get('name_he', '')} / {rec.get('name_en', '')}")
            next_id += 1
            added += 1

        # Save after each batch
        with open(RECIPES_FILE, "w", encoding="utf-8") as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        print(f"  Saved. Total: {len(recipes)}")

    except Exception as e:
        print(f"  ERROR: {e}")

    time.sleep(2)

print(f"\nDone! Added {added} recipes. Total: {len(recipes)}")
