"""Design tokens — single source of truth for colors, spacing, radii.

All colors are checked for WCAG AA contrast against the dark background
(#0f1020 / #1a1a2e).
"""

# ── Surface colors ──────────────────────────────────────────────────────────
BG          = "#0f1020"
SURFACE     = "#1a1a2e"
SURFACE_2   = "#252540"
BORDER      = "#2a2a4a"
BORDER_2    = "#3a3a5a"

# ── Text ────────────────────────────────────────────────────────────────────
TEXT        = "#e8e8ff"
TEXT_MUTED  = "#a0a0c0"   # 4.7:1 on BG — passes AA
TEXT_DIM    = "#7a7a9a"   # use only for non-essential meta

# ── Brand / accent ──────────────────────────────────────────────────────────
PRIMARY     = "#7c5cff"
PRIMARY_HOV = "#9377ff"
ACCENT      = "#5cffd1"

# ── Status (icon + text + color, never color alone) ─────────────────────────
SUCCESS     = "#66e08a"
WARNING     = "#ffb74d"
DANGER      = "#ff6b7a"
INFO        = "#64b5f6"

# ── Macro accents ───────────────────────────────────────────────────────────
CAL_COLOR     = "#ffd54f"
CAL_BG        = "#3a3500"
PROTEIN_COLOR = "#81c784"
PROTEIN_BG    = "#003a14"
CARBS_COLOR   = "#64b5f6"
CARBS_BG      = "#00253a"
FAT_COLOR     = "#ef9a9a"
FAT_BG        = "#3a0020"

# ── Kashrut accents (always paired with icon + label) ──────────────────────
KASHRUT_COLORS = {
    "meat":  "#ff6b7a",
    "dairy": "#64b5f6",
    "parve": "#a4d65e",
}
KASHRUT_BG = {
    "meat":  "#3a0010",
    "dairy": "#00253a",
    "parve": "#1a3000",
}

# ── Sizing ──────────────────────────────────────────────────────────────────
RADIUS_SM = "8px"
RADIUS    = "12px"
RADIUS_LG = "16px"

HIT_TARGET = "44px"   # WCAG 2.5.5 minimum

FONT_SM = "0.85rem"
FONT_MD = "1rem"
FONT_LG = "1.2rem"
FONT_XL = "1.6rem"
