"""Tests for visual detector (mock backend, no ONNX required)."""

from __future__ import annotations

import numpy as np
import pytest

from app.analysis.visual_detector import (
    FramePrediction,
    VisualDetector,
    _ScoringBackend,
)
from app.moderation.timestamp_manager import group_flagged_frames


class _MockBackend(_ScoringBackend):
    """Flags frames where mean pixel value exceeds a threshold."""

    def __init__(self, cutoff: float = 100.0) -> None:
        self.cutoff = cutoff

    def score_nsfw(self, frame_bgr: np.ndarray) -> float:
        mean_val = float(np.mean(frame_bgr))
        return 0.9 if mean_val > self.cutoff else 0.1


def test_predict_frame_flagging():
    detector = VisualDetector(threshold=0.65, backend=_MockBackend(cutoff=50))
    dark = np.zeros((100, 100, 3), dtype=np.uint8)
    bright = np.full((100, 100, 3), 200, dtype=np.uint8)

    safe = detector.predict_frame(dark, 0.0)
    unsafe = detector.predict_frame(bright, 2.0)

    assert safe.is_flagged is False
    assert unsafe.is_flagged is True
    assert unsafe.confidence == 0.9


def test_build_timestamp_ranges_from_predictions():
    predictions = [
        FramePrediction(10.0, 0.9, True, "unsafe_visual"),
        FramePrediction(12.0, 0.8, True, "unsafe_visual"),
        FramePrediction(20.0, 0.1, False, "safe"),
    ]
    flagged = [
        (p.timestamp_sec, p.confidence, p.label)
        for p in predictions
        if p.is_flagged
    ]
    ranges = group_flagged_frames(flagged, sample_interval_sec=2.0)
    assert len(ranges) == 1
    # 10s flag minus 2s visual lead padding
    assert ranges[0].start_time == 8.0
    assert ranges[0].end_time == 15.0


@pytest.mark.skipif(
    not VisualDetector.is_model_available(),
    reason="ONNX model not downloaded",
)
def test_onnx_model_loads():
    detector = VisualDetector(threshold=0.99)
    frame = np.zeros((224, 224, 3), dtype=np.uint8)
    pred = detector.predict_frame(frame, 0.0)
    assert 0.0 <= pred.confidence <= 1.0
