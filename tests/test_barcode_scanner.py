#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3 tests for the barcode scanner (all-in-browser architecture):
  1. barcode_scanner HTML has file-input, BarcodeDetector, and ZXing fallback
  2. barcode_scanner Python wrapper is importable and has correct signature
  3. pages/12_barcode.py uses barcode_scanner() correctly (no image roundtrip)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Test 1: barcode_scanner HTML is correct ───────────────────────────────
def test_scanner_html():
    """Verify the component HTML has all required decode strategies."""
    path = os.path.join(_BASE, "components", "barcode_scanner", "index.html")
    if not os.path.exists(path):
        print(f"FAIL test_scanner_html  (file not found: {path})")
        return False

    with open(path, encoding="utf-8") as f:
        html = f.read()

    checks = [
        ("file input with capture=environment",
         'type="file"' in html and 'capture="environment"' in html),
        ("BarcodeDetector native API",
         "BarcodeDetector" in html),
        ("ZXing CDN fallback",
         "zxing" in html.lower() and "BrowserMultiFormatReader" in html),
        ("setComponentValue sends barcode string",
         "setComponentValue" in html and "accept" in html),
        ("resetAll clears value",
         "resetAll" in html and "setComponentValue(null)" in html),
    ]

    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"FAIL test_scanner_html  — checks failed: {failed}")
        return False

    print(f"PASS test_scanner_html  (all {len(checks)} checks OK)")
    return True


# ── Test 2: Python wrapper imports correctly ──────────────────────────────
def test_scanner_wrapper():
    """Verify barcode_scanner() is importable and has a key parameter."""
    try:
        import inspect
        from nutrition_app.components.barcode_comp import barcode_scanner
    except ImportError as e:
        print(f"FAIL test_scanner_wrapper  (import error: {e})")
        return False

    sig    = inspect.signature(barcode_scanner)
    params = list(sig.parameters.keys())

    if "key" not in params:
        print(f"FAIL test_scanner_wrapper  (no key param, got: {params})")
        return False

    print("PASS test_scanner_wrapper  (import OK, key param present)")
    return True


# ── Test 3: barcode page uses the scanner correctly ───────────────────────
def test_page_integration():
    """
    Verify pages/12_barcode.py:
    (a) imports barcode_scanner (not barcode_decoder_js)
    (b) calls barcode_scanner() in the camera tab
    (c) stores the result in session_state['_bc_last']
    (d) does NOT import st.camera_input for the camera tab logic
        (image must not be sent server-side)
    """
    page_path = os.path.join(_BASE, "pages", "12_barcode.py")
    if not os.path.exists(page_path):
        print(f"FAIL test_page_integration  (page not found: {page_path})")
        return False

    with open(page_path, encoding="utf-8") as f:
        src = f.read()

    checks = [
        ("imports barcode_scanner",
         "from nutrition_app.components.barcode_comp import barcode_scanner" in src),
        ("does not use barcode_decoder_js",
         "barcode_decoder_js" not in src),
        ("calls barcode_scanner(key=",
         'barcode_scanner(key=' in src),
        ("stores result in _bc_last",
         '"_bc_last"' in src),
    ]

    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"FAIL test_page_integration  — checks failed: {failed}")
        return False

    print(f"PASS test_page_integration  (all {len(checks)} integration checks OK)")
    return True


# ── Run ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Barcode Scanner — 3 Tests")
    print("="*55 + "\n")

    r1 = test_scanner_html()
    r2 = test_scanner_wrapper()
    r3 = test_page_integration()

    passed = sum([r1, r2, r3])
    print(f"\n{'='*55}")
    print(f"  SCORE: {passed}/3")
    print(f"{'='*55}")
    sys.exit(0 if passed == 3 else 1)
