"""Floating fullscreen control bar — VLC-style show/hide on activity."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QCursor, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.ui.player_controls import PlayerControls
from app.ui.styles import VIDEO_OVERLAY_STYLESHEET

KeyHandler = Callable[[], None]


class FullscreenAppInputFilter(QObject):
    """
    Application-wide filter so VLC focus does not swallow keyboard activity.

    Reveals the control bar on any key press/release and forwards transport
    shortcuts when handlers are registered.
    """

    def __init__(self, dock: "FullscreenControlsDock") -> None:
        super().__init__()
        self._dock = dock
        self._handlers: dict[int, KeyHandler] = {}

    def set_key_handlers(self, handlers: dict[int, KeyHandler]) -> None:
        self._handlers = dict(handlers)

    def clear_key_handlers(self) -> None:
        self._handlers.clear()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if not self._dock._host:
            return False
        et = event.type()
        if et == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            handler = self._handlers.get(event.key())
            if handler is not None:
                handler()
            self._dock.notify_activity()
            return handler is not None
        if et in (
            QEvent.Type.KeyRelease,
            QEvent.Type.Shortcut,
        ):
            self._dock.notify_activity()
        elif et == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
            pos = event.globalPosition().toPoint()
            host = self._dock._host
            if host and host.rect().contains(host.mapFromGlobal(pos)):
                self._dock._last_cursor_pos = pos
                self._dock.notify_activity()
        return False


class FullscreenControlsDock(QWidget):
    """
    Floats above the fullscreen window (not in the video layout).

    When idle: the dock is fully hidden — only video is visible.
    On mouse move, click, or key: bar fades in; hides again after idle timeout.
    """

    HIDE_DELAY_MS = 4000
    FADE_OUT_MS = 180
    MOUSE_POLL_MS = 16
    HORIZONTAL_MARGIN = 20
    BOTTOM_MARGIN = 18

    def __init__(self, parent: QMainWindow) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self.hide()

        self._host: QMainWindow | None = None
        self._playing = False
        self._controls_visible = False
        self._docked_controls: PlayerControls | None = None
        self._dock_parent: QWidget | None = None
        self._dock_layout: QVBoxLayout | None = None
        self._video_area: QWidget | None = None
        self._tracked_widgets: list[QWidget] = []
        self._last_cursor_pos: QPoint | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._controls_bar = QFrame()
        self._controls_bar.setObjectName("videoControlsBar")
        self._controls_bar.setStyleSheet(VIDEO_OVERLAY_STYLESHEET)
        self._bar_layout = QVBoxLayout(self._controls_bar)
        self._bar_layout.setContentsMargins(14, 10, 14, 12)
        self._bar_layout.setSpacing(0)
        root.addWidget(self._controls_bar)

        self._opacity = QGraphicsOpacityEffect(self._controls_bar)
        self._opacity.setOpacity(0.0)
        self._controls_bar.setGraphicsEffect(self._opacity)

        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(self.FADE_OUT_MS)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._on_fade_finished)
        self._pinned_while_paused = False

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out_controls)

        self._mouse_poll = QTimer(self)
        self._mouse_poll.setInterval(self.MOUSE_POLL_MS)
        self._mouse_poll.timeout.connect(self._poll_cursor)

        self._app_filter = FullscreenAppInputFilter(self)

        self.setMouseTracking(True)
        self.installEventFilter(self)

    def attach_video_area(self, video_area: QWidget) -> None:
        self._video_area = video_area
        self._track_widget(video_area)

    def attach_pointer_targets(self, *widgets: QWidget) -> None:
        for widget in widgets:
            self._track_widget(widget)

    def _track_widget(self, widget: QWidget) -> None:
        if widget not in self._tracked_widgets:
            widget.setMouseTracking(True)
            widget.installEventFilter(self)
            self._tracked_widgets.append(widget)

    def dock_controls(
        self,
        controls: PlayerControls,
        parent: QWidget,
        layout: QVBoxLayout,
    ) -> None:
        self._docked_controls = controls
        self._dock_parent = parent
        self._dock_layout = layout

    def set_key_handlers(self, handlers: dict[int, KeyHandler]) -> None:
        self._app_filter.set_key_handlers(handlers)

    def enter_fullscreen(self, host: QMainWindow) -> None:
        if not self._docked_controls or not self._dock_layout:
            return
        self._host = host
        controls = self._docked_controls
        self._dock_layout.removeWidget(controls)
        self._bar_layout.addWidget(controls)
        controls.installEventFilter(self)
        host.installEventFilter(self)
        self._track_widget(host)

        self._last_cursor_pos = QCursor.pos()
        self._mouse_poll.start()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self._app_filter)

        self._pinned_while_paused = not self._playing
        self._hide_timer.stop()
        self._fade.stop()

        if self._pinned_while_paused:
            self._show_controls_instant()
        else:
            self._opacity.setOpacity(0.0)
            self._controls_visible = False
            self.hide()

    def exit_fullscreen(self) -> None:
        if not self._docked_controls or not self._dock_layout or not self._dock_parent:
            return
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self._app_filter)
        self._app_filter.clear_key_handlers()
        controls = self._docked_controls
        self._mouse_poll.stop()
        self._hide_timer.stop()
        self._fade.stop()
        if self._host:
            self._host.removeEventFilter(self)
        controls.removeEventFilter(self)
        self._bar_layout.removeWidget(controls)
        controls.setParent(self._dock_parent)
        self._dock_layout.addWidget(controls)
        self._opacity.setOpacity(1.0)
        self._controls_visible = True
        self._host = None
        self._last_cursor_pos = None
        self._pinned_while_paused = False
        self.hide()

    def position_at_bottom(self, host: QMainWindow) -> None:
        if not self.isVisible():
            return
        self.adjustSize()
        bar_h = max(self._controls_bar.sizeHint().height(), 100)
        width = host.width() - 2 * self.HORIZONTAL_MARGIN
        x = self.HORIZONTAL_MARGIN
        y = host.height() - bar_h - self.BOTTOM_MARGIN
        self.setGeometry(x, max(0, y), max(200, width), bar_h)
        self.raise_()

    def set_playing(self, playing: bool) -> None:
        was_playing = self._playing
        self._playing = playing
        if not self._host:
            return
        if not playing:
            self._pinned_while_paused = True
            self._hide_timer.stop()
            self._fade.stop()
            self._show_controls_instant()
        else:
            self._pinned_while_paused = False
            if not was_playing and playing:
                if self._controls_visible:
                    self._schedule_hide()
                elif not self._controls_visible:
                    self._hide_chrome()

    def notify_activity(self, *, permanent: bool = False) -> None:
        """Reveal controls immediately; auto-hide only while video is playing."""
        if not self._host:
            return
        pin = permanent or self._pinned_while_paused or not self._playing
        self._hide_timer.stop()
        self._fade.stop()
        self._show_controls_instant()
        if pin or not self._should_auto_hide():
            self._hide_timer.stop()
        else:
            self._schedule_hide()

    def reveal_controls(self, *, permanent: bool = False) -> None:
        self.notify_activity(permanent=permanent)

    def _show_controls_instant(self) -> None:
        """Snap the bar in at full opacity (VLC-style, no fade-in delay)."""
        if not self._host:
            return
        self._controls_visible = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._opacity.setOpacity(1.0)
        self.show()
        self.position_at_bottom(self._host)
        self.raise_()

    def _poll_cursor(self) -> None:
        if not self._host:
            return
        pos = QCursor.pos()
        if self._last_cursor_pos is None:
            self._last_cursor_pos = pos
            return
        if pos == self._last_cursor_pos:
            return
        if not self._cursor_over_host(pos):
            return
        self._last_cursor_pos = pos
        self.notify_activity()

    def _set_bar_visible(self, visible: bool, *, animate: bool = True) -> None:
        if not self._host:
            return
        if visible:
            self._show_controls_instant()
            return
        if self._pinned_while_paused:
            return
        if not animate:
            self._hide_chrome()
            return
        self._controls_visible = False
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _hide_chrome(self) -> None:
        """Remove bottom bar rectangle so only video remains visible."""
        self._controls_visible = False
        self._opacity.setOpacity(0.0)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()
        self.setGeometry(0, 0, 0, 0)

    def _on_fade_finished(self) -> None:
        if self._opacity.opacity() <= 0.01:
            self._hide_chrome()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if not self._host:
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.MouseMove:
            if isinstance(event, QMouseEvent):
                self._last_cursor_pos = event.globalPosition().toPoint()
            self.notify_activity()
        elif event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.Wheel,
        ):
            self.notify_activity()
        elif event.type() in (
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
        ):
            self.notify_activity()
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._last_cursor_pos = event.globalPosition().toPoint()
        self.notify_activity()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.notify_activity()
        super().mousePressEvent(event)

    def _should_auto_hide(self) -> bool:
        return (
            self._host is not None
            and self._playing
            and not self._pinned_while_paused
        )

    def _schedule_hide(self) -> None:
        if self._should_auto_hide():
            self._hide_timer.stop()
            self._hide_timer.start(self.HIDE_DELAY_MS)

    def _fade_out_controls(self) -> None:
        if not self._should_auto_hide():
            return
        self._set_bar_visible(False, animate=True)

    def _cursor_over_host(self, global_pos: QPoint) -> bool:
        host = self._host
        if not host:
            return False
        return host.rect().contains(host.mapFromGlobal(global_pos))
