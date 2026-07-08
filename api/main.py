"""
BiteFit FastAPI Backend
מחליף את Streamlit — מגיש את כל הלוגיקה כ-REST API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from api.routers import auth, profile, food_log, recipes, daily_menu, chat, camera, water, barcode, workout, inventory, meal_balance, adaptation, waitlist, weight_log

app = FastAPI(title="BiteFit API", version="1.0.0")

# Native app requests (React Native) aren't subject to CORS, so this mainly guards
# browser origins (e.g. the /privacy page or any future web client). Set
# ALLOWED_ORIGINS as a comma-separated list to restrict; unset keeps "*" (no change).
_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
_allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/auth",       tags=["auth"])
app.include_router(profile.router,    prefix="/profile",    tags=["profile"])
app.include_router(food_log.router,   prefix="/food-log",   tags=["food-log"])
app.include_router(recipes.router,    prefix="/recipes",    tags=["recipes"])
app.include_router(daily_menu.router, prefix="/daily-menu", tags=["daily-menu"])
app.include_router(chat.router,       prefix="/chat",       tags=["chat"])
app.include_router(camera.router,     prefix="/camera",     tags=["camera"])
app.include_router(water.router,      prefix="/water",      tags=["water"])
app.include_router(weight_log.router, prefix="/weight-log", tags=["weight-log"])
app.include_router(barcode.router,    prefix="/barcode",    tags=["barcode"])
app.include_router(workout.router,    prefix="/workout",    tags=["workout"])
app.include_router(inventory.router,  prefix="/inventory",  tags=["inventory"])
app.include_router(meal_balance.router,  prefix="/meal-balance",  tags=["meal-balance"])
app.include_router(adaptation.router,   prefix="/adaptation",    tags=["adaptation"])
app.include_router(waitlist.router,     prefix="/waitlist",      tags=["waitlist"])

_images_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage_agents", "recipe_images", "approved")
if os.path.exists(_images_path):
    app.mount("/recipe-images", StaticFiles(directory=_images_path), name="recipe-images")

# User-captured food photos (from the camera identify flow).
_photos_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage_agents", "food_photos")
os.makedirs(_photos_path, exist_ok=True)
app.mount("/food-photos", StaticFiles(directory=_photos_path), name="food-photos")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


_PRIVACY_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NutriSmart — מדיניות פרטיות</title>
<style>
  body { font-family: -apple-system, Segoe UI, Arial, sans-serif; background:#f2ede0;
         color:#1c2b20; max-width:760px; margin:0 auto; padding:28px 20px 60px; line-height:1.7; }
  h1 { color:#3a7a4a; } h2 { color:#3a7a4a; margin-top:28px; font-size:1.15rem; }
  a { color:#3a7a4a; } .en { direction:ltr; text-align:left; margin-top:48px;
      border-top:1px solid #d8d0bd; padding-top:24px; }
  .muted { color:#6b7568; font-size:.9rem; }
</style>
</head>
<body>
<h1>מדיניות פרטיות — NutriSmart</h1>
<p class="muted">עודכן לאחרונה: יולי 2026</p>

<p>NutriSmart ("האפליקציה") היא אפליקציית תזונה אישית. מסמך זה מסביר אילו נתונים אנו אוספים וכיצד אנו משתמשים בהם.</p>

<h2>אילו נתונים אנו אוספים</h2>
<ul>
  <li><b>פרטי פרופיל</b> — גיל, מין, גובה, משקל, יעדי תזונה שאתה מזין, לצורך חישוב יעדים קלוריים.</li>
  <li><b>יומן מזון</b> — מאכלים שרשמת, כמויות, וערכים תזונתיים.</li>
  <li><b>תמונות מזון</b> — תמונות שאתה מצלם לזיהוי מזון. התמונות מעובדות לזיהוי בלבד.</li>
  <li><b>הקלטות קול</b> — הקלטה שאתה יוצר להזנת מזון בדיבור, מתומללת לטקסט ואינה נשמרת לאחר התמלול.</li>
</ul>

<h2>כיצד אנו משתמשים בנתונים</h2>
<p>הנתונים משמשים אך ורק כדי לספק את שירות התזונה: חישוב יעדים, בניית תפריטים, מעקב יומי וזיהוי מזון. איננו מוכרים את הנתונים שלך לצד שלישי.</p>

<h2>שירותי צד שלישי</h2>
<ul>
  <li><b>Groq</b> — עיבוד שפה טבעית וזיהוי מזון בצ'אט ותמלול קול.</li>
  <li><b>OpenFoodFacts</b> — מאגר נתוני מזון ציבורי לזיהוי מוצרים.</li>
  <li><b>Supabase</b> — אחסון מאובטח של הפרופיל ויומן המזון שלך.</li>
</ul>

<h2>הרשאות מכשיר</h2>
<p><b>מצלמה</b> — לסריקת ברקוד וצילום מזון. <b>מיקרופון</b> — להזנת מזון בדיבור. ההרשאות פעילות רק בזמן שימוש יזום שלך בפיצ'ר.</p>

<h2>מחיקת נתונים</h2>
<p>ניתן למחוק את החשבון וכל הנתונים לצמיתות ישירות מתוך האפליקציה: הגדרות → חשבון → מחיקת חשבון. לחלופין אפשר לפנות לכתובת המייל למטה.</p>

<h2>יצירת קשר</h2>
<p>לשאלות בנושא פרטיות: <a href="mailto:dviryona8@gmail.com">dviryona8@gmail.com</a></p>

<div class="en">
<h1>Privacy Policy — NutriSmart</h1>
<p class="muted">Last updated: July 2026</p>
<p>NutriSmart is a personal nutrition app. We collect profile details (age, sex, height, weight, goals), your food log, food photos you capture (processed for recognition only), and voice recordings (transcribed to text, not retained). Data is used solely to provide the nutrition service and is never sold. Third-party services: Groq (AI food recognition &amp; voice transcription), OpenFoodFacts (public food database), Supabase (secure data storage). Camera and microphone permissions are used only during active use of those features. You may request full deletion of your data at any time by contacting <a href="mailto:dviryona8@gmail.com">dviryona8@gmail.com</a>.</p>
</div>
</body>
</html>"""


_TERMS_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NutriSmart — תנאי שימוש</title>
<style>
  body { font-family: -apple-system, Segoe UI, Arial, sans-serif; background:#f2ede0;
         color:#1c2b20; max-width:760px; margin:0 auto; padding:28px 20px 60px; line-height:1.7; }
  h1 { color:#3a7a4a; } h2 { color:#3a7a4a; margin-top:28px; font-size:1.15rem; }
  a { color:#3a7a4a; } .en { direction:ltr; text-align:left; margin-top:48px;
      border-top:1px solid #d8d0bd; padding-top:24px; }
  .muted { color:#6b7568; font-size:.9rem; }
  .warn { background:#fff4e5; border:1px solid #e0c48a; border-radius:8px; padding:12px 16px; }
</style>
</head>
<body>
<h1>תנאי שימוש — NutriSmart</h1>
<p class="muted">עודכן לאחרונה: יולי 2026</p>

<p>השימוש באפליקציית NutriSmart ("האפליקציה") כפוף לתנאים הבאים. עצם השימוש מהווה הסכמה לתנאים אלה.</p>

<h2>1. השירות</h2>
<p>האפליקציה מספקת מעקב תזונה, בניית תפריטים, זיהוי מזון ומעקב אחר יעדים אישיים. אנו שואפים לדיוק אך איננו מתחייבים לכך שכל הערכים התזונתיים או ההמלצות מדויקים לחלוטין.</p>

<h2>2. אינו ייעוץ רפואי</h2>
<div class="warn">
<p>NutriSmart אינה מספקת ייעוץ רפואי, אבחון או טיפול. המידע באפליקציה הוא למטרות מידע כללי בלבד ואינו תחליף לייעוץ של רופא, דיאטן או איש מקצוע מוסמך. התייעץ תמיד עם גורם רפואי לפני שינויים משמעותיים בתזונה, במיוחד אם יש לך מצב רפואי, אלרגיות, או שאתה בהיריון.</p>
</div>

<h2>3. אחריות המשתמש</h2>
<p>אתה אחראי לדיוק הנתונים שאתה מזין ולהחלטות התזונתיות שאתה מקבל. אין להשתמש באפליקציה למטרות בלתי חוקיות או לפגיעה באחרים.</p>

<h2>4. חשבון</h2>
<p>אתה אחראי לשמירת סודיות פרטי ההתחברות שלך. ניתן למחוק את החשבון בכל עת מתוך האפליקציה (הגדרות → חשבון → מחיקת חשבון).</p>

<h2>5. מנויים ותשלומים</h2>
<p>אם וכאשר יוצעו תכונות בתשלום, החיוב יתבצע דרך חשבון ה-App Store שלך בהתאם לתנאי Apple. ניתן לבטל מנוי דרך הגדרות ה-App Store.</p>

<h2>6. הגבלת אחריות</h2>
<p>האפליקציה מסופקת "כפי שהיא" (AS IS). איננו אחראים לכל נזק ישיר או עקיף הנובע מהשימוש בה, במידה המרבית המותרת בחוק.</p>

<h2>7. שינויים</h2>
<p>אנו רשאים לעדכן תנאים אלה מעת לעת. המשך השימוש לאחר עדכון מהווה הסכמה לתנאים המעודכנים.</p>

<h2>8. יצירת קשר</h2>
<p>לשאלות: <a href="mailto:dviryona8@gmail.com">dviryona8@gmail.com</a></p>

<div class="en">
<h1>Terms of Service — NutriSmart</h1>
<p class="muted">Last updated: July 2026</p>
<p>By using NutriSmart ("the App") you agree to these terms. The App provides nutrition tracking, meal planning and food recognition for general informational purposes. <b>The App does not provide medical advice, diagnosis or treatment and is not a substitute for a physician or licensed dietitian; consult a professional before significant dietary changes, especially with a medical condition, allergies or pregnancy.</b> You are responsible for the accuracy of the data you enter and for your dietary decisions. You may delete your account and all data at any time in Settings → Account → Delete Account. Any paid features are billed through your App Store account under Apple's terms and can be cancelled in App Store settings. The App is provided "AS IS" without warranties, and we are not liable for damages arising from its use to the maximum extent permitted by law. We may update these terms; continued use constitutes acceptance. Contact: <a href="mailto:dviryona8@gmail.com">dviryona8@gmail.com</a>.</p>
</div>
</body>
</html>"""


@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    """Public privacy policy — required URL for App Store / Play Store submission."""
    return _PRIVACY_HTML


@app.get("/terms", response_class=HTMLResponse)
def terms():
    """Public terms of service — includes the not-medical-advice disclaimer."""
    return _TERMS_HTML


@app.get("/diag")
def diag():
    """Deployment diagnostics — confirms which build is live and key/feature state."""
    import subprocess
    commit = os.environ.get("RENDER_GIT_COMMIT", "")
    if not commit:
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(os.path.dirname(__file__)),
            ).decode().strip()
        except Exception:
            commit = "unknown"
    try:
        from nutrition_app.agents.agent_recipe_images.image_fetcher import _get_api_key
        has_pexels = bool(_get_api_key())
    except Exception:
        has_pexels = False
    # Live image resolution probe for a previously-broken food name.
    try:
        from api.food_image import get_food_image
        probe = get_food_image("", "פתיבר")
    except Exception as e:
        probe = f"error: {e}"
    # Live household-unit probe: run the real recipe builder on a sample.
    try:
        from api.routers.chat import _build_recipe_data
        _r = _build_recipe_data({"title": "t", "meal_type": "morning_snack", "foods": [
            {"name_he": "טוטים", "name_en": "strawberries", "grams": 50,
             "calories": 20, "protein": 0, "carbs": 5, "fat": 0}]}, None)
        household = _r["foods"][0].get("display_he")
    except Exception as e:
        household = f"error: {e}"
    return {
        "commit": commit[:12],
        "has_pexels_key": has_pexels,
        "public_base_url": os.environ.get("PUBLIC_BASE_URL", ""),
        "household_probe": household,
        "petibeur_image": probe,
    }
