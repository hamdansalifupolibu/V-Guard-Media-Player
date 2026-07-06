"""Tests for playback moderation controller."""

from pathlib import Path

from app.database.db import VGuardDatabase
from app.moderation.moderation_controller import ModerationController


def test_mute_in_flagged_range(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "mod.db")
    vid = db.upsert_video("C:/v/test.mp4")
    db.add_detection(vid, "visual", 10.0, 12.0, label="unsafe")
    db.add_detection(vid, "audio", 20.0, 21.0, label="unsafe_audio:damn")

    ctrl = ModerationController(db)
    ctrl.load(vid, "mute_audio")

    assert ctrl.evaluate(5.0).mute_audio is False
    assert ctrl.evaluate(11.0).mute_audio is True
    assert ctrl.evaluate(20.5).mute_audio is True


def test_skip_seeks_to_end(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "skip.db")
    vid = db.upsert_video("C:/v/skip.mp4")
    db.add_detection(vid, "visual", 5.0, 8.0)

    ctrl = ModerationController(db)
    ctrl.load(vid, "skip_scene")
    action = ctrl.evaluate(6.0)
    assert action.skip_to_sec is not None
    assert action.skip_to_sec >= 8.0


def test_hide_video_mutes_during_visual_scene(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "hide.db")
    vid = db.upsert_video("C:/v/hide.mp4")
    db.add_detection(vid, "visual", 10.0, 20.0, label="unsafe_visual")

    ctrl = ModerationController(db)
    ctrl.load(vid, "hide_video")
    action = ctrl.evaluate(15.0)
    assert action.hide_video is True
    assert action.mute_audio is True


def test_hide_video_audio_keyword_mutes_without_blackout(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "audioonly.db")
    vid = db.upsert_video("C:/v/a.mp4")
    db.add_detection(vid, "audio", 5.0, 8.0, label="unsafe_audio:damn")

    ctrl = ModerationController(db)
    ctrl.load(vid, "hide_video")
    action = ctrl.evaluate(6.0)
    assert action.hide_video is False
    assert action.mute_audio is True
