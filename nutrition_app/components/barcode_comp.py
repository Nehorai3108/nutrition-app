"""
barcode_comp.py — Streamlit custom components for barcode scanning.
Must be declared from a real Python module (not a Streamlit page script)
to avoid RuntimeError: module is None.
"""
import os, shutil, tempfile
import streamlit.components.v1 as components

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Cache-bust: copy component to a version-stamped temp dir so the
#    browser always loads the latest HTML when the file changes.
def _versioned_component_path(src_dir: str) -> str:
    html_path = os.path.join(src_dir, "index.html")
    try:
        ver = int(os.path.getmtime(html_path))
    except OSError:
        ver = 0
    dst = os.path.join(tempfile.gettempdir(), f"bc_scanner_v{ver}")
    if not os.path.isdir(dst):
        shutil.copytree(src_dir, dst)
    return dst

_scanner_src = os.path.join(_BASE, "components", "barcode_scanner")
_scanner_inner = components.declare_component(
    "barcode_scanner",
    path=_versioned_component_path(_scanner_src),
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
