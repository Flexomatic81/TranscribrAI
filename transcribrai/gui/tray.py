"""
System tray icon and menu for TranscribrAI.

This module provides a system tray integration that allows users to:
- View the current application state via icon color changes
- Toggle recording on/off
- Access settings
- Show/hide the main window
- Quit the application

The tray icon changes color based on the application state:
- IDLE: Blue microphone icon (ready for recording)
- RECORDING: Red icon (actively recording)
- TRANSCRIBING: Yellow icon (processing audio)
- SENDING: Green icon (typing text)
- ERROR: Orange icon with exclamation mark

Example:
    >>> from PyQt6.QtWidgets import QApplication
    >>> from transcribrai.gui.tray import SystemTray
    >>> from transcribrai.app import AppState
    >>>
    >>> app = QApplication([])
    >>> tray = SystemTray()
    >>> tray.toggle_recording_requested.connect(on_toggle_recording)
    >>> tray.quit_requested.connect(app.quit)
    >>> tray.show()
    >>> app.exec()
"""

from enum import Enum
from typing import Dict, Optional

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QMenu,
    QSystemTrayIcon,
)

from transcribrai.app import AppState


# GNOME color palette as specified in the GUI design document
COLORS: Dict[str, str] = {
    "blue": "#3584e4",      # Idle state
    "red": "#e01b24",       # Recording state
    "yellow": "#f6d32d",    # Transcribing state
    "green": "#33d17a",     # Sending state
    "orange": "#ff7800",    # Error state
    "white": "#ffffff",     # Icon foreground
    "dark": "#2e3436",      # Dark foreground
}

# Status text for tooltips (German as per design)
STATUS_TEXTS: Dict[AppState, str] = {
    AppState.IDLE: "Bereit",
    AppState.RECORDING: "Aufnahme lauft",
    AppState.TRANSCRIBING: "Transkribiere...",
    AppState.SENDING: "Sende Text...",
}

# Icon size for generated icons
ICON_SIZE = 32


class SystemTray(QSystemTrayIcon):
    """
    System tray icon for TranscribrAI with state-aware icons and context menu.

    The tray icon provides visual feedback about the application state through
    color-coded icons and offers quick access to common actions via a context
    menu. It follows the GNOME Human Interface Guidelines for system tray
    integration.

    Attributes:
        current_state: The current application state being displayed.

    Signals:
        show_window_requested: Emitted when user wants to show the main window.
        hide_window_requested: Emitted when user wants to hide the main window.
        toggle_recording_requested: Emitted when user toggles recording.
        settings_requested: Emitted when user opens settings.
        quit_requested: Emitted when user wants to quit the application.

    Example:
        >>> tray = SystemTray()
        >>> tray.show_window_requested.connect(main_window.show)
        >>> tray.toggle_recording_requested.connect(app.toggle_recording)
        >>> tray.set_state(AppState.RECORDING)
        >>> tray.show_notification("Recording", "Recording started...")
    """

    # Signals for communication with the main application
    show_window_requested = pyqtSignal()
    hide_window_requested = pyqtSignal()
    toggle_recording_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """
        Initialize the system tray icon.

        Creates the tray icon with an initial IDLE state, generates all
        state-specific icons programmatically, and sets up the context menu.

        Args:
            parent: Optional parent QObject for memory management.
        """
        super().__init__(parent)

        self._current_state: AppState = AppState.IDLE
        self._window_visible: bool = True
        self._icons: Dict[AppState, QIcon] = {}
        self._error_icon: Optional[QIcon] = None

        # Generate all state icons
        self._generate_icons()

        # Set up context menu
        self._setup_menu()

        # Set initial icon and tooltip
        self.setIcon(self._icons[AppState.IDLE])
        self._update_tooltip()

        # Connect double-click to show/hide window
        self.activated.connect(self._on_activated)

    @property
    def current_state(self) -> AppState:
        """
        Get the current application state being displayed.

        Returns:
            The current AppState value.
        """
        return self._current_state

    def set_state(self, state: AppState) -> None:
        """
        Update the tray icon and menu to reflect a new application state.

        Changes the icon color, updates the tooltip text, and modifies the
        recording menu item text based on the new state.

        Args:
            state: The new application state to display.

        Example:
            >>> tray.set_state(AppState.RECORDING)
            >>> # Icon turns red, tooltip shows "Aufnahme lauft"
        """
        self._current_state = state

        # Update icon
        if state in self._icons:
            self.setIcon(self._icons[state])

        # Update tooltip
        self._update_tooltip()

        # Update menu item text
        self._update_menu_text()

    def set_error_state(self, error_message: Optional[str] = None) -> None:
        """
        Set the tray to error state with an optional error message in tooltip.

        Displays the error icon (orange with exclamation mark) and updates
        the tooltip to show the error message if provided.

        Args:
            error_message: Optional error message to show in the tooltip.

        Example:
            >>> tray.set_error_state("Microphone not found")
            >>> # Icon turns orange, tooltip shows error message
        """
        if self._error_icon:
            self.setIcon(self._error_icon)

        if error_message:
            self.setToolTip(f"TranscribrAI - Fehler: {error_message}")
        else:
            self.setToolTip("TranscribrAI - Fehler")

    def show_notification(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 3000
    ) -> None:
        """
        Display a system notification via the tray icon.

        Uses freedesktop.org notifications on Linux via QSystemTrayIcon.
        The notification appears near the system tray area.

        Args:
            title: The notification title.
            message: The notification body text.
            icon: The icon type to display (Information, Warning, Critical).
            duration_ms: How long to show the notification in milliseconds.

        Example:
            >>> tray.show_notification(
            ...     "Transkription abgeschlossen",
            ...     "Text wurde eingegeben: 'Hallo Welt...'",
            ...     duration_ms=3000
            ... )
        """
        if self.supportsMessages():
            self.showMessage(title, message, icon, duration_ms)

    def set_window_visible(self, visible: bool) -> None:
        """
        Update the internal window visibility state.

        This updates the menu item text to reflect whether the window
        is currently shown or hidden.

        Args:
            visible: True if the main window is visible, False otherwise.
        """
        self._window_visible = visible
        self._update_window_menu_text()

    def _generate_icons(self) -> None:
        """
        Generate state-specific icons programmatically using QPainter.

        Creates colored circle icons for each application state. The icons
        are simple 32x32 pixel circles with microphone-like visual elements.
        This serves as a fallback when SVG icon files are not available.
        """
        # State to color mapping
        state_colors: Dict[AppState, str] = {
            AppState.IDLE: COLORS["blue"],
            AppState.RECORDING: COLORS["red"],
            AppState.TRANSCRIBING: COLORS["yellow"],
            AppState.SENDING: COLORS["green"],
        }

        for state, color in state_colors.items():
            self._icons[state] = self._create_microphone_icon(color)

        # Create error icon separately
        self._error_icon = self._create_error_icon()

    def _create_microphone_icon(self, color: str) -> QIcon:
        """
        Create a microphone-style icon with the specified background color.

        Generates a simple icon representing a microphone with a colored
        circular background. The microphone is rendered as a white oval
        shape with a stand.

        Args:
            color: Hex color code for the icon background (e.g., "#3584e4").

        Returns:
            QIcon with the generated microphone image.
        """
        pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw colored circle background
        bg_color = QColor(color)
        painter.setBrush(bg_color)
        painter.setPen(QPen(bg_color.darker(110), 1))
        painter.drawEllipse(1, 1, ICON_SIZE - 2, ICON_SIZE - 2)

        # Draw microphone shape (white)
        mic_color = QColor(COLORS["white"])
        painter.setBrush(mic_color)
        painter.setPen(QPen(mic_color, 1))

        # Microphone head (oval)
        mic_width = 10
        mic_height = 14
        mic_x = (ICON_SIZE - mic_width) // 2
        mic_y = 5
        painter.drawRoundedRect(mic_x, mic_y, mic_width, mic_height, 5, 5)

        # Microphone stand (lines)
        center_x = ICON_SIZE // 2
        painter.setPen(QPen(mic_color, 2))

        # U-shape around microphone
        painter.drawArc(
            mic_x - 2, mic_y + mic_height // 2,
            mic_width + 4, mic_height,
            0, -180 * 16  # Bottom half of arc
        )

        # Vertical line down
        painter.drawLine(center_x, mic_y + mic_height + 2, center_x, ICON_SIZE - 6)

        # Horizontal base
        painter.drawLine(center_x - 4, ICON_SIZE - 6, center_x + 4, ICON_SIZE - 6)

        painter.end()

        return QIcon(pixmap)

    def _create_error_icon(self) -> QIcon:
        """
        Create an error state icon with exclamation mark.

        Generates an orange circular icon with a white exclamation mark
        to indicate an error condition.

        Returns:
            QIcon with the error indicator.
        """
        pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw orange circle background
        bg_color = QColor(COLORS["orange"])
        painter.setBrush(bg_color)
        painter.setPen(QPen(bg_color.darker(110), 1))
        painter.drawEllipse(1, 1, ICON_SIZE - 2, ICON_SIZE - 2)

        # Draw exclamation mark (white)
        painter.setPen(QPen(QColor(COLORS["white"]), 3))

        center_x = ICON_SIZE // 2

        # Exclamation line
        painter.drawLine(center_x, 7, center_x, 18)

        # Exclamation dot
        painter.setBrush(QColor(COLORS["white"]))
        painter.drawEllipse(center_x - 2, 22, 4, 4)

        painter.end()

        return QIcon(pixmap)

    def _setup_menu(self) -> None:
        """
        Create and configure the context menu for the tray icon.

        Sets up the menu with the following structure:
        - TranscribrAI (title, disabled)
        - Separator
        - Aufnahme starten/stoppen (toggle recording)
        - Einstellungen... (open settings)
        - Separator
        - Fenster anzeigen/verbergen (toggle window visibility)
        - Beenden (quit application)
        """
        menu = QMenu()

        # Title action (disabled, informational)
        self._title_action = QAction("TranscribrAI", menu)
        self._title_action.setEnabled(False)
        menu.addAction(self._title_action)

        menu.addSeparator()

        # Recording toggle action
        self._recording_action = QAction("Aufnahme starten", menu)
        self._recording_action.triggered.connect(self._on_toggle_recording)
        menu.addAction(self._recording_action)

        # Settings action
        self._settings_action = QAction("Einstellungen...", menu)
        self._settings_action.triggered.connect(self._on_settings)
        menu.addAction(self._settings_action)

        menu.addSeparator()

        # Window visibility toggle action
        self._window_action = QAction("Fenster verbergen", menu)
        self._window_action.triggered.connect(self._on_toggle_window)
        menu.addAction(self._window_action)

        # Quit action
        self._quit_action = QAction("Beenden", menu)
        self._quit_action.triggered.connect(self._on_quit)
        menu.addAction(self._quit_action)

        self.setContextMenu(menu)

    def _update_tooltip(self) -> None:
        """
        Update the tooltip text based on the current application state.

        The tooltip shows "TranscribrAI - [Status]" where status is the
        German description of the current state.
        """
        status_text = STATUS_TEXTS.get(self._current_state, "Bereit")
        self.setToolTip(f"TranscribrAI - {status_text}")

    def _update_menu_text(self) -> None:
        """
        Update the recording menu item text based on the current state.

        When recording, shows "Aufnahme stoppen".
        Otherwise, shows "Aufnahme starten".
        """
        if self._current_state == AppState.RECORDING:
            self._recording_action.setText("Aufnahme stoppen")
        else:
            self._recording_action.setText("Aufnahme starten")

    def _update_window_menu_text(self) -> None:
        """
        Update the window visibility menu item text.

        When window is visible, shows "Fenster verbergen".
        When window is hidden, shows "Fenster anzeigen".
        """
        if self._window_visible:
            self._window_action.setText("Fenster verbergen")
        else:
            self._window_action.setText("Fenster anzeigen")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Handle tray icon activation (click, double-click, etc.).

        Double-clicking the tray icon toggles the main window visibility.

        Args:
            reason: The type of activation that occurred.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_toggle_window()

    def _on_toggle_recording(self) -> None:
        """
        Handle the recording toggle menu action.

        Emits the toggle_recording_requested signal for the main
        application to handle.
        """
        self.toggle_recording_requested.emit()

    def _on_settings(self) -> None:
        """
        Handle the settings menu action.

        Emits the settings_requested signal for the main application
        to open the settings dialog.
        """
        self.settings_requested.emit()

    def _on_toggle_window(self) -> None:
        """
        Handle the window visibility toggle menu action.

        Emits either show_window_requested or hide_window_requested
        based on the current window visibility state.
        """
        if self._window_visible:
            self._window_visible = False
            self.hide_window_requested.emit()
        else:
            self._window_visible = True
            self.show_window_requested.emit()

        self._update_window_menu_text()

    def _on_quit(self) -> None:
        """
        Handle the quit menu action.

        Emits the quit_requested signal for the main application
        to perform cleanup and exit.
        """
        self.quit_requested.emit()
