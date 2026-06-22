"""
audit_chat.py — wide audit of the chat pipeline (no live LLM calls).
Exercises name normalization, ingredient recompute, recipe completeness,
JSON extraction, scaling, and macro sanity. Run: py scripts/audit_chat.py
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routers import chat as C

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("✅" if cond else "❌") + f" {name}" + (f"  — {detail}" if detail else ""))

print("=" * 64)
print("AUDIT — צ'אט תזונאי")
print("=" * 64)

# ── A. Hebrew name normalization (typos / truncations) ───────────────────
print("\n[A] נרמול שמות עברית")
cases = {
    "תפוח אדם": "תפוח אדמה",
    "תפוח אדמ": "תפוח אדמה",
    "חזה עו": "חזה עוף",
    "שמן זי": "שמן זית",
    "עגבני": "עגבנייה",
    "מלפפו": "מלפפון",
    "אבוקד": "אבוקדו",
    "קינוא": "קינואה",
    "ביצה": "ביצה",          # already correct → unchanged
    "סלמון": "סלמון",
}
for raw, want in cases.items():
    got = C._normalize_food_name(raw)
    check(f"  '{raw}' → '{want}'", got == want, f"got '{got}'")

# ── B. Ingredient calories recomputed from real data ─────────────────────
print("\n[B] חישוב קלוריות אמיתי למרכיבים")
veg = C._enrich_food({"name_he": "ירקות", "grams": 200, "calories": 665}, recompute=True)
check("  ירקות 200g סביר (<150)", veg["calories"] < 150, f"{veg['calories']} kcal")
egg = C._enrich_food({"name_he": "ביצה", "grams": 110, "calories": 9999}, recompute=True)
check("  ביצה 110g סביר (120-200)", 120 <= egg["calories"] <= 200, f"{egg['calories']} kcal")
oil = C._enrich_food({"name_he": "שמן זית", "grams": 10}, recompute=True)
check("  שמן זית 10g ~88", 70 <= oil["calories"] <= 100, f"{oil['calories']} kcal")
# implausible guard on logging path (recompute=False)
bad = C._enrich_food({"name_he": "מלפפון", "grams": 100, "calories": 800})
check("  שומר היגיון (מלפפון 800→<100)", bad["calories"] < 100, f"{bad['calories']} kcal")

# ── C. Recipe completeness: oil added when cooking ───────────────────────
print("\n[C] שלמות מתכון — הוספת שמן")
foods = [C._enrich_food({"name_he": "חזה עוף", "grams": 170}, recompute=True),
         C._enrich_food({"name_he": "ירקות", "grams": 200}, recompute=True)]
foods = C._ensure_recipe_has_fat(foods, ["מטגנים את העוף", "מוסיפים ירקות מוקפצים"])
has_oil = any("שמן" in (f.get("name_he") or "") for f in foods)
check("  שמן נוסף למתכון מטוגן", has_oil, f"{[f['name_he'] for f in foods]}")
# no oil added when nothing is cooked
foods2 = [C._enrich_food({"name_he": "יוגורט", "grams": 150}, recompute=True)]
foods2 = C._ensure_recipe_has_fat(foods2, ["מערבבים יוגורט עם פירות"])
check("  לא מוסיף שמן למנה קרה", not any("שמן" in (f.get("name_he") or "") for f in foods2))
# no duplicate oil when already present
foods3 = [C._enrich_food({"name_he": "שמן זית", "grams": 10}, recompute=True)]
foods3 = C._ensure_recipe_has_fat(foods3, ["מטגנים בשמן"])
oils = sum(1 for f in foods3 if "שמן" in (f.get("name_he") or ""))
check("  לא מכפיל שמן קיים", oils == 1, f"{oils} oils")

# ── D. JSON extraction robustness ────────────────────────────────────────
print("\n[D] חילוץ JSON מתגובת המודל")
samples = [
    ('```json\n{"reply":"היי"}\n```', "היי"),
    ('טקסט לפני ```json\n{"reply":"שלום"}\n``` טקסט אחרי', "שלום"),
    ('{"reply":"בלי גדר"}', "בלי גדר"),
    ('```\n{"reply":"בלי json תווית"}\n```', "בלי json תווית"),
]
for raw, want in samples:
    d = C._extract_json(raw)
    check(f"  חילוץ: '{want}'", d and d.get("reply") == want, f"got {d}")
# plain text returns None (no JSON)
check("  טקסט חופשי → None", C._extract_json("סתם תשובה בעברית בלי JSON") is None)

# ── E. Recipe scaling to meal target ─────────────────────────────────────
print("\n[E] כיול מתכון ליעד הארוחה")
foods = [{"name_he": "א", "grams": 100, "calories": 200, "protein": 10, "carbs": 20, "fat": 5},
         {"name_he": "ב", "grams": 100, "calories": 200, "protein": 10, "carbs": 20, "fat": 5}]
scaled = C._scale_recipe_to_target([dict(f) for f in foods], 600)
total = sum(f["calories"] for f in scaled)
check("  כיול ל-600 (מ-400)", abs(total - 600) <= 5, f"total {total}")
# tiny diff → unchanged
scaled2 = C._scale_recipe_to_target([dict(f) for f in foods], 410)
check("  שינוי זניח לא מכייל", sum(f["calories"] for f in scaled2) == 400)

# ── F. macro consistency of recomputed foods ─────────────────────────────
print("\n[F] עקביות מאקרו")
for nm in ["חזה עוף", "אורז לבן מבושל", "אבוקדו", "שקדים"]:
    f = C._enrich_food({"name_he": nm, "grams": 100}, recompute=True)
    macro_cal = f["protein"] * 4 + f["carbs"] * 4 + f["fat"] * 9
    ok = f["calories"] == 0 or abs(macro_cal - f["calories"]) <= max(25, f["calories"] * 0.2)
    check(f"  {nm}: מאקרו≈קלוריות", ok, f"cal={f['calories']} macro={round(macro_cal)}")

# ── G. Hebrew enforcement (no Arabic leaks) ──────────────────────────────
print("\n[G] אכיפת עברית")
f = C._enrich_food({"name_he": "دجاج", "name_en": "chicken", "grams": 100}, recompute=True)
has_arabic = any("؀" <= ch <= "ۿ" for ch in f["name_he"])
check("  שם ערבי לא דולף", not has_arabic, f"name='{f['name_he']}'")

# ── H. End-to-end recipe build (simulated model output) ──────────────────
print("\n[H] בניית מתכון מקצה-לקצה")
# the kind of broken recipe the model produced: typo name, hallucinated veg
# calories, frying with no oil listed
rec = {
    "title": "תפוח אדמה עם חזה עוף",
    "meal_type": "lunch",
    "instructions": ["מטגנים את חזה העוף", "מבשלים תפוח אדמה", "מוסיפים ירקות"],
    "foods": [
        {"name_he": "תפוח אדם", "name_en": "potato", "grams": 110, "calories": 150},
        {"name_he": "חזה עו", "name_en": "chicken", "grams": 170, "calories": 999},
        {"name_he": "ירקות", "name_en": "vegetables", "grams": 200, "calories": 665},
    ],
}
built = C._build_recipe_data(rec, target_cal=660)
names = [f["name_he"] for f in built["foods"]]
check("  שם תוקן: 'תפוח אדמה'", "תפוח אדמה" in names, str(names))
check("  שם תוקן: 'חזה עוף'", "חזה עוף" in names, str(names))
check("  שמן נוסף (טיגון)", any("שמן" in n for n in names), str(names))
check("  סה\"כ ≈ יעד 660", abs(built["total_calories"] - 660) <= 10, f"{built['total_calories']} kcal")
# every ingredient now has a plausible energy density
bad_dens = [f["name_he"] for f in built["foods"]
            if f["grams"] > 0 and f["calories"] / f["grams"] > 9.1]
check("  כל מרכיב בצפיפות אנרגיה סבירה", not bad_dens, f"חריגים: {bad_dens}")
check("  לכל מרכיב יש קלוריות > 0", all(f["calories"] > 0 for f in built["foods"]))

# cold recipe keeps no oil + scales down
rec2 = {"title": "יוגורט עם פירות", "meal_type": "breakfast",
        "instructions": ["מערבבים יוגורט עם פירות חתוכים"],
        "foods": [{"name_he": "יוגורט", "grams": 200, "calories": 9999},
                  {"name_he": "בננה", "grams": 120, "calories": 9999}]}
built2 = C._build_recipe_data(rec2, target_cal=300)
check("  מנה קרה בלי שמן", not any("שמן" in f["name_he"] for f in built2["foods"]))
check("  כויל ל-300", abs(built2["total_calories"] - 300) <= 10, f"{built2['total_calories']}")

# ── summary ──────────────────────────────────────────────────────────────
print("\n" + "=" * 64)
print(f"תוצאה: {len(PASS)}/{len(PASS)+len(FAIL)} עברו")
if FAIL:
    print("נכשלו:")
    for n, d in FAIL:
        print(f"  ❌ {n}  ({d})")
    sys.exit(1)
print("🎉 כל בדיקות הצ'אט עברו")
