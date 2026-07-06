"""
Unified audio pre-scan: FFmpeg extract, Vosk keywords, explicit-sound CNN.

Designed to fail softly (warnings, not whole-scan failure) and reuse one
ExplicitAudioDetector instance per scanner run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from app.analysis.audio_extractor import AudioExtractor
from app.analysis.detection_builder import merge_detection_ranges
from app.analysis.explicit_audio_detector import (
    ExplicitAudioDetector,
    events_to_timestamp_ranges,
)
from app.analysis.keyword_filter import KeywordFilter
from app.analysis.speech_detector import SpeechDetector
from app.config import (
    BLOCKED_WORDS_PATH,
    SETTING_ENABLE_AUDIO,
    SETTING_ENABLE_EXPLICIT_AUDIO,
    SETTING_ENABLE_PANNS_AUDIO,
)
from app.database.db import VGuardDatabase
from app.moderation.timestamp_manager import TimestampRange

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]


class AudioScanPipeline:
    """Run keyword + explicit-sound analysis on one extracted WAV."""

    def __init__(self, database: VGuardDatabase) -> None:
        self._db = database
        self._extractor = AudioExtractor()
        self._explicit_detector: ExplicitAudioDetector | None = None

    def run(
        self,
        video_id: int,
        video_path: Path,
        *,
        progress: ProgressCallback | None = None,
    ) -> tuple[int, str]:
        """
        Return (audio_segment_count, joined_warnings).

        Never raises — scan worker treats this as non-fatal.
        """
        warnings: list[str] = []

        def emit(pct: int, msg: str) -> None:
            if progress:
                progress(pct, msg)

        if not self._setting_bool(SETTING_ENABLE_AUDIO, True):
            return 0, "Audio scan disabled in Settings."

        if not AudioExtractor.is_ffmpeg_available():
            return (
                0,
                "Audio scan skipped: FFmpeg not found. Run: python scripts/install_ffmpeg.py",
            )

        try:
            emit(82, "Extracting audio (FFmpeg)…")
            wav_path = self._extractor.extract(video_path, video_id=video_id)
        except Exception as exc:  # noqa: BLE001
            return 0, f"Audio scan skipped: could not extract audio ({exc})."

        record = self._db.get_video_by_id(video_id)
        duration = float(record.duration) if record and record.duration else None
        all_ranges: list[TimestampRange] = []

        # --- Vosk / keywords ---
        if self._setting_bool(SETTING_ENABLE_AUDIO, True):
            kw_ranges, kw_warn = self._run_keyword_scan(wav_path, duration, emit)
            warnings.extend(kw_warn)
            all_ranges = merge_detection_ranges([], kw_ranges, merge_gap_sec=2.0)

        # --- Explicit-sound CNN ---
        if self._explicit_enabled():
            exp_ranges, exp_warn = self._run_explicit_scan(wav_path, duration, emit)
            warnings.extend(exp_warn)
            all_ranges = merge_detection_ranges(
                [],
                all_ranges + exp_ranges,
                merge_gap_sec=2.0,
            )

        self._db.clear_detections(video_id, "audio")
        for time_range in all_ranges:
            self._db.add_detection(
                video_id,
                "audio",
                time_range.start_time,
                time_range.end_time,
                confidence=time_range.confidence,
                label=time_range.label,
            )

        return len(all_ranges), "\n".join(w for w in warnings if w)

    def _run_keyword_scan(
        self,
        wav_path: Path,
        duration: float | None,
        emit: Callable[[int, str], None],
    ) -> tuple[list[TimestampRange], list[str]]:
        warnings: list[str] = []
        if not SpeechDetector.is_model_available():
            warnings.append(
                "Keyword scan skipped: Vosk model not found. "
                "Run: python scripts/download_vosk_model.py"
            )
            return [], warnings
        try:
            emit(86, "Transcribing speech (Vosk)…")
            speech = SpeechDetector()
            segments = speech.transcribe(wav_path)
            emit(90, "Checking blocked keywords…")
            words_path = self._db.get_setting("blocked_words_path")
            kw_file = Path(words_path) if words_path else BLOCKED_WORDS_PATH
            keyword_filter = KeywordFilter(kw_file)
            _hits, ranges = keyword_filter.scan_segments(
                segments, video_duration_sec=duration
            )
            return ranges, warnings
        except Exception as exc:  # noqa: BLE001
            logger.warning("Keyword scan failed: %s", exc)
            warnings.append(f"Keyword scan failed ({exc}).")
            return [], warnings

    def _run_explicit_scan(
        self,
        wav_path: Path,
        duration: float | None,
        emit: Callable[[int, str], None],
    ) -> tuple[list[TimestampRange], list[str]]:
        warnings: list[str] = []
        try:
            detector = self._get_explicit_detector()
            if not detector.is_ready:
                warnings.append(
                    f"Explicit audio scan skipped: {detector.load_error or 'model missing'}. "
                    "Run: python scripts/download_explicit_audio_model.py"
                )
                return [], warnings

            emit(92, "Analyzing explicit audio (log-mel CNN)…")

            def on_progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                pct = 92 + int(6 * done / total)
                emit(min(98, pct), f"Explicit audio… {done}/{total} windows")

            events = detector.analyze_audio(
                str(wav_path),
                progress_callback=on_progress,
                max_duration_sec=duration,
            )
            ranges = events_to_timestamp_ranges(events, video_duration_sec=duration)
            if events:
                emit(98, f"Explicit audio: {len(events)} segment(s) flagged")
            return ranges, warnings
        except Exception as exc:  # noqa: BLE001
            logger.warning("Explicit audio scan failed: %s", exc)
            warnings.append(f"Explicit audio scan failed ({exc}).")
            return [], warnings

    def _get_explicit_detector(self) -> ExplicitAudioDetector:
        if self._explicit_detector is None:
            self._explicit_detector = ExplicitAudioDetector(device="cpu")
        return self._explicit_detector

    def _explicit_enabled(self) -> bool:
        if not self._setting_bool(SETTING_ENABLE_AUDIO, True):
            return False
        return self._setting_bool(
            SETTING_ENABLE_EXPLICIT_AUDIO,
            self._setting_bool(SETTING_ENABLE_PANNS_AUDIO, True),
        )

    def _setting_bool(self, key: str, default: bool) -> bool:
        raw = self._db.get_setting(key)
        if raw is None:
            return default
        return raw.strip().lower() in ("true", "1", "yes", "on")
