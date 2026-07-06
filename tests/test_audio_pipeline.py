"""AudioScanPipeline settings gates and soft-failure behaviour."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.analysis.audio_pipeline import AudioScanPipeline
from app.config import SETTING_ENABLE_AUDIO, SETTING_ENABLE_EXPLICIT_AUDIO


@pytest.fixture
def db(tmp_path: Path) -> MagicMock:
    mock = MagicMock()
    mock.get_setting.return_value = None
    mock.get_video_by_id.return_value = None
    return mock


def test_audio_disabled_returns_zero(db: MagicMock) -> None:
    db.get_setting.side_effect = lambda key: (
        "false" if key == SETTING_ENABLE_AUDIO else None
    )
    pipeline = AudioScanPipeline(db)
    count, warning = pipeline.run(1, Path("missing.mp4"))
    assert count == 0
    assert "disabled" in warning.lower()


def test_missing_ffmpeg_warning(db: MagicMock) -> None:
    with patch(
        "app.analysis.audio_pipeline.AudioExtractor.is_ffmpeg_available",
        return_value=False,
    ):
        pipeline = AudioScanPipeline(db)
        count, warning = pipeline.run(1, Path("video.mp4"))
    assert count == 0
    assert "ffmpeg" in warning.lower()


@patch("app.analysis.audio_pipeline.AudioExtractor.is_ffmpeg_available", return_value=True)
@patch("app.analysis.audio_pipeline.AudioExtractor.extract")
def test_explicit_scan_runs_when_enabled(
    extract: MagicMock,
    _ffmpeg: MagicMock,
    db: MagicMock,
    tmp_path: Path,
) -> None:
    wav = tmp_path / "1.wav"
    wav.write_bytes(b"RIFF")
    extract.return_value = wav

    db.get_setting.side_effect = lambda key: (
        "true"
        if key in (SETTING_ENABLE_AUDIO, SETTING_ENABLE_EXPLICIT_AUDIO)
        else None
    )

    with patch.object(
        AudioScanPipeline,
        "_run_keyword_scan",
        return_value=([], []),
    ), patch.object(
        AudioScanPipeline,
        "_run_explicit_scan",
        return_value=([], []),
    ) as explicit:
        pipeline = AudioScanPipeline(db)
        pipeline.run(1, tmp_path / "video.mp4")
        explicit.assert_called_once()
