"""Tests for incremental detection merge."""

from pathlib import Path

from app.analysis.detection_builder import apply_chunk_visual_detections
from app.analysis.visual_detector import FramePrediction
from app.database.db import VGuardDatabase


def test_apply_chunk_merges_adjacent_ranges(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "merge.db")
    vid = db.upsert_video("C:/v/merge.mp4", duration=100.0)
    preds = [
        FramePrediction(10.0, 0.9, True, "unsafe_visual"),
        FramePrediction(12.0, 0.85, True, "unsafe_visual"),
    ]
    count = apply_chunk_visual_detections(
        db, vid, preds, fps=24.0, sample_interval_sec=2.0, video_duration_sec=100.0
    )
    assert count == 1
    more = [
        FramePrediction(14.0, 0.88, True, "unsafe_visual"),
    ]
    count2 = apply_chunk_visual_detections(
        db, vid, more, fps=24.0, sample_interval_sec=2.0, video_duration_sec=100.0
    )
    assert count2 >= 1
    dets = db.get_detections(vid, detection_type="visual")
    assert len(dets) >= 1
