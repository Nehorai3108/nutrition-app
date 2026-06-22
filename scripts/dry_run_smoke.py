"""
dry_run_smoke.py — 22 end-to-end smoke checks across the whole system.
A pre-launch "dress rehearsal". Run:  py scripts/dry_run_smoke.py
"""
import sys, os, json, glob
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    mark = "✅" if cond else "❌"
    print(f"{mark} {name}" + (f"  — {detail}" if detail else ""))

# ── setup ──────────────────────────────────────────────────────────────
from api.routers.profile import build_user_profile, derive_weekly_change_kg, compute_targets
from nutrition_app.agents.agent_2_nutrition import NutritionEngine
from nutrition_app.agents.agent_12_adaptation.adaptation_engine import AdaptationEngine

eng = NutritionEngine()
adapt = AdaptationEngine()

def prof(**kw):
    base = {"name": "T", "gender": "male", "date_of_birth": "1995-01-01",
            "height_cm": 178, "weight_kg": 85, "activity_level": "moderately_active",
            "goal": "maintain"}
    base.update(kw)
    return base

def targets(p):
    pr = build_user_profile(p, "_smoke")
    wc = derive_weekly_change_kg(p)
    tw = p.get("target_weight")
    return eng.calculate_targets(pr, weekly_change_kg=wc,
                                 target_weight_kg=float(tw) if tw else None)

print("=" * 60)
print("DRY RUN — 22 בדיקות מערכת")
print("=" * 60)

# 1. BMR positive + Mifflin
t = targets(prof())
check("1. BMR מחושב וחיובי", t.bmr_kcal > 1500, f"bmr={round(t.bmr_kcal)}")

# 2. TDEE > BMR
check("2. TDEE גדול מ-BMR", t.tdee_kcal > t.bmr_kcal, f"tdee={round(t.tdee_kcal)}")

# 3. maintain ≈ tdee
check("3. שמירה ≈ TDEE", abs(t.target_calories_kcal - t.tdee_kcal) < 50,
      f"target={round(t.target_calories_kcal)}")

# 4. lose_weight < maintain
tl = targets(prof(goal="lose_weight"))
check("4. ירידה < שמירה", tl.target_calories_kcal < t.target_calories_kcal,
      f"lose={round(tl.target_calories_kcal)}")

# 5. gain_weight > maintain
tg = targets(prof(goal="gain_weight"))
check("5. עלייה > שמירה", tg.target_calories_kcal > t.target_calories_kcal,
      f"gain={round(tg.target_calories_kcal)}")

# 6. target weight short timeline → bigger deficit than long timeline
short = targets(prof(goal="lose_weight", target_weight=75, weeks_to_goal=8))
long  = targets(prof(goal="lose_weight", target_weight=75, weeks_to_goal=20))
check("6. יעד בזמן קצר = גירעון גדול יותר", short.target_calories_kcal < long.target_calories_kcal,
      f"8wk={round(short.target_calories_kcal)} vs 20wk={round(long.target_calories_kcal)}")

# 7. calorie floor never < 1200
extreme = targets(prof(goal="lose_weight", target_weight=60, weeks_to_goal=4))
check("7. רצפת קלוריות ≥ 1200", extreme.target_calories_kcal >= 1200,
      f"target={round(extreme.target_calories_kcal)}")

# 8. macros sum to calories (±15 kcal)
macro_cal = t.protein_g * 4 + t.carbs_g * 4 + t.fat_g * 9
check("8. מאקרו מסתכם לקלוריות", abs(macro_cal - t.target_calories_kcal) < 15,
      f"macro={round(macro_cal)} target={round(t.target_calories_kcal)}")

# 9. protein scales with weight (heavier → more protein)
light = targets(prof(weight_kg=60, goal="lose_weight"))
heavy = targets(prof(weight_kg=100, goal="lose_weight"))
check("9. חלבון עולה עם משקל", heavy.protein_g > light.protein_g,
      f"60kg={round(light.protein_g)}g 100kg={round(heavy.protein_g)}g")

# 10. derive_weekly_change_kg math
wc = derive_weekly_change_kg(prof(target_weight=75, weeks_to_goal=10))
check("10. חישוב קצב שבועי", abs(wc - 1.0) < 0.01, f"weekly={wc}")

# 11. female BMR < male BMR (same stats)
tf = targets(prof(gender="female"))
check("11. BMR נשי < גברי", tf.bmr_kcal < t.bmr_kcal,
      f"female={round(tf.bmr_kcal)} male={round(t.bmr_kcal)}")

# 12. adaptation day-target cold start = base
pr = build_user_profile(prof(goal="lose_weight", target_weight=75, weeks_to_goal=12), "_smoke12")
base12 = targets(prof(goal="lose_weight", target_weight=75, weeks_to_goal=12))
day = adapt.adjusted_day_target(pr, base12)
check("12. אדפטציה cold-start = בסיס", day.calories == round(base12.target_calories_kcal),
      f"day={day.calories} base={round(base12.target_calories_kcal)}")
for fp in glob.glob("storage_agents/adaptation/_smoke12*"): os.remove(fp)

# 13. meal subtargets: breakfast present & reasonable
pr13 = build_user_profile(prof(goal="lose_weight", target_weight=75, weeks_to_goal=12), "_smoke13")
day13 = adapt.adjusted_day_target(pr13, base12)
subs = adapt.meal_subtargets(pr13, base12, day13, {})
bf = next((s for s in subs if s.meal_type == "breakfast"), None)
check("13. יעד ארוחת בוקר תקין", bf is not None and 300 < bf.calories < 800,
      f"breakfast={bf.calories if bf else None} kcal")

# 14. subtargets sum ≈ day target
total_sub = sum(s.calories for s in subs)
check("14. סכום ארוחות ≈ יעד יומי", abs(total_sub - day13.calories) < 50,
      f"sum={total_sub} day={day13.calories}")
for fp in glob.glob("storage_agents/adaptation/_smoke13*"): os.remove(fp)

# 15. food catalog has 450+ items
with open(os.path.join(ROOT, "nutrition_app/data/foods_extended.json"), encoding="utf-8") as f:
    foods = json.load(f)
check("15. מסד מזון ≥ 450 פריטים", len(foods) >= 450, f"count={len(foods)}")

# 16. food catalog lookup works
from nutrition_app.agents.agent_3_food import FoodCatalog
cat = FoodCatalog()
all_foods = cat.get_all_foods()
chicken = [f for f in all_foods if "עוף" in (f.name_he or "")]
check("16. חיפוש בקטלוג (עוף)", len(chicken) > 0, f"matches={len(chicken)}")

# 17. camera IL table — pita portion math
from api.routers.camera import _lookup_il_table
pita = _lookup_il_table("פיתה לבנה", 60)
check("17. טבלת מזון — פיתה 60g", pita and 150 < pita["calories"] < 180,
      f"60g pita={pita['calories'] if pita else None} kcal")

# 18. camera Hebrew enforcement (strips Arabic)
from api.routers.camera import _ensure_hebrew
fixed = _ensure_hebrew("دجاج", "Chicken")
check("18. אכיפת עברית (חוסם ערבית)", fixed == "Chicken", f"result={fixed}")

# 19. camera crossref validates macros
from api.routers.camera import _crossref_and_validate
bad = _crossref_and_validate({"name": "Mystery", "name_he": "מאכל לא ידוע",
                              "grams": 100, "calories": 5000,
                              "protein": 10, "carbs": 10, "fat": 10})
check("19. תיקון קלוריות לא הגיוניות", bad["calories"] < 1000,
      f"corrected={bad['calories']} kcal")

# 20. recipes.json integrity — all have ingredients
with open(os.path.join(ROOT, "storage_agents/recipes/recipes.json"), encoding="utf-8") as f:
    recipes = json.load(f)
no_ing = [r.get("recipe_id") for r in recipes if not r.get("ingredients")]
check("20. כל המתכונים עם מרכיבים", len(no_ing) == 0,
      f"recipes={len(recipes)} missing={len(no_ing)}")

# 21. recipe images coverage
img_dir = os.path.join(ROOT, "storage_agents/recipe_images/approved")
imgs = set(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(img_dir, "*.jpg")))
rec_ids = set(r.get("recipe_id") for r in recipes)
covered = sum(1 for rid in rec_ids if rid in imgs)
check("21. כיסוי תמונות מתכונים", covered > 0, f"covered={covered}/{len(rec_ids)}")

# 22. FastAPI app + all routers import
import api.main
route_count = len([r for r in api.main.app.routes])
check("22. FastAPI + כל ה-routers נטענים", route_count > 30, f"routes={route_count}")

# ── summary ────────────────────────────────────────────────────────────
print("=" * 60)
print(f"תוצאה: {len(PASS)}/{len(PASS)+len(FAIL)} עברו")
if FAIL:
    print("נכשלו:", ", ".join(FAIL))
    sys.exit(1)
print("🎉 כל הבדיקות עברו — המערכת מוכנה")
