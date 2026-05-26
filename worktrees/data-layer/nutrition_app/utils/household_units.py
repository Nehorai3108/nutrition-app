"""
household_units.py
Maps Hebrew food names to intuitive Israeli household units
(כפות, יחידות, פרוסות, גביעים, כוסות) while keeping grams
for internal calorie calculations.

Rules are ordered by specificity — longer/more-specific keywords first.
"""

from __future__ import annotations

# Each rule: ([keywords_he], (unit_he, grams_per_unit))
# The FIRST matching rule wins, so put specific names before generic ones.
_RULES: list[tuple[list[str], tuple[str, float]]] = [

    # ── Whole items / יחידות ─────────────────────────────────────────────────
    (["ביצה"],                              ("יחידה",   55.0)),
    (["שניצל עוף", "שניצל"],               ("יחידה",  130.0)),
    (["קציצת בשר", "קציצה"],               ("יחידה",   80.0)),
    (["המבורגר"],                           ("יחידה",  150.0)),
    (["לחמנייה"],                           ("יחידה",   50.0)),
    (["פיתה"],                              ("יחידה",   60.0)),
    (["לאפה", "טורטייה"],                   ("יחידה",   60.0)),
    (["בננה"],                              ("יחידה",  120.0)),
    (["תפוח עץ", "תפוח"],                   ("יחידה",  150.0)),
    (["תפוז", "מנדרינה"],                   ("יחידה",  130.0)),
    (["אבוקדו"],                            ("יחידה",  150.0)),
    (["עגבנייה"],                           ("יחידה",  100.0)),
    (["מלפפון"],                            ("יחידה",   80.0)),
    (["כנפי עוף", "כנפיים"],               ("יחידה",   80.0)),
    (["ירך עוף", "ירך"],                    ("יחידה",  120.0)),
    (["חזה עוף", "חזה"],                    ("יחידה",  150.0)),

    # ── Slices / פרוסות ─────────────────────────────────────────────────────
    (["לחם לבן", "לחם מלא", "לחם שיפון",
      "לחם קל", "לחם שחור", "לחם"],        ("פרוסה",   30.0)),

    # ── Tablespoons — spreads & oils / כפות ─────────────────────────────────
    (["שמן זית", "שמן קנולה", "שמן"],      ("כף",      14.0)),
    (["חמאה"],                              ("כף",      14.0)),
    (["טחינה גולמית", "טחינה מוכנה",
      "טחינה"],                             ("כף",      15.0)),
    (["חומוס מוכן", "חומוס"],              ("כף",      15.0)),
    (["ממרח אבוקדו", "גואקמולה"],          ("כף",      15.0)),
    (["ריבה"],                              ("כף",      20.0)),
    (["דבש"],                               ("כף",      21.0)),
    (["חמאת בוטנים"],                       ("כף",      16.0)),
    (["ממרח שוקולד", "נוטלה"],             ("כף",      20.0)),
    (["מיונז"],                             ("כף",      14.0)),
    (["קטשופ"],                             ("כף",      17.0)),

    # ── Tablespoons — grains & legumes (cooked) / כפות ──────────────────────
    # User explicitly prefers כף (tablespoon) over כוס for these
    (["אורז לבן", "אורז מלא", "אורז"],     ("כף",      20.0)),
    (["פסטה ספגטי", "פסטה פנה",
      "פסטה פרפרים", "פסטה"],              ("כף",      20.0)),
    (["קינואה"],                            ("כף",      20.0)),
    (["קוסקוס"],                            ("כף",      20.0)),
    (["עדשים כתומות", "עדשים ירוקות",
      "עדשים"],                             ("כף",      20.0)),
    (["גרגרי חומוס"],                       ("כף",      20.0)),
    (["שעועית לבנה", "שעועית אדומה",
      "שעועית"],                            ("כף",      20.0)),
    (["שיבולת שועל"],                       ("כף",      10.0)),  # dry

    # ── Cups — liquids / כוסות ───────────────────────────────────────────────
    (["חלב"],                               ("כוס",    240.0)),
    (["מיץ תפוזים", "מיץ"],               ("כוס",    200.0)),

    # ── Containers / גביעים ─────────────────────────────────────────────────
    (["יוגורט"],                            ("גביע",   125.0)),
    (["גבינת קוטג'", "קוטג'", "קוטג"],     ("גביע",   150.0)),
    (["שמנת חמוצה", "שמנת"],              ("גביע",   100.0)),

    # ── Cups — vegetables & salads / כוסות ──────────────────────────────────
    (["תרד", "חסה", "כרוב", "רוקט"],      ("כוס",    100.0)),
    (["פירות יער", "ענבים"],               ("כוס",    150.0)),
    (["גרנולה"],                            ("כוס",     60.0)),
]


def get_unit_info(food_name: str) -> tuple[str, float] | None:
    """
    Return (unit_he, grams_per_unit) for the given Hebrew food name.
    Returns None if no household unit is defined → caller should fall back to grams.
    """
    name = food_name.strip()
    for keywords, unit_info in _RULES:
        for kw in keywords:
            if kw in name or name in kw:
                return unit_info
    return None


def grams_to_household(food_name: str, grams: float) -> str:
    """
    Convert grams → human-readable Hebrew unit string.
    Examples:
        grams_to_household("אורז לבן", 100) → "5 כפות"
        grams_to_household("ביצה", 110)      → "2 יחידות"
        grams_to_household("חזה עוף", 150)   → "1 יחידה"
        grams_to_household("דג סלמון", 200)  → "200ג"   (no rule → fallback)
    """
    info = get_unit_info(food_name)
    if info is None:
        return f"{int(round(grams))}ג"

    unit_he, gpunit = info
    qty = grams / gpunit

    # Round to nearest 0.5
    qty_r = round(qty * 2) / 2
    if qty_r <= 0:
        qty_r = 0.5

    if qty_r == int(qty_r):
        qty_str = str(int(qty_r))
    else:
        qty_str = f"{qty_r:.1f}"

    # Plural suffix for יחידה
    plural = ""
    if unit_he == "יחידה" and qty_r > 1:
        plural = "ות"

    return f"{qty_str} {unit_he}{plural}"


def suggested_quantity(food_name: str, target_calories: float,
                       cal_per_100g: float) -> tuple[float, str, float]:
    """
    Given a calorie target and food, return:
        (n_units, unit_he, grams)
    where n_units is rounded to nearest 0.5.
    Falls back to grams if no unit is defined.
    """
    if cal_per_100g <= 0:
        return 1.0, "יחידה", 100.0

    info = get_unit_info(food_name)
    if info is None:
        # Fall back to grams
        grams = max(10.0, round(target_calories / cal_per_100g * 100 / 10) * 10)
        return grams, "גרם", grams

    unit_he, gpunit = info
    cal_per_unit = cal_per_100g * gpunit / 100.0
    n = target_calories / max(cal_per_unit, 1.0)
    # Round to nearest 0.5, min 0.5
    n_r = max(0.5, round(n * 2) / 2)
    grams = n_r * gpunit
    return n_r, unit_he, grams
