"""
Main window for TranscribrAI application.

This module provides the MainWindow class, the primary user interface for
TranscribrAI. It features a central push-to-talk button, status display,
volume indicator, and transcription preview.

Design follows GNOME Human Interface Guidelines with proper color coding
for different application states.

Example:
    >>> from PyQt6.QtWidgets import QApplication
    >>> from transcribrai.app import TranscribrApp
    >>> from transcribrai.gui.main_window import MainWindow
    >>>
    >>> qt_app = QApplication([])
    >>> app = TranscribrApp()
    >>> window = MainWindow(app)
    >>> window.show()
    >>> qt_app.exec()
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QClipboard,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QPalette,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from transcribrai.app import AppState, TranscribrApp

from .settings import SettingsDialog

logger = logging.getLogger(__name__)


# GNOME Color Palette for status states
class GnomeColors:
    """GNOME HIG color palette for status indication."""

    BLUE_IDLE = "#3584e4"       # Idle state
    RED_RECORDING = "#e01b24"   # Recording state
    YELLOW_TRANSCRIBING = "#f6d32d"  # Transcribing state
    GREEN_SENDING = "#33d17a"   # Sending state
    ORANGE_WARNING = "#ff7800"  # Warning/Error state

    # Hover variants (5% lighter)
    BLUE_HOVER = "#4a90e8"
    RED_HOVER = "#f03a46"
    YELLOW_HOVER = "#f7db57"
    GREEN_HOVER = "#52dc92"

    # Pressed variants (10% darker)
    BLUE_PRESSED = "#2a6ac7"
    RED_PRESSED = "#b8161e"
    YELLOW_PRESSED = "#d4b520"
    GREEN_PRESSED = "#2ab066"

    # Text colors
    TEXT_DARK = "#2e3436"
    TEXT_LIGHT = "#f6f5f4"


class PushToTalkButton(QPushButton):
    """
    Custom circular push-to-talk button with state-based styling.

    This button provides visual feedback through color changes and
    pulse animations based on the application state.

    Attributes:
        current_state: The current visual state of the button.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the push-to-talk button.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self._current_state = "idle"
        self._pulse_animation: Optional[QPropertyAnimation] = None
        self._pulse_timer: Optional[QTimer] = None
        self._is_pulsing = False
        self._pulse_bright = False

        self._setup_ui()
        self._setup_accessibility()
        self._apply_idle_style()

    def _setup_ui(self) -> None:
        """Configure button size, icon, and base properties."""
        self.setFixedSize(160, 160)
        self.setIconSize(QSize(48, 48))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Try to load microphone icon from theme, fallback to text
        mic_icon = QIcon.fromTheme("audio-input-microphone")
        if not mic_icon.isNull():
            self.setIcon(mic_icon)
        else:
            self.setText("MIC")
            font = self.font()
            font.setPointSize(24)
            font.setBold(True)
            self.setFont(font)

    def _setup_accessibility(self) -> None:
        """Configure accessibility properties for screen readers."""
        self.setAccessibleName("Push-to-Talk Button")
        self.setAccessibleDescription(
            "Drücken um Sprachaufnahme zu starten. "
            "Nochmals drücken um zu stoppen."
        )
        self.setToolTip("Klicken oder Ctrl+Shift+Space drücken")

    def _get_base_style(
        self,
        bg_color: str,
        hover_color: str,
        pressed_color: str
    ) -> str:
        """
        Generate stylesheet for button with given colors.

        Args:
            bg_color: Background color for normal state.
            hover_color: Background color for hover state.
            pressed_color: Background color for pressed state.

        Returns:
            Complete stylesheet string.
        """
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 80px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:focus {{
                outline: 2px solid {GnomeColors.BLUE_IDLE};
                outline-offset: 4px;
            }}
        """

    def _apply_idle_style(self) -> None:
        """Apply idle state styling (blue)."""
        self._current_state = "idle"
        self._stop_pulse_animation()
        self.setStyleSheet(self._get_base_style(
            GnomeColors.BLUE_IDLE,
            GnomeColors.BLUE_HOVER,
            GnomeColors.BLUE_PRESSED
        ))

    def _apply_recording_style(self) -> None:
        """Apply recording state styling (red with pulse)."""
        self._current_state = "recording"
        self.setStyleSheet(self._get_base_style(
            GnomeColors.RED_RECORDING,
            GnomeColors.RED_HOVER,
            GnomeColors.RED_PRESSED
        ))
        self._start_pulse_animation()

    def _apply_transcribing_style(self) -> None:
        """Apply transcribing state styling (yellow)."""
        self._current_state = "transcribing"
        self._stop_pulse_animation()
        self.setStyleSheet(self._get_base_style(
            GnomeColors.YELLOW_TRANSCRIBING,
            GnomeColors.YELLOW_HOVER,
            GnomeColors.YELLOW_PRESSED
        ))

    def _apply_sending_style(self) -> None:
        """Apply sending state styling (green)."""
        self._current_state = "sending"
        self._stop_pulse_animation()
        self.setStyleSheet(self._get_base_style(
            GnomeColors.GREEN_SENDING,
            GnomeColors.GREEN_HOVER,
            GnomeColors.GREEN_PRESSED
        ))

    def _start_pulse_animation(self) -> None:
        """Start the pulsing animation for recording state."""
        if self._is_pulsing:
            return

        self._is_pulsing = True
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_step)
        self._pulse_timer.start(750)  # Toggle every 750ms for 1.5s cycle

        # Track pulse state
        self._pulse_bright = False

    def _pulse_step(self) -> None:
        """Execute one step of the pulse animation."""
        if not self._is_pulsing or self._current_state != "recording":
            return

        self._pulse_bright = not self._pulse_bright

        if self._pulse_bright:
            color = GnomeColors.RED_HOVER
        else:
            color = GnomeColors.RED_RECORDING

        # Update only background, preserve other styles
        self.setStyleSheet(self._get_base_style(
            color,
            GnomeColors.RED_HOVER,
            GnomeColors.RED_PRESSED
        ))

    def _stop_pulse_animation(self) -> None:
        """Stop the pulsing animation."""
        self._is_pulsing = False

        if self._pulse_timer:
            self._pulse_timer.stop()
            self._pulse_timer.deleteLater()
            self._pulse_timer = None

    def set_state(self, state_name: str) -> None:
        """
        Set the visual state of the button.

        Args:
            state_name: One of 'idle', 'recording', 'transcribing', 'sending'.
        """
        state_methods = {
            "idle": self._apply_idle_style,
            "recording": self._apply_recording_style,
            "transcribing": self._apply_transcribing_style,
            "sending": self._apply_sending_style,
        }

        method = state_methods.get(state_name.lower())
        if method:
            method()
        else:
            logger.warning(f"Unknown button state: {state_name}")
            self._apply_idle_style()

    @property
    def current_state(self) -> str:
        """Get the current visual state of the button."""
        return self._current_state


class VolumeIndicator(QProgressBar):
    """
    Custom progress bar for displaying audio input volume.

    Features smooth animation when volume levels change and
    a gradient color scheme from green (quiet) to red (loud).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the volume indicator.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self._animation: Optional[QPropertyAnimation] = None
        self._setup_ui()
        self._setup_accessibility()

    def _setup_ui(self) -> None:
        """Configure progress bar appearance and properties."""
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(24)

        # Apply gradient styling
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                background-color: rgba(0, 0, 0, 0.1);
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #33d17a,
                    stop: 0.5 #f6d32d,
                    stop: 1 #e01b24
                );
                border-radius: 3px;
            }
        """)

    def _setup_accessibility(self) -> None:
        """Configure accessibility properties."""
        self.setAccessibleName("Aufnahme-Lautstärke")
        self.setAccessibleDescription(
            "Zeigt die aktuelle Lautstärke der Aufnahme an"
        )

    def set_volume(self, level: float) -> None:
        """
        Set volume level with smooth animation.

        Args:
            level: Volume level from 0.0 to 1.0.
        """
        # Clamp and convert to percentage
        percentage = int(max(0.0, min(1.0, level)) * 100)

        # Stop and clean up any existing animation to prevent memory leak
        if self._animation:
            self._animation.stop()
            self._animation.deleteLater()

        # Create smooth transition
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(100)  # 100ms for responsive feel
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(percentage)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()


class TranscriptionPreview(QGroupBox):
    """
    Group box containing a read-only text area for transcription preview.

    Displays the most recent transcription result with proper styling
    and placeholder text when empty.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the transcription preview.

        Args:
            parent: Parent widget.
        """
        super().__init__("Letzte Transkription", parent)

        self._text_edit: Optional[QTextEdit] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure the group box and text edit."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setMinimumHeight(80)
        self._text_edit.setMaximumHeight(200)
        self._text_edit.setPlaceholderText(
            "Keine Aufnahme vorhanden.\n"
            "Drücken Sie den Button oder Ctrl+Shift+Space."
        )

        # Accessibility
        self._text_edit.setAccessibleName("Transkriptions-Vorschau")
        self._text_edit.setAccessibleDescription(
            "Zeigt den zuletzt transkribierten Text an"
        )

        # Styling
        self._text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 6px;
                padding: 12px;
                background-color: rgba(0, 0, 0, 0.03);
                font-family: monospace;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #3584e4;
            }
        """)

        # Use system monospace font
        mono_font = QFont("monospace")
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        mono_font.setPointSize(12)
        self._text_edit.setFont(mono_font)

        layout.addWidget(self._text_edit)

        # Group box styling
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
                font-weight: 500;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: transparent;
                color: #666666;
                font-size: 10pt;
            }
        """)

    def set_text(self, text: str) -> None:
        """
        Set the transcription text.

        Args:
            text: The transcription text to display.
        """
        self._text_edit.setPlainText(text)

    def append_text(self, text: str) -> None:
        """
        Append text to the existing transcription.

        Args:
            text: Text to append.
        """
        current = self._text_edit.toPlainText()
        if current:
            self._text_edit.setPlainText(f"{current}\n\n{text}")
        else:
            self._text_edit.setPlainText(text)

        # Scroll to bottom
        scrollbar = self._text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        """Clear the transcription text."""
        self._text_edit.clear()


class MainWindow(QMainWindow):
    """
    Main application window for TranscribrAI.

    Provides the primary user interface with:
    - Central push-to-talk button (160x160px)
    - Status label with color-coded state indication
    - Volume indicator (visible during recording)
    - Transcription preview area
    - Settings access via header bar button

    Attributes:
        push_to_talk_clicked: Signal emitted when PTT button is clicked.
        settings_requested: Signal emitted when settings should open.

    Example:
        >>> from transcribrai.app import TranscribrApp
        >>> app = TranscribrApp()
        >>> window = MainWindow(app)
        >>> window.show()
    """

    # Signals for external communication
    push_to_talk_clicked = pyqtSignal()
    settings_requested = pyqtSignal()

    # Private signals for thread-safe UI updates from background threads
    # These signals marshal callbacks from audio/transcription threads to the Qt main thread
    _volume_level_signal = pyqtSignal(float)
    _state_changed_signal = pyqtSignal(str)
    _transcription_ready_signal = pyqtSignal(str)
    _error_signal = pyqtSignal(str)

    # Status text mapping
    STATUS_TEXTS = {
        "idle": "Bereit zur Aufnahme",
        "recording": "● Aufnahme läuft...",
        "transcribing": "⟳ Transkribiere...",
        "sending": "✓ Sende Text...",
        "error": "⚠ Fehler aufgetreten",
    }

    def __init__(self, app: Optional[TranscribrApp] = None) -> None:
        """
        Initialize the main window.

        Args:
            app: TranscribrApp instance for integration. If provided, the
                 window will connect to app callbacks for state updates.
        """
        super().__init__()

        self._app = app
        self._current_state = "idle"

        # UI Components (initialized in _setup_ui)
        self._ptt_button: PushToTalkButton = None
        self._status_label: QLabel = None
        self._hotkey_label: QLabel = None
        self._volume_indicator: VolumeIndicator = None
        self._transcription_preview: TranscriptionPreview = None
        self._copy_button: QPushButton = None
        self._clear_button: QPushButton = None
        self._settings_button: QToolButton = None

        self._setup_window()
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_app_callbacks()

        logger.info("MainWindow initialized")

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("TranscribrAI")
        self.setMinimumSize(480, 520)
        self.resize(520, 580)

        # Window icon
        window_icon = QIcon.fromTheme("audio-input-microphone")
        if not window_icon.isNull():
            self.setWindowIcon(window_icon)

    def _setup_ui(self) -> None:
        """Create and arrange all UI components."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Header bar (GNOME-style) if in GNOME session
        self._setup_header_bar()

        # Push-to-Talk Button (centered)
        self._ptt_button = PushToTalkButton()
        self._ptt_button.clicked.connect(self._on_ptt_clicked)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._ptt_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Status label
        self._status_label = QLabel(self.STATUS_TEXTS["idle"])
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("font-size: 16px;")
        self._status_label.setAccessibleName("Status-Anzeige")
        main_layout.addWidget(self._status_label)

        # Hotkey display label
        hotkey_text = self._get_hotkey_display_text()
        self._hotkey_label = QLabel(hotkey_text)
        self._hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hotkey_label.setStyleSheet(
            "font-size: 11px; color: #666666;"
        )
        main_layout.addWidget(self._hotkey_label)

        # Volume indicator (hidden by default)
        self._volume_indicator = VolumeIndicator()
        self._volume_indicator.setVisible(False)

        # Center the volume bar and limit width
        volume_layout = QHBoxLayout()
        volume_layout.addStretch()
        volume_container = QWidget()
        volume_container.setMaximumWidth(400)
        volume_container.setMinimumWidth(200)
        volume_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        volume_inner_layout = QVBoxLayout(volume_container)
        volume_inner_layout.setContentsMargins(0, 0, 0, 0)
        volume_inner_layout.addWidget(self._volume_indicator)
        volume_layout.addWidget(volume_container)
        volume_layout.addStretch()
        main_layout.addLayout(volume_layout)

        # Transcription preview
        self._transcription_preview = TranscriptionPreview()
        main_layout.addWidget(self._transcription_preview)

        # Button row for copy and clear
        button_row_layout = QHBoxLayout()
        button_row_layout.setSpacing(12)

        # Copy to clipboard button
        self._copy_button = QPushButton("In Zwischenablage kopieren")
        self._copy_button.setIcon(QIcon.fromTheme("edit-copy"))
        self._copy_button.setFixedHeight(36)
        self._copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_button.clicked.connect(self._on_copy_clicked)
        self._copy_button.setEnabled(False)  # Disabled until there's text
        self._copy_button.setStyleSheet("""
            QPushButton {
                background-color: #3584e4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4a90e8;
            }
            QPushButton:pressed {
                background-color: #2a6ac7;
            }
            QPushButton:disabled {
                background-color: #888888;
                color: #cccccc;
            }
        """)
        self._copy_button.setAccessibleName("In Zwischenablage kopieren")
        self._copy_button.setToolTip("Kopiert den transkribierten Text (Ctrl+Shift+C)")

        # Clear text button
        self._clear_button = QPushButton("Text löschen")
        self._clear_button.setIcon(QIcon.fromTheme("edit-clear"))
        self._clear_button.setFixedHeight(36)
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self._on_clear_clicked)
        self._clear_button.setEnabled(False)  # Disabled until there's text
        self._clear_button.setStyleSheet("""
            QPushButton {
                background-color: #e01b24;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f03a46;
            }
            QPushButton:pressed {
                background-color: #b8161e;
            }
            QPushButton:disabled {
                background-color: #888888;
                color: #cccccc;
            }
        """)
        self._clear_button.setAccessibleName("Text löschen")
        self._clear_button.setToolTip("Löscht den transkribierten Text")

        # Center the buttons
        button_row_layout.addStretch()
        button_row_layout.addWidget(self._copy_button)
        button_row_layout.addWidget(self._clear_button)
        button_row_layout.addStretch()
        main_layout.addLayout(button_row_layout)

        # Spacer at bottom
        main_layout.addStretch()

    def _setup_header_bar(self) -> None:
        """Create GNOME-style header bar with settings button."""
        toolbar = QToolBar("Header Bar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setFixedHeight(36)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        # App title
        title_label = QLabel("TranscribrAI")
        title_label.setStyleSheet(
            "font-weight: bold; font-size: 11pt; padding-left: 8px;"
        )
        toolbar.addWidget(title_label)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        toolbar.addWidget(spacer)

        # Settings button
        self._settings_button = QToolButton()
        settings_icon = QIcon.fromTheme("preferences-system")
        if settings_icon.isNull():
            settings_icon = QIcon.fromTheme("emblem-system")
        if settings_icon.isNull():
            self._settings_button.setText("⚙")
        else:
            self._settings_button.setIcon(settings_icon)

        self._settings_button.setToolTip("Einstellungen (Ctrl+,)")
        self._settings_button.setAccessibleName("Einstellungen")
        self._settings_button.clicked.connect(self._on_settings_clicked)
        toolbar.addWidget(self._settings_button)

    def _setup_shortcuts(self) -> None:
        """Configure keyboard shortcuts."""
        # Settings shortcut (Ctrl+,)
        settings_shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        settings_shortcut.activated.connect(self._on_settings_clicked)

        # Copy to clipboard shortcut (Ctrl+Shift+C)
        copy_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        copy_shortcut.activated.connect(self._on_copy_clicked)

        # Toggle recording with Space when button is focused
        # Note: This is handled naturally by QPushButton when focused

        # Quit shortcut (Ctrl+Q)
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.close)

    def _get_hotkey_display_text(self) -> str:
        """
        Get the hotkey display text from app config.

        Returns:
            Formatted hotkey string for display.
        """
        if self._app:
            hotkey = self._app.config.get("hotkey", "Ctrl+Shift+Space")
        else:
            hotkey = "Ctrl+Shift+Space"

        return f"Hotkey: {hotkey}"

    def _connect_app_callbacks(self) -> None:
        """
        Connect TranscribrApp callbacks to UI update methods.

        Uses Qt signals to ensure thread-safe UI updates. The app callbacks
        may be invoked from background threads (audio thread, transcription
        thread), so we emit signals that are automatically queued and
        dispatched on the Qt main thread.

        We use Qt.QueuedConnection explicitly to ensure signals emitted from
        background threads are properly marshalled to the main thread's event
        loop, avoiding potential deadlocks.
        """
        # Connect internal signals to UI update slots with QueuedConnection
        # This ensures thread-safe cross-thread signal delivery
        self._volume_level_signal.connect(
            self.update_volume, Qt.ConnectionType.QueuedConnection
        )
        self._state_changed_signal.connect(
            self.update_status, Qt.ConnectionType.QueuedConnection
        )
        self._transcription_ready_signal.connect(
            self.append_transcription, Qt.ConnectionType.QueuedConnection
        )
        self._error_signal.connect(
            self._handle_error_message, Qt.ConnectionType.QueuedConnection
        )

        if not self._app:
            return

        # Import AppState here to avoid circular imports
        from transcribrai.app import AppState

        def on_state_changed(old_state: AppState, new_state: AppState) -> None:
            """Handle app state changes - emits signal for thread safety."""
            state_name = new_state.name.lower()
            self._state_changed_signal.emit(state_name)

        def on_volume_level(level: float) -> None:
            """Handle volume level updates - emits signal for thread safety."""
            self._volume_level_signal.emit(level)

        def on_transcription_ready(text: str) -> None:
            """Handle transcription completion - emits signal for thread safety."""
            self._transcription_ready_signal.emit(text)

        def on_error(error: Exception) -> None:
            """Handle errors - emits signal for thread safety."""
            self._error_signal.emit(str(error))

        self._app.on_state_changed = on_state_changed
        self._app.on_volume_level = on_volume_level
        self._app.on_transcription_ready = on_transcription_ready
        self._app.on_error = on_error

    def _handle_error_message(self, error_message: str) -> None:
        """
        Handle error message from background thread.

        Args:
            error_message: The error message string.
        """
        self.update_status("error")
        logger.error(f"App error: {error_message}")

    def _on_ptt_clicked(self) -> None:
        """Handle push-to-talk button click."""
        logger.debug("PTT button clicked")
        self.push_to_talk_clicked.emit()

        if self._app:
            self._app.toggle_recording()

    def _on_settings_clicked(self) -> None:
        """Handle settings button click - open settings dialog."""
        logger.debug("Opening settings dialog")
        self.settings_requested.emit()

        dialog = SettingsDialog(self)

        # Load current settings from app
        if self._app:
            dialog.load_settings(self._app.config)

        # Connect settings changed signal
        dialog.settings_changed.connect(self._on_settings_changed)

        dialog.exec()

    def _on_settings_changed(self, new_settings: dict) -> None:
        """
        Handle settings changes from the settings dialog.

        Args:
            new_settings: Dictionary with new settings values.
        """
        if not self._app:
            return

        logger.info(f"Applying new settings: {new_settings}")

        # Update app configuration
        self._app.update_config(**new_settings)

        # Update hotkey display
        if "hotkey" in new_settings:
            self.update_hotkey_display(new_settings["hotkey"])

        # Apply hotkey change if app is running
        if "hotkey" in new_settings and self._app.is_running:
            try:
                self._app.set_hotkey(new_settings["hotkey"])
            except Exception as e:
                logger.error(f"Failed to apply hotkey: {e}")

        # Apply transcription settings (model, language, device)
        if "transcription" in new_settings:
            trans_settings = new_settings["transcription"]
            try:
                self._app.apply_transcription_settings(
                    model_size=trans_settings.get("model_size"),
                    language=trans_settings.get("language"),
                    device=trans_settings.get("device")
                )
            except Exception as e:
                logger.error(f"Failed to apply transcription settings: {e}")

        # Apply audio device change
        if "audio" in new_settings:
            audio_settings = new_settings["audio"]
            device_index = audio_settings.get("device_index")
            try:
                self._app.set_audio_device(device_index)
            except Exception as e:
                logger.error(f"Failed to apply audio device: {e}")

        # Save configuration
        try:
            self._app.save_config()
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _on_copy_clicked(self) -> None:
        """Copy transcription text to clipboard."""
        text = self._transcription_preview._text_edit.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            logger.info(f"Copied {len(text)} chars to clipboard")

            # Visual feedback - temporarily change button text
            original_text = self._copy_button.text()
            self._copy_button.setText("✓ Kopiert!")
            self._copy_button.setStyleSheet("""
                QPushButton {
                    background-color: #33d17a;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }
            """)

            # Reset after 1.5 seconds
            QTimer.singleShot(1500, lambda: self._reset_copy_button(original_text))

    def _reset_copy_button(self, original_text: str) -> None:
        """Reset copy button to original state."""
        self._copy_button.setText(original_text)
        self._copy_button.setStyleSheet("""
            QPushButton {
                background-color: #3584e4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4a90e8;
            }
            QPushButton:pressed {
                background-color: #2a6ac7;
            }
            QPushButton:disabled {
                background-color: #888888;
                color: #cccccc;
            }
        """)

    def _on_clear_clicked(self) -> None:
        """Clear the transcription text."""
        self.clear_transcription()
        logger.info("Transcription text cleared")

    # --- Public Slots ---

    def update_status(self, state: str) -> None:
        """
        Update the UI to reflect a new application state.

        Changes the button color, status text, and volume indicator
        visibility based on the state.

        Args:
            state: State name ('idle', 'recording', 'transcribing', 'sending', 'error').
        """
        self._current_state = state.lower()

        # Update button styling
        self._ptt_button.set_state(self._current_state)

        # Update status text
        status_text = self.STATUS_TEXTS.get(
            self._current_state,
            self.STATUS_TEXTS["idle"]
        )
        self._status_label.setText(status_text)

        # Update status label color based on state
        color = self._get_status_color(self._current_state)
        self._status_label.setStyleSheet(f"font-size: 16px; color: {color};")

        # Show/hide volume indicator
        self._volume_indicator.setVisible(self._current_state == "recording")

        # Reset volume when not recording
        if self._current_state != "recording":
            self._volume_indicator.setValue(0)

        logger.debug(f"UI state updated to: {self._current_state}")

    def _get_status_color(self, state: str) -> str:
        """
        Get the appropriate text color for a state.

        Args:
            state: The state name.

        Returns:
            Hex color string.
        """
        colors = {
            "idle": GnomeColors.BLUE_IDLE,
            "recording": GnomeColors.RED_RECORDING,
            "transcribing": GnomeColors.YELLOW_TRANSCRIBING,
            "sending": GnomeColors.GREEN_SENDING,
            "error": GnomeColors.ORANGE_WARNING,
        }
        return colors.get(state, GnomeColors.TEXT_DARK)

    def update_volume(self, level: float) -> None:
        """
        Update the volume indicator level.

        Args:
            level: Volume level from 0.0 to 1.0.
        """
        if self._current_state == "recording":
            self._volume_indicator.set_volume(level)

    def append_transcription(self, text: str) -> None:
        """
        Append transcribed text to the preview area.

        Args:
            text: The transcribed text to display.
        """
        self._transcription_preview.append_text(text)
        # Enable buttons when there's text
        self._copy_button.setEnabled(True)
        self._clear_button.setEnabled(True)

    def set_transcription(self, text: str) -> None:
        """
        Set the transcription preview text (replacing existing).

        Args:
            text: The transcription text to display.
        """
        self._transcription_preview.set_text(text)
        # Enable buttons when there's text
        has_text = bool(text)
        self._copy_button.setEnabled(has_text)
        self._clear_button.setEnabled(has_text)

    def clear_transcription(self) -> None:
        """Clear the transcription preview."""
        self._transcription_preview.clear()
        # Disable buttons when no text
        self._copy_button.setEnabled(False)
        self._clear_button.setEnabled(False)

    def update_hotkey_display(self, hotkey: str) -> None:
        """
        Update the hotkey display label.

        Args:
            hotkey: The hotkey string to display.
        """
        self._hotkey_label.setText(f"Hotkey: {hotkey}")

    # --- Window Events ---

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        Stops the app if running before closing.

        Args:
            event: The close event.
        """
        if self._app and self._app.is_running:
            logger.info("Stopping app on window close")
            self._app.stop()

        event.accept()

    def keyPressEvent(self, event) -> None:
        """
        Handle key press events.

        Allows Space or Enter to toggle recording when the PTT button
        has focus.

        Args:
            event: The key event.
        """
        if self._ptt_button.hasFocus():
            if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._on_ptt_clicked()
                event.accept()
                return

        super().keyPressEvent(event)


def is_gnome_session() -> bool:
    """
    Check if running in a GNOME desktop session.

    Returns:
        True if GNOME session detected, False otherwise.
    """
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    return "GNOME" in desktop.upper()


def is_dark_theme() -> bool:
    """
    Check if the system is using a dark theme.

    Returns:
        True if dark theme detected, False otherwise.
    """
    palette = QApplication.palette()
    bg = palette.color(QPalette.ColorRole.Window)
    return bg.lightness() < 128
