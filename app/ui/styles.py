"""Qt stylesheets aligned with V-Guard UI mockup (light theme, purple accent)."""

# Mockup reference: `V Guard player mock up.png` in project root
COLORS = {
    "bg": "#F4F5F7",
    "surface": "#FFFFFF",
    "border": "#E2E4E8",
    "text": "#1F2937",
    "text_muted": "#6B7280",
    "primary": "#7C3AED",
    "primary_hover": "#6D28D9",
    "primary_light": "#EDE9FE",
    "video_bg": "#111827",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "visual_badge": "#FCE7F3",
    "audio_badge": "#FFEDD5",
}

APP_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}
QFrame#sidebar, QFrame#rightPanel, QFrame#card {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QLabel#appTitle {{
    font-size: 16px;
    font-weight: 700;
    color: {COLORS['primary']};
}}
QLabel#sectionTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {COLORS['text_muted']};
    letter-spacing: 0.5px;
}}
QPushButton {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 14px;
    color: {COLORS['text']};
}}
QPushButton:hover {{
    border-color: {COLORS['primary']};
    color: {COLORS['primary']};
}}
QPushButton#primaryBtn {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    font-weight: 600;
}}
QPushButton#primaryBtn:hover {{
    background-color: {COLORS['primary_hover']};
}}
QPushButton#navBtn {{
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-radius: 8px;
}}
QPushButton#navBtn:checked {{
    background-color: {COLORS['primary']};
    color: white;
}}
QPushButton#playBtn {{
    background-color: {COLORS['primary']};
    color: white;
    border-radius: 22px;
    min-width: 44px;
    min-height: 44px;
    font-size: 16px;
    font-weight: bold;
    border: none;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: {COLORS['border']};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    margin: -5px 0;
    background: {COLORS['primary']};
    border-radius: 7px;
}}
QComboBox, QLineEdit {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px;
}}
QStatusBar {{
    background: {COLORS['surface']};
    border-top: 1px solid {COLORS['border']};
    color: {COLORS['text_muted']};
}}
QProgressDialog {{
    background: {COLORS['surface']};
}}
"""

VIDEO_OVERLAY_STYLESHEET = f"""
QFrame#videoControlsBar {{
    background-color: rgba(255, 255, 255, 0.94);
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}
QFrame#videoControlsBar QLabel {{
    color: {COLORS['text']};
    font-size: 12px;
    background: transparent;
}}
QFrame#videoControlsBar QPushButton {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 10px;
    min-width: 36px;
    min-height: 32px;
}}
QFrame#videoControlsBar QPushButton#playBtn {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: 22px;
    min-width: 48px;
    min-height: 48px;
    font-size: 18px;
}}
QFrame#videoControlsBar QSlider::groove:horizontal {{
    height: 6px;
    background: {COLORS['border']};
    border-radius: 3px;
}}
QFrame#videoControlsBar QSlider::handle:horizontal {{
    width: 14px;
    margin: -5px 0;
    background: {COLORS['primary']};
    border-radius: 7px;
}}
QFrame#videoControlsBar QSlider::sub-page:horizontal {{
    background: {COLORS['primary']};
    border-radius: 3px;
}}
"""
