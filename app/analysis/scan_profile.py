"""Adaptive scan settings from video duration (speed vs coverage)."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import (
    FRAME_SAMPLE_INTERVAL_SEC,
    SCAN_AUDIO_MAX_DURATION_SEC,
    SCAN_CHUNK_DURATION_SEC,
    SCAN_FORCE_AUDIO_ON_LONG_VIDEOS,
    SCAN_LONG_VIDEO_CHUNK_SEC,
    SCAN_VISUAL_BATCH_SIZE,
)


@dataclass(frozen=True)
class ScanProfile:
    """Effective parameters for one scan run."""

    duration_sec: float
    sample_interval_sec: float
    chunk_duration_sec: float
    visual_batch_size: int
    run_audio: bool
    audio_skip_reason: str
    long_form: bool
    estimated_frame_samples: int


def build_scan_profile(
    duration_sec: float,
    *,
    user_interval_sec: float,
    user_chunk_sec: float,
    audio_enabled: bool,
    force_audio_long: bool | None = None,
) -> ScanProfile:
    """
    Scale interval and chunk size for TV episodes / films so scans stay responsive.

    Short clips keep the user's frame interval. Longer files use a coarser interval
    automatically (still overridable via Settings).
    """
    duration_sec = max(0.0, duration_sec)
    user_interval = max(0.5, user_interval_sec)
    user_chunk = max(10.0, user_chunk_sec)

    long_form = duration_sec >= 900.0  # 15+ minutes

    if duration_sec >= 3600.0:
        auto_interval = 4.0
    elif duration_sec >= 1800.0:
        auto_interval = 3.0
    elif duration_sec >= 900.0:
        auto_interval = 2.0
    else:
        auto_interval = user_interval

    interval = max(user_interval, auto_interval) if long_form else user_interval

    if duration_sec >= 2700.0:
        chunk = max(user_chunk, 90.0)
    elif long_form:
        chunk = max(user_chunk, SCAN_LONG_VIDEO_CHUNK_SEC)
    else:
        chunk = user_chunk

    force_long = (
        force_audio_long
        if force_audio_long is not None
        else SCAN_FORCE_AUDIO_ON_LONG_VIDEOS
    )
    run_audio = audio_enabled
    audio_skip = ""
    if audio_enabled and duration_sec > SCAN_AUDIO_MAX_DURATION_SEC and not force_long:
        run_audio = False
        audio_skip = (
            f"Audio keyword scan skipped (video is {duration_sec / 60:.0f} min; "
            f"limit {SCAN_AUDIO_MAX_DURATION_SEC / 60:.0f} min for speed). "
            "Enable “Audio on long videos” in Settings or use Hide+mute on visual scenes."
        )

    est_frames = int(duration_sec / interval) + 1 if duration_sec > 0 else 0

    return ScanProfile(
        duration_sec=duration_sec,
        sample_interval_sec=interval,
        chunk_duration_sec=chunk,
        visual_batch_size=SCAN_VISUAL_BATCH_SIZE,
        run_audio=run_audio,
        audio_skip_reason=audio_skip,
        long_form=long_form,
        estimated_frame_samples=est_frames,
    )
