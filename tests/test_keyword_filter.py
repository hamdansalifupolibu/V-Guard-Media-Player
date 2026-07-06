"""Tests for keyword matching and range grouping."""

from pathlib import Path

from app.analysis.keyword_filter import KeywordFilter
from app.analysis.speech_detector import TranscriptSegment, TranscriptWord


def test_keyword_hits_and_ranges(tmp_path: Path) -> None:
    words_file = tmp_path / "blocked.txt"
    words_file.write_text("stupid\ndamn\n", encoding="utf-8")

    segments = [
        TranscriptSegment(
            text="that was stupid",
            start_sec=1.0,
            end_sec=2.5,
            words=(
                TranscriptWord("that", 1.0, 1.2, 0.9),
                TranscriptWord("was", 1.2, 1.4, 0.9),
                TranscriptWord("stupid", 1.4, 2.0, 0.85),
            ),
        ),
        TranscriptSegment(
            text="damn it",
            start_sec=10.0,
            end_sec=11.0,
            words=(
                TranscriptWord("damn", 10.0, 10.4, 0.9),
                TranscriptWord("it", 10.4, 10.8, 0.9),
            ),
        ),
    ]

    filt = KeywordFilter(words_file)
    hits, ranges = filt.scan_segments(segments)
    assert len(hits) == 2
    assert len(ranges) == 2
    assert ranges[0].start_time <= 1.4
    assert "unsafe_audio" in ranges[0].label


def test_empty_wordlist(tmp_path: Path) -> None:
    words_file = tmp_path / "empty.txt"
    words_file.write_text("# only comments\n", encoding="utf-8")
    filt = KeywordFilter(words_file)
    hits, ranges = filt.scan_segments([])
    assert hits == []
    assert ranges == []
