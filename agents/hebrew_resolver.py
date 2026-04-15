"""
Hebrew Resolver — translates Hebrew food queries to English for API lookups.

Two-stage resolution:
  1. Manual dictionary of 30 common Israeli foods (fast, exact)
  2. Phonetic transliteration fallback (no external dependencies)
"""

# ── Manual dictionary ──────────────────────────────────────────────────────────

_HEBREW_TO_ENGLISH: dict[str, str] = {
    # Proteins
    "עוף צלוי":        "roasted chicken",
    "חזה עוף":         "chicken breast",
    "שניצל":           "schnitzel chicken",
    "שניצל עוף":       "chicken schnitzel",
    "המבורגר":         "hamburger beef patty",
    "סטייק":           "beef steak",
    "דג סלמון":        "salmon fillet",
    "טונה":            "canned tuna",
    "ביצה קשה":        "hard boiled egg",
    "ביצה מקושקשת":    "scrambled eggs",
    "ביצה עלומה":      "poached egg",

    # Dairy
    "שוקו":            "chocolate milk",
    "חלב":             "whole milk",
    "גבינה צהובה":     "yellow cheese cheddar",
    "גבינה לבנה":      "white cheese",
    "קוטג'":           "cottage cheese",
    "יוגורט":          "plain yogurt",
    "שמנת חמוצה":      "sour cream",
    "גבינה בולגרית":   "bulgarian feta cheese",

    # Grains & Bread
    "פיתה":            "pita bread",
    "לחם":             "white bread",
    "לחם מלא":         "whole wheat bread",
    "אורז לבן":        "cooked white rice",
    "פסטה":            "cooked pasta",
    "קוסקוס":          "couscous",
    "בורקס":           "bourekas pastry",
    "קרואסון":         "croissant",

    # Vegetables & Salads
    "סלט ירקות":       "vegetable salad",
    "חסה":             "lettuce",
    "מלפפון":          "cucumber",
    "עגבניה":          "tomato",
    "גזר":             "carrot",
    "תפוח אדמה":       "potato",
    "בטטה":            "sweet potato",
    "ברוקולי":         "broccoli",
    "כרובית":          "cauliflower",
    "פלפל":            "bell pepper",

    # Legumes & Spreads
    "חומוס":           "hummus",
    "עדשים":           "lentils",
    "שעועית":          "kidney beans",
    "פול":             "fava beans",
    "טחינה":           "tahini",

    # Fruits
    "תפוח":            "apple",
    "בננה":            "banana",
    "תפוז":            "orange",
    "ענבים":           "grapes",
    "אבוקדו":          "avocado",

    # Snacks & Other
    "שוקולד":          "dark chocolate",
    "עוגיות":          "cookies",
    "גרנולה":          "granola",
    "שקדים":           "almonds",
    "אגוזים":          "walnuts",
    "זיתים":           "olives",
    "שמן זית":         "olive oil",
    "מיץ תפוזים":      "orange juice",
    "קפה שחור":        "black coffee",
}


# ── Phonetic transliteration fallback ─────────────────────────────────────────
# Maps each Hebrew letter to its approximate Latin phoneme.

_HCHAR_MAP: dict[str, str] = {
    "א": "",   "ב": "b",  "ג": "g",  "ד": "d",  "ה": "h",
    "ו": "v",  "ז": "z",  "ח": "ch", "ט": "t",  "י": "y",
    "כ": "k",  "ך": "k",  "ל": "l",  "מ": "m",  "ם": "m",
    "נ": "n",  "ן": "n",  "ס": "s",  "ע": "",   "פ": "p",
    "ף": "f",  "צ": "tz", "ץ": "tz", "ק": "k",  "ר": "r",
    "ש": "sh", "ת": "t",
    # Vowel markers (niqqud) — strip silently
    "\u05b0": "", "\u05b1": "e", "\u05b2": "a", "\u05b3": "o",
    "\u05b4": "i", "\u05b5": "e", "\u05b6": "e", "\u05b7": "a",
    "\u05b8": "a", "\u05b9": "o", "\u05ba": "o", "\u05bb": "u",
    "\u05bc": "", "\u05bd": "", "\u05be": "-", "\u05bf": "",
    "\u05c1": "sh", "\u05c2": "s",
}


def _transliterate(text: str) -> str:
    """Convert Hebrew characters to a phonetic Latin approximation."""
    result = []
    for ch in text:
        if ch == " ":
            result.append(" ")
        elif ch in _HCHAR_MAP:
            result.append(_HCHAR_MAP[ch])
        elif ord(ch) < 128:
            result.append(ch)          # keep Latin chars as-is
        # else: unknown non-ASCII, drop
    return "".join(result).strip()


def _is_hebrew(text: str) -> bool:
    """Return True if the string contains any Hebrew character."""
    return any("\u05d0" <= ch <= "\u05ea" for ch in text)


# ── Public API ─────────────────────────────────────────────────────────────────

def resolve_hebrew(query: str) -> str:
    """
    Translate a Hebrew food query to an English search term.

    Resolution order:
      1. Exact match in the manual dictionary (case/whitespace normalised).
      2. Phonetic transliteration of each word.

    Returns the English term if resolved, otherwise returns the original query
    unchanged (so callers can always pass the return value straight to a search).
    """
    if not _is_hebrew(query):
        return query  # nothing to do

    # Normalise whitespace
    normalised = " ".join(query.split())

    # 1. Exact dictionary lookup
    english = _HEBREW_TO_ENGLISH.get(normalised)
    if english:
        return english

    # 2. Try each word individually and stitch together
    words = normalised.split()
    translated_words = [_HEBREW_TO_ENGLISH.get(w, _transliterate(w)) for w in words]
    transliterated = " ".join(translated_words).strip()

    return transliterated if transliterated else query
