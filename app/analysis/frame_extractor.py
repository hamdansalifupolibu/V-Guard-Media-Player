"""Sample frames from video files using OpenCV."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from app.config import FRAME_SAMPLE_INTERVAL_SEC


@dataclass(frozen=True)
class SampledFrame:
    """A frame captured at a specific timestamp."""

    timestamp_sec: float
    frame_index: int
    image_bgr: object  # numpy ndarray; typed loosely to avoid hard numpy import in stubs


class FrameExtractor:
    """Extract frames at fixed time intervals for visual analysis."""

    def __init__(self, interval_sec: float = FRAME_SAMPLE_INTERVAL_SEC) -> None:
        self.interval_sec = max(0.5, interval_sec)

    def probe(self, file_path: str | Path) -> dict:
        """Return duration, fps, frame count without extracting frames."""
        path = Path(file_path)
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {path}")
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration = frame_count / fps if fps > 0 else 0.0
            return {
                "duration_sec": duration,
                "fps": fps,
                "frame_count": frame_count,
            }
        finally:
            cap.release()

    @staticmethod
    def open_capture(file_path: str | Path) -> cv2.VideoCapture:
        """Open once per scan; reuse across chunks for faster sequential reads."""
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {file_path}")
        return cap

    @staticmethod
    def close_capture(cap: cv2.VideoCapture | None) -> None:
        if cap is not None:
            cap.release()

    def extract(self, file_path: str | Path) -> list[SampledFrame]:
        """Sample one frame every `interval_sec` across the full video."""
        meta = self.probe(file_path)
        duration = float(meta.get("duration_sec") or 0.0)
        if duration <= 0:
            return []
        cap = self.open_capture(file_path)
        try:
            return self.extract_range_from_capture(
                cap, 0.0, duration, float(meta.get("fps") or 0.0)
            )
        finally:
            self.close_capture(cap)

    def extract_range(
        self,
        file_path: str | Path,
        start_sec: float,
        end_sec: float,
    ) -> list[SampledFrame]:
        """Sample frames in [start_sec, end_sec] (opens a new capture)."""
        cap = self.open_capture(file_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            return self.extract_range_from_capture(cap, start_sec, end_sec, float(fps))
        finally:
            self.close_capture(cap)

    def extract_range_from_capture(
        self,
        cap: cv2.VideoCapture,
        start_sec: float,
        end_sec: float,
        fps: float,
    ) -> list[SampledFrame]:
        """
        Fast path: one seek to chunk start, then sequential read/grab.

        Avoids per-frame cap.set() which is very slow on long MKV/MP4 files.
        """
        start_sec = max(0.0, start_sec)
        end_sec = max(start_sec, end_sec)
        safe_fps = fps if fps > 1.0 else 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = frame_count / safe_fps if frame_count > 0 else end_sec
        end_sec = min(end_sec, duration)

        if end_sec <= start_sec:
            return []

        start_frame = int(start_sec * safe_fps)
        end_frame = int(end_sec * safe_fps)
        step = max(1, int(round(self.interval_sec * safe_fps)))

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        samples: list[SampledFrame] = []
        frame_idx = start_frame

        while frame_idx <= end_frame:
            if frame_idx == start_frame or (frame_idx - start_frame) % step == 0:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                timestamp = frame_idx / safe_fps
                samples.append(
                    SampledFrame(
                        timestamp_sec=round(timestamp, 3),
                        frame_index=frame_idx,
                        image_bgr=frame,
                    )
                )
                frame_idx += 1
            else:
                if not cap.grab():
                    break
                frame_idx += 1

        return samples
