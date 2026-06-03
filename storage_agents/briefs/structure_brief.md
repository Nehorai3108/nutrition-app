# Structure Brief — 2026-05-31

## Current State Assessment

| Item | Value |
|------|-------|
| App name | BiteFit — מעקב תזונה חכם |
| Version | 1.0.0 (pyproject.toml) |
| Python runtime | 3.13 (.claude/launch.json) |
| Framework | Streamlit ≥ 1.32 |
| Auth | Supabase email/password + JWT, cookie-persisted via `extra-streamlit-components` |
| Primary DB | SQLite (`storage/nutrition.db`) for foods/recipes/local logs |
| Cloud DB | Supabase (PostgreSQL) for user profiles, preferences, sync |
| AI / Chat | Groq API (gsk_...) via `groq>=0.5.0` |
| Pages | 18 pages (profile, recipes, inventory, barcode, scanner, workouts, meal planner, history, calendar, chat, settings, hydration, preferences) |
| PWA shell | `static/manifest.json` + `static/sw.js` present but **not wired into Streamlit** |
| Deployment | Local only — `0.0.0.0:8510`, no HTTPS, no cloud target configured |

---

## Critical Blockers (must fix before any store submission)

### 1. Credentials in `.env` — service key + database password exposed on-disk
The `.env` file contains `SUPABASE_SERVICE_KEY` (service role — bypasses ALL Row Level Security) and a plaintext PostgreSQL password in `DATABASE_URL`. Even though `.gitignore` excludes `.env`, a compromised developer machine fully exposes the Supabase database.

### 2. `showErrorDetails = true` in `.streamlit/config.toml`
Full Python stack traces are sent to the browser in production. This leaks internal paths, library versions, and potentially partial data. Must be `false` before any public deployment.

### 3. PWA not actually registered in the app
`static/manifest.json` and `static/sw.js` exist but Streamlit does **not** serve files from `static/` by default, and there is no `staticDir` in `.streamlit/config.toml`. No `<link rel="manifest">` is injected. No `navigator.serviceWorker.register(...)` call exists anywhere. The PWA cannot be installed by any browser.

### 4. Manifest icons use external CDN URLs
`manifest.json` lines 14–23: both icons point to `https://em-content.zobj.net/source/apple/...`. External CDN icons are blocked by App Store policy, break offline mode, and that CDN does not guarantee uptime. App stores require self-hosted, properly-sized icon assets.

### 5. GROQ_API_KEY is a placeholder
`.env` line 6: `GROQ_API_KEY=gsk_your_key_here`. The Groq-powered chat (`chatbot/grok_client.py`, `pages/10_chat_log.py`) will fail at runtime for any user who tries it.

### 6. USDA_API_KEY is `DEMO_KEY`
The food data agent uses the USDA FoodData Central demo key, which is rate-limited to ~1,000 requests/day and returns inconsistent results. Not acceptable for multi-user production.

### 7. No HTTPS enforcement
`.streamlit/config.toml` has no TLS config. Supabase JWTs and user passwords transit in plaintext on any non-localhost deployment. Apple requires HTTPS for all iOS apps; Google Play requires HTTPS for TWA.

### 8. `pyproject.toml` and `requirements.txt` are out of sync
`pyproject.toml` declares `openai>=1.0` and `streamlit-extras>=0.4` but `requirements.txt` does not include `openai`. `requirements.txt` includes `groq`, `supabase`, `pyzbar`, `qrcode` etc. that are absent from `pyproject.toml`. This means `pip install -e .` and `pip install -r requirements.txt` install different dependency sets.

### 9. Stale temp files tracked in git
`pages/14_settings.py.tmpnew`, `nutrition_app/models/user_meal_preferences.py.tmpnew`, and similar `.tmpnew` files are in the working tree and visible to git status. These should not exist in a release state.

---

## Recommended Mobile Path

**Recommendation: PWA-first for Android via TWA, Capacitor for iOS.**

### Why not pure PWA for iOS
Apple does not allow standalone PWAs in the App Store. iOS Safari supports PWA "Add to Home Screen" but that is not a store listing. For iOS App Store submission you need a native shell.

### Recommended architecture: Capacitor.js wrapper

```
BiteFit Streamlit (HTTPS hosted) ←── Capacitor WebView ──→ iOS / Android store
```

1. **Deploy Streamlit** to Streamlit Community Cloud (free tier), Railway, or Render behind HTTPS. All three provide automatic TLS.
2. **Fix the manifest + SW** (see P1 actions below) so the hosted URL is a proper PWA.
3. **Create a Capacitor project** that wraps the hosted URL:
   - `npm init @capacitor/app bitefit-native`
   - Set `server.url` to the hosted Streamlit HTTPS URL
   - `npx cap add ios && npx cap add android`
4. **Add native plugins** where needed:
   - `@capacitor/camera` — replace the barcode/receipt scanner `pyzbar` approach with native camera
   - `@capacitor/local-notifications` — daily meal reminders
5. **Submit to stores** using native metadata, icons, and screenshots.

### Why not Streamlit Community Cloud as the only delivery
Community Cloud is fine for development/demo but does not support custom domains on the free tier, and the URL is not app-store-submittable. Use it as the backend, Capacitor as the shell.

---

## Action Plan (Prioritized)

### P0 — Rotate exposed credentials immediately

- **File(s):** `.env`
- **Change:** Rotate `SUPABASE_SERVICE_KEY` in the Supabase dashboard (Settings → API → rotate service role key). Rotate the PostgreSQL password in Supabase → Database → Reset password. Update `.env` with new values. Move service key to an environment variable injected at deploy time (never in `.env` on dev machines).
- **Why:** The service role key bypasses Row Level Security. If it leaks, every user's health data is exposed with no audit trail.

---

### P1 — Wire manifest.json + service worker into Streamlit

- **File(s):** `.streamlit/config.toml`, `static/manifest.json`, `static/sw.js`, `ui/components.py` (or `app_user.py`)
- **Change 1 — serve static files:** Add to `.streamlit/config.toml`:
  ```toml
  [server]
  staticDir = "static"
  ```
- **Change 2 — inject manifest link and SW registration:** In `ui/components.py`, inside `inject_global_css()` (or as a separate function called from every page), append:
  ```python
  st.markdown(
      '<link rel="manifest" href="/app/static/manifest.json">'
      '<script>if("serviceWorker" in navigator) '
      'navigator.serviceWorker.register("/app/static/sw.js")</script>',
      unsafe_allow_html=True,
  )
  ```
  Note: Streamlit serves static files under `/app/static/` when `staticDir` is set.
- **Why:** Without this, the PWA cannot be installed by any browser. This is the minimum needed for "Add to Home Screen" on Android Chrome.

---

### P2 — Replace CDN icons with self-hosted assets

- **File(s):** `static/manifest.json`, `static/icons/` (create directory)
- **Change:** Create proper PNG icon files at `static/icons/icon-192.png` and `static/icons/icon-512.png`. For iOS also add `icon-180.png` (Apple touch icon). Update `manifest.json`:
  ```json
  "icons": [
    {"src": "/app/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "/app/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
    {"src": "/app/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
  ]
  ```
  Add to app HTML: `<link rel="apple-touch-icon" href="/app/static/icons/icon-180.png">`
- **Why:** CDN icons break offline mode (service worker can't cache external origins by default) and App Store review rejects apps with externally-hosted assets.

---

### P3 — Disable error details in production

- **File(s):** `.streamlit/config.toml`
- **Change:**
  ```toml
  [client]
  showErrorDetails = false
  ```
- **Why:** Stack traces expose internal file paths and library versions. This is a standard hardening step before any public deployment.

---

### P4 — Fix dependency manifest inconsistency

- **File(s):** `pyproject.toml`
- **Change:** Remove `openai>=1.0` from `pyproject.toml` dependencies (the app uses Groq, not OpenAI). Add the packages that are in `requirements.txt` but missing from `pyproject.toml`: `groq`, `supabase`, `pyzbar`, `qrcode`, `Pillow`, `PyJWT`, `pydantic`, `python-dateutil`, `httpx[http2]`, `requests`.
- **Why:** `pip install -e .` installs a different dependency set than `pip install -r requirements.txt`. CI or a new developer cloning the repo will get a broken install from `pyproject.toml`.

---

### P5 — Configure real API keys

- **File(s):** `.env`, production secrets manager
- **Change:** Replace `GROQ_API_KEY=gsk_your_key_here` with a real Groq key. Replace `USDA_API_KEY=DEMO_KEY` with a real USDA FoodData Central API key (free registration at api.nal.usda.gov).
- **Why:** Chat feature is non-functional. USDA demo key is rate-limited at 1,000 req/day, insufficient for multi-user production.

---

### P6 — Set up HTTPS and deployment target

- **File(s):** `.streamlit/config.toml`, new deployment config (e.g., `railway.toml` or `Procfile`)
- **Change:** Deploy to Streamlit Community Cloud (simplest) or Railway. Add `[server] enableCORS = false` and `enableXsrfProtection = true` to `.streamlit/config.toml`. Set environment variables in the platform's secrets panel, not in `.env`.
- **Why:** Supabase JWTs and passwords transit in plaintext without HTTPS. Required for any store submission. Required for Supabase magic links and email confirmation links to work correctly.

---

### P7 — Add privacy policy and app metadata

- **File(s):** `static/privacy.html` (new), `static/manifest.json`
- **Change:** Write a minimal privacy policy covering what health data is collected, where it is stored (Supabase), and how users can delete their account. Add `"related_applications": []` and `"prefer_related_applications": false` to manifest.json. Add screenshot placeholders in `screenshots: []`.
- **Why:** Both iOS App Store and Google Play require a privacy policy URL for health/fitness apps. Rejection is automatic without one.

---

### P8 — Delete stale temp files

- **File(s):** `pages/14_settings.py.tmpnew`, `app_user.py.tmpnew`, `nutrition_app/models/user_meal_preferences.py.tmpnew`, `nutrition_app/repositories/user_meal_preferences_repository.py.tmpnew`
- **Change:** Delete all `.tmpnew` files. Add `*.tmpnew` to `.gitignore`.
- **Why:** Stale files confuse editors, linters, and future developers. `.tmpnew` files indicate incomplete write operations that were not cleaned up.

---

## Environment & Security Audit

| Variable | Value in .env | Risk Level | Action |
|----------|--------------|------------|--------|
| `SUPABASE_URL` | `https://bmefzqnvtrqvskfikbxw.supabase.co` | Low — public URL | OK to keep in .env |
| `SUPABASE_ANON_KEY` | `sb_publishable_...` | Low — designed to be public | OK to keep in .env |
| `SUPABASE_SERVICE_KEY` | `sb_secret_3KExzq...` | **CRITICAL** — bypasses all RLS | Rotate immediately. Remove from .env. Use only server-side via platform secrets. |
| `DATABASE_URL` | `postgresql://postgres:HyHWa3k...` | **HIGH** — plaintext DB password | Rotate the DB password. Do not store in .env. Use platform secrets only. |
| `USDA_API_KEY` | `DEMO_KEY` | Medium — rate-limited public key | Replace with a real registered key |
| `GROQ_API_KEY` | `gsk_your_key_here` | High — feature is broken | Obtain and configure a real key |

**.env is in `.gitignore`** ✅ — credentials will not be committed.

**No hardcoded credentials were found in Python source files.** Auth credentials are loaded exclusively via `os.environ.get()` in `auth/supabase_client.py:150-162`. Streamlit secrets fallback is also correctly implemented.

---

## Performance Bottlenecks Found

1. **`app_user.py` sidebar makes 3+ repository calls on every Streamlit rerun** (lines 267–270: `WorkoutRepository`, line 474–476: `WaterRepository`, line 559: inventory count). Each of these opens a SQLite connection. With Streamlit's rerun-on-interaction model, a single user tapping a button triggers all of these. Add `@st.cache_data(ttl=30)` wrappers around the sidebar data loaders.

2. **SQLite has no connection pooling** (`db/database.py:101` creates a new connection per call). Under concurrent users (Streamlit Cloud, multiple browser tabs), SQLite's write-lock will cause `OperationalError: database is locked`. Acceptable for single-user local use; not acceptable for multi-user cloud. Medium-term: migrate all local JSON/SQLite storage to Supabase tables.

3. **`ALL_FOODS` list is built on every page that imports from `app_user.py`** (line 123: sorted list of all food items). This is 319 foods sorted alphabetically each time. The `@st.cache_resource` on `_get_catalog()` avoids re-reading the DB, but the sort and list comprehension still run per session. Extract the sorted list into the cached function's return value.

4. **`pages/6_daily_menu.py` and `pages/11_meal_wizard.py`** likely run the full MealPlanner pipeline on load. Meal plan generation should be cached per `(user_id, date)` pair for the session to avoid re-running on every sidebar interaction.

5. **No `@st.cache_data` on profile loads** — `_ProfileRepo().load(_USER_ID)` is called at the top of `app_user.py` on every rerun. Wrap with `@st.cache_data(ttl=300)` keyed on `user_id`.

---

## Store Submission Checklist

### PWA (Android Chrome / Google Play TWA)
- ✅ `manifest.json` exists with correct `display: standalone`
- ✅ Service worker (`sw.js`) exists with network-first strategy
- ✅ Dark theme configured (`background_color`, `theme_color` in manifest)
- ✅ Hebrew language and RTL direction declared
- ✅ App category: `["health", "fitness"]`
- ❌ Manifest not served by Streamlit (`staticDir` not configured)
- ❌ Service worker not registered in the app
- ❌ Icons are external CDN URLs, not self-hosted
- ❌ No maskable icon variant (separate file)
- ❌ `screenshots` array is empty (required for Google Play feature graphic)
- ❌ No `shortcuts` defined (lock-screen quick actions)

### iOS App Store (requires Capacitor shell)
- ✅ Auth flow complete (login, signup, email confirmation)
- ✅ Hebrew RTL UI
- ❌ No Capacitor project created
- ❌ No Xcode project / iOS bundle ID
- ❌ No Apple touch icon (`icon-180.png`)
- ❌ No launch/splash screens
- ❌ No privacy policy URL
- ❌ No App Store description, keywords, or age rating
- ❌ No screenshot assets (6.5" and 5.5" required)
- ❌ Camera permission string for barcode scanner (`NSCameraUsageDescription` in Info.plist)
- ❌ Health data privacy string (`NSHealthUpdateUsageDescription`) if HealthKit is added

### Security & Compliance
- ✅ JWT tokens stored in browser cookies (not localStorage)
- ✅ JWT auto-refresh implemented (`auth/supabase_client.py:196-208`)
- ✅ `.env` excluded from git
- ✅ Row Level Security configured in Supabase (inferred from RLS error handling in `get_supabase()`)
- ✅ Password confirmation on signup
- ❌ Service key is on-disk in `.env` (rotate + remove)
- ❌ `showErrorDetails = true` in config (disable before deployment)
- ❌ No rate limiting on login attempts (Supabase handles some, but no client-side throttle)
- ❌ HTTPS not configured
- ❌ No Content-Security-Policy header
