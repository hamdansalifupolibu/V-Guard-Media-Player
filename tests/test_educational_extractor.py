"""Tests for educational extractor helpers."""

from app.downloads.educational_extractor import _clean_error_message, _format_selector


def test_clean_error_strips_ansi_and_ffmpeg_hint() -> None:
    raw = "\x1b[0;31mERROR:\x1b[0m merging of multiple formats but ffmpeg is not installed"
    msg = _clean_error_message(Exception(raw))
    assert "FFmpeg" in msg
    assert "\x1b" not in msg


def test_format_selector_without_merge_when_no_ffmpeg(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.downloads.educational_extractor.is_ffmpeg_available",
        lambda: False,
        raising=False,
    )
    monkeypatch.setattr(
        "app.utils.ffmpeg_path.is_ffmpeg_available",
        lambda: False,
    )
    assert "+" not in _format_selector()


def test_format_selector_allows_merge_with_ffmpeg(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.downloads.educational_extractor.is_ffmpeg_available",
        lambda: True,
        raising=False,
    )
    monkeypatch.setattr(
        "app.utils.ffmpeg_path.is_ffmpeg_available",
        lambda: True,
    )
    assert "+" in _format_selector()
