"""Tests for explicit-sound CNN detector."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.analysis.explicit_audio_detector import (
    EXPLICIT_AUDIO_THRESHOLD,
    ExplicitAudioDetector,
    _merge_hits,
    _WindowHit,
    events_to_timestamp_ranges,
)
from app.config import EXPLICIT_AUDIO_MODEL_PATH


def test_merge_hits():
    hits = [
        _WindowHit(0.0, 2.0, 0.8),
        _WindowHit(2.0, 4.0, 0.7),
        _WindowHit(10.0, 12.0, 0.6),
    ]
    merged = _merge_hits(hits, gap_sec=1.0)
    assert len(merged) == 2
    assert merged[0].end_time == 4.0


def test_events_to_timestamp_ranges_prefix():
    events = [
        {
            "start_time": 5.0,
            "end_time": 7.0,
            "confidence": 0.9,
            "label": "sexual vocal sound (moan-like)",
        }
    ]
    ranges = events_to_timestamp_ranges(events, video_duration_sec=60.0)
    assert len(ranges) == 1
    assert ranges[0].label.startswith("audio_event:")


def test_analyze_missing_file():
    det = ExplicitAudioDetector()
    assert det.analyze_audio("missing.wav") == []


@patch("app.analysis.audio_pipeline.ExplicitAudioDetector")
@patch("app.analysis.audio_pipeline.SpeechDetector")
@patch("app.analysis.audio_pipeline.AudioExtractor")
def test_scan_pipeline_uses_explicit_detector(
    mock_extractor_cls: MagicMock,
    mock_speech_cls: MagicMock,
    mock_detector_cls: MagicMock,
    tmp_path: Path,
) -> None:
    from app.analysis.video_scanner import VideoScanner
    from app.database.db import VGuardDatabase

    db = VGuardDatabase(tmp_path / "exp.db")
    vid = db.upsert_video(str(tmp_path / "v.mp4"))
    db.update_duration(vid, 20.0)
    wav = tmp_path / "v_1_audio.wav"
    wav.write_bytes(b"x")
    mock_extractor_cls.is_ffmpeg_available.return_value = True
    mock_extractor_cls.return_value.extract.return_value = wav
    mock_speech_cls.is_model_available.return_value = False

    detector = MagicMock()
    detector.is_ready = True
    detector.load_error = None
    detector.analyze_audio.return_value = [
        {
            "detection_type": "audio_event",
            "start_time": 3.0,
            "end_time": 5.0,
            "label": "sexual vocal sound (moan-like)",
            "confidence": 0.88,
            "source": "explicit_audio_cnn",
        }
    ]
    mock_detector_cls.return_value = detector

    scanner = VideoScanner(db)
    count, _warn = scanner._run_audio_pipeline(vid, tmp_path / "v.mp4")
    assert count >= 1
    rows = db.get_detections(vid, detection_type="audio")
    assert any("audio_event" in (r.label or "") for r in rows)


@pytest.mark.slow
def test_analyze_real_audio_if_model_and_file():
    if not EXPLICIT_AUDIO_MODEL_PATH.is_file():
        pytest.skip("Train model: python scripts/download_explicit_audio_model.py")
    audio_path = os.environ.get("AUDIO_TEST_PATH", "").strip()
    if not audio_path:
        pytest.skip("Set AUDIO_TEST_PATH to a WAV file")
    det = ExplicitAudioDetector()
    assert det.is_ready
    results = det.analyze_audio(audio_path)
    assert isinstance(results, list)
    for row in results:
        assert row["confidence"] >= EXPLICIT_AUDIO_THRESHOLD


def _run_cli() -> int:
    if len(sys.argv) < 2:
        print("Usage: python tests/test_explicit_audio_detector.py <audio.wav>")
        return 1
    if not EXPLICIT_AUDIO_MODEL_PATH.is_file():
        print("Model missing. Run: python scripts/download_explicit_audio_model.py")
        return 1
    det = ExplicitAudioDetector()
    results = det.analyze_audio(sys.argv[1])
    for row in results:
        print(
            f"{row['start_time']:.1f}s–{row['end_time']:.1f}s  "
            f"conf={row['confidence']:.2f}  {row['label']}"
        )
    if not results:
        print("No explicit sounds detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_cli())
