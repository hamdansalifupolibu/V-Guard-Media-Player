"""Resolve FFmpeg — bundled tools/ffmpeg first, then system PATH."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.config import FFMPEG_BIN_DIR, PROJECT_ROOT


def bundled_ffmpeg_exe() -> Path | None:
    exe = FFMPEG_BIN_DIR / "ffmpeg.exe"
    return exe if exe.is_file() else None


def resolve_ffmpeg_dir() -> str | None:
    """Directory containing ffmpeg.exe for yt-dlp, or None."""
    bundled = bundled_ffmpeg_exe()
    if bundled:
        return str(bundled.parent)
    found = shutil.which("ffmpeg")
    if found:
        return str(Path(found).parent)
    return None


def is_ffmpeg_available() -> bool:
    return resolve_ffmpeg_dir() is not None


def ensure_ffmpeg_on_path() -> None:
    """Prepend bundled FFmpeg to process PATH so VLC analysis also finds it."""
    ff_dir = resolve_ffmpeg_dir()
    if not ff_dir:
        return
    current = os.environ.get("PATH", "")
    if ff_dir not in current.split(os.pathsep):
        os.environ["PATH"] = ff_dir + os.pathsep + current
