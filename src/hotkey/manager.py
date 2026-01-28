"""
Global hotkey management for TranscribrAI.

This module provides a unified interface for global hotkey detection that works
across both X11 and Wayland display servers. On X11, it uses pynput's GlobalHotKeys.
On Wayland, it uses evdev for direct keyboard input device access.

The HotkeyManager supports push-to-talk functionality with callbacks for both
key press and release events.
"""

import logging
import os
import threading
from typing import Callable, Optional, Set

from ..exceptions import (
    HotkeyError,
    HotkeyRegistrationError,
    EvdevPermissionError,
)

logger = logging.getLogger(__name__)

# Default hotkey combination
DEFAULT_HOTKEY = "ctrl+shift+space"


def _detect_display_server() -> str:
    """
    Detect the current display server (X11 or Wayland).

    Returns:
        String identifying the display server: 'wayland', 'x11', or 'unknown'.

    Note:
        Detection is based on environment variables. On Wayland,
        XDG_SESSION_TYPE is typically set to 'wayland', while
        WAYLAND_DISPLAY is also present.
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    wayland_display = os.environ.get("WAYLAND_DISPLAY")

    if session_type == "wayland" or wayland_display:
        return "wayland"
    elif session_type == "x11" or os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


class HotkeyManager:
    """
    Global hotkey manager with support for X11 and Wayland.

    Provides a unified interface for registering and handling global hotkeys
    across different display servers. Supports push-to-talk functionality
    with separate callbacks for key press and release events.

    On X11, uses pynput's GlobalHotKeys for hotkey detection.
    On Wayland, uses evdev to read keyboard events directly from input devices.

    Attributes:
        hotkey: The currently configured hotkey string (e.g., "ctrl+shift+space").
        on_hotkey_pressed: Callback invoked when the hotkey combination is pressed.
        on_hotkey_released: Callback invoked when the hotkey combination is released.

    Example:
        >>> manager = HotkeyManager()
        >>> manager.on_hotkey_pressed = lambda: print("Recording started")
        >>> manager.on_hotkey_released = lambda: print("Recording stopped")
        >>> manager.start()
        >>> # ... application runs ...
        >>> manager.stop()

    Note:
        On Wayland, the user must be a member of the 'input' group to access
        keyboard devices via evdev. Run: sudo usermod -aG input $USER
    """

    def __init__(self, hotkey: str = DEFAULT_HOTKEY) -> None:
        """
        Initialize the hotkey manager.

        Args:
            hotkey: The hotkey combination string in the format "modifier+modifier+key".
                   Supported modifiers: ctrl, shift, alt. Default is "ctrl+shift+space".

        Raises:
            HotkeyError: If the hotkey string format is invalid.
        """
        self._hotkey = ""
        self._display_server = _detect_display_server()
        self._running = False
        self._lock = threading.Lock()

        # Event loop thread for evdev (Wayland)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # X11: pynput listener
        self._x11_listener = None
        self._x11_pressed_keys: Set[str] = set()
        self._x11_hotkey_active = False

        # Wayland: evdev devices and state
        self._evdev_devices: list = []
        self._pressed_keys: Set[int] = set()
        self._hotkey_active = False

        # Parsed hotkey components
        self._required_modifiers: Set[str] = set()
        self._trigger_key: str = ""

        # Callbacks
        self.on_hotkey_pressed: Optional[Callable[[], None]] = None
        self.on_hotkey_released: Optional[Callable[[], None]] = None

        # Set the initial hotkey (validates format)
        self.set_hotkey(hotkey)

        logger.info(f"HotkeyManager initialized (display server: {self._display_server})")

    @property
    def hotkey(self) -> str:
        """Get the currently configured hotkey string."""
        return self._hotkey

    @property
    def is_running(self) -> bool:
        """Check if the hotkey listener is currently running."""
        return self._running

    def set_hotkey(self, hotkey_str: str) -> None:
        """
        Set the hotkey combination.

        Parses and validates the hotkey string, then updates the internal
        configuration. If the manager is currently running, the change
        takes effect immediately for evdev, or requires a restart for X11.

        Args:
            hotkey_str: The hotkey combination in format "modifier+modifier+key".
                       Examples: "ctrl+shift+space", "alt+r", "ctrl+alt+delete".
                       Modifiers: ctrl, shift, alt (case-insensitive).

        Raises:
            HotkeyError: If the hotkey string format is invalid or contains
                        unsupported keys.

        Example:
            >>> manager = HotkeyManager()
            >>> manager.set_hotkey("ctrl+alt+r")
        """
        if not hotkey_str or not isinstance(hotkey_str, str):
            raise HotkeyError("Hotkey string must be a non-empty string")

        # Parse the hotkey string
        parts = [p.strip().lower() for p in hotkey_str.split("+")]

        if len(parts) < 1:
            raise HotkeyError(f"Invalid hotkey format: {hotkey_str}")

        # Identify modifiers and trigger key
        # Note: "super" and "meta" are synonyms for the Super/Windows/Command key
        valid_modifiers = {"ctrl", "shift", "alt", "super", "meta"}
        modifiers = set()
        trigger_key = ""

        for part in parts:
            if part in valid_modifiers:
                # Normalize "meta" to "super" for consistent handling
                if part == "meta":
                    modifiers.add("super")
                else:
                    modifiers.add(part)
            elif not trigger_key:
                trigger_key = part
            else:
                raise HotkeyError(
                    f"Invalid hotkey format: multiple trigger keys found in '{hotkey_str}'"
                )

        if not trigger_key:
            raise HotkeyError(f"No trigger key found in hotkey: {hotkey_str}")

        # Validate trigger key
        if not self._validate_trigger_key(trigger_key):
            raise HotkeyError(f"Unsupported trigger key: {trigger_key}")

        self._hotkey = hotkey_str.lower()
        self._required_modifiers = modifiers
        self._trigger_key = trigger_key

        logger.info(f"Hotkey set to: {self._hotkey}")

    def _validate_trigger_key(self, key: str) -> bool:
        """
        Validate that a trigger key is supported.

        Args:
            key: The key name to validate.

        Returns:
            True if the key is supported, False otherwise.
        """
        # Common valid keys
        valid_keys = {
            "space", "enter", "return", "tab", "escape", "esc",
            "backspace", "delete", "insert", "home", "end",
            "pageup", "pagedown", "up", "down", "left", "right",
            "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
        }

        # Single letters and numbers
        if len(key) == 1 and (key.isalpha() or key.isdigit()):
            return True

        return key in valid_keys

    def start(self) -> None:
        """
        Start listening for the configured hotkey.

        Initializes the appropriate backend (pynput for X11, evdev for Wayland)
        and begins monitoring keyboard events in a background thread.

        Raises:
            HotkeyRegistrationError: If the hotkey listener cannot be started.
            EvdevPermissionError: On Wayland, if the user lacks permissions
                                 to access input devices (not in 'input' group).

        Example:
            >>> manager = HotkeyManager()
            >>> manager.on_hotkey_pressed = lambda: print("Pressed!")
            >>> manager.start()
        """
        with self._lock:
            if self._running:
                logger.warning("HotkeyManager is already running")
                return

            self._stop_event.clear()

            try:
                if self._display_server == "wayland":
                    self._start_wayland()
                else:
                    self._start_x11()

                self._running = True
                logger.info("HotkeyManager started")

            except EvdevPermissionError:
                raise
            except Exception as e:
                raise HotkeyRegistrationError(
                    f"Failed to start hotkey listener: {e}"
                ) from e

    def stop(self) -> None:
        """
        Stop listening for hotkeys.

        Stops the background thread and releases all resources associated
        with the hotkey listener. Safe to call multiple times.

        Example:
            >>> manager.stop()
        """
        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stop_event.set()

            if self._display_server == "wayland":
                self._stop_wayland()
            else:
                self._stop_x11()

            logger.info("HotkeyManager stopped")

    # =========================================================================
    # X11 Implementation (pynput)
    # =========================================================================

    def _start_x11(self) -> None:
        """
        Start the X11 hotkey listener using pynput.

        Uses pynput's keyboard listener to detect key press and release events.
        Tracks modifier state manually to support push-to-talk functionality.

        Raises:
            HotkeyRegistrationError: If pynput cannot be initialized.
        """
        try:
            from pynput import keyboard
        except ImportError as e:
            raise HotkeyRegistrationError(
                "pynput is required for X11 hotkey support. "
                "Install with: pip install pynput"
            ) from e

        self._x11_pressed_keys.clear()
        self._x11_hotkey_active = False

        def on_press(key):
            """Handle key press events."""
            key_name = self._pynput_key_to_name(key)
            if key_name:
                self._x11_pressed_keys.add(key_name)
                self._check_x11_hotkey_state()

        def on_release(key):
            """Handle key release events."""
            key_name = self._pynput_key_to_name(key)
            if key_name:
                self._x11_pressed_keys.discard(key_name)
                self._check_x11_hotkey_state()

        try:
            self._x11_listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release
            )
            self._x11_listener.start()
            logger.debug("X11 pynput listener started")
        except Exception as e:
            raise HotkeyRegistrationError(f"Failed to start X11 listener: {e}") from e

    def _stop_x11(self) -> None:
        """Stop the X11 pynput listener."""
        if self._x11_listener is not None:
            try:
                self._x11_listener.stop()
            except Exception as e:
                logger.warning(f"Error stopping X11 listener: {e}")
            finally:
                self._x11_listener = None

        self._x11_pressed_keys.clear()
        self._x11_hotkey_active = False

    def _pynput_key_to_name(self, key) -> Optional[str]:
        """
        Convert a pynput key object to a normalized key name.

        Args:
            key: A pynput Key or KeyCode object.

        Returns:
            Normalized key name string, or None if the key is not recognized.
        """
        try:
            from pynput.keyboard import Key
        except ImportError:
            return None

        # Handle special keys
        key_mapping = {
            Key.ctrl_l: "ctrl",
            Key.ctrl_r: "ctrl",
            Key.shift_l: "shift",
            Key.shift_r: "shift",
            Key.alt_l: "alt",
            Key.alt_r: "alt",
            Key.cmd_l: "super",
            Key.cmd_r: "super",
            Key.space: "space",
            Key.enter: "enter",
            Key.tab: "tab",
            Key.esc: "escape",
            Key.backspace: "backspace",
            Key.delete: "delete",
            Key.insert: "insert",
            Key.home: "home",
            Key.end: "end",
            Key.page_up: "pageup",
            Key.page_down: "pagedown",
            Key.up: "up",
            Key.down: "down",
            Key.left: "left",
            Key.right: "right",
            Key.f1: "f1",
            Key.f2: "f2",
            Key.f3: "f3",
            Key.f4: "f4",
            Key.f5: "f5",
            Key.f6: "f6",
            Key.f7: "f7",
            Key.f8: "f8",
            Key.f9: "f9",
            Key.f10: "f10",
            Key.f11: "f11",
            Key.f12: "f12",
        }

        if key in key_mapping:
            return key_mapping[key]

        # Handle character keys
        if hasattr(key, 'char') and key.char:
            return key.char.lower()

        return None

    def _check_x11_hotkey_state(self) -> None:
        """
        Check if the hotkey combination is currently active on X11.

        Compares the currently pressed keys against the required modifiers
        and trigger key. Invokes callbacks on state changes.
        """
        # Check if all required modifiers are pressed
        modifiers_pressed = all(
            mod in self._x11_pressed_keys
            for mod in self._required_modifiers
        )

        # Check if trigger key is pressed
        trigger_pressed = self._trigger_key in self._x11_pressed_keys

        hotkey_is_active = modifiers_pressed and trigger_pressed

        if hotkey_is_active and not self._x11_hotkey_active:
            # Hotkey just activated
            self._x11_hotkey_active = True
            logger.debug("Hotkey pressed (X11)")
            if self.on_hotkey_pressed:
                try:
                    self.on_hotkey_pressed()
                except Exception as e:
                    logger.error(f"Error in on_hotkey_pressed callback: {e}")

        elif not hotkey_is_active and self._x11_hotkey_active:
            # Hotkey just deactivated
            self._x11_hotkey_active = False
            logger.debug("Hotkey released (X11)")
            if self.on_hotkey_released:
                try:
                    self.on_hotkey_released()
                except Exception as e:
                    logger.error(f"Error in on_hotkey_released callback: {e}")

    # =========================================================================
    # Wayland Implementation (evdev)
    # =========================================================================

    def _start_wayland(self) -> None:
        """
        Start the Wayland hotkey listener using evdev.

        Opens keyboard input devices and starts a background thread to
        monitor key events. Requires the user to be in the 'input' group.

        Raises:
            EvdevPermissionError: If the user lacks permission to access
                                 input devices.
            HotkeyRegistrationError: If no keyboard devices are found.
        """
        try:
            import evdev
        except ImportError as e:
            raise HotkeyRegistrationError(
                "evdev is required for Wayland hotkey support. "
                "Install with: pip install evdev"
            ) from e

        # Find keyboard devices
        devices = []
        seen_devices = {}  # Track devices by name, keep best one
        try:
            for path in evdev.list_devices():
                try:
                    device = evdev.InputDevice(path)
                    capabilities = device.capabilities()

                    # Check if device has key events (EV_KEY = 1)
                    if evdev.ecodes.EV_KEY in capabilities:
                        keys = capabilities[evdev.ecodes.EV_KEY]
                        # Check for keyboard-like keys (KEY_A = 30)
                        if evdev.ecodes.KEY_A in keys or evdev.ecodes.KEY_SPACE in keys:
                            # Check if device has modifier keys (prefer devices with modifiers)
                            has_modifiers = (evdev.ecodes.KEY_LEFTCTRL in keys or
                                           evdev.ecodes.KEY_LEFTALT in keys)

                            # Handle duplicate devices - keep the one with modifiers
                            if device.name in seen_devices:
                                old_device, old_has_mods = seen_devices[device.name]
                                if has_modifiers and not old_has_mods:
                                    # Replace with better device
                                    old_device.close()
                                    seen_devices[device.name] = (device, has_modifiers)
                                    logger.debug(f"Replaced device with better version: {device.name}")
                                else:
                                    device.close()
                                    logger.debug(f"Skipping duplicate device: {device.name}")
                                continue
                            seen_devices[device.name] = (device, has_modifiers)
                            logger.debug(f"Found keyboard device: {device.name} (modifiers: {has_modifiers})")
                except PermissionError:
                    continue
                except Exception as e:
                    logger.debug(f"Error accessing device {path}: {e}")
                    continue
        except PermissionError as e:
            raise EvdevPermissionError(
                "Keine Berechtigung zum Zugriff auf Eingabegeraete. "
                "Bitte fuegen Sie Ihren Benutzer zur 'input'-Gruppe hinzu: "
                "sudo usermod -aG input $USER (Neuanmeldung erforderlich)"
            ) from e

        # Extract devices from seen_devices dict
        devices = [dev for dev, _ in seen_devices.values()]

        if not devices:
            raise HotkeyRegistrationError(
                "No keyboard devices found. Ensure you are in the 'input' group."
            )

        self._evdev_devices = devices
        self._pressed_keys.clear()
        self._hotkey_active = False

        # Start event loop thread
        self._thread = threading.Thread(
            target=self._evdev_event_loop,
            daemon=True,
            name="HotkeyManager-evdev"
        )
        self._thread.start()
        logger.debug(f"Wayland evdev listener started with {len(devices)} device(s)")

    def _stop_wayland(self) -> None:
        """Stop the Wayland evdev listener and close devices."""
        # Signal thread to stop
        self._stop_event.set()

        # Wait for thread to finish
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        # Close devices
        for device in self._evdev_devices:
            try:
                device.close()
            except Exception as e:
                logger.debug(f"Error closing device: {e}")

        self._evdev_devices.clear()
        self._pressed_keys.clear()
        self._hotkey_active = False

    def _evdev_event_loop(self) -> None:
        """
        Event loop for processing evdev keyboard events.

        Runs in a background thread and uses select() to monitor multiple
        keyboard devices simultaneously.
        """
        try:
            import evdev
            import select
        except ImportError:
            logger.error("evdev not available")
            return

        logger.debug("evdev event loop started")

        while not self._stop_event.is_set():
            try:
                # Use select to wait for events on any device
                readable = select.select(
                    self._evdev_devices, [], [], 0.1
                )[0]

                for device in readable:
                    try:
                        for event in device.read():
                            if event.type == evdev.ecodes.EV_KEY:
                                self._handle_evdev_key_event(event)
                    except Exception as e:
                        logger.debug(f"Error reading device events: {e}")
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error(f"Error in evdev event loop: {e}")
                break

        logger.debug("evdev event loop stopped")

    def _handle_evdev_key_event(self, event) -> None:
        """
        Handle an evdev key event.

        Updates the set of pressed keys and checks if the hotkey
        combination state has changed.

        Args:
            event: An evdev InputEvent with type EV_KEY.
        """
        try:
            import evdev
        except ImportError:
            return

        key_code = event.code

        # event.value: 0=release, 1=press, 2=repeat
        if event.value == 1:  # Key press
            self._pressed_keys.add(key_code)
        elif event.value == 0:  # Key release
            self._pressed_keys.discard(key_code)

        # Check hotkey state
        self._check_evdev_hotkey_state()

    def _check_evdev_hotkey_state(self) -> None:
        """
        Check if the hotkey combination is currently active via evdev.

        Maps the pressed evdev key codes to modifier/key names and compares
        against the configured hotkey combination.
        """
        try:
            import evdev.ecodes as ec
        except ImportError:
            return

        # Map modifier names to evdev key codes
        modifier_codes = {
            "ctrl": {ec.KEY_LEFTCTRL, ec.KEY_RIGHTCTRL},
            "shift": {ec.KEY_LEFTSHIFT, ec.KEY_RIGHTSHIFT},
            "alt": {ec.KEY_LEFTALT, ec.KEY_RIGHTALT},
            "super": {ec.KEY_LEFTMETA, ec.KEY_RIGHTMETA},
            "meta": {ec.KEY_LEFTMETA, ec.KEY_RIGHTMETA},
        }

        # Check if all required modifiers are pressed
        modifiers_pressed = all(
            bool(modifier_codes.get(mod, set()) & self._pressed_keys)
            for mod in self._required_modifiers
        )

        # Get the evdev key code for the trigger key
        trigger_code = self._get_evdev_key_code(self._trigger_key)
        trigger_pressed = trigger_code in self._pressed_keys if trigger_code else False

        hotkey_is_active = modifiers_pressed and trigger_pressed

        if hotkey_is_active and not self._hotkey_active:
            # Hotkey just activated
            self._hotkey_active = True
            logger.debug("Hotkey pressed (Wayland/evdev)")
            if self.on_hotkey_pressed:
                try:
                    self.on_hotkey_pressed()
                except Exception as e:
                    logger.error(f"Error in on_hotkey_pressed callback: {e}")

        elif not hotkey_is_active and self._hotkey_active:
            # Hotkey just deactivated
            self._hotkey_active = False
            logger.debug("Hotkey released (Wayland/evdev)")
            if self.on_hotkey_released:
                try:
                    self.on_hotkey_released()
                except Exception as e:
                    logger.error(f"Error in on_hotkey_released callback: {e}")

    def _get_evdev_key_code(self, key_name: str) -> Optional[int]:
        """
        Convert a key name to its evdev key code.

        Args:
            key_name: The normalized key name (e.g., "space", "a", "f1").

        Returns:
            The evdev key code, or None if not found.
        """
        try:
            import evdev.ecodes as ec
        except ImportError:
            return None

        # Mapping of key names to evdev codes
        key_mapping = {
            "space": ec.KEY_SPACE,
            "enter": ec.KEY_ENTER,
            "return": ec.KEY_ENTER,
            "tab": ec.KEY_TAB,
            "escape": ec.KEY_ESC,
            "esc": ec.KEY_ESC,
            "backspace": ec.KEY_BACKSPACE,
            "delete": ec.KEY_DELETE,
            "insert": ec.KEY_INSERT,
            "home": ec.KEY_HOME,
            "end": ec.KEY_END,
            "pageup": ec.KEY_PAGEUP,
            "pagedown": ec.KEY_PAGEDOWN,
            "up": ec.KEY_UP,
            "down": ec.KEY_DOWN,
            "left": ec.KEY_LEFT,
            "right": ec.KEY_RIGHT,
            "f1": ec.KEY_F1,
            "f2": ec.KEY_F2,
            "f3": ec.KEY_F3,
            "f4": ec.KEY_F4,
            "f5": ec.KEY_F5,
            "f6": ec.KEY_F6,
            "f7": ec.KEY_F7,
            "f8": ec.KEY_F8,
            "f9": ec.KEY_F9,
            "f10": ec.KEY_F10,
            "f11": ec.KEY_F11,
            "f12": ec.KEY_F12,
        }

        if key_name in key_mapping:
            return key_mapping[key_name]

        # Handle single letter keys (a-z)
        if len(key_name) == 1 and key_name.isalpha():
            key_attr = f"KEY_{key_name.upper()}"
            return getattr(ec, key_attr, None)

        # Handle number keys (0-9)
        if len(key_name) == 1 and key_name.isdigit():
            key_attr = f"KEY_{key_name}"
            return getattr(ec, key_attr, None)

        return None

    def __enter__(self) -> "HotkeyManager":
        """Context manager entry: start listening."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: stop listening."""
        self.stop()
