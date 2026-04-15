"""
Pexels-based recipe image fetcher.

Fetches candidate images for recipes from the Pexels API, stores them
locally under storage_agents/recipe_images/, and tracks pending approvals
in pending_approvals.json. Approved images get moved to approved/<recipe_id>.jpg
and the chosen path is written back to recipes.json via RecipeManager.

API key lookup order:
 1. Environment variable PEXELS_API_KEY
 2. Local file storage_agents/recipe_images/.pexels_api_key (single line)

If neither is set, fetch calls log a warning and return an empty list — the
dashboard keeps working without crashing.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# ---- Paths ----
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))
IMAGES_DIR = os.path.join(PROJECT_ROOT, "storage_agents", "recipe_images")
CANDIDATES_DIR = os.path.join(IMAGES_DIR, "candidates")
APPROVED_DIR = os.path.join(IMAGES_DIR, "approved")
PENDING_FILE = os.path.join(IMAGES_DIR, "pending_approvals.json")
API_KEY_FILE = os.path.join(IMAGES_DIR, ".pexels_api_key")
RECIPES_FILE = os.path.join(PROJECT_ROOT, "storage_agents", "recipes", "recipes.json")

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
REQUEST_TIMEOUT = 10

# Cloudflare in front of api.pexels.com rejects the default Python urllib
# User-Agent with a 1010 challenge, so we must present as a real browser.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _ensure_dirs() -> None:
    os.makedirs(CANDIDATES_DIR, exist_ok=True)
    os.makedirs(APPROVED_DIR, exist_ok=True)


def _get_api_key() -> Optional[str]:
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if key:
        return key
    if os.path.isfile(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, "r", encoding="utf-8") as fh:
                return fh.read().strip() or None
        except OSError:
            return None
    return None


# ---- Pending approvals I/O ----

def load_pending() -> Dict[str, dict]:
    """Return mapping: recipe_id -> {candidates: [...], status: 'pending'|'no_results'}."""
    if not os.path.isfile(PENDING_FILE):
        return {}
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_pending(pending: Dict[str, dict]) -> None:
    _ensure_dirs()
    with open(PENDING_FILE, "w", encoding="utf-8") as fh:
        json.dump(pending, fh, ensure_ascii=False, indent=2)


# ---- Recipes helpers ----

def _load_recipes() -> List[dict]:
    if not os.path.isfile(RECIPES_FILE):
        return []
    try:
        with open(RECIPES_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


# ---- Pexels API ----

def _pexels_search(query: str, per_page: int, api_key: str) -> List[dict]:
    params = urllib.parse.urlencode({"query": query, "per_page": per_page})
    req = urllib.request.Request(
        f"{PEXELS_SEARCH_URL}?{params}",
        headers={
            "Authorization": api_key,
            "User-Agent": _BROWSER_UA,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return data.get("photos", []) or []
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        log.warning("Pexels search failed for '%s': %s", query, exc)
        return []


def _download(url: str, dest: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            with open(dest, "wb") as fh:
                shutil.copyfileobj(resp, fh)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
        log.warning("Image download failed (%s): %s", url, exc)
        return False


def fetch_candidates(
    recipe_id: str,
    query_en: str,
    query_he: str = "",
    n: int = 3,
) -> List[dict]:
    """Fetch up to n candidate images for a recipe. Returns list of candidate dicts.

    Each candidate dict: {local_path, src_url, photographer, photographer_url, pexels_id}
    Paths are project-root-relative for portability.
    """
    api_key = _get_api_key()
    if not api_key:
        log.warning("PEXELS_API_KEY not set — skipping fetch for %s", recipe_id)
        return []

    _ensure_dirs()

    # Try a sequence of queries for best match.
    queries = []
    if query_en:
        queries.append(query_en)
        queries.append(f"{query_en} food")
        queries.append(f"{query_en} dish")
    if query_he:
        queries.append(query_he)

    photos: List[dict] = []
    for q in queries:
        photos = _pexels_search(q, per_page=n, api_key=api_key)
        if photos:
            break

    if not photos:
        return []

    recipe_dir = os.path.join(CANDIDATES_DIR, recipe_id)
    os.makedirs(recipe_dir, exist_ok=True)

    candidates: List[dict] = []
    for idx, photo in enumerate(photos[:n]):
        src = photo.get("src", {}) or {}
        img_url = src.get("large") or src.get("medium") or src.get("original")
        if not img_url:
            continue
        local_abs = os.path.join(recipe_dir, f"{idx}.jpg")
        if not _download(img_url, local_abs):
            continue
        local_rel = os.path.relpath(local_abs, PROJECT_ROOT).replace("\\", "/")
        candidates.append({
            "local_path": local_rel,
            "src_url": img_url,
            "photographer": photo.get("photographer", ""),
            "photographer_url": photo.get("photographer_url", ""),
            "pexels_id": photo.get("id"),
        })
    return candidates


# ---- Workflow ----

def run_batch(limit: int = 10) -> Dict[str, int]:
    """Process up to `limit` recipes that don't yet have an image or pending entry.

    Returns counts: {fetched, no_results, skipped}.
    """
    stats = {"fetched": 0, "no_results": 0, "skipped": 0}
    recipes = _load_recipes()
    pending = load_pending()

    for rec in recipes:
        if stats["fetched"] + stats["no_results"] >= limit:
            break
        rid = rec.get("recipe_id")
        if not rid:
            continue
        if rec.get("image_path"):
            continue  # already approved
        if rid in pending:
            continue  # already pending or marked no_results

        name_en = rec.get("name_en", "") or ""
        name_he = rec.get("name_he", "") or ""
        candidates = fetch_candidates(rid, name_en, name_he, n=3)
        if candidates:
            pending[rid] = {
                "name_he": name_he,
                "name_en": name_en,
                "status": "pending",
                "candidates": candidates,
            }
            stats["fetched"] += 1
        else:
            pending[rid] = {
                "name_he": name_he,
                "name_en": name_en,
                "status": "no_results",
                "candidates": [],
            }
            stats["no_results"] += 1
        # Persist after each recipe so partial progress survives crashes.
        save_pending(pending)
    return stats


def approve(recipe_id: str, chosen_index: int) -> Optional[dict]:
    """Move the chosen candidate to approved/ and remove the pending entry.

    Returns {image_path, image_credit} on success, or None if invalid.
    Does NOT update recipes.json — caller must invoke RecipeManager.set_recipe_image.
    """
    pending = load_pending()
    entry = pending.get(recipe_id)
    if not entry:
        return None
    candidates = entry.get("candidates", [])
    if chosen_index < 0 or chosen_index >= len(candidates):
        return None

    chosen = candidates[chosen_index]
    src_rel = chosen.get("local_path", "")
    src_abs = os.path.join(PROJECT_ROOT, src_rel)
    if not os.path.isfile(src_abs):
        return None

    _ensure_dirs()
    dest_abs = os.path.join(APPROVED_DIR, f"{recipe_id}.jpg")
    try:
        shutil.copyfile(src_abs, dest_abs)
    except OSError as exc:
        log.error("Failed to copy approved image for %s: %s", recipe_id, exc)
        return None

    # Cleanup candidates directory.
    recipe_cand_dir = os.path.join(CANDIDATES_DIR, recipe_id)
    if os.path.isdir(recipe_cand_dir):
        shutil.rmtree(recipe_cand_dir, ignore_errors=True)

    # Remove from pending.
    pending.pop(recipe_id, None)
    save_pending(pending)

    dest_rel = os.path.relpath(dest_abs, PROJECT_ROOT).replace("\\", "/")
    credit = chosen.get("photographer", "")
    return {"image_path": dest_rel, "image_credit": f"Pexels / {credit}" if credit else "Pexels"}


def reject(recipe_id: str) -> bool:
    """Discard all candidates for this recipe and mark it as no_results so it won't re-fetch."""
    pending = load_pending()
    entry = pending.get(recipe_id)
    if not entry:
        return False
    recipe_cand_dir = os.path.join(CANDIDATES_DIR, recipe_id)
    if os.path.isdir(recipe_cand_dir):
        shutil.rmtree(recipe_cand_dir, ignore_errors=True)
    entry["candidates"] = []
    entry["status"] = "rejected"
    pending[recipe_id] = entry
    save_pending(pending)
    return True


def get_stats() -> Dict[str, int]:
    """Return counts: {total_recipes, with_image, pending, no_results}."""
    recipes = _load_recipes()
    pending = load_pending()
    with_image = sum(1 for r in recipes if r.get("image_path"))
    pending_ct = sum(1 for v in pending.values() if v.get("status") == "pending")
    no_results_ct = sum(1 for v in pending.values() if v.get("status") in ("no_results", "rejected"))
    return {
        "total_recipes": len(recipes),
        "with_image": with_image,
        "pending": pending_ct,
        "no_results": no_results_ct,
    }
