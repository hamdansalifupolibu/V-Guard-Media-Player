"""Application settings (Stage 12)."""



from __future__ import annotations



from pathlib import Path



from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (

    QCheckBox,

    QComboBox,

    QDoubleSpinBox,

    QFormLayout,

    QHBoxLayout,

    QLabel,

    QPushButton,

    QSlider,

    QVBoxLayout,

    QWidget,

    QFileDialog,

    QLineEdit,

)



from app.analysis.visual_strictness import (

    PRESETS,

    strictness_summary,

    strictness_to_threshold,

    threshold_to_strictness,

)

from app.config import (

    BLOCKED_WORDS_PATH,

    DEFAULT_MODERATION_MODE,

    DEFAULT_VISUAL_STRICTNESS_PERCENT,

    FRAME_SAMPLE_INTERVAL_SEC,

    SETTING_AUTO_SCAN_ON_LOAD,

    SETTING_ENABLE_AUDIO,

    SETTING_ENABLE_EXPLICIT_AUDIO,

    SETTING_ENABLE_VISUAL,

    SETTING_FORCE_AUDIO_LONG,

    SETTING_FRAME_INTERVAL,

    SETTING_MODERATION_MODE,

    SETTING_REQUIRE_SCAN_BEFORE_PLAY,

    SETTING_VISUAL_STRICTNESS,

    SETTING_VISUAL_THRESHOLD,

    VISUAL_CONFIDENCE_THRESHOLD,

    moderation_mode_index,

    moderation_mode_key,

)

from app.database.db import VGuardDatabase





class SettingsPanel(QWidget):

    """User preferences stored in SQLite."""



    settings_saved = Signal()

    open_blocked_words = Signal()



    def __init__(self, database: VGuardDatabase, parent: QWidget | None = None) -> None:

        super().__init__(parent)

        self._db = database



        root = QVBoxLayout(self)

        root.setContentsMargins(24, 24, 24, 24)



        title = QLabel("Settings")

        title.setObjectName("appTitle")

        root.addWidget(title)



        subtitle = QLabel(

            "Changes apply to the next scan and playback session. "

            "After changing content strictness, re-scan your video."

        )

        subtitle.setStyleSheet("color: #6B7280;")

        subtitle.setWordWrap(True)

        root.addWidget(subtitle)



        form = QFormLayout()

        form.setSpacing(12)



        self.mode_combo = QComboBox()

        from app.config import MODERATION_MODES



        for _key, label in MODERATION_MODES:

            self.mode_combo.addItem(label)

        form.addRow("Default moderation mode:", self.mode_combo)



        strictness_box = QWidget()

        strictness_layout = QVBoxLayout(strictness_box)

        strictness_layout.setContentsMargins(0, 0, 0, 0)

        strictness_layout.setSpacing(8)



        slider_row = QHBoxLayout()

        slider_row.addWidget(QLabel("Relaxed"))

        self.strictness_slider = QSlider(Qt.Orientation.Horizontal)

        self.strictness_slider.setRange(0, 100)

        self.strictness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.strictness_slider.setTickInterval(25)

        self.strictness_slider.valueChanged.connect(self._update_strictness_label)

        slider_row.addWidget(self.strictness_slider, stretch=1)

        slider_row.addWidget(QLabel("Max safety"))

        strictness_layout.addLayout(slider_row)



        self.strictness_summary_label = QLabel()

        self.strictness_summary_label.setWordWrap(True)

        self.strictness_summary_label.setStyleSheet("font-weight: 600;")

        strictness_layout.addWidget(self.strictness_summary_label)



        self.strictness_hint = QLabel(

            "Model scores from your test set: safe beach scenes ~0.04–0.06; "

            "suggestive / undressing ~0.34+; explicit ~0.97+. "

            "Maximum safety lowers the cutoff but cannot flag frames the model "

            "scores below ~0.10 (e.g. some bikini still-images)."

        )

        self.strictness_hint.setWordWrap(True)

        self.strictness_hint.setStyleSheet("color: #6B7280; font-size: 12px;")

        strictness_layout.addWidget(self.strictness_hint)



        preset_row = QHBoxLayout()

        for preset in PRESETS:

            btn = QPushButton(preset.label)

            btn.setToolTip(preset.description)

            btn.clicked.connect(

                lambda _checked=False, p=preset: self.strictness_slider.setValue(

                    p.percent

                )

            )

            preset_row.addWidget(btn)

        strictness_layout.addLayout(preset_row)



        form.addRow("Content strictness:", strictness_box)



        self.frame_interval = QDoubleSpinBox()

        self.frame_interval.setRange(0.5, 10.0)

        self.frame_interval.setSingleStep(0.5)

        self.frame_interval.setDecimals(1)

        self.frame_interval.setSuffix(" sec")

        form.addRow("Frame sample interval:", self.frame_interval)



        self.enable_visual = QCheckBox("Enable visual detection when scanning")

        self.enable_audio = QCheckBox("Enable audio / keyword detection when scanning")

        self.enable_explicit_audio = QCheckBox(
            "Detect explicit sexual sounds (log-mel CNN, moans / vocal)"
        )
        self.enable_explicit_audio.setToolTip(
            "Dedicated model (Lovenia et al. 2022). Runs after FFmpeg extract. Re-scan required."
        )

        form.addRow(self.enable_visual)

        form.addRow(self.enable_audio)

        form.addRow(self.enable_explicit_audio)



        self.auto_scan_on_load = QCheckBox(

            "Automatically scan every video when it is opened (no prompt)"

        )

        self.require_scan_before_play = QCheckBox(

            "Require a completed pre-scan before playback starts"

        )

        self.force_audio_long = QCheckBox(

            "Run audio keyword scan on long videos (>45 min, much slower)"

        )

        form.addRow(self.auto_scan_on_load)

        form.addRow(self.require_scan_before_play)

        form.addRow(self.force_audio_long)



        words_row = QHBoxLayout()

        self.blocked_words_path = QLineEdit()

        self.blocked_words_path.setReadOnly(True)

        browse_btn = QPushButton("Browse…")

        browse_btn.clicked.connect(self._browse_blocked_words)

        open_btn = QPushButton("Open in editor")

        open_btn.clicked.connect(self._open_blocked_words_file)

        words_row.addWidget(self.blocked_words_path, stretch=1)

        words_row.addWidget(browse_btn)

        words_row.addWidget(open_btn)

        form.addRow("Blocked words file:", words_row)



        root.addLayout(form)

        root.addStretch()



        btn_row = QHBoxLayout()

        reset_btn = QPushButton("Reset defaults")

        reset_btn.clicked.connect(self._reset_defaults)

        save_btn = QPushButton("Save settings")

        save_btn.setObjectName("primaryBtn")

        save_btn.clicked.connect(self._save)

        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)



        self._load_from_db()



    def _update_strictness_label(self, value: int) -> None:

        self.strictness_summary_label.setText(strictness_summary(value))



    def _load_strictness_from_db(self) -> None:

        raw_strict = self._db.get_setting(SETTING_VISUAL_STRICTNESS)

        if raw_strict is not None and str(raw_strict).strip() != "":

            try:

                pct = int(float(raw_strict))

                self.strictness_slider.setValue(max(0, min(100, pct)))

                return

            except ValueError:

                pass

        try:

            thresh = float(

                self._db.get_setting(SETTING_VISUAL_THRESHOLD)

                or VISUAL_CONFIDENCE_THRESHOLD

            )

        except ValueError:

            thresh = VISUAL_CONFIDENCE_THRESHOLD

        self.strictness_slider.setValue(threshold_to_strictness(thresh))



    def _load_from_db(self) -> None:

        mode = (

            self._db.get_setting(SETTING_MODERATION_MODE, DEFAULT_MODERATION_MODE)

            or DEFAULT_MODERATION_MODE

        )

        self.mode_combo.setCurrentIndex(moderation_mode_index(mode))



        self._load_strictness_from_db()



        try:

            interval = float(

                self._db.get_setting(SETTING_FRAME_INTERVAL)

                or FRAME_SAMPLE_INTERVAL_SEC

            )

        except ValueError:

            interval = FRAME_SAMPLE_INTERVAL_SEC

        self.frame_interval.setValue(interval)



        self.enable_visual.setChecked(

            self._db.get_setting(SETTING_ENABLE_VISUAL, "true").lower()

            not in ("false", "0", "no")

        )

        self.enable_audio.setChecked(

            self._db.get_setting(SETTING_ENABLE_AUDIO, "true").lower()

            not in ("false", "0", "no")

        )

        raw_explicit = self._db.get_setting(SETTING_ENABLE_EXPLICIT_AUDIO)
        if raw_explicit is None:
            raw_explicit = self._db.get_setting("enable_panns_audio_events", "true")
        self.enable_explicit_audio.setChecked(
            str(raw_explicit).lower() not in ("false", "0", "no")
        )

        self.auto_scan_on_load.setChecked(

            self._db.get_setting(SETTING_AUTO_SCAN_ON_LOAD, "false").lower()

            in ("true", "1", "yes", "on")

        )

        self.require_scan_before_play.setChecked(

            self._db.get_setting(SETTING_REQUIRE_SCAN_BEFORE_PLAY, "true").lower()

            not in ("false", "0", "no", "off")

        )

        self.force_audio_long.setChecked(

            self._setting_bool(SETTING_FORCE_AUDIO_LONG, False)

        )

        self.blocked_words_path.setText(str(BLOCKED_WORDS_PATH))



    def _setting_bool(self, key: str, default: bool) -> bool:

        raw = self._db.get_setting(key)

        if raw is None:

            return default

        return raw.strip().lower() in ("true", "1", "yes", "on")



    def _save(self) -> None:

        strictness = self.strictness_slider.value()

        threshold = strictness_to_threshold(strictness)

        self._db.set_setting(

            SETTING_MODERATION_MODE,

            moderation_mode_key(self.mode_combo.currentIndex()),

        )

        self._db.set_setting(SETTING_VISUAL_STRICTNESS, str(strictness))

        self._db.set_setting(SETTING_VISUAL_THRESHOLD, str(threshold))

        self._db.set_setting(

            SETTING_FRAME_INTERVAL,

            str(self.frame_interval.value()),

        )

        self._db.set_setting(

            SETTING_ENABLE_VISUAL,

            "true" if self.enable_visual.isChecked() else "false",

        )

        self._db.set_setting(

            SETTING_ENABLE_AUDIO,

            "true" if self.enable_audio.isChecked() else "false",

        )

        self._db.set_setting(
            SETTING_ENABLE_EXPLICIT_AUDIO,
            "true" if self.enable_explicit_audio.isChecked() else "false",
        )

        self._db.set_setting(

            SETTING_AUTO_SCAN_ON_LOAD,

            "true" if self.auto_scan_on_load.isChecked() else "false",

        )

        self._db.set_setting(

            SETTING_REQUIRE_SCAN_BEFORE_PLAY,

            "true" if self.require_scan_before_play.isChecked() else "false",

        )

        self._db.set_setting(

            SETTING_FORCE_AUDIO_LONG,

            "true" if self.force_audio_long.isChecked() else "false",

        )

        self.settings_saved.emit()



    def _reset_defaults(self) -> None:

        self.mode_combo.setCurrentIndex(moderation_mode_index(DEFAULT_MODERATION_MODE))

        self.strictness_slider.setValue(DEFAULT_VISUAL_STRICTNESS_PERCENT)

        self.frame_interval.setValue(FRAME_SAMPLE_INTERVAL_SEC)

        self.enable_visual.setChecked(True)

        self.enable_audio.setChecked(True)

        self.enable_explicit_audio.setChecked(True)

        self.auto_scan_on_load.setChecked(False)

        self.require_scan_before_play.setChecked(True)

        self.force_audio_long.setChecked(False)

        self.blocked_words_path.setText(str(BLOCKED_WORDS_PATH))



    def _browse_blocked_words(self) -> None:

        path, _ = QFileDialog.getOpenFileName(

            self,

            "Select blocked words file",

            str(BLOCKED_WORDS_PATH.parent),

            "Text files (*.txt);;All files (*.*)",

        )

        if path:

            self.blocked_words_path.setText(path)

            self._db.set_setting("blocked_words_path", path)



    def _open_blocked_words_file(self) -> None:

        path = Path(self.blocked_words_path.text() or BLOCKED_WORDS_PATH)

        if not path.is_file():

            path.parent.mkdir(parents=True, exist_ok=True)

            path.write_text("# Add blocked words, one per line\n", encoding="utf-8")

        import os

        import subprocess

        import sys



        if sys.platform.startswith("win"):

            os.startfile(path)  # noqa: S606

        else:

            subprocess.run(["xdg-open", str(path)], check=False)

        self.open_blocked_words.emit()


