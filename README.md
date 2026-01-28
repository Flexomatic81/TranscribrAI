# TranscribrAI

Speech-to-text application with push-to-talk hotkey for Linux (X11/Wayland).

## Features

- **Push-to-Talk Recording**: Hold a hotkey to record, release to transcribe
- **Local Transcription**: Uses OpenAI Whisper (via faster-whisper) - no cloud required
- **Wayland & X11 Support**: Works on both display servers
- **Configurable Hotkeys**: Set your preferred key combination
- **System Tray**: Minimize to tray for quick access
- **German & English**: Full language support

## Installation

### Fedora/RHEL (including Bazzite, Distrobox)

```bash
# 1. Enable RPM Fusion (required for FFmpeg)
sudo dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm -y

# 2. Install system dependencies
sudo dnf install ffmpeg-devel portaudio python3-pip ydotool -y

# 3. Install TranscribrAI
pip install transcribrai
```

### Ubuntu/Debian

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install ffmpeg libavcodec-dev libavformat-dev libavdevice-dev \
    libavutil-dev libswscale-dev libswresample-dev \
    portaudio19-dev python3-pip ydotool -y

# 2. Install TranscribrAI
pip install transcribrai
```

### Arch Linux

```bash
# 1. Install system dependencies
sudo pacman -S ffmpeg portaudio python-pip ydotool

# 2. Install TranscribrAI
pip install transcribrai
```

### Wayland Setup

For global hotkeys on Wayland, add your user to the `input` group:

```bash
sudo usermod -aG input $USER
# Log out and back in
```

Start the ydotool daemon for keyboard simulation:

```bash
systemctl --user enable --now ydotool
```

## Usage

```bash
transcribrai
```

Or run directly:

```bash
python -m transcribrai
```

### Default Hotkey

- **Ctrl+Shift+Space**: Hold to record, release to transcribe

Configure in Settings or edit `~/.config/transcribrai/config.json`.

## Configuration

Configuration file: `~/.config/transcribrai/config.json`

```json
{
  "hotkey": "ctrl+shift+space",
  "audio": {
    "device_index": null
  },
  "transcription": {
    "model_size": "base",
    "language": "de"
  }
}
```

### Whisper Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 75 MB | Fastest | Lower |
| base | 150 MB | Fast | Good |
| small | 500 MB | Medium | Better |
| medium | 1.5 GB | Slow | High |
| large-v3 | 3 GB | Slowest | Highest |

## Requirements

- Python 3.11+
- Linux (X11 or Wayland)
- PipeWire or PulseAudio
- PortAudio library

## License

MIT License
