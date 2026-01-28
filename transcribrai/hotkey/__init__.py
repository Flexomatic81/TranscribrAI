"""
Hotkey module for TranscribrAI.

Provides global hotkey management for push-to-talk functionality,
supporting both X11 (via pynput) and Wayland (via evdev).
"""

from .manager import HotkeyManager

__all__ = ['HotkeyManager']
