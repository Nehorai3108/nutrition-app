"""
barcode_comp.py — Streamlit custom component for barcode scanning.
Must be declared from a real Python module (not a Streamlit page script)
to avoid RuntimeError: module is None.
"""
import os
import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "components", "barcode_scanner"
)

_inner = components.declare_component(
    "barcode_scanner",
    path=_COMPONENT_DIR,
)


def barcode_scanner(key: str = "bc_scanner", height: int = 140) -> str | None:
    """
    Render the barcode scanner component.
    Returns the detected barcode string, or None if nothing scanned yet.
    height: initial iframe height in px (before JS sets it via setFrameHeight).
    """
    return _inner(key=key, height=height)
