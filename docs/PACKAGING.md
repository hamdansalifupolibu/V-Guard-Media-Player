# Packaging V-Guard (Stage 14)

## What you get

A **Windows folder** `dist/VGuard/` containing:

- `VGuard.exe` — main application (no console window)
- Python runtime and PySide6 libraries (PyInstaller onedir)
- `tools/ffmpeg/bin/` — portable FFmpeg (if built from a machine that ran `install_ffmpeg.py`)
- `data/blocked_words.txt` — default keyword list
- `models/` — copied by build script if present on the build machine

## Prerequisites on the build machine

```powershell
cd "C:\Users\Gebruiker\OneDrive\Desktop\V Guard project"
.\venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_visual_model.py
python scripts/download_vosk_model.py
python scripts/install_ffmpeg.py
python scripts/smoke_check.py
```

**VLC** must be installed on any PC that **runs** the app (not bundled by PyInstaller).

## Build steps

```powershell
.\venv\Scripts\activate
.\scripts\build_windows.ps1
```

Output: `dist\VGuard\VGuard.exe`

First build may take several minutes.

## Distributing to another PC

Copy the entire **`dist\VGuard`** folder (or zip it). On the target machine:

1. Install **VLC** — https://www.videolan.org/vlc/
2. Ensure `models/visual_model/open_nsfw.onnx` and Vosk folder exist inside the copy.
3. Double-click **`VGuard.exe`**.
4. First run creates `data/` next to the exe (database, downloads, thesis figures).

## What is not inside the executable

| Item | Why | What to do |
|------|-----|------------|
| Open-NSFW ONNX (~24 MB) | Too large to hide in onefile | Include `models/` folder from build |
| Vosk model (~40 MB) | Same | Include `models/vosk/` |
| VLC | Separate installer / DLLs | User installs VLC |
| Internet | Downloads only | Needed for yt-dlp URLs only |

## Development vs packaged paths

`app/config.py` detects PyInstaller:

- **Dev:** `PROJECT_ROOT` = repository folder  
- **Packaged:** `PROJECT_ROOT` = folder containing `VGuard.exe`

Database and downloads are stored under `data/` relative to that folder.

## Troubleshooting build

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` at runtime | Add module to `hiddenimports` in `build/vguard.spec`, rebuild |
| App starts but no video | Install VLC on target PC |
| Scan fails | Copy `models/` into dist folder |
| YouTube download fails | Ensure `tools/ffmpeg/bin/ffmpeg.exe` exists in dist |

## Manual test after build

```powershell
cd dist\VGuard
.\VGuard.exe
```

Run through `docs/TESTING_CHECKLIST.md`.
