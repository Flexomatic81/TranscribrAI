"""
Whisper-based speech-to-text transcription for TranscribrAI.

Provides transcription functionality using faster-whisper with support
for multiple model sizes, languages, and asynchronous operation.
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Literal, Optional, Union

import numpy as np
import soundfile as sf

try:
    from scipy import signal as scipy_signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from faster_whisper import WhisperModel

from ..exceptions import ModelLoadError, TranscriptionFailedError

logger = logging.getLogger(__name__)

# Type aliases for clarity
ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]
Language = Literal["de", "en"]


class WhisperTranscriber:
    """
    Speech-to-text transcriber using faster-whisper.

    Provides synchronous and asynchronous transcription of audio files
    using OpenAI's Whisper model through the faster-whisper implementation.
    Supports multiple model sizes and automatic or manual language detection.

    Attributes:
        model_size: The Whisper model size to use.
        language: Target language for transcription (None for auto-detection).
        device: Compute device ('cpu' or 'cuda').
        compute_type: Computation precision type.

    Callbacks:
        on_transcription_complete: Called when transcription finishes successfully.
            Signature: (text: str) -> None
        on_transcription_error: Called when transcription fails.
            Signature: (error: Exception) -> None
        on_model_loading: Called when model loading starts.
            Signature: () -> None
        on_model_loaded: Called when model loading completes.
            Signature: () -> None

    Example:
        >>> transcriber = WhisperTranscriber(model_size="base", language="de")
        >>> transcriber.on_transcription_complete = lambda text: print(f"Result: {text}")
        >>> transcriber.load_model()
        >>> transcriber.transcribe_async(Path("audio.wav"))
    """

    # Valid model sizes for validation
    VALID_MODEL_SIZES: tuple[ModelSize, ...] = ("tiny", "base", "small", "medium", "large-v3")

    # Valid languages for validation
    VALID_LANGUAGES: tuple[Language, ...] = ("de", "en")

    def __init__(
        self,
        model_size: ModelSize = "base",
        language: Optional[Language] = None,
        device: str = "cpu",
        compute_type: str = "int8"
    ) -> None:
        """
        Initialize the Whisper transcriber.

        Args:
            model_size: Whisper model size to use. Options are:
                - "tiny": Fastest, lowest accuracy (~39M parameters)
                - "base": Good balance of speed/accuracy (~74M parameters)
                - "small": Better accuracy, slower (~244M parameters)
                - "medium": High accuracy (~769M parameters)
                - "large-v3": Best accuracy, slowest (~1.5B parameters)
                Default is "base".
            language: Target language code for transcription.
                - "de": German
                - "en": English
                - None: Auto-detect language (default)
            device: Compute device to use. Default is "cpu".
                Use "cuda" for GPU acceleration if available.
            compute_type: Computation type for inference.
                Default is "int8" for CPU efficiency.
                Use "float16" for GPU or "float32" for highest precision.

        Raises:
            ValueError: If model_size or language is invalid.
        """
        if model_size not in self.VALID_MODEL_SIZES:
            raise ValueError(
                f"Invalid model_size '{model_size}'. "
                f"Valid options: {', '.join(self.VALID_MODEL_SIZES)}"
            )

        if language is not None and language not in self.VALID_LANGUAGES:
            raise ValueError(
                f"Invalid language '{language}'. "
                f"Valid options: {', '.join(self.VALID_LANGUAGES)} or None for auto-detection"
            )

        self.model_size = model_size
        self.language = language

        # Handle "auto" device selection by detecting CUDA availability
        if device == "auto":
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device

        self.compute_type = compute_type

        self._model: Optional[WhisperModel] = None
        self._model_lock = threading.Lock()
        self._transcription_lock = threading.Lock()

        # Callbacks
        self.on_transcription_complete: Optional[Callable[[str], None]] = None
        self.on_transcription_error: Optional[Callable[[Exception], None]] = None
        self.on_model_loading: Optional[Callable[[], None]] = None
        self.on_model_loaded: Optional[Callable[[], None]] = None

        logger.info(
            f"WhisperTranscriber initialized (model={model_size}, "
            f"language={language or 'auto'}, device={device})"
        )

    @property
    def is_model_loaded(self) -> bool:
        """Check if the Whisper model is currently loaded."""
        return self._model is not None

    def load_model(self) -> None:
        """
        Load the Whisper model synchronously.

        Downloads the model if not cached and loads it into memory.
        This operation can take significant time depending on the model size
        and network speed.

        Raises:
            ModelLoadError: If the model fails to load due to memory,
                network, or other issues.

        Note:
            This method is thread-safe. If the model is already loaded,
            this method returns immediately without reloading.
        """
        with self._model_lock:
            if self._model is not None:
                logger.debug("Model already loaded, skipping reload")
                return

            logger.info(f"Loading Whisper model '{self.model_size}'...")

            # Notify callback that loading is starting
            if self.on_model_loading is not None:
                try:
                    self.on_model_loading()
                except Exception as e:
                    logger.warning(f"on_model_loading callback error: {e}")

            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info(f"Whisper model '{self.model_size}' loaded successfully")

                # Notify callback that loading is complete
                if self.on_model_loaded is not None:
                    try:
                        self.on_model_loaded()
                    except Exception as e:
                        logger.warning(f"on_model_loaded callback error: {e}")

            except Exception as e:
                error_msg = f"Failed to load Whisper model '{self.model_size}': {e}"
                logger.error(error_msg)
                raise ModelLoadError(error_msg) from e

    def load_model_async(self) -> threading.Thread:
        """
        Load the Whisper model asynchronously in a background thread.

        Starts model loading in a separate thread and returns immediately.
        Use the on_model_loaded callback to be notified when loading completes.

        Returns:
            The background thread performing the model loading.
            Can be used to wait for completion with thread.join().

        Example:
            >>> transcriber = WhisperTranscriber()
            >>> transcriber.on_model_loaded = lambda: print("Model ready!")
            >>> thread = transcriber.load_model_async()
            >>> # Do other work while model loads...
            >>> thread.join()  # Wait for completion if needed
        """
        thread = threading.Thread(
            target=self._load_model_thread,
            name="WhisperModelLoader",
            daemon=True
        )
        thread.start()
        logger.debug("Started async model loading thread")
        return thread

    def _load_model_thread(self) -> None:
        """
        Internal method for async model loading.

        Handles exceptions and invokes error callback if loading fails.
        """
        try:
            self.load_model()
        except ModelLoadError as e:
            logger.error(f"Async model loading failed: {e}")
            if self.on_transcription_error is not None:
                try:
                    self.on_transcription_error(e)
                except Exception as callback_error:
                    logger.warning(f"on_transcription_error callback error: {callback_error}")

    def transcribe(self, audio_path: Union[str, Path]) -> str:
        """
        Transcribe an audio file synchronously.

        Converts speech in the audio file to text using the loaded Whisper model.
        The model must be loaded before calling this method.

        Args:
            audio_path: Path to the audio file to transcribe.
                Supported formats include WAV, MP3, FLAC, and others
                supported by ffmpeg.

        Returns:
            The transcribed text as a string.

        Raises:
            ModelLoadError: If the model has not been loaded yet.
            TranscriptionFailedError: If transcription fails due to
                file not found, invalid format, or processing errors.

        Example:
            >>> transcriber = WhisperTranscriber(model_size="base", language="de")
            >>> transcriber.load_model()
            >>> text = transcriber.transcribe("speech.wav")
            >>> print(text)
            'Hallo, dies ist ein Test.'
        """
        # Ensure path is a Path object for consistent handling
        audio_path = Path(audio_path)

        # Validate preconditions
        if self._model is None:
            raise ModelLoadError(
                "Whisper model not loaded. Call load_model() first."
            )

        if not audio_path.exists():
            raise TranscriptionFailedError(
                f"Audio file not found: {audio_path}"
            )

        logger.info(f"Starting transcription of '{audio_path}'")

        with self._transcription_lock:
            try:
                # Load audio using soundfile to bypass PyAV encoding issues
                # PyAV has problems with non-ASCII locales (de_DE.UTF-8) when
                # FFmpeg returns localized error messages
                logger.debug(f"Loading audio from {audio_path}")
                audio_data, sample_rate = sf.read(audio_path, dtype=np.float32)

                # Ensure mono audio (take first channel if stereo)
                if len(audio_data.shape) > 1:
                    audio_data = audio_data[:, 0]

                # Log audio stats for debugging
                audio_max = np.max(np.abs(audio_data))
                logger.debug(f"Audio loaded: {len(audio_data)} samples, rate={sample_rate}Hz, max_amplitude={audio_max:.4f}")

                # Resample to 16kHz if needed (Whisper expects 16kHz)
                if sample_rate != 16000:
                    logger.debug(f"Resampling from {sample_rate}Hz to 16000Hz")
                    target_length = int(len(audio_data) * 16000 / sample_rate)

                    if HAS_SCIPY:
                        # Use scipy for high-quality resampling
                        audio_data = scipy_signal.resample(audio_data, target_length).astype(np.float32)
                    else:
                        # Fallback: numpy interpolation (lower quality but works)
                        audio_data = np.interp(
                            np.linspace(0, len(audio_data) - 1, target_length),
                            np.arange(len(audio_data)),
                            audio_data
                        ).astype(np.float32)

                    logger.debug(f"Resampled to {len(audio_data)} samples")

                # Additional audio quality checks
                non_zero = np.count_nonzero(audio_data)
                logger.debug(f"Starting transcription ({len(audio_data)} samples, {non_zero} non-zero, dtype={audio_data.dtype})")

                # Pass numpy array directly to avoid PyAV
                # Note: VAD disabled to allow transcription of quiet audio
                # Lower no_speech_threshold to be less aggressive at filtering
                segments, info = self._model.transcribe(
                    audio_data,
                    language=self.language,
                    beam_size=5,
                    vad_filter=False,
                    no_speech_threshold=0.3,  # Lower from default 0.6
                    log_prob_threshold=-1.5,  # Lower from default -1.0
                )
                logger.debug(f"Transcribe call returned, language={info.language}, duration={info.duration:.2f}s")

                # Collect all segments into a single text
                # Ensure proper UTF-8 handling for German umlauts
                text_segments = []
                segment_count = 0
                for segment in segments:
                    segment_count += 1
                    # segment.text should be a str, but ensure it's properly decoded
                    segment_text = segment.text
                    if isinstance(segment_text, bytes):
                        segment_text = segment_text.decode('utf-8', errors='replace')
                    logger.debug(f"Segment {segment_count}: {segment_text!r}")
                    text_segments.append(segment_text.strip())

                transcribed_text = " ".join(text_segments).strip()
                logger.debug(f"Combined {segment_count} segments into {len(transcribed_text)} chars")

                # Log result info (use repr for safe logging of unicode)
                detected_lang = info.language if self.language is None else self.language
                logger.info(
                    f"Transcription complete (language={detected_lang}, "
                    f"duration={info.duration:.2f}s, "
                    f"text_length={len(transcribed_text)} chars)"
                )

                return transcribed_text

            except UnicodeDecodeError as e:
                import traceback
                logger.error(f"Encoding error during transcription of '{audio_path}': {e}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                raise TranscriptionFailedError(f"Encoding error: {e}") from e
            except Exception as e:
                import traceback
                logger.error(f"Transcription failed for '{audio_path}': {e}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                raise TranscriptionFailedError(f"Transcription failed: {e}") from e

    def transcribe_async(self, audio_path: Union[str, Path]) -> threading.Thread:
        """
        Transcribe an audio file asynchronously in a background thread.

        Starts transcription in a separate thread and returns immediately.
        Use the on_transcription_complete callback to receive the result,
        or on_transcription_error if transcription fails.

        Args:
            audio_path: Path to the audio file to transcribe.

        Returns:
            The background thread performing the transcription.
            Can be used to wait for completion with thread.join().

        Raises:
            ModelLoadError: If the model has not been loaded yet.
                This is checked before starting the thread.

        Example:
            >>> transcriber = WhisperTranscriber(model_size="base")
            >>> transcriber.on_transcription_complete = lambda text: print(f"Result: {text}")
            >>> transcriber.on_transcription_error = lambda e: print(f"Error: {e}")
            >>> transcriber.load_model()
            >>> thread = transcriber.transcribe_async("speech.wav")
            >>> # Continue with other work...
        """
        # Validate model is loaded before starting thread
        if self._model is None:
            raise ModelLoadError(
                "Whisper model not loaded. Call load_model() first."
            )

        audio_path = Path(audio_path)

        thread = threading.Thread(
            target=self._transcribe_thread,
            args=(audio_path,),
            name="WhisperTranscription",
            daemon=True
        )
        thread.start()
        logger.debug(f"Started async transcription thread for '{audio_path}'")
        return thread

    def _transcribe_thread(self, audio_path: Path) -> None:
        """
        Internal method for async transcription.

        Performs transcription and invokes appropriate callbacks.

        Args:
            audio_path: Path to the audio file to transcribe.
        """
        try:
            text = self.transcribe(audio_path)

            if self.on_transcription_complete is not None:
                try:
                    self.on_transcription_complete(text)
                except Exception as e:
                    logger.warning(f"on_transcription_complete callback error: {e}")

        except (ModelLoadError, TranscriptionFailedError) as e:
            if self.on_transcription_error is not None:
                try:
                    self.on_transcription_error(e)
                except Exception as callback_error:
                    logger.warning(f"on_transcription_error callback error: {callback_error}")

    def unload_model(self) -> None:
        """
        Unload the Whisper model from memory.

        Releases the model resources. Useful for freeing memory when
        transcription is not needed for an extended period.

        Note:
            After calling this method, load_model() must be called again
            before transcription can be performed.
        """
        with self._model_lock:
            if self._model is not None:
                self._model = None
                logger.info("Whisper model unloaded")

    def set_model_size(self, model_size: ModelSize) -> None:
        """
        Change the model size.

        The model must be reloaded after changing the size.

        Args:
            model_size: New model size to use.

        Raises:
            ValueError: If model_size is invalid.
            RuntimeError: If called while model is loaded.
        """
        if model_size not in self.VALID_MODEL_SIZES:
            raise ValueError(
                f"Invalid model_size '{model_size}'. "
                f"Valid options: {', '.join(self.VALID_MODEL_SIZES)}"
            )

        if self._model is not None:
            raise RuntimeError(
                "Cannot change model size while model is loaded. "
                "Call unload_model() first."
            )

        self.model_size = model_size
        logger.info(f"Model size changed to '{model_size}'")

    def set_language(self, language: Optional[Language]) -> None:
        """
        Change the target language for transcription.

        Can be changed without reloading the model.

        Args:
            language: Language code ("de", "en") or None for auto-detection.

        Raises:
            ValueError: If language is invalid.
        """
        if language is not None and language not in self.VALID_LANGUAGES:
            raise ValueError(
                f"Invalid language '{language}'. "
                f"Valid options: {', '.join(self.VALID_LANGUAGES)} or None"
            )

        self.language = language
        logger.info(f"Language set to '{language or 'auto'}'")
