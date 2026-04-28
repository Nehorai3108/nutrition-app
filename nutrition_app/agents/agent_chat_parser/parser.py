"""
Hebrew meal text parser — no API key required.
Extracts food items + quantities from free Hebrew text.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# ── Hebrew number words → float ───────────────────────────────────────────────
HEB_NUMBERS = {
    "חצי": 0.5, "חצי-": 0.5, "חצי ": 0.5,
    "רבע": 0.25,
    "שלושה רבעים": 0.75,
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
    # Weight
    "גרם": 1, "גר": 1, "גר׳": 1, "ג׳": 1, "ג": 1,
    "קילוגרם": 1000, "קג": 1000, "ק״ג": 1000,
    # Volume (approximate)
    "כוס": 240, "כוסות": 240,
    "כף": 15, "כפות": 15,
    "כפית": 5, "כפיות": 5,
    "מיליליטר": 1, "מ״ל": 1, "מל": 1,
    "ליטר": 1000,
    # Count (default serving size used)
    "יחידה": None, "יחידות": None,
    "חתיכה": None, "חתיכות": None,
    "פרוסה": 30, "פרוסות": 30,
    "קציצה": 80, "קציצות": 80,
    "ביצה": None, "ביצים": None,
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
    confidence: float  # 0–1


def _detect_meal_type(text: str) -> str:
    text_l = text.lower()
    for meal_type, keywords in MEAL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_l:
                return meal_type
    return "lunch"


def _parse_quantity(token: str) -> Optional[float]:
    token = token.strip()
    # Try float/int
    try:
        return float(token.replace(",", "."))
    except ValueError:
        pass
    # Try Hebrew word
    for heb, val in sorted(HEB_NUMBERS.items(), key=lambda x: -len(x[0])):
        if token == heb or token.startswith(heb):
            return val
    return None


def _split_to_segments(text: str) -> List[str]:
    """Split text on conjunctions and punctuation into food segments."""
    # Normalize
    text = text.strip()
    # Remove meal-time context phrases (they're handled separately)
    for meal_type, keywords in MEAL_KEYWORDS.items():
        for kw in keywords:
            text = re.sub(r'\b' + re.escape(kw) + r'\b', '', text, flags=re.IGNORECASE)
    # Split on: ו, וגם, עם, ,, +
    separators = r'(?:,|\bוגם\b|\bועם\b|\bוכן\b|\bבנוסף\b|\bפלוס\b|[,،]|\bו\b(?=\s*[א-ת]))'
    segments = re.split(separators, text)
    return [s.strip() for s in segments if s.strip() and len(s.strip()) > 1]


def _parse_segment(segment: str) -> ParsedFoodItem:
    """Parse one segment like 'שתי ביצים', '150 גרם גבינה לבנה', 'כוס קפה'."""
    segment = segment.strip()
    original = segment

    quantity = 1.0
    unit = "יחידה"
    grams = None

    # Pattern 1: number (digits) + optional unit + food
    # e.g. "150 גרם גבינה", "2 ביצים", "3 כפות שמן"
    m = re.match(r'^(\d+(?:[.,]\d+)?)\s*([א-ת"״\']+)?\s*(.*)', segment)
    if m:
        qty_str, unit_str, rest = m.group(1), m.group(2) or "", m.group(3)
        parsed_qty = _parse_quantity(qty_str)
        if parsed_qty:
            quantity = parsed_qty
            if unit_str and unit_str in UNIT_TO_GRAMS:
                unit = unit_str
                grams = UNIT_TO_GRAMS[unit_str]
                if grams:
                    grams = grams * quantity
                segment = rest.strip()
            elif unit_str:
                segment = (unit_str + " " + rest).strip()
            else:
                segment = rest.strip()

    # Pattern 2: Hebrew number word at start
    # e.g. "שתי ביצים", "שלוש כפות סוכר"
    else:
        for heb, val in sorted(HEB_NUMBERS.items(), key=lambda x: -len(x[0])):
            if segment.startswith(heb):
                quantity = val
                remainder = segment[len(heb):].strip()
                # Check if next word is a unit
                words = remainder.split()
                if words and words[0] in UNIT_TO_GRAMS:
                    unit = words[0]
                    grams = UNIT_TO_GRAMS[unit]
                    if grams:
                        grams = grams * quantity
                    segment = " ".join(words[1:])
                else:
                    segment = remainder
                break

    # Pattern 3: unit at start (e.g. "כוס חלב", "כף שמן זית")
    words = segment.split()
    if words and words[0] in UNIT_TO_GRAMS:
        unit = words[0]
        unit_g = UNIT_TO_GRAMS[unit]
        if unit_g:
            grams = unit_g * quantity
        segment = " ".join(words[1:])

    # Clean up common prefix words
    segment = re.sub(r'^(של|מ|את|ה|ו)\s*', '', segment).strip()

    # If no grams computed yet, use default serving (None = use food's default)
    if grams is None and unit not in ("יחידה", "חתיכה", "יחידות", "חתיכות"):
        grams = None

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
    # Remove common prefix phrases
    text = re.sub(
        r'^(אכלתי|שתיתי|אכלנו|קניתי|הכנתי|צרכתי|בליעתי|הייתה לי|היה לי)\s*',
        '', text.strip(), flags=re.IGNORECASE
    )

    meal_type = _detect_meal_type(text)
    segments = _split_to_segments(text)

    if not segments:
        segments = [text]

    items = [_parse_segment(s) for s in segments if s]
    items = [i for i in items if i.food_query]

    # Confidence: higher if we have multiple items and quantities
    has_qty = sum(1 for i in items if i.quantity != 1.0)
    confidence = min(0.5 + 0.15 * len(items) + 0.1 * has_qty, 1.0)

    return ParseResult(items=items, meal_type=meal_type, confidence=confidence)
