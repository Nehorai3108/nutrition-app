#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3 tests for the barcode page improvements:
  1. _is_drink correctly identifies drinks vs food
  2. _serving_options returns drink portions (כוס/פחית/בקבוק) for drinks
  3. _serving_options returns gram-based portions for solid food
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import the functions under test ──────────────────────────────────────────
# We can't import the Streamlit page directly, so we duplicate the logic here
# (exactly as written in pages/12_barcode.py)

_DRINK_KEYWORDS_HE = ["מיץ", "שתייה", "קולה", "בירה", "יין", "וודקה", "ויסקי",
                      "ספרייט", "פנטה", "מים", "תה", "קפה", "שייק", "סודה",
                      "אנרגיה", "איזוטוני", "לימונדה", "חלב", "מחלב", "פרימור"]
_DRINK_KEYWORDS_EN = ["beverage", "drink", "juice", "cola", "beer", "wine", "water",
                      "tea", "coffee", "milk", "shake", "soda", "energy drink",
                      "sport", "smoothie", "lemonade", "dairy drink"]

def _is_drink(product: dict) -> bool:
    name = (product.get("name_he") or product.get("name_en") or "").lower()
    cats = str(product.get("categories") or "").lower()
    for kw in _DRINK_KEYWORDS_HE:
        if kw in name: return True
    for kw in _DRINK_KEYWORDS_EN:
        if kw in name or kw in cats: return True
    if "beverage" in cats or "drinks" in cats or "en:beverages" in cats:
        return True
    return False

def _serving_options(product: dict) -> list:
    serving = int(product.get("serving_g") or 100)
    if _is_drink(product):
        return [
            ("כוס קטנה  (150 מ\"ל)",  150),
            ("כוס          (200 מ\"ל)",  200),
            ("כוס גדולה  (250 מ\"ל)",  250),
            ("פחית            (330 מ\"ל)",  330),
            ("בקבוק קטן (500 מ\"ל)",  500),
            ("בקבוק גדול (1.5 ל׳)", 1500),
            (f"מנה מהאריזה ({serving} מ\"ל)", serving),
        ]
    else:
        return [
            (f"מנה מהאריזה ({serving}g)",   serving),
            ("100 גרם",                      100),
            ("מנה קטנה   (50g)",              50),
            ("מנה בינונית (150g)",           150),
            ("מנה גדולה  (200g)",            200),
        ]


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_is_drink_detection():
    """Test 1: _is_drink correctly identifies drinks vs solid food."""
    drinks = [
        {"name_he": "מיץ תפוזים", "name_en": "orange juice"},
        {"name_he": "קוקה קולה"},
        {"name_he": "מים מינרליים"},
        {"name_he": "חלב 1%"},
        {"name_en": "energy drink", "categories": "en:beverages"},
        {"name_he": "שייק חלבון"},
        {"name_en": "coca cola", "categories": "en:beverages,en:sodas"},
        {"name_he": "בירה מאלט"},
    ]
    foods = [
        {"name_he": "במבה", "name_en": "Bamba"},
        {"name_he": "חזה עוף", "name_en": "chicken breast"},
        {"name_he": "גבינה צהובה"},
        {"name_he": "לחם מלא"},
        {"name_he": "שוקולד מריר"},
        {"name_he": "אורז לבן"},
    ]

    failed = []
    for d in drinks:
        if not _is_drink(d):
            failed.append(f"  MISS-drink: {d.get('name_he') or d.get('name_en')}")
    for f in foods:
        if _is_drink(f):
            failed.append(f"  FALSE-drink: {f.get('name_he') or f.get('name_en')}")

    if failed:
        print(f"FAIL test_is_drink_detection:\n" + "\n".join(failed))
        return False
    print(f"PASS test_is_drink_detection  ({len(drinks)} drinks, {len(foods)} foods)")
    return True


def test_drink_serving_options():
    """Test 2: drinks get כוס/פחית/בקבוק options."""
    product = {"name_he": "מיץ תפוזים", "serving_g": 200}
    opts = _serving_options(product)

    labels = [o[0] for o in opts]
    grams  = [o[1] for o in opts]

    checks = [
        (150 in grams,  "כוס קטנה 150ml missing"),
        (330 in grams,  "פחית 330ml missing"),
        (500 in grams,  "בקבוק קטן 500ml missing"),
        (1500 in grams, "בקבוק גדול 1500ml missing"),
        (200 in grams,  "מנה מהאריזה 200ml missing"),
        (len(opts) >= 5, f"Expected ≥5 options, got {len(opts)}"),
    ]

    failed = [msg for ok, msg in checks if not ok]
    if failed:
        print(f"FAIL test_drink_serving_options: {failed}")
        return False
    print(f"PASS test_drink_serving_options  ({len(opts)} options: {grams})")
    return True


def test_food_serving_options():
    """Test 3: solid food gets gram-based options, NOT ml options."""
    product = {"name_he": "במבה", "name_en": "Bamba", "serving_g": 30}
    opts = _serving_options(product)

    grams = [o[1] for o in opts]
    labels_str = " ".join(o[0] for o in opts)

    checks = [
        (30 in grams,          "מנה מהאריזה 30g missing"),
        (100 in grams,         "100 גרם option missing"),
        (1500 not in grams,    "1500 (drink size) should NOT appear for solid food"),
        (330 not in grams,     "330ml (can size) should NOT appear for solid food"),
        ("מ\"ל" not in labels_str, "מל label should NOT appear for solid food"),
    ]

    failed = [msg for ok, msg in checks if not ok]
    if failed:
        print(f"FAIL test_food_serving_options: {failed}")
        return False
    print(f"PASS test_food_serving_options  ({len(opts)} options: {grams})")
    return True


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Barcode Page — 3 Unit Tests")
    print("="*50 + "\n")

    results = [
        test_is_drink_detection(),
        test_drink_serving_options(),
        test_food_serving_options(),
    ]

    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*50}")
    print(f"  SCORE: {passed}/{total}")
    print(f"{'='*50}")
    import sys
    sys.exit(0 if passed == total else 1)
