"""Moderation applies to PANNs audio_event ranges."""

from pathlib import Path

from app.database.db import VGuardDatabase
from app.moderation.moderation_controller import ModerationController


def test_hide_video_mutes_audio_event_range(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "panns_mute.db")
    vid = db.upsert_video("C:/v/panns.mp4")
    db.add_detection(
        vid,
        "audio",
        10.0,
        14.0,
        label="audio_event:Screaming / Groan",
        confidence=0.8,
    )

    ctrl = ModerationController(db)
    ctrl.load(vid, "hide_video")

    action = ctrl.evaluate(12.0)
    assert action.hide_video is False
    assert action.mute_audio is True


def test_mute_audio_mode_mutes_audio_event(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "panns_mute2.db")
    vid = db.upsert_video("C:/v/panns2.mp4")
    db.add_detection(vid, "audio", 3.0, 5.0, label="audio_event:Wail, moan")

    ctrl = ModerationController(db)
    ctrl.load(vid, "mute_audio")
    assert ctrl.evaluate(4.0).mute_audio is True
