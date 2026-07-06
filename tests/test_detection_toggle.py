"""Tests for enabling/disabling detections (Stage 10)."""

from pathlib import Path

from app.database.db import VGuardDatabase


def test_detection_enable_disable(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "toggle.db")
    vid = db.upsert_video("C:/v/toggle.mp4")
    d1 = db.add_detection(vid, "visual", 1.0, 3.0, label="unsafe")
    d2 = db.add_detection(vid, "audio", 5.0, 6.0, label="unsafe_audio:damn")

    all_det = db.get_detections(vid)
    assert len(all_det) == 2
    assert all(d.enabled for d in all_det)

    db.set_detection_enabled(d1, False)
    enabled = db.get_detections(vid, enabled_only=True)
    assert len(enabled) == 1
    assert enabled[0].id == d2

    db.set_detection_enabled(d1, True)
    assert len(db.get_detections(vid, enabled_only=True)) == 2
