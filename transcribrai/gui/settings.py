"""
Settings dialog for TranscribrAI.

Provides a modal dialog for configuring application settings including
transcription options, audio devices, hotkeys, and general preferences.
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..audio.devices import AudioDeviceManager

logger = logging.getLogger(__name__)


# Constants for available options
WHISPER_MODELS: dict[str, str] = {
    "tiny": "Tiny - Schnellste Verarbeitung (~1 GB RAM)",
    "base": "Base - Gute Balance (~1 GB RAM)",
    "small": "Small - Empfohlen (~2 GB RAM)",
    "medium": "Medium - Hohe Genauigkeit (~5 GB RAM)",
    "large-v3": "Large - Beste Qualitaet (~10 GB RAM)",
}

LANGUAGES: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "auto": "Auto-Erkennung",
}


class HotkeyCaptureDialog(QDialog):
    """
    Dialog for capturing a hotkey combination.

    Displays a prompt and waits for the user to press a key combination.
    The captured hotkey is returned as a string (e.g., "ctrl+shift+space").

    Attributes:
        captured_hotkey: The captured hotkey string, or None if cancelled.

    Example:
        >>> dialog = HotkeyCaptureDialog(parent)
        >>> if dialog.exec() == QDialog.DialogCode.Accepted:
        ...     hotkey = dialog.captured_hotkey
        ...     print(f"Captured: {hotkey}")
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the hotkey capture dialog.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(parent)
        self.captured_hotkey: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        self.setWindowTitle("Hotkey aufnehmen")
        self.setFixedSize(350, 150)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Instruction label
        instruction_label = QLabel(
            "Druecken Sie die gewuenschte Tastenkombination..."
        )
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(instruction_label)

        # Current key display
        self._key_display = QLabel("Warte auf Eingabe...")
        self._key_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._key_display.setStyleSheet(
            "font-size: 16px; font-weight: bold; "
            "padding: 12px; "
            "background-color: rgba(0, 0, 0, 0.05); "
            "border: 1px solid rgba(0, 0, 0, 0.15); "
            "border-radius: 6px;"
        )
        layout.addWidget(self._key_display)

        # Hint label
        hint_label = QLabel("Mindestens ein Modifier (Ctrl, Alt, Shift) erforderlich")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(hint_label)

        # Cancel button
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Set focus policy to capture key events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Accessibility
        self.setAccessibleName("Hotkey-Aufnahme-Dialog")
        self.setAccessibleDescription(
            "Druecken Sie die gewuenschte Tastenkombination fuer den globalen Hotkey"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle key press events to capture the hotkey.

        Captures the key combination when a valid key with modifiers is pressed.
        Requires at least one modifier key (Ctrl, Alt, Shift, or Meta).

        Args:
            event: The key press event.
        """
        key = event.key()
        modifiers = event.modifiers()

        # Ignore pure modifier keys
        modifier_keys = {
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
            Qt.Key.Key_AltGr,
        }
        if key in modifier_keys:
            return

        # Escape cancels the dialog
        if key == Qt.Key.Key_Escape:
            self.reject()
            return

        # Build the hotkey string
        hotkey_parts: list[str] = []

        # Check modifiers
        has_modifier = False
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            hotkey_parts.append("ctrl")
            has_modifier = True
        if modifiers & Qt.KeyboardModifier.AltModifier:
            hotkey_parts.append("alt")
            has_modifier = True
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            hotkey_parts.append("shift")
            has_modifier = True
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            hotkey_parts.append("super")
            has_modifier = True

        # Require at least one modifier
        if not has_modifier:
            self._key_display.setText("Modifier erforderlich!")
            self._key_display.setStyleSheet(
                "font-size: 16px; font-weight: bold; "
                "padding: 12px; "
                "background-color: rgba(224, 27, 36, 0.1); "
                "border: 1px solid #e01b24; "
                "border-radius: 6px; "
                "color: #e01b24;"
            )
            return

        # Get the key name
        key_sequence = QKeySequence(key)
        key_name = key_sequence.toString().lower()

        # Handle special keys
        special_keys: dict[int, str] = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Return: "return",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_F1: "f1",
            Qt.Key.Key_F2: "f2",
            Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5",
            Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7",
            Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10",
            Qt.Key.Key_F11: "f11",
            Qt.Key.Key_F12: "f12",
        }

        if key in special_keys:
            key_name = special_keys[key]

        hotkey_parts.append(key_name)

        # Combine into final hotkey string
        self.captured_hotkey = "+".join(hotkey_parts)

        # Update display with success styling
        self._key_display.setText(self.captured_hotkey)
        self._key_display.setStyleSheet(
            "font-size: 16px; font-weight: bold; "
            "padding: 12px; "
            "background-color: rgba(51, 209, 122, 0.1); "
            "border: 1px solid #33d17a; "
            "border-radius: 6px; "
            "color: #33d17a;"
        )

        logger.info(f"Hotkey captured: {self.captured_hotkey}")
        self.accept()


class SettingsDialog(QDialog):
    """
    Modal settings dialog for TranscribrAI.

    Provides grouped settings for transcription, audio, hotkey, and
    advanced options. Emits settings_changed signal when the user
    applies changes.

    Attributes:
        settings_changed: Signal emitted when settings are applied,
            carrying the new settings dictionary.

    Example:
        >>> dialog = SettingsDialog(parent)
        >>> dialog.load_settings(current_config)
        >>> dialog.settings_changed.connect(on_settings_changed)
        >>> dialog.exec()
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the settings dialog.

        Args:
            parent: The parent widget, if any.
        """
        super().__init__(parent)
        self._audio_device_manager: Optional[AudioDeviceManager] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        self.setWindowTitle("Einstellungen")
        self.setFixedSize(500, 550)
        self.setModal(True)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Create setting groups
        main_layout.addWidget(self._create_transcription_group())
        main_layout.addWidget(self._create_audio_group())
        main_layout.addWidget(self._create_hotkey_group())
        main_layout.addWidget(self._create_advanced_group())

        # Add stretch to push button box to bottom
        main_layout.addStretch()

        # Button box (GNOME style: Cancel left, OK right)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        button_box.button(QDialogButtonBox.StandardButton.Apply).setText("Uebernehmen")

        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._on_apply
        )

        main_layout.addWidget(button_box)

        # Accessibility
        self.setAccessibleName("Einstellungs-Dialog")
        self.setAccessibleDescription(
            "Konfigurieren Sie Transkription, Audio, Hotkey und erweiterte Optionen"
        )

    def _create_transcription_group(self) -> QGroupBox:
        """
        Create the transcription settings group.

        Returns:
            QGroupBox containing transcription settings.
        """
        group = QGroupBox("Transkription")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)

        # Whisper model selection
        self._model_combo = QComboBox()
        self._model_combo.setAccessibleName("Whisper-Modell")
        self._model_combo.setToolTip(
            "Groessere Modelle benoetigen mehr RAM und sind langsamer, aber genauer."
        )
        for model_id, model_name in WHISPER_MODELS.items():
            self._model_combo.addItem(model_name, model_id)
        layout.addRow("Whisper-Modell:", self._model_combo)

        # Model info label
        model_info = QLabel(
            "Groessere Modelle sind genauer, aber langsamer"
        )
        model_info.setStyleSheet("font-size: 11px; color: #666; margin-left: 4px;")
        layout.addRow("", model_info)

        # Language selection
        self._language_combo = QComboBox()
        self._language_combo.setAccessibleName("Sprache")
        self._language_combo.setToolTip(
            "Waehlen Sie die Sprache der Aufnahme oder Auto-Erkennung"
        )
        for lang_id, lang_name in LANGUAGES.items():
            self._language_combo.addItem(lang_name, lang_id)
        layout.addRow("Sprache:", self._language_combo)

        return group

    def _create_audio_group(self) -> QGroupBox:
        """
        Create the audio settings group.

        Returns:
            QGroupBox containing audio settings.
        """
        group = QGroupBox("Audio")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)

        # Input device selection with refresh button
        device_layout = QHBoxLayout()
        device_layout.setSpacing(8)

        self._device_combo = QComboBox()
        self._device_combo.setAccessibleName("Eingabegeraet")
        self._device_combo.setToolTip("Waehlen Sie das Mikrofon fuer die Aufnahme")
        self._device_combo.setMinimumWidth(280)
        self._device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self._device_combo, 1)

        refresh_button = QPushButton("Aktualisieren")
        refresh_button.setAccessibleName("Geraete aktualisieren")
        refresh_button.setToolTip("Geraete-Liste neu laden")
        refresh_button.setFixedWidth(100)
        refresh_button.clicked.connect(self._refresh_audio_devices)
        device_layout.addWidget(refresh_button)

        layout.addRow("Eingabegeraet:", device_layout)

        # Sample rate display (read-only)
        self._sample_rate_label = QLabel("-- Hz")
        self._sample_rate_label.setAccessibleName("Sample-Rate")
        self._sample_rate_label.setStyleSheet("color: #666;")
        layout.addRow("Sample-Rate:", self._sample_rate_label)

        return group

    def _create_hotkey_group(self) -> QGroupBox:
        """
        Create the hotkey settings group.

        Returns:
            QGroupBox containing hotkey settings.
        """
        group = QGroupBox("Hotkey")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)

        # Current hotkey display with change button
        hotkey_layout = QHBoxLayout()
        hotkey_layout.setSpacing(8)

        self._hotkey_edit = QLineEdit()
        self._hotkey_edit.setReadOnly(True)
        self._hotkey_edit.setAccessibleName("Aktueller Hotkey")
        self._hotkey_edit.setToolTip("Aktuell konfigurierter globaler Hotkey")
        self._hotkey_edit.setPlaceholderText("Kein Hotkey gesetzt")
        self._hotkey_edit.setMinimumWidth(200)
        hotkey_layout.addWidget(self._hotkey_edit, 1)

        change_button = QPushButton("Aendern...")
        change_button.setAccessibleName("Hotkey aendern")
        change_button.setToolTip("Neuen Hotkey aufnehmen")
        change_button.setFixedWidth(100)
        change_button.clicked.connect(self._capture_hotkey)
        hotkey_layout.addWidget(change_button)

        layout.addRow("Globaler Hotkey:", hotkey_layout)

        return group

    def _create_advanced_group(self) -> QGroupBox:
        """
        Create the advanced settings group.

        Returns:
            QGroupBox containing advanced settings.
        """
        group = QGroupBox("Erweitert")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)

        # Input delay spin box
        self._delay_spinbox = QSpinBox()
        self._delay_spinbox.setAccessibleName("Eingabe-Verzoegerung")
        self._delay_spinbox.setToolTip(
            "Wartezeit bevor Text eingegeben wird. "
            "Nuetzlich wenn Zielfenster Fokus-Verzoegerung hat."
        )
        self._delay_spinbox.setRange(0, 500)
        self._delay_spinbox.setSingleStep(10)
        self._delay_spinbox.setSuffix(" ms")
        self._delay_spinbox.setMinimumWidth(100)
        layout.addRow("Eingabe-Verzoegerung:", self._delay_spinbox)

        # Delay info label
        delay_info = QLabel("Zeit vor der Texteingabe")
        delay_info.setStyleSheet("font-size: 11px; color: #666;")
        layout.addRow("", delay_info)

        # Minimize to tray checkbox
        self._tray_checkbox = QCheckBox("In System-Tray minimieren")
        self._tray_checkbox.setAccessibleName("In System-Tray minimieren")
        self._tray_checkbox.setToolTip(
            "Minimiert die Anwendung in den System-Tray statt in die Taskleiste"
        )
        layout.addRow("", self._tray_checkbox)

        return group

    def _on_device_changed(self, index: int) -> None:
        """
        Handle device selection change to update sample rate display.

        Args:
            index: The new selected index in the device combo box.
        """
        if index < 0 or self._audio_device_manager is None:
            self._sample_rate_label.setText("-- Hz")
            return

        device_index = self._device_combo.currentData()
        if device_index is not None:
            try:
                device = self._audio_device_manager.get_device_by_index(device_index)
                sample_rate = int(device.default_sample_rate)
                self._sample_rate_label.setText(f"{sample_rate} Hz")
            except Exception as e:
                logger.warning(f"Could not get device sample rate: {e}")
                self._sample_rate_label.setText("-- Hz")

    def _refresh_audio_devices(self) -> None:
        """Refresh the list of available audio devices."""
        try:
            if self._audio_device_manager is None:
                self._audio_device_manager = AudioDeviceManager()
            else:
                self._audio_device_manager.refresh_devices()

            # Store current selection if possible
            current_device_index = self._device_combo.currentData()

            # Clear and repopulate device combo
            self._device_combo.clear()
            devices = self._audio_device_manager.get_input_devices()

            if not devices:
                self._device_combo.addItem("Kein Geraet gefunden", None)
                self._sample_rate_label.setText("-- Hz")
                return

            # Add devices to combo box
            selected_index = 0
            for i, device in enumerate(devices):
                self._device_combo.addItem(str(device), device.index)
                # Try to restore previous selection
                if device.index == current_device_index:
                    selected_index = i

            self._device_combo.setCurrentIndex(selected_index)
            logger.info(f"Refreshed audio devices, found {len(devices)} device(s)")

        except Exception as e:
            logger.error(f"Failed to refresh audio devices: {e}")
            self._device_combo.clear()
            self._device_combo.addItem("Fehler beim Laden", None)
            self._sample_rate_label.setText("-- Hz")

    def _capture_hotkey(self) -> None:
        """Open the hotkey capture dialog and update the hotkey if successful."""
        dialog = HotkeyCaptureDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.captured_hotkey:
                self._hotkey_edit.setText(dialog.captured_hotkey)
                logger.info(f"New hotkey set: {dialog.captured_hotkey}")

    def _on_apply(self) -> None:
        """Handle the Apply button click."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
        logger.info(f"Settings applied: {settings}")
        self.accept()

    def load_settings(self, config: dict) -> None:
        """
        Load settings from a configuration dictionary.

        Populates the dialog fields with values from the provided config.
        Supports the nested structure used by DEFAULT_CONFIG in app.py.
        If a value is missing, the corresponding field retains its default.

        Args:
            config: Dictionary containing setting values. Expected structure:
                {
                    "transcription": {
                        "model_size": str,  # Whisper model ID
                        "language": str,    # Language code (de, en) or None
                        "device": str       # Compute device (auto, cpu, cuda)
                    },
                    "audio": {
                        "device_index": int  # Audio device index
                    },
                    "hotkey": str,          # Hotkey string (e.g., "ctrl+shift+space")
                    "input": {
                        "delay_ms": int     # Input delay in milliseconds
                    },
                    "gui": {
                        "minimize_to_tray": bool
                    }
                }

        Example:
            >>> dialog.load_settings({
            ...     "transcription": {"model_size": "small", "language": "de"},
            ...     "audio": {"device_index": 0},
            ...     "hotkey": "ctrl+shift+space",
            ...     "input": {"delay_ms": 50},
            ...     "gui": {"minimize_to_tray": True}
            ... })
        """
        logger.debug(f"Loading settings: {config}")

        # Extract nested config sections with defaults
        transcription_config = config.get("transcription", {})
        audio_config = config.get("audio", {})
        input_config = config.get("input", {})
        gui_config = config.get("gui", {})

        # Load whisper model
        model = transcription_config.get("model_size", "small")
        model_index = self._model_combo.findData(model)
        if model_index >= 0:
            self._model_combo.setCurrentIndex(model_index)

        # Load language (None maps to "auto" in the combo)
        language = transcription_config.get("language")
        if language is None:
            language = "auto"
        language_index = self._language_combo.findData(language)
        if language_index >= 0:
            self._language_combo.setCurrentIndex(language_index)

        # Initialize audio device manager and load devices
        self._refresh_audio_devices()

        # Set device selection
        device_index = audio_config.get("device_index")
        if device_index is not None:
            combo_index = self._device_combo.findData(device_index)
            if combo_index >= 0:
                self._device_combo.setCurrentIndex(combo_index)

        # Load hotkey (top-level key)
        hotkey = config.get("hotkey", "")
        self._hotkey_edit.setText(hotkey)

        # Load input delay
        input_delay = input_config.get("delay_ms", 50)
        self._delay_spinbox.setValue(input_delay)

        # Load tray setting
        minimize_to_tray = gui_config.get("minimize_to_tray", True)
        self._tray_checkbox.setChecked(minimize_to_tray)

    def get_settings(self) -> dict:
        """
        Get the current settings from the dialog.

        Returns settings in the same nested structure as DEFAULT_CONFIG in app.py
        for consistent configuration handling.

        Returns:
            Dictionary containing all current setting values in nested structure:
                {
                    "transcription": {
                        "model_size": str,
                        "language": Optional[str],
                        "device": str
                    },
                    "audio": {
                        "device_index": Optional[int]
                    },
                    "hotkey": str,
                    "input": {
                        "delay_ms": int
                    },
                    "gui": {
                        "minimize_to_tray": bool
                    }
                }

        Example:
            >>> settings = dialog.get_settings()
            >>> print(settings)
            {
                "transcription": {"model_size": "small", "language": None, "device": "auto"},
                "audio": {"device_index": 0},
                "hotkey": "ctrl+shift+space",
                "input": {"delay_ms": 50},
                "gui": {"minimize_to_tray": True}
            }
        """
        # Map "auto" language selection to None for Whisper auto-detection
        language = self._language_combo.currentData()
        if language == "auto":
            language = None

        return {
            "transcription": {
                "model_size": self._model_combo.currentData(),
                "language": language,
                "device": "auto"
            },
            "audio": {
                "device_index": self._device_combo.currentData()
            },
            "hotkey": self._hotkey_edit.text(),
            "input": {
                "delay_ms": self._delay_spinbox.value()
            },
            "gui": {
                "minimize_to_tray": self._tray_checkbox.isChecked()
            }
        }
