"""
Custom exceptions for TranscribrAI.

This module defines application-specific exceptions for better error handling
and user feedback across all components.
"""


class TranscribrAIError(Exception):
    """Base exception for all TranscribrAI errors."""
    pass


# Audio Exceptions
class AudioError(TranscribrAIError):
    """Base exception for audio-related errors."""
    pass


class AudioDeviceError(AudioError):
    """Raised when there's an issue with audio devices."""
    pass


class AudioRecordingError(AudioError):
    """Raised when audio recording fails."""
    pass


class NoAudioDeviceError(AudioDeviceError):
    """Raised when no audio input device is available."""
    pass


# Transcription Exceptions
class TranscriptionError(TranscribrAIError):
    """Base exception for transcription-related errors."""
    pass


class ModelLoadError(TranscriptionError):
    """Raised when the Whisper model fails to load."""
    pass


class TranscriptionFailedError(TranscriptionError):
    """Raised when transcription of audio fails."""
    pass


# Input Exceptions
class InputError(TranscribrAIError):
    """Base exception for text input-related errors."""
    pass


class InputSimulationError(InputError):
    """Raised when keyboard input simulation fails."""
    pass


class YdotoolNotAvailableError(InputError):
    """Raised when ydotool is not available on Wayland."""
    pass


# Hotkey Exceptions
class HotkeyError(TranscribrAIError):
    """Base exception for hotkey-related errors."""
    pass


class HotkeyRegistrationError(HotkeyError):
    """Raised when global hotkey registration fails."""
    pass


class EvdevPermissionError(HotkeyError):
    """Raised when user lacks permissions for evdev (not in 'input' group)."""
    pass


# Configuration Exceptions
class ConfigurationError(TranscribrAIError):
    """Raised when configuration loading or saving fails."""
    pass
