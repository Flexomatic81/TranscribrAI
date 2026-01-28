"""
Audio module for TranscribrAI.

Provides audio recording functionality and device management.
"""

from .recorder import AudioRecorder, unregister_temp_file
from .devices import AudioDeviceManager

__all__ = ['AudioRecorder', 'AudioDeviceManager', 'unregister_temp_file']
