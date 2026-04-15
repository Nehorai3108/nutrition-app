"""Reusable Streamlit UI components for the nutrition app.

All helpers are RTL-aware, dark-themed, and meet WCAG AA contrast.
Buttons rendered through ``icon_button`` always pair an SVG icon with
visible Hebrew text — no icon-only controls.
"""

from contextlib import contextmanager
from typing import Optional

import streamlit as st

from . import theme as t
from .icons import icon as _icon, has_icon
from .labels import KASHRUT_LABELS, KASHRUT_ICON, MEAL_LABELS, MEAL_ICON

# ── Global CSS injection ────────────────────────────────────────────────────

_CSS_FLAG = "_nut_ui_css_injected"


def inject_global_css() -> None:
    """Inject the design-system CSS once per session.

    Safe to call from every page top-level. Subsequent calls are no-ops
    within the same Streamlit run.
    """
    # Force-inject every run because Streamlit re-renders the page from
    # scratch on each interaction. The flag merely prevents duplicates
    # within a single render pass.
    if st.session_state.get(_CSS_FLAG):
        return
    st.session_state[_CSS_FLAG] = True

    css = f"""
    <style>
        /* ─── RTL ─────────────────────────────────────────────────────── */
        .main .block-container {{ direction: rtl; }}
        section[data-testid="stSidebar"] > div {{ direction: rtl; }}
        h1, h2, h3, h4, h5 {{ text-align: right; color: {t.TEXT}; }}
        input[type="number"], input[type="text"], input[type="password"], textarea {{
            text-align: right;
        }}

        /* ─── Larger hit targets (WCAG 2.5.5) ─────────────────────────── */
        .stButton > button,
        .stDownloadButton > button,
        button[data-testid="baseButton-primary"],
        button[data-testid="baseButton-secondary"] {{
            min-height: {t.HIT_TARGET};
            border-radius: {t.RADIUS};
            font-weight: 600;
            transition: transform 0.08s ease, box-shadow 0.15s ease, background 0.15s ease;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(124, 92, 255, 0.25);
        }}
        .stButton > button:active {{
            transform: translateY(0);
        }}

        /* Visible focus ring everywhere */
        button:focus-visible,
        input:focus-visible,
        textarea:focus-visible,
        select:focus-visible,
        a:focus-visible,
        [tabindex]:focus-visible {{
            outline: 3px solid {t.PRIMARY} !important;
            outline-offset: 2px !important;
            border-radius: {t.RADIUS_SM};
        }}

        /* ─── Cards ───────────────────────────────────────────────────── */
        .nut-card {{
            background: {t.SURFACE};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_LG};
            padding: 18px 20px;
            margin: 10px 0;
        }}
        .nut-card-clickable {{ cursor: pointer; transition: all 0.18s ease; }}
        .nut-card-clickable:hover {{
            background: {t.SURFACE_2};
            border-color: {t.PRIMARY};
            transform: translateY(-2px);
        }}

        /* ─── Page header ─────────────────────────────────────────────── */
        .nut-pageheader {{
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px 18px;
            background: linear-gradient(135deg, {t.SURFACE} 0%, {t.SURFACE_2} 100%);
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_LG};
            margin: 6px 0 18px 0;
        }}
        .nut-pageheader .nut-ph-icon {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 52px;
            height: 52px;
            border-radius: {t.RADIUS};
            background: {t.PRIMARY};
            color: #ffffff;
            flex-shrink: 0;
        }}
        .nut-pageheader .nut-ph-title {{
            font-size: 1.55rem;
            font-weight: 700;
            color: {t.TEXT};
            line-height: 1.15;
        }}
        .nut-pageheader .nut-ph-subtitle {{
            font-size: 0.92rem;
            color: {t.TEXT_MUTED};
            margin-top: 2px;
        }}

        /* ─── Section header ──────────────────────────────────────────── */
        .nut-section {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.1rem;
            font-weight: 700;
            color: {t.TEXT};
            margin: 18px 0 10px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid {t.BORDER};
        }}
        .nut-section svg {{ color: {t.PRIMARY}; }}

        /* ─── Chips & badges ──────────────────────────────────────────── */
        .nut-chip {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            background: {t.SURFACE_2};
            color: {t.TEXT};
            border: 1px solid {t.BORDER};
            margin: 2px;
        }}
        .nut-chip-meat   {{ background:{t.KASHRUT_BG['meat']};   color:{t.KASHRUT_COLORS['meat']};   border-color:{t.KASHRUT_COLORS['meat']}; }}
        .nut-chip-dairy  {{ background:{t.KASHRUT_BG['dairy']};  color:{t.KASHRUT_COLORS['dairy']};  border-color:{t.KASHRUT_COLORS['dairy']}; }}
        .nut-chip-parve  {{ background:{t.KASHRUT_BG['parve']};  color:{t.KASHRUT_COLORS['parve']};  border-color:{t.KASHRUT_COLORS['parve']}; }}

        /* ─── Status text ─────────────────────────────────────────────── */
        .nut-status-ok   {{ color: {t.SUCCESS}; font-weight: 700; }}
        .nut-status-warn {{ color: {t.WARNING}; font-weight: 700; }}
        .nut-status-fail {{ color: {t.DANGER};  font-weight: 700; }}

        /* ─── Macro tile ──────────────────────────────────────────────── */
        .nut-macro-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin: 10px 0;
        }}
        .nut-macro-tile {{
            background: {t.SURFACE_2};
            border-radius: {t.RADIUS};
            padding: 10px 8px;
            text-align: center;
            border: 1px solid {t.BORDER};
        }}
        .nut-macro-tile .nut-macro-val {{ font-size: 1.05rem; font-weight: 700; }}
        .nut-macro-tile .nut-macro-lbl {{ font-size: 0.72rem; color: {t.TEXT_MUTED}; margin-top: 2px; }}
        .nut-mt-cal     .nut-macro-val {{ color: {t.CAL_COLOR}; }}
        .nut-mt-protein .nut-macro-val {{ color: {t.PROTEIN_COLOR}; }}
        .nut-mt-carbs   .nut-macro-val {{ color: {t.CARBS_COLOR}; }}
        .nut-mt-fat     .nut-macro-val {{ color: {t.FAT_COLOR}; }}

        /* ─── Welcome cards ───────────────────────────────────────────── */
        .nut-welcome-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin: 14px 0;
        }}
        .nut-welcome-card {{
            background: {t.SURFACE};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_LG};
            padding: 28px 18px;
            text-align: center;
            text-decoration: none;
            color: {t.TEXT};
            display: block;
            transition: all 0.2s ease;
        }}
        .nut-welcome-card:hover {{
            background: {t.SURFACE_2};
            border-color: {t.PRIMARY};
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(124, 92, 255, 0.18);
        }}
        .nut-welcome-icon {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 64px;
            height: 64px;
            border-radius: 16px;
            background: {t.PRIMARY};
            color: #fff;
            margin-bottom: 12px;
        }}
        .nut-welcome-title {{ font-weight: 700; font-size: 1.1rem; color: {t.TEXT}; }}
        .nut-welcome-sub {{ font-size: 0.85rem; color: {t.TEXT_MUTED}; margin-top: 6px; line-height: 1.5; }}

        /* ─── Login form ──────────────────────────────────────────────── */
        .nut-login-card {{
            max-width: 420px;
            margin: 60px auto;
            padding: 32px 28px;
            background: {t.SURFACE};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_LG};
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }}

        /* ─── Recipe images ───────────────────────────────────────────── */
        .nut-recipe-image {{
            width: 100%;
            height: 280px;
            object-fit: cover;
            border-radius: {t.RADIUS};
            margin-bottom: 12px;
            display: block;
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def reset_css_flag() -> None:
    """Reset the once-per-render flag — Streamlit reruns clear it automatically.

    Provided for tests / advanced callers; normal pages do not need this.
    """
    st.session_state.pop(_CSS_FLAG, None)


# ── Page header ────────────────────────────────────────────────────────────

def page_header(title: str, icon_name: str = "plate",
                subtitle: Optional[str] = None) -> None:
    """Render a consistent page header with an icon, title, and optional subtitle."""
    inject_global_css()
    icon_html = _icon(icon_name, size=28, decorative=True)
    sub_html = (
        f'<div class="nut-ph-subtitle">{subtitle}</div>' if subtitle else ""
    )
    st.markdown(
        f'<div class="nut-pageheader">'
        f'<div class="nut-ph-icon">{icon_html}</div>'
        f'<div><div class="nut-ph-title">{title}</div>{sub_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Section header ─────────────────────────────────────────────────────────

def section_header(title: str, icon_name: str = "menu") -> None:
    """Render a smaller in-page section header with an icon."""
    inject_global_css()
    icon_html = _icon(icon_name, size=20, decorative=True)
    st.markdown(
        f'<div class="nut-section">{icon_html}<span>{title}</span></div>',
        unsafe_allow_html=True,
    )


# ── Icon button ────────────────────────────────────────────────────────────

def icon_button(label: str, icon_name: str = "confirm", *,
                key: Optional[str] = None,
                type: str = "secondary",
                use_container_width: bool = True,
                disabled: bool = False,
                help: Optional[str] = None) -> bool:
    """A standard ``st.button`` whose label is prefixed with a small symbol.

    Streamlit ``st.button`` does not render raw HTML, so we pair the icon as
    a Unicode/text marker via the ``icon`` parameter when supported, falling
    back to a text glyph in the label. The visible Hebrew text is always
    present — no icon-only buttons.
    """
    inject_global_css()
    # Streamlit's `icon` kwarg only accepts a single emoji or Material Symbol
    # name, which our compact glyph set doesn't always satisfy. We render the
    # glyph as a text prefix instead — that keeps "icon + Hebrew text" pairing
    # without depending on an opinionated icon validator.
    prefix = _unicode_glyph(icon_name)
    return st.button(
        f"{prefix} {label}",
        key=key,
        type=type,
        use_container_width=use_container_width,
        disabled=disabled,
        help=help,
    )


# Mapping of icon name → unicode glyph fallback (used in st.button labels).
# These are picked for clarity and good RTL behavior. SVG icons remain the
# primary visual language in cards/headers; buttons use these for compactness.
_GLYPHS = {
    "home": "🏠",
    "back": "←",
    "menu": "☰",
    "search": "🔎",
    "add": "＋",
    "delete": "🗑",
    "edit": "✎",
    "confirm": "✓",
    "close": "✕",
    "clear": "🧹",
    "save": "💾",
    "play": "▶",
    "refresh": "↻",
    "info": "ⓘ",
    "warning": "⚠",
    "calendar": "📅",
    "settings": "⚙",
    "login": "🔓",
    "logout": "⎋",
    "lock": "🔒",
    "recipe": "🍳",
    "plate": "🍽",
    "utensils": "🍴",
    "breakfast": "🌅",
    "lunch": "🍽",
    "dinner": "🌙",
    "snack": "🍎",
    "flame": "🔥",
    "protein": "💪",
    "carbs": "🌾",
    "fat": "🫒",
    "training": "🏋",
    "dumbbell": "🏋",
    "running": "🏃",
    "inventory": "📦",
    "package": "📦",
    "scan": "🔍",
    "receipt": "🧾",
    "agent": "🤖",
    "user": "👤",
    "star": "⭐",
    "target": "🎯",
    "trophy": "🏆",
}


def _unicode_glyph(name: str) -> str:
    return _GLYPHS.get(name, "•")


# ── Kashrut & meal badges ───────────────────────────────────────────────────

def kashrut_badge_html(kashrut: str) -> str:
    """HTML chip for a kashrut category — icon + Hebrew text + color."""
    k = (kashrut or "parve").lower()
    label = KASHRUT_LABELS.get(k, k)
    icon_name = KASHRUT_ICON.get(k, "plate")
    css = f"nut-chip nut-chip-{k}"
    return (
        f'<span class="{css}">{_icon(icon_name, size=14, decorative=True)}'
        f'<span>{label}</span></span>'
    )


def meal_badge_html(meal_key: str) -> str:
    """HTML chip for a meal type — icon + Hebrew text."""
    k = (meal_key or "").lower()
    label = MEAL_LABELS.get(k, meal_key)
    icon_name = MEAL_ICON.get(k, "plate")
    return (
        f'<span class="nut-chip">{_icon(icon_name, size=14, decorative=True)}'
        f'<span>{label}</span></span>'
    )


# ── Macro grid ──────────────────────────────────────────────────────────────

def macro_grid_html(cal: int, protein: int, carbs: int, fat: int) -> str:
    """Render a 4-column macro tile grid as HTML."""
    return (
        f'<div class="nut-macro-grid">'
        f'<div class="nut-macro-tile nut-mt-cal">'
        f'<div class="nut-macro-val">{cal}</div>'
        f'<div class="nut-macro-lbl">קק״ל</div></div>'
        f'<div class="nut-macro-tile nut-mt-protein">'
        f'<div class="nut-macro-val">{protein}ג</div>'
        f'<div class="nut-macro-lbl">חלבון</div></div>'
        f'<div class="nut-macro-tile nut-mt-carbs">'
        f'<div class="nut-macro-val">{carbs}ג</div>'
        f'<div class="nut-macro-lbl">פחמימות</div></div>'
        f'<div class="nut-macro-tile nut-mt-fat">'
        f'<div class="nut-macro-val">{fat}ג</div>'
        f'<div class="nut-macro-lbl">שומן</div></div>'
        f'</div>'
    )


# ── Recipe card ─────────────────────────────────────────────────────────────

def recipe_card_html(recipe: dict, image_uri: str = "",
                     match_pct: Optional[int] = None,
                     show_rank: bool = False) -> str:
    """Render a recipe card as HTML — used by main, recipes list, daily menu.

    The card always:
      - has an ``alt`` attribute on the image,
      - shows kashrut as icon + label + color (not color alone),
      - links to ``/recipe_detail?id=<recipe_id>`` for navigation.
    """
    name_he   = recipe.get("name_he", "")
    name_en   = recipe.get("name_en", "")
    portions  = max(recipe.get("portions", 1), 1)
    prep      = recipe.get("prep_time_minutes", 0)
    kashrut   = (recipe.get("kashrut") or "parve").lower()
    nut       = recipe.get("total_nutrition", {}) or {}
    cal       = round(nut.get("calories", 0) / portions)
    protein   = round(nut.get("protein", 0) / portions)
    carbs     = round(nut.get("carbs", 0) / portions)
    fat       = round(nut.get("fat", 0) / portions)
    recipe_id = recipe.get("recipe_id", "")
    href      = f"/recipe_detail?id={recipe_id}"
    alt       = name_he or "מתכון"

    image_block = (
        f'<img src="{image_uri}" alt="{alt}" class="nut-recipe-image" />'
        if image_uri else ""
    )

    rank_html = ""
    if show_rank:
        star = _icon("star", size=12, decorative=True)
        rank_html = (
            f'<span class="nut-chip" '
            f'style="background:{t.PRIMARY};color:#fff;border-color:{t.PRIMARY}">'
            f'{star}<span>מומלץ</span></span>'
        )

    match_html = ""
    if match_pct is not None:
        match_color = (
            t.SUCCESS if match_pct >= 85 else (t.WARNING if match_pct >= 70 else t.DANGER)
        )
        match_html = (
            f'<span style="color:{match_color};font-weight:600">'
            f'{match_pct}% התאמה</span>'
        )

    return (
        f'<a href="{href}" target="_self" '
        f'style="text-decoration:none;color:inherit">'
        f'<div class="nut-card nut-card-clickable">'
        f'{image_block}'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;gap:8px;flex-wrap:wrap">'
        f'<div style="font-size:1.15rem;font-weight:700;color:{t.TEXT}">'
        f'{name_he}</div>'
        f'<div style="display:flex;gap:4px;align-items:center">'
        f'{kashrut_badge_html(kashrut)}{rank_html}</div>'
        f'</div>'
        f'<div style="font-size:0.82rem;color:{t.TEXT_MUTED};margin:4px 0 8px 0">'
        f'{name_en} · ⏱ {prep} דק׳ · 🍽 {portions} מנות'
        f'{" · " + match_html if match_html else ""}</div>'
        f'{macro_grid_html(cal, protein, carbs, fat)}'
        f'</div></a>'
    )


# ── Welcome card ────────────────────────────────────────────────────────────

def welcome_card_html(href: str, icon_name: str, title: str, subtitle: str) -> str:
    return (
        f'<a class="nut-welcome-card" href="{href}" target="_self">'
        f'<div class="nut-welcome-icon">{_icon(icon_name, size=32, decorative=True)}</div>'
        f'<div class="nut-welcome-title">{title}</div>'
        f'<div class="nut-welcome-sub">{subtitle}</div>'
        f'</a>'
    )


# ── Top navigation menu ─────────────────────────────────────────────────────

# Maps display label → page file path. Order matters.
_NAV_ITEMS = [
    ("ראשי",        "app_user.py",                      "home"),
    ("מתכונים",     "pages/2_recipes.py",              "recipe"),
    ("תפריט יומי",  "pages/6_daily_menu.py",           "plate"),
    ("מלאי",        "pages/4_inventory.py",            "inventory"),
    ("סריקת קבלה",  "pages/2_receipt_scanner.py",      "scan"),
    ("אימונים",     "pages/7_weekly_workout_plan.py",  "training"),
]

# Admin nav item is now in pages_admin/1_agents_dashboard.py (separate app)
_ADMIN_NAV_ITEM = ("סוכנים", "pages_admin/1_agents_dashboard.py", "agent")


def nav_menu(active: Optional[str] = None) -> None:
    """Render the top navigation bar.

    Uses ``streamlit-option-menu`` when available; falls back to a simple
    ``st.columns`` of page links otherwise. The "סוכנים" entry is hidden
    unless the current session is authenticated as admin.
    """
    inject_global_css()

    # Build the live item list (filter admin entry by auth state)
    try:
        from .auth import is_admin  # local import to avoid cycles
    except Exception:
        def is_admin() -> bool:  # type: ignore
            return False

    items = list(_NAV_ITEMS)
    if is_admin():
        items.append(_ADMIN_NAV_ITEM)

    # Hide the built-in sidebar entry for the agents dashboard when not admin
    if not is_admin():
        st.markdown(
            '<style>'
            'section[data-testid="stSidebar"] a[href*="1_agents_dashboard"] '
            '{display:none !important;}'
            '</style>',
            unsafe_allow_html=True,
        )

    # Try the rich menu first
    try:
        from streamlit_option_menu import option_menu  # type: ignore

        labels = [lbl for lbl, _, _ in items]
        # streamlit-option-menu uses Bootstrap icon names
        bs_icons = {
            "home": "house",
            "recipe": "journal-text",
            "plate": "egg-fried",
            "inventory": "box-seam",
            "scan": "upc-scan",
            "training": "person-walking",
            "agent": "robot",
        }
        icons = [bs_icons.get(name, "circle") for _, _, name in items]

        default_idx = 0
        if active:
            for i, (lbl, _, _) in enumerate(items):
                if lbl == active:
                    default_idx = i
                    break

        chosen = option_menu(
            menu_title=None,
            options=labels,
            icons=icons,
            orientation="horizontal",
            default_index=default_idx,
            styles={
                "container": {
                    "padding": "6px",
                    "background-color": t.SURFACE,
                    "border": f"1px solid {t.BORDER}",
                    "border-radius": t.RADIUS_LG,
                    "margin-bottom": "14px",
                    "direction": "rtl",
                },
                "icon": {"color": t.PRIMARY, "font-size": "18px"},
                "nav-link": {
                    "font-size": "0.95rem",
                    "color": t.TEXT,
                    "text-align": "center",
                    "padding": "10px 14px",
                    "margin": "0 4px",
                    "border-radius": t.RADIUS,
                    "min-height": t.HIT_TARGET,
                },
                "nav-link-selected": {
                    "background-color": t.PRIMARY,
                    "color": "#fff",
                    "font-weight": "700",
                },
            },
        )
        if chosen != active and chosen is not None:
            for lbl, page, _ in items:
                if lbl == chosen:
                    try:
                        st.switch_page(page)
                    except Exception:
                        pass
                    break
        return
    except ImportError:
        pass

    # Fallback: simple page links in a row
    cols = st.columns(len(items))
    for col, (lbl, page, icon_name) in zip(cols, items):
        with col:
            st.page_link(page, label=f"{_unicode_glyph(icon_name)} {lbl}",
                         use_container_width=True)
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)


# ── Admin sidebar menu ───────────────────────────────────────────────────────

# Admin context pages
_ADMIN_PAGES = [
    ("סוכנים",        "pages_admin/1_agents_dashboard.py", "agent"),
    ("מנהל תמונות",   "pages_admin/2_photo_manager.py",   "images"),
    ("ביקורת לוג",    "pages_admin/3_audit_logs.py",      "file-text"),
    ("הגדרות",       "pages_admin/4_settings.py",        "gear"),
]

# System context pages (recipes, workouts, etc.)
_SYSTEM_PAGES = [
    ("מתכונים",      "pages/2_recipes.py",               "recipe"),
    ("אימונים",      "pages/7_weekly_workout_plan.py",   "training"),
]


def admin_sidebar_menu(context: str = "admin", active: Optional[str] = None) -> None:
    """Render the admin dashboard sidebar menu.

    Args:
        context: "admin" (default) shows admin pages, "system" shows system config pages
        active: Optional label to highlight as active
    """
    inject_global_css()

    # Select pages based on context
    pages = _ADMIN_PAGES if context == "admin" else _SYSTEM_PAGES
    page_title = "ניהול" if context == "admin" else "הגדרות מערכת"

    # Try the rich menu first
    try:
        from streamlit_option_menu import option_menu  # type: ignore

        labels = [lbl for lbl, _, _ in pages]
        bs_icons = {
            "agent": "robot",
            "images": "image",
            "file-text": "file-text",
            "gear": "gear",
            "recipe": "journal-text",
            "training": "person-walking",
        }
        icons = [bs_icons.get(name, "circle") for _, _, name in pages]

        default_idx = 0
        if active:
            for i, (lbl, _, _) in enumerate(pages):
                if lbl == active:
                    default_idx = i
                    break

        chosen = option_menu(
            menu_title=page_title,
            options=labels,
            icons=icons,
            orientation="vertical",
            default_index=default_idx,
            styles={
                "container": {
                    "padding": "10px",
                    "background-color": t.SURFACE,
                    "border": f"1px solid {t.BORDER}",
                    "border-radius": t.RADIUS_LG,
                    "margin-bottom": "14px",
                    "direction": "rtl",
                },
                "icon": {"color": t.PRIMARY, "font-size": "18px"},
                "nav-link": {
                    "font-size": "0.95rem",
                    "color": t.TEXT,
                    "text-align": "right",
                    "padding": "12px 14px",
                    "margin": "4px 0",
                    "border-radius": t.RADIUS,
                    "min-height": t.HIT_TARGET,
                },
                "nav-link-selected": {
                    "background-color": t.PRIMARY,
                    "color": "#fff",
                    "font-weight": "700",
                },
            },
        )
        if chosen is not None:
            for lbl, page, _ in pages:
                if lbl == chosen:
                    try:
                        st.switch_page(page)
                    except Exception:
                        pass
                    break
        return
    except ImportError:
        pass

    # Fallback: simple vertical menu
    st.markdown(f"### {page_title}")
    for lbl, page, icon_name in pages:
        st.page_link(page, label=f"{_unicode_glyph(icon_name)} {lbl}",
                     use_container_width=True)
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)


# ── Section context manager (sugar) ─────────────────────────────────────────

@contextmanager
def section(title: str, icon_name: str = "menu"):
    """``with section('כותרת', 'icon'):`` block — renders a header above content."""
    section_header(title, icon_name)
    yield
