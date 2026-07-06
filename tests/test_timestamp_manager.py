"""Tests for grouping flagged frames into ranges."""

from app.moderation.timestamp_manager import (
    frame_padding_sec,
    group_flagged_frames,
    scene_padding_sec,
)


def test_scene_padding_lead_two_sec_trail_one_sec():
    lead, trail = scene_padding_sec(24.0)
    assert lead >= 2.0
    assert trail >= 1.0
    assert trail < lead


def test_group_adjacent_frames_with_scene_padding():
    flagged = [
        (10.0, 0.9, "unsafe_visual"),
        (12.0, 0.85, "unsafe_visual"),
        (14.0, 0.88, "unsafe_visual"),
    ]
    lead, trail = scene_padding_sec(24.0)
    ranges = group_flagged_frames(
        flagged, sample_interval_sec=1.0, fps=24.0, video_duration_sec=120.0
    )
    assert len(ranges) == 1
    assert ranges[0].start_time == round(10.0 - lead, 3)
    assert ranges[0].end_time == round(14.0 + 1.0 + trail, 3)
    assert ranges[0].confidence == 0.9


def test_group_separate_segments():
    flagged = [
        (10.0, 0.9, "unsafe_visual"),
        (12.0, 0.8, "unsafe_visual"),
        (40.0, 0.7, "unsafe_visual"),
    ]
    lead, _ = scene_padding_sec(25.0)
    ranges = group_flagged_frames(
        flagged, sample_interval_sec=1.0, max_gap_sec=3.0, fps=25.0
    )
    assert len(ranges) == 2
    assert ranges[0].start_time == round(10.0 - lead, 3)
    assert ranges[1].start_time == round(40.0 - lead, 3)


def test_empty_flagged_list():
    assert group_flagged_frames([], sample_interval_sec=1.0) == []


def test_frame_padding_seconds():
    lead, trail = frame_padding_sec(24.0, lead_frames=2, trail_frames=2)
    assert abs(lead - 2 / 24.0) < 1e-9
    assert abs(trail - 2 / 24.0) < 1e-9
