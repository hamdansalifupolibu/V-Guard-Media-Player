"""Tests for progressive scan helpers."""

from pathlib import Path

from app.analysis.detection_builder import rebuild_visual_detections
from app.database.db import VGuardDatabase


def test_append_predictions_and_rebuild_ranges(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "prog.db")
    vid = db.upsert_video("C:/v/chunk.mp4", duration=60.0)
    db.append_frame_predictions(
        vid,
        [
            {"timestamp_sec": 10.0, "nsfw_confidence": 0.9, "is_flagged": True},
            {"timestamp_sec": 12.0, "nsfw_confidence": 0.85, "is_flagged": True},
        ],
        threshold=0.65,
    )
    count = rebuild_visual_detections(
        db, vid, fps=24.0, sample_interval_sec=2.0, video_duration_sec=60.0
    )
    assert count == 1
    detections = db.get_detections(vid, detection_type="visual")
    assert len(detections) == 1
    assert detections[0].start_time < 10.0


def test_scan_progress_persistence(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "progress.db")
    vid = db.upsert_video("C:/v/p.mp4")
    db.update_scan_progress(vid, 30.0)
    record = db.get_video_by_id(vid)
    assert record is not None
    assert record.scan_progress_sec == 30.0
