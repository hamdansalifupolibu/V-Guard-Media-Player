# V-Guard Media Player

## Project Overview

**V-Guard Media Player** is a smart desktop multimedia player designed to help users watch videos in a safer and more controlled way. Unlike normal media players that only focus on playback, V-Guard adds intelligent content moderation features that can detect potentially inappropriate visual or audio sections and apply user-selected actions such as muting, hiding, or skipping those parts.

The project is intended as an academic prototype and proof-of-concept. It does not aim to replace professional content moderation systems or guarantee 100% detection accuracy.

---

## Core Problem

Most existing media players allow unrestricted playback of video content. This can expose children, students, families, institutions, and other users to content they may consider inappropriate. V-Guard aims to solve this by combining:

- Multimedia playback
- AI-assisted scene detection
- Audio/transcript analysis
- User-controlled moderation
- Safe and legal download management

---

## Main Aim

To develop a desktop-based smart media player that allows users to watch videos while reducing exposure to inappropriate visual and audio content through automated detection and user-controlled moderation.

---

## Objectives

The system should be able to:

1. Play common video formats using standard media controls.
2. Scan video files before playback.
3. Detect potentially inappropriate visual scenes using computer vision.
4. Detect offensive or unwanted spoken words using audio transcription and keyword matching.
5. Save detected timestamps for future playback moderation.
6. Allow users to choose moderation actions:
   - Mute audio
   - Hide/blackout video scene
   - Mute audio and hide scene
   - Skip scene
7. Provide a basic legal download manager.
8. Store scan results, user preferences, and download history locally.
9. Package the project as a desktop application.

---

## Important Project Direction

The first version of V-Guard should use a **pre-scan approach**, not real-time AI detection.

### Recommended MVP Flow

```text
1. User selects a local video
2. App scans the video before playback
3. App extracts frames and audio
4. AI/audio modules detect suspicious sections
5. Detected timestamp ranges are saved in SQLite
6. User plays the video
7. The playback controller applies mute, hide, or skip actions
```

This approach is more realistic, easier to build, easier to debug, and better for academic demonstration.

---

## Final Locked Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Programming Language | Python 3.12 | Main development language |
| Desktop GUI | PySide6 | Modern desktop interface |
| Video Playback | python-vlc / libVLC | Video playback engine |
| Video Frame Processing | OpenCV | Extract and sample video frames |
| Visual AI Detection | TensorFlow/Keras or ONNX Runtime | Detect unsafe visual frames |
| Audio Extraction | FFmpeg | Extract audio from video |
| Speech Recognition | Vosk | Offline speech-to-text |
| Audio Moderation | VLC mute controls | Mute playback during flagged timestamps |
| Database | SQLite | Store video records, detections, settings, downloads |
| Download Manager | requests / urllib | Download legal direct video links |
| Packaging | PyInstaller | Create Windows executable |
| Target OS | Windows first, Linux optional | Deployment target |

---

## Why This Stack?

### Python 3.12

Python is suitable because the project requires AI, computer vision, audio processing, SQLite storage, and desktop development.

### PySide6

PySide6 should be used for the desktop interface because it supports modern Qt-based desktop applications. It is better to use PySide6 instead of mixing Python with JavaFX.

### python-vlc / libVLC

VLC already supports many media formats, so using `python-vlc` gives the project a strong playback engine without building video decoding from scratch.

### OpenCV

OpenCV will be used to open video files, sample frames, and send selected frames to the visual detection model.

### TensorFlow/Keras or ONNX Runtime

For the first version, the project should use a pre-trained model. Training a model from scratch is not recommended for the MVP because it requires large datasets, more time, and careful ethical handling.

### FFmpeg

FFmpeg will be used behind the scenes to extract audio from video files.

### Vosk

Vosk is recommended for offline speech recognition. This supports the privacy goal because the user’s media does not need to be uploaded to an external server.

### SQLite

SQLite is simple and reliable for storing scan results, moderation timestamps, app settings, and download history.

### PyInstaller

PyInstaller will be used at the end to package the application into an executable file.

---

## Key Terminology Correction

The original project idea uses the phrase **Mute Scene**. Technically, a visual scene cannot be “muted.” Audio can be muted, but video should be hidden, blurred, blacked out, or skipped.

Recommended wording:

| Original Term | Better Technical Term |
|---|---|
| Mute Scene | Hide Scene / Blackout Scene / Blur Scene |
| Mute Sound | Mute Audio |
| Mute Scene & Sound | Hide Scene + Mute Audio |
| Skip Scene | Skip Scene |

---

## System Architecture

```text
V-Guard Media Player
│
├── User Interface Layer
│   └── PySide6
│
├── Playback Layer
│   └── python-vlc / libVLC
│
├── Video Analysis Layer
│   ├── OpenCV frame extraction
│   └── Visual safety classifier
│
├── Audio Analysis Layer
│   ├── FFmpeg audio extraction
│   ├── Vosk speech-to-text
│   └── Keyword matching
│
├── Moderation Layer
│   ├── Mute audio
│   ├── Hide/blackout video
│   ├── Hide video + mute audio
│   └── Skip flagged scene
│
├── Storage Layer
│   └── SQLite
│
├── Download Manager
│   └── Legal direct-link downloads
│
└── Packaging Layer
    └── PyInstaller
```

---

## Proposed Folder Structure

```text
vguard-media-player/
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── player_controls.py
│   │   ├── settings_panel.py
│   │   └── download_panel.py
│   │
│   ├── playback/
│   │   ├── vlc_player.py
│   │   └── playback_controller.py
│   │
│   ├── analysis/
│   │   ├── video_scanner.py
│   │   ├── frame_extractor.py
│   │   ├── visual_detector.py
│   │   ├── audio_extractor.py
│   │   ├── speech_detector.py
│   │   └── keyword_filter.py
│   │
│   ├── moderation/
│   │   ├── moderation_controller.py
│   │   └── timestamp_manager.py
│   │
│   ├── database/
│   │   ├── db.py
│   │   ├── models.py
│   │   └── schema.sql
│   │
│   ├── downloads/
│   │   └── download_manager.py
│   │
│   └── utils/
│       ├── file_utils.py
│       └── time_utils.py
│
├── models/
│   └── visual_model/
│
├── data/
│   ├── vguard.db
│   └── downloads/
│
├── tests/
│   ├── test_video_scanner.py
│   ├── test_audio_detector.py
│   ├── test_database.py
│   └── test_moderation.py
│
├── requirements.txt
├── README.md
└── build.spec
```

---

## Development Stages

## Stage 0: Research and Project Scope Finalization

### Goal

Clearly define what the project will and will not do.

### Tasks

- Review the proposal.
- Confirm the target users.
- Confirm that the app is a desktop-based prototype.
- Decide that the MVP will use pre-scan moderation, not real-time AI.
- Define ethical boundaries.
- Define legal download limitations.
- Finalize the tech stack.

### Deliverables

- Final project scope
- Final tech stack
- System architecture diagram
- Development roadmap

---

## Stage 1: Environment Setup

### Goal

Prepare the development environment.

### Tasks

- Install Python 3.12.
- Create a virtual environment.
- Install base dependencies.
- Install VLC media player on the development machine.
- Install FFmpeg.
- Create the project folder structure.
- Initialize Git/GitHub repository.

### Suggested Commands

```bash
python -m venv venv
venv\Scripts\activate
pip install PySide6 python-vlc opencv-python requests
pip install vosk
pip install pyinstaller
```

### Deliverables

- Working Python environment
- Installed dependencies
- Initial project repository

---

## Stage 2: Basic Desktop Interface

### Goal

Build the first version of the user interface.

### Tasks

- Create the main app window.
- Add video display area.
- Add open file button.
- Add play, pause, stop buttons.
- Add volume control.
- Add seek/timeline slider.
- Add moderation mode dropdown.
- Add scan button.

### Deliverables

- App opens successfully.
- User can see the interface.
- Buttons and layout are visible.

---

## Stage 3: Basic Video Playback

### Goal

Make the app play local video files.

### Tasks

- Integrate `python-vlc`.
- Load local video file.
- Play, pause, stop video.
- Seek forward and backward.
- Adjust volume.
- Toggle mute.
- Show current playback time and total duration.

### Deliverables

- User can select and play a video.
- Player has basic media controls.

---

## Stage 4: SQLite Database Setup

### Goal

Store videos, detection results, and app settings locally.

### Tasks

- Create SQLite database.
- Create tables for:
  - videos
  - detections
  - settings
  - downloads
- Save video file path and scan status.
- Save detected timestamp ranges.
- Save selected moderation mode.

### Example Tables

```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    duration REAL,
    scan_status TEXT DEFAULT 'not_scanned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER,
    detection_type TEXT,
    start_time REAL,
    end_time REAL,
    confidence REAL,
    label TEXT,
    FOREIGN KEY(video_id) REFERENCES videos(id)
);

CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE,
    value TEXT
);

CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    file_path TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Deliverables

- SQLite database created.
- App can save and retrieve video records.
- App can save detected timestamp ranges.

---

## Stage 5: Video Frame Extraction

### Goal

Extract frames from video for analysis.

### Tasks

- Use OpenCV to open selected video.
- Read video duration and FPS.
- Sample one frame every 1 or 2 seconds.
- Save sampled frame timestamps.
- Prepare frames for the visual AI model.

### Important Note

Do not analyze every frame in the MVP. It will be too slow.

Recommended MVP sampling:

```text
1 frame every 1 or 2 seconds
```

### Deliverables

- Video scanner can process a selected video.
- Frame timestamps are generated.
- Extracted frames can be passed to the visual detector.

---

## Stage 6: Visual Content Detection

### Goal

Detect potentially unsafe visual sections from sampled frames.

### Tasks

- Load a pre-trained visual safety classifier.
- Pass sampled frames to the model.
- Get prediction labels and confidence scores.
- Set a confidence threshold.
- Group nearby unsafe frames into timestamp ranges.
- Save detected ranges in SQLite.

### Example Logic

```text
If frame at 00:01:20 is flagged
and frame at 00:01:22 is flagged
and frame at 00:01:24 is flagged

Group as:
start_time = 00:01:20
end_time = 00:01:24
```

### Deliverables

- Visual detector module works.
- Unsafe visual timestamp ranges are saved.
- Results can be shown in the UI.

---

## Stage 7: Audio Extraction

### Goal

Extract audio from video for speech analysis.

### Tasks

- Use FFmpeg to extract audio from selected video.
- Convert audio to WAV format.
- Store the temporary audio file locally.
- Prepare audio for speech recognition.

### Example Command

```bash
ffmpeg -i input_video.mp4 -ar 16000 -ac 1 output_audio.wav
```

### Deliverables

- Audio can be extracted from video.
- Audio is converted to a speech-recognition-friendly format.

---

## Stage 8: Speech Recognition and Keyword Detection

### Goal

Detect unwanted spoken words from audio.

### Tasks

- Use Vosk to transcribe audio offline.
- Store transcript segments with timestamps.
- Compare transcript text against a blocked keyword list.
- Save detected audio timestamp ranges in SQLite.

### Example Keyword File

```text
blocked_words.txt
```

### Deliverables

- Audio speech is transcribed.
- Offensive or unwanted keywords are detected.
- Timestamp ranges are saved.

---

## Stage 9: Moderation Controller

### Goal

Apply moderation actions during playback.

### Tasks

- Continuously check the current playback timestamp.
- Compare current time with saved detection ranges.
- Apply the selected moderation action:
  - Mute audio
  - Hide/blackout video
  - Hide video + mute audio
  - Skip scene
- Restore normal playback after the flagged range ends.

### Example Logic

```text
If current_time is inside flagged range:
    If mode == "mute_audio":
        mute audio
    If mode == "hide_video":
        show black overlay
    If mode == "hide_and_mute":
        show black overlay and mute audio
    If mode == "skip_scene":
        seek to end_time
Else:
    restore normal playback
```

### Deliverables

- Moderation actions work during playback.
- User can change moderation mode.
- App applies saved detection results correctly.

---

## Stage 10: Scan Results Screen

### Goal

Let users view what the system detected.

### Tasks

- Show scan summary.
- Display visual detections.
- Display audio detections.
- Show timestamps.
- Show confidence scores.
- Allow user to enable/disable specific detected ranges.

### Deliverables

- User can review detection results.
- User can control what gets moderated.

---

## Stage 11: Legal Download Manager

### Goal

Add a safe download feature without supporting piracy.

### Tasks

- Add URL input field.
- Validate URL format.
- Allow download only from direct legal video links.
- Save download history in SQLite.
- Show download progress.
- Save files into local downloads folder.

### Important Legal Rule

Do not build a YouTube downloader or movie piracy downloader. The download manager should only support legal, direct, user-approved video links or public-domain/approved educational sources.

### Deliverables

- User can paste a legal direct video link.
- App can download and save the file.
- Download history is stored.

---

## Stage 12: Settings and Preferences

### Goal

Allow users to control how moderation works.

### Tasks

- Add moderation mode selection.
- Add confidence threshold setting.
- Add blocked keyword editor.
- Add local storage settings.
- Add option to enable/disable audio detection.
- Add option to enable/disable visual detection.

### Deliverables

- Settings screen works.
- Preferences are saved in SQLite.
- App remembers settings after restart.

---

## Stage 13: Testing and Debugging

### Goal

Make the app stable and presentable.

### Tasks

- Test video loading.
- Test play/pause/stop.
- Test frame extraction.
- Test visual detection.
- Test audio extraction.
- Test transcription.
- Test timestamp moderation.
- Test database saving/loading.
- Test download manager.
- Test app on Windows.

### Deliverables

- Stable prototype.
- Known issues documented.
- Demo-ready app.

---

## Stage 14: Packaging

### Goal

Package the app for final demonstration.

### Tasks

- Use PyInstaller to create an executable.
- Include required model files.
- Include database folder.
- Include FFmpeg/VLC dependency instructions.
- Test the packaged application.

### Example Command

```bash
pyinstaller --onefile --windowed app/main.py
```

### Deliverables

- Windows executable file
- Setup/run instructions
- Final demo version

---

## Stage 15: Final Documentation and Presentation

### Goal

Prepare the project for academic evaluation.

### Tasks

- Update README.
- Add screenshots.
- Add architecture diagram.
- Add explanation of algorithms.
- Add limitations.
- Add ethical considerations.
- Add future improvements.
- Prepare PowerPoint slides.
- Prepare live demo script.

### Deliverables

- Final README
- Final report section
- Presentation slides
- Demo video or live demo

---

## MVP Feature List

The MVP should include:

- Desktop app interface
- Local video playback
- Open video file
- Play, pause, stop
- Seek/timeline slider
- Volume control
- Video pre-scan
- Frame extraction
- Basic visual detection
- Audio extraction
- Basic speech-to-text
- Keyword-based audio detection
- SQLite timestamp storage
- User-selected moderation mode
- Mute/hide/skip playback behavior
- Basic legal download manager

---

## Features to Avoid in MVP

Do not build these in the first version:

- Full real-time AI detection
- Online streaming moderation
- Cloud-based video upload
- Advanced multilingual speech recognition
- YouTube/movie downloading
- Training a custom AI model from scratch
- Mobile app version
- Complex user accounts
- Advanced parental control system

These can be future improvements.

---

## Ethical and Privacy Considerations

V-Guard should process media locally where possible. User videos should not be uploaded to external servers. The app should not collect personal user data or monitor user behavior.

The user should also be informed that AI detection is not perfect. The system may miss some inappropriate content or incorrectly flag safe content.

---

## Limitations

- Detection accuracy is not guaranteed.
- AI models may produce false positives and false negatives.
- Pre-scan may take time for long videos.
- Audio detection depends on speech clarity.
- Keyword detection may miss slang, accents, or non-English speech.
- Some video formats may require additional codec support.
- The download manager must only support legal sources.

---

## Future Improvements

Possible future improvements include:

- Better visual detection model
- Blur instead of black screen
- More accurate audio classification
- Multi-language support
- Parental PIN settings
- Export cleaned version of video
- Batch video scanning
- Advanced subtitle analysis
- Cloud model option with user consent
- Linux support
- Installer with bundled dependencies

---

## Suggested Development Priority

The recommended development order is:

```text
1. Project setup
2. Basic GUI
3. Video playback
4. SQLite database
5. Frame extraction
6. Visual detection
7. Audio extraction
8. Speech-to-text and keyword detection
9. Timestamp moderation
10. Scan results screen
11. Settings
12. Legal download manager
13. Testing
14. Packaging
15. Final documentation
```

---

## Final Recommendation

Build V-Guard as a **desktop pre-scan smart media player** first. This version is realistic, defendable, and suitable for academic evaluation. After the MVP works well, real-time detection and advanced features can be added as future improvements.
