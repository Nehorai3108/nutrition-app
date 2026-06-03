"""
Unit test — protein ring color thresholds.

Pins the FF_PROTEIN_FIRST_WIDGET ring thresholds so future refactors of
nutrition_app.macro_calculator can't silently move the color cutoffs.

Acceptance criteria (from work order 2026-05-27_191208_sel):
    ratio < 0.70             → red
    0.70 <= ratio < 0.90     → yellow
    ratio >= 0.90            → green
"""

import pytest

from nutrition_app.macro_calculator import (
    RING_COLOR_GREEN,
    RING_COLOR_RED,
    RING_COLOR_YELLOW,
    RING_THRESHOLD_RED,
    RING_THRESHOLD_YELLOW,
    protein_ring_color,
)


def test_named_threshold_constants_match_spec():
    # The two cutoffs come straight from the acceptance criteria —
    # changing these constants requires bumping the work order too.
    assert RING_THRESHOLD_RED == pytest.approx(0.70)
    assert RING_THRESHOLD_YELLOW == pytest.approx(0.90)


@pytest.mark.parametrize(
    "ratio,expected_color",
    [
        # below red threshold
        (0.0, RING_COLOR_RED),
        (0.50, RING_COLOR_RED),
        (0.6999, RING_COLOR_RED),
        # red→yellow boundary is exact at 0.70
        (0.70, RING_COLOR_YELLOW),
        (0.80, RING_COLOR_YELLOW),
        (0.8999, RING_COLOR_YELLOW),
        # yellow→green boundary is exact at 0.90
        (0.90, RING_COLOR_GREEN),
        (1.00, RING_COLOR_GREEN),
        (1.50, RING_COLOR_GREEN),
    ],
)
def test_ring_color_thresholds(ratio, expected_color):
    assert protein_ring_color(ratio) == expected_color


def test_invalid_ratio_falls_back_to_red():
    # A non-numeric input must still produce a defined color (red), never
    # raise — the home-tab render path can't tolerate exceptions.
    assert protein_ring_color("not a number") == RING_COLOR_RED
    assert protein_ring_color(None) == RING_COLOR_RED
