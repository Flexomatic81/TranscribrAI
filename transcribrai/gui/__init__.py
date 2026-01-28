"""
GUI module for TranscribrAI.

This module provides the graphical user interface components for TranscribrAI,
built with PyQt6 and following GNOME Human Interface Guidelines.

Components:
    MainWindow: The main application window with push-to-talk button and status display.
    SettingsDialog: Configuration dialog for transcription, audio, and hotkey settings.
    SystemTray: System tray icon with context menu and notifications.

Example:
    >>> from transcribrai.gui import MainWindow
    >>> from transcribrai.app import TranscribrApp
    >>>
    >>> app = TranscribrApp()
    >>> window = MainWindow(app)
    >>> window.show()
"""

from .main_window import MainWindow
from .settings import HotkeyCaptureDialog, SettingsDialog
from .tray import SystemTray

__all__ = [
    'HotkeyCaptureDialog',
    'MainWindow',
    'SettingsDialog',
    'SystemTray',
]
