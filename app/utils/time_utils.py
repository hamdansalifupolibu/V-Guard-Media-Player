"""Time formatting helpers for playback UI."""

from __future__ import annotations


def format_timestamp(seconds: float, *, hms: bool = False) -> str:
    """Format seconds as HH:MM:SS (mockup style) or MM:SS when short."""
    if seconds < 0:
        seconds = 0
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hms or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
