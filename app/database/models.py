"""Data models for database records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ScanStatus = Literal[
    "not_scanned",
    "scanning",
    "frames_sampled",
    "complete",
    "failed",
]

DetectionType = Literal["visual", "audio"]


@dataclass(frozen=True)
class VideoRecord:
    id: int
    file_path: str
    file_name: str
    duration: float | None
    scan_status: str
    scan_progress_sec: float
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class DetectionRecord:
    id: int
    video_id: int
    detection_type: str
    start_time: float
    end_time: float
    confidence: float | None
    label: str | None
    enabled: bool
    created_at: str


@dataclass(frozen=True)
class DownloadRecord:
    id: int
    url: str
    file_path: str | None
    status: str
    created_at: str
