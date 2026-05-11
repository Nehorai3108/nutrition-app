"""
Hebrew meal text parser — no API key required.
Extracts food items + quantities from free Hebrew text.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

# ── Hebrew number words → float ───────────────────────────────────────────────
HEB_NUMBERS = {
    "שלושה רבעים": 0.75,
    "שני שלישים": 0.667,
    "שליש": 0.333,
    "חצי": 0.5,
    "רבע": 0.25,
    "אחד": 1, "אחת": 1,
    "שניים": 2, "שתיים": 2, "שני": 2, "שתי": 2,
    "שלושה": 3, "שלוש": 3,
    "ארבעה": 4, "ארבע": 4,
    "חמישה": 5, "חמש": 5,
    "שישה": 6, "שש": 6,
    "שבעה": 7, "שבע": 7,
    "שמונה": 8,
    "תשעה": 9, "תשע": 9,
    "עשרה": 10, "עשר": 10,
    "אחד עשר": 11, "אחת עשרה": 11,
    "שנים עשר": 12, "שתים עשרה": 12,
    "חמישה עשר": 15, "חמש עשרה": 15,
    "עשרים": 20,
    "שלושים": 30,
}

# ── Unit → grams conversion ───────────────────────────────────────────────────
UNIT_TO_GRAMS = {
    # Weight
    "גרם": 1, "גר": 1, "גר׳": 1, "ג׳": 1, "ג": 1,
    "קילוגרם": 1000, "קילו": 1000, "קג": 1000, "ק״ג": 1000,
    # Volume
    "כוס": 240, "כוסות": 240,
    "כף": 15, "כפות": 15,
    "כפית": 5, "כפיות": 5,
    "מיליליטר": 1, "מ״ל": 1, "מל": 1,
    "ליטר": 1000, "ל׳": 1000,
    "מ״ל": 1,
    # Portion descriptors
    "יחידה": None, "יחידות": None,
    "חתיכה": None, "חתיכות": None,
    "פרוסה": 30, "פרוסות": 30,
    "קציצה": 80, "קציצות": 80,
    "עוגייה": 15, "עוגיות": 15,
    "מנה": None, "מנות": None,
    "צלחת": None, "צלחות": None,
    "קערה": None, "קערות": None,
    "קופסה": None, "קופסאות": None,
    "פחית": 330, "פחיות": 330,
    "בקבוק": 500, "בקבוקים": 500,
    "חבילה": None, "חבילות": None,
    "קרטון": None,
    "כדור": None, "כדורים": None,   # e.g. כדורי גלידה
    "פרי": None, "פירות": None,
    "ביצה": 55, "ביצים": 55,        # average egg weight
    "רצועה": None, "רצועות": None,  # strips
    "שקית": None, "שקיות": None,
    "סיר": None,
    "תרמיל": None,
    "קוביה": 10, "קוביות": 10,      # e.g. קוביות סוכר / גבינה
    "פרוסת": 30,                     # construct form: פרוסת לחם
    "כוסית": 100, "כוסיות": 100,    # small cup / shot glass area
    "קפסולה": None, "קפסולות": None,
    "גביע": 125, "גביעים": 125,     # yogurt cup
    "שקדייה": None,                  # almond-shaped cookie
    "לחמנייה": 50, "לחמניות": 50,
    "עלה": None, "עלים": None,       # e.g. עלי חסה
}

# ── Meal type keywords ────────────────────────────────────────────────────────
MEAL_KEYWORDS = {
    "breakfast":       ["ארוחת בוקר", "בראנץ׳", "בראנץ", "ארוחת שחר", "בוקר"],
    "morning_snack":   ["חטיף של בוקר", "חטיף בוקר", "הפסקת בוקר"],
    "lunch":           ["ארוחת צהריים", "אמצע היום", "הפסקת צהריים", "צהריים"],
    "afternoon_snack": ["חטיף אחרי הצהריים", "חטיף אחה״צ", "אחרי הצהריים", "אחה״צ", "חטיף"],
    "dinner":          ["ארוחת ערב", "ארוחת לילה", "לילה", "ערב"],
    "evening_snack":   ["חטיף לילה", "חטיף ערב", "נשנוש לילה"],
}

# ── Compound food names that should NOT be split on "עם" ──────────────────────
COMPOUND_FOODS = [
    # Drinks
    "קפה עם חלב", "קפה עם סוכר", "תה עם לימון", "תה עם חלב",
    "קפה עם שמנת", "שוקו עם חלב",
    # Bread / sandwiches
    "לחם עם חמאה", "לחם עם גבינה", "לחם עם ביצה",
    "פיתה עם חומוס", "פיתה עם ביצה", "פיתה עם לאפה",
    "טוסט עם ביצה", "טוסט עם גבינה", "טוסט עם אבוקדו",
    # Grain + dairy
    "דגן עם חלב", "גרנולה עם יוגורט", "שיבולת שועל עם חלב",
    "קוואקר עם חלב", "כוסמת עם חלב",
    # Protein + side
    "עוף עם אורז", "עוף עם ירקות", "עוף עם תפוחי אדמה",
    "בשר עם אורז", "דג עם ירקות", "דג עם אורז",
    # Salad combos
    "סלט עם טונה", "סלט עם ביצה", "סלט עם גבינה",
    # Fruit + dairy
    "יוגורט עם פירות", "קוטג׳ עם פירות", "גבינה עם דבש",
]

# ── Food word aliases (Hebrew slang / short forms → canonical search term) ────
FOOD_ALIASES: dict = {
    # Dairy
    "קוטג'": "גבינת קוטג'",
    "קוטג׳": "גבינת קוטג'",
    "בולגרית": "גבינה בולגרית",
    "צהובה": "גבינה צהובה",
    "לבנה": "גבינה לבנה",
    "שמנת חמוצה": "שמנת חמוצה",
    "שמנת": "שמנת",
    "פרמז'ן": "גבינת פרמזן",
    "פרמז׳ן": "גבינת פרמזן",
    "ריקוטה": "גבינת ריקוטה",
    "מוצרלה": "גבינת מוצרלה",
    # Meat / chicken
    "חזה": "חזה עוף",
    "שניצל": "שניצל עוף",
    "כנפיים": "כנפי עוף",
    "ירך": "ירך עוף",
    "פרגית": "פרגית עוף",
    "קבב": "קבב בקר",
    # Fish
    "טונה": "טונה בשמן",
    "סלמון": "דג סלמון",
    "לוקוס": "דג לוקוס",
    "בורי": "דג בורי",
    # Bread / grains
    "לאפה": "פיתה",
    "פיתות": "פיתה",
    "טורטיה": "טורטייה",
    "קרואסון": "קרואסן",
    "ספגטי": "פסטה ספגטי",
    "פנה": "פסטה פנה",
    "פסטה": "פסטה",
    "אורז": "אורז לבן",
    "אורז מלא": "אורז מלא",
    "קינואה": "קינואה",
    "קוסקוס": "קוסקוס",
    "עדשים": "עדשים כתומות",
    "חומוס גרגרים": "חומוס גרגרים",
    # Vegetables
    "עגבנייה": "עגבנייה",
    "עגבניות": "עגבנייה",
    "מלפפון": "מלפפון",
    "חסה": "חסה",
    "גזר": "גזר",
    "בצל": "בצל",
    "ברוקולי": "ברוקולי",
    "תרד": "תרד",
    "פלפל": "פלפל אדום",
    "פלפל ירוק": "פלפל ירוק",
    "תפוח אדמה": "תפוח אדמה",
    "בטטה": "בטטה",
    "כרובית": "כרובית",
    "קישוא": "קישוא",
    "חצילים": "חציל",
    "חציל": "חציל",
    # Fruits
    "תפוח": "תפוח עץ",
    "בננה": "בננה",
    "תפוז": "תפוז",
    "מנגו": "מנגו",
    "אבוקדו": "אבוקדו",
    "ענבים": "ענבים",
    "תות": "תות שדה",
    "תותים": "תות שדה",
    "אפרסק": "אפרסק",
    "אגס": "אגס",
    "מלון": "מלון",
    "אבטיח": "אבטיח",
    "שזיף": "שזיף",
    # Drinks
    "מיץ תפוזים": "מיץ תפוזים",
    "מיץ": "מיץ פרי",
    "קפה שחור": "קפה שחור",
    "אספרסו": "קפה אספרסו",
    "לאטה": "קפה לאטה",
    "קפוצינו": "קפה קפוצ'ינו",
    "קפוצ'ינו": "קפה קפוצ'ינו",
    "שוקו": "שוקולד חם",
    "חלב": "חלב 3%",
    "מים": "מים",
    # Snacks / sweets
    "שוקולד": "שוקולד מריר",
    "חטיף": "חטיף דגנים",
    "במבה": "במבה",
    "ביסלי": "ביסלי",
    "פופקורן": "פופקורן",
    "קרקר": "קרקר",
    "קרקרים": "קרקר",
    "עוגיות": "עוגיית שוקולד",
    "עוגייה": "עוגיית שוקולד",
    "גלידה": "גלידה וניל",
    # Spreads / condiments
    "חמאה": "חמאה",
    "מרגרינה": "מרגרינה",
    "טחינה": "טחינה גולמית",
    "חומוס": "חומוס מוכן",
    "גואקמולה": "ממרח אבוקדו",
    "ריבה": "ריבה",
    "דבש": "דבש",
    "שמן זית": "שמן זית",
    "שמן": "שמן צמחי",
    # Eggs
    "ביצה": "ביצה",
    "ביצים": "ביצה",
    "ביצה קשה": "ביצה קשה",
    "חביתה": "חביתה",
    "שקשוקה": "שקשוקה",
    # Legumes
    "שעועית": "שעועית לבנה",
    "פול": "פול",
    "אפונה": "אפונה ירוקה",
    # Other
    "גרנולה": "גרנולה",
    "מוזלי": "מוזלי",
    "יוגורט": "יוגורט",
    "לבן": "יוגורט",   # "לבן" alone often means לבן / שתייה
}


@dataclass
class ParsedFoodItem:
    raw_text: str
    food_query: str
    quantity: float
    unit: str
    grams: Optional[float]


@dataclass
class ParseResult:
    items: List[ParsedFoodItem]
    meal_type: str
    confidence: float


def _detect_meal_type(text: str) -> str:
    text_l = text.lower()
    # Sort keywords longest-first so "ארוחת בוקר" matches before "בוקר"
    for meal_type, keywords in MEAL_KEYWORDS.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in text_l:
                return meal_type
    # Guess from food context cues
    if any(w in text_l for w in ["בוקר", "קפה", "שמנת", "דגני", "גרנולה", "קוואקר",
                                   "שיבולת שועל", "אספרסו", "לאטה", "קפוצינו"]):
        return "breakfast"
    if any(w in text_l for w in ["ערב", "לילה"]):
        return "dinner"
    return "lunch"


def _parse_quantity(token: str) -> Optional[float]:
    token = token.strip()
    try:
        return float(token.replace(",", "."))
    except ValueError:
        pass
    for heb, val in sorted(HEB_NUMBERS.items(), key=lambda x: -len(x[0])):
        if token == heb or token.startswith(heb + " "):
            return val
    return None


def _split_to_segments(text: str) -> List[str]:
    """Split text into food segments on conjunctions, commas and 'עם'."""
    # Remove meal-time context phrases
    for meal_type, keywords in MEAL_KEYWORDS.items():
        for kw in sorted(keywords, key=len, reverse=True):
            text = re.sub(r'(?:ל|ב)?' + re.escape(kw), '', text, flags=re.IGNORECASE)

    # Protect compound food names from splitting
    placeholder_map = {}
    for i, compound in enumerate(COMPOUND_FOODS):
        if compound in text:
            ph = f"__COMPOUND_{i}__"
            placeholder_map[ph] = compound
            text = text.replace(compound, ph)

    # Split on: comma, וגם, ועם, וכן, בנוסף, פלוס, ו+word, עם
    # "עם" as separator when between food items (not at start of segment)
    separators = (
        r'(?:'
        r',|،|'                          # commas
        r'\bוגם\b|\bועם\b|\bוכן\b|'     # ו-conjunctions
        r'\bבנוסף\b|\bפלוס\b|'          # additionally / plus
        r'\bו(?=\s*[א-ת])|'            # ו before Hebrew
        r'(?<=\s)\bעם\b(?=\s)|'        # עם surrounded by spaces (between items)
        r'\+)'
    )
    segments = re.split(separators, text)

    # Restore compound names
    result = []
    for seg in segments:
        seg = seg.strip()
        for ph, original in placeholder_map.items():
            seg = seg.replace(ph, original)
        # Clean up leading/trailing noise
        seg = re.sub(r'^(של|מ|את|ה|ו|ל)\s+', '', seg).strip()
        if seg and len(seg) > 1:
            result.append(seg)

    return result


def _apply_aliases(food_query: str) -> str:
    """Replace known aliases with canonical search terms."""
    # Try exact full match first
    if food_query in FOOD_ALIASES:
        return FOOD_ALIASES[food_query]
    # Try longest partial match (e.g. "גבינה לבנה" inside "גבינה לבנה 5%")
    best = None
    best_len = 0
    for alias, canonical in FOOD_ALIASES.items():
        if alias in food_query and len(alias) > best_len:
            best = canonical
            best_len = len(alias)
    return best if best else food_query


def _parse_segment(segment: str) -> ParsedFoodItem:
    """Parse one food segment into a ParsedFoodItem."""
    segment = segment.strip()
    original = segment
    quantity = 1.0
    unit = "יחידה"
    grams = None

    # Pattern 1: digits + optional unit + food  e.g. "150 גרם גבינה"
    m = re.match(r'^(\d+(?:[.,]\d+)?)\s*([א-ת"״\']+(?:״[א-ת]+)?)?\s*(.*)', segment)
    if m:
        qty_str, unit_str, rest = m.group(1), (m.group(2) or "").strip(), m.group(3)
        parsed_qty = _parse_quantity(qty_str)
        if parsed_qty:
            quantity = parsed_qty
            if unit_str and unit_str in UNIT_TO_GRAMS:
                unit = unit_str
                unit_g = UNIT_TO_GRAMS[unit_str]
                grams = unit_g * quantity if unit_g else None
                segment = rest.strip()
            elif unit_str:
                segment = (unit_str + " " + rest).strip()
            else:
                segment = rest.strip()

    # Pattern 2: Hebrew number word at start  e.g. "שתי ביצים"
    elif any(segment.startswith(heb) for heb, _ in
             sorted(HEB_NUMBERS.items(), key=lambda x: -len(x[0]))):
        for heb, val in sorted(HEB_NUMBERS.items(), key=lambda x: -len(x[0])):
            if segment.startswith(heb):
                quantity = val
                remainder = segment[len(heb):].strip()
                words = remainder.split()
                if words and words[0] in UNIT_TO_GRAMS:
                    unit = words[0]
                    unit_g = UNIT_TO_GRAMS[unit]
                    grams = unit_g * quantity if unit_g else None
                    segment = " ".join(words[1:])
                else:
                    segment = remainder
                break

    # Pattern 3: unit at start  e.g. "כוס קפה", "כף שמן זית"
    words = segment.split()
    if words and words[0] in UNIT_TO_GRAMS:
        unit = words[0]
        unit_g = UNIT_TO_GRAMS[unit]
        grams = unit_g * quantity if unit_g else None
        segment = " ".join(words[1:])

    # Pattern 4: food then digits then unit at end  e.g. "חזה עוף 150 גרם"
    if grams is None:
        m2 = re.search(r'(\d+(?:[.,]\d+)?)\s*([א-ת"״\']+(?:״[א-ת]+)?)\s*$', segment)
        if m2:
            qty2_str, unit2_str = m2.group(1), m2.group(2)
            if unit2_str in UNIT_TO_GRAMS:
                qty2 = float(qty2_str.replace(",", "."))
                unit_g2 = UNIT_TO_GRAMS[unit2_str]
                if unit_g2:
                    grams = unit_g2 * qty2
                    quantity = qty2
                    unit = unit2_str
                segment = segment[:m2.start()].strip()

    # Clean leading prepositions
    segment = re.sub(r'^(של|מ|את|ה|ו|ל)\s+', '', segment).strip()

    food_query = segment if segment else original

    # Apply alias resolution
    food_query = _apply_aliases(food_query)

    return ParsedFoodItem(
        raw_text=original,
        food_query=food_query,
        quantity=quantity,
        unit=unit,
        grams=grams,
    )


def parse_hebrew_meal(text: str) -> ParseResult:
    """
    Parse free Hebrew meal text into structured food items.

    Example:
        "אכלתי שתי ביצים, גבינה לבנה 150 גרם וכוס קפה לארוחת בוקר"
        → ParseResult with 3 items, meal_type="breakfast"
    """
    # Remove common prefix verbs / phrases
    text = re.sub(
        r'^(אכלתי|שתיתי|אכלנו|שתינו|קניתי|הכנתי|הכנו|צרכתי|בליעתי|'
        r'לקחתי|אוכל|אוכלת|אוכלים|היה לי|הייתה לי|היה|היו|'
        r'נאכל|נשתה|הייתי אוכל|הייתי שותה)\s*',
        '', text.strip(), flags=re.IGNORECASE
    )
    # Remove filler phrases
    text = re.sub(r'\b(לאכול|לשתות|לארוחה)\b', '', text, flags=re.IGNORECASE).strip()

    meal_type = _detect_meal_type(text)
    segments  = _split_to_segments(text)

    if not segments:
        segments = [text]

    items = [_parse_segment(s) for s in segments if s]
    items = [i for i in items if i.food_query and len(i.food_query) > 1]

    has_qty = sum(1 for i in items if i.quantity != 1.0)
    confidence = min(0.5 + 0.15 * len(items) + 0.1 * has_qty, 1.0)

    return ParseResult(items=items, meal_type=meal_type, confidence=confidence)
