"""Tests for download manager (mocked HTTP)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.downloads.download_manager import DownloadManager


def test_probe_direct_mp4(tmp_path: Path) -> None:
    manager = DownloadManager(tmp_path)
    url = "https://cdn.example.edu/lecture01.mp4"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {
        "Content-Type": "video/mp4",
        "Content-Disposition": 'attachment; filename="lecture01.mp4"',
    }

    with patch("app.downloads.download_manager.requests.head", return_value=mock_resp):
        result = manager.probe_url(url)

    assert result.ok
    assert result.file_path
    assert not result.use_stream_extractor
    assert Path(result.file_path).suffix == ".mp4"


def test_probe_html_uses_extractor(tmp_path: Path) -> None:
    manager = DownloadManager(tmp_path)
    url = "https://www.youtube.com/watch?v=test123"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html"}

    with patch("app.downloads.download_manager.requests.head", return_value=mock_resp):
        with patch(
            "app.downloads.download_manager.is_extractor_available",
            return_value=True,
        ):
            result = manager.probe_url(url)

    assert result.ok
    assert result.use_stream_extractor
