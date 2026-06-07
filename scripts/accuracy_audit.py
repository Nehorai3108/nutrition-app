"""
Accuracy audit for all recipes and food DB.
Run: python scripts/accuracy_audit.py
"""
import json, sqlite3, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RECIPES_PATH = Path("storage_agents/recipes/recipes.json")
DB_PATH      = Path("storage/nutrition.db")

with open(RECIPES_PATH, encoding="utf-8") as f:
    recipes = json.load(f)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

PASS = "✅"; WARN = "⚠ "; FAIL = "❌"

issues = []

def flag(level, rid, name, msg):
    issues.append((level, rid, name, msg))

# ── 1. Missing nutrition ──────────────────────────────────────────────────────
for r in recipes:
    rid  = r.get("recipe_id","?")
    name = r.get("name_he","?")
    nut  = r.get("total_nutrition") or {}
    if not nut or nut.get("calories") is None:
        flag(FAIL, rid, name, "חסר total_nutrition לחלוטין")
        continue
    for field in ("calories","protein","carbs","fat"):
        if nut.get(field) is None:
            flag(FAIL, rid, name, f"חסר שדה {field}")

# ── 2. Calorie sanity per portion ────────────────────────────────────────────
for r in recipes:
    rid      = r.get("recipe_id","?")
    name     = r.get("name_he","?")
    nut      = r.get("total_nutrition") or {}
    portions = max(r.get("portions",1) or 1, 1)
    cal      = nut.get("calories")
    if cal is None: continue
    per_portion = cal / portions
    if per_portion < 80:
        flag(WARN, rid, name, f"מנה זעירה: {per_portion:.0f} קק\"ל למנה (סה\"כ {cal}, {portions} מנות)")
    elif per_portion > 1500:
        flag(WARN, rid, name, f"מנה ענקית: {per_portion:.0f} קק\"ל למנה (סה\"כ {cal}, {portions} מנות)")

# ── 3. Macro-calorie consistency  (P*4 + C*4 + F*9 should ≈ calories) ────────
for r in recipes:
    rid  = r.get("recipe_id","?")
    name = r.get("name_he","?")
    nut  = r.get("total_nutrition") or {}
    cal   = nut.get("calories")
    prot  = nut.get("protein")
    carbs = nut.get("carbs")
    fat   = nut.get("fat")
    if None in (cal, prot, carbs, fat) or cal == 0:
        continue
    calc = prot * 4 + carbs * 4 + fat * 9
    diff_pct = abs(calc - cal) / cal * 100
    if diff_pct > 25:
        flag(WARN, rid, name,
             f"אי-עקביות מאקרוים: {cal} קק\"ל אבל P{prot}+C{carbs}+F{fat} → {calc:.0f} קק\"ל (Δ{diff_pct:.0f}%)")

# ── 4. Impossible macros ─────────────────────────────────────────────────────
for r in recipes:
    rid  = r.get("recipe_id","?")
    name = r.get("name_he","?")
    nut  = r.get("total_nutrition") or {}
    cal   = nut.get("calories") or 0
    prot  = nut.get("protein")  or 0
    carbs = nut.get("carbs")    or 0
    fat   = nut.get("fat")      or 0
    if fat * 9 > cal * 1.1 and cal > 0:
        flag(FAIL, rid, name, f"שומן בלתי אפשרי: {fat}g שומן ({fat*9:.0f} קק\"ל) > סה\"כ {cal} קק\"ל")
    if prot * 4 > cal * 1.1 and cal > 0:
        flag(FAIL, rid, name, f"חלבון בלתי אפשרי: {prot}g חלבון ({prot*4:.0f} קק\"ל) > סה\"כ {cal} קק\"ל")
    if prot < 0 or carbs < 0 or fat < 0:
        flag(FAIL, rid, name, f"ערך שלילי: P={prot} C={carbs} F={fat}")

# ── 5. Zero-calorie non-water ingredients ────────────────────────────────────
for r in recipes:
    rid  = r.get("recipe_id","?")
    name = r.get("name_he","?")
    nut  = r.get("total_nutrition") or {}
    cal  = nut.get("calories") or 0
    if cal == 0 and r.get("ingredients"):
        ings = [i.get("food_name_en","") or i.get("food_name","") for i in r.get("ingredients",[])]
        non_water = [i for i in ings if i.lower() not in ("water","cold water","ice","")]
        if non_water:
            flag(FAIL, rid, name, f"0 קק\"ל למרות מרכיבים: {', '.join(non_water[:3])}")

# ── 6. Food DB spot-check — calories vs macro formula ────────────────────────
cur.execute("""
    SELECT food_id, name_he, name_en, calories_kcal, protein_g, carbs_g, fat_g
    FROM foods
    WHERE calories_kcal IS NOT NULL AND protein_g IS NOT NULL
      AND carbs_g IS NOT NULL AND fat_g IS NOT NULL
      AND calories_kcal > 0
""")
db_issues = []
for row in cur.fetchall():
    calc = row["protein_g"]*4 + row["carbs_g"]*4 + row["fat_g"]*9
    diff_pct = abs(calc - row["calories_kcal"]) / row["calories_kcal"] * 100
    if diff_pct > 30:
        db_issues.append((row["food_id"], row["name_en"], row["calories_kcal"], round(calc), round(diff_pct)))

# ── Report ────────────────────────────────────────────────────────────────────
fails  = [x for x in issues if x[0] == FAIL]
warns  = [x for x in issues if x[0] == WARN]

print("=" * 65)
print("  ACCURACY AUDIT — BiteFit Recipes")
print("=" * 65)
print(f"  סה\"כ מתכונים: {len(recipes)}")
print(f"  {FAIL} בעיות קריטיות: {len(fails)}")
print(f"  {WARN} אזהרות:        {len(warns)}")
print()

if fails:
    print(f"── {FAIL} בעיות קריטיות ──────────────────────────────────────")
    for _, rid, name, msg in fails:
        print(f"  {rid} | {name}")
        print(f"    → {msg}")
    print()

if warns:
    print(f"── {WARN} אזהרות ─────────────────────────────────────────────")
    for _, rid, name, msg in warns:
        print(f"  {rid} | {name}")
        print(f"    → {msg}")
    print()

if db_issues:
    print(f"── {WARN} DB Food — אי-עקביות מאקרוים (מדגם, >30% סטייה) ──")
    for fid, fname, cal, calc, diff in db_issues[:20]:
        print(f"  {fid} | {fname[:40]}")
        print(f"    → DB={cal} קק\"ל  |  חישוב מאקרוים={calc} קק\"ל  (Δ{diff}%)")
    if len(db_issues) > 20:
        print(f"  ... ועוד {len(db_issues)-20} רשומות")
    print()

total_issues = len(fails) + len(warns)
if total_issues == 0:
    print(f"{PASS} אין בעיות — כל הערכים תקינים!")
else:
    print(f"סיכום: {len(fails)} קריטי / {len(warns)} אזהרה / {len(db_issues)} DB")
