# Known Issues and Limitations

| Area | Issue | Workaround |
|------|-------|------------|
| Visual AI | Open-NSFW can misclassify safe/unsafe content | Adjust threshold in Settings; disable false segments in scan results |
| Audio STT | Vosk English model; not perfect on noisy audio | Edit `data/blocked_words.txt`; rescan after keyword changes |
| Playback | VLC must be installed separately | Install from https://www.videolan.org/vlc/ |
| Fullscreen | Rare black video until resize | Toggle fullscreen off/on; VLC rebind runs automatically |
| Downloads | Page URLs need yt-dlp + FFmpeg | `pip install yt-dlp` and `python scripts/install_ffmpeg.py` |
| Downloads | Very long videos / slow network | Wait for progress; cancel and retry if needed |
| Packaging | Large models not inside `.exe` | Copy `models/` folder next to distributed app (see PACKAGING.md) |
| Thesis metrics | Visual precision/recall need labeled frames | Follow `data/evaluation/VISUAL_VALIDATION_GUIDE.md` |

Last updated: Stage 13 testing pass.
