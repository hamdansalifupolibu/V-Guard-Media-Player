"""Legal direct-link download support for V-Guard."""

from app.downloads.download_manager import DownloadManager, DownloadResult
from app.downloads.educational_extractor import (
    download_educational_video,
    is_extractor_available,
)
from app.downloads.url_validator import UrlValidationResult, validate_download_url

__all__ = [
    "DownloadManager",
    "DownloadResult",
    "UrlValidationResult",
    "validate_download_url",
    "download_educational_video",
    "is_extractor_available",
]
