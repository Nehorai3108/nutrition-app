"""Design tokens — NutriSmart brand theme.

Palette is derived from the NutriSmart logo: the forest→leaf greens
(nutrition / health), the steel→slate blues (the "AI / smart" side and the
transformation arc), and the coral circuit accents (energy). The app ships a
**light base** that matches the logo's white-card look, with an optional
**dark mode**.

Both ``ui/components.py`` and ``app_user.py`` import this module as an object
(``t.PRIMARY``), so values are resolved at call-time. ``set_mode()`` rewrites
the module-level tokens before each render, which is what makes the runtime
light/dark toggle work without touching every component.
"""

# ── Mode-independent tokens ───────────────────────────────────────────────────
# Sizing
RADIUS_SM = "8px"
RADIUS    = "12px"
RADIUS_LG = "16px"
RADIUS_XL = "20px"

HIT_TARGET = "44px"

FONT_SM = "0.82rem"
FONT_MD = "1rem"
FONT_LG = "1.2rem"
FONT_XL = "1.65rem"

# Motion — single easing + duration vocabulary so every animation feels consistent.
EASE       = "cubic-bezier(0.4, 0, 0.2, 1)"
EASE_OUT   = "cubic-bezier(0.16, 1, 0.3, 1)"
DUR_FAST   = "0.18s"
DUR_MED    = "0.35s"
DUR_SLOW   = "0.6s"

# Brand hues shared across both modes (used for gradient text, logo wordmark).
BRAND_GREEN = "#3f9e57"   # forest/leaf green — nutrition
BRAND_BLUE  = "#2d6fb3"   # steel/slate blue — the "smart / AI" side
BRAND_CORAL = "#e8825a"   # circuit coral — energy

# ── Palettes ──────────────────────────────────────────────────────────────────

_LIGHT = {
    # Surfaces — white cards on a soft blue-grey page, like the logo backdrop.
    "BG":        "#eef3f9",
    "SURFACE":   "#ffffff",
    "SURFACE_2": "#f3f7fc",
    "SURFACE_3": "#e7eef6",
    "BORDER":    "#dde6f0",
    "BORDER_2":  "#c6d5e4",
    # Text — navy headline like the logo wordmark.
    "TEXT":       "#15304e",
    "TEXT_MUTED": "#5a7088",
    "TEXT_DIM":   "#92a3b6",
    # Brand
    "PRIMARY":     "#2d6fb3",
    "PRIMARY_HOV": "#3f82c6",
    "PRIMARY_DIM": "#dceaf7",
    "ACCENT":      "#3f9e57",
    "ACCENT_DIM":  "#3f9e5722",
    # Gradients — the logo's signature green→blue transformation arc.
    "GRAD_PRIMARY": "linear-gradient(135deg, #3f9e57 0%, #2d6fb3 100%)",
    "GRAD_ACCENT":  "linear-gradient(135deg, #6cbf4a 0%, #3f9e57 100%)",
    "GRAD_SURFACE": "linear-gradient(160deg, #ffffff 0%, #f3f7fc 100%)",
    "GRAD_CARD":    "linear-gradient(135deg, rgba(45,111,179,0.05) 0%, rgba(63,158,87,0.04) 100%)",
    "GRAD_HEADER":  "linear-gradient(135deg, #ffffff 0%, #e9f1f9 100%)",
    # Status
    "SUCCESS":    "#3f9e57",
    "SUCCESS_BG": "#e6f4ea",
    "WARNING":    "#e0763f",   # coral, echoing the circuit traces
    "WARNING_BG": "#fceee4",
    "DANGER":     "#d65745",
    "DANGER_BG":  "#fce9e6",
    "INFO":       "#2d6fb3",
    "INFO_BG":    "#e4eff9",
    # Macro colors — logo trio (blue / coral / green) + navy for calories.
    "CAL_COLOR":     "#15304e",
    "CAL_BG":        "#eef3f9",
    "CAL_GRAD":      "linear-gradient(135deg, #15304e, #5a7088)",
    "PROTEIN_COLOR": "#2d6fb3",
    "PROTEIN_BG":    "#e4eff9",
    "PROTEIN_GRAD":  "linear-gradient(135deg, #2d6fb3, #4f8ef7)",
    "CARBS_COLOR":   "#e0763f",
    "CARBS_BG":      "#fceee4",
    "CARBS_GRAD":    "linear-gradient(135deg, #e8825a, #e0763f)",
    "FAT_COLOR":     "#3f9e57",
    "FAT_BG":        "#e6f4ea",
    "FAT_GRAD":      "linear-gradient(135deg, #6cbf4a, #3f9e57)",
    # Kashrut
    "KASHRUT_COLORS": {"meat": "#d65745", "dairy": "#2d6fb3", "parve": "#3f9e57"},
    "KASHRUT_BG":     {"meat": "#fce9e6", "dairy": "#e4eff9", "parve": "#e6f4ea"},
    # Shadows — soft, navy-tinted (no harsh black on a light page).
    "SHADOW_SM":   "0 1px 3px rgba(21,48,78,0.07)",
    "SHADOW_MD":   "0 4px 16px rgba(21,48,78,0.10)",
    "SHADOW_LG":   "0 10px 34px rgba(21,48,78,0.14)",
    "SHADOW_PRI":  "0 6px 22px rgba(45,111,179,0.20)",
    "SHADOW_ACC":  "0 6px 22px rgba(63,158,87,0.18)",
    "SHADOW_GLOW": "0 0 24px rgba(63,158,87,0.28)",
}

_DARK = {
    # Surfaces — deep navy-teal rather than neutral grey, to stay on-brand.
    "BG":        "#0c1622",
    "SURFACE":   "#14212f",
    "SURFACE_2": "#1b2c3d",
    "SURFACE_3": "#23384c",
    "BORDER":    "#23384c",
    "BORDER_2":  "#2e455c",
    "TEXT":       "#eaf2fa",
    "TEXT_MUTED": "#93a8bd",
    "TEXT_DIM":   "#5d7489",
    "PRIMARY":     "#5b9bdc",
    "PRIMARY_HOV": "#74aee6",
    "PRIMARY_DIM": "#16314d",
    "ACCENT":      "#56bd6b",
    "ACCENT_DIM":  "#56bd6b22",
    "GRAD_PRIMARY": "linear-gradient(135deg, #56bd6b 0%, #5b9bdc 100%)",
    "GRAD_ACCENT":  "linear-gradient(135deg, #7cd05a 0%, #56bd6b 100%)",
    "GRAD_SURFACE": "linear-gradient(160deg, #14212f 0%, #1b2c3d 100%)",
    "GRAD_CARD":    "linear-gradient(135deg, rgba(91,155,220,0.07) 0%, rgba(86,189,107,0.04) 100%)",
    "GRAD_HEADER":  "linear-gradient(135deg, #14212f 0%, #1b2c3d 100%)",
    "SUCCESS":    "#56bd6b",
    "SUCCESS_BG": "#0e2a18",
    "WARNING":    "#f0935f",
    "WARNING_BG": "#2a1810",
    "DANGER":     "#ef7d6c",
    "DANGER_BG":  "#2a1310",
    "INFO":       "#5b9bdc",
    "INFO_BG":    "#0e2640",
    "CAL_COLOR":     "#eaf2fa",
    "CAL_BG":        "#1b2c3d",
    "CAL_GRAD":      "linear-gradient(135deg, #eaf2fa, #93a8bd)",
    "PROTEIN_COLOR": "#5b9bdc",
    "PROTEIN_BG":    "#0e2640",
    "PROTEIN_GRAD":  "linear-gradient(135deg, #5b9bdc, #74aee6)",
    "CARBS_COLOR":   "#f0935f",
    "CARBS_BG":      "#2a1810",
    "CARBS_GRAD":    "linear-gradient(135deg, #f0935f, #e8825a)",
    "FAT_COLOR":     "#56bd6b",
    "FAT_BG":        "#0e2a18",
    "FAT_GRAD":      "linear-gradient(135deg, #7cd05a, #56bd6b)",
    "KASHRUT_COLORS": {"meat": "#ef7d6c", "dairy": "#5b9bdc", "parve": "#56bd6b"},
    "KASHRUT_BG":     {"meat": "#2a1310", "dairy": "#0e2640", "parve": "#0e2a18"},
    "SHADOW_SM":   "0 1px 4px rgba(0,0,0,0.4)",
    "SHADOW_MD":   "0 4px 16px rgba(0,0,0,0.5)",
    "SHADOW_LG":   "0 8px 32px rgba(0,0,0,0.6)",
    "SHADOW_PRI":  "0 4px 20px rgba(91,155,220,0.25)",
    "SHADOW_ACC":  "0 4px 20px rgba(86,189,107,0.18)",
    "SHADOW_GLOW": "0 0 24px rgba(86,189,107,0.32)",
}

_PALETTES = {"light": _LIGHT, "dark": _DARK}
DEFAULT_MODE = "light"

# Current active mode — read via current_mode(); written via set_mode().
MODE = DEFAULT_MODE


def set_mode(mode: str) -> None:
    """Activate a palette by copying its tokens into module-level globals.

    Safe to call on every render. Unknown modes fall back to the default.
    """
    global MODE
    mode = mode if mode in _PALETTES else DEFAULT_MODE
    MODE = mode
    globals().update(_PALETTES[mode])


def current_mode() -> str:
    """Return the currently active mode ("light" or "dark")."""
    return MODE


# Populate the module-level tokens at import time (light base).
set_mode(DEFAULT_MODE)
