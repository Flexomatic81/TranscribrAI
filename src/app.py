"""
Main application controller for TranscribrAI.

This module provides the central TranscribrApp class that orchestrates all
components of the application: audio recording, transcription, text input,
and hotkey management. It implements a state machine to manage the application
flow and provides callbacks for GUI integration.

Example:
    >>> app = TranscribrApp()
    >>> app.on_transcription_ready = lambda text: print(f"Transcribed: {text}")
    >>> app.start()
    >>> # ... user presses hotkey, speaks, releases hotkey ...
    >>> app.stop()
"""

import copy
import json
import logging
from enum import Enum, auto
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, Optional

from .audio import AudioRecorder, AudioDeviceManager
from .transcription import WhisperTranscriber
from .input import TerminalInput
from .hotkey import HotkeyManager
from .exceptions import (
    ConfigurationError,
    HotkeyError,
    TranscribrAIError,
)

logger = logging.getLogger(__name__)

# Default configuration file path
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "transcribrai" / "config.json"

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "hotkey": "ctrl+shift+space",
    "audio": {
        "sample_rate": None,  # Use device native rate for best PipeWire compatibility
        "channels": 1,
        "device_index": None,
    },
    "transcription": {
        "model_size": "base",
        "language": "de",
        "device": "auto",
    },
    "input": {
        "delay_ms": 10,
    },
}


class AppState(Enum):
    """
    Application states for the TranscribrAI state machine.

    The application transitions between these states based on user actions
    and processing results:

    - IDLE: Application is ready, waiting for user to press the hotkey.
    - RECORDING: User is holding the hotkey and speaking; audio is being captured.
    - TRANSCRIBING: Recording finished, audio is being transcribed by Whisper.
    - SENDING: Transcription complete, text is being typed into the target application.

    State transitions:
        IDLE -> RECORDING (hotkey pressed)
        RECORDING -> TRANSCRIBING (hotkey released)
        TRANSCRIBING -> SENDING (transcription complete)
        SENDING -> IDLE (text input complete)

        Any state -> IDLE (error or cancellation)
    """

    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    SENDING = auto()


class TranscribrApp:
    """
    Main application controller that orchestrates all TranscribrAI components.

    Manages the lifecycle of audio recording, speech transcription, and text
    input components. Implements a state machine to handle the push-to-talk
    workflow and provides callbacks for GUI integration.

    Attributes:
        state: Current application state (AppState enum).
        config: Current configuration dictionary.

    Callbacks:
        on_state_changed: Called when application state changes.
                         Signature: (old_state: AppState, new_state: AppState) -> None
        on_transcription_ready: Called when transcription is complete.
                               Signature: (text: str) -> None
        on_volume_level: Called with real-time volume level during recording.
                        Signature: (level: float) -> None  # level is 0.0 to 1.0
        on_error: Called when an error occurs.
                 Signature: (error: Exception) -> None

    Example:
        >>> app = TranscribrApp()
        >>> app.on_state_changed = lambda old, new: print(f"State: {old} -> {new}")
        >>> app.on_transcription_ready = lambda text: print(f"Result: {text}")
        >>> app.on_error = lambda e: print(f"Error: {e}")
        >>> app.start()
        >>> # Application runs, user uses hotkey to record and transcribe
        >>> app.stop()

    Note:
        The application automatically loads configuration from the default
        config file path if it exists. Use load_config() and save_config()
        for explicit configuration management.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize the TranscribrAI application controller.

        Creates instances of all required components (AudioRecorder,
        WhisperTranscriber, TerminalInput, HotkeyManager) and sets up
        the initial state.

        Args:
            config_path: Path to the configuration file. If None, uses the
                        default path (~/.config/transcribrai/config.json).
                        If the file doesn't exist, default settings are used.

        Raises:
            ConfigurationError: If the config file exists but cannot be parsed.
        """
        self._config_path = config_path or DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._state = AppState.IDLE
        self._state_lock = Lock()
        self._running = False

        # Load configuration if available
        if self._config_path.exists():
            try:
                self.load_config(self._config_path)
            except ConfigurationError:
                logger.warning(
                    f"Failed to load config from {self._config_path}, using defaults"
                )

        # Initialize components (lazy initialization - created but not started)
        self._recorder: Optional[AudioRecorder] = None
        self._transcriber: Optional[WhisperTranscriber] = None
        self._text_input: Optional[TerminalInput] = None
        self._hotkey_manager: Optional[HotkeyManager] = None

        # Temporary audio file path for current recording
        self._current_audio_file: Optional[Path] = None

        # Callbacks for GUI integration
        self.on_state_changed: Optional[Callable[[AppState, AppState], None]] = None
        self.on_transcription_ready: Optional[Callable[[str], None]] = None
        self.on_volume_level: Optional[Callable[[float], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

        logger.info("TranscribrApp initialized")

    @property
    def state(self) -> AppState:
        """Get the current application state."""
        return self._state

    @property
    def config(self) -> Dict[str, Any]:
        """Get a copy of the current configuration."""
        return self._config.copy()

    @property
    def is_running(self) -> bool:
        """Check if the application is currently running."""
        return self._running

    def _set_state(self, new_state: AppState) -> None:
        """
        Transition to a new application state.

        Updates the internal state and invokes the on_state_changed callback
        if registered. Thread-safe.

        Args:
            new_state: The new state to transition to.
        """
        with self._state_lock:
            old_state = self._state
            if old_state == new_state:
                return

            self._state = new_state
            logger.info(f"State transition: {old_state.name} -> {new_state.name}")

            if self.on_state_changed:
                try:
                    self.on_state_changed(old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in on_state_changed callback: {e}")

    def _handle_error(self, error: Exception) -> None:
        """
        Handle an error by logging it and notifying the callback.

        Also transitions the application back to IDLE state.

        Args:
            error: The exception that occurred.
        """
        logger.error(f"Application error: {error}")
        self._set_state(AppState.IDLE)

        if self.on_error:
            try:
                self.on_error(error)
            except Exception as e:
                logger.error(f"Error in on_error callback: {e}")

    def start(self) -> None:
        """
        Start the application and all its components.

        Initializes and starts the audio recorder, transcriber, text input,
        and hotkey manager based on the current configuration. The application
        enters the IDLE state and waits for hotkey activation.

        Raises:
            TranscribrAIError: If any component fails to initialize.

        Example:
            >>> app = TranscribrApp()
            >>> app.start()
            >>> print(app.is_running)  # True
        """
        if self._running:
            logger.warning("Application is already running")
            return

        logger.info("Starting TranscribrApp...")

        try:
            # Initialize audio recorder
            audio_config = self._config.get("audio", {})
            self._recorder = AudioRecorder(
                sample_rate=audio_config.get("sample_rate"),  # None = use device native rate
                channels=audio_config.get("channels", 1),
                device_index=audio_config.get("device_index"),
            )
            self._recorder.on_volume_change = self._on_volume_callback

            # Initialize transcriber
            transcription_config = self._config.get("transcription", {})
            # Map "auto" language to None for auto-detection
            language = transcription_config.get("language", "de")
            if language == "auto":
                language = None
            self._transcriber = WhisperTranscriber(
                model_size=transcription_config.get("model_size", "base"),
                language=language,
                device=transcription_config.get("device", "auto"),
            )
            # Start loading the Whisper model asynchronously
            self._transcriber.load_model_async()

            # Initialize text input
            input_config = self._config.get("input", {})
            # Support both old 'typing_delay' (in seconds) and new 'delay_ms' config keys
            # for backwards compatibility with existing config files
            if "delay_ms" in input_config:
                delay_ms = int(input_config.get("delay_ms", 10))
            elif "typing_delay" in input_config:
                # Convert typing_delay from seconds to milliseconds
                typing_delay = input_config.get("typing_delay", 0.01)
                delay_ms = int(typing_delay * 1000) if typing_delay < 1 else int(typing_delay)
            else:
                delay_ms = 10  # Default value
            self._text_input = TerminalInput(
                delay_ms=delay_ms,
            )

            # Initialize hotkey manager
            hotkey_str = self._config.get("hotkey", "ctrl+shift+space")
            self._hotkey_manager = HotkeyManager(hotkey=hotkey_str)
            self._hotkey_manager.on_hotkey_pressed = self._on_hotkey_pressed
            self._hotkey_manager.on_hotkey_released = self._on_hotkey_released
            self._hotkey_manager.start()

            self._running = True
            self._set_state(AppState.IDLE)
            logger.info("TranscribrApp started successfully")

        except Exception as e:
            self._cleanup_components()
            raise TranscribrAIError(f"Failed to start application: {e}") from e

    def stop(self) -> None:
        """
        Stop the application and release all resources.

        Stops all components (hotkey manager, recorder, transcriber, text input)
        and cleans up any temporary files. Safe to call multiple times.

        Example:
            >>> app.stop()
            >>> print(app.is_running)  # False
        """
        if not self._running:
            return

        logger.info("Stopping TranscribrApp...")

        # Cancel any ongoing recording
        if self._recorder and self._recorder.is_recording:
            try:
                self._recorder.cancel_recording()
            except Exception as e:
                logger.warning(f"Error canceling recording: {e}")

        self._cleanup_components()
        self._running = False
        self._set_state(AppState.IDLE)

        logger.info("TranscribrApp stopped")

    def _cleanup_components(self) -> None:
        """Clean up and release all component resources."""
        # Stop hotkey manager
        if self._hotkey_manager:
            try:
                self._hotkey_manager.stop()
            except Exception as e:
                logger.warning(f"Error stopping hotkey manager: {e}")
            self._hotkey_manager = None

        # Clean up temporary audio file
        if self._current_audio_file and self._current_audio_file.exists():
            try:
                self._current_audio_file.unlink()
            except Exception as e:
                logger.warning(f"Error deleting temp file: {e}")
            self._current_audio_file = None

        # Release component references
        self._recorder = None
        self._transcriber = None
        self._text_input = None

    def _reload_transcriber(self) -> None:
        """
        Reload the Whisper transcriber with current settings.

        Unloads the current model and creates a new transcriber with
        the updated configuration. Loads the model asynchronously.
        """
        if self._state != AppState.IDLE:
            logger.warning("Cannot reload transcriber while not idle")
            return

        logger.info("Reloading Whisper transcriber...")

        # Unload current model
        if self._transcriber:
            self._transcriber.unload_model()

        # Get current transcription settings
        transcription_config = self._config.get("transcription", {})
        language = transcription_config.get("language")
        if language == "auto":
            language = None

        # Create new transcriber
        self._transcriber = WhisperTranscriber(
            model_size=transcription_config.get("model_size", "base"),
            language=language,
            device=transcription_config.get("device", "auto"),
        )

        # Load model asynchronously
        self._transcriber.load_model_async()
        logger.info("Transcriber reload initiated")

    def toggle_recording(self) -> None:
        """
        Toggle recording state manually (without hotkey).

        If the application is IDLE, starts recording. If recording,
        stops and begins transcription. Useful for GUI buttons.

        Example:
            >>> if app.state == AppState.IDLE:
            ...     app.toggle_recording()  # Start recording
            >>> # ... user speaks ...
            >>> if app.state == AppState.RECORDING:
            ...     app.toggle_recording()  # Stop and transcribe
        """
        if self._state == AppState.IDLE:
            self._start_recording()
        elif self._state == AppState.RECORDING:
            self._stop_recording_and_transcribe()

    def _on_hotkey_pressed(self) -> None:
        """Callback for when the hotkey is pressed."""
        if self._state == AppState.IDLE:
            self._start_recording()

    def _on_hotkey_released(self) -> None:
        """Callback for when the hotkey is released."""
        if self._state == AppState.RECORDING:
            self._stop_recording_and_transcribe()

    def _on_volume_callback(self, level: float) -> None:
        """Forward volume level to the registered callback."""
        if self.on_volume_level:
            try:
                self.on_volume_level(level)
            except Exception as e:
                logger.warning(f"Error in on_volume_level callback: {e}")

    def _start_recording(self) -> None:
        """
        Start audio recording.

        Transitions to RECORDING state and begins capturing audio.
        """
        if not self._recorder:
            self._handle_error(TranscribrAIError("Audio recorder not initialized"))
            return

        try:
            self._set_state(AppState.RECORDING)
            self._recorder.start_recording()
            logger.debug("Recording started")
        except Exception as e:
            self._handle_error(e)

    def _stop_recording_and_transcribe(self) -> None:
        """
        Stop recording and begin transcription asynchronously.

        Saves the recorded audio to a temporary file and starts
        the transcription process in a background thread to avoid
        blocking the UI.
        """
        if not self._recorder or not self._transcriber:
            self._handle_error(TranscribrAIError("Components not initialized"))
            return

        try:
            # Stop recording and get audio file
            audio_file = self._recorder.stop_recording()

            if audio_file is None:
                logger.warning("No audio captured")
                self._set_state(AppState.IDLE)
                return

            self._current_audio_file = audio_file
            self._set_state(AppState.TRANSCRIBING)

            # Set up callbacks for async transcription
            def on_transcription_complete(transcription: str) -> None:
                """Handle successful transcription."""
                # Clean up audio file
                if self._current_audio_file and self._current_audio_file.exists():
                    try:
                        self._current_audio_file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete temp audio file: {e}")
                self._current_audio_file = None

                if not transcription or not transcription.strip():
                    logger.warning("Empty transcription result")
                    self._set_state(AppState.IDLE)
                    return

                # Notify callback (UI will display the text)
                if self.on_transcription_ready:
                    try:
                        self.on_transcription_ready(transcription)
                    except Exception as e:
                        logger.error(f"Error in on_transcription_ready callback: {e}")

                # Return to idle state - user can copy text manually
                self._set_state(AppState.IDLE)
                logger.info(f"Transcription ready: {transcription[:50]}...")

            def on_transcription_error(error: Exception) -> None:
                """Handle transcription failure."""
                # Clean up audio file
                if self._current_audio_file and self._current_audio_file.exists():
                    try:
                        self._current_audio_file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete temp audio file: {e}")
                self._current_audio_file = None

                self._handle_error(error)

            # Register callbacks
            self._transcriber.on_transcription_complete = on_transcription_complete
            self._transcriber.on_transcription_error = on_transcription_error

            # Start async transcription (non-blocking)
            logger.debug(f"Starting async transcription of: {audio_file}")
            self._transcriber.transcribe_async(audio_file)

        except Exception as e:
            self._handle_error(e)

    def _send_text(self, text: str) -> None:
        """
        Send transcribed text to the active window.

        Args:
            text: The transcribed text to type.
        """
        if not self._text_input:
            self._handle_error(TranscribrAIError("Text input not initialized"))
            return

        try:
            self._set_state(AppState.SENDING)
            logger.debug(f"Sending text: {text[:50]}...")
            self._text_input.type_text(text)
            self._set_state(AppState.IDLE)
            logger.debug("Text sent successfully")
        except Exception as e:
            self._handle_error(e)

    def load_config(self, config_path: Optional[Path] = None) -> None:
        """
        Load configuration from a JSON file.

        Reads the configuration file and merges it with default values.
        Missing keys in the file will use default values.

        Args:
            config_path: Path to the config file. If None, uses the path
                        specified during initialization.

        Raises:
            ConfigurationError: If the file cannot be read or parsed.

        Example:
            >>> app.load_config(Path("/path/to/custom_config.json"))
        """
        path = config_path or self._config_path

        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}") from e
        except OSError as e:
            raise ConfigurationError(f"Failed to read config file: {e}") from e

        # Merge with defaults (deep merge for nested dicts)
        self._config = self._merge_config(DEFAULT_CONFIG, loaded_config)
        logger.info(f"Configuration loaded from {path}")

    def save_config(self, config_path: Optional[Path] = None) -> None:
        """
        Save the current configuration to a JSON file.

        Creates the parent directory if it doesn't exist.

        Args:
            config_path: Path to save the config file. If None, uses the
                        path specified during initialization.

        Raises:
            ConfigurationError: If the file cannot be written.

        Example:
            >>> app.config["hotkey"] = "ctrl+alt+r"
            >>> app.save_config()
        """
        path = config_path or self._config_path

        try:
            # Create parent directory if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

            logger.info(f"Configuration saved to {path}")
        except OSError as e:
            raise ConfigurationError(f"Failed to save config file: {e}") from e

    def _merge_config(
        self, default: Dict[str, Any], loaded: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep merge loaded configuration with defaults.

        Values from the loaded config override defaults. For nested
        dictionaries, merging is performed recursively.

        Args:
            default: The default configuration dictionary.
            loaded: The loaded configuration dictionary.

        Returns:
            Merged configuration dictionary.
        """
        result = default.copy()

        for key, value in loaded.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def update_config(self, **kwargs: Any) -> None:
        """
        Update configuration values.

        Accepts keyword arguments for top-level config keys.
        Changes take effect after restarting the application.

        Args:
            **kwargs: Configuration key-value pairs to update.

        Example:
            >>> app.update_config(hotkey="ctrl+alt+space")
            >>> app.update_config(audio={"sample_rate": 44100})
        """
        for key, value in kwargs.items():
            if isinstance(value, dict) and key in self._config:
                if isinstance(self._config[key], dict):
                    self._config[key].update(value)
                else:
                    self._config[key] = value
            else:
                self._config[key] = value

        logger.debug(f"Configuration updated: {list(kwargs.keys())}")

    def set_hotkey(self, hotkey_str: str) -> None:
        """
        Change the hotkey combination.

        Updates the hotkey in both the configuration and the active
        hotkey manager (if running).

        Args:
            hotkey_str: The new hotkey combination (e.g., "ctrl+alt+r").

        Raises:
            HotkeyError: If the hotkey string is invalid.

        Example:
            >>> app.set_hotkey("ctrl+alt+space")
        """
        # Validate by trying to set on manager (if exists)
        if self._hotkey_manager:
            self._hotkey_manager.set_hotkey(hotkey_str)

        self._config["hotkey"] = hotkey_str
        logger.info(f"Hotkey changed to: {hotkey_str}")

    def set_audio_device(self, device_index: Optional[int]) -> None:
        """
        Change the audio input device.

        Updates the device in both the configuration and the active
        recorder (if not currently recording).

        Args:
            device_index: Index of the audio device, or None for default.

        Raises:
            TranscribrAIError: If called while recording is active.

        Example:
            >>> devices = AudioDeviceManager.list_input_devices()
            >>> app.set_audio_device(devices[0]['index'])
        """
        if self._recorder:
            self._recorder.set_device(device_index)

        self._config.setdefault("audio", {})["device_index"] = device_index
        logger.info(f"Audio device changed to index: {device_index}")

    def apply_transcription_settings(
        self,
        model_size: Optional[str] = None,
        language: Optional[str] = None,
        device: Optional[str] = None
    ) -> None:
        """
        Apply transcription settings at runtime.

        If the model size or device changes, the model will be reloaded.
        Language changes can be applied without reloading.

        Args:
            model_size: New Whisper model size (tiny, base, small, medium, large-v3).
            language: New language setting (de, en, or None for auto).
            device: Compute device (cpu, cuda, or auto).
        """
        if not self._transcriber:
            logger.warning("Cannot apply settings - transcriber not initialized")
            return

        needs_reload = False

        # Check if model size changed
        current_model = self._config.get("transcription", {}).get("model_size")
        if model_size and model_size != current_model:
            logger.info(f"Model size changing from {current_model} to {model_size}")
            self._config.setdefault("transcription", {})["model_size"] = model_size
            needs_reload = True

        # Check if device changed
        current_device = self._config.get("transcription", {}).get("device")
        if device and device != current_device:
            logger.info(f"Compute device changing from {current_device} to {device}")
            self._config.setdefault("transcription", {})["device"] = device
            needs_reload = True

        # Apply language change (doesn't require reload)
        if language is not None:
            current_lang = self._config.get("transcription", {}).get("language")
            if language != current_lang:
                self._config.setdefault("transcription", {})["language"] = language
                # Map "auto" to None for Whisper
                whisper_lang = None if language == "auto" else language
                self._transcriber.set_language(whisper_lang)
                logger.info(f"Language changed to: {language}")

        # Reload model if needed
        if needs_reload:
            self._reload_transcriber()

    def get_audio_devices(self) -> list:
        """
        Get a list of available audio input devices.

        Returns:
            List of dictionaries with device information (index, name, etc.).

        Example:
            >>> devices = app.get_audio_devices()
            >>> for dev in devices:
            ...     print(f"{dev['index']}: {dev['name']}")
        """
        return AudioDeviceManager.list_input_devices()

    def __enter__(self) -> "TranscribrApp":
        """Context manager entry: start the application."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: stop the application."""
        self.stop()
