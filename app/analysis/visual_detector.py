"""Visual safety classifier using a pre-trained Open NSFW ONNX model."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from app.analysis.frame_extractor import SampledFrame
from app.config import (
    FRAME_SAMPLE_INTERVAL_SEC,
    VISUAL_CONFIDENCE_THRESHOLD,
    VISUAL_MODEL_PATH,
)
from app.moderation.timestamp_manager import TimestampRange, group_flagged_frames

DEFAULT_MODEL_PATH = VISUAL_MODEL_PATH
UNSAFE_LABEL = "unsafe_visual"
SAFE_LABEL = "safe"


@dataclass(frozen=True)
class FramePrediction:
    """Classification result for one sampled frame."""

    timestamp_sec: float
    confidence: float
    is_flagged: bool
    label: str


class _ScoringBackend(ABC):
    @abstractmethod
    def score_nsfw(self, frame_bgr: np.ndarray) -> float:
        """Return NSFW probability in [0, 1]."""


class OnnxOpenNsfwBackend(_ScoringBackend):
    """ONNX Runtime backend for Yahoo Open-NSFW (NHWC, VGG mean)."""

    def __init__(self, model_path: Path) -> None:
        import onnxruntime as ort

        if not model_path.is_file():
            raise FileNotFoundError(
                f"Visual model not found: {model_path}\n"
                "Run: python scripts/download_visual_model.py"
            )
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = max(2, min(4, (os.cpu_count() or 4) // 2))
        self._session = ort.InferenceSession(
            str(model_path),
            opts,
            providers=["CPUExecutionProvider"],
        )
        self._input_name = self._session.get_inputs()[0].name

    def score_nsfw(self, frame_bgr: np.ndarray) -> float:
        scores = self.score_nsfw_batch([frame_bgr])
        return scores[0]

    def score_nsfw_batch(self, frames_bgr: list[np.ndarray]) -> list[float]:
        if not frames_bgr:
            return []
        tensors = np.concatenate(
            [_preprocess_nhwc(frame) for frame in frames_bgr],
            axis=0,
        )
        outputs = self._session.run(None, {self._input_name: tensors})
        raw = np.asarray(outputs[0])
        if raw.ndim == 1:
            raw = raw.reshape(1, -1)
        scores: list[float] = []
        for row in raw:
            flat = np.asarray(row).reshape(-1)
            if flat.size >= 2:
                scores.append(float(flat[1]))
            else:
                scores.append(float(flat[0]))
        return scores


def _preprocess_nhwc(frame_bgr: np.ndarray) -> np.ndarray:
    """Resize to 224x224, BGR mean subtraction (Open-NSFW SIMPLE pipeline)."""
    resized = cv2.resize(frame_bgr, (224, 224), interpolation=cv2.INTER_LINEAR)
    image = resized.astype(np.float32)
    image = image[:, :, ::-1]  # RGB -> BGR channel order for mean
    image -= np.array([104.0, 117.0, 123.0], dtype=np.float32)
    return image[np.newaxis, ...]


class VisualDetector:
    """
    Run visual safety inference on sampled frames and build timestamp ranges.

    Uses ONNX by default (`models/visual_model/open_nsfw.onnx`).
    """

    def __init__(
        self,
        *,
        threshold: float = VISUAL_CONFIDENCE_THRESHOLD,
        model_path: Path | None = None,
        backend: _ScoringBackend | None = None,
        sample_interval_sec: float = FRAME_SAMPLE_INTERVAL_SEC,
    ) -> None:
        self.threshold = threshold
        self.sample_interval_sec = sample_interval_sec
        self._backend = backend or OnnxOpenNsfwBackend(
            Path(model_path or DEFAULT_MODEL_PATH)
        )

    @classmethod
    def is_model_available(cls, model_path: Path | None = None) -> bool:
        return Path(model_path or DEFAULT_MODEL_PATH).is_file()

    def predict_frame(
        self,
        frame_bgr: np.ndarray,
        timestamp_sec: float,
    ) -> FramePrediction:
        nsfw_prob = self._backend.score_nsfw(frame_bgr)
        is_flagged = nsfw_prob >= self.threshold
        return FramePrediction(
            timestamp_sec=timestamp_sec,
            confidence=nsfw_prob,
            is_flagged=is_flagged,
            label=UNSAFE_LABEL if is_flagged else SAFE_LABEL,
        )

    def scan_samples(
        self,
        samples: list[SampledFrame],
        progress_callback: Callable[[int, int], None] | None = None,
        *,
        batch_size: int = 1,
    ) -> list[FramePrediction]:
        """Classify sampled frames (batched ONNX when batch_size > 1)."""
        if not samples:
            return []

        predictions: list[FramePrediction] = []
        total = len(samples)
        batch_size = max(1, batch_size)
        done = 0

        for start in range(0, total, batch_size):
            chunk = samples[start : start + batch_size]
            if batch_size > 1 and hasattr(self._backend, "score_nsfw_batch"):
                scores = self._backend.score_nsfw_batch(
                    [s.image_bgr for s in chunk]
                )
                for sample, nsfw_prob in zip(chunk, scores, strict=True):
                    predictions.append(
                        FramePrediction(
                            timestamp_sec=sample.timestamp_sec,
                            confidence=nsfw_prob,
                            is_flagged=nsfw_prob >= self.threshold,
                            label=UNSAFE_LABEL if nsfw_prob >= self.threshold else SAFE_LABEL,
                        )
                    )
            else:
                for sample in chunk:
                    predictions.append(
                        self.predict_frame(sample.image_bgr, sample.timestamp_sec)
                    )
            done += len(chunk)
            if progress_callback:
                progress_callback(done, total)

        return predictions

    def build_timestamp_ranges(
        self,
        predictions: list[FramePrediction],
        *,
        fps: float = 0.0,
        video_duration_sec: float | None = None,
    ) -> list[TimestampRange]:
        flagged = [
            (p.timestamp_sec, p.confidence, p.label)
            for p in predictions
            if p.is_flagged
        ]
        return group_flagged_frames(
            flagged,
            sample_interval_sec=self.sample_interval_sec,
            fps=fps,
            video_duration_sec=video_duration_sec,
        )

    def scan_and_group(
        self,
        samples: list[SampledFrame],
        progress_callback: Callable[[int, int], None] | None = None,
        *,
        fps: float = 0.0,
        video_duration_sec: float | None = None,
    ) -> tuple[list[FramePrediction], list[TimestampRange]]:
        predictions = self.scan_samples(samples, progress_callback)
        ranges = self.build_timestamp_ranges(
            predictions,
            fps=fps,
            video_duration_sec=video_duration_sec,
        )
        return predictions, ranges
