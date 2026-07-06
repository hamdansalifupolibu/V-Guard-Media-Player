# V-Guard Media Player

Desktop smart media player (BSc prototype) with **pre-scan content moderation**: Open-NSFW visual AI, Vosk keyword detection, a **dedicated explicit-sound CNN** (moans / sexual vocals), adjustable **content strictness**, playback moderation (mute / hide / skip), progressive scanning, and an **educational download manager**.

| Document | Purpose |
|----------|---------|
| [VGuard_README.md](VGuard_README.md) | Full roadmap, architecture, ethics |
| [V Guard player mock up.png](V%20Guard%20player%20mock%20up.png) | UI design reference |
| [data/evaluation/VISUAL_VALIDATION_GUIDE.md](data/evaluation/VISUAL_VALIDATION_GUIDE.md) | Labeled images for thesis metrics |

---

## How to run the app

### First-time setup (once)

```powershell
cd "C:\Users\Gebruiker\OneDrive\Desktop\V Guard project"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_visual_model.py
python scripts/download_vosk_model.py
python scripts/download_explicit_audio_model.py
python scripts/install_ffmpeg.py
```

Also install **VLC** ([videolan.org](https://www.videolan.org/vlc/)) on your system for video playback.

> **FFmpeg:** The install script above downloads a portable copy into `tools/ffmpeg/`. The app uses it automatically for scans and YouTube downloads — you do not need FFmpeg on your system PATH.

### Run every time

```powershell
cd "C:\Users\Gebruiker\OneDrive\Desktop\V Guard project"
.\venv\Scripts\activate
python app\main.py
```

### Other useful commands

```powershell
pytest tests -q
python scripts/smoke_check.py
python scripts/run_model_evaluation.py
python scripts/generate_thesis_figures.py
python scripts/download_explicit_audio_model.py
python scripts/prepare_explicit_audio_clip.py --help
python scripts/train_explicit_audio_cnn.py
python scripts/install_ffmpeg.py
.\scripts\build_windows.ps1
```

See [docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) and [docs/PACKAGING.md](docs/PACKAGING.md).

Edit blocked keywords: `data/blocked_words.txt` (or change the path in **Settings**).

---

## Requirements

| Component | Purpose |
|-----------|---------|
| Python 3.12 (3.10+) | Runtime |
| PySide6 | Desktop UI |
| VLC | Embedded video playback |
| FFmpeg | Audio extraction for scans; YouTube merge via yt-dlp |
| yt-dlp | Educational downloads from page URLs (YouTube, Vimeo, …) |
| Open-NSFW ONNX (~24 MB) | Visual classifier |
| Vosk English (~40 MB) | Offline speech-to-text |
| Explicit-sound CNN (~0.6 MB, after train script) | Log-mel classifier for moan / sexual vocal sounds |
| PyTorch + librosa | Train/run explicit audio model (no PANNs) |
| SQLite | Videos, detections, settings, download history |

---

## What we have implemented (full summary)

### Stages 1–4 — Foundation

| Area | What it does |
|------|----------------|
| **Project setup** | `venv`, `requirements.txt`, config paths, folder layout |
| **UI shell** | Three-column layout: sidebar navigation, center player, right panel (mockup-aligned) |
| **Video playback** | libVLC embedded in a Qt native surface (`app/playback/vlc_player.py`) |
| **SQLite database** | `videos`, `detections`, `settings`, `downloads`, `frame_predictions` |

### Stages 5–6 — Visual pre-scan

| Area | What it does |
|------|----------------|
| **Progressive (chunked) scan** | Video analyzed in **30 s chunks**; results saved after each chunk so you can play while the rest scans |
| **Frame sampling** | Default **2 s** between frames on short clips; **2–4 s** adaptive on long episodes (configurable in Settings) |
| **Visual AI** | Open-NSFW ONNX model scores each frame |
| **Scene ranges** | Flagged frames merged into one range per scene with **≥ 2 s padding** before and after (plus frame margin) |
| **Storage** | Detections + per-frame scores in SQLite for thesis plots |

### Stages 7–8 — Audio pre-scan

| Area | What it does |
|------|----------------|
| **Audio extraction** | FFmpeg extracts mono 16 kHz WAV from the video |
| **Speech-to-text** | Vosk (offline) transcribes with **word-level timestamps** |
| **Keyword filter** | Matches `data/blocked_words.txt` (words, phrases, segment-level) |
| **Explicit-sound CNN** | Small **log-mel CNN** (~0.6 MB) for moan / sexual vocal sounds — based on Lovenia et al. (2022) and mel annotations from [sexual-content-audio-classifier](https://github.com/xaverhimmelsbach/sexual-content-audio-classifier) (we train our own PyTorch weights; we do **not** ship the upstream 247 MB YOLO model) |
| **Audio ranges** | Keyword hits + explicit-sound hits merged with **≥ 2 s lead/trail** padding |
| **Detections** | Saved as `audio` rows (`unsafe_audio:…` for words, `audio_event:…` for explicit sounds) |
| **Settings toggle** | Enable/disable explicit-sound scan independently of Vosk |

### Stage 9 — Playback moderation

| Area | What it does |
|------|----------------|
| **Moderation modes** | None, mute audio, hide scene (blackout), hide + mute, skip scene |
| **Real-time enforcement** | Blackout for **visual** ranges; **mute** for visual + keyword + explicit-sound ranges |
| **Hide scene mode** | Blackout only on visual NSFW; audio-only flags (profanity, moans) **mute without** blacking out the picture |
| **Default mode** | **⬛🔇 Hide + mute** |
| **Scan-before-play** | Optional gate: prompt or auto-scan on load; first chunk unlocks playback (~20 s) |
| **User control** | Moderation cards on the player page; default mode in Settings |

### Stage 10 — Scan results

| Area | What it does |
|------|----------------|
| **Results dialog** | Lists visual and audio detections after a scan |
| **Enable / disable** | Turn individual segments on or off before playback |
| **Live reload** | Only enabled segments are applied during moderation |

### Stage 11 — Educational download manager

| Area | What it does |
|------|----------------|
| **URL input** | Paste any `http`/`https` video link |
| **Educational confirmation** | Checkbox: user confirms permission for educational use |
| **Direct downloads** | `.mp4`, `.webm`, university CDNs, etc. via `requests` streaming |
| **Page URLs** | YouTube, Vimeo, and similar via **yt-dlp** + **FFmpeg** merge |
| **Progress** | Progress bar and status text on a background thread |
| **History** | All downloads stored in SQLite; list with status colours |
| **Play in player** | Double-click or **Play in player** opens the file in the main player |
| **Portable FFmpeg** | `scripts/install_ffmpeg.py` + auto-detect in `tools/ffmpeg/bin/` |

See [How the download manager works](#how-the-download-manager-works) below for implementation detail.

### Stage 12 — Settings

| Area | What it does |
|------|----------------|
| **Content strictness** | Slider **Relaxed → Max safety** maps to Open-NSFW threshold (~0.65 → ~0.26); default ~82% catches suggestive frames (~0.34+ scores on validation images) |
| **Frame interval** | Seconds between sampled frames (default **2.0 s** on short clips; long episodes use adaptive 2–4 s) |
| **Scan toggles** | Enable/disable visual scan, audio (Vosk), and **explicit-sound CNN** |
| **Auto-scan on load** | Scan automatically when a video opens (no prompt) |
| **Require scan before play** | Block playback until the first scan chunk is ready |
| **Audio on long videos** | Run full audio pipeline on videos **> 45 min** (much slower) |
| **Blocked words path** | Custom path to keyword list |
| **Moderation default** | Default playback moderation mode (use **Hide + mute** for demos) |
| **Persistence** | All settings saved to SQLite; **re-scan** after changing strictness or audio options |

### UI and player polish (beyond original stages)

| Area | What it does |
|------|----------------|
| **Mockup-aligned UI** | Purple accent, sidebar, right panel, moderation cards |
| **Combined play/pause** | Single button toggles ▶ / ⏸ |
| **Mute icon** | 🔊 / 🔇 reflects mute state; volume slider restores level |
| **Controls below video** | Transport bar always visible in normal window mode |
| **Fullscreen** | Video fills the screen; sidebar and panels hidden |
| **VLC-style fullscreen bar** | Floating bar auto-hides while playing; any mouse move or key shows it; hides after ~4 s idle |
| **Keyboard shortcuts** | Space, ←/→, J/L, M, F, Esc |
| **Library** | Lists past videos from the database; open or double-click to play |
| **About** | App info panel |
| **Scan status** | Right panel shows scan state and detection counts |
| **Thesis figures** | Generate scan charts + model metric PNGs from the UI |

### Thesis and model evaluation

| Area | What it does |
|------|----------------|
| **Classification metrics** | Accuracy, precision, recall, F1, Brier, log loss, ROC-AUC |
| **Confusion matrix** | TP / TN / FP / FN plots |
| **Keyword metrics** | Word-level F1 on `data/evaluation/keyword_test_cases.json` |
| **Output** | `data/thesis/figures/M0–M6*.png`, JSON/CSV summaries |
| **Scripts** | `scripts/run_model_evaluation.py`, `scripts/generate_thesis_figures.py` |

### Tests

| Module | Coverage |
|--------|----------|
| Database | CRUD, settings, videos |
| Keyword filter | Blocked word matching |
| Moderation | Timestamp evaluation, skip/mute/hide, explicit-audio mute |
| Visual strictness | Threshold ↔ slider mapping |
| Explicit audio | CNN detector, scan pipeline integration |
| Progressive scan | Chunk helpers |
| Model metrics | Metric calculations |
| Download validator | URL rules, educational mode |
| FFmpeg helpers | Error messages, format selection |

Run: `pytest tests -q` (50+ tests).

---

## How moderation and scanning work

This section explains what happens when you press **Scan Video** or open a file with auto-scan enabled.

### Progressive scan (lazy-load style)

Long videos are **not** analyzed in one blocking pass:

1. The file is split into **chunks** (30 s default; **60–90 s** for long episodes).
2. Each chunk: sample frames → batched Open-NSFW → append scores → update moderation ranges.
3. After the **first chunk** (~20 s of coverage), playback can start; remaining chunks continue in the background.
4. **Audio** (FFmpeg + Vosk keywords + explicit-sound CNN) runs at the end — **skipped over 45 min** unless Settings → “Audio on long videos” is enabled.

**Long-video speedups (e.g. full TV episodes):** adaptive coarser sampling (2–4 s/frame), sequential frame reads, ONNX batches of 8, incremental DB updates, throttled progress UI. Visual **Hide + mute** still covers sex scenes without waiting for speech transcription.

If you seek **past** the scanned portion, the status bar warns that moderation only applies to analyzed time.

### Visual scene blackout (sexual / unsafe frames)

| Step | Detail |
|------|--------|
| Sampling | Frames every **2 s** by default (Settings → frame interval; use **1 s** for stricter coverage) |
| Model | Open-NSFW ONNX; score ≥ threshold → flagged |
| Strictness | Settings slider lowers threshold for stricter policy (re-scan required) |
| Merge | Nearby flagged samples become **one scene range** |
| Padding | **2 s before** the scene (covers slow model / sampling) and **1 s after** (avoids long blackout on safe footage) |
| Playback | Solid **black overlay** (not blur) when mode is Hide scene or Hide + mute |

**Important:** Re-scan videos after changing padding or interval — old detection rows in the database do not update automatically.

Example: flagged samples at 10 s and 12 s with 1 s interval → blackout roughly **8 s → 14 s** (2 s lead + sample window + 1 s trail).

### Audio moderation (three layers)

| Layer | What it catches | Label in DB |
|-------|-----------------|-------------|
| **Vosk + keywords** | Spoken profanity / blocked words | `unsafe_audio:keyword` |
| **Explicit-sound CNN** | Moan-like / sexual vocal sounds (non-verbal) | `audio_event:sexual vocal sound…` |
| **Combined** | Merged ranges with 2 s padding | `detection_type = audio` |

| Step | Detail |
|------|--------|
| Extract | FFmpeg → mono 16 kHz WAV |
| Keywords | Vosk transcribes → match `data/blocked_words.txt` |
| Explicit CNN | 2 s windows, 1 s hop, log-mel → binary CNN (threshold ~0.35) |
| Playback | **Mute** for any audio detection; **blackout** only for visual ranges in Hide scene mode |

Test explicit audio on a WAV clip:

```powershell
python tests/test_explicit_audio_detector.py "data\temp_audio\YourVideo_1_audio.wav"
```

### Explicit-sound CNN (setup and research basis)

| Item | Detail |
|------|--------|
| **Paper** | Lovenia et al. (2022), *What Did I Just Hear?* — CNN on log-mel spectrograms for pornographic sounds |
| **Training data** | Moan annotations from [sexual-content-audio-classifier](https://github.com/xaverhimmelsbach/sexual-content-audio-classifier) release (mel PNGs + VOC XML; **not** the 247 MB YOLO weights) |
| **Our weights** | `models/explicit_audio/explicit_audio_cnn.pt` (~0.6 MB), trained via `scripts/train_explicit_audio_cnn.py` |
| **One-time setup** | `python scripts/download_explicit_audio_model.py` (downloads training pack, trains CNN) |
| **In the app** | Settings → “Detect explicit sexual sounds”; results appear in **View results** → Audio tab as `audio_event:…` |

### Adding your own audio to improve the explicit-sound model

The default CNN is trained on a **small public set** (~86 spectrogram images). You will get better results on your own shows (e.g. TV episodes) if you add **short WAV clips** from permitted test material and **retrain**.

#### What you need

| Item | Guidance |
|------|----------|
| **Legal use** | Only audio you may use for research/education (your own recordings, licensed clips, or segments you are allowed to analyze). |
| **Clip length** | **5–30 seconds** per file works well (full-scene extracts). |
| **Format** | `.wav` (any sample rate; converted to 16 kHz mono internally). |
| **Positive clips** | Contain moan / sexual vocal sounds — note **start and end time** of each moan in seconds. |
| **Negative clips** | Safe dialogue, music, battle, news, outdoor ambience — **no** moan regions. |
| **Balance** | Add both types; aim for at least **10–20 clips per class** before expecting a clear improvement. |

#### Step 1 — Extract audio from a video (FFmpeg)

After scanning a video in V-Guard, a WAV may already exist under `data/temp_audio/`. Or extract manually:

```powershell
ffmpeg -y -i "C:\path\to\episode.mp4" -vn -acodec pcm_s16le -ar 16000 -ac 1 "data\my_clips\scene_01.wav"
```

Cut a shorter segment (e.g. only the moan window plus ~2 s context):

```powershell
ffmpeg -y -i "data\my_clips\scene_01.wav" -ss 120 -to 135 -c copy "data\my_clips\scene_01_moan.wav"
```

#### Step 2 — Register the clip in the training set

Use the helper script (creates mel PNG + annotation XML under `data/explicit_audio_training/`):

**Positive** (moan between 3 s and 6 s):

```powershell
python scripts/prepare_explicit_audio_clip.py ^
  --wav "data\my_clips\scene_01_moan.wav" ^
  --split train ^
  --label positive ^
  --moan-start 3 ^
  --moan-end 6
```

**Negative** (safe speech, no moans):

```powershell
python scripts/prepare_explicit_audio_clip.py ^
  --wav "data\my_clips\safe_dialogue.wav" ^
  --split train ^
  --label negative
```

Multiple moan regions in one clip:

```powershell
python scripts/prepare_explicit_audio_clip.py ^
  --wav "data\my_clips\two_moans.wav" ^
  --split train ^
  --label positive ^
  --moan-start 2 --moan-end 4 ^
  --moan-start 9 --moan-end 11
```

Put ~20% of clips in `--split validation` for a honest validation score during training.

#### Step 3 — Retrain and deploy

```powershell
python scripts/train_explicit_audio_cnn.py
```

This overwrites `models/explicit_audio/explicit_audio_cnn.pt`. Then:

1. **Re-scan** videos in the app (Settings → explicit sounds on).
2. Test a clip: `python tests/test_explicit_audio_detector.py "data\temp_audio\YourVideo_1_audio.wav"`

#### Tips for better models

| Tip | Why |
|-----|-----|
| Mark moan times accurately | Wrong boxes teach the CNN the wrong horizontal band on the spectrogram. |
| Include hard negatives | Dialogue, dramatic screaming, loud music — reduces false mutes. |
| Match your target content | GOT-style clips help GOT; add beach/dialogue negatives if those cause false positives. |
| Re-train after every batch | Old weights do not include new clips until you run `train_explicit_audio_cnn.py`. |
| Keep a copy of `explicit_audio_cnn.pt` | Rename backups (e.g. `explicit_audio_cnn_v2.pt`) before experimenting. |

Folder layout after adding clips:

```
data/explicit_audio_training/
├── train/
│   ├── images/          # *.png mel spectrograms (auto-generated)
│   └── annotations/     # *.xml — Moan boxes for positive clips
└── validation/
    ├── images/
    └── annotations/
```

### Recommended demo settings

1. Settings → **Hide + mute** as default moderation mode.
2. **Content strictness** → **Very strict** or **Max safety** for TV/film with nudity; **re-scan** after changing.
3. Enable **explicit sexual sounds** and ensure `python scripts/download_explicit_audio_model.py` has been run once.
4. **Require scan before play** = on; **Auto-scan on load** = optional.
5. Frame interval **1.0–2.0 s** for important demos (lower = slower, better coverage).

---

## How the download manager works

This is the main design behind Stage 11 — written so you can explain it in a report or viva.

### Goal

Let students and researchers download videos they are **allowed** to use for education, without building a piracy tool. The app supports:

1. **Direct file links** — URL points straight at a `.mp4` (or similar).
2. **Page links** — URL is a YouTube/Vimeo watch page; the app extracts the real video file.

### Architecture

```
DownloadsPanel (UI)
    → DownloadWorker (QThread, non-blocking UI)
        → DownloadManager
            → url_validator.py     (format + educational rules)
            → requests (stream)    (direct HTTP download)
            → educational_extractor.py + yt-dlp (page URLs)
            → ffmpeg_path.py       (bundled or system FFmpeg)
    → VGuardDatabase (downloads table — history)
```

### Key files

| File | Role |
|------|------|
| `app/ui/downloads_panel.py` | URL field, educational checkbox, progress bar, history list, play/folder buttons |
| `app/downloads/url_validator.py` | Accepts any `http`/`https` URL in educational mode; detects direct vs page links |
| `app/downloads/download_manager.py` | HEAD probe, chooses direct vs extractor path, streams bytes to disk |
| `app/downloads/educational_extractor.py` | Wraps **yt-dlp**; passes `ffmpeg_location` for merge; cleans error messages |
| `app/downloads/download_worker.py` | Background thread; updates SQLite status (`pending` → `downloading` → `complete` / `failed`) |
| `app/utils/ffmpeg_path.py` | Finds `tools/ffmpeg/bin/ffmpeg.exe` first, then system PATH |
| `scripts/install_ffmpeg.py` | One-time download of portable FFmpeg (BtbN win64 build) |

### Direct download flow

1. User pastes URL and confirms educational use.
2. `validate_download_url()` checks scheme and host.
3. `DownloadManager.probe_url()` sends HTTP **HEAD** (or GET) to read `Content-Type` and `Content-Disposition`.
4. If the response is a video file, a unique path under `data/downloads/` is chosen.
5. `requests.get(..., stream=True)` downloads in 256 KB chunks; progress callbacks update the UI.
6. SQLite row is updated with `file_path` and `status=complete`.

### YouTube / page URL flow

1. Server returns `text/html` → validator sets `use_stream_extractor=True`.
2. App checks **yt-dlp** is installed (`pip install yt-dlp`).
3. App resolves **FFmpeg** via `resolve_ffmpeg_dir()` (bundled `tools/ffmpeg/bin` preferred).
4. yt-dlp options:
   - `format`: merged best MP4 if FFmpeg exists; otherwise single-file `best[ext=mp4]/best` (no merge).
   - `ffmpeg_location`: points at bundled bin folder.
   - `merge_output_format`: `mp4` when FFmpeg is available.
5. Progress hooks emit byte counts to the progress bar.
6. Finished file path is stored in SQLite; user can play it in the main player.

### Why portable FFmpeg?

Many Windows machines do not have FFmpeg on PATH. Chocolatey/winget installs can hang or need admin rights. Bundling FFmpeg inside the project means:

- `python scripts/install_ffmpeg.py` — one command, no admin.
- `app/main.py` calls `ensure_ffmpeg_on_path()` at startup.
- yt-dlp always receives `ffmpeg_location` so YouTube merge works reliably.

### Educational safeguards (UI + ethics)

- Checkbox: *“I confirm this is for educational use and I have permission to download.”*
- On-screen note when FFmpeg is missing (orange) or detected (green).
- Errors are stripped of ANSI colour codes and show actionable text (e.g. run `install_ffmpeg.py`).
- User is responsible for copyright and terms of use; the app does not bypass DRM or logins.

### Using downloads in the app

1. Sidebar → **Downloads**.
2. Confirm the educational checkbox.
3. Paste URL → **Download**.
4. Wait for progress → item appears in **Download history**.
5. **Play in player** or double-click to watch and optionally **Scan Video**.

---

## Using the app (quick reference)

| Control | Action |
|---------|--------|
| **Open** | Load a local video |
| **Play/Pause** | One button toggles ▶ / ⏸ |
| **Stop** | Stop playback |
| **Seek bar** | Jump in video |
| **Volume / Mute** | Slider + 🔊/🔇 toggle |
| **Fullscreen** | Button, **F**, or double-click video; **Esc** to exit |
| **Normal mode** | Control bar below the video (always visible) |
| **Fullscreen mode** | Video fills screen; bar auto-hides; mouse or keyboard shows it |
| **Keyboard** | Space, ←/→, J/L, M, F, Esc |
| **Settings** | Content strictness, scan toggles, keywords, explicit audio, moderation default |
| **Scan Video** | Progressive pre-scan (chunks); first ~20 s unlocks play |
| **View results** | Enable/disable flagged segments |
| **Moderation cards** | Mute / hide / skip during playback |
| **Library** | Re-open videos from the database |
| **Downloads** | Educational download with progress and history |

---

## Project structure

```
V Guard project/
├── app/
│   ├── main.py                 # Entry point
│   ├── config.py               # Paths, defaults, VLC args
│   ├── analysis/               # Scan pipeline (visual, Vosk, explicit-audio CNN, keywords)
│   │   └── explicit_audio/     # Log-mel features + CNN model code
│   ├── database/               # SQLite schema, db.py, models
│   ├── downloads/              # URL validation, manager, yt-dlp extractor
│   ├── moderation/             # Playback enforcement
│   ├── playback/               # VLC + playback controller
│   ├── reporting/              # Thesis figures + model metrics
│   ├── ui/                     # All panels and player chrome
│   └── utils/                  # Time, files, FFmpeg path
├── data/
│   ├── downloads/              # Downloaded video files
│   ├── evaluation/             # Test cases + visual validation guide
│   ├── thesis/figures/         # Generated charts (M0–M6, scan plots)
│   └── blocked_words.txt
├── models/
│   ├── visual_model/           # Open-NSFW ONNX
│   ├── vosk/                   # Speech model
│   └── explicit_audio/         # explicit_audio_cnn.pt (after train script)
├── scripts/
│   ├── download_visual_model.py
│   ├── download_vosk_model.py
│   ├── download_explicit_audio_model.py
│   ├── download_explicit_audio_data.py
│   ├── prepare_explicit_audio_clip.py
│   ├── train_explicit_audio_cnn.py
│   └── install_ffmpeg.py, …
├── tests/                      # pytest suite
├── tools/ffmpeg/bin/           # Portable FFmpeg (after install_ffmpeg.py)
└── requirements.txt
```

---

## Implementation status (roadmap)

| Stage | Feature | Status |
|-------|---------|--------|
| 1–4 | Setup, UI, playback, SQLite | Done |
| 5–6 | Frame sampling + visual AI | Done |
| 7–8 | FFmpeg + Vosk + keywords + explicit-sound CNN | Done |
| 9 | Playback moderation | Done |
| 10 | Scan results enable/disable | Done |
| 11 | Educational download manager | Done |
| 12 | Settings panel | Done |
| — | Library, About, UI polish, fullscreen, thesis metrics | Done |
| — | Visual **content strictness** slider; PANNs removed → explicit CNN | Done |
| 13 | Testing checklist, smoke script, extra tests | Done |
| 14 | PyInstaller Windows build (`dist/VGuard/`) | Done |
| 15 | Slides, demo script, final report assets | Planned |

---

## Packaging (Stage 14)

```powershell
.\scripts\build_windows.ps1
```

Creates `dist\VGuard\VGuard.exe` plus bundled app files. Copy the whole `dist\VGuard` folder to another PC; install **VLC** there. Details: [docs/PACKAGING.md](docs/PACKAGING.md).

## Testing (Stage 13)

```powershell
pytest tests -q
python scripts/smoke_check.py
```

Manual demo checklist: [docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md)  
Known issues: [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)

## Visual model evaluation (before Stage 14–15)

V-Guard uses a **pre-trained** Open-NSFW model (not trained inside this app). You still need **labeled test images** so your thesis can report precision, recall, and F1.

1. Download images (see [data/evaluation/VISUAL_VALIDATION_GUIDE.md](data/evaluation/VISUAL_VALIDATION_GUIDE.md)):
   - **Safe:** Pexels, Pixabay, Unsplash (15–30 images) → `data/evaluation/frames/safe/`
   - **Unsafe:** frames from your own test videos or FFmpeg screenshots (10–20) → `data/evaluation/frames/unsafe/`
2. Build the label file:

```powershell
python scripts/build_visual_labels_csv.py
python scripts/run_model_evaluation.py
```

3. Check charts in `data/thesis/figures/M0–M6*.png`.

**Recommended order:** validation images → evaluation metrics → Stage 14 build → Stage 15 presentation.

## What is next (recommended order)

| Priority | Task | Why |
|----------|------|-----|
| 1 | **Run explicit audio setup** | `python scripts/download_explicit_audio_model.py` (once) |
| 2 | **Re-scan test videos** | Strictness, explicit CNN, and padding only apply after a fresh scan |
| 3 | **Validation images** | `data/evaluation/frames/` → `build_visual_labels_csv.py` + `run_model_evaluation.py` |
| 4 | **Demo rehearsal** | [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) — hide + mute, GOT/test clips |
| 5 | **Stage 14 build** | `.\scripts\build_windows.ps1` → test on another PC (VLC required) |
| 6 | **Stage 15** | Slides, report — use `data/thesis/figures/M0–M6` |
| 7 | **Optional tuning** | Stricter visual slider; lower frame interval; retrain explicit CNN with more clips |

### Known limitations (honest, for thesis)

| Item | Description |
|------|-------------|
| **Visual model** | Open-NSFW under-scores some policy-unsafe stills (e.g. bikini ~0.06); strictness slider helps from ~0.34+ |
| **Explicit audio CNN** | Trained on a small public moan-spectrogram set (~86 clips); will miss some TV scenes — combine with visual + keywords |
| **No PANNs** | Generic AudioSet taggers removed; replaced by purpose-built explicit-sound CNN |
| **Blur effect** | Blackout only; blur is future work |
| **100% coverage** | Frame sampling (1–4 s) can miss very short cuts; audio uses 2 s windows |
| **Long videos** | Audio scan skipped over **45 min** unless Settings → “Audio on long videos” |
| **Resolution metadata** | Now Playing resolution field (optional) |

---

## Thesis figures

After running the evaluation scripts, see `data/thesis/figures/`:

| File | Meaning |
|------|---------|
| **M0** | Summary of all metrics |
| **M1** | Confusion matrix |
| **M2** | ROC curve |
| **M3** | Precision–recall curve |
| **M4** | Calibration / Brier score |
| **M5** | Metrics vs threshold |
| **M6** | Keyword filter F1 |
| **01–07** | Scan-related charts from database |

```powershell
python scripts/run_model_evaluation.py
python scripts/generate_thesis_figures.py
```

---

## References

Key sources and tools cited in this project (use your faculty’s citation style in the thesis; examples below are APA-like).

### Visual moderation

1. **Yahoo Open-NSFW model** — Pre-trained ONNX classifier for adult visual content, used as V-Guard’s visual detector.  
   Yahoo Research (2016). *Open NSFW Model*.  
   https://github.com/yahoo/open_nsfw

2. **ONNX Runtime** — Inference engine for the visual model.  
   Microsoft (2024). *ONNX Runtime*.  
   https://onnxruntime.ai/

### Speech and keywords

3. **Vosk** — Offline speech recognition for word-level timestamps and keyword matching.  
   Alpacephei (2024). *Vosk Speech Recognition Toolkit*.  
   https://alphacephei.com/vosk/

4. **Kaldi** (indirect) — Architecture lineage for Vosk acoustic models.  
   Povey, D., et al. (2011). *The Kaldi Speech Recognition Toolkit*. IEEE ASRU.

### Explicit / sexual sound detection

5. **Lovenia et al. (2022)** — CNN on log-mel spectrograms for pornographic sound detection; primary research basis for our explicit-audio approach.  
   Lovenia, H., Lestari, D. P., & Frieske, R. (2022). *What Did I Just Hear? Detecting Pornographic Sounds in Adult Videos Using Neural Networks*. Proceedings of Audio Mostly (AM ’22). arXiv:2209.03711.  
   https://doi.org/10.1145/3561212.3561244

6. **Pornography-800** — Dataset cited in Lovenia et al. for adult vs non-adult video audio research.  
   Garcia-Ortega, J. H., et al. *Pornography Database* (Pornography-800).  
   https://sites.google.com/site/pornographydatabase/

7. **sexual-content-audio-classifier** — Open-source mel-spectrogram + moan annotations; training data for our CNN (we train a small PyTorch model, not the upstream YOLO weights).  
   Himmelsbach, X. (2022). *Supporting the Detection of Sexual Content in Videos by Listening for Characteristic Sounds* (term paper).  
   https://github.com/xaverhimmelsbach/sexual-content-audio-classifier

8. **librosa** — Audio loading, mel spectrograms, and training export.  
   McFee, B., et al. (2023). *librosa: Audio and Music Signal Analysis in Python*.  
   https://librosa.org/

9. **PyTorch** — Explicit-sound CNN training and inference.  
   Paszke, A., et al. (2019). *PyTorch: An Imperative Style, High-Performance Deep Learning Library*. NeurIPS.

### General audio tagging (replaced in V-Guard)

10. **PANNs (Cnn10)** — Previously considered; replaced because AudioSet tagging is not explicit-sound-specific. Listed for comparison in the thesis.  
    Kong, Q., et al. (2020). *PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern Recognition*. IEEE/ACM Transactions on Audio, Speech, and Language Processing.  
    https://github.com/qiuqiangkong/audioset_tagging_cnn

11. **AudioSet** — Label ontology underlying PANNs and YAMNet-class models.  
    Gemmeke, J. F., et al. (2017). *Audio Set: An ontology and human-labeled dataset for audio events*. ICASSP.

### Application stack

12. **PySide6 / Qt** — Desktop user interface.  
    The Qt Company (2024). *Qt for Python (PySide6)*.  
    https://doc.qt.io/qtforpython/

13. **VLC / libVLC** — Video playback.  
    VideoLAN (2024). *VLC media player*.  
    https://www.videolan.org/vlc/

14. **FFmpeg** — Audio extraction and YouTube merge.  
    FFmpeg Developers (2024). *FFmpeg*.  
    https://ffmpeg.org/

15. **yt-dlp** — Educational downloads from page URLs.  
    yt-dlp contributors (2024). *yt-dlp*.  
    https://github.com/yt-dlp/yt-dlp

16. **SQLite** — Local database for videos, detections, and settings.  
    SQLite Consortium (2024). *SQLite*.  
    https://www.sqlite.org/

### Evaluation and packaging

17. **scikit-learn** — Classification metrics (precision, recall, F1, ROC-AUC) for thesis figures.  
    Pedregosa, F., et al. (2011). *Scikit-learn: Machine Learning in Python*. JMLR.

18. **PyInstaller** — Windows executable build (Stage 14).  
    PyInstaller Development Team (2024). *PyInstaller*.  
    https://pyinstaller.org/

---

## Ethics and legal use

- Processing is **local** — no cloud upload of video content.
- Detection is **not 100% accurate** — false positives and negatives are possible.
- Use **legal, permitted** media for testing and demos.
- **Downloads:** only content you have the right to use for education or research; the app does not bypass DRM or paid subscriptions.
- **Keywords and visual model** are aids for moderation research, not a substitute for human judgment.

---

## Tests

```powershell
.\venv\Scripts\activate
pytest tests -q
```

---

*V-Guard Media Player — BSc prototype. Safe Media. Smart Protection.*
