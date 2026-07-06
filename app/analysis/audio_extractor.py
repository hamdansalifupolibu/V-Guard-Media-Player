"""Extract mono 16 kHz WAV audio from video via FFmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import TEMP_AUDIO_DIR, VOSK_SAMPLE_RATE_HZ


class AudioExtractor:
    """Use FFmpeg to produce speech-recognition-friendly WAV files."""

    def __init__(
        self,
        *,
        sample_rate: int = VOSK_SAMPLE_RATE_HZ,
        output_dir: Path | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.output_dir = Path(output_dir or TEMP_AUDIO_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_ffmpeg_available() -> bool:
        return shutil.which("ffmpeg") is not None

    def extract(self, video_path: str | Path, *, video_id: int | None = None) -> Path:
        """
        Extract audio to WAV. Returns path to the WAV file.

        Raises FileNotFoundError if video missing, RuntimeError if FFmpeg fails.
        """
        if not self.is_ffmpeg_available():
            raise RuntimeError(
                "FFmpeg not found on PATH. Install FFmpeg and restart the terminal."
            )

        video = Path(video_path)
        if not video.is_file():
            raise FileNotFoundError(f"Video not found: {video}")

        suffix = f"_{video_id}" if video_id is not None else ""
        output = self.output_dir / f"{video.stem}{suffix}_audio.wav"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video.resolve()),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(self.sample_rate),
            "-ac",
            "1",
            str(output),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not output.is_file():
            stderr = (result.stderr or "").strip()[-500:]
            raise RuntimeError(f"FFmpeg audio extraction failed:\n{stderr}")

        return output
