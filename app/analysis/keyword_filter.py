"""Match transcript words against a blocked keyword list."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.analysis.speech_detector import TranscriptSegment, TranscriptWord
from app.config import (
    AUDIO_KEYWORD_MERGE_GAP_SEC,
    AUDIO_MODERATION_LEAD_SEC,
    AUDIO_MODERATION_TRAIL_SEC,
    BLOCKED_WORDS_PATH,
)
from app.moderation.timestamp_manager import TimestampRange, group_flagged_frames


AUDIO_UNSAFE_LABEL = "unsafe_audio"


@dataclass(frozen=True)
class KeywordHit:
    word: str
    matched_keyword: str
    start_sec: float
    end_sec: float
    confidence: float


class KeywordFilter:
    """Load blocked words and find timestamp ranges from transcript."""

    def __init__(self, wordlist_path: Path | None = None) -> None:
        self.wordlist_path = Path(wordlist_path or BLOCKED_WORDS_PATH)
        self._blocked = self._load_words()

    def _load_words(self) -> set[str]:
        if not self.wordlist_path.is_file():
            return set()
        words: set[str] = set()
        for line in self.wordlist_path.read_text(encoding="utf-8").splitlines():
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            words.add(line)
        return words

    @property
    def blocked_words(self) -> set[str]:
        return set(self._blocked)

    def reload(self) -> None:
        self._blocked = self._load_words()

    def find_hits(self, segments: list[TranscriptSegment]) -> list[KeywordHit]:
        """Return every blocked word occurrence with timestamps."""
        if not self._blocked:
            return []

        hits: list[KeywordHit] = []
        for segment in segments:
            for word in segment.words:
                matched = self._match_word(word.word)
                if matched:
                    hits.append(
                        KeywordHit(
                            word=word.word,
                            matched_keyword=matched,
                            start_sec=max(0.0, word.start_sec),
                            end_sec=word.end_sec,
                            confidence=word.confidence,
                        )
                    )
            # Phrase-level match on full segment text (multi-word blocked lines)
            segment_hits = self._match_segment_phrases(segment)
            hits.extend(segment_hits)

        return hits

    def _match_segment_phrases(self, segment: TranscriptSegment) -> list[KeywordHit]:
        """Detect blocked phrases that span multiple words in one segment."""
        if not segment.words:
            return []
        text = segment.text.lower()
        found: list[KeywordHit] = []
        for blocked in self._blocked:
            if " " not in blocked or blocked not in text:
                continue
            start_w = segment.words[0]
            end_w = segment.words[-1]
            found.append(
                KeywordHit(
                    word=blocked,
                    matched_keyword=blocked,
                    start_sec=start_w.start_sec,
                    end_sec=end_w.end_sec,
                    confidence=min(w.confidence for w in segment.words),
                )
            )
        return found

    def _match_word(self, token: str) -> str | None:
        clean = re.sub(r"[^a-z0-9']+", "", token.lower())
        if not clean:
            return None
        if clean in self._blocked:
            return clean
        for blocked in self._blocked:
            if " " in blocked and blocked in token.lower():
                return blocked
        return None

    def scan_segments(
        self,
        segments: list[TranscriptSegment],
        *,
        video_duration_sec: float | None = None,
    ) -> tuple[list[KeywordHit], list[TimestampRange]]:
        hits = self.find_hits(segments)
        if not hits:
            return [], []

        flagged = [
            (h.start_sec, h.confidence, f"{AUDIO_UNSAFE_LABEL}:{h.matched_keyword}")
            for h in hits
        ]
        # Word timings are dense; use small sample interval + scene padding (2s each side)
        return hits, group_flagged_frames(
            flagged,
            sample_interval_sec=0.25,
            max_gap_sec=AUDIO_KEYWORD_MERGE_GAP_SEC,
            lead_sec=AUDIO_MODERATION_LEAD_SEC,
            trail_sec=AUDIO_MODERATION_TRAIL_SEC,
            lead_frames=0,
            trail_frames=0,
            video_duration_sec=video_duration_sec,
        )
