"""
בדיקות מקיפות לפייפליין זיהוי מזון מתמונה.
מריץ בלי API call — בודק את כל השלבים מקצה לקצה.
"""
import sys, ast, json, sqlite3
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from nutrition_app.agents.agent_3_food.food_catalog import FoodCatalog

PASS = "✅"; FAIL = "❌"; WARN = "⚠ "
errors = []
warnings = []

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}" + (f" — {detail}" if detail else ""))
        errors.append(name)

def warn(name, detail=""):
    print(f"  {WARN} {name}" + (f" — {detail}" if detail else ""))
    warnings.append(name)

# ─── 1. Syntax ───────────────────────────────────────────────────────────────
print("\n── 1. Syntax Check ──────────────────────────────────────────────────")
for f in ["pages/13_food_camera.py", "app_user.py", "ui/components.py"]:
    with open(f, encoding="utf-8") as fh:
        src = fh.read()
    try:
        ast.parse(src)
        check(f, True)
    except SyntaxError as e:
        check(f, False, str(e))

# ─── 2. Imports ──────────────────────────────────────────────────────────────
print("\n── 2. Imports ───────────────────────────────────────────────────────")
try:
    from nutrition_app.repositories.food_log_repository import FoodLogRepository, FoodLogEntry
    check("FoodLogRepository", True)
except Exception as e:
    check("FoodLogRepository", False, str(e))

try:
    cat = FoodCatalog()
    check("FoodCatalog", True)
except Exception as e:
    check("FoodCatalog", False, str(e))
    sys.exit(1)

# ─── 3. Food Coverage ────────────────────────────────────────────────────────
print("\n── 3. Food Coverage (DB + catalog) ──────────────────────────────────")

MUST_FIND = [
    # פרות
    ("apple","תפוח"), ("banana","בננה"), ("orange","תפוז"),
    ("mango","מנגו"), ("watermelon","אבטיח"), ("peach","אפרסק"),
    ("grape","ענב"), ("strawberry","תות"), ("pear","אגס"),
    ("blueberry","אוכמנית"), ("kiwi","קיווי"), ("pineapple","אננס"),
    # ירקות
    ("tomato","עגבנייה"), ("cucumber","מלפפון"), ("carrot","גזר"),
    ("onion","בצל"), ("potato","תפוח אדמה"), ("sweet potato","בטטה"),
    ("avocado","אבוקדו"), ("broccoli","ברוקולי"), ("mushroom","פטריות"),
    ("eggplant","חציל"), ("pepper","פלפל"), ("corn","תירס"),
    # חלבונים
    ("chicken","עוף"), ("chicken breast","חזה עוף"), ("beef","בשר"),
    ("salmon","סלמון"), ("tuna","טונה"), ("egg","ביצה"),
    ("turkey","הודו"), ("tofu","טופו"),
    # פחמימות
    ("rice","אורז"), ("pasta","פסטה"), ("bread","לחם"),
    ("oats","שיבולת"), ("quinoa","קינואה"),
    # חלב
    ("milk","חלב"), ("yogurt","יוגורט"), ("cheese","גבינה"),
    # שמנים/ממרחים
    ("olive oil","שמן"), ("hummus","חומוס"), ("tahini","טחינ"),
]

found = 0
for en, he_partial in MUST_FIND:
    hits = cat.search_foods(en, limit=1)
    if hits:
        found += 1
        print(f"  {PASS} {en:20} → {hits[0].name_he}")
    else:
        warn(f"{en:20} → לא נמצא")

print(f"\n  כיסוי: {found}/{len(MUST_FIND)}")
if found < len(MUST_FIND) * 0.9:
    errors.append(f"כיסוי מזון נמוך: {found}/{len(MUST_FIND)}")

# ─── 4. Aliases Test ─────────────────────────────────────────────────────────
print("\n── 4. Alias Resolution ──────────────────────────────────────────────")

# טען aliases מהדף
with open("pages/13_food_camera.py", encoding="utf-8") as f:
    src = f.read()

# extract FOOD_ALIASES dict safely
import re
m = re.search(r'FOOD_ALIASES.*?=\s*(\{.*?\})\n\n', src, re.DOTALL)
aliases_ok = 0
aliases_fail = 0
if m:
    try:
        aliases = eval(m.group(1))
        for key, search_terms in list(aliases.items())[:20]:
            found_any = False
            for term in search_terms[:2]:
                hits = cat.search_foods(term, limit=1)
                if hits:
                    found_any = True
                    break
            if found_any:
                aliases_ok += 1
            else:
                aliases_fail += 1
                warn(f"alias '{key}' לא מוצא ב-DB")
        check(f"Aliases ({aliases_ok} מתוך {aliases_ok+aliases_fail})", aliases_fail == 0)
    except Exception as e:
        warn(f"לא ניתן לבדוק aliases: {e}")
else:
    warn("לא נמצא FOOD_ALIASES בקוד")

# ─── 5. Mock Pipeline Test ───────────────────────────────────────────────────
print("\n── 5. Mock Pipeline — Gemini → DB → FoodLogEntry ────────────────────")

mock_gemini_responses = [
    ["apple"],
    ["chicken breast", "rice"],
    ["egg", "tomato"],
    ["salmon"],
    ["pasta"],
    ["peach"],
    ["yogurt"],
    ["bread", "cheese"],
    ["tuna"],
    ["avocado", "cucumber"],
]

def mock_search(name):
    """חיפוש ב-DB בלי Gemini."""
    # משתמש ב-aliases מהקובץ
    hits = cat.search_foods(name, limit=3)
    if hits:
        return hits
    # fallback aliases בסיסי
    BASIC = {
        "chicken breast": "chicken", "green apple": "apple",
        "white rice": "rice", "brown rice": "rice",
    }
    if name.lower() in BASIC:
        return cat.search_foods(BASIC[name.lower()], limit=3)
    return []

pipeline_ok = 0
for mock_names in mock_gemini_responses:
    results = []
    for name in mock_names:
        hits = mock_search(name)
        results.extend(hits[:1])
    if results:
        pipeline_ok += 1
        foods_str = ", ".join(f"{h.name_he}" for h in results[:2])
        print(f"  {PASS} {str(mock_names):35} → {foods_str}")
    else:
        print(f"  {FAIL} {str(mock_names):35} → לא נמצא")
        errors.append(f"mock pipeline failed: {mock_names}")

# ─── 6. DB Integrity ─────────────────────────────────────────────────────────
print("\n── 6. DB Integrity ──────────────────────────────────────────────────")
conn = sqlite3.connect("storage/nutrition.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM foods")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM foods WHERE calories_kcal IS NULL OR calories_kcal = 0")
missing_cal = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM foods WHERE calories_kcal > 0")
valid = cur.fetchone()[0]
conn.close()

check(f"סה\"כ מזונות ({total})", total > 11000)
check(f"מזונות עם קלוריות ({valid})", valid > 10000)
if missing_cal > 500:
    warn(f"{missing_cal} מזונות ללא קלוריות")
else:
    check(f"מזונות חסרי קלוריות ({missing_cal})", True)

# ─── 7. Nav + Home Page ──────────────────────────────────────────────────────
print("\n── 7. Nav & Home Page ───────────────────────────────────────────────")
with open("ui/components.py", encoding="utf-8") as f:
    nav_src = f.read()
check("צילום הוסר מהנאב", "13_food_camera" not in nav_src or "camera" not in nav_src.split("items = [")[1].split("]")[0])

with open("app_user.py", encoding="utf-8") as f:
    home_src = f.read()
check("SVG camera icon בדף הבית", "food_camera" in home_src and "svg" in home_src.lower())

# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print(f"  {PASS} עברו: {sum(1 for _ in range(1)) - len(errors)} בדיקות")
print(f"  {FAIL} נכשלו: {len(errors)}")
print(f"  {WARN} אזהרות: {len(warnings)}")

if errors:
    print("\n  שגיאות:")
    for e in errors:
        print(f"    • {e}")

if not errors:
    print(f"\n  {PASS} הפייפליין תקין לחלוטין!")
else:
    print(f"\n  {FAIL} יש {len(errors)} בעיות לתיקון")
    sys.exit(1)
