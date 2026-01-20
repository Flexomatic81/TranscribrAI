#!/usr/bin/env python3
"""
TranscribrAI - Speech-to-Text Application for Claude Code

A PyQt6-based voice input application that captures speech, transcribes it locally
using Whisper, and automatically inputs the text into the active terminal window.

Usage:
    python main.py

Requirements:
    - Python 3.11+
    - PyQt6
    - faster-whisper
    - sounddevice
    - For Wayland: ydotool daemon running, user in 'input' group
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce noise from external libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("numba").setLevel(logging.WARNING)
logging.getLogger("faster_whisper").setLevel(logging.INFO)

# Set DEBUG for audio module when troubleshooting
# logging.getLogger("src.audio").setLevel(logging.DEBUG)


def main() -> int:
    """
    Application entry point.

    Initializes the Qt application and launches the main window.

    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt

        # Enable High DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        qt_app = QApplication(sys.argv)
        qt_app.setApplicationName("TranscribrAI")
        qt_app.setApplicationVersion("0.1.0")
        qt_app.setOrganizationName("TranscribrAI")

        # Import and create application controller and main window
        from src.app import TranscribrApp
        from src.gui.main_window import MainWindow

        # Create the application controller
        transcribr_app = TranscribrApp()

        # Create main window with application controller
        window = MainWindow(app=transcribr_app)
        window.show()

        # Start the application (initializes components and hotkey listener)
        transcribr_app.start()

        logger.info("TranscribrAI started successfully")

        # Run the Qt event loop
        exit_code = qt_app.exec()

        # Ensure clean shutdown
        transcribr_app.stop()

        return exit_code

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please install dependencies: pip install -r requirements.txt")
        return 1
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
