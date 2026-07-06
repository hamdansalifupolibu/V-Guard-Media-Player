"""Basic unit tests for utilities."""

from app.utils.time_utils import format_timestamp


def test_format_timestamp_seconds_only():
    assert format_timestamp(65) == "01:05"


def test_format_timestamp_with_hours():
    assert format_timestamp(3661, hms=True) == "01:01:01"
