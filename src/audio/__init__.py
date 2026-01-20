"""
Audio module for TranscribrAI.

Provides audio recording functionality and device management.
"""

from .recorder import AudioRecorder
from .devices import AudioDeviceManager

__all__ = ['AudioRecorder', 'AudioDeviceManager']
