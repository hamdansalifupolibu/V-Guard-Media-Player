"""Offline speech-to-text using Vosk."""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass
from pathlib import Path

from app.config import DEFAULT_VOSK_MODEL_DIR, VOSK_SAMPLE_RATE_HZ


@dataclass(frozen=True)
class TranscriptWord:
    word: str
    start_sec: float
    end_sec: float
    confidence: float


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start_sec: float
    end_sec: float
    words: tuple[TranscriptWord, ...]


class SpeechDetector:
    """Transcribe WAV audio with word-level timestamps."""

    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = Path(model_path or DEFAULT_VOSK_MODEL_DIR)

    @classmethod
    def is_model_available(cls, model_path: Path | None = None) -> bool:
        path = Path(model_path or DEFAULT_VOSK_MODEL_DIR)
        return (path / "am").is_dir() or (path / "graph").is_dir() or path.is_dir()

    def transcribe(self, wav_path: str | Path) -> list[TranscriptSegment]:
        """Return transcript segments with word timings."""
        from vosk import KaldiRecognizer, Model

        wav = Path(wav_path)
        if not wav.is_file():
            raise FileNotFoundError(f"Audio file not found: {wav}")
        if not self.is_model_available():
            raise FileNotFoundError(
                f"Vosk model not found at {self.model_path}\n"
                "Run: python scripts/download_vosk_model.py"
            )

        model = Model(str(self.model_path))
        segments: list[TranscriptSegment] = []

        with wave.open(str(wav), "rb") as wf:
            if wf.getnchannels() != 1:
                raise ValueError("WAV must be mono for Vosk")
            if wf.getframerate() != VOSK_SAMPLE_RATE_HZ:
                raise ValueError(
                    f"WAV must be {VOSK_SAMPLE_RATE_HZ} Hz (got {wf.getframerate()})"
                )

            recognizer = KaldiRecognizer(model, wf.getframerate())
            recognizer.SetWords(True)

            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if recognizer.AcceptWaveform(data):
                    segments.append(_parse_segment(json.loads(recognizer.Result())))

            final = json.loads(recognizer.FinalResult())
            if final.get("text", "").strip():
                segments.append(_parse_segment(final))

        return [s for s in segments if s.text.strip()]


def _parse_segment(payload: dict) -> TranscriptSegment:
    words_raw = payload.get("result") or []
    words: list[TranscriptWord] = []
    for item in words_raw:
        words.append(
            TranscriptWord(
                word=str(item.get("word", "")).lower(),
                start_sec=float(item.get("start", 0)),
                end_sec=float(item.get("end", 0)),
                confidence=float(item.get("conf", 0)),
            )
        )
    text = payload.get("text", "").strip()
    if not text and words:
        text = " ".join(w.word for w in words)
    start = words[0].start_sec if words else 0.0
    end = words[-1].end_sec if words else 0.0
    return TranscriptSegment(
        text=text,
        start_sec=start,
        end_sec=end,
        words=tuple(words),
    )
