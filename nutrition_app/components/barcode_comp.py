"""
barcode_comp.py — Streamlit custom components for barcode scanning.
Must be declared from a real Python module (not a Streamlit page script)
to avoid RuntimeError: module is None.
"""
import os
import streamlit.components.v1 as components

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Component 1: live camera scanner (ZXing in iframe) ───────────────────────
_scanner_inner = components.declare_component(
    "barcode_scanner",
    path=os.path.join(_BASE, "components", "barcode_scanner"),
)

def barcode_scanner(key: str = "bc_scanner", height: int = 140) -> str | None:
    """Live camera barcode scanner. Returns barcode string or None."""
    return _scanner_inner(key=key, height=height)


# ── Component 2: decode barcode from captured image bytes (ZXing in iframe) ──
_decoder_inner = components.declare_component(
    "barcode_decoder",
    path=os.path.join(_BASE, "components", "barcode_decoder"),
)

def barcode_decoder_js(img_bytes: bytes, key: str = "bc_decoder") -> str | None:
    """
    Decode a barcode from raw image bytes using ZXing in the browser.
    Pass bytes from st.camera_input().getvalue().
    Returns the detected barcode string, or None.
    """
    import base64, hashlib
    b64  = base64.b64encode(img_bytes).decode("ascii")
    # Hash to detect new images (avoid re-decoding same frame)
    h    = hashlib.md5(img_bytes).hexdigest()
    return _decoder_inner(img_b64=b64, mime="image/jpeg", img_hash=h, key=key, height=50)
