"""Download educational videos — direct links and page URLs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from app.config import DOWNLOADS_DIR
from app.downloads.educational_extractor import (
    download_educational_video,
    is_extractor_available,
)
from app.downloads.url_validator import validate_download_url

ProgressCallback = Callable[[int, int, str], None]

CHUNK_SIZE = 256 * 1024
HEAD_TIMEOUT = 20
GET_TIMEOUT = 120
USER_AGENT = "V-Guard-Media-Player/1.0 (educational downloads)"


@dataclass(frozen=True)
class DownloadResult:
    ok: bool
    message: str
    file_path: str | None = None
    url: str = ""
    use_stream_extractor: bool = False


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")
    return cleaned[:180] if cleaned else "educational_video.mp4"


def _unique_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / filename
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix or ".mp4"
    n = 1
    while True:
        candidate = directory / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


class DownloadManager:
    """Downloads videos for educational use (direct URLs and page links)."""

    def __init__(self, downloads_dir: Path | None = None) -> None:
        self._dir = downloads_dir or DOWNLOADS_DIR

    @property
    def downloads_dir(self) -> Path:
        return self._dir

    def probe_url(self, url: str) -> DownloadResult:
        """Check URL and choose direct download vs educational extractor."""
        validation = validate_download_url(url, educational=True)
        if not validation.ok:
            return DownloadResult(False, validation.message, url=url)

        normalized = validation.normalized_url or url.strip()
        use_extractor = validation.use_stream_extractor

        try:
            response = requests.head(
                normalized,
                allow_redirects=True,
                timeout=HEAD_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            if response.status_code >= 400:
                response = requests.get(
                    normalized,
                    stream=True,
                    timeout=HEAD_TIMEOUT,
                    headers={"User-Agent": USER_AGENT},
                )
                response.close()

            ctype = response.headers.get("Content-Type", "")
            disp = response.headers.get("Content-Disposition", "")
            checked = validate_download_url(
                normalized,
                content_type=ctype,
                content_disposition=disp,
                educational=True,
            )
            if checked.ok:
                use_extractor = checked.use_stream_extractor
                validation = checked
        except requests.RequestException:
            if not use_extractor:
                use_extractor = True

        if use_extractor:
            if not is_extractor_available():
                return DownloadResult(
                    False,
                    "This looks like a video page, not a direct file. "
                    "Install yt-dlp: pip install yt-dlp",
                    url=normalized,
                    use_stream_extractor=True,
                )
            return DownloadResult(
                True,
                validation.message,
                url=normalized,
                file_path=str(self._dir.resolve()),
                use_stream_extractor=True,
            )

        filename = validation.suggested_filename or "educational_video.mp4"
        return DownloadResult(
            True,
            validation.message,
            url=normalized,
            file_path=str(
                _unique_path(self._dir, _safe_filename(filename))
            ),
            use_stream_extractor=False,
        )

    def download(
        self,
        url: str,
        dest_path: str | Path,
        on_progress: ProgressCallback | None = None,
        *,
        cancel_check: Callable[[], bool] | None = None,
        use_stream_extractor: bool = False,
    ) -> DownloadResult:
        """Download to ``dest_path`` (file) or extract into ``dest_path`` (folder)."""
        if use_stream_extractor:
            ok, message, file_path = download_educational_video(
                url,
                Path(dest_path),
                on_progress,
                cancel_check=cancel_check,
            )
            return DownloadResult(ok, message, file_path=file_path, url=url)

        dest = Path(dest_path)
        probe = self.probe_url(url)
        if not probe.ok:
            return probe
        if probe.use_stream_extractor:
            return self.download(
                probe.url or url,
                self._dir,
                on_progress,
                cancel_check=cancel_check,
                use_stream_extractor=True,
            )

        download_url = probe.url or url
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            with requests.get(
                download_url,
                stream=True,
                timeout=GET_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            ) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", 0) or 0)
                received = 0
                if on_progress:
                    on_progress(0, total, "Downloading…")

                with dest.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if cancel_check and cancel_check():
                            dest.unlink(missing_ok=True)
                            return DownloadResult(
                                False,
                                "Download cancelled.",
                                url=download_url,
                            )
                        if not chunk:
                            continue
                        handle.write(chunk)
                        received += len(chunk)
                        if on_progress:
                            on_progress(received, total, "Downloading…")

            if dest.stat().st_size == 0:
                dest.unlink(missing_ok=True)
                return DownloadResult(
                    False,
                    "Downloaded file is empty.",
                    url=download_url,
                )

            if on_progress:
                on_progress(received, total or received, "Complete")
            return DownloadResult(
                True,
                f"Saved to {dest.name}",
                file_path=str(dest.resolve()),
                url=download_url,
            )
        except requests.RequestException as exc:
            dest.unlink(missing_ok=True)
            return DownloadResult(
                False,
                f"Download failed: {exc}",
                url=download_url,
            )
