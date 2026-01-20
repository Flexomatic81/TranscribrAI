"""
Keyboard input simulation for TranscribrAI.

Provides cross-platform keyboard simulation supporting both X11 and Wayland
display servers on Linux systems.
"""

import logging
import os
import shutil
import subprocess
import time
from typing import Optional

from ..exceptions import InputSimulationError, YdotoolNotAvailableError

logger = logging.getLogger(__name__)


class TerminalInput:
    """
    Keyboard input simulator for typing text automatically.

    Provides platform-aware keyboard simulation that automatically detects
    and uses the appropriate backend:
    - X11: Uses pynput for direct keyboard simulation
    - Wayland: Uses ydotool for privileged keyboard simulation

    This class is designed for typing transcribed speech into the currently
    focused text field in any application.

    Attributes:
        delay_ms: Delay between keystrokes in milliseconds.
        is_wayland: True if running under Wayland display server.
        backend: The active backend ("x11" or "wayland").

    Example:
        >>> input_sim = TerminalInput()
        >>> input_sim.set_delay(50)  # 50ms between keystrokes
        >>> input_sim.type_text("Hello, World!")
        >>> input_sim.press_enter()

    Note:
        On Wayland, ydotool must be installed and the ydotoold daemon
        must be running. Use check_wayland_requirements() to verify.
    """

    def __init__(self, delay_ms: int = 20) -> None:
        """
        Initialize the keyboard input simulator.

        Automatically detects the display server (X11 or Wayland) and
        configures the appropriate input backend.

        Args:
            delay_ms: Delay between keystrokes in milliseconds.
                A small delay helps prevent dropped characters in some
                applications. Default is 20ms.

        Raises:
            YdotoolNotAvailableError: If running on Wayland and ydotool
                is not available or properly configured.
        """
        self.delay_ms = delay_ms
        self.is_wayland = self._detect_wayland()
        self.backend = "wayland" if self.is_wayland else "x11"

        self._keyboard = None  # Lazy-loaded pynput keyboard

        if self.is_wayland:
            # Verify ydotool is available on Wayland
            requirements = self.check_wayland_requirements()
            if not requirements["ydotool_installed"]:
                raise YdotoolNotAvailableError(
                    "ydotool ist nicht installiert. "
                    "Bitte installieren Sie es mit: sudo dnf install ydotool (Fedora) "
                    "oder sudo apt install ydotool (Ubuntu/Debian)"
                )
            if not requirements["ydotoold_running"]:
                raise YdotoolNotAvailableError(
                    "Der ydotoold-Dienst läuft nicht. "
                    "Bitte starten Sie ihn mit: systemctl --user start ydotool"
                )

        logger.info(
            f"TerminalInput initialized (backend={self.backend}, delay={delay_ms}ms)"
        )

    @staticmethod
    def _detect_wayland() -> bool:
        """
        Detect if the current session is using Wayland.

        Checks environment variables to determine the display server type.

        Returns:
            True if running under Wayland, False for X11 or unknown.
        """
        # Check XDG_SESSION_TYPE first (most reliable)
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session_type == "wayland":
            return True
        if session_type == "x11":
            return False

        # Fallback: Check for WAYLAND_DISPLAY environment variable
        if os.environ.get("WAYLAND_DISPLAY"):
            return True

        # Default to X11 if detection fails
        return False

    @staticmethod
    def check_wayland_requirements() -> dict:
        """
        Check if Wayland requirements for input simulation are met.

        Verifies that ydotool is installed and the ydotoold daemon is running,
        which are required for keyboard simulation on Wayland.

        Returns:
            A dictionary with requirement status:
            - "ydotool_installed" (bool): True if ydotool binary is found
            - "ydotoold_running" (bool): True if ydotoold daemon is active
            - "ydotool_path" (str | None): Path to ydotool binary if installed
            - "socket_exists" (bool): True if ydotool socket file exists

        Example:
            >>> reqs = TerminalInput.check_wayland_requirements()
            >>> if not reqs["ydotool_installed"]:
            ...     print("Please install ydotool")
            >>> if not reqs["ydotoold_running"]:
            ...     print("Please start ydotoold service")
        """
        result = {
            "ydotool_installed": False,
            "ydotoold_running": False,
            "ydotool_path": None,
            "socket_exists": False,
        }

        # Check if ydotool is installed
        ydotool_path = shutil.which("ydotool")
        result["ydotool_installed"] = ydotool_path is not None
        result["ydotool_path"] = ydotool_path

        # Check if ydotoold socket exists (indicates daemon is running)
        # Common socket locations
        socket_paths = [
            os.path.expanduser("~/.ydotool_socket"),
            "/tmp/.ydotool_socket",
            f"/run/user/{os.getuid()}/.ydotool_socket",
        ]

        for socket_path in socket_paths:
            if os.path.exists(socket_path):
                result["socket_exists"] = True
                break

        # Check if ydotoold process is running
        try:
            # Try to run a simple ydotool command to verify daemon connectivity
            subprocess.run(
                ["ydotool", "type", ""],
                capture_output=True,
                timeout=2,
                check=False
            )
            # If it doesn't throw an exception about daemon, it's likely running
            result["ydotoold_running"] = True
        except subprocess.TimeoutExpired:
            result["ydotoold_running"] = False
        except FileNotFoundError:
            # ydotool not installed
            result["ydotoold_running"] = False
        except Exception as e:
            logger.debug(f"ydotool check failed: {e}")
            # Fall back to socket check
            result["ydotoold_running"] = result["socket_exists"]

        return result

    def _get_keyboard(self):
        """
        Lazy-load and return the pynput keyboard controller.

        Returns:
            pynput.keyboard.Controller instance for X11 input.

        Raises:
            InputSimulationError: If pynput cannot be imported or initialized.
        """
        if self._keyboard is None:
            try:
                from pynput.keyboard import Controller
                self._keyboard = Controller()
            except ImportError as e:
                raise InputSimulationError(
                    "pynput ist nicht installiert. "
                    "Bitte installieren Sie es mit: pip install pynput"
                ) from e
            except Exception as e:
                raise InputSimulationError(
                    f"Keyboard-Controller konnte nicht initialisiert werden: {e}"
                ) from e
        return self._keyboard

    def type_text(self, text: str) -> None:
        """
        Type the given text using simulated keyboard input.

        Simulates pressing keys to type the text into the currently
        focused text field or application.

        Args:
            text: The text to type. Can include any printable characters.
                Special characters and Unicode are supported.

        Raises:
            InputSimulationError: If keyboard simulation fails.

        Example:
            >>> input_sim = TerminalInput()
            >>> input_sim.type_text("Hello, World!")
        """
        if not text:
            logger.debug("Empty text provided, nothing to type")
            return

        logger.debug(f"Typing text ({len(text)} chars) via {self.backend}")

        try:
            if self.is_wayland:
                self._type_text_wayland(text)
            else:
                self._type_text_x11(text)
        except (InputSimulationError, YdotoolNotAvailableError):
            raise
        except Exception as e:
            raise InputSimulationError(
                f"Texteingabe fehlgeschlagen: {e}"
            ) from e

    def _type_text_x11(self, text: str) -> None:
        """
        Type text using pynput on X11.

        Args:
            text: The text to type.

        Raises:
            InputSimulationError: If typing fails.
        """
        keyboard = self._get_keyboard()
        delay_seconds = self.delay_ms / 1000.0

        try:
            for char in text:
                keyboard.type(char)
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
        except Exception as e:
            raise InputSimulationError(
                f"X11-Texteingabe fehlgeschlagen: {e}"
            ) from e

    def _type_text_wayland(self, text: str) -> None:
        """
        Type text using ydotool on Wayland.

        Args:
            text: The text to type.

        Raises:
            YdotoolNotAvailableError: If ydotool execution fails.
        """
        try:
            # ydotool type with delay option
            # --key-delay sets delay between keystrokes in ms
            cmd = [
                "ydotool", "type",
                "--key-delay", str(self.delay_ms),
                "--",  # End of options
                text
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # Timeout for long texts
                check=False
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                raise YdotoolNotAvailableError(
                    f"ydotool-Ausführung fehlgeschlagen: {error_msg}"
                )

        except subprocess.TimeoutExpired:
            raise YdotoolNotAvailableError(
                "ydotool-Ausführung hat das Zeitlimit überschritten"
            )
        except FileNotFoundError:
            raise YdotoolNotAvailableError(
                "ydotool wurde nicht gefunden. Bitte installieren Sie es."
            )

    def press_enter(self) -> None:
        """
        Simulate pressing the Enter key.

        Useful for submitting text or confirming input after typing.

        Raises:
            InputSimulationError: If key simulation fails.

        Example:
            >>> input_sim = TerminalInput()
            >>> input_sim.type_text("Hello")
            >>> input_sim.press_enter()  # Submit the text
        """
        logger.debug(f"Pressing Enter via {self.backend}")

        try:
            if self.is_wayland:
                self._press_enter_wayland()
            else:
                self._press_enter_x11()
        except (InputSimulationError, YdotoolNotAvailableError):
            raise
        except Exception as e:
            raise InputSimulationError(
                f"Enter-Taste konnte nicht gedrückt werden: {e}"
            ) from e

    def _press_enter_x11(self) -> None:
        """
        Press Enter using pynput on X11.

        Raises:
            InputSimulationError: If key press fails.
        """
        from pynput.keyboard import Key

        keyboard = self._get_keyboard()

        try:
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
        except Exception as e:
            raise InputSimulationError(
                f"X11 Enter-Taste fehlgeschlagen: {e}"
            ) from e

    def _press_enter_wayland(self) -> None:
        """
        Press Enter using ydotool on Wayland.

        Raises:
            YdotoolNotAvailableError: If ydotool execution fails.
        """
        try:
            # ydotool key command uses key codes
            # 28 is the key code for Enter
            result = subprocess.run(
                ["ydotool", "key", "28:1", "28:0"],  # Press and release
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                raise YdotoolNotAvailableError(
                    f"ydotool Enter-Taste fehlgeschlagen: {error_msg}"
                )

        except subprocess.TimeoutExpired:
            raise YdotoolNotAvailableError(
                "ydotool-Ausführung hat das Zeitlimit überschritten"
            )
        except FileNotFoundError:
            raise YdotoolNotAvailableError(
                "ydotool wurde nicht gefunden"
            )

    def set_delay(self, delay_ms: int) -> None:
        """
        Set the delay between keystrokes.

        A longer delay can help prevent dropped characters in applications
        that process keyboard input slowly.

        Args:
            delay_ms: Delay in milliseconds between keystrokes.
                Must be non-negative. Common values are 10-50ms.

        Raises:
            ValueError: If delay_ms is negative.

        Example:
            >>> input_sim = TerminalInput()
            >>> input_sim.set_delay(50)  # 50ms between keys
        """
        if delay_ms < 0:
            raise ValueError("delay_ms must be non-negative")

        self.delay_ms = delay_ms
        logger.debug(f"Keystroke delay set to {delay_ms}ms")

    def get_backend_info(self) -> dict:
        """
        Get information about the current input backend.

        Returns:
            A dictionary with backend details:
            - "backend" (str): Current backend ("x11" or "wayland")
            - "is_wayland" (bool): True if using Wayland
            - "delay_ms" (int): Current keystroke delay
            - "session_type" (str): Value of XDG_SESSION_TYPE
            - "wayland_display" (str | None): Value of WAYLAND_DISPLAY

        Example:
            >>> input_sim = TerminalInput()
            >>> info = input_sim.get_backend_info()
            >>> print(f"Using {info['backend']} backend")
        """
        return {
            "backend": self.backend,
            "is_wayland": self.is_wayland,
            "delay_ms": self.delay_ms,
            "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
            "wayland_display": os.environ.get("WAYLAND_DISPLAY"),
        }
