"""Tests for visual strictness → threshold mapping."""

from app.analysis.visual_strictness import (
    DEFAULT_STRICTNESS_PERCENT,
    THRESHOLD_AT_LENIENT,
    THRESHOLD_AT_STRICT,
    resolve_visual_threshold,
    strictness_to_threshold,
    threshold_to_strictness,
)
from app.config import DEFAULT_VISUAL_STRICTNESS_PERCENT


def test_lenient_matches_legacy_default():
    assert strictness_to_threshold(0) == THRESHOLD_AT_LENIENT


def test_maximum_safety_threshold():
    assert strictness_to_threshold(100) == THRESHOLD_AT_STRICT


def test_default_strictness_catches_suggestive_band():
    t = strictness_to_threshold(DEFAULT_STRICTNESS_PERCENT)
    assert t <= 0.35
    assert t >= 0.28


def test_threshold_roundtrip():
    for pct in (0, 40, 82, 100):
        back = threshold_to_strictness(strictness_to_threshold(pct))
        assert abs(back - pct) <= 1


def test_resolve_prefers_strictness_setting():
    assert resolve_visual_threshold(
        strictness_raw="100",
        threshold_raw="0.65",
    ) == THRESHOLD_AT_STRICT


def test_resolve_falls_back_to_threshold():
    assert resolve_visual_threshold(
        strictness_raw=None,
        threshold_raw="0.50",
    ) == 0.50


def test_resolve_default_when_empty():
    t = resolve_visual_threshold(strictness_raw=None, threshold_raw=None)
    assert t == strictness_to_threshold(DEFAULT_STRICTNESS_PERCENT)
