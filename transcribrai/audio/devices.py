"""
Audio device management for TranscribrAI.

Provides functionality to enumerate and manage audio input devices.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import sounddevice as sd

from ..exceptions import AudioDeviceError, NoAudioDeviceError

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    index: int
    name: str
    channels: int
    default_sample_rate: float
    is_default: bool = False

    def __str__(self) -> str:
        default_marker = " (Standard)" if self.is_default else ""
        return f"{self.name}{default_marker}"


class AudioDeviceManager:
    """
    Manages audio input devices.

    Provides methods to enumerate available input devices and select
    the appropriate device for recording.

    Example:
        >>> manager = AudioDeviceManager()
        >>> devices = manager.get_input_devices()
        >>> for device in devices:
        ...     print(device)
        >>> selected = manager.get_device_by_index(0)
    """

    def __init__(self) -> None:
        """Initialize the audio device manager."""
        self._devices: list[AudioDevice] = []
        self._default_device_index: Optional[int] = None
        self.refresh_devices()

    def refresh_devices(self) -> None:
        """
        Refresh the list of available audio input devices.

        Raises:
            AudioDeviceError: If querying devices fails.
        """
        try:
            self._devices.clear()
            devices = sd.query_devices()

            # Get default input device
            try:
                default_input = sd.query_devices(kind='input')
                self._default_device_index = default_input.get('index') if isinstance(default_input, dict) else None
            except sd.PortAudioError:
                self._default_device_index = None

            for idx, device in enumerate(devices):
                # Only include input devices (max_input_channels > 0)
                if device.get('max_input_channels', 0) > 0:
                    audio_device = AudioDevice(
                        index=idx,
                        name=device.get('name', f'Device {idx}'),
                        channels=device.get('max_input_channels', 1),
                        default_sample_rate=device.get('default_samplerate', 44100.0),
                        is_default=(idx == self._default_device_index)
                    )
                    self._devices.append(audio_device)

            logger.info(f"Found {len(self._devices)} audio input device(s)")

        except Exception as e:
            logger.error(f"Failed to query audio devices: {e}")
            raise AudioDeviceError(f"Failed to query audio devices: {e}") from e

    def get_input_devices(self) -> list[AudioDevice]:
        """
        Get list of available audio input devices.

        Returns:
            List of AudioDevice objects representing available input devices.
        """
        return self._devices.copy()

    def get_default_device(self) -> Optional[AudioDevice]:
        """
        Get the default audio input device.

        Returns:
            The default AudioDevice, or None if no default is available.
        """
        for device in self._devices:
            if device.is_default:
                return device
        return self._devices[0] if self._devices else None

    def get_device_by_index(self, index: int) -> AudioDevice:
        """
        Get an audio device by its index.

        Args:
            index: The device index to look up.

        Returns:
            The AudioDevice with the specified index.

        Raises:
            AudioDeviceError: If no device with the given index exists.
        """
        for device in self._devices:
            if device.index == index:
                return device
        raise AudioDeviceError(f"No audio device with index {index}")

    def get_device_by_name(self, name: str) -> Optional[AudioDevice]:
        """
        Get an audio device by its name (partial match).

        Args:
            name: The device name or partial name to search for.

        Returns:
            The first matching AudioDevice, or None if not found.
        """
        name_lower = name.lower()
        for device in self._devices:
            if name_lower in device.name.lower():
                return device
        return None

    def has_devices(self) -> bool:
        """Check if any audio input devices are available."""
        return len(self._devices) > 0

    def validate_device_available(self) -> None:
        """
        Validate that at least one audio input device is available.

        Raises:
            NoAudioDeviceError: If no audio input devices are found.
        """
        if not self.has_devices():
            raise NoAudioDeviceError(
                "Kein Audio-Eingabegerät gefunden. "
                "Bitte verbinden Sie ein Mikrofon und versuchen Sie es erneut."
            )
