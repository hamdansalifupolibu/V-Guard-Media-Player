"""Validate video URLs for educational downloads (open, permission-aware)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

ALLOWED_VIDEO_EXTENSIONS = (
    ".mp4",
    ".webm",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".ogv",
)

VIDEO_CONTENT_TYPES = (
    "video/",
    "application/octet-stream",
    "application/vnd.apple.mpegurl",
)

HTML_CONTENT_TYPES = ("text/html", "application/xhtml")

DISPOSITION_FILENAME = re.compile(
    r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UrlValidationResult:
    ok: bool
    message: str
    normalized_url: str = ""
    suggested_filename: str = ""
    use_stream_extractor: bool = False


def _extension_from_path(path: str) -> str:
    lower = path.lower().split("?")[0]
    for ext in ALLOWED_VIDEO_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    return ""


def _filename_from_disposition(header: str | None) -> str:
    if not header:
        return ""
    match = DISPOSITION_FILENAME.search(header)
    if not match:
        return ""
    name = match.group(1).strip()
    if _extension_from_path(name):
        return name
    return ""


def _guess_filename(url: str) -> str:
    parsed = urlparse(url)
    path_ext = _extension_from_path(parsed.path or "")
    if path_ext:
        segment = (parsed.path or "").rstrip("/").split("/")[-1]
        if segment and "." in segment:
            return segment
        return f"educational_video{path_ext}"
    return "educational_video.mp4"


def validate_download_url(
    url: str,
    *,
    content_type: str | None = None,
    content_disposition: str | None = None,
    educational: bool = True,
) -> UrlValidationResult:
    """
    Validate a user-supplied URL for download.

    Educational mode (default) accepts any http/https link. Direct file links are
    preferred; page links (e.g. YouTube) may use an extractor when available.
    """
    raw = (url or "").strip()
    if not raw:
        return UrlValidationResult(False, "Enter a URL to download.")

    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return UrlValidationResult(
            False,
            "Only http:// or https:// links are supported.",
        )

    if not parsed.netloc:
        return UrlValidationResult(False, "URL is missing a host name.")

    path_ext = _extension_from_path(parsed.path or "")
    filename = _filename_from_disposition(content_disposition)
    if not filename and path_ext:
        segment = (parsed.path or "").rstrip("/").split("/")[-1]
        filename = segment if segment else f"educational_video{path_ext}"

    ctype = (content_type or "").split(";")[0].strip().lower()
    ctype_video = any(ctype.startswith(p) for p in VIDEO_CONTENT_TYPES)
    ctype_html = any(ctype.startswith(p) for p in HTML_CONTENT_TYPES)

    if path_ext or filename:
        return UrlValidationResult(
            True,
            "Video link accepted for educational download.",
            normalized_url=raw,
            suggested_filename=filename or f"educational_video{path_ext}",
        )

    if content_type is not None:
        if ctype_video:
            return UrlValidationResult(
                True,
                "Video file confirmed by server.",
                normalized_url=raw,
                suggested_filename=filename or _guess_filename(raw),
            )
        if educational and (ctype_html or not ctype):
            return UrlValidationResult(
                True,
                "Educational page link — will try to extract the video.",
                normalized_url=raw,
                suggested_filename=_guess_filename(raw),
                use_stream_extractor=True,
            )
        if educational:
            return UrlValidationResult(
                True,
                "Educational link accepted — attempting download.",
                normalized_url=raw,
                suggested_filename=_guess_filename(raw),
                use_stream_extractor=True,
            )

    if educational:
        return UrlValidationResult(
            True,
            "Educational URL accepted.",
            normalized_url=raw,
            suggested_filename=_guess_filename(raw),
        )

    return UrlValidationResult(
        False,
        "Could not verify this URL as a video. Enable educational mode or use a direct file link.",
    )
