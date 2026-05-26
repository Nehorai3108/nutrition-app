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

barcode_scanner = components.declare_component(
    "barcode_scanner",
    path=_COMPONENT_DIR,
)
