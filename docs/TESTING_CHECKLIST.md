# V-Guard Testing Checklist (Stage 13)

Use this before a demo, viva, or submission. Run automated checks first, then manual UI tests.

## Automated

```powershell
cd "C:\Users\Gebruiker\OneDrive\Desktop\V Guard project"
.\venv\Scripts\activate
pytest tests -q
python scripts/smoke_check.py
```

| Check | Command | Expected |
|-------|---------|----------|
| Unit/integration tests | `pytest tests -q` | All passed |
| Dependencies + models | `python scripts/smoke_check.py` | All `[OK]` |

## Manual — Player

| # | Test | Pass? |
|---|------|-------|
| 1 | Open `.mp4` from disk | Plays with picture and sound |
| 2 | Play / pause / stop | Single play-pause button toggles correctly |
| 3 | Seek bar | Position updates; seek works |
| 4 | Volume and mute | Mute icon changes; volume restores |
| 5 | Fullscreen (F) | Video fills screen; bar hides while playing |
| 6 | Mouse move in fullscreen | Control bar appears |
| 7 | Keyboard ← / → | Skips ±10 s; bar appears in fullscreen |
| 8 | Esc exits fullscreen | Returns to normal layout |

## Manual — Pre-scan and moderation

| # | Test | Pass? |
|---|------|-------|
| 9 | Scan Video | Progressive chunks; first segment unlocks play; completes in background |
| 10 | View results | Visual/audio segments listed |
| 11 | Disable a segment | Toggle off; count updates |
| 12 | Moderation cards | Emoji labels; selected card has purple border + tint (stays until changed) |
| 13 | Moderation: mute | Audio muted in flagged range |
| 14 | Moderation: hide | Blackout ~2 s before scene, ~1 s after |
| 15 | Moderation: hide + mute | Both effects together |
| 16 | Moderation: skip | Jumps past flagged range |

## Manual — Downloads

| # | Test | Pass? |
|---|------|-------|
| 17 | Direct `.mp4` URL | Downloads to `data/downloads/` |
| 18 | YouTube URL (educational checkbox) | Extracts with yt-dlp + FFmpeg |
| 19 | Play in player | Opens downloaded file |
| 20 | History list | Shows status (complete / failed) |

## Manual — Other pages

| # | Test | Pass? |
|---|------|-------|
| 21 | Library | Lists previously opened videos |
| 22 | Settings | Save threshold / toggles; persists after restart |
| 23 | Generate figures | PNGs in `data/thesis/figures/` |
| 24 | Model evaluation | `python scripts/run_model_evaluation.py` — M0–M6 updated |

## Video formats to try (optional)

| Format | Extension |
|--------|-----------|
| MP4 | `.mp4` |
| MKV | `.mkv` |
| AVI | `.avi` |
| WebM | `.webm` |

## Known limitations

- Visual model: false positives/negatives possible; needs labeled validation set for thesis metrics.
- Vosk: English small model; accent/noisy audio may reduce accuracy.
- VLC embed: requires VLC installed on Windows.
- Downloads: user must have permission; DRM/login-protected sites not supported.

Record any failures in `docs/KNOWN_ISSUES.md`.
