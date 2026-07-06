"""Progressive pre-scan: visual chunks + background audio analysis."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, Signal

from app.analysis.audio_pipeline import AudioScanPipeline
from app.analysis.detection_builder import (
    apply_chunk_visual_detections,
    merge_detection_ranges,
    rebuild_visual_detections,
)
from app.analysis.frame_extractor import FrameExtractor
from app.analysis.scan_profile import ScanProfile, build_scan_profile
from app.analysis.visual_detector import VisualDetector
from app.analysis.visual_strictness import resolve_visual_threshold
from app.config import (
    FRAME_SAMPLE_INTERVAL_SEC,
    SCAN_PROGRESS_MIN_INTERVAL_SEC,
    SETTING_ENABLE_AUDIO,
    SETTING_ENABLE_VISUAL,
    SETTING_FORCE_AUDIO_LONG,
    SETTING_FRAME_INTERVAL,
    SETTING_SCAN_CHUNK_DURATION,
    SETTING_VISUAL_STRICTNESS,
    SETTING_VISUAL_THRESHOLD,
)
from app.database.db import VGuardDatabase


class _ProgressThrottle:
    """Limit Qt signal frequency so the UI stays responsive on long scans."""

    def __init__(self, emit, min_interval_sec: float = SCAN_PROGRESS_MIN_INTERVAL_SEC) -> None:
        self._emit = emit
        self._min_interval = min_interval_sec
        self._last_emit = 0.0
        self._last_pct = -1

    def emit(self, percent: int, message: str, *, force: bool = False) -> None:
        now = time.monotonic()
        pct = max(0, min(100, percent))
        if (
            not force
            and (now - self._last_emit) < self._min_interval
            and pct == self._last_pct
        ):
            return
        self._last_emit = now
        self._last_pct = pct
        self._emit(pct, message)


class VideoScanner(QObject):
    """
    Progressive (lazy-style) pre-scan on a background thread.

    Long TV episodes use coarser sampling, larger chunks, batched ONNX,
    sequential frame reads, and incremental DB updates.
    """

    progress = Signal(int, str)
    chunk_ready = Signal(int, float, int)
    finished = Signal(int, int, int, int, str)
    failed = Signal(str)

    def __init__(
        self,
        database: VGuardDatabase,
        interval_sec: float = FRAME_SAMPLE_INTERVAL_SEC,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = database
        self._extractor = FrameExtractor(interval_sec=interval_sec)
        self._audio_pipeline = AudioScanPipeline(database)
        self._last_warning: str = ""
        self._cancel_requested = False
        self._progress = _ProgressThrottle(self.progress.emit)

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _setting_bool(self, key: str, default: bool = True) -> bool:
        raw = self._db.get_setting(key)
        if raw is None:
            return default
        return raw.strip().lower() not in ("false", "0", "no", "off")

    def _frame_interval_sec(self) -> float:
        raw = self._db.get_setting(SETTING_FRAME_INTERVAL)
        if raw is None:
            return FRAME_SAMPLE_INTERVAL_SEC
        try:
            return float(raw)
        except ValueError:
            return FRAME_SAMPLE_INTERVAL_SEC

    def _chunk_duration_sec(self) -> float:
        from app.config import SCAN_CHUNK_DURATION_SEC

        raw = self._db.get_setting(SETTING_SCAN_CHUNK_DURATION)
        if raw is None:
            return SCAN_CHUNK_DURATION_SEC
        try:
            return max(10.0, float(raw))
        except ValueError:
            return SCAN_CHUNK_DURATION_SEC

    def _force_audio_long(self) -> bool:
        return self._setting_bool(SETTING_FORCE_AUDIO_LONG, False)

    def _visual_threshold(self) -> float:
        return resolve_visual_threshold(
            strictness_raw=self._db.get_setting(SETTING_VISUAL_STRICTNESS),
            threshold_raw=self._db.get_setting(SETTING_VISUAL_THRESHOLD),
        )

    def run_scan(self, video_id: int, file_path: str | Path, *, resume: bool = False) -> None:
        path = Path(file_path)
        if not path.is_file():
            self.failed.emit(f"Video file not found: {path}")
            return

        visual_enabled = self._setting_bool(SETTING_ENABLE_VISUAL, True)
        audio_enabled = self._setting_bool(SETTING_ENABLE_AUDIO, True)
        frame_count = 0
        visual_count = 0
        self._last_warning = ""
        self._cancel_requested = False
        warnings: list[str] = []
        cap: cv2.VideoCapture | None = None

        try:
            self._db.update_scan_status(video_id, "scanning")
            self._progress.emit(2, "Opening video…", force=True)

            meta = self._extractor.probe(path)
            video_fps = float(meta.get("fps") or 0.0)
            video_duration = float(meta.get("duration_sec") or 0.0)
            if video_duration > 0:
                self._db.update_duration(video_id, video_duration)

            profile = build_scan_profile(
                video_duration,
                user_interval_sec=self._frame_interval_sec(),
                user_chunk_sec=self._chunk_duration_sec(),
                audio_enabled=audio_enabled,
                force_audio_long=self._force_audio_long(),
            )
            self._extractor.interval_sec = profile.sample_interval_sec
            chunk_sec = profile.chunk_duration_sec

            if profile.long_form:
                warnings.append(
                    f"Long video mode: sampling every {profile.sample_interval_sec:.1f}s, "
                    f"~{profile.estimated_frame_samples} frames total."
                )
            if profile.audio_skip_reason:
                warnings.append(profile.audio_skip_reason)

            record = self._db.get_video_by_id(video_id)
            start_sec = float(record.scan_progress_sec) if resume and record else 0.0

            if not resume or start_sec <= 0.0:
                self._db.reset_scan_progress(video_id)
                self._db.clear_detections(video_id, "visual")
                self._db.clear_frame_predictions(video_id)
                start_sec = 0.0

            threshold = self._visual_threshold()

            if visual_enabled:
                if not VisualDetector.is_model_available():
                    self.failed.emit(
                        "Visual AI model not found.\n\n"
                        "Run: python scripts/download_visual_model.py"
                    )
                    return

                detector = VisualDetector(
                    threshold=threshold,
                    sample_interval_sec=profile.sample_interval_sec,
                )
                cap = FrameExtractor.open_capture(path)

                if video_duration <= 0:
                    self._progress.emit(100, "No video duration — skipping visual scan.", force=True)
                else:
                    chunk_index = 0
                    while start_sec < video_duration - 1e-6:
                        if self._cancel_requested:
                            self._db.update_scan_status(video_id, "scanning")
                            self._progress.emit(
                                int(100 * start_sec / video_duration),
                                "Scan cancelled — partial results kept.",
                                force=True,
                            )
                            return

                        end_sec = min(start_sec + chunk_sec, video_duration)
                        chunk_index += 1
                        pct_base = int(8 + 72 * start_sec / video_duration)
                        self._progress.emit(
                            pct_base,
                            f"Analyzing {start_sec:.0f}s–{end_sec:.0f}s of "
                            f"{video_duration:.0f}s "
                            f"(~{profile.sample_interval_sec:.1f}s per frame)…",
                        )

                        samples = self._extractor.extract_range_from_capture(
                            cap, start_sec, end_sec, video_fps
                        )
                        frame_count += len(samples)

                        if samples:
                            def on_ai_progress(done: int, total: int) -> None:
                                sub = pct_base + int(
                                    6 * done / max(total, 1)
                                )
                                self._progress.emit(
                                    sub,
                                    f"Visual AI: {done}/{total} frames "
                                    f"({start_sec:.0f}s–{end_sec:.0f}s)…",
                                )

                            predictions = detector.scan_samples(
                                samples,
                                progress_callback=on_ai_progress,
                                batch_size=profile.visual_batch_size,
                            )
                            self._db.append_frame_predictions(
                                video_id,
                                [
                                    {
                                        "timestamp_sec": p.timestamp_sec,
                                        "nsfw_confidence": p.confidence,
                                        "is_flagged": p.is_flagged,
                                    }
                                    for p in predictions
                                ],
                                threshold=threshold,
                            )
                            visual_count = apply_chunk_visual_detections(
                                self._db,
                                video_id,
                                predictions,
                                fps=video_fps,
                                sample_interval_sec=profile.sample_interval_sec,
                                video_duration_sec=video_duration,
                            )

                        self._db.update_scan_progress(video_id, end_sec)
                        start_sec = end_sec

                        pct = int(8 + 72 * end_sec / video_duration)
                        self._progress.emit(
                            pct,
                            f"Segment {chunk_index} saved — safe to play through {end_sec:.0f}s",
                        )
                        self.chunk_ready.emit(video_id, end_sec, visual_count)

                    if not self._cancel_requested and frame_count > 0:
                        visual_count = rebuild_visual_detections(
                            self._db,
                            video_id,
                            fps=video_fps,
                            sample_interval_sec=profile.sample_interval_sec,
                            video_duration_sec=video_duration,
                        )

            if cap is not None:
                FrameExtractor.close_capture(cap)

            if self._cancel_requested:
                return

            audio_count = 0
            if profile.run_audio:
                audio_count, audio_warning = self._run_audio_pipeline(video_id, path)
                if audio_warning:
                    warnings.append(audio_warning)
                if audio_count > 0:
                    self.chunk_ready.emit(
                        video_id,
                        video_duration,
                        visual_count,
                    )

            self._last_warning = "\n".join(warnings)
            self._db.update_scan_progress(video_id, video_duration)
            self._db.update_scan_status(video_id, "complete")
            self._progress.emit(
                100,
                f"Scan complete — {frame_count} frames, "
                f"{visual_count} visual, {audio_count} audio segment(s)",
                force=True,
            )
            self.finished.emit(
                video_id,
                frame_count,
                visual_count,
                audio_count,
                self._last_warning,
            )
        except Exception as exc:  # noqa: BLE001
            if cap is not None:
                FrameExtractor.close_capture(cap)
            self._db.update_scan_status(video_id, "failed")
            self.failed.emit(str(exc))

    def _run_audio_pipeline(self, video_id: int, path: Path) -> tuple[int, str]:
        """Return (segment_count, optional_warning). Never fails the whole scan."""

        def on_progress(pct: int, message: str) -> None:
            self._progress.emit(pct, message, force=(pct >= 98))

        return self._audio_pipeline.run(
            video_id,
            path,
            progress=on_progress,
        )
