"""Tests for SQLite layer."""

import gc
from pathlib import Path

import pytest

from app.database.db import VGuardDatabase


@pytest.fixture
def db(tmp_path: Path) -> VGuardDatabase:
    database = VGuardDatabase(tmp_path / "test.db")
    yield database
    del database
    gc.collect()


def test_upsert_and_get_video(db: VGuardDatabase, tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.touch()
    vid = db.upsert_video(video)
    assert vid == 1

    record = db.get_video_by_path(video)
    assert record is not None
    assert record.file_name == "video.mp4"
    assert record.scan_status == "not_scanned"


def test_settings_and_detections(db: VGuardDatabase) -> None:
    vid = db.upsert_video("C:/media/sample.mkv")

    db.set_setting("moderation_mode", "mute_audio")
    assert db.get_setting("moderation_mode") == "mute_audio"

    db.add_detection(
        vid,
        "visual",
        10.0,
        12.5,
        confidence=0.9,
        label="unsafe",
    )
    detections = db.get_detections(vid)
    assert len(detections) == 1
    assert detections[0].start_time == 10.0
    assert detections[0].enabled is True

    db.update_scan_status(vid, "complete")
    updated = db.get_video_by_id(vid)
    assert updated is not None
    assert updated.scan_status == "complete"
