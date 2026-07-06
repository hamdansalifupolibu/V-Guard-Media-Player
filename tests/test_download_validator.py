"""Tests for educational download URL validation."""

from app.downloads.url_validator import validate_download_url


def test_rejects_empty_url() -> None:
    result = validate_download_url("")
    assert not result.ok


def test_accepts_youtube_for_education() -> None:
    result = validate_download_url(
        "https://www.youtube.com/watch?v=abc123",
        educational=True,
    )
    assert result.ok


def test_accepts_direct_mp4_path() -> None:
    result = validate_download_url(
        "https://cdn.example.org/education/lecture01.mp4"
    )
    assert result.ok
    assert result.suggested_filename.endswith(".mp4")


def test_accepts_video_content_type() -> None:
    result = validate_download_url(
        "https://files.example.org/stream/clip",
        content_type="video/mp4",
    )
    assert result.ok


def test_educational_html_uses_extractor() -> None:
    result = validate_download_url(
        "https://www.youtube.com/watch?v=abc",
        content_type="text/html",
        educational=True,
    )
    assert result.ok
    assert result.use_stream_extractor


def test_rejects_non_http() -> None:
    result = validate_download_url("ftp://example.org/video.mp4")
    assert not result.ok
