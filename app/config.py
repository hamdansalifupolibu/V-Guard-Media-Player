"""Application configuration and paths."""

from __future__ import annotations

import sys
from pathlib import Path


def _resolve_project_root() -> Path:
    """Project root in dev; folder containing the .exe when packaged (PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _resolve_assets_dir() -> Path:
    """Bundled logos live under sys._MEIPASS/app/assets when frozen."""
    if getattr(sys, "frozen", False):
        bundle = getattr(sys, "_MEIPASS", None)
        if bundle:
            return Path(bundle) / "app" / "assets"
        internal = _resolve_project_root() / "_internal" / "app" / "assets"
        if internal.is_dir():
            return internal
        return _resolve_project_root() / "app" / "assets"
    return Path(__file__).resolve().parent / "assets"


PROJECT_ROOT = _resolve_project_root()

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "vguard.db"
DOWNLOADS_DIR = DATA_DIR / "downloads"
MODELS_DIR = PROJECT_ROOT / "models"
VISUAL_MODEL_DIR = MODELS_DIR / "visual_model"
VOSK_MODEL_DIR = MODELS_DIR / "vosk"
VOSK_MODEL_EXTRACTED = VOSK_MODEL_DIR / "vosk-model-small-en-us-0.15"
DEFAULT_VOSK_MODEL_DIR = (
    VOSK_MODEL_EXTRACTED
    if VOSK_MODEL_EXTRACTED.is_dir()
    else VOSK_MODEL_DIR / "model"
)
TEMP_AUDIO_DIR = DATA_DIR / "temp_audio"
BLOCKED_WORDS_PATH = DATA_DIR / "blocked_words.txt"
THESIS_DIR = DATA_DIR / "thesis"
THESIS_FIGURES_DIR = THESIS_DIR / "figures"
MOCKUP_IMAGE = PROJECT_ROOT / "V Guard player mock up.png"
ASSETS_DIR = _resolve_assets_dir()
APP_LOGO_PATH = ASSETS_DIR / "vguard_logo.png"
APP_MARK_PATH = ASSETS_DIR / "vguard_mark.png"
APP_ICON_PATH = ASSETS_DIR / "vguard_icon.ico"
# Display sizes (trimmed logo is ~386×388 px — do not scale the raw 1536×1024 file)
LOGO_SIDEBAR_MAX_WIDTH = 196
LOGO_SIDEBAR_MAX_HEIGHT = 200
LOGO_ABOUT_MAX_WIDTH = 440
SIDEBAR_WIDTH = 228
FFMPEG_BIN_DIR = PROJECT_ROOT / "tools" / "ffmpeg" / "bin"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
VISUAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
VOSK_MODEL_DIR.mkdir(parents=True, exist_ok=True)
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
EXPLICIT_AUDIO_MODEL_DIR = MODELS_DIR / "explicit_audio"
EXPLICIT_AUDIO_MODEL_DIR.mkdir(parents=True, exist_ok=True)
THESIS_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
FFMPEG_BIN_DIR.mkdir(parents=True, exist_ok=True)

# Application metadata
APP_NAME = "V-Guard Media Player"
APP_VERSION = "0.1.0"

# Video analysis defaults (used in later stages)
FRAME_SAMPLE_INTERVAL_SEC = 2.0
VISUAL_CONFIDENCE_THRESHOLD = 0.65
DEFAULT_VISUAL_STRICTNESS_PERCENT = 88
SETTING_VISUAL_STRICTNESS = "visual_strictness_percent"
VOSK_SAMPLE_RATE_HZ = 16000
DEFAULT_VIDEO_FPS = 25.0

# Visual moderation shield (blurred overlay instead of solid blackout)
MODERATION_SHIELD_FPS = 8
MODERATION_SHIELD_CAPTURE_WIDTH = 480
MODERATION_SHIELD_CAPTURE_HEIGHT = 270
MODERATION_SHIELD_BLUR_SIGMA = 32.0
MODERATION_SHIELD_DOWNSAMPLE_FACTOR = 12
MODERATION_SHIELD_FROST_ALPHA = 0.22
MODERATION_SHIELD_SNAPSHOT_WIDTH = 640
MODERATION_SHIELD_SNAPSHOT_HEIGHT = 360

# Scene shield/mute padding: max(seconds, frames at FPS) on each side of a scene
VISUAL_MODERATION_LEAD_SEC = 2.0
VISUAL_MODERATION_TRAIL_SEC = 1.0
VISUAL_MODERATION_LEAD_FRAMES = 2
VISUAL_MODERATION_TRAIL_FRAMES = 2
AUDIO_MODERATION_LEAD_SEC = 2.0
AUDIO_MODERATION_TRAIL_SEC = 1.0
AUDIO_KEYWORD_MERGE_GAP_SEC = 4.0

# Extra margin at playback so ticks do not flash one frame of a scene
MODERATION_PLAYBACK_LEAD_SEC = 0.25
MODERATION_PLAYBACK_TRAIL_SEC = 0.25

# Progressive (chunked) scan — lazy-load style pre-analysis
SCAN_CHUNK_DURATION_SEC = 30.0
SCAN_LONG_VIDEO_CHUNK_SEC = 60.0
SCAN_INITIAL_UNLOCK_SEC = 20.0
SCAN_VISUAL_BATCH_SIZE = 8
SCAN_PROGRESS_MIN_INTERVAL_SEC = 0.2
SCAN_AUDIO_MAX_DURATION_SEC = 2700.0
SETTING_SCAN_CHUNK_DURATION = "scan_chunk_duration_sec"
SETTING_FORCE_AUDIO_LONG = "scan_force_audio_long_videos"

# Supported local video extensions for open dialog
VIDEO_EXTENSIONS = (
    "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v *.mpeg *.mpg"
)

# VLC instance arguments (minimal; extend if needed)
VLC_ARGS = ["--intf=dummy", "--no-video-title-show"]

# Default playback moderation for new installs / reset
DEFAULT_MODERATION_MODE = "hide_and_mute"

# Moderation modes (labels shown in UI)
MODERATION_MODES = [
    ("none", "▶️ No moderation"),
    ("mute_audio", "🔇 Mute audio"),
    ("hide_video", "🛡 Shield scene (blur)"),
    ("hide_and_mute", "🛡🔇 Shield + mute"),
    ("skip_scene", "⏭️ Skip scene"),
]

# Settings keys (SQLite)
SETTING_MODERATION_MODE = "moderation_mode"
SETTING_FRAME_INTERVAL = "frame_sample_interval_sec"
SETTING_VISUAL_THRESHOLD = "visual_confidence_threshold"
SETTING_ENABLE_AUDIO = "enable_audio_detection"
SETTING_ENABLE_EXPLICIT_AUDIO = "enable_explicit_audio_detection"
SETTING_ENABLE_PANNS_AUDIO = "enable_panns_audio_events"  # legacy DB key
EXPLICIT_AUDIO_MODEL_PATH = EXPLICIT_AUDIO_MODEL_DIR / "explicit_audio_cnn.pt"
SETTING_ENABLE_VISUAL = "enable_visual_detection"
SETTING_AUTO_SCAN_ON_LOAD = "auto_scan_on_load"
SETTING_REQUIRE_SCAN_BEFORE_PLAY = "require_scan_before_play"
SCAN_FORCE_AUDIO_ON_LONG_VIDEOS = False

VISUAL_MODEL_FILENAME = "open_nsfw.onnx"
VISUAL_MODEL_PATH = VISUAL_MODEL_DIR / VISUAL_MODEL_FILENAME

# Scan status display labels
SCAN_STATUS_LABELS: dict[str, str] = {
    "not_scanned": "Not scanned",
    "scanning": "Scanning (in progress)…",
    "frames_sampled": "Frames sampled (awaiting AI)",
    "complete": "Scan complete",
    "failed": "Scan failed",
}


def moderation_mode_index(mode_key: str) -> int:
    """Return combo box index for a moderation mode key."""
    for i, (key, _) in enumerate(MODERATION_MODES):
        if key == mode_key:
            return i
    return 0


def moderation_mode_key(index: int) -> str:
    """Return moderation mode key from combo box index."""
    if 0 <= index < len(MODERATION_MODES):
        return MODERATION_MODES[index][0]
    return MODERATION_MODES[0][0]
