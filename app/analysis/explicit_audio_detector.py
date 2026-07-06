"""
Detect sexual / moan-like sounds using a dedicated log-mel CNN.

Based on research by Lovenia et al. (2022) and the
sexual-content-audio-classifier spectrogram approach. This replaces generic
AudioSet taggers (PANNs) which are not trained for explicit audio.

Final moderation should combine:
  - OpenNSFW (visual)
  - Vosk + blocked words (speech)
  - ExplicitAudioDetector (non-verbal sexual sounds)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Any

import numpy as np
import torch

from app.analysis.explicit_audio.cnn_model import ExplicitAudioCNN, load_checkpoint
from app.analysis.explicit_audio.mel_features import (
    HOP_LENGTH,
    SAMPLE_RATE,
    compute_log_mel,
    extract_time_window,
    frames_for_seconds,
    load_audio_mono,
    normalize_log_mel,
)
from app.config import EXPLICIT_AUDIO_MODEL_PATH

logger = logging.getLogger(__name__)

# --- Tunables ---
WINDOW_SECONDS = 2.0
WINDOW_HOP_SECONDS = 1.0
EXPLICIT_AUDIO_THRESHOLD = 0.35
PATCH_TIME_FRAMES = 64

SOURCE_TAG = "explicit_audio_cnn"
AUDIO_EVENT_LABEL_PREFIX = "audio_event:"
DEFAULT_DISPLAY_LABEL = "sexual vocal sound (moan-like)"


@dataclass(frozen=True)
class _WindowHit:
    start_time: float
    end_time: float
    confidence: float


class ExplicitAudioDetector:
    """
    Scan audio with a binary log-mel CNN trained for moan / sexual vocal sounds.

    Parameters
    ----------
    device:
        ``cpu`` by default.
    threshold:
        Probability cutoff for flagging a window (default 0.5 per Lovenia et al.).
    """

    def __init__(
        self,
        *,
        device: str = "cpu",
        threshold: float = EXPLICIT_AUDIO_THRESHOLD,
        model_path: Path | None = None,
        window_seconds: float = WINDOW_SECONDS,
        hop_seconds: float = WINDOW_HOP_SECONDS,
    ) -> None:
        self.device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.hop_seconds = hop_seconds
        self.model_path = Path(model_path or EXPLICIT_AUDIO_MODEL_PATH)

        self._model: ExplicitAudioCNN | None = None
        self._load_error: str | None = None

        try:
            self._load_model()
        except Exception as exc:  # noqa: BLE001
            self._load_error = str(exc)
            logger.warning("Explicit audio model load failed: %s", exc)

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._load_error is None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @staticmethod
    def is_model_available(model_path: Path | None = None) -> bool:
        path = Path(model_path or EXPLICIT_AUDIO_MODEL_PATH)
        return path.is_file() and path.stat().st_size > 10_000

    def _load_model(self) -> None:
        if not self.is_model_available(self.model_path):
            raise FileNotFoundError(
                f"Explicit audio model not found: {self.model_path}\n"
                "Run: python scripts/download_explicit_audio_model.py"
            )
        model, _meta = load_checkpoint(self.model_path, map_location=self.device)
        if self.device == "cuda":
            model = model.cuda()
        self._model = model

    def analyze_audio(
        self,
        audio_path: str,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
        max_duration_sec: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze a WAV/MP3 file and return suspicious timestamp ranges.

        Returns [] if the file or model is unavailable.
        """
        path = Path(audio_path)
        if not path.is_file():
            logger.error("Audio file not found: %s", path)
            return []

        if not self.is_ready:
            logger.error(
                "ExplicitAudioDetector not ready: %s",
                self._load_error or "model not loaded",
            )
            return []

        try:
            audio = load_audio_mono(str(path))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load audio %s: %s", path, exc)
            return []

        if audio.size == 0:
            return []

        if max_duration_sec and max_duration_sec > 0:
            max_samples = int(max_duration_sec * SAMPLE_RATE)
            audio = audio[:max_samples]

        hits = self._scan_waveform(audio, progress_callback=progress_callback)
        return _hits_to_detection_dicts(hits)

    def _scan_waveform(
        self,
        audio: np.ndarray,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[_WindowHit]:
        assert self._model is not None
        log_mel = normalize_log_mel(compute_log_mel(audio))
        window_frames = frames_for_seconds(self.window_seconds)
        hop_frames = max(1, frames_for_seconds(self.hop_seconds))

        hits: list[_WindowHit] = []
        total_frames = log_mel.shape[1]
        start_frame = 0
        total_windows = max(1, (total_frames + hop_frames - 1) // hop_frames)
        window_index = 0
        duration_sec = len(audio) / SAMPLE_RATE

        while start_frame < total_frames:
            patch = extract_time_window(log_mel, start_frame, window_frames)
            if patch.shape[1] != PATCH_TIME_FRAMES:
                patch = _resize_time_axis(patch, PATCH_TIME_FRAMES)

            prob = self._predict_patch(patch)
            start_sec = start_frame * HOP_LENGTH / SAMPLE_RATE
            end_sec = min(start_sec + self.window_seconds, duration_sec)

            if prob >= self.threshold:
                hits.append(
                    _WindowHit(
                        start_time=start_sec,
                        end_time=end_sec,
                        confidence=prob,
                    )
                )
            start_frame += hop_frames
            window_index += 1
            if progress_callback and window_index % 8 == 0:
                progress_callback(window_index, total_windows)

        if progress_callback:
            progress_callback(total_windows, total_windows)

        return _merge_hits(hits, gap_sec=self.hop_seconds * 0.5)

    def _predict_patch(self, patch: np.ndarray) -> float:
        assert self._model is not None
        tensor = torch.from_numpy(patch).float().unsqueeze(0).unsqueeze(0)
        if self.device == "cuda":
            tensor = tensor.cuda()
        with torch.no_grad():
            logits = self._model(tensor)
            prob = torch.sigmoid(logits).item()
        return float(prob)


def _resize_time_axis(patch: np.ndarray, target_frames: int) -> np.ndarray:
    """Linear resample along time axis to fixed width."""
    n_mels, current = patch.shape
    if current == target_frames:
        return patch
    x_old = np.linspace(0.0, 1.0, current)
    x_new = np.linspace(0.0, 1.0, target_frames)
    out = np.zeros((n_mels, target_frames), dtype=np.float32)
    for i in range(n_mels):
        out[i] = np.interp(x_new, x_old, patch[i])
    return out


def _merge_hits(hits: list[_WindowHit], *, gap_sec: float) -> list[_WindowHit]:
    if not hits:
        return []
    merged: list[_WindowHit] = [hits[0]]
    for hit in hits[1:]:
        prev = merged[-1]
        if hit.start_time <= prev.end_time + gap_sec:
            merged[-1] = _WindowHit(
                start_time=prev.start_time,
                end_time=max(prev.end_time, hit.end_time),
                confidence=max(prev.confidence, hit.confidence),
            )
        else:
            merged.append(hit)
    return merged


def events_to_timestamp_ranges(
    events: list[dict[str, Any]],
    *,
    video_duration_sec: float | None = None,
) -> list:
    """Convert detections to padded moderation ranges (same padding as keywords)."""
    from app.config import (
        AUDIO_KEYWORD_MERGE_GAP_SEC,
        AUDIO_MODERATION_LEAD_SEC,
        AUDIO_MODERATION_TRAIL_SEC,
    )
    from app.moderation.timestamp_manager import group_flagged_frames

    flagged = [
        (
            float(event["start_time"]),
            float(event["confidence"]),
            f"{AUDIO_EVENT_LABEL_PREFIX}{event.get('label', DEFAULT_DISPLAY_LABEL)}",
        )
        for event in events
    ]
    if not flagged:
        return []
    return group_flagged_frames(
        flagged,
        sample_interval_sec=WINDOW_HOP_SECONDS,
        max_gap_sec=AUDIO_KEYWORD_MERGE_GAP_SEC,
        lead_sec=AUDIO_MODERATION_LEAD_SEC,
        trail_sec=AUDIO_MODERATION_TRAIL_SEC,
        lead_frames=0,
        trail_frames=0,
        video_duration_sec=video_duration_sec,
    )


def _hits_to_detection_dicts(hits: list[_WindowHit]) -> list[dict[str, Any]]:
    return [
        {
            "detection_type": "audio_event",
            "start_time": round(hit.start_time, 3),
            "end_time": round(hit.end_time, 3),
            "label": DEFAULT_DISPLAY_LABEL,
            "confidence": round(hit.confidence, 4),
            "source": SOURCE_TAG,
        }
        for hit in hits
    ]
