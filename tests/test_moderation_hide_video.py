"""Blackout range timing with frame lead/trail."""

from pathlib import Path

from app.database.db import VGuardDatabase
from app.moderation.moderation_controller import ModerationController


def test_hide_video_starts_before_flagged_time(tmp_path: Path) -> None:
    db = VGuardDatabase(tmp_path / "hide.db")
    vid = db.upsert_video("C:/v/hide.mp4")
    # Range already includes 2-frame lead at 24fps (~0.083s before t=10)
    db.add_detection(vid, "visual", 8.0, 18.0, label="unsafe")

    ctrl = ModerationController(db)
    ctrl.load(vid, "hide_video")

    assert ctrl.evaluate(8.0).hide_video is True
    assert ctrl.evaluate(7.7).hide_video is False
    assert ctrl.evaluate(11.0).hide_video is True
    assert ctrl.evaluate(18.3).hide_video is False
