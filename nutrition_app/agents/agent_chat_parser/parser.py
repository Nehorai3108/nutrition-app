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
}

# ── Unit → grams conversion ───────────────────────────────────────────────────
UNIT_TO_GRAMS = {
    "גרם": 1, "גר": 1, "גר׳": 1, "ג׳": 1, "ג": 1,
    "קילוגרם": 1000, "קג": 1000, "ק״ג": 1000,
    "כוס": 240, "כוסות": 240,
    "כף": 15, "כפות": 15,
    "כפית": 5, "כפיות": 5,
    "מיליליטר": 1, "מ״ל": 1, "מל": 1,
    "ליטר": 1000,
    "יחידה": None, "יחידות": None,
    "חתיכה": None, "חתיכות": None,
    "פרוסה": 30, "פרוסות": 30,
    "קציצה": 80, "קציצות": 80,
    "עוגייה": 15, "עוגיות": 15,
}

# ── Meal type keywords ────────────────────────────────────────────────────────
MEAL_KEYWORDS = {
    "breakfast":       ["בוקר", "ארוחת בוקר", "בראנץ"],
    "morning_snack":   ["חטיף בוקר", "חטיף של בוקר"],
    "lunch":           ["צהריים", "ארוחת צהריים", "אמצע היום"],
    "afternoon_snack": ["חטיף", "חטיף אחה״צ", "אחה״צ", "אחרי הצהריים"],
    "dinner":          ["ערב", "ארוחת ערב", "לילה"],
    "evening_snack":   ["חטיף ערב", "חטיף לילה"],
}

# ── Compound food names that should NOT be split on "עם" ──────────────────────
COMPOUND_FOODS = [
    "קפה עם חלב", "לחם עם חמאה", "פיתה עם חומוס", "עוף עם אורז",
    "דגן עם חלב", "גרנולה עם יוגורט", "טוסט עם ביצה",
]


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
    for meal_type, keywords in MEAL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_l:
                return meal_type
    # Guess from time of day context
    if any(w in text_l for w in ["בוקר", "קפה", "שמנת", "דגני"]):
        return "breakfast"
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
    # Remove common prefix verbs
    text = re.sub(
        r'^(אכלתי|שתיתי|אכלנו|קניתי|הכנתי|צרכתי|בליעתי|הייתה לי|היה לי|היה)\s*',
        '', text.strip(), flags=re.IGNORECASE
    )

    meal_type = _detect_meal_type(text)
    segments  = _split_to_segments(text)

    if not segments:
        segments = [text]

    items = [_parse_segment(s) for s in segments if s]
    items = [i for i in items if i.food_query and len(i.food_query) > 1]

    has_qty = sum(1 for i in items if i.quantity != 1.0)
    confidence = min(0.5 + 0.15 * len(items) + 0.1 * has_qty, 1.0)

    return ParseResult(items=items, meal_type=meal_type, confidence=confidence)
