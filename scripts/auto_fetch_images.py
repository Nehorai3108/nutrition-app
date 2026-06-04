"""
Auto-fetch Unsplash images for all recipes that don't have one yet.
Run: python scripts/auto_fetch_images.py
"""
import json, os, time, urllib.request, urllib.parse

ROOT          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES_FILE  = os.path.join(ROOT, "storage_agents", "recipes", "recipes.json")
IMAGES_FILE   = os.path.join(ROOT, "data", "recipe_images.json")
SECRETS_FILE  = os.path.join(ROOT, ".streamlit", "secrets.toml")

# Read API key from secrets.toml
def _read_key():
    with open(SECRETS_FILE, encoding="utf-8") as f:
        for line in f:
            if "UNSPLASH_ACCESS_KEY" in line:
                return line.split("=")[1].strip().strip('"')
    return ""

KEY = _read_key()

def _search(query: str) -> str:
    params = urllib.parse.urlencode({
        "query": f"{query} food dish",
        "per_page": 1,
        "orientation": "landscape",
        "client_id": KEY,
    })
    req = urllib.request.Request(
        f"https://api.unsplash.com/search/photos?{params}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    results = data.get("results", [])
    if results:
        return results[0]["urls"]["regular"]
    return ""

recipes = json.load(open(RECIPES_FILE, encoding="utf-8"))
try:
    images = json.load(open(IMAGES_FILE, encoding="utf-8"))
except:
    images = {}

# Replace TheMealDB images with Unsplash
missing = [r for r in recipes
           if not images.get(r.get("recipe_id",""))
           or "themealdb" in images.get(r.get("recipe_id",""), "")]
print(f"מתכונים ללא תמונה: {len(missing)}")

for i, recipe in enumerate(missing):
    rid     = recipe.get("recipe_id", "")
    name_en = recipe.get("name_en", "")
    name_he = recipe.get("name_he", "")
    query   = name_en or name_he

    try:
        url = _search(query)
        if url:
            images[rid] = url
            print(f"[{i+1}/{len(missing)}] {name_en} - OK")
        else:
            print(f"[{i+1}/{len(missing)}] {name_en} - not found")
    except Exception as e:
        err = str(e)
        if "403" in err or "Rate" in err:
            print(f"\nRate limit reached after {i} recipes. Saved progress. Run again in 1 hour.")
            break
        print(f"[{i+1}/{len(missing)}] {name_en} - error: {err}")

    # Save after every 5
    if (i + 1) % 5 == 0:
        with open(IMAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(images, f, ensure_ascii=False, indent=2)
        print(f"  saved ({len(images)} total)")

    time.sleep(1.5)  # ~40 req/hour to stay under 50 limit

# Final save
with open(IMAGES_FILE, "w", encoding="utf-8") as f:
    json.dump(images, f, ensure_ascii=False, indent=2)

print(f"\nסיים! סך הכל תמונות: {len(images)}")
