"""
Knowledge Router — builds the system prompt for the nutrition agent.

Architecture (from email recommendation):
  1. Always load: red-flags.md + conflict-matrix.md + disclaimer.md  (deterministic, full)
  2. Selective RAG: conditions/ + patterns/ + sport-profiles/        (based on user profile)

The router is model-agnostic — it returns a plain string system prompt
that can be passed to any LLM (Groq, OpenAI, Claude, etc.)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_KNOWLEDGE_DIR = Path(__file__).parent

# ── Always-load files (deterministic, always included in full) ─────────────
_ALWAYS_LOAD = [
    _KNOWLEDGE_DIR / "always-load" / "red-flags.md",
    _KNOWLEDGE_DIR / "always-load" / "conflict-matrix.md",
    _KNOWLEDGE_DIR / "always-load" / "disclaimer.md",
]

# ── Condition modules (loaded based on user profile) ──────────────────────
_CONDITIONS: dict[str, Path] = {
    "dyslipidemia":          _KNOWLEDGE_DIR / "conditions" / "dyslipidemia.md",
    "cholesterol":           _KNOWLEDGE_DIR / "conditions" / "dyslipidemia.md",
    "celiac":                _KNOWLEDGE_DIR / "conditions" / "celiac.md",
    "gluten_free":           _KNOWLEDGE_DIR / "conditions" / "celiac.md",
    "ibs":                   _KNOWLEDGE_DIR / "conditions" / "gi-disorders.md",
    "gerd":                  _KNOWLEDGE_DIR / "conditions" / "gi-disorders.md",
    "crohn":                 _KNOWLEDGE_DIR / "conditions" / "gi-disorders.md",
    "colitis":               _KNOWLEDGE_DIR / "conditions" / "gi-disorders.md",
    "constipation":          _KNOWLEDGE_DIR / "conditions" / "gi-disorders.md",
    "gi_disorder":           _KNOWLEDGE_DIR / "conditions" / "gi-disorders.md",
    "allergy":               _KNOWLEDGE_DIR / "conditions" / "allergies-intolerances.md",
    "intolerance":           _KNOWLEDGE_DIR / "conditions" / "allergies-intolerances.md",
    "lactose_intolerance":   _KNOWLEDGE_DIR / "conditions" / "allergies-intolerances.md",
    "kashrut":               _KNOWLEDGE_DIR / "conditions" / "kashrut.md",
    "kosher":                _KNOWLEDGE_DIR / "conditions" / "kashrut.md",
}

# ── Diet pattern modules ───────────────────────────────────────────────────
_PATTERNS: dict[str, Path] = {
    "mediterranean":         _KNOWLEDGE_DIR / "patterns" / "mediterranean.md",
    "keto":                  _KNOWLEDGE_DIR / "patterns" / "keto-lchf.md",
    "lchf":                  _KNOWLEDGE_DIR / "patterns" / "keto-lchf.md",
    "low_carb":              _KNOWLEDGE_DIR / "patterns" / "keto-lchf.md",
    "intermittent_fasting":  _KNOWLEDGE_DIR / "patterns" / "intermittent-fasting.md",
    "if":                    _KNOWLEDGE_DIR / "patterns" / "intermittent-fasting.md",
    "16_8":                  _KNOWLEDGE_DIR / "patterns" / "intermittent-fasting.md",
}

# ── Sport profile modules ──────────────────────────────────────────────────
_SPORT_PROFILES: dict[str, Path] = {
    "strength":              _KNOWLEDGE_DIR / "sport-profiles" / "strength-power.md",
    "powerlifting":          _KNOWLEDGE_DIR / "sport-profiles" / "strength-power.md",
    "weightlifting":         _KNOWLEDGE_DIR / "sport-profiles" / "strength-power.md",
    "crossfit":              _KNOWLEDGE_DIR / "sport-profiles" / "strength-power.md",
    "gym":                   _KNOWLEDGE_DIR / "sport-profiles" / "strength-power.md",
    "endurance":             _KNOWLEDGE_DIR / "sport-profiles" / "endurance.md",
    "running":               _KNOWLEDGE_DIR / "sport-profiles" / "endurance.md",
    "cycling":               _KNOWLEDGE_DIR / "sport-profiles" / "endurance.md",
    "triathlon":             _KNOWLEDGE_DIR / "sport-profiles" / "endurance.md",
    "swimming":              _KNOWLEDGE_DIR / "sport-profiles" / "endurance.md",
    "team_sport":            _KNOWLEDGE_DIR / "sport-profiles" / "team-mixed.md",
    "football":              _KNOWLEDGE_DIR / "sport-profiles" / "team-mixed.md",
    "basketball":            _KNOWLEDGE_DIR / "sport-profiles" / "team-mixed.md",
    "volleyball":            _KNOWLEDGE_DIR / "sport-profiles" / "team-mixed.md",
    "martial_arts":          _KNOWLEDGE_DIR / "sport-profiles" / "team-mixed.md",
    "tennis":                _KNOWLEDGE_DIR / "sport-profiles" / "team-mixed.md",
    "bodybuilding":          _KNOWLEDGE_DIR / "sport-profiles" / "weight-class-aesthetic.md",
    "physique":              _KNOWLEDGE_DIR / "sport-profiles" / "weight-class-aesthetic.md",
    "aesthetic":             _KNOWLEDGE_DIR / "sport-profiles" / "weight-class-aesthetic.md",
    "weight_class":          _KNOWLEDGE_DIR / "sport-profiles" / "weight-class-aesthetic.md",
    "boxing":                _KNOWLEDGE_DIR / "sport-profiles" / "weight-class-aesthetic.md",
}


def _read(path: Path) -> str:
    """Read a markdown file, return empty string on error."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _resolve_profile_modules(profile: dict) -> list[Path]:
    """
    Map a user profile dict to a list of knowledge module paths.

    Expected profile keys (all optional):
      conditions   : list[str]  e.g. ["dyslipidemia", "ibs"]
      intolerances : list[str]  e.g. ["lactose", "gluten"]
      diet_pattern : str        e.g. "mediterranean"
      sport_profile: str        e.g. "strength"
      kashrut      : str        e.g. "strict" / "moderate" / "none"
    """
    modules: list[Path] = []
    seen: set[Path] = set()

    def _add(path: Path):
        if path not in seen and path.exists():
            seen.add(path)
            modules.append(path)

    # Conditions
    for cond in profile.get("conditions", []):
        key = cond.lower().replace("-", "_").replace(" ", "_")
        if key in _CONDITIONS:
            _add(_CONDITIONS[key])

    # Intolerances / allergies
    intolerances = profile.get("intolerances", [])
    if intolerances:
        _add(_CONDITIONS["allergy"])
    for intol in intolerances:
        key = intol.lower().replace("-", "_")
        if key == "gluten" or key == "celiac":
            _add(_CONDITIONS["celiac"])
        if key == "lactose":
            _add(_CONDITIONS["lactose_intolerance"])

    # Kashrut
    kashrut = profile.get("kashrut", "none")
    if kashrut and kashrut != "none":
        _add(_CONDITIONS["kashrut"])

    # Diet pattern
    pattern = profile.get("diet_pattern", "")
    if pattern:
        key = pattern.lower().replace("-", "_").replace(" ", "_")
        if key in _PATTERNS:
            _add(_PATTERNS[key])

    # Sport profile
    sport = profile.get("sport_profile", "")
    if sport:
        key = sport.lower().replace("-", "_").replace(" ", "_")
        if key in _SPORT_PROFILES:
            _add(_SPORT_PROFILES[key])

    return modules


def build_system_prompt(profile: Optional[dict] = None) -> str:
    """
    Build the full system prompt for the nutrition agent.

    Args:
        profile: dict with user profile data (see _resolve_profile_modules for keys)

    Returns:
        A complete system prompt string to pass to any LLM.
    """
    parts: list[str] = []

    # ── Preamble ────────────────────────────────────────────────────────────
    parts.append("""אתה סוכן תזונאי מקצועי ואישי. תפקידך לסייע למשתמשים להשיג מטרות תזונתיות
בצורה בטוחה, מדויקת ומותאמת אישית. אתה מתבסס על ידע עדכני ומבוסס ראיות.

השב תמיד בעברית, בצורה ידידותית אך מקצועית. כשאתה לא בטוח — אמור זאת.""")

    # ── Always-load modules (deterministic) ─────────────────────────────────
    for path in _ALWAYS_LOAD:
        content = _read(path)
        if content:
            parts.append(f"\n---\n{content}")

    # ── Selective modules (based on profile) ────────────────────────────────
    if profile:
        selective_modules = _resolve_profile_modules(profile)
        if selective_modules:
            parts.append("\n\n## ידע ספציפי לפרופיל המשתמש\n")
            for path in selective_modules:
                content = _read(path)
                if content:
                    parts.append(f"\n---\n{content}")

    # ── Critic checklist (always loaded, last) ───────────────────────────────
    critic = _read(_KNOWLEDGE_DIR / "always-load" / "critic-checklist.md")
    if critic:
        parts.append(f"\n---\n## בדיקת איכות — לפני כל תשובה\n{critic}")

    return "\n".join(parts)


def get_loaded_modules(profile: Optional[dict] = None) -> dict:
    """Return a summary of which modules would be loaded for a profile (for debugging)."""
    always = [p.name for p in _ALWAYS_LOAD if p.exists()]
    selective = [p.name for p in _resolve_profile_modules(profile or {})]
    return {
        "always_load": always,
        "selective": selective,
        "total_files": len(always) + len(selective),
    }
