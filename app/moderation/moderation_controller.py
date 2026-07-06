"""Apply moderation actions during playback based on detection ranges."""

from __future__ import annotations

from dataclasses import dataclass

from app.database.db import VGuardDatabase
from app.database.models import DetectionRecord
from app.moderation.timestamp_manager import TimestampRange, range_contains_playback_time


@dataclass(frozen=True)
class ModerationAction:
    """Actions to apply for the current playback instant."""

    mute_audio: bool = False
    hide_video: bool = False
    skip_to_sec: float | None = None


class ModerationController:
    """
    Compare playback time with saved detection ranges and return actions.

    Modes (from settings):
      - none
      - mute_audio
      - hide_video
      - hide_and_mute
      - skip_scene
    """

    def __init__(self, database: VGuardDatabase) -> None:
        self._db = database
        self._ranges: list[TimestampRange] = []
        self._mode = "none"
        self._video_id: int | None = None
        self._last_skip_end: float = -1.0

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_active(self) -> bool:
        return self._mode != "none" and bool(self._ranges)

    def load(self, video_id: int, mode: str) -> None:
        self._video_id = video_id
        self._mode = mode if mode else "none"
        self._last_skip_end = -1.0
        self._ranges = []

        if self._mode == "none":
            return

        detections = self._db.get_detections(video_id, enabled_only=True)
        for det in detections:
            self._ranges.append(
                TimestampRange(
                    start_time=det.start_time,
                    end_time=det.end_time,
                    confidence=det.confidence or 0.0,
                    label=det.label or det.detection_type,
                )
            )
        self._ranges.sort(key=lambda r: r.start_time)

    def reload_detections(self) -> None:
        if self._video_id is not None:
            self.load(self._video_id, self._mode)

    def clear(self) -> None:
        self._ranges = []
        self._mode = "none"
        self._video_id = None
        self._last_skip_end = -1.0

    def active_range_at(self, time_sec: float) -> TimestampRange | None:
        for r in self._ranges:
            if range_contains_playback_time(time_sec, r):
                return r
        return None

    def evaluate(self, time_sec: float) -> ModerationAction:
        """Return moderation action for current playback time (seconds)."""
        if self._mode == "none":
            return ModerationAction()

        active = self.active_range_at(time_sec)
        if active is None:
            return ModerationAction()

        if self._mode == "mute_audio":
            return ModerationAction(mute_audio=True)

        if self._mode == "hide_video":
            # Blackout only visual NSFW ranges; still mute keywords + explicit audio.
            return ModerationAction(
                hide_video=_is_visual_detection_range(active),
                mute_audio=_should_mute_audio_in_hide_mode(active),
            )

        if self._mode == "hide_and_mute":
            return ModerationAction(mute_audio=True, hide_video=True)

        if self._mode == "skip_scene":
            # Skip once per range (avoid seek loop)
            if time_sec < self._last_skip_end - 0.5:
                return ModerationAction()
            if active.end_time > time_sec + 0.1:
                self._last_skip_end = active.end_time
                return ModerationAction(skip_to_sec=active.end_time + 0.05)
            return ModerationAction()

        return ModerationAction()


def _is_visual_detection_range(range_: TimestampRange) -> bool:
    """True when the active range came from the visual NSFW pipeline."""
    label = (range_.label or "").lower()
    if label.startswith("unsafe_audio") or label.startswith("audio_event"):
        return False
    return (
        label.startswith("unsafe_visual")
        or label == "visual"
        or label == "unsafe"
    )


def _is_audio_moderation_range(range_: TimestampRange) -> bool:
    """Keyword profanity or explicit-sound CNN ranges."""
    label = (range_.label or "").lower()
    return label.startswith("unsafe_audio") or label.startswith("audio_event")


def _should_mute_audio_in_hide_mode(range_: TimestampRange) -> bool:
    return _is_visual_detection_range(range_) or _is_audio_moderation_range(range_)
