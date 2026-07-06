"""Tests for adaptive scan profiles."""

from app.analysis.scan_profile import build_scan_profile


def test_short_clip_keeps_user_interval():
    p = build_scan_profile(
        120.0,
        user_interval_sec=1.0,
        user_chunk_sec=30.0,
        audio_enabled=True,
    )
    assert p.sample_interval_sec == 1.0
    assert p.run_audio is True
    assert not p.long_form


def test_long_episode_coarser_sampling():
    p = build_scan_profile(
        3600.0,
        user_interval_sec=1.0,
        user_chunk_sec=30.0,
        audio_enabled=True,
    )
    assert p.sample_interval_sec >= 3.0
    assert p.long_form
    assert not p.run_audio
    assert p.audio_skip_reason
