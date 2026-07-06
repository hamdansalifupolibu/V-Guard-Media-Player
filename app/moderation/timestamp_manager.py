"""Group per-frame flags into contiguous moderation timestamp ranges."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import (
    DEFAULT_VIDEO_FPS,
    MODERATION_PLAYBACK_LEAD_SEC,
    MODERATION_PLAYBACK_TRAIL_SEC,
    VISUAL_MODERATION_LEAD_FRAMES,
    VISUAL_MODERATION_LEAD_SEC,
    VISUAL_MODERATION_TRAIL_FRAMES,
    VISUAL_MODERATION_TRAIL_SEC,
)


@dataclass(frozen=True)
class TimestampRange:
    """A continuous time range for playback moderation."""

    start_time: float
    end_time: float
    confidence: float
    label: str


def frame_padding_sec(
    fps: float,
    *,
    lead_frames: int = VISUAL_MODERATION_LEAD_FRAMES,
    trail_frames: int = VISUAL_MODERATION_TRAIL_FRAMES,
) -> tuple[float, float]:
    """Seconds equivalent to N frames at the given FPS."""
    safe_fps = fps if fps > 1.0 else DEFAULT_VIDEO_FPS
    return lead_frames / safe_fps, trail_frames / safe_fps


def scene_padding_sec(
    fps: float,
    *,
    lead_sec: float = VISUAL_MODERATION_LEAD_SEC,
    trail_sec: float = VISUAL_MODERATION_TRAIL_SEC,
    lead_frames: int = VISUAL_MODERATION_LEAD_FRAMES,
    trail_frames: int = VISUAL_MODERATION_TRAIL_FRAMES,
) -> tuple[float, float]:
    """
    Blackout/mute padding before and after a scene.

    Uses the **larger** of fixed seconds or frame-based padding so short scenes
    are never exposed at the edges because of coarse frame sampling.
    """
    frame_lead, frame_trail = frame_padding_sec(
        fps, lead_frames=lead_frames, trail_frames=trail_frames
    )
    return max(lead_sec, frame_lead), max(trail_sec, frame_trail)


def default_merge_gap_sec(sample_interval_sec: float) -> float:
    """Bridge gaps between sampled frames so one scene becomes one range."""
    return max(sample_interval_sec * 2.5, VISUAL_MODERATION_LEAD_SEC * 2.0)


def group_flagged_frames(
    flagged: list[tuple[float, float, str]],
    *,
    sample_interval_sec: float,
    max_gap_sec: float | None = None,
    fps: float = DEFAULT_VIDEO_FPS,
    lead_sec: float = VISUAL_MODERATION_LEAD_SEC,
    trail_sec: float = VISUAL_MODERATION_TRAIL_SEC,
    lead_frames: int = VISUAL_MODERATION_LEAD_FRAMES,
    trail_frames: int = VISUAL_MODERATION_TRAIL_FRAMES,
    video_duration_sec: float | None = None,
) -> list[TimestampRange]:
    """
    Merge nearby flagged frames into ranges with full-scene padding.

    Each item is (timestamp_sec, confidence, label).
    """
    if not flagged:
        return []

    gap = max_gap_sec if max_gap_sec is not None else default_merge_gap_sec(
        sample_interval_sec
    )
    flagged = sorted(flagged, key=lambda item: item[0])

    ranges: list[TimestampRange] = []
    start, end, peak_conf, label = flagged[0][0], flagged[0][0], flagged[0][1], flagged[0][2]

    for timestamp, confidence, item_label in flagged[1:]:
        if timestamp - end <= gap:
            end = timestamp
            peak_conf = max(peak_conf, confidence)
        else:
            ranges.append(
                _make_range(
                    start,
                    end,
                    peak_conf,
                    label,
                    sample_interval_sec,
                    fps=fps,
                    lead_sec=lead_sec,
                    trail_sec=trail_sec,
                    lead_frames=lead_frames,
                    trail_frames=trail_frames,
                    video_duration_sec=video_duration_sec,
                )
            )
            start, end, peak_conf, label = timestamp, timestamp, confidence, item_label

    ranges.append(
        _make_range(
            start,
            end,
            peak_conf,
            label,
            sample_interval_sec,
            fps=fps,
            lead_sec=lead_sec,
            trail_sec=trail_sec,
            lead_frames=lead_frames,
            trail_frames=trail_frames,
            video_duration_sec=video_duration_sec,
        )
    )
    return ranges


def _make_range(
    start: float,
    end: float,
    confidence: float,
    label: str,
    sample_interval_sec: float,
    *,
    fps: float = DEFAULT_VIDEO_FPS,
    lead_sec: float = VISUAL_MODERATION_LEAD_SEC,
    trail_sec: float = VISUAL_MODERATION_TRAIL_SEC,
    lead_frames: int = VISUAL_MODERATION_LEAD_FRAMES,
    trail_frames: int = VISUAL_MODERATION_TRAIL_FRAMES,
    video_duration_sec: float | None = None,
) -> TimestampRange:
    lead_pad, trail_pad = scene_padding_sec(
        fps,
        lead_sec=lead_sec,
        trail_sec=trail_sec,
        lead_frames=lead_frames,
        trail_frames=trail_frames,
    )
    # First flagged sample time minus lead; last sample window plus trail
    range_start = max(0.0, start - lead_pad)
    range_end = end + sample_interval_sec + trail_pad
    if video_duration_sec is not None and video_duration_sec > 0:
        range_end = min(range_end, video_duration_sec)
    return TimestampRange(
        start_time=round(range_start, 3),
        end_time=round(range_end, 3),
        confidence=round(confidence, 4),
        label=label,
    )


def range_contains_playback_time(
    time_sec: float,
    range_: TimestampRange,
    *,
    playback_lead_sec: float = MODERATION_PLAYBACK_LEAD_SEC,
    playback_trail_sec: float = MODERATION_PLAYBACK_TRAIL_SEC,
) -> bool:
    """True if playback time falls inside a range including tick safety margins."""
    return (
        range_.start_time - playback_lead_sec
        <= time_sec
        <= range_.end_time + playback_trail_sec
    )
