# Design Brief — 2026-05-31

## Executive Summary

BiteFit has a well-structured dark-theme design system (`ui/theme.py`) and a polished
home dashboard with SVG calorie/macro rings that rivals native apps. The two critical
gaps are: (1) **bottom navigation exists but is only wired up on 3–4 pages**, leaving
most pages unreachable without the hidden sidebar; and (2) there is **no quick-log
path** from the home screen — the primary action of a nutrition app is buried two
navigations deep. Fixing these two issues will account for ~80% of the UX debt.

---

## Top 5 UI Improvements (Priority Order)

### 1. Wire `bottom_nav()` on Every Missing Page
- **File(s):** `pages/0_profile.py`, `pages/4_inventory.py`, `pages/9_history.py`,
  `pages/8_calendar.py`, `pages/7_workout_tracker.py`, `pages/7_weekly_workout_plan.py`,
  `pages/2_recipes.py`, `pages/13_meal_preferences.py`, `pages/10_chat_log.py`,
  `pages/12_barcode.py`, `pages/11_meal_wizard.py`, `pages/16_hydration.py`
- **Current state:** `bottom_nav()` is called only in `app_user.py`, `pages/6_daily_menu.py`,
  and `pages/14_settings.py`. All other pages leave users stranded — no bottom bar,
  and the sidebar is hidden (`initial_sidebar_state="collapsed"` + CSS hides
  `[data-testid="collapsedControl"]`).
- **Change:** Add `from ui.components import bottom_nav` import and call
  `bottom_nav("<active_tab>")` at the end of each missing page's render block,
  before any `st.stop()`. Pass the correct active tab key:
  `"home"` / `"menu"` / `"log"` / `"profile"` / `"settings"`.
  Also add `padding-bottom: 90px` is already global — no CSS change needed.
- **Acceptance criteria:** Tapping any of the 5 bottom-nav icons on any page shows
  the same bottom bar with the correct active state highlighted.
- **Effort:** S

---

### 2. Add a "Log Food" FAB (Floating Action Button) to the Home Dashboard
- **File(s):** `app_user.py` (lines 869–996), `ui/components.py`
- **Current state:** The home dashboard shows calorie/macro rings and a recent-meals
  feed, but there is no obvious CTA to log food. The path to logging is:
  sidebar → tפריט יומי (page 6), which is invisible since the sidebar is collapsed.
  The `bottom_nav` has no "log" shortcut as a primary tappable FAB.
- **Change:**
  1. In `ui/components.py`, add a `fab_html(label, page_url)` helper that renders
     a fixed-position circular button using inline CSS:
     ```python
     def fab_html(label: str = "+") -> str:
         return (
             '<div style="position:fixed;bottom:72px;left:50%;transform:translateX(-50%);'
             'z-index:1000">'
             f'<div style="width:56px;height:56px;border-radius:50%;'
             'background:linear-gradient(135deg,#4f8ef7,#00d4aa);'
             'display:flex;align-items:center;justify-content:center;'
             'font-size:1.8rem;color:#fff;cursor:pointer;'
             'box-shadow:0 4px 20px rgba(79,142,247,0.4)">'
             f'{label}</div></div>'
         )
     ```
  2. In `app_user.py` just before `bottom_nav("home")` (line 995), inject
     `st.markdown(fab_html("+"), unsafe_allow_html=True)` followed by a
     `st.page_link("pages/6_daily_menu.py", label="הוסף ארוחה", use_container_width=True)`
     wrapped in a visually hidden container (so the FAB is the visible trigger).
- **Acceptance criteria:** A circular `+` button is permanently visible above the
  bottom bar on the home screen. Tapping it navigates to `pages/6_daily_menu.py`.
- **Effort:** S

---

### 3. Remove Sidebar Workout + Water Blocks from `app_user.py`; Dedicate to Their Own Pages
- **File(s):** `app_user.py` (lines 189–568), `pages/16_hydration.py`,
  `pages/7_workout_tracker.py`
- **Current state:** The sidebar in `app_user.py` contains a full workout-log UI
  (lines 265–468) and full water-tracking UI (lines 471–555) — a total of ~300 lines
  of form logic. The sidebar is collapsed by default and hidden via CSS on narrow
  viewports, so this entire block is **invisible on mobile**. Meanwhile,
  `pages/16_hydration.py` and `pages/7_workout_tracker.py` exist as full pages for
  the same features.
- **Change:**
  1. Remove the `with st.expander("🏋️ אימוני היום")` block (lines 265–468) from
     `app_user.py`'s sidebar.
  2. Remove the `with st.expander("💧 מים - היום")` block (lines 471–555) from
     `app_user.py`'s sidebar.
  3. Keep only the navigation links and the slim profile card in the sidebar.
  4. Add the water 4-button quick-add row (`250 / 500 / 750 / 1L`) directly to
     the home dashboard (it's already there at lines 874–887) — no new code needed.
  5. The workout expander's functionality is fully replicated in `pages/7_workout_tracker.py`.
- **Acceptance criteria:** `app_user.py` sidebar code is reduced from ~380 lines to
  ~30 lines (navigation + profile card only). Water quick-add on dashboard is unaffected.
  Workout tracking still works via bottom nav → workout page.
- **Effort:** M

---

### 4. Onboarding: Convert `pages/0_profile.py` Tab-Form to Step-by-Step Wizard
- **File(s):** `pages/0_profile.py`
- **Current state:** New users land on a 3-tab form (`tab_personal / tab_prefs / tab_targets`)
  containing all fields at once. This is overwhelming for first-time users and common
  in 2020-era web forms. The research confirms that modern nutrition apps (MyFitnessPal,
  Lifesum) use a 1-question-per-screen onboarding flow with a progress bar that shows
  instant personalized results as the "wow moment" at the end.
- **Change:** Add step-based routing within `pages/0_profile.py` using
  `st.session_state["onboard_step"]` (int 0–5). Each step renders one input group:
  - Step 0: Goal selection (3 large icon cards: lose/maintain/gain)
  - Step 1: Name + gender
  - Step 2: Age (date of birth) + height + weight
  - Step 3: Activity level (5 options with brief descriptions)
  - Step 4: Dietary preferences / allergies (from `tab_prefs`)
  - Step 5: Results screen — show calculated TDEE, daily kcal target, macro split
    using the existing `NutritionEngine` call (already in the file).

  Add a top progress bar:
  ```python
  st.progress((st.session_state.get("onboard_step", 0)) / 5)
  ```

  Show Back/Next buttons instead of a single Save button. On Step 5 "wow screen",
  show a `st.success("יעד יומי שלך: X קק״ל")` card before saving and redirecting.

  The existing tab-based UI remains accessible for returning users who want to edit
  (add a "ערוך פרופיל מלא" expander at the bottom that shows the current 3-tab layout).
- **Acceptance criteria:** First-time users (empty profile) see 1-step-per-screen flow
  with progress indicator. Returning users can still access and edit all fields via
  the existing tab layout.
- **Effort:** L

---

### 5. Fix `layout="wide"` on All Sub-Pages to `layout="centered"`
- **File(s):** `pages/0_profile.py` (line 20), `pages/6_daily_menu.py` (line 41),
  `pages/2_recipes.py`, `pages/4_inventory.py`, `pages/9_history.py`,
  `pages/8_calendar.py`, `pages/7_workout_tracker.py`, `pages/12_barcode.py`,
  `pages/13_meal_preferences.py`, `pages/11_meal_wizard.py`
- **Current state:** All sub-pages call `st.set_page_config(layout="wide")`.
  The global CSS caps `.main .block-container` at `max-width: 480px; margin: 0 auto`,
  which means "wide" layout is immediately overridden. This causes: (a) brief layout
  flash on page load before CSS applies; (b) Streamlit's column ratio math uses
  the wider container for initial layout, then CSS compresses it, causing cramped
  columns; (c) native Streamlit widgets (charts, dataframes) render at full width
  before being constrained.
- **Change:** In each `st.set_page_config(...)` call on every sub-page, change
  `layout="wide"` → `layout="centered"`. This aligns the Streamlit intrinsic layout
  with the CSS constraint and eliminates the flash.
- **Acceptance criteria:** No visual flash on page load. `st.columns([1,1])` on
  sub-pages splits at ~240px each rather than ~600px each before CSS compression.
- **Effort:** S

---

## Color & Typography Recommendations

The existing `ui/theme.py` design token system is solid and aligns well with 2025–2026
nutrition app conventions. No overhaul needed. Specific refinements:

| Token | Current | Recommended | Reason |
|-------|---------|-------------|--------|
| `BG` | `#0d0f14` | Keep | OLED-friendly near-black |
| `SURFACE` | `#161b26` | Keep | Good card contrast |
| `PRIMARY` | `#4f8ef7` | Keep | Strong blue, protein color |
| `ACCENT` | `#00d4aa` | Keep | Teal works as success/calorie |
| `FAT_COLOR` | `#f472b6` | `#f87171` | Pink is less standard; red aligns with MyFitnessPal fat convention |
| `CARBS_COLOR` | `#f59e0b` | Keep | Orange/amber is universal for carbs |

**Typography:** Inter (already imported) is an excellent choice — it was designed for
UI legibility. One addition: load **Noto Sans Hebrew** as fallback for Hebrew glyphs
for correct character rendering on devices without system Hebrew fonts:
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Hebrew:wght@400;600;700&display=swap');
font-family: 'Inter', 'Noto Sans Hebrew', -apple-system, sans-serif;
```
Add this to `inject_global_css()` in `ui/components.py` (line 31).

---

## RTL/Hebrew Notes

**Already working well:**
- `direction: rtl` applied to stMarkdownContainer, form labels, expanders, tab labels
- All inline HTML uses `dir="rtl"` attributes
- `.main .block-container { direction: rtl }` set globally
- Sidebar has `direction: rtl` applied

**Issues to fix:**

1. **`st.progress()` fills left→right** (LTR artifact). Native Streamlit progress bars
   always fill from left, which is visually reversed for Hebrew/RTL users (progress
   should fill right→left). Replace all `st.progress()` calls in `pages/0_profile.py`
   (lines 193, 194, 203) and `app_user.py` (tabs_targets section, lines 1193–1204)
   with inline SVG progress bars that respect RTL direction, or add CSS:
   ```css
   [data-testid="stProgressBar"] > div {
       transform: scaleX(-1);
   }
   ```
   Add to `inject_global_css()` in `ui/components.py`.

2. **`st.metric()` delta arrows** point left/right (LTR). The delta indicator in
   `st.metric()` uses Unicode arrows that don't flip for RTL. This is minor but
   jarring — consider replacing `st.metric()` on key screens with custom HTML
   metric cards that use `↑`/`↓` arrows (bidirectional-safe).

3. **`st.columns()` ordering** — in RTL, users expect the first/primary column to
   be on the right. Streamlit renders columns left-to-right regardless of `dir`.
   Add to global CSS:
   ```css
   [data-testid="stHorizontalBlock"] {
       flex-direction: row-reverse;
   }
   ```
   **Warning:** Test carefully — this reverses ALL column blocks. Verify that the
   calorie ring card (`app_user.py` lines 722–754) still looks correct after this
   change, since it already manually positions elements with flexbox.

---

## Quick Wins (< 30 min each)

- **`pages/0_profile.py` line 20:** `layout="wide"` → `layout="centered"` (30 sec)
- **`pages/6_daily_menu.py` line 42:** `layout="wide"` → `layout="centered"` (30 sec)
- **`app_user.py` line 574:** The `#f4f6fb` text color in the BiteFit header is
  hardcoded — swap to `{t.TEXT}` using the imported theme token.
- **`app_user.py` lines 576–577:** Hardcoded date format `%d/%m/%Y` — consider
  `%e %B` for a more human-friendly Hebrew date style (e.g., "31 מאי").
- **`ui/components.py` line 31:** Add `Noto Sans Hebrew` to the font import URL
  for correct Hebrew glyph rendering on Windows/Linux without system Hebrew fonts.
- **`pages/14_settings.py` line 39–44:** Replace hardcoded `<h2>` and `<h3>` tags
  with `page_header()` and `section_header()` calls from `ui.components` —
  they're already imported and enforce design-system typography.
- **`app_user.py` line 83:** The dismiss-banner button uses `"✕"` text — change to
  an `icon_button("", "close", ...)` call to get the SVG close icon with correct
  hit-target size (`44px` per `theme.HIT_TARGET`).
- **Calm Mode banner duplication:** In `app_user.py` the calm-mode banner shows
  on first load (line 77–84) AND again inside `tab_targets` (line 1176–1179) for
  the same session. Remove the `tab_targets` instance — the home-screen banner is
  sufficient.
- **`pages/16_hydration.py`:** Add `bottom_nav("hydration")` if a hydration tab
  is added to the nav, or `bottom_nav("home")` as a fallback, so users aren't
  stranded on this page.
