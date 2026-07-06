"""Rebuild moderation ranges from stored frame predictions."""

from __future__ import annotations

from app.analysis.visual_detector import FramePrediction, UNSAFE_LABEL
from app.database.db import VGuardDatabase
from app.database.models import DetectionRecord
from app.moderation.timestamp_manager import TimestampRange, group_flagged_frames


def _prediction_flagged(pred: FramePrediction) -> tuple[float, float, str] | None:
    if not pred.is_flagged:
        return None
    return (pred.timestamp_sec, pred.confidence, pred.label)


def merge_detection_ranges(
    existing: list[DetectionRecord],
    new_ranges: list[TimestampRange],
    *,
    merge_gap_sec: float = 3.0,
) -> list[TimestampRange]:
    """Merge DB detections with new chunk ranges (sorted, adjacent join)."""
    combined: list[TimestampRange] = []
    for det in existing:
        combined.append(
            TimestampRange(
                start_time=det.start_time,
                end_time=det.end_time,
                confidence=det.confidence or 0.0,
                label=det.label or UNSAFE_LABEL,
            )
        )
    combined.extend(new_ranges)
    if not combined:
        return []

    combined.sort(key=lambda r: r.start_time)
    merged: list[TimestampRange] = [combined[0]]
    for current in combined[1:]:
        prev = merged[-1]
        if current.start_time <= prev.end_time + merge_gap_sec:
            merged[-1] = TimestampRange(
                start_time=prev.start_time,
                end_time=max(prev.end_time, current.end_time),
                confidence=max(prev.confidence, current.confidence),
                label=prev.label,
            )
        else:
            merged.append(current)
    return merged


def apply_chunk_visual_detections(
    database: VGuardDatabase,
    video_id: int,
    chunk_predictions: list[FramePrediction],
    *,
    fps: float,
    sample_interval_sec: float,
    video_duration_sec: float | None = None,
) -> int:
    """
    Append visual ranges from one scan chunk without reloading all frame rows.

    Much faster than rebuild_visual_detections() on every chunk for long videos.
    """
    flagged = [
        item
        for pred in chunk_predictions
        if (item := _prediction_flagged(pred)) is not None
    ]
    chunk_ranges = group_flagged_frames(
        flagged,
        sample_interval_sec=sample_interval_sec,
        fps=fps,
        video_duration_sec=video_duration_sec,
    )
    if not chunk_ranges and not chunk_predictions:
        return len(database.get_detections(video_id, detection_type="visual"))

    existing = database.get_detections(video_id, detection_type="visual")
    merged = merge_detection_ranges(
        existing,
        chunk_ranges,
        merge_gap_sec=sample_interval_sec * 2.5,
    )
    database.clear_detections(video_id, "visual")
    for time_range in merged:
        database.add_detection(
            video_id,
            "visual",
            time_range.start_time,
            time_range.end_time,
            confidence=time_range.confidence,
            label=time_range.label,
        )
    return len(merged)


def rebuild_visual_detections(
    database: VGuardDatabase,
    video_id: int,
    *,
    fps: float,
    sample_interval_sec: float,
    video_duration_sec: float | None = None,
) -> int:
    """Regroup all frame predictions into visual detection rows (final pass)."""
    predictions = database.get_frame_predictions(video_id)
    flagged = [
        (
            item["timestamp_sec"],
            item["nsfw_confidence"],
            UNSAFE_LABEL,
        )
        for item in predictions
        if item["is_flagged"]
    ]
    ranges = group_flagged_frames(
        flagged,
        sample_interval_sec=sample_interval_sec,
        fps=fps,
        video_duration_sec=video_duration_sec,
    )
    database.clear_detections(video_id, "visual")
    for time_range in ranges:
        database.add_detection(
            video_id,
            "visual",
            time_range.start_time,
            time_range.end_time,
            confidence=time_range.confidence,
            label=time_range.label,
        )
    return len(ranges)
