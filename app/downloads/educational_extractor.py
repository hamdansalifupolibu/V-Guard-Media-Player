"""Extract educational videos from page URLs (YouTube, Vimeo, etc.) via yt-dlp."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from app.utils.ffmpeg_path import is_ffmpeg_available, resolve_ffmpeg_dir

ProgressCallback = Callable[[int, int, str], None]

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def is_extractor_available() -> bool:
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


def _clean_error_message(exc: BaseException) -> str:
    text = _ANSI_ESCAPE.sub("", str(exc)).strip()
    if "ffmpeg is not installed" in text.lower() or "merging of multiple formats" in text.lower():
        return (
            "FFmpeg is required for many YouTube downloads.\n\n"
            "Run: python scripts/install_ffmpeg.py\n"
            "Or install FFmpeg system-wide: https://ffmpeg.org/download.html\n\n"
            "Then restart V-Guard and try again."
        )
    if len(text) > 400:
        text = text[:400] + "…"
    return text or "Unknown extraction error."


def _format_selector() -> str:
    """Prefer a single file when FFmpeg is missing (no merge step)."""
    if is_ffmpeg_available():
        return "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best[ext=mp4]/best"
    return "best[ext=mp4]/best"


def download_educational_video(
    url: str,
    output_dir: Path,
    on_progress: ProgressCallback | None = None,
    *,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[bool, str, str | None]:
    """
    Download video from a page URL for educational use.

    Returns (ok, message, file_path).
    """
    try:
        import yt_dlp
    except ImportError:
        return (
            False,
            "Install yt-dlp for educational page links: pip install yt-dlp",
            None,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    last_path: list[str] = []

    def hook(status: dict) -> None:
        if cancel_check and cancel_check():
            raise RuntimeError("Download cancelled")
        if status.get("status") == "downloading" and on_progress:
            received = int(status.get("downloaded_bytes") or 0)
            total = int(
                status.get("total_bytes")
                or status.get("total_bytes_estimate")
                or 0
            )
            on_progress(received, total, "Extracting video…")
        if status.get("status") == "finished":
            path = status.get("filename")
            if path:
                last_path.append(path)

    ydl_opts: dict = {
        "format": _format_selector(),
        "outtmpl": str(output_dir / "%(title).180s.%(ext)s"),
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    ff_dir = resolve_ffmpeg_dir()
    if ff_dir:
        ydl_opts["ffmpeg_location"] = ff_dir
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return False, "Could not read video information.", None
            filepath = last_path[-1] if last_path else ydl.prepare_filename(info)
            path = Path(filepath)
            if not path.is_file():
                candidates = sorted(
                    output_dir.glob("*"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                path = next((p for p in candidates if p.is_file()), path)
            if not path.is_file():
                return False, "Extraction finished but no video file was found.", None
            if on_progress:
                size = path.stat().st_size
                on_progress(size, size, "Complete")
            return True, f"Saved to {path.name}", str(path.resolve())
    except RuntimeError as exc:
        if "cancelled" in str(exc).lower():
            return False, "Download cancelled.", None
        raise
    except Exception as exc:  # noqa: BLE001
        return False, f"Could not extract video:\n\n{_clean_error_message(exc)}", None
