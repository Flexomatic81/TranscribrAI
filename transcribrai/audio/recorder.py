"""
Audio recording functionality for TranscribrAI.

Provides push-to-talk audio recording with volume level callbacks.
"""

import atexit
import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Set

import numpy as np
import sounddevice as sd
import soundfile as sf

from ..exceptions import AudioRecordingError, NoAudioDeviceError

logger = logging.getLogger(__name__)

# Global registry for tracking temp files across all AudioRecorder instances
# This enables cleanup on exit even after crashes
_temp_file_registry: Set[Path] = set()
_temp_file_lock = threading.Lock()


def _cleanup_temp_files() -> None:
    """
    Clean up any remaining temporary audio files on exit.

    This function is registered with atexit to ensure temp files are
    removed even if the application crashes or exits unexpectedly.
    """
    with _temp_file_lock:
        for temp_path in list(_temp_file_registry):
            try:
                if temp_path.exists():
                    temp_path.unlink()
                    logger.debug(f"Cleaned up temp file on exit: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_path}: {e}")
        _temp_file_registry.clear()


# Register cleanup function to run on interpreter exit
atexit.register(_cleanup_temp_files)


def unregister_temp_file(temp_path: Path) -> None:
    """
    Remove a temp file from the cleanup registry after it has been processed.

    Call this function after successfully processing and deleting a temp audio
    file to remove it from the atexit cleanup registry.

    Args:
        temp_path: The path to the temp file to unregister.
    """
    with _temp_file_lock:
        _temp_file_registry.discard(temp_path)


class AudioRecorder:
    """
    Audio recorder with push-to-talk functionality.

    Records audio synchronously and stores in a pre-allocated buffer.
    """

    MAX_RECORDING_DURATION = 300  # 5 minutes

    def __init__(
        self,
        sample_rate: Optional[int] = None,
        channels: int = 1,
        device_index: Optional[int] = None
    ) -> None:
        self._requested_sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index
        self.sample_rate = 44100  # Will be updated when recording starts

        self._recording = False
        self._audio_buffer: Optional[np.ndarray] = None
        self._start_time: Optional[float] = None
        self._volume_thread: Optional[threading.Thread] = None
        self._stop_volume = threading.Event()

        self.on_volume_change: Optional[Callable[[float], None]] = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        """Start audio recording."""
        if self._recording:
            raise AudioRecordingError("Recording already active")

        try:
            # Get compatible sample rate
            self.sample_rate = self._get_compatible_sample_rate()

            # Log device info
            try:
                device_info = sd.query_devices(self.device_index, 'input')
                logger.info(f"Using device: {device_info['name']}, rate={self.sample_rate}Hz")
            except Exception as e:
                logger.warning(f"Could not query device: {e}")

            # Pre-allocate buffer for max duration
            frames = int(self.MAX_RECORDING_DURATION * self.sample_rate)
            self._audio_buffer = np.zeros((frames, self.channels), dtype=np.float32)

            self._recording = True
            self._start_time = time.time()
            self._stop_volume.clear()

            # Start non-blocking recording into the buffer
            # This call returns immediately, recording happens in background
            sd.rec(
                frames,
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device_index,
                dtype=np.float32,
                out=self._audio_buffer,
                blocking=False
            )

            logger.info(f"Started recording (device={self.device_index}, rate={self.sample_rate}Hz)")

            # Start volume monitoring in a separate thread
            if self.on_volume_change:
                self._volume_thread = threading.Thread(
                    target=self._monitor_volume,
                    daemon=True,
                    name="VolumeMonitor"
                )
                self._volume_thread.start()

        except sd.PortAudioError as e:
            self._recording = False
            self._audio_buffer = None
            raise AudioRecordingError(f"Recording failed: {e}") from e
        except Exception as e:
            self._recording = False
            self._audio_buffer = None
            raise AudioRecordingError(f"Recording failed: {e}") from e

    def _monitor_volume(self) -> None:
        """Monitor volume levels during recording."""
        last_pos = 0

        while not self._stop_volume.is_set() and self._recording:
            time.sleep(0.05)  # 50ms updates

            if self._audio_buffer is None or self._start_time is None:
                continue

            # Calculate current position based on elapsed time
            elapsed = time.time() - self._start_time
            current_pos = min(int(elapsed * self.sample_rate), len(self._audio_buffer))

            if current_pos > last_pos:
                # Get new samples
                new_samples = self._audio_buffer[last_pos:current_pos]
                last_pos = current_pos

                if len(new_samples) > 0:
                    rms = np.sqrt(np.mean(new_samples ** 2))
                    volume = min(1.0, rms * 10)
                    try:
                        self.on_volume_change(volume)
                    except Exception as e:
                        logger.warning(f"Error in volume change callback: {e}")

    def _get_compatible_sample_rate(self) -> int:
        """Get a compatible sample rate for the device."""
        try:
            device_info = sd.query_devices(self.device_index, 'input')
            default_rate = int(device_info['default_samplerate'])

            # If no specific rate requested, use device default
            if self._requested_sample_rate is None:
                return default_rate

            # Check if requested rate is supported
            try:
                sd.check_input_settings(device=self.device_index, samplerate=self._requested_sample_rate)
                return self._requested_sample_rate
            except sd.PortAudioError:
                logger.warning(f"Sample rate {self._requested_sample_rate}Hz not supported, using {default_rate}Hz")
                return default_rate
        except Exception as e:
            logger.warning(f"Could not query device: {e}")
            return 44100

    def stop_recording(self) -> Optional[Path]:
        """Stop recording and save to file."""
        if not self._recording:
            raise AudioRecordingError("No active recording")

        # Calculate duration before stopping
        actual_duration = time.time() - self._start_time if self._start_time else 0
        actual_samples = int(actual_duration * self.sample_rate)

        self._recording = False
        self._stop_volume.set()

        # Stop the recording and wait for buffer to be fully written
        sd.stop()
        sd.wait()

        # Stop volume thread
        if self._volume_thread:
            self._volume_thread.join(timeout=1.0)
            self._volume_thread = None

        # Process the recorded data
        try:
            if self._audio_buffer is None:
                logger.warning("No audio buffer")
                return None

            # Trim to actual duration
            actual_samples = min(actual_samples, len(self._audio_buffer))
            audio = self._audio_buffer[:actual_samples].copy()

            if len(audio) == 0:
                logger.warning("No audio captured (0 samples)")
                return None

            # Flatten for mono
            if self.channels == 1 and len(audio.shape) > 1:
                audio = audio.flatten()

            # Check audio levels
            max_amp = np.max(np.abs(audio))
            rms = np.sqrt(np.mean(audio ** 2))
            duration = len(audio) / self.sample_rate

            logger.info(f"Captured {duration:.2f}s, max_amp={max_amp:.4f}, rms={rms:.6f}")

            if max_amp < 0.001:
                logger.warning("Audio is essentially silent!")

            # Normalize if clipping (values > 1.0)
            if max_amp > 1.0:
                logger.debug(f"Normalizing audio (was clipping at {max_amp:.4f})")
                audio = audio / max_amp * 0.95  # Normalize to 95% to avoid edge clipping

            # Save to file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False, prefix='transcribrai_')
            temp_path = Path(temp_file.name)
            temp_file.close()

            # Register temp file for cleanup on exit
            with _temp_file_lock:
                _temp_file_registry.add(temp_path)

            sf.write(temp_path, audio, self.sample_rate)
            logger.info(f"Saved to {temp_path}")

            return temp_path

        except Exception as e:
            raise AudioRecordingError(f"Failed to save: {e}") from e
        finally:
            self._audio_buffer = None

    def cancel_recording(self) -> None:
        """Cancel recording without saving."""
        self._recording = False
        self._stop_volume.set()
        sd.stop()

        if self._volume_thread:
            self._volume_thread.join(timeout=1.0)
            self._volume_thread = None

        self._audio_buffer = None
        logger.info("Recording cancelled")

    def set_device(self, device_index: Optional[int]) -> None:
        if self._recording:
            raise AudioRecordingError("Cannot change device while recording")
        self.device_index = device_index

    def set_sample_rate(self, sample_rate: int) -> None:
        if self._recording:
            raise AudioRecordingError("Cannot change rate while recording")
        self._requested_sample_rate = sample_rate
