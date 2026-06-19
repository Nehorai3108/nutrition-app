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

    # Activate the user's chosen palette before building the CSS. Light is the
    # brand default; the dark toggle stores "dark" in session_state.
    t.set_mode("dark" if st.session_state.get("theme_mode") == "dark" else "light")

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700;800&display=swap');

        /* ─── Global & RTL ────────────────────────────────────────────── */
        html, body, [class*="css"] {{
            font-family: 'Rubik', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}
        /* Paint surfaces from theme tokens so the light/dark toggle repaints
           the whole app (config.toml's base is fixed at server start). */
        [data-testid="stAppViewContainer"], .stApp, body {{
            background: {t.BG} !important;
            color: {t.TEXT};
        }}
        [data-testid="stMarkdownContainer"] {{ color: {t.TEXT}; }}

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
        /* st.metric delta label */
        [data-testid="stMetricDelta"] {{
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

        /* Center the mobile-first layout as a phone-width column on desktop.
           Streamlit renamed this container across versions, so target every
           known selector with !important — `layout="wide"` otherwise lets the
           content sprawl full-width and the components look stretched. */
        .main .block-container,
        .block-container,
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        [data-testid="stAppViewBlockContainer"] {{
            direction: rtl;
            padding-top: 0.75rem !important;
            padding-bottom: 90px !important;
            max-width: 480px !important;
            margin: 0 auto !important;
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
        h1, h2, h3, h4, h5 {{ text-align: right; color: {t.TEXT}; font-family: 'Rubik', sans-serif !important; }}
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
            position: relative;
            overflow: hidden;
        }}
        /* Shine sweep on hover — transform-only, GPU-composited */
        button[data-testid="baseButton-primary"]::after {{
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 40%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent);
            transform: translateX(-150%) skewX(-20deg);
            transition: transform {t.DUR_SLOW} {t.EASE};
            pointer-events: none;
        }}
        button[data-testid="baseButton-primary"]:hover::after {{
            transform: translateX(350%) skewX(-20deg);
        }}
        button[data-testid="baseButton-primary"]:hover {{
            transform: translateY(-2px);
            box-shadow: {t.SHADOW_PRI} !important;
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

        /* ═══ Motion system ════════════════════════════════════════════
           Only `transform` and `opacity` are animated (GPU-composited),
           so animations never trigger layout/paint and stay at 60fps. */
        html {{ scroll-behavior: smooth; }}
        @keyframes nutFadeUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes nutPop {{
            0%   {{ opacity: 0; transform: scale(0.85); }}
            70%  {{ transform: scale(1.04); }}
            100% {{ opacity: 1; transform: scale(1); }}
        }}
        @keyframes nutGrowRTL {{
            from {{ transform: scaleX(0); }}
            to   {{ transform: scaleX(1); }}
        }}
        @keyframes nutRingDraw {{
            from {{ stroke-dasharray: 0 999; }}
        }}
        @keyframes nutShimmer {{
            100% {{ transform: translateX(-200%); }}
        }}
        @keyframes nutGlowFade {{
            0%, 100% {{ opacity: 0.25; }}
            50%      {{ opacity: 1; }}
        }}
        @keyframes nutBlobDrift {{
            from {{ transform: translate(0, 0) scale(1); }}
            to   {{ transform: translate(14px, 10px) scale(1.25); }}
        }}

        /* ─── Entrance animations ─────────────────────────────────────── */
        .nut-pageheader {{ animation: nutFadeUp 0.4s {t.EASE_OUT} both; }}
        .nut-card,
        .nut-macro-card,
        .nut-ring-card {{ animation: nutFadeUp {t.DUR_MED} {t.EASE_OUT} both; }}
        [data-testid="stMetric"] {{ animation: nutFadeUp 0.3s {t.EASE_OUT} both; }}
        [data-testid="stAlert"] {{ animation: nutFadeUp 0.3s {t.EASE_OUT} both; }}
        [data-testid="stChatMessage"] {{ animation: nutFadeUp {t.DUR_MED} {t.EASE_OUT} both; }}

        /* Staggered card entrances — capped to the first few children so
           long lists don't feel sluggish */
        .nut-welcome-grid .nut-welcome-card {{ animation: nutFadeUp 0.4s {t.EASE_OUT} both; }}
        .nut-welcome-grid .nut-welcome-card:nth-child(2) {{ animation-delay: 0.06s; }}
        .nut-welcome-grid .nut-welcome-card:nth-child(3) {{ animation-delay: 0.12s; }}
        .nut-welcome-grid .nut-welcome-card:nth-child(4) {{ animation-delay: 0.18s; }}
        .nut-welcome-grid .nut-welcome-card:nth-child(5) {{ animation-delay: 0.24s; }}
        .nut-welcome-grid .nut-welcome-card:nth-child(6) {{ animation-delay: 0.30s; }}
        .nut-rings-grid .nut-ring-card:nth-child(2) {{ animation-delay: 0.08s; }}
        .nut-rings-grid .nut-ring-card:nth-child(3) {{ animation-delay: 0.16s; }}

        /* Macro tiles pop in with a tiny cascade */
        .nut-macro-grid .nut-macro-tile {{ animation: nutPop 0.3s {t.EASE_OUT} both; }}
        .nut-macro-grid .nut-macro-tile:nth-child(2) {{ animation-delay: 0.04s; }}
        .nut-macro-grid .nut-macro-tile:nth-child(3) {{ animation-delay: 0.08s; }}
        .nut-macro-grid .nut-macro-tile:nth-child(4) {{ animation-delay: 0.12s; }}

        /* Section header underline draws in from the right (RTL) */
        .nut-section::after {{
            transform-origin: right;
            animation: nutGrowRTL 0.5s {t.EASE_OUT} both;
        }}

        /* Page header decorative blob drifts slowly */
        .nut-pageheader::after {{
            animation: nutBlobDrift 7s ease-in-out infinite alternate;
        }}

        /* ─── Calorie ring draw-in ─────────────────────────────────────── */
        .nut-ring-progress {{
            animation: nutRingDraw 0.9s {t.EASE_OUT} both;
        }}
        .nut-ring-center-val {{ animation: nutPop 0.5s {t.EASE_OUT} 0.35s both; }}

        /* ─── "Eat now" hero glow ──────────────────────────────────────── */
        .nut-now-eating {{ position: relative; }}
        .nut-now-eating::after {{
            content: '';
            position: absolute;
            inset: -2px;
            border-radius: 16px;
            box-shadow: {t.SHADOW_GLOW};
            opacity: 0.25;
            animation: nutGlowFade 3s ease-in-out infinite;
            pointer-events: none;
        }}

        /* ─── Skeleton shimmer (loading placeholders) ──────────────────── */
        .nut-skeleton {{
            position: relative;
            overflow: hidden;
            background: {t.SURFACE_2};
            border-radius: {t.RADIUS};
            min-height: 16px;
        }}
        .nut-skeleton::after {{
            content: '';
            position: absolute;
            inset: 0;
            transform: translateX(200%);
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07), transparent);
            animation: nutShimmer 1.4s ease-in-out infinite;
        }}

        /* ─── Welcome card icon delight ────────────────────────────────── */
        .nut-welcome-icon {{ transition: transform 0.25s {t.EASE}; }}
        .nut-welcome-card:hover .nut-welcome-icon {{
            transform: scale(1.1) rotate(-4deg);
        }}

        /* ─── Inputs: focus glow ───────────────────────────────────────── */
        .stTextInput input, .stNumberInput input, .stTextArea textarea,
        [data-baseweb="select"] > div {{
            transition: border-color {t.DUR_FAST} ease, box-shadow {t.DUR_FAST} ease;
        }}
        .stTextInput input:focus, .stNumberInput input:focus,
        .stTextArea textarea:focus {{
            border-color: {t.PRIMARY} !important;
            box-shadow: 0 0 0 3px rgba(79,142,247,0.18) !important;
        }}

        /* ─── Tabs: animated highlight ─────────────────────────────────── */
        [data-baseweb="tab-highlight"] {{
            background: {t.GRAD_PRIMARY} !important;
            height: 3px !important;
            border-radius: 3px;
        }}
        button[role="tab"] {{ transition: color 0.2s ease; }}

        /* ─── Expander chevron ─────────────────────────────────────────── */
        [data-testid="stExpander"] summary svg {{
            transition: transform 0.25s {t.EASE};
        }}

        /* ─── Toasts & progress ────────────────────────────────────────── */
        [data-testid="stToast"] {{
            background: {t.SURFACE_2} !important;
            border: 1px solid {t.BORDER_2} !important;
            border-radius: {t.RADIUS_LG} !important;
            box-shadow: {t.SHADOW_LG} !important;
            animation: nutFadeUp 0.3s {t.EASE_OUT} both;
        }}
        [data-testid="stProgress"] > div > div {{
            background: {t.SURFACE_3} !important;
            border-radius: 999px !important;
            overflow: hidden;
        }}
        [data-testid="stProgress"] > div > div > div {{
            background: {t.GRAD_ACCENT} !important;
            border-radius: 999px !important;
            transition: width {t.DUR_SLOW} {t.EASE};
        }}

        /* ─── Home dashboard (app_user.py builds it as inline-styled HTML,
               so we hook animations by class names added there) ──────────── */
        @keyframes bfBreathe {{
            0%, 100% {{ transform: scale(1); }}
            50%      {{ transform: scale(1.035); }}
        }}
        /* Direct children of the dashboard slide up in a staggered cascade
           on every load — the visible "it's alive" cue on refresh. */
        .bf-home > div {{ animation: nutFadeUp 0.5s {t.EASE_OUT} both; }}
        .bf-home > div:nth-child(2) {{ animation-delay: 0.06s; }}
        .bf-home > div:nth-child(3) {{ animation-delay: 0.12s; }}
        .bf-home > div:nth-child(4) {{ animation-delay: 0.18s; }}
        .bf-home > div:nth-child(5) {{ animation-delay: 0.24s; }}
        .bf-home > div:nth-child(6) {{ animation-delay: 0.30s; }}
        .bf-home > div:nth-child(7) {{ animation-delay: 0.36s; }}
        /* Every ring pops in on load */
        .bf-home svg {{ animation: nutPop 0.6s {t.EASE_OUT} both; }}
        /* The big calorie ring keeps gently breathing — persistent, always
           visible even in a static screenshot */
        .bf-ring-main {{ animation: bfBreathe 3.5s ease-in-out infinite; }}
        /* Cards & tiles lift on hover/tap */
        .bf-tile {{ transition: transform 0.22s {t.EASE}, box-shadow 0.22s {t.EASE}, border-color 0.22s {t.EASE}; }}
        .bf-tile:hover {{
            transform: translateY(-3px);
            border-color: {t.PRIMARY} !important;
            box-shadow: {t.SHADOW_MD};
        }}
        .bf-tile:active {{ transform: translateY(-1px) scale(0.99); }}
        /* Today's chip in the week strip pulses softly */
        .bf-today {{ animation: bfBreathe 2.6s ease-in-out infinite; }}

        /* ─── Accessibility: respect reduced-motion preference ─────────── */
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                scroll-behavior: auto !important;
            }}
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # ── PWA: manifest + service-worker registration ───────────────────────────
    st.markdown(
        '<link rel="manifest" href="/app/static/manifest.json">'
        '<meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        '<meta name="apple-mobile-web-app-title" content="NutriSmart">'
        f'<meta name="theme-color" content="{t.BG}">'
        '<script>'
        'if("serviceWorker" in navigator){'
        '  navigator.serviceWorker.register("/app/static/sw.js")'
        '    .catch(function(){});'
        '}'
        '</script>',
        unsafe_allow_html=True,
    )


def brand_wordmark(size: str = "1.1rem") -> str:
    """Return the 'NutriSmart' wordmark as gradient HTML (green→blue, per logo).

    Falls back to a solid PRIMARY fill where background-clip:text is unsupported.
    """
    return (
        f'<span style="font-size:{size};font-weight:800;letter-spacing:-0.02em;'
        f'background:{t.GRAD_PRIMARY};-webkit-background-clip:text;background-clip:text;'
        f'-webkit-text-fill-color:transparent;color:{t.PRIMARY}">NutriSmart</span>'
    )


def theme_toggle(key: str = "nut_theme_toggle") -> None:
    """Render a light/dark mode switch. Persists choice in session_state."""
    is_dark = st.session_state.get("theme_mode") == "dark"
    label = "☀️ מצב בהיר" if is_dark else "🌙 מצב כהה"
    if st.button(label, key=key, use_container_width=True):
        st.session_state["theme_mode"] = "light" if is_dark else "dark"
        st.rerun()


def _logo_path() -> str:
    import os as _os
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    return _os.path.join(root, "logo sketch.png")


@st.cache_data(show_spinner=False)
def logo_bytes():
    """Return the raw NutriSmart logo PNG bytes (or None if missing).

    Use with ``st.image`` — Streamlit's markdown sanitizer strips sizing
    attributes off raw ``<img>`` tags, so HTML embedding renders unusable.
    """
    import os as _os
    path = _logo_path()
    if not _os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


@st.cache_data(show_spinner=False)
def logo_data_uri() -> str:
    """Return a base64 data-URI for the NutriSmart logo (or empty string)."""
    import base64
    data = logo_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii") if data else ""


def app_header(date_str: Optional[str] = None, theme_key: str = "nut_hdr_theme") -> bool:
    """Sticky top header: logo (or wordmark) + date + a light/dark toggle.

    Returns True if the theme toggle was clicked this run (caller may persist
    the new ``st.session_state['theme_mode']`` and rerun). The toggle itself
    updates session_state and triggers a rerun.
    """
    inject_global_css()
    _lb = logo_bytes()
    hc1, hc2, hc3 = st.columns([1, 5, 1], vertical_alignment="center")
    with hc1:
        if _lb:
            st.image(_lb, width=42)
        else:
            st.markdown(brand_wordmark("1.1rem"), unsafe_allow_html=True)
    with hc2:
        bits = [brand_wordmark("1.15rem")]
        if date_str:
            bits.append(
                f'<span style="font-size:0.72rem;color:{t.TEXT_DIM};font-weight:600">{date_str}</span>'
            )
        st.markdown(
            f'<div dir="rtl" style="display:flex;align-items:center;gap:10px;padding-top:6px">'
            f'{"".join(bits)}</div>',
            unsafe_allow_html=True,
        )
    clicked = False
    with hc3:
        is_dark = st.session_state.get("theme_mode") == "dark"
        if st.button("☀️" if is_dark else "🌙", key=theme_key,
                     help="החלף מצב בהיר/כהה"):
            st.session_state["theme_mode"] = "light" if is_dark else "dark"
            clicked = True
    return clicked


def swipe_deck_css() -> None:
    """Lay out the ``bf_deck`` container's columns as a horizontal scroll-snap deck.

    Each Streamlit column becomes a full-width panel; native swipe/scroll moves
    between them. The deck scrolls LTR (panel 0 = leftmost) for predictable
    index→offset math even though panel content stays RTL.
    """
    st.markdown(
        f"""
<style>
.st-key-bf_deck [data-testid="stHorizontalBlock"] {{
    flex-wrap: nowrap !important;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    direction: ltr;
    gap: 0 !important;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
}}
.st-key-bf_deck [data-testid="stHorizontalBlock"]::-webkit-scrollbar {{ display: none; }}
.st-key-bf_deck [data-testid="stColumn"] {{
    flex: 0 0 100% !important;
    width: 100% !important;
    min-width: 100% !important;
    scroll-snap-align: start;
    padding: 0 3px !important;
}}
/* Segmented deck nav — pill bar */
.st-key-bf_decknav {{
    position: sticky; top: 0; z-index: 50;
    background: {t.BG};
    padding: 4px 0 8px !important;
}}
.st-key-bf_decknav [data-testid="stHorizontalBlock"] {{
    gap: 4px !important;
    background: {t.SURFACE_2};
    border: 1px solid {t.BORDER};
    border-radius: 999px;
    padding: 4px !important;
}}
.st-key-bf_decknav button {{
    border-radius: 999px !important;
    min-height: 38px !important;
    border: none !important;
    background: transparent !important;
    color: {t.TEXT_MUTED} !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    box-shadow: none !important;
}}
.st-key-bf_decknav button:hover {{ color: {t.TEXT} !important; transform: none !important; }}
</style>
""",
        unsafe_allow_html=True,
    )


def deck_nav(items, active: int = 0) -> None:
    """Sticky pill nav for the swipe deck. ``items`` = list of (icon, label).

    Clicking a pill sets ``st.session_state['_deck_target']`` and reruns; the
    JS in :func:`swipe_deck_behavior` scrolls the deck to that panel.
    """
    with st.container(key="bf_decknav"):
        cols = st.columns(len(items))
        for i, (icon, label) in enumerate(items):
            mark = "🔵 " if i == active else ""
            if cols[i].button(f"{icon} {label}", key=f"_decknav_{i}",
                              use_container_width=True):
                st.session_state["_deck_target"] = i
                st.rerun()
        # Highlight the active pill (filled) via injected nth-child rule.
        st.markdown(
            f'<style>.st-key-bf_decknav [data-testid="stColumn"]:nth-child({active + 1}) '
            f'button {{ background: {t.GRAD_PRIMARY} !important; color: #fff !important; '
            f'box-shadow: {t.SHADOW_PRI} !important; }}</style>',
            unsafe_allow_html=True,
        )


def swipe_deck_behavior(target_index: int, panel_count: int = 4) -> None:
    """Drive the deck's scroll position across Streamlit reruns.

    Streamlit reruns replace the deck DOM, which would reset the scroll to
    panel 0. This injects (via a 0-height same-origin iframe) JS that:
      • scrolls to ``target_index`` when the nav target changed, else
      • restores the user's last manual scroll position from sessionStorage.
    """
    import streamlit.components.v1 as _stc
    _stc.html(
        f"""
<script>
(function() {{
  const TARGET = {int(target_index)};
  const doc = window.parent.document;
  function deck() {{
    return doc.querySelector('.st-key-bf_deck [data-testid="stHorizontalBlock"]');
  }}
  function apply() {{
    const d = deck();
    if (!d) return;
    const lastT = sessionStorage.getItem('bf_deck_T');
    if (String(TARGET) !== lastT) {{
      sessionStorage.setItem('bf_deck_T', String(TARGET));
      const x = TARGET * d.clientWidth;
      d.scrollTo({{ left: x, behavior: 'smooth' }});
      sessionStorage.setItem('bf_deck_X', String(x));
    }} else {{
      const sx = parseFloat(sessionStorage.getItem('bf_deck_X') || '0');
      if (Math.abs(d.scrollLeft - sx) > 4) d.scrollLeft = sx;
    }}
    if (!d.dataset.bfWired) {{
      d.dataset.bfWired = '1';
      d.addEventListener('scroll', function() {{
        sessionStorage.setItem('bf_deck_X', String(d.scrollLeft));
      }});
    }}
  }}
  apply();
  let n = 0;
  const iv = setInterval(function() {{ apply(); if (++n > 24) clearInterval(iv); }}, 150);
}})();
</script>
""",
        height=0,
    )


def month_calendar_html(today, logged_days=None) -> str:
    """Compact, themed month grid (Sunday-first, Israeli week). Read-only.

    ``logged_days`` — optional set of day-ints in the current month to dot-mark.
    """
    import calendar as _cal
    logged_days = logged_days or set()
    cal = _cal.Calendar(firstweekday=6)  # Sunday first
    weeks = cal.monthdayscalendar(today.year, today.month)
    heads = "".join(
        f'<div style="text-align:center;font-size:0.6rem;color:{t.TEXT_DIM};'
        f'font-weight:700;padding:2px 0">{d}</div>'
        for d in ["א", "ב", "ג", "ד", "ה", "ו", "ש"]
    )
    cells = ""
    for wk in weeks:
        for day in wk:
            if day == 0:
                cells += "<div></div>"
                continue
            is_today = day == today.day
            dot = (
                f'<div style="width:4px;height:4px;border-radius:50%;background:{t.ACCENT};'
                f'margin:1px auto 0"></div>'
                if (day in logged_days and not is_today) else '<div style="height:5px"></div>'
            )
            bg = t.PRIMARY if is_today else "transparent"
            fg = "#ffffff" if is_today else t.TEXT
            cells += (
                f'<div style="text-align:center;padding:3px 0">'
                f'<div style="width:26px;height:26px;line-height:26px;margin:0 auto;'
                f'border-radius:50%;background:{bg};color:{fg};font-size:0.72rem;'
                f'font-weight:{"800" if is_today else "500"}">{day}</div>{dot}</div>'
            )
    month_names = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי",
                   "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
    title = f"{month_names[today.month - 1]} {today.year}"
    return (
        f'<div class="nut-card" dir="rtl" style="padding:14px 16px">'
        f'<div style="font-size:0.9rem;font-weight:800;color:{t.TEXT};margin-bottom:10px">'
        f'📅 {title}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(7,1fr);margin-bottom:4px">{heads}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(7,1fr)">{cells}</div>'
        f'</div>'
    )


def bottom_nav(active: str = "home") -> None:
    """Hidden-by-default bottom nav that expands from a floating button.

    A circular FAB sits at the bottom centre; tapping it toggles the full
    phone-width tab-bar (``st.session_state['_nav_open']``). Collapsed by
    default so it never covers content at page open. Uses ``st.page_link`` so
    clicks stay in Streamlit's router.
    """
    items = [
        ("home",     "app_user.py",                    "בית",        "🏠"),
        ("food",     "pages/6_daily_menu.py",          "תזונה",      "🍽️"),
        ("chat",     "pages/10_chat_log.py",           "צאט",        "💬"),
        ("barcode",  "pages/12_barcode.py",            "ברקוד",      "📲"),
        ("workout",  "pages/7_workout_tracker.py",     "אימון",      "💪"),
        ("water",    "pages/16_hydration.py",          "מים",        "💧"),
        ("history",  "pages/9_history.py",             "היסטוריה",   "📊"),
        ("profile",  "pages/0_profile.py",             "פרופיל",     "👤"),
        ("settings", "pages/14_settings.py",           "הגדרות",     "⚙️"),
    ]

    # Map active key → column index so we can highlight the right cell.
    active_idx = next((i for i, it in enumerate(items) if it[0] == active), 0)

    nav_open = st.session_state.get("_nav_open", False)

    # ── Floating toggle (always visible) ──────────────────────────────────────
    st.markdown(
        f"""
<style>
.st-key-bf_nav_fab {{
    position: fixed; bottom: 16px; left: 0; right: 0; z-index: 10000;
    width: 58px; margin: 0 auto !important;
}}
.st-key-bf_nav_fab button {{
    width: 58px !important; height: 58px !important; min-height: 0 !important;
    border-radius: 50% !important; padding: 0 !important; border: none !important;
    background: {t.GRAD_PRIMARY} !important; color: #fff !important;
    box-shadow: {t.SHADOW_PRI} !important; font-size: 1.4rem !important;
}}
.st-key-bf_nav_fab button:hover {{ transform: translateY(-2px) scale(1.04); }}
/* Always keep content clear of the FAB */
[data-testid="stMain"] .block-container {{ padding-bottom: 92px !important; }}
</style>
""",
        unsafe_allow_html=True,
    )
    with st.container(key="bf_nav_fab"):
        if st.button("✕" if nav_open else "☰", key="bf_nav_fab_btn",
                     help="תפריט ניווט"):
            st.session_state["_nav_open"] = not nav_open
            st.rerun()

    if not nav_open:
        return

    st.markdown(
        f"""
<style>
/* Fixed, centered phone-width tab-bar anchored to the keyed container */
.st-key-bf_bottom_nav {{
    position: fixed;
    bottom: 84px;
    left: 0;
    right: 0;
    z-index: 9999;
    max-width: 480px;
    margin: 0 auto !important;
    background: {t.SURFACE};
    backdrop-filter: blur(18px);
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_LG};
    box-shadow: {t.SHADOW_LG};
    padding: 8px 6px !important;
    animation: nutFadeUp {t.DUR_MED} {t.EASE_OUT};
}}
.st-key-bf_bottom_nav [data-testid="stHorizontalBlock"] {{
    gap: 0 !important;
    flex-wrap: nowrap !important;
}}
.st-key-bf_bottom_nav [data-testid="stColumn"] {{
    min-width: 0 !important;
    flex: 1 1 0 !important;
    padding: 0 !important;
}}
.st-key-bf_bottom_nav a[data-testid="stPageLink-NavLink"] {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    text-decoration: none;
    color: {t.TEXT_DIM};
    padding: 5px 1px;
    border-radius: 10px;
    font-size: 0.68rem;
    font-weight: 500;
    line-height: 1.25;
    white-space: nowrap;
    transition: color .15s, background .15s, transform .2s cubic-bezier(0.34, 1.56, 0.64, 1);
}}
/* page_link renders the emoji + label inline; bump the emoji size a touch */
.st-key-bf_bottom_nav a[data-testid="stPageLink-NavLink"] p {{
    font-size: 0.68rem !important;
    line-height: 1.25 !important;
}}
.st-key-bf_bottom_nav a[data-testid="stPageLink-NavLink"]:hover {{
    color: {t.TEXT_MUTED};
    background: {t.SURFACE_2};
}}
.st-key-bf_bottom_nav a[data-testid="stPageLink-NavLink"]:active {{
    transform: scale(0.9);
}}
/* Active cell — colored + lifted */
.st-key-bf_bottom_nav [data-testid="stColumn"]:nth-child({active_idx + 1}) a[data-testid="stPageLink-NavLink"] {{
    color: {t.PRIMARY} !important;
    transform: translateY(-2px);
}}
</style>
""",
        unsafe_allow_html=True,
    )

    with st.container(key="bf_bottom_nav"):
        cols = st.columns(len(items))
        for i, (key, page, label, icon) in enumerate(items):
            with cols[i]:
                st.page_link(page, label=f"{icon} {label}", use_container_width=True)


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
          <circle cx="{cx}" cy="{cy}" r="{r}" class="nut-ring-progress"
            fill="none" stroke="{color}" stroke-width="12"
            stroke-dasharray="{filled:.1f} {gap:.1f}"
            stroke-dashoffset="{circumference * 0.25:.1f}"
            stroke-linecap="round"/>
        </svg>
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;text-align:center">
          <div class="nut-ring-center-val" style="font-size:1.5rem;font-weight:800;color:{t.TEXT};line-height:1">{consumed}</div>
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


def skeleton_html(height: str = "80px", count: int = 1) -> str:
    """Shimmering loading placeholder — render before slow content arrives.

    Usage: ``ph = st.empty(); ph.markdown(skeleton_html("120px", 3), unsafe_allow_html=True)``
    then replace ``ph`` with the real content once loaded.
    """
    block = (
        f'<div class="nut-skeleton" '
        f'style="height:{height};margin:8px 0"></div>'
    )
    return f'<div dir="rtl">{block * max(count, 1)}</div>'


# ── Recipe card ─────────────────────────────────────────────────────────────

def recipe_card_html(recipe: dict, image_uri: str = "",
                     match_pct: Optional[int] = None,
                     show_rank: bool = False) -> str:
    """Render a recipe card as HTML — used by main, recipes list, daily menu.

    The card always:
      - has an ``alt`` attribute on the image,
      - shows kashrut as icon + label + color (not color alone),
      - renders as a non-navigating card (no detail route exists yet).
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
    href      = "#"
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
        f'<a href="{href}" target="_self" onclick="return false;" style="text-decoration:none;color:inherit">'
        f'<div class="nut-card nut-card-clickable" style="padding:0;overflow:hidden">'
        f'{"<div style=\'position:relative\'>" + image_block + "</div>" if image_block else ""}'
        f'<div class="nut-card-body" style="padding:16px 18px">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;margin-bottom:6px">'
        f'<div style="font-size:1rem;font-weight:700;color:{t.TEXT};line-height:1.3">{name_he}</div>'
        f'<div style="display:flex;gap:4px;align-items:center;flex-shrink:0">{kashrut_badge_html(kashrut)}{rank_html}</div>'
        f'</div>'
        f'<div style="font-size:0.8rem;color:{t.TEXT_MUTED};margin-bottom:12px;display:flex;gap:10px;flex-wrap:wrap">'
        f'<span>⏱ {prep} דק׳</span>'
        f'{"<span style=\'color:" + match_color + ";font-weight:600\'>" + str(match_pct) + "% התאמה</span>" if match_pct is not None else ""}'
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
    ("סריקת קבלה",  "pages/15_receipt_scanner.py",     "scan"),
    ("אימונים",     "pages/17_weekly_workout_plan.py", "training"),
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


# ── Meal-picker components (first-login flow) ────────────────────────────────

def meal_picker_card_html(
    recipe: dict,
    selected: bool = False,
    adjusted: bool = False,
) -> str:
    """Compact card used in pages/13_meal_preferences.py.

    Shows the recipe name, prep time, kashrut, and per-portion macros.
    The selection / adjust state is purely visual; the Streamlit page below
    handles the actual button wiring.
    """
    name_he   = recipe.get("name_he", "") or recipe.get("name_en", "")
    name_en   = recipe.get("name_en", "")
    portions  = max(recipe.get("portions", 1), 1)
    prep      = recipe.get("prep_time_minutes", 0)
    kashrut   = (recipe.get("kashrut") or "parve").lower()
    nut       = recipe.get("total_nutrition", {}) or {}
    cal       = round(nut.get("calories", 0) / portions)
    protein   = round(nut.get("protein", 0) / portions)
    carbs     = round(nut.get("carbs", 0) / portions)
    fat       = round(nut.get("fat", 0) / portions)

    border = t.ACCENT if selected else t.BORDER
    badge = ""
    if selected:
        badge = (
            f'<span style="background:{t.ACCENT};color:#fff;font-size:0.7rem;'
            f'padding:3px 8px;border-radius:6px;font-weight:700">נבחר</span>'
        )
    elif adjusted:
        badge = (
            f'<span style="background:{t.WARNING};color:#fff;font-size:0.7rem;'
            f'padding:3px 8px;border-radius:6px;font-weight:700">הותאם</span>'
        )

    return f"""
    <div style="background:{t.SURFACE_2};border:2px solid {border};
                border-radius:12px;padding:14px;margin-bottom:8px;direction:rtl">
      <div style="display:flex;justify-content:space-between;align-items:start;gap:8px">
        <div style="flex:1">
          <div style="font-weight:700;color:{t.TEXT};font-size:1rem">{name_he}</div>
          <div style="font-size:0.72rem;color:{t.TEXT_MUTED};margin-top:2px">{name_en}</div>
        </div>
        {badge}
      </div>
      <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
        {kashrut_badge_html(kashrut)}
        <span style="background:{t.SURFACE_3};color:{t.TEXT_MUTED};font-size:0.7rem;
                     padding:3px 8px;border-radius:6px">⏱ {prep} דקות</span>
      </div>
      <div style="margin-top:10px">
        {macro_grid_html(cal, protein, carbs, fat)}
      </div>
    </div>
    """


def macro_delta_html(
    before: dict,
    after: dict,
    targets: Optional[dict] = None,
    label_before: str = "לפני",
    label_after: str = "אחרי",
) -> str:
    """Before / after macro comparison with deltas, optionally vs. targets.

    `before` and `after` are dicts with keys: calories, protein, carbs, fat
    (any of them missing → treated as 0). `targets` is optional and adds a
    third row with target value + colored delta-from-target.
    """
    def _v(d, k):
        try:
            return float((d or {}).get(k, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    rows = [
        ("קלוריות", "calories", "קק״ל", t.ACCENT),
        ("חלבון", "protein", "g", t.PROTEIN_COLOR),
        ("פחמימות", "carbs", "g", t.CARBS_COLOR),
        ("שומן", "fat", "g", t.FAT_COLOR),
    ]

    cells = []
    for label, key, unit, color in rows:
        b = _v(before, key)
        a = _v(after, key)
        d = a - b
        arrow = "→"
        if d > 0.5:
            delta_str = f"<span style='color:{t.WARNING}'>▲ +{d:.0f}</span>"
        elif d < -0.5:
            delta_str = f"<span style='color:{t.ACCENT}'>▼ {d:.0f}</span>"
        else:
            delta_str = f"<span style='color:{t.TEXT_MUTED}'>•</span>"

        target_row = ""
        if targets is not None:
            tgt = _v(targets, key)
            if tgt > 0:
                pct = (a / tgt) * 100
                pct_col = t.ACCENT if 85 <= pct <= 110 else (t.WARNING if 70 <= pct < 130 else t.DANGER)
                target_row = (
                    f"<div style='font-size:0.68rem;color:{t.TEXT_MUTED};margin-top:2px'>"
                    f"יעד: {tgt:.0f} <span style='color:{pct_col};font-weight:700'>"
                    f"({pct:.0f}%)</span></div>"
                )

        cells.append(f"""
          <div style='text-align:center;padding:8px;background:{t.SURFACE_2};
                       border-radius:8px;border:1px solid {t.BORDER}'>
            <div style='font-size:0.72rem;color:{t.TEXT_MUTED}'>{label}</div>
            <div style='display:flex;align-items:center;justify-content:center;gap:6px;
                         margin-top:4px;font-size:0.95rem;font-weight:700;color:{color}'>
              <span style='color:{t.TEXT_MUTED};font-size:0.78rem'>{b:.0f}</span>
              <span style='color:{t.TEXT_MUTED}'>{arrow}</span>
              <span>{a:.0f}{unit}</span>
            </div>
            <div style='font-size:0.72rem;margin-top:2px'>{delta_str}</div>
            {target_row}
          </div>
        """)

    return f"""
    <div style='direction:rtl'>
      <div style='display:flex;justify-content:space-between;font-size:0.75rem;
                   color:{t.TEXT_MUTED};margin-bottom:6px'>
        <span>{label_before} ← → {label_after}</span>
      </div>
      <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:8px'>
        {''.join(cells)}
      </div>
    </div>
    """


def now_eating_html(
    meal_label: str,
    variant_name: str,
    calories: float,
    protein: float,
    carbs: float,
    fat: float,
    time_window_label: str = "",
) -> str:
    """Hero block for pages/6_daily_menu.py — "Eat now: <meal>"."""
    return f"""
    <div class='nut-now-eating'
         style='background:linear-gradient(135deg,{t.ACCENT}22,{t.SURFACE_2});
                border:2px solid {t.ACCENT};border-radius:16px;padding:18px;
                direction:rtl;margin-bottom:14px'>
      <div style='display:flex;justify-content:space-between;align-items:center'>
        <div>
          <div style='font-size:0.75rem;color:{t.ACCENT};font-weight:800;
                       letter-spacing:0.5px;text-transform:uppercase'>אכול עכשיו</div>
          <div style='font-size:1.4rem;font-weight:800;color:{t.TEXT};margin-top:4px'>
            {meal_label}
          </div>
          <div style='font-size:1rem;color:{t.TEXT_MUTED};margin-top:2px'>
            {variant_name}
          </div>
        </div>
        <div style='text-align:left'>
          <div style='font-size:1.6rem;font-weight:800;color:{t.ACCENT}'>{round(calories)}</div>
          <div style='font-size:0.7rem;color:{t.TEXT_MUTED}'>קק״ל</div>
          {f"<div style='font-size:0.7rem;color:{t.TEXT_MUTED};margin-top:6px'>{time_window_label}</div>" if time_window_label else ""}
        </div>
      </div>
      <div style='margin-top:12px'>
        {macro_grid_html(round(calories), round(protein), round(carbs), round(fat))}
      </div>
    </div>
    """


def swap_option_html(variant_name: str, calories: float, protein: float) -> str:
    """One row inside the swap drawer — name + headline macros."""
    return f"""
    <div style='background:{t.SURFACE_2};border:1px solid {t.BORDER};
                border-radius:10px;padding:10px 12px;direction:rtl;
                display:flex;justify-content:space-between;align-items:center'>
      <div style='font-weight:600;color:{t.TEXT};font-size:0.95rem'>{variant_name}</div>
      <div style='display:flex;gap:10px;font-size:0.78rem'>
        <span style='color:{t.ACCENT};font-weight:700'>{round(calories)} קק״ל</span>
        <span style='color:{t.PROTEIN_COLOR};font-weight:700'>{round(protein)}g חלבון</span>
      </div>
    </div>
    """
