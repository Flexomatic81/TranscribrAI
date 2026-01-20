# TranscribrAI - Spracheingabe für Claude Code

## Übersicht

Eine Python-Anwendung mit PyQt6-GUI, die Sprache aufnimmt, lokal mit Whisper transkribiert und den Text automatisch ins Terminal eingibt.

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Sprache | Python 3.11+ |
| GUI | PyQt6 |
| Speech-to-Text | OpenAI Whisper (lokal) / faster-whisper |
| Audio-Aufnahme | sounddevice + soundfile |
| Terminal-Eingabe | pynput / ydotool (Wayland) |
| Globaler Hotkey | pynput / evdev |
| Konfiguration | JSON oder TOML |

## Architektur

```
transcribrAI/
├── main.py                 # Einstiegspunkt
├── requirements.txt        # Dependencies
├── config.json            # Benutzereinstellungen
├── src/
│   ├── __init__.py
│   ├── app.py             # Hauptanwendung
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── recorder.py    # Audio-Aufnahme
│   │   └── devices.py     # Audio-Geräte-Management
│   ├── transcription/
│   │   ├── __init__.py
│   │   └── whisper.py     # Whisper-Integration
│   ├── input/
│   │   ├── __init__.py
│   │   └── terminal.py    # Terminal-Eingabe
│   ├── hotkey/
│   │   ├── __init__.py
│   │   └── manager.py     # Globaler Hotkey-Manager
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py # Hauptfenster
│       ├── settings.py    # Einstellungs-Dialog
│       └── tray.py        # System-Tray-Icon
└── resources/
    └── icons/             # Icons für GUI
```

## Hauptkomponenten

### 1. Audio-Aufnahme (`src/audio/recorder.py`)
- Verwendet `sounddevice` für plattformübergreifende Audio-Aufnahme
- Konfigurierbare Sample-Rate (Standard: 16kHz für Whisper)
- Push-to-Talk Modus mit Start/Stop Methoden
- Speichert temporär als WAV für Whisper

### 2. Whisper-Integration (`src/transcription/whisper.py`)
- **Option A**: `openai-whisper` (Original)
- **Option B**: `faster-whisper` (empfohlen für CPU/AMD)
  - Nutzt CTranslate2, 4x schneller auf CPU
  - Weniger RAM-Verbrauch
- Modell-Auswahl: tiny, base, small, medium, large
- Sprache: Deutsch (mit Option für Auto-Detect)
- AMD GPU: ROCm optional, CPU als Fallback

### 3. Terminal-Eingabe (`src/input/terminal.py`)
- **X11**: `pynput` oder `xdotool`
- **Wayland**: `ydotool` (benötigt ydotoold Daemon)
- Automatische Erkennung des Display-Servers
- Simuliert Tastatureingabe im aktiven Fenster

### 4. Globaler Hotkey (`src/hotkey/manager.py`)
- Standard-Hotkey: `Ctrl+Shift+Space` (konfigurierbar)
- **X11**: `pynput` GlobalHotKeys
- **Wayland**: `evdev` für Keyboard-Events (benötigt Gruppe `input`)
- Toggle zwischen Aufnahme starten/stoppen

### 5. GUI (`src/gui/`)
**Hauptfenster:**
- Push-to-Talk Button (groß, zentral)
- Status-Anzeige (Idle, Recording, Transcribing, Sending)
- Letzter transkribierter Text (Vorschau)
- Lautstärke-Indikator während Aufnahme

**Einstellungen:**
- Whisper-Modell Auswahl
- Sprache (de/en/auto)
- Hotkey-Konfiguration
- Audio-Eingabegerät
- Eingabe-Verzögerung (ms)

**System-Tray:**
- Minimieren ins Tray
- Quick-Toggle für Aufnahme
- Status-Icon (Farbe je nach Zustand)

## Wayland-Kompatibilität (Fedora 43)

Fedora nutzt standardmäßig Wayland. Besondere Beachtung:

1. **Keyboard-Simulation**: `ydotool` statt `xdotool`
   - Installation: `sudo dnf install ydotool`
   - Daemon: `systemctl --user enable --now ydotool`

2. **Globale Hotkeys**: `evdev` direkt
   - Benutzer muss in Gruppe `input` sein
   - `sudo usermod -aG input $USER`

3. **Alternative**: Portal-API (komplexer)

## AMD GPU Unterstützung

**Option 1: CPU (empfohlen für Einfachheit)**
- `faster-whisper` ist auf modernen CPUs sehr schnell
- Medium-Modell: ~5-10 Sekunden pro Minute Audio

**Option 2: ROCm (optional)**
- Fedora: `sudo dnf install rocm-hip`
- PyTorch mit ROCm: `pip install torch --index-url https://download.pytorch.org/whl/rocm6.0`
- Nicht alle AMD GPUs unterstützt

## Dependencies (requirements.txt)

```
PyQt6>=6.5.0
sounddevice>=0.4.6
soundfile>=0.12.1
numpy>=1.24.0
faster-whisper>=1.0.0
pynput>=1.7.6
evdev>=1.6.0
```

## Implementierungsplan

### Phase 1: Grundgerüst
1. Projektstruktur erstellen
2. Dependencies installieren
3. Basis-GUI mit PyQt6 (Hauptfenster, Button)

### Phase 2: Audio-Aufnahme
4. Audio-Recorder Klasse implementieren
5. Audio-Gerät Auswahl
6. Push-to-Talk Logik

### Phase 3: Transkription
7. Whisper/faster-whisper Integration
8. Modell-Download und -Laden
9. Transkriptions-Worker (separater Thread)

### Phase 4: Terminal-Integration
10. Display-Server Erkennung (X11/Wayland)
11. Keyboard-Simulation implementieren
12. Text-Eingabe ins aktive Fenster

### Phase 5: Hotkeys
13. Globaler Hotkey-Manager
14. X11 und Wayland Support

### Phase 6: GUI-Verfeinerung
15. Einstellungs-Dialog
16. System-Tray Integration
17. Status-Anzeigen und Feedback

### Phase 7: Polish
18. Fehlerbehandlung
19. Konfiguration speichern/laden
20. Testen und Bugfixes

## Verifizierung

1. **Audio-Test**: Aufnahme starten, sprechen, WAV-Datei prüfen
2. **Transkriptions-Test**: Vordefinierte Audio-Datei transkribieren
3. **Terminal-Test**: Text in geöffnetes Terminal eingeben
4. **Hotkey-Test**: Globaler Hotkey von anderem Fenster aus
5. **End-to-End**: Spracheingabe → Transkription → Claude Code Terminal

## Design-Entscheidungen

- **Direktes Senden**: Text wird sofort nach Transkription gesendet (keine Editierung)
- **Manueller Start**: Kein Autostart, nur manuell starten
- **Keine Historie**: Nur aktuelle Sitzung, keine Speicherung vergangener Transkriptionen
