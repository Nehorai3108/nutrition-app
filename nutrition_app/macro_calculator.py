"""
macro_calculator — protein-floor helpers for the FF_PROTEIN_FIRST_WIDGET surface.

Centralises the small amount of arithmetic the home-tab protein widget needs so
both the rendering layer and any future server-side validator share one source
of truth:

  * `effective_lbm_kg(user)`   — measured LBM if the user supplied one, else a
                                 Boer-formula fallback derived from
                                 height / weight / gender. **Never returns 0
                                 silently** — when the inputs are unusable we
                                 raise ValueError so callers must handle it.
  * `protein_floor_g(user)`    — 1.6 g protein per kg LBM, rounded to int. This
                                 is the personalized "floor" the protein ring
                                 fills toward.
  * `protein_ring_color(r)`    — maps a ratio (consumed / floor) to one of the
                                 three threshold colors:
                                    red    when ratio <  0.70
                                    yellow when 0.70 <= ratio < 0.90
                                    green  when ratio >= 0.90
  * `calorie_floor_warning_threshold(user)` — kcal/day below which the nutrition
                                 engine flags targets as unsafe. Standard
                                 threshold is 1200 kcal; when a user opts in
                                 to FF_GLP1_AWARE_TARGETS the threshold drops
                                 by GLP1_CALORIE_FLOOR_REDUCTION_KCAL.

Owner: Agent 2 (Nutrition).  No AI, no hidden heuristics.
"""

from __future__ import annotations

from typing import Optional

from nutrition_app.models.user import UserProfile
from nutrition_app.models.enums import Gender


# ── Ring color thresholds (kept as named constants so the unit test, the
#    widget rendering, and any future copy translator all share one source). ──
RING_THRESHOLD_RED: float = 0.70     # ratio < RED   → red
RING_THRESHOLD_YELLOW: float = 0.90  # RED <= ratio < YELLOW → yellow
                                     # ratio >= YELLOW → green

# Ring color hex codes — match the rest of the home-tab palette in app_user.py.
RING_COLOR_RED: str = "#f87171"
RING_COLOR_YELLOW: str = "#f59e0b"
RING_COLOR_GREEN: str = "#00d4aa"

# Protein floor coefficient — grams of protein per kilogram of lean body mass.
# Sourced from the task acceptance criteria: "1.6 g/kg lean body mass".
PROTEIN_PER_KG_LBM: float = 1.6

# GLP-1 aware protein floor (g/kg LBM) — same numeric value as the default
# today, kept as a separate named constant so future tuning of the default
# cannot silently change the GLP-1-path muscle-preservation guarantee
# documented in work order 2026-05-27_201008_sel.
PROTEIN_PER_KG_LBM_GLP1: float = 1.6

# Standard calorie-floor warning threshold (kcal/day). The nutrition
# engine flags daily targets below this value as unsafe.
STANDARD_CALORIE_FLOOR_WARNING_KCAL: float = 1200.0

# Reduction (kcal) applied to the calorie-floor warning when a user
# self-reports active GLP-1 medication AND FF_GLP1_AWARE_TARGETS is ON.
# GLP-1 patients commonly eat 200–400 kcal/day below the standard floor
# under medical supervision; we accept 200 kcal as a safe relaxation.
GLP1_CALORIE_FLOOR_REDUCTION_KCAL: float = 200.0


def _glp1_active(user: UserProfile) -> bool:
    """True iff FF_GLP1_AWARE_TARGETS is ON and user opted in to GLP-1 path.

    Imports the feature flag lazily so any failure to import (e.g. during
    a partial refactor) collapses to the safe default of OFF rather than
    raising — preserves the byte-identical-when-disabled guarantee.
    """
    try:
        from nutrition_app import feature_flags as _ff
        if not getattr(_ff, "FF_GLP1_AWARE_TARGETS", False):
            return False
    except Exception:
        return False
    return getattr(user, "glp1_medication_in_use", None) is True


def effective_lbm_kg(user: UserProfile) -> float:
    """Return the user's lean body mass in kg.

    Order of preference:
      1. `user.lean_body_mass_kg` if the user supplied a measured value (>0).
      2. Boer formula derived from height_cm, weight_kg, and gender.

    Boer (1984):
        Male:   LBM = 0.407 * W + 0.267 * H - 19.2
        Female: LBM = 0.252 * W + 0.473 * H - 48.3

    Raises ValueError if the user record lacks the inputs needed for the
    fallback (e.g. zero height/weight) — this is deliberate so a missing
    value can never collapse to a silent 0 kg LBM in the UI.
    """
    measured = getattr(user, "lean_body_mass_kg", None)
    if measured is not None and float(measured) > 0:
        return float(measured)

    w = float(getattr(user, "weight_kg", 0) or 0)
    h = float(getattr(user, "height_cm", 0) or 0)
    if w <= 0 or h <= 0:
        raise ValueError(
            "effective_lbm_kg: cannot fall back to Boer estimate — "
            "user.height_cm and user.weight_kg must both be > 0"
        )

    gender = getattr(user, "gender", None)
    gender_value = gender.value if isinstance(gender, Gender) else str(gender or "").lower()
    if gender_value == Gender.MALE.value:
        lbm = 0.407 * w + 0.267 * h - 19.2
    else:
        # Default to the female coefficients for non-binary / unspecified —
        # the lower-LBM curve avoids over-estimating the protein floor.
        lbm = 0.252 * w + 0.473 * h - 48.3

    # Boer can theoretically go negative for very short/light bodies — clamp to
    # a minimum sane value (15 kg ≈ a small child) so the protein floor never
    # collapses to ≤ 0 and the ring math stays defined.
    return max(lbm, 15.0)


def protein_floor_g(user: UserProfile) -> float:
    """Personalized daily protein floor in grams.

    When `FF_GLP1_AWARE_TARGETS` is ON AND `user.glp1_medication_in_use`
    is True, returns 1.6 g/kg LBM via `PROTEIN_PER_KG_LBM_GLP1`. Otherwise
    falls back to the default `PROTEIN_PER_KG_LBM` (also 1.6 today).
    Behavior is byte-identical whenever the flag is OFF or the field is
    False/None.
    """
    lbm = effective_lbm_kg(user)
    coeff = PROTEIN_PER_KG_LBM_GLP1 if _glp1_active(user) else PROTEIN_PER_KG_LBM
    return round(coeff * lbm, 1)


def calorie_floor_warning_threshold(user: UserProfile) -> float:
    """Return the calorie-floor warning threshold (kcal/day) for `user`.

    When `FF_GLP1_AWARE_TARGETS` is ON AND `user.glp1_medication_in_use`
    is True, the standard threshold is lowered by
    `GLP1_CALORIE_FLOOR_REDUCTION_KCAL` kcal. Otherwise the standard
    threshold is returned unchanged — preserving byte-identical
    behavior for every caller when the flag is disabled.
    """
    if _glp1_active(user):
        return STANDARD_CALORIE_FLOOR_WARNING_KCAL - GLP1_CALORIE_FLOOR_REDUCTION_KCAL
    return STANDARD_CALORIE_FLOOR_WARNING_KCAL


def protein_ring_color(ratio: float) -> str:
    """Map consumed/floor ratio → ring color hex.

    Thresholds are exact per acceptance criteria:
      ratio < 0.70                       → RED
      0.70 <= ratio < 0.90               → YELLOW
      ratio >= 0.90                      → GREEN
    """
    try:
        r = float(ratio)
    except (TypeError, ValueError):
        r = 0.0
    if r < RING_THRESHOLD_RED:
        return RING_COLOR_RED
    if r < RING_THRESHOLD_YELLOW:
        return RING_COLOR_YELLOW
    return RING_COLOR_GREEN


def protein_ratio(consumed_g: float, user: UserProfile) -> float:
    """Convenience: ratio of `consumed_g` against the personalized floor."""
    floor = protein_floor_g(user)
    if floor <= 0:
        return 0.0
    return float(consumed_g) / floor
