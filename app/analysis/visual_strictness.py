"""
Map UI strictness (0–100) to Open-NSFW probability thresholds.

Lower threshold = stricter (more blackouts). Calibrated from
data/evaluation visual_challenge_labels.csv and thesis runs at 0.65.

Reference scores (your evaluation set):
  ~0.04–0.06  typical safe / beach (model under-scores some policy-unsafe bikini)
  ~0.34–0.44  suggestive / swimwear / undressing-adjacent frames
  ~0.97+      explicit sexual content (m1, m2, m4)
"""

from __future__ import annotations

from dataclasses import dataclass

# Slider endpoints (strictness percent → NSFW probability cutoff)
THRESHOLD_AT_LENIENT = 0.65
THRESHOLD_AT_STRICT = 0.26
DEFAULT_STRICTNESS_PERCENT = 82


@dataclass(frozen=True)
class StrictnessPreset:
    percent: int
    threshold: float
    label: str
    description: str


PRESETS: tuple[StrictnessPreset, ...] = (
    StrictnessPreset(
        0,
        THRESHOLD_AT_LENIENT,
        "Relaxed",
        "Only very explicit scenes (fewest false blackouts)",
    ),
    StrictnessPreset(
        40,
        0.50,
        "Balanced",
        "Middle ground for mixed content",
    ),
    StrictnessPreset(
        65,
        0.38,
        "Strict",
        "Undressing / suggestive (~0.34+ model scores)",
    ),
    StrictnessPreset(
        82,
        0.32,
        "Very strict",
        "Strong policy — re-scan after changing",
    ),
    StrictnessPreset(
        100,
        THRESHOLD_AT_STRICT,
        "Maximum safety",
        "Lowest cutoff — breasts, buttocks, partial nudity if scored high",
    ),
)


def strictness_to_threshold(strictness_percent: int) -> float:
    """
    Convert slider position to NSFW threshold.

    strictness 0 = lenient (0.65), 100 = maximum safety (0.26).
    """
    pct = max(0, min(100, int(strictness_percent)))
    t = THRESHOLD_AT_LENIENT - (pct / 100.0) * (
        THRESHOLD_AT_LENIENT - THRESHOLD_AT_STRICT
    )
    return round(t, 3)


def threshold_to_strictness(threshold: float) -> int:
    """Approximate slider position from a stored threshold."""
    t = max(THRESHOLD_AT_STRICT, min(THRESHOLD_AT_LENIENT, float(threshold)))
    span = THRESHOLD_AT_LENIENT - THRESHOLD_AT_STRICT
    if span <= 0:
        return DEFAULT_STRICTNESS_PERCENT
    pct = int(round((THRESHOLD_AT_LENIENT - t) / span * 100))
    return max(0, min(100, pct))


def strictness_label(strictness_percent: int) -> str:
    pct = max(0, min(100, int(strictness_percent)))
    best = PRESETS[0]
    for preset in PRESETS:
        if abs(preset.percent - pct) <= abs(best.percent - pct):
            best = preset
    return best.label


def strictness_summary(strictness_percent: int) -> str:
    thresh = strictness_to_threshold(strictness_percent)
    label = strictness_label(strictness_percent)
    return (
        f"{label} — flags when NSFW score ≥ {thresh:.2f} "
        f"(slider {strictness_percent}%)"
    )


def resolve_visual_threshold(
    *,
    strictness_raw: str | None,
    threshold_raw: str | None,
    default_strictness: int = DEFAULT_STRICTNESS_PERCENT,
) -> float:
    """
    Prefer strictness slider if set; else legacy threshold spinbox value.
    """
    if strictness_raw is not None and str(strictness_raw).strip() != "":
        try:
            return strictness_to_threshold(int(float(strictness_raw)))
        except ValueError:
            pass
    if threshold_raw is not None:
        try:
            return float(threshold_raw)
        except ValueError:
            pass
    return strictness_to_threshold(default_strictness)
