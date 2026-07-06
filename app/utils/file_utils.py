"""File path helpers."""

from pathlib import Path


def file_display_name(path: str | Path) -> str:
    """Return the file name for UI display."""
    return Path(path).name
