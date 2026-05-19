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
    """Inject the design-system CSS on every render.

    Called from every page top-level. Streamlit re-renders from scratch
    on each interaction so CSS must be re-injected every run.
    """

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ─── Global & RTL ────────────────────────────────────────────── */
        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}

        /* ── RTL for all text-bearing Streamlit containers ────────────── */
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] div,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] span {{
            direction: rtl !important;
            unicode-bidi: embed !important;
        }}
        /* Preserve flex layout direction (don't flip row ordering) */
        [data-testid="stMarkdownContainer"] div[style*="display:flex"],
        [data-testid="stMarkdownContainer"] div[style*="display: flex"] {{
            direction: rtl !important;
        }}
        /* Expander summary labels */
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] details > summary,
        [data-testid="stExpanderToggleIcon"] + p {{
            direction: rtl !important;
            text-align: right !important;
        }}
        /* Tab labels */
        [data-baseweb="tab"] [data-testid="stMarkdownContainer"] p,
        [data-baseweb="tab"] span,
        button[role="tab"] {{
            direction: rtl !important;
            unicode-bidi: embed !important;
        }}
        /* Form labels (number input, selectbox, slider, text input, radio) */
        .stNumberInput label,
        .stSelectbox label,
        .stTextInput label,
        .stSlider label,
        .stTextArea label,
        .stRadio label,
        .stCheckbox label,
        .stRadio > div > label,
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p {{
            direction: rtl !important;
            text-align: right !important;
        }}
        /* Hide "Press Enter to submit form" hint in all text inputs */
        [data-testid="InputInstructions"],
        .stTextInput small,
        .stTextArea small {{
            display: none !important;
        }}
        /* Radio option text */
        .stRadio [data-testid="stMarkdownContainer"] p {{
            direction: rtl !important;
        }}
        /* Selectbox options and current value */
        [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
        [data-baseweb="select"] span {{
            direction: rtl !important;
        }}
        /* Alert / info / warning / error boxes */
        [data-testid="stAlert"] p,
        [data-testid="stAlert"] div {{
            direction: rtl !important;
            text-align: right !important;
        }}
        /* st.caption, st.write, st.text */
        [data-testid="stText"],
        [data-testid="stCaptionContainer"] p {{
            direction: rtl !important;
            text-align: right !important;
        }}
        /* ─── Hide Streamlit chrome ───────────────────────────────────── */
        header[data-testid="stHeader"] {{ display: none !important; }}
        footer {{ display: none !important; }}
        #MainMenu {{ display: none !important; }}
        [data-testid="stToolbar"] {{ display: none !important; }}
        [data-testid="stDecoration"] {{ display: none !important; }}
        /* Hide collapsed sidebar toggle arrow (black strip on left) */
        [data-testid="collapsedControl"] {{ display: none !important; }}
        section[data-testid="stSidebar"][aria-expanded="false"] {{ display: none !important; }}

        .main .block-container {{
            direction: rtl;
            padding-top: 0.75rem;
            padding-bottom: 90px;
            max-width: 480px;
            margin: 0 auto;
        }}
        section[data-testid="stSidebar"] > div {{
            direction: rtl;
            background: {t.SURFACE} !important;
            border-right: 1px solid {t.BORDER};
        }}
        section[data-testid="stSidebar"] {{
            min-width: 220px !important;
            max-width: 260px !important;
        }}
        section[data-testid="stSidebar"] .stButton > button {{
            min-height: 36px !important;
            font-size: 0.82rem !important;
            padding: 4px 10px !important;
        }}
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] h4 {{
            font-size: 0.9rem !important;
            margin: 4px 0 !important;
        }}
        section[data-testid="stSidebar"] hr {{
            margin: 6px 0 !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stMetric"] {{
            padding: 4px 0 !important;
        }}
        h1, h2, h3, h4, h5 {{ text-align: right; color: {t.TEXT}; font-family: 'Inter', sans-serif !important; }}
        input[type="number"], input[type="text"], input[type="password"], textarea {{
            text-align: right;
        }}

        /* ─── Buttons ─────────────────────────────────────────────────── */
        .stButton > button,
        .stDownloadButton > button {{
            min-height: {t.HIT_TARGET};
            border-radius: {t.RADIUS};
            font-weight: 600;
            font-size: 0.92rem;
            letter-spacing: 0.01em;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid transparent;
        }}
        button[data-testid="baseButton-primary"] {{
            background: {t.GRAD_PRIMARY} !important;
            box-shadow: {t.SHADOW_PRI};
        }}
        button[data-testid="baseButton-primary"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(124,92,255,0.4) !important;
        }}
        button[data-testid="baseButton-secondary"] {{
            background: {t.SURFACE_2} !important;
            border-color: {t.BORDER_2} !important;
        }}
        button[data-testid="baseButton-secondary"]:hover {{
            border-color: {t.PRIMARY} !important;
            background: {t.SURFACE_3} !important;
            transform: translateY(-1px);
        }}
        .stButton > button:active {{ transform: translateY(0) scale(0.98); }}

        /* ─── Secondary buttons — compact, minimal ───────────────────── */
        button[data-testid="baseButton-secondary"] {{
            background: transparent !important;
            border: 1px solid {t.BORDER} !important;
            color: {t.TEXT_MUTED} !important;
            box-shadow: none !important;
            min-height: 36px !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
        }}
        button[data-testid="baseButton-secondary"]:hover {{
            border-color: {t.PRIMARY} !important;
            color: {t.PRIMARY} !important;
            background: transparent !important;
            transform: none !important;
        }}

        button:focus-visible, input:focus-visible,
        textarea:focus-visible, select:focus-visible,
        a:focus-visible, [tabindex]:focus-visible {{
            outline: 2px solid {t.ACCENT} !important;
            outline-offset: 3px !important;
            border-radius: {t.RADIUS_SM};
        }}

        /* ─── Metrics ─────────────────────────────────────────────────── */
        [data-testid="metric-container"] {{
            background: {t.SURFACE_2};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_LG};
            padding: 16px 18px;
            transition: all 0.2s ease;
        }}
        [data-testid="metric-container"]:hover {{
            border-color: {t.PRIMARY};
            box-shadow: {t.SHADOW_PRI};
            transform: translateY(-1px);
        }}

        /* ─── Expanders ───────────────────────────────────────────────── */
        [data-testid="stExpander"] {{
            background: {t.SURFACE} !important;
            border: 1px solid {t.BORDER} !important;
            border-radius: {t.RADIUS_LG} !important;
            overflow: hidden;
        }}
        [data-testid="stExpander"]:hover {{
            border-color: {t.BORDER_2} !important;
        }}

        /* ─── Cards ───────────────────────────────────────────────────── */
        .nut-card {{
            background: {t.SURFACE};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_LG};
            padding: 20px 22px;
            margin: 10px 0;
            backdrop-filter: blur(8px);
            position: relative;
            overflow: hidden;
        }}
        .nut-card::before {{
            content: '';
            position: absolute;
            inset: 0;
            background: {t.GRAD_CARD};
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
        }}
        .nut-card-clickable {{ cursor: pointer; transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1); }}
        .nut-card-clickable:hover {{
            border-color: {t.PRIMARY};
            transform: translateY(-3px);
            box-shadow: {t.SHADOW_PRI};
        }}
        .nut-card-clickable:hover::before {{ opacity: 1; }}

        /* ─── Page header ─────────────────────────────────────────────── */
        .nut-pageheader {{
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 18px 22px;
            background: {t.GRAD_HEADER};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_XL};
            margin: 4px 0 20px 0;
            position: relative;
            overflow: hidden;
        }}
        .nut-pageheader::after {{
            content: '';
            position: absolute;
            top: -40px; left: -40px;
            width: 120px; height: 120px;
            background: radial-gradient(circle, rgba(124,92,255,0.15) 0%, transparent 70%);
            pointer-events: none;
        }}
        .nut-pageheader .nut-ph-icon {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 56px; height: 56px;
            border-radius: {t.RADIUS_LG};
            background: {t.GRAD_PRIMARY};
            color: #ffffff;
            flex-shrink: 0;
            box-shadow: {t.SHADOW_PRI};
        }}
        .nut-pageheader .nut-ph-title {{
            font-size: 1.65rem;
            font-weight: 800;
            color: {t.TEXT};
            line-height: 1.15;
            letter-spacing: -0.02em;
        }}
        .nut-pageheader .nut-ph-subtitle {{
            font-size: 0.9rem;
            color: {t.TEXT_MUTED};
            margin-top: 3px;
        }}

        /* ─── Section header ──────────────────────────────────────────── */
        .nut-section {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.05rem;
            font-weight: 700;
            color: {t.TEXT};
            margin: 22px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid {t.BORDER};
            position: relative;
        }}
        .nut-section::after {{
            content: '';
            position: absolute;
            bottom: -1px; right: 0;
            width: 48px; height: 2px;
            background: {t.GRAD_PRIMARY};
            border-radius: 2px;
        }}

        /* ─── Chips & badges ──────────────────────────────────────────── */
        .nut-chip {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 11px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            background: {t.SURFACE_3};
            color: {t.TEXT_MUTED};
            border: 1px solid {t.BORDER_2};
            margin: 2px;
            letter-spacing: 0.02em;
        }}
        .nut-chip-meat  {{ background:{t.KASHRUT_BG['meat']};  color:{t.KASHRUT_COLORS['meat']};  border-color:{t.KASHRUT_COLORS['meat']}33; }}
        .nut-chip-dairy {{ background:{t.KASHRUT_BG['dairy']}; color:{t.KASHRUT_COLORS['dairy']}; border-color:{t.KASHRUT_COLORS['dairy']}33; }}
        .nut-chip-parve {{ background:{t.KASHRUT_BG['parve']}; color:{t.KASHRUT_COLORS['parve']}; border-color:{t.KASHRUT_COLORS['parve']}33; }}

        /* ─── Status text ─────────────────────────────────────────────── */
        .nut-status-ok   {{ color: {t.SUCCESS}; font-weight: 700; }}
        .nut-status-warn {{ color: {t.WARNING}; font-weight: 700; }}
        .nut-status-fail {{ color: {t.DANGER};  font-weight: 700; }}

        /* ─── Macro tiles ─────────────────────────────────────────────── */
        .nut-macro-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin: 12px 0;
        }}
        .nut-macro-tile {{
            background: {t.SURFACE_2};
            border-radius: {t.RADIUS};
            padding: 12px 8px;
            text-align: center;
            border: 1px solid {t.BORDER};
            position: relative;
            overflow: hidden;
            transition: transform 0.15s ease;
        }}
        .nut-macro-tile:hover {{ transform: translateY(-2px); }}
        .nut-macro-tile::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            border-radius: {t.RADIUS} {t.RADIUS} 0 0;
        }}
        .nut-mt-cal::before     {{ background: {t.CAL_GRAD}; }}
        .nut-mt-protein::before {{ background: {t.PROTEIN_GRAD}; }}
        .nut-mt-carbs::before   {{ background: {t.CARBS_GRAD}; }}
        .nut-mt-fat::before     {{ background: {t.FAT_GRAD}; }}
        .nut-macro-tile .nut-macro-val {{ font-size: 1.1rem; font-weight: 700; }}
        .nut-macro-tile .nut-macro-lbl {{ font-size: 0.7rem; color: {t.TEXT_MUTED}; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.05em; }}
        .nut-mt-cal     .nut-macro-val {{ color: {t.CAL_COLOR}; }}
        .nut-mt-protein .nut-macro-val {{ color: {t.PROTEIN_COLOR}; }}
        .nut-mt-carbs   .nut-macro-val {{ color: {t.CARBS_COLOR}; }}
        .nut-mt-fat     .nut-macro-val {{ color: {t.FAT_COLOR}; }}

        /* ─── Welcome cards ───────────────────────────────────────────── */
        .nut-welcome-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 14px;
            margin: 16px 0;
        }}
        .nut-welcome-card {{
            background: {t.SURFACE};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_XL};
            padding: 28px 18px 24px;
            text-align: center;
            text-decoration: none;
            color: {t.TEXT};
            display: block;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}
        .nut-welcome-card::before {{
            content: '';
            position: absolute;
            inset: 0;
            background: {t.GRAD_CARD};
            opacity: 0;
            transition: opacity 0.25s ease;
        }}
        .nut-welcome-card:hover {{
            border-color: {t.PRIMARY};
            transform: translateY(-4px);
            box-shadow: {t.SHADOW_PRI};
        }}
        .nut-welcome-card:hover::before {{ opacity: 1; }}
        .nut-welcome-icon {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 64px; height: 64px;
            border-radius: {t.RADIUS_LG};
            background: {t.GRAD_PRIMARY};
            color: #fff;
            margin-bottom: 14px;
            box-shadow: {t.SHADOW_PRI};
            position: relative;
        }}
        .nut-welcome-title {{ font-weight: 700; font-size: 1.05rem; color: {t.TEXT}; letter-spacing: -0.01em; }}
        .nut-welcome-sub {{ font-size: 0.82rem; color: {t.TEXT_MUTED}; margin-top: 6px; line-height: 1.5; }}

        /* ─── Login form ──────────────────────────────────────────────── */
        .nut-login-card {{
            max-width: 420px;
            margin: 60px auto;
            padding: 36px 32px;
            background: {t.SURFACE};
            border: 1px solid {t.BORDER};
            border-radius: {t.RADIUS_XL};
            box-shadow: {t.SHADOW_LG}, 0 0 0 1px rgba(124,92,255,0.08);
        }}

        /* ─── Recipe images ───────────────────────────────────────────── */
        .nut-recipe-image {{
            width: 100%;
            height: 220px;
            object-fit: cover;
            border-radius: {t.RADIUS};
            margin-bottom: 14px;
            display: block;
        }}

        /* ─── Divider ─────────────────────────────────────────────────── */
        hr {{
            border: none !important;
            border-top: 1px solid {t.BORDER} !important;
            margin: 18px 0 !important;
        }}

        /* ─── Dataframes ──────────────────────────────────────────────── */
        [data-testid="stDataFrame"] {{
            border-radius: {t.RADIUS_LG} !important;
            overflow: hidden;
            border: 1px solid {t.BORDER} !important;
        }}

        /* ─── Alerts / info boxes ─────────────────────────────────────── */
        [data-testid="stAlert"] {{
            border-radius: {t.RADIUS_LG} !important;
            border-left-width: 4px !important;
        }}

        /* ─── Hide auto-generated Streamlit nav ───────────────────────── */
        [data-testid="stSidebarNav"] {{ display: none !important; }}

        /* ─── Custom Hebrew nav links ─────────────────────────────────── */
        [data-testid="stPageLink"] a {{
            border-radius: {t.RADIUS} !important;
            padding: 8px 12px !important;
            font-weight: 500 !important;
            color: {t.TEXT_MUTED} !important;
            transition: all 0.18s ease !important;
            display: block;
        }}
        [data-testid="stPageLink"] a:hover {{
            background: {t.SURFACE_2} !important;
            color: {t.TEXT} !important;
        }}
        [data-testid="stPageLink-active"] a {{
            background: {t.PRIMARY_DIM} !important;
            color: {t.PRIMARY} !important;
            font-weight: 600 !important;
        }}

        /* ─── Mobile responsive ───────────────────────────────────────── */
        .nut-rings-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 14px;
            margin: 0 0 16px 0;
        }}
        .nut-macro-card {{
            background: {t.SURFACE};
            border: 1px solid {t.BORDER};
            border-radius: 20px;
            padding: 20px 24px;
            margin-bottom: 16px;
        }}

        @media (max-width: 700px) {{
            .nut-rings-grid {{ grid-template-columns: 1fr !important; }}
            .main .block-container {{
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-top: 0.75rem !important;
            }}
            .stButton > button {{
                min-height: 52px !important;
                font-size: 1rem !important;
            }}
            /* Recipe cards — compact on mobile */
            .nut-recipe-image {{
                height: 140px !important;
            }}
            .nut-card {{ margin: 6px 0 !important; }}
            .nut-card-body {{ padding: 10px 12px !important; }}
            .nut-card .nut-macro-grid {{
                gap: 5px !important;
                margin: 8px 0 !important;
            }}
            .nut-macro-tile {{
                padding: 8px 4px !important;
            }}
            .nut-macro-tile .nut-macro-val {{ font-size: 0.9rem !important; }}
            .nut-macro-tile .nut-macro-lbl {{ font-size: 0.6rem !important; }}
        }}

        /* ─── Bottom nav bar ──────────────────────────────────────────── */
        .nut-bottom-nav {{
            position: fixed;
            bottom: 0; left: 0; right: 0;
            z-index: 9999;
            background: {t.SURFACE};
            border-top: 1px solid {t.BORDER};
            display: flex;
            justify-content: space-around;
            align-items: center;
            padding: 8px 0 env(safe-area-inset-bottom, 12px) 0;
            backdrop-filter: blur(20px);
        }}
        .nut-nav-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 3px;
            padding: 6px 12px;
            border-radius: 12px;
            text-decoration: none;
            color: {t.TEXT_DIM};
            font-size: 0.65rem;
            font-weight: 500;
            transition: all 0.15s ease;
            cursor: pointer;
            min-width: 52px;
        }}
        .nut-nav-item:hover {{ color: {t.TEXT}; }}
        .nut-nav-item.active {{ color: {t.PRIMARY}; }}
        .nut-nav-item .nav-icon {{ font-size: 1.4rem; line-height: 1; }}

        /* ─── Premium ring card ───────────────────────────────────────── */
        .nut-ring-card {{
            background: {t.SURFACE};
            border: 1px solid {t.BORDER_2};
            border-radius: 24px;
            padding: 20px 16px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow: hidden;
        }}
        .nut-ring-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            border-radius: 24px 24px 0 0;
        }}
        .nut-ring-cal::before   {{ background: {t.GRAD_ACCENT}; }}
        .nut-ring-sport::before {{ background: linear-gradient(90deg, {t.WARNING}, #f97316); }}
        .nut-ring-water::before {{ background: linear-gradient(90deg, {t.INFO}, {t.ACCENT}); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # ── PWA: manifest + service-worker registration ───────────────────────────
    st.markdown(
        '<link rel="manifest" href="/app/static/manifest.json">'
        '<meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        '<meta name="apple-mobile-web-app-title" content="BiteFit">'
        '<meta name="theme-color" content="#0d111c">'
        '<script>'
        'if("serviceWorker" in navigator){'
        '  navigator.serviceWorker.register("/app/static/sw.js")'
        '    .catch(function(){});'
        '}'
        '</script>',
        unsafe_allow_html=True,
    )


def bottom_nav(active: str = "home") -> None:
    """Fixed bottom nav — SVG icons, client-side React-Router navigation.

    Uses history.pushState + popstate to trigger Streamlit's internal
    page router instead of a full browser reload.  This keeps the
    WebSocket session alive and preserves session_state, so the user
    is never sent back to the login screen on navigation.
    """
    SVG = {
        "home":    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "food":    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><path d="M18 8h1a4 4 0 010 8h-1"/><path d="M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>',
        "chat":    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
        "workout": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><path d="M6 4v6m0 4v6M18 4v6m0 4v6M2 9h4m12 0h4M2 15h4m12 0h4"/></svg>',
        "history": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
        "profile": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "barcode": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><path d="M3 5v2M3 19v-2M3 10v4M7 5v14M11 5v14M15 5v2M15 19v-2M15 10v4M19 5v14M21 5h-2M21 19h-2M21 10h-2"/></svg>',
    }
    items = [
        ("home",    "/",                  "בית"),
        ("food",    "/daily_menu",        "תזונה"),
        ("chat",    "/chat_log",          "צאט"),
        ("barcode", "/barcode",           "ברקוד"),
        ("workout", "/workout_tracker",   "אימון"),
        ("profile", "/profile",           "פרופיל"),
    ]
    html = (
        '<style>'
        '.gn{position:fixed;bottom:0;left:0;right:0;z-index:9999;'
        'background:#0d0f14;border-top:1px solid #1e2433;'
        'display:flex;justify-content:space-around;align-items:center;'
        'padding:6px 0 max(env(safe-area-inset-bottom),10px)}'
        '.gn a{display:flex;flex-direction:column;align-items:center;gap:4px;'
        'text-decoration:none;color:#3a4254;min-width:52px;padding:6px 4px;'
        'font-size:0.6rem;font-weight:500;transition:color .15s}'
        '.gn a svg{stroke:#3a4254;transition:stroke .15s}'
        '.gn a:hover,.gn a:hover svg{color:#8892a4;stroke:#8892a4}'
        '.gn a.on,.gn a.on svg{color:#4f8ef7 !important;stroke:#4f8ef7 !important}'
        '</style>'
        # JavaScript: intercept clicks, use pushState+popstate so React Router
        # navigates internally (preserves WebSocket session & session_state).
        '<script>'
        '(function(){'
        'function stNav(href){'
        '  window.history.pushState({},"",href);'
        '  window.dispatchEvent(new PopStateEvent("popstate",{state:{}}));'
        '}'
        'document.addEventListener("click",function(e){'
        '  var a=e.target.closest(".gn a");'
        '  if(!a)return;'
        '  e.preventDefault();'
        '  stNav(a.getAttribute("href"));'
        '});'
        '})()'
        '</script>'
        '<nav class="gn">'
    )
    for key, href, label in items:
        cls = "on" if key == active else ""
        html += f'<a href="{href}" class="{cls}">{SVG[key]}<span>{label}</span></a>'
    html += '</nav>'
    st.markdown(html, unsafe_allow_html=True)


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
    """Render a 4-column macro tile grid as HTML — Cal AI style."""
    return (
        f'<div class="nut-macro-grid">'
        f'<div class="nut-macro-tile nut-mt-cal">'
        f'<div class="nut-macro-val">{cal}</div>'
        f'<div class="nut-macro-lbl">קק״ל</div></div>'
        f'<div class="nut-macro-tile nut-mt-protein">'
        f'<div class="nut-macro-val">{protein}g</div>'
        f'<div class="nut-macro-lbl">חלבון</div></div>'
        f'<div class="nut-macro-tile nut-mt-carbs">'
        f'<div class="nut-macro-val">{carbs}g</div>'
        f'<div class="nut-macro-lbl">פחמימות</div></div>'
        f'<div class="nut-macro-tile nut-mt-fat">'
        f'<div class="nut-macro-val">{fat}g</div>'
        f'<div class="nut-macro-lbl">שומן</div></div>'
        f'</div>'
    )


def calorie_ring_html(consumed: int, target: int,
                      protein: int = 0, carbs: int = 0, fat: int = 0) -> str:
    """Cal AI style circular calorie ring with macro breakdown."""
    pct = min(consumed / max(target, 1), 1.0)
    remaining = max(target - consumed, 0)
    r, cx, cy = 54, 70, 70
    circumference = 2 * 3.14159 * r
    filled = circumference * pct
    gap = circumference - filled
    color = t.ACCENT if pct < 0.85 else (t.WARNING if pct < 1.0 else t.DANGER)

    return f"""
    <div style="display:flex;align-items:center;gap:24px;padding:16px 0">
      <div style="position:relative;width:140px;height:140px;flex-shrink:0">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle cx="{cx}" cy="{cy}" r="{r}"
            fill="none" stroke="{t.SURFACE_3}" stroke-width="12"/>
          <circle cx="{cx}" cy="{cy}" r="{r}"
            fill="none" stroke="{color}" stroke-width="12"
            stroke-dasharray="{filled:.1f} {gap:.1f}"
            stroke-dashoffset="{circumference * 0.25:.1f}"
            stroke-linecap="round"/>
        </svg>
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;text-align:center">
          <div style="font-size:1.5rem;font-weight:800;color:{t.TEXT};line-height:1">{consumed}</div>
          <div style="font-size:0.7rem;color:{t.TEXT_MUTED};margin-top:2px">קק״ל</div>
          <div style="font-size:0.65rem;color:{t.ACCENT};margin-top:4px;font-weight:600">
            {remaining} נותרו
          </div>
        </div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:0.8rem;color:{t.TEXT_MUTED}">יעד</span>
          <span style="font-size:0.9rem;font-weight:700;color:{t.TEXT}">{target} קק״ל</span>
        </div>
        <div style="height:1px;background:{t.BORDER}"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
          <div style="text-align:center">
            <div style="font-size:1rem;font-weight:700;color:{t.PROTEIN_COLOR}">{protein}g</div>
            <div style="font-size:0.68rem;color:{t.TEXT_MUTED};margin-top:2px">חלבון</div>
            <div style="height:3px;background:{t.PROTEIN_GRAD};border-radius:2px;margin-top:4px"></div>
          </div>
          <div style="text-align:center">
            <div style="font-size:1rem;font-weight:700;color:{t.CARBS_COLOR}">{carbs}g</div>
            <div style="font-size:0.68rem;color:{t.TEXT_MUTED};margin-top:2px">פחמימות</div>
            <div style="height:3px;background:{t.CARBS_GRAD};border-radius:2px;margin-top:4px"></div>
          </div>
          <div style="text-align:center">
            <div style="font-size:1rem;font-weight:700;color:{t.FAT_COLOR}">{fat}g</div>
            <div style="font-size:0.68rem;color:{t.TEXT_MUTED};margin-top:2px">שומן</div>
            <div style="height:3px;background:{t.FAT_GRAD};border-radius:2px;margin-top:4px"></div>
          </div>
        </div>
      </div>
    </div>
    """


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

    image_wrapper = (
        f'<div style="position:relative">{image_block}</div>' if image_block else ""
    )

    return (
        f'<a href="{href}" target="_self" style="text-decoration:none;color:inherit">'
        f'<div class="nut-card nut-card-clickable" style="padding:0;overflow:hidden">'
        f'{image_wrapper}'
        f'<div class="nut-card-body" style="padding:16px 18px">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;margin-bottom:6px">'
        f'<div style="font-size:1rem;font-weight:700;color:{t.TEXT};line-height:1.3">{name_he}</div>'
        f'<div style="display:flex;gap:4px;align-items:center;flex-shrink:0">{kashrut_badge_html(kashrut)}{rank_html}</div>'
        f'</div>'
        f'<div style="font-size:0.8rem;color:{t.TEXT_MUTED};margin-bottom:12px;display:flex;gap:10px;flex-wrap:wrap">'
        f'<span>⏱ {prep} דק׳</span>'
        f'{match_html}'
        f'</div>'
        f'{macro_grid_html(cal, protein, carbs, fat)}'
        f'</div></div></a>'
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
                    "padding": "6px 8px",
                    "background-color": t.SURFACE,
                    "border": f"1px solid {t.BORDER}",
                    "border-radius": t.RADIUS_XL,
                    "margin-bottom": "16px",
                    "direction": "rtl",
                    "box-shadow": t.SHADOW_SM,
                },
                "icon": {"color": t.ACCENT, "font-size": "17px"},
                "nav-link": {
                    "font-size": "0.88rem",
                    "font-weight": "500",
                    "color": t.TEXT_MUTED,
                    "text-align": "center",
                    "padding": "9px 12px",
                    "margin": "0 2px",
                    "border-radius": t.RADIUS,
                    "min-height": t.HIT_TARGET,
                    "transition": "all 0.2s ease",
                },
                "nav-link-selected": {
                    "background": f"linear-gradient(135deg, {t.PRIMARY} 0%, #b06aff 100%)",
                    "color": "#fff",
                    "font-weight": "700",
                    "box-shadow": t.SHADOW_PRI,
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

    # Fallback: simple page links in a row (skip pages not registered in this app)
    cols = st.columns(len(items))
    for col, (lbl, page, icon_name) in zip(cols, items):
        with col:
            try:
                st.page_link(page, label=f"{_unicode_glyph(icon_name)} {lbl}",
                             use_container_width=True)
            except Exception:
                pass
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)


# ── Section context manager (sugar) ─────────────────────────────────────────

@contextmanager
def section(title: str, icon_name: str = "menu"):
    """``with section('כותרת', 'icon'):`` block — renders a header above content."""
    section_header(title, icon_name)
    yield
