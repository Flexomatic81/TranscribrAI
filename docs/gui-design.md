# TranscribrAI - GUI Design Dokumentation

Version: 1.0
Plattform: Linux (GNOME/KDE, Wayland/X11)
Framework: PyQt6
Letzte Aktualisierung: 2026-01-19

---

## Inhaltsverzeichnis

1. [Design-Philosophie](#design-philosophie)
2. [Hauptfenster-Design](#hauptfenster-design)
3. [Farbschema](#farbschema)
4. [Einstellungs-Dialog](#einstellungs-dialog)
5. [System-Tray-Integration](#system-tray-integration)
6. [PyQt6-Implementierung](#pyqt6-implementierung)
7. [Barrierefreiheit](#barrierefreiheit)
8. [GNOME/KDE-Konformität](#gnomekde-konformität)
9. [Responsive Design](#responsive-design)
10. [Status-Feedback](#status-feedback)

---

## Design-Philosophie

### Leitprinzipien

**Klarheit über Komplexität**
Die Anwendung hat einen einzigen Hauptzweck: Push-to-Talk-Sprachaufnahme. Die UI muss sofort verständlich sein.

**Linux-Native Experience**
Volle Integration in GNOME/KDE mit nativen Themes, korrekter Header Bar und freedesktop.org-Standards.

**Fokus auf Statusklarheit**
Der Benutzer muss jederzeit wissen, was die Anwendung gerade tut (Idle, Recording, Transcribing, Sending).

**Tastatur-First**
Globaler Hotkey und vollständige Tastaturnavigation für effizientes Arbeiten.

**Accessibility by Default**
Screenreader-Unterstützung, ausreichende Kontraste und klare Beschriftungen von Anfang an.

---

## Hauptfenster-Design

### Layout-Wireframe

```
┌─────────────────────────────────────────────┐
│ TranscribrAI                    [⚙] [─] [×] │  ← Header Bar (32px)
├─────────────────────────────────────────────┤
│                                             │
│          ┌───────────────────┐              │
│          │                   │              │
│          │    [  MICRO  ]    │              │  ← Push-to-Talk Button
│          │      160×160      │              │     (160×160px, zentral)
│          │                   │              │
│          └───────────────────┘              │
│                                             │
│    Status: Idle                             │  ← Status-Text (16px)
│                                             │
│    ╔═══════════════════════════════╗        │  ← Lautstärke-Indikator
│    ║████████░░░░░░░░░░░░░░░░░░░░░░░║        │     (nur bei Recording)
│    ╚═══════════════════════════════╝        │
│                                             │
│    ┌─ Letzte Transkription ────────────┐    │  ← Vorschau-Bereich
│    │                                   │    │     (min. 80px hoch)
│    │ "Hier erscheint der               │    │
│    │  transkribierte Text..."          │    │
│    │                                   │    │
│    └───────────────────────────────────┘    │
│                                             │
└─────────────────────────────────────────────┘

Mindestgröße: 480×520px
Bevorzugte Größe: 520×580px
```

### Komponenten-Spezifikation

#### 1. Header Bar (GNOME-Style)

**Höhe:** 32px
**Hintergrund:** System-Theme
**Elemente:**
- Links: App-Name "TranscribrAI" (Bold, 11pt)
- Rechts: Einstellungen-Button [⚙], Minimieren [─], Schließen [×]

**Implementation:**
```python
# Für GNOME-Umgebungen: Native Header Bar
self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
```

#### 2. Push-to-Talk Button

**Größe:** 160×160px
**Form:** Kreisförmig (border-radius: 50%)
**Position:** Horizontal und vertikal zentriert im oberen Bereich
**Icon:** Mikrofon-Symbol (48×48px)
**Hover-Effekt:** 5% Aufhellung
**Pressed-Effekt:** 10% Abdunkelung + 2px Schatten nach innen

**Zustandsfarben:**
- Idle: `#3584e4` (GNOME Blue)
- Recording: `#e01b24` (GNOME Red) + pulsierender Ring-Effekt
- Transcribing: `#f6d32d` (GNOME Yellow) + Spinner-Overlay
- Sending: `#33d17a` (GNOME Green) + kurzes Aufleuchten

**Zugänglichkeit:**
```python
button.setAccessibleName("Push-to-Talk Button")
button.setAccessibleDescription("Drücken um Aufnahme zu starten")
button.setToolTip("Klicken oder Ctrl+Shift+Space drücken")
```

#### 3. Status-Anzeige

**Position:** Direkt unter dem Button (16px Abstand)
**Schriftart:** System-Default, 16px
**Ausrichtung:** Horizontal zentriert

**Status-Texte:**
```
Idle         → "Bereit zur Aufnahme"
Recording    → "● Aufnahme läuft..." (roter Punkt pulsiert)
Transcribing → "⟳ Transkribiere..." (drehendes Symbol)
Sending      → "✓ Sende Text..." (Haken)
Error        → "⚠ Fehler: [Details]" (orange)
```

#### 4. Lautstärke-Indikator

**Position:** Unter Status-Text (12px Abstand)
**Höhe:** 24px
**Breite:** 90% der Fensterbreite, max. 400px
**Sichtbarkeit:** Nur während Recording-Status

**Design:**
- Hintergrund: `rgba(0, 0, 0, 0.1)`
- Border: 1px solid `rgba(0, 0, 0, 0.2)`
- Border-Radius: 4px
- Fortschrittsbalken: Gradient von grün (leise) zu gelb (mittel) zu rot (laut)

**Animation:** Smooth Update (60 FPS), Decay-Time 100ms

#### 5. Transkriptions-Vorschau

**Position:** Unterer Bereich (16px Abstand zu allen Seiten)
**Höhe:** Flexibel, min. 80px, max. 200px
**Rahmen:** 1px solid `rgba(0, 0, 0, 0.15)`, border-radius: 6px
**Padding:** 12px
**Schriftart:** Monospace, 12px
**Scrollbar:** Nur vertikal, bei Bedarf

**Header:** "Letzte Transkription" (Grau, 10px, Semi-Bold)
**Text-Farbe:** System-Foreground
**Hintergrund:** `rgba(0, 0, 0, 0.03)` in Light Mode

**Platzhalter-Text:**
```
"Keine Aufnahme vorhanden.
Drücken Sie den Button oder Ctrl+Shift+Space."
```

---

## Farbschema

### GNOME-Palette (Primär)

Folgt den [GNOME HIG Color Guidelines](https://developer.gnome.org/hig/reference/palette.html).

#### Status-Farben

| Status         | Hex       | RGB            | Verwendung                          |
|----------------|-----------|----------------|-------------------------------------|
| Blue (Idle)    | `#3584e4` | 53, 132, 228   | Button im Idle-Zustand              |
| Red (Record)   | `#e01b24` | 224, 27, 36    | Button während Aufnahme             |
| Yellow (Trans) | `#f6d32d` | 246, 211, 45   | Button während Transkription        |
| Green (Send)   | `#33d17a` | 51, 209, 122   | Button beim Senden                  |
| Orange (Warn)  | `#ff7800` | 255, 120, 0    | Warnungen                           |
| Dark (Text)    | `#2e3436` | 46, 52, 54     | Primärer Text (Light Theme)         |
| Light (Text)   | `#f6f5f4` | 246, 245, 244  | Primärer Text (Dark Theme)          |

#### UI-Elemente

| Element               | Light Mode         | Dark Mode          |
|-----------------------|--------------------|--------------------|
| Hintergrund           | `#ffffff`          | `#242424`          |
| Sekundärer Hintergrund| `#f6f5f4`          | `#303030`          |
| Border                | `rgba(0,0,0,0.15)` | `rgba(255,255,255,0.15)` |
| Disabled Text         | `#949494`          | `#6e6e6e`          |
| Focus Ring            | `#3584e4` (2px)    | `#3584e4` (2px)    |

### KDE-Anpassung

Wenn KDE-Plasma erkannt wird, nutze `QPalette` für automatische Theme-Integration:

```python
from PyQt6.QtGui import QPalette

# Systemfarben verwenden
palette = QApplication.palette()
bg_color = palette.color(QPalette.ColorRole.Base)
fg_color = palette.color(QPalette.ColorRole.Text)
```

### Kontrast-Anforderungen

Alle Text-Hintergrund-Kombinationen erfüllen **WCAG 2.1 Level AA**:
- Normaler Text: Kontrast-Verhältnis ≥ 4.5:1
- Großer Text (≥18pt): Kontrast-Verhältnis ≥ 3:1
- UI-Komponenten: Kontrast-Verhältnis ≥ 3:1

---

## Einstellungs-Dialog

### Layout

```
┌─────────────────────────────────────────────────────────┐
│ Einstellungen                              [×]           │
├─────────────────────────────────────────────────────────┤
│  ┌─ Transkription ──────────────────────────────────┐   │
│  │                                                   │   │
│  │  Whisper-Modell:    [Dropdown ▼]                 │   │
│  │                     ⓘ Größere Modelle sind       │   │
│  │                       genauer, aber langsamer     │   │
│  │                                                   │   │
│  │  Sprache:           ( ) Deutsch                  │   │
│  │                     ( ) Englisch                 │   │
│  │                     (●) Automatisch erkennen     │   │
│  │                                                   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─ Audio ──────────────────────────────────────────┐   │
│  │                                                   │   │
│  │  Eingabegerät:      [Dropdown ▼]                 │   │
│  │                     [Aktualisieren]              │   │
│  │                                                   │   │
│  │  Sample-Rate:       16000 Hz (empfohlen)         │   │
│  │                                                   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─ Hotkey ─────────────────────────────────────────┐   │
│  │                                                   │   │
│  │  Globaler Hotkey:   [Ctrl+Shift+Space ▼]         │   │
│  │                     [Aufnehmen...]               │   │
│  │                                                   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─ Eingabe ────────────────────────────────────────┐   │
│  │                                                   │   │
│  │  Verzögerung:       [50] ms                      │   │
│  │                     (Zeit vor der Texteingabe)   │   │
│  │                                                   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─ Allgemein ──────────────────────────────────────┐   │
│  │                                                   │   │
│  │  ☑ In System-Tray minimieren                     │   │
│  │  ☐ Minimiert starten                             │   │
│  │                                                   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│                           [Abbrechen]  [Übernehmen]      │
└─────────────────────────────────────────────────────────┘

Größe: 600×700px (fest)
```

### Komponenten-Details

#### Whisper-Modell Dropdown

**Optionen:**
```
Tiny    - Schnellste Verarbeitung (~1 GB RAM)
Base    - Gute Balance (~1 GB RAM)
Small   - Empfohlen (~2 GB RAM) [DEFAULT]
Medium  - Hohe Genauigkeit (~5 GB RAM)
Large   - Beste Qualität (~10 GB RAM)
```

**Tooltip:** "Größere Modelle benötigen mehr RAM und sind langsamer, aber genauer."

**Hinweis-Icon:** Info-Icon mit erklärendem Tooltip bei Hover

#### Sprache-Auswahl

**Radio Buttons:**
- `de` - Deutsch
- `en` - Englisch
- `auto` - Automatisch erkennen (Standard)

**Verhalten:** Bei "Automatisch" verlängert sich die Verarbeitungszeit um ~10%.

#### Audio-Eingabegerät

**Dropdown:** Listet alle verfügbaren Mikrofone via `sounddevice.query_devices()`

**Format:**
```
Standard-Mikrofon (PulseAudio)
USB-Mikrofon (hw:2,0)
Webcam-Mikrofon (hw:0,0)
```

**Aktualisieren-Button:** Refresh-Icon, scannt Geräte neu

#### Hotkey-Konfiguration

**Standard:** `Ctrl+Shift+Space`

**Aufnehmen-Button:** Startet Listening-Modus (3 Sekunden), zeigt "Drücken Sie die gewünschte Tastenkombination..."

**Validierung:**
- Mindestens ein Modifier (Ctrl, Alt, Shift, Super)
- Keine Konflikte mit System-Hotkeys
- Warnung bei problematischen Kombinationen

**Wayland-Hinweis:**
Bei Wayland-Session: "Globale Hotkeys benötigen Mitgliedschaft in der Gruppe 'input'. Siehe Dokumentation."

#### Eingabe-Verzögerung

**Typ:** SpinBox
**Range:** 0-1000 ms
**Standard:** 50 ms
**Schritte:** 10 ms

**Erklärung:** "Wartezeit bevor Text eingegeben wird. Nützlich wenn Zielfenster Fokus-Verzögerung hat."

#### Buttons

**Layout:** Rechtsbündig am unteren Rand
**Abstand:** 8px zwischen Buttons, 16px zu Rändern

**Abbrechen:**
- Verwirft Änderungen
- Shortcut: `Esc`

**Übernehmen:**
- Speichert Änderungen in `config.json`
- Validation vor dem Speichern
- Shortcut: `Ctrl+Return`

### Dialog-Verhalten

**Öffnen:**
- Via Einstellungs-Button in Header Bar
- Via System-Tray → "Einstellungen"
- Shortcut: `Ctrl+,`

**Modal:** Ja, blockiert Hauptfenster

**Speichern:**
```python
# Automatisches Speichern bei "Übernehmen"
config.save_to_file("/home/user/.config/transcribrai/config.json")
```

**Fehlerbehandlung:**
- Bei ungültigem Hotkey: Inline-Warnung unter dem Feld
- Bei Modell-Download-Fehler: InfoBar am oberen Rand
- Bei Geräte-Fehler: Tooltip mit Fehlerdetails

---

## System-Tray-Integration

### Icon-Design

**Format:** SVG für scharfe Darstellung bei beliebiger Größe
**Größen:** 16×16, 22×22, 24×24, 32×32, 48×48 px
**Stil:** Monochrome Icons, automatische Theme-Anpassung

#### Icon-Zustände

| Status       | Icon-Design                           | Farbe         |
|--------------|---------------------------------------|---------------|
| Idle         | Mikrofon (outline)                    | Theme-Default |
| Recording    | Mikrofon (filled) + roter Punkt       | Rot           |
| Transcribing | Mikrofon + Zahnrad (klein)            | Gelb          |
| Sending      | Mikrofon + Pfeil nach rechts          | Grün          |
| Error        | Mikrofon + Warnsymbol                 | Orange        |

**Icon-Pfad:** `/resources/icons/tray/`

```
tray/
├── idle.svg
├── recording.svg
├── transcribing.svg
├── sending.svg
└── error.svg
```

### Kontextmenü

```
┌──────────────────────────┐
│ ● Aufnahme starten       │  ← Toggle (je nach Status)
├──────────────────────────┤
│ Fenster anzeigen         │
│ Einstellungen            │
├──────────────────────────┤
│ Status: Bereit           │  ← Info-Zeile (deaktiviert)
├──────────────────────────┤
│ Beenden                  │
└──────────────────────────┘
```

**Verhalten:**

1. **Aufnahme starten/stoppen**
   - Gleiche Funktion wie Hauptbutton
   - Text wechselt: "● Aufnahme starten" ↔ "■ Aufnahme stoppen"
   - Bold bei Recording

2. **Fenster anzeigen**
   - Stellt Hauptfenster wieder her (wenn minimiert)
   - Bringt Fenster in Vordergrund
   - Default-Action bei Doppelklick auf Tray-Icon

3. **Einstellungen**
   - Öffnet Einstellungs-Dialog
   - Stellt Hauptfenster wieder her, falls minimiert

4. **Status**
   - Read-only Zeile
   - Zeigt aktuellen Status (Idle, Recording, etc.)
   - Ausgegraut

5. **Beenden**
   - Bestätigungs-Dialog wenn Recording läuft
   - Bereinigt temp-Dateien
   - Beendet ydotool-Verbindungen

### Notifications

**Tool:** Nutze freedesktop.org Notifications via `QSystemTrayIcon.showMessage()`

**Anlässe:**
```python
# Erfolgreiche Transkription
tray.showMessage(
    "Transkription abgeschlossen",
    "Text wurde eingegeben: 'Hallo Welt...'",
    QSystemTrayIcon.MessageIcon.Information,
    3000  # 3 Sekunden
)

# Fehler
tray.showMessage(
    "Transkriptionsfehler",
    "Whisper-Modell konnte nicht geladen werden",
    QSystemTrayIcon.MessageIcon.Critical,
    5000
)
```

**Einstellungen:** Optional deaktivierbar in Settings

---

## PyQt6-Implementierung

### Empfohlene Widget-Struktur

#### Hauptfenster

```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPalette

class MainWindow(QMainWindow):
    """TranscribrAI Hauptfenster"""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_signals()

    def setup_ui(self):
        """UI-Komponenten initialisieren"""

        # Fenster-Eigenschaften
        self.setWindowTitle("TranscribrAI")
        self.setMinimumSize(480, 520)
        self.resize(520, 580)

        # Zentrales Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Haupt-Layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Push-to-Talk Button
        self.ptt_button = QPushButton()
        self.ptt_button.setFixedSize(160, 160)
        self.ptt_button.setIcon(QIcon("resources/icons/microphone.svg"))
        self.ptt_button.setIconSize(QSize(48, 48))
        self.ptt_button.setAccessibleName("Push-to-Talk Button")
        self.ptt_button.setToolTip("Klicken oder Ctrl+Shift+Space drücken")

        # Button zentrieren
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ptt_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Status-Label
        self.status_label = QLabel("Bereit zur Aufnahme")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px;")
        main_layout.addWidget(self.status_label)

        # Lautstärke-Indikator
        self.volume_bar = QProgressBar()
        self.volume_bar.setMaximum(100)
        self.volume_bar.setTextVisible(False)
        self.volume_bar.setFixedHeight(24)
        self.volume_bar.setVisible(False)  # Initially hidden
        main_layout.addWidget(self.volume_bar)

        # Transkriptions-Vorschau
        preview_group = QGroupBox("Letzte Transkription")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(80)
        self.preview_text.setMaximumHeight(200)
        self.preview_text.setPlaceholderText(
            "Keine Aufnahme vorhanden.\n"
            "Drücken Sie den Button oder Ctrl+Shift+Space."
        )
        preview_layout.addWidget(self.preview_text)

        main_layout.addWidget(preview_group)
        main_layout.addStretch()
```

### QSS-Stylesheet-Beispiele

#### Push-to-Talk Button - Idle State

```css
QPushButton {
    background-color: #3584e4;
    border: none;
    border-radius: 80px;
    color: white;
    font-size: 14px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #4a90e8;
}

QPushButton:pressed {
    background-color: #2a6ac7;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

QPushButton:focus {
    outline: 2px solid #3584e4;
    outline-offset: 4px;
}
```

#### Push-to-Talk Button - Recording State

```css
QPushButton#recording {
    background-color: #e01b24;
    animation: pulse 1.5s infinite;
}

/* Pulsierender Effekt (via QPropertyAnimation in Code) */
@keyframes pulse {
    0%, 100% { background-color: #e01b24; }
    50% { background-color: #f03a46; }
}

QPushButton#recording:hover {
    background-color: #f03a46;
}
```

#### Lautstärke-Indikator

```css
QProgressBar {
    border: 1px solid rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    background-color: rgba(0, 0, 0, 0.1);
    text-align: center;
}

QProgressBar::chunk {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #33d17a,
        stop: 0.5 #f6d32d,
        stop: 1 #e01b24
    );
    border-radius: 3px;
}
```

#### Transkriptions-Vorschau

```css
QTextEdit {
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 6px;
    padding: 12px;
    background-color: rgba(0, 0, 0, 0.03);
    font-family: monospace;
    font-size: 12px;
}

QTextEdit:focus {
    border: 1px solid #3584e4;
    outline: none;
}

/* Dark Theme Variante */
QTextEdit[darkTheme="true"] {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #f6f5f4;
}
```

#### Einstellungs-Dialog GroupBoxes

```css
QGroupBox {
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 500;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: transparent;
}
```

### Signal/Slot-Patterns

#### State Management

```python
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

class AppState(Enum):
    """Anwendungs-Zustände"""
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    SENDING = "sending"
    ERROR = "error"

class StateManager(QObject):
    """Zentrales State-Management"""

    state_changed = pyqtSignal(AppState)

    def __init__(self):
        super().__init__()
        self._state = AppState.IDLE

    @property
    def state(self) -> AppState:
        return self._state

    @state.setter
    def state(self, new_state: AppState):
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(new_state)

# Verwendung im MainWindow
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state_manager = StateManager()
        self.state_manager.state_changed.connect(self.on_state_changed)

    def on_state_changed(self, state: AppState):
        """UI basierend auf neuem State aktualisieren"""

        # Button-Farbe ändern
        colors = {
            AppState.IDLE: "#3584e4",
            AppState.RECORDING: "#e01b24",
            AppState.TRANSCRIBING: "#f6d32d",
            AppState.SENDING: "#33d17a",
            AppState.ERROR: "#ff7800"
        }
        self.ptt_button.setStyleSheet(
            f"background-color: {colors[state]};"
        )

        # Status-Text ändern
        status_texts = {
            AppState.IDLE: "Bereit zur Aufnahme",
            AppState.RECORDING: "● Aufnahme läuft...",
            AppState.TRANSCRIBING: "⟳ Transkribiere...",
            AppState.SENDING: "✓ Sende Text...",
            AppState.ERROR: "⚠ Fehler aufgetreten"
        }
        self.status_label.setText(status_texts[state])

        # Volume Bar Sichtbarkeit
        self.volume_bar.setVisible(state == AppState.RECORDING)

        # Tray-Icon aktualisieren
        self.update_tray_icon(state)
```

#### Audio-Level-Update (Threading)

```python
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

class AudioRecorder(QThread):
    """Audio-Aufnahme in separatem Thread"""

    volume_updated = pyqtSignal(int)  # 0-100
    recording_finished = pyqtSignal(str)  # Dateipfad

    def run(self):
        """Aufnahme-Schleife"""
        while self.is_recording:
            # Audio-Chunk aufnehmen
            audio_chunk = self.stream.read(self.chunk_size)

            # Lautstärke berechnen
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
            volume = int(np.abs(audio_data).mean() / 327.67)  # Normalisiert auf 0-100

            # Signal emittieren
            self.volume_updated.emit(volume)

# Im MainWindow verbinden
self.recorder = AudioRecorder()
self.recorder.volume_updated.connect(self.volume_bar.setValue)
self.recorder.recording_finished.connect(self.on_recording_done)
```

#### Whisper-Transkription (Worker)

```python
from PyQt6.QtCore import QRunnable, pyqtSlot, QThreadPool

class TranscriptionWorker(QRunnable):
    """Whisper-Transkription als Worker"""

    class Signals(QObject):
        finished = pyqtSignal(str)  # Transkribierter Text
        error = pyqtSignal(str)     # Fehlermeldung
        progress = pyqtSignal(int)  # 0-100

    def __init__(self, audio_file: str, model):
        super().__init__()
        self.audio_file = audio_file
        self.model = model
        self.signals = self.Signals()

    @pyqtSlot()
    def run(self):
        """Transkription durchführen"""
        try:
            # Whisper-Modell aufrufen
            segments, info = self.model.transcribe(
                self.audio_file,
                language="de",
                beam_size=5
            )

            # Text zusammenfügen
            text = " ".join([seg.text for seg in segments])

            self.signals.finished.emit(text.strip())

        except Exception as e:
            self.signals.error.emit(str(e))

# Verwendung
worker = TranscriptionWorker(audio_file, self.whisper_model)
worker.signals.finished.connect(self.on_transcription_done)
worker.signals.error.connect(self.on_transcription_error)

QThreadPool.globalInstance().start(worker)
```

---

## Barrierefreiheit

### Tastaturnavigation

#### Tab-Reihenfolge (Hauptfenster)

1. Push-to-Talk Button
2. Transkriptions-Vorschau (read-only, skip mit Tab)
3. Einstellungs-Button (Header Bar)

```python
# Tab-Order explizit setzen
self.setTabOrder(self.ptt_button, self.settings_button)
```

#### Tastatur-Shortcuts

| Shortcut         | Aktion                        | Scope   |
|------------------|-------------------------------|---------|
| `Ctrl+Shift+Space` | Toggle Aufnahme             | Global  |
| `Space`          | Button aktivieren (bei Fokus) | Lokal   |
| `Ctrl+,`         | Einstellungen öffnen          | Lokal   |
| `Esc`            | Dialog schließen              | Dialog  |
| `Ctrl+Q`         | Anwendung beenden             | Lokal   |
| `F1`             | Hilfe anzeigen                | Lokal   |

```python
# Shortcuts definieren
from PyQt6.QtGui import QShortcut, QKeySequence

shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
shortcut.activated.connect(self.open_settings)
```

### Screen Reader-Unterstützung

#### AccessibleName und AccessibleDescription

```python
# Push-to-Talk Button
self.ptt_button.setAccessibleName("Push-to-Talk Button")
self.ptt_button.setAccessibleDescription(
    "Drücken um Sprachaufnahme zu starten. "
    "Nochmals drücken um zu stoppen."
)

# Status-Label
self.status_label.setAccessibleName("Status-Anzeige")

# Lautstärke-Indikator
self.volume_bar.setAccessibleName("Aufnahme-Lautstärke")
self.volume_bar.setAccessibleDescription(
    "Zeigt die aktuelle Lautstärke der Aufnahme an"
)

# Transkriptions-Vorschau
self.preview_text.setAccessibleName("Transkriptions-Vorschau")
self.preview_text.setAccessibleDescription(
    "Zeigt den zuletzt transkribierten Text an"
)
```

#### Live-Updates für Screen Reader

```python
from PyQt6.QtCore import QAccessible

def update_status(self, new_status: str):
    """Status aktualisieren mit Screen Reader-Notification"""
    self.status_label.setText(new_status)

    # Screen Reader benachrichtigen
    QAccessible.updateAccessibility(
        QAccessibleEvent(
            self.status_label,
            QAccessible.Event.NameChanged
        )
    )
```

### Visuelle Anforderungen

#### Fokus-Indikatoren

```css
/* Sichtbarer Fokus-Ring (2px, GNOME Blue) */
*:focus {
    outline: 2px solid #3584e4;
    outline-offset: 2px;
}

/* Alternativ: Box-Shadow für runde Elemente */
QPushButton:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(53, 132, 228, 0.5);
}
```

#### Kontrast-Prüfung

Alle Text-Hintergrund-Kombinationen erfüllen WCAG AA:

```python
def check_contrast_ratio(fg_color, bg_color) -> float:
    """
    Berechnet Kontrast-Verhältnis nach WCAG 2.1

    Returns:
        float: Kontrast-Verhältnis (z.B. 4.5 für AA Normal Text)
    """
    # Relative Luminanz berechnen
    def luminance(color):
        r, g, b = color.red(), color.green(), color.blue()
        r, g, b = r/255, g/255, b/255

        def adjust(c):
            return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4

        return 0.2126*adjust(r) + 0.7152*adjust(g) + 0.0722*adjust(b)

    l1 = luminance(fg_color)
    l2 = luminance(bg_color)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)
```

#### Textgröße und Skalierung

```python
# High-DPI-Skalierung aktivieren
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

# Font-Größen in pt (nicht px) für korrekte Skalierung
font = QFont()
font.setPointSize(12)  # Skaliert automatisch
self.preview_text.setFont(font)
```

### Farbblindheit-Unterstützung

Verlasse dich nicht nur auf Farbe zur Informationsvermittlung:

- **Idle:** Blau + Text "Bereit"
- **Recording:** Rot + Pulsierender Punkt "●" + Text "Aufnahme läuft"
- **Transcribing:** Gelb + Spinner "⟳" + Text "Transkribiere"
- **Sending:** Grün + Haken "✓" + Text "Sende"

---

## GNOME/KDE-Konformität

### GNOME Human Interface Guidelines

#### Header Bar-Integration

```python
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # GNOME: Client-Side Decorations (CSD)
        if self.is_gnome_session():
            self.setup_gnome_headerbar()
        else:
            self.setup_standard_menubar()

    def is_gnome_session(self) -> bool:
        """Prüft ob GNOME-Session läuft"""
        import os
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
        return 'GNOME' in desktop.upper()

    def setup_gnome_headerbar(self):
        """GNOME-Style Header Bar erstellen"""
        from PyQt6.QtWidgets import QToolBar, QLabel, QToolButton
        from PyQt6.QtGui import QIcon

        # Toolbar als Header Bar
        headerbar = QToolBar("Header Bar")
        headerbar.setMovable(False)
        headerbar.setFloatable(False)
        headerbar.setFixedHeight(32)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, headerbar)

        # App-Titel
        title = QLabel("TranscribrAI")
        title.setStyleSheet("font-weight: bold; padding-left: 8px;")
        headerbar.addWidget(title)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        headerbar.addWidget(spacer)

        # Einstellungs-Button
        settings_btn = QToolButton()
        settings_btn.setIcon(QIcon.fromTheme("preferences-system"))
        settings_btn.setToolTip("Einstellungen")
        settings_btn.clicked.connect(self.open_settings)
        headerbar.addWidget(settings_btn)
```

#### Native Theme-Integration

```python
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor

def apply_native_theme(app: QApplication):
    """Systemfarben verwenden"""

    # GTK-Theme in Qt laden (wenn verfügbar)
    app.setStyle("Fusion")  # Fallback

    # Alternativ: QGtkStyle (wenn kompiliert mit GTK-Support)
    try:
        app.setStyle("gtk2")
    except:
        pass

    # System-Palette verwenden
    palette = app.palette()

    # Optional: Anpassungen für bessere GTK-Integration
    if is_dark_theme():
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        app.setPalette(palette)

def is_dark_theme() -> bool:
    """Prüft ob dunkles Theme aktiv ist"""
    palette = QApplication.palette()
    bg = palette.color(QPalette.ColorRole.Window)
    return bg.lightness() < 128
```

### KDE Plasma-Integration

#### Breeze-Style

```python
from PyQt6.QtWidgets import QApplication

def setup_kde_integration(app: QApplication):
    """KDE/Plasma-spezifische Anpassungen"""

    # Breeze-Style verwenden (wenn verfügbar)
    if "Breeze" in QStyleFactory.keys():
        app.setStyle("Breeze")

    # KDE-Farbschema respektieren
    palette = app.palette()
    # Keine manuellen Überschreibungen - Breeze kümmert sich darum
```

#### System-Tray-Icons (KDE)

KDE nutzt StatusNotifierItem statt Legacy Tray:

```python
from PyQt6.QtWidgets import QSystemTrayIcon
from PyQt6.QtGui import QIcon

# Automatische Anpassung durch Qt
tray = QSystemTrayIcon(QIcon.fromTheme("transcribrai"))
tray.setToolTip("TranscribrAI")
```

### Wayland-Spezifika

#### Window-Management

```python
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Wayland: Keine absolute Positionierung
        # Fenster-Position wird vom Compositor bestimmt

        # Statt setGeometry() nur Größe setzen
        self.resize(520, 580)

        # Window-Hints für Wayland
        self.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint,
            False  # Auf Wayland problematisch
        )
```

#### Global Shortcuts (Wayland-Einschränkungen)

Wayland erlaubt keine direkten globalen Hotkeys aus Sicherheitsgründen.

**Lösungen:**

1. **evdev (empfohlen für TranscribrAI):**
```python
import evdev

class WaylandHotkeyManager:
    def __init__(self):
        # Benötigt Gruppe 'input'
        self.device = evdev.InputDevice('/dev/input/event0')

    def listen(self):
        for event in self.device.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                self.handle_key(event)
```

2. **XDG Desktop Portal (zukünftig):**
```python
# Noch nicht vollständig in PyQt6 integriert
# Würde GlobalShortcuts-Portal nutzen
```

**Dokumentation für Benutzer:**
```
Wayland-Nutzer:
Fügen Sie sich zur Gruppe 'input' hinzu für globale Hotkeys:
  sudo usermod -aG input $USER

Danach neu anmelden.
```

### freedesktop.org-Standards

#### Desktop-Entry

```ini
[Desktop Entry]
Version=1.5
Type=Application
Name=TranscribrAI
GenericName=Speech-to-Text
Comment=Lokale Sprach-Transkription mit Whisper
Icon=transcribrai
Exec=/usr/local/bin/transcribrai
Terminal=false
Categories=AudioVideo;Audio;Recorder;
Keywords=speech;voice;transcription;whisper;stt;
StartupNotify=true
StartupWMClass=transcribrai
```

Installationspfad: `~/.local/share/applications/transcribrai.desktop`

#### Icon-Theme-Spec

```
icons/
├── hicolor/
│   ├── 16x16/apps/transcribrai.svg
│   ├── 22x22/apps/transcribrai.svg
│   ├── 24x24/apps/transcribrai.svg
│   ├── 32x32/apps/transcribrai.svg
│   ├── 48x48/apps/transcribrai.svg
│   ├── scalable/apps/transcribrai.svg
│   └── symbolic/apps/transcribrai-symbolic.svg
```

Installation:
```bash
xdg-icon-resource install --size 48 transcribrai.svg
```

---

## Responsive Design

### Fenstergrößen

| Größe        | Breite × Höhe | Verwendung                          |
|--------------|---------------|-------------------------------------|
| Minimum      | 480 × 520     | Absolute Untergrenze                |
| Bevorzugt    | 520 × 580     | Standard beim ersten Start          |
| Maximum      | 800 × 900     | Empfohlenes Maximum                 |

### Layout-Verhalten bei Resize

```python
class MainWindow(QMainWindow):
    def resizeEvent(self, event):
        """Responsive Anpassungen bei Größenänderung"""
        super().resizeEvent(event)

        width = self.width()

        # Button-Größe skalieren (begrenzt)
        if width < 500:
            button_size = 120
        elif width > 700:
            button_size = 180
        else:
            button_size = 160

        self.ptt_button.setFixedSize(button_size, button_size)

        # Preview-Höhe anpassen
        available_height = self.height() - 400
        self.preview_text.setMaximumHeight(
            max(80, min(200, available_height))
        )
```

### Orientation-Aware

Obwohl primär Desktop-App, sollte extremes Querformat funktionieren:

```python
def adjust_for_aspect_ratio(self):
    """Layout bei breiten Fenstern anpassen"""
    aspect_ratio = self.width() / self.height()

    if aspect_ratio > 1.5:
        # Horizontales Layout für breite Fenster
        self.switch_to_horizontal_layout()
    else:
        # Vertikales Standard-Layout
        self.switch_to_vertical_layout()
```

---

## Status-Feedback

### Visuelle Feedback-Mechanismen

#### Button-States (Detailliert)

**Idle → Recording Transition:**
```python
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

def start_recording(self):
    """Aufnahme starten mit Animation"""

    # Farb-Übergang
    animation = QPropertyAnimation(self.ptt_button, b"styleSheet")
    animation.setDuration(300)
    animation.setStartValue("background-color: #3584e4;")
    animation.setEndValue("background-color: #e01b24;")
    animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    animation.start()

    # Pulsier-Animation starten
    self.pulse_timer.start(1500)

def pulse_effect(self):
    """Pulsierender Ring-Effekt während Recording"""
    # Implementierung via CSS-Animation oder QPainterPath
    pass
```

**Recording → Transcribing Transition:**
```python
def start_transcribing(self):
    """Transkription starten mit Spinner"""

    # Pulsier-Animation stoppen
    self.pulse_timer.stop()

    # Farbe zu Gelb wechseln
    self.ptt_button.setStyleSheet("background-color: #f6d32d;")

    # Spinner-Overlay anzeigen
    self.show_spinner_overlay()
```

#### Lautstärke-Animation

```python
class VolumeBar(QProgressBar):
    """Custom ProgressBar mit Smooth-Animation"""

    def __init__(self):
        super().__init__()
        self.target_value = 0
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_volume(self, volume: int):
        """Setzt Lautstärke mit smooth transition"""
        self.animation.stop()
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(volume)
        self.animation.start()
```

### Akustisches Feedback (Optional)

```python
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl

class SoundManager:
    """Optionale Sound-Effekte"""

    def __init__(self):
        self.start_sound = QSoundEffect()
        self.start_sound.setSource(
            QUrl.fromLocalFile("resources/sounds/start.wav")
        )

        self.stop_sound = QSoundEffect()
        self.stop_sound.setSource(
            QUrl.fromLocalFile("resources/sounds/stop.wav")
        )

    def play_start(self):
        if config.get("sounds_enabled", False):
            self.start_sound.play()

    def play_stop(self):
        if config.get("sounds_enabled", False):
            self.stop_sound.play()
```

### Fehler-Handling UI

#### Inline-Fehleranzeige

```python
class ErrorBanner(QWidget):
    """Fehler-Banner am oberen Rand"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Icon
        self.icon = QLabel()
        self.icon.setPixmap(
            QIcon.fromTheme("dialog-error").pixmap(24, 24)
        )
        layout.addWidget(self.icon)

        # Nachricht
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message, 1)

        # Schließen-Button
        close_btn = QPushButton("✕")
        close_btn.setFlat(True)
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)

        # Styling
        self.setStyleSheet("""
            ErrorBanner {
                background-color: #ffd7d5;
                border-left: 4px solid #e01b24;
                border-radius: 4px;
            }
        """)

        self.hide()

    def show_error(self, message: str):
        """Zeigt Fehlermeldung an"""
        self.message.setText(message)
        self.show()

        # Auto-Hide nach 10 Sekunden
        QTimer.singleShot(10000, self.hide)
```

#### Fehler-Typen und Nachrichten

```python
ERROR_MESSAGES = {
    "microphone_not_found": (
        "Kein Mikrofon gefunden",
        "Bitte schließen Sie ein Mikrofon an und wählen Sie es in den "
        "Einstellungen aus."
    ),
    "whisper_model_error": (
        "Whisper-Modell konnte nicht geladen werden",
        "Prüfen Sie Ihre Internetverbindung für den Download oder wählen "
        "Sie ein anderes Modell in den Einstellungen."
    ),
    "permission_denied": (
        "Zugriff verweigert",
        "Fehlende Berechtigung für Audio-Aufnahme. Prüfen Sie die "
        "System-Einstellungen."
    ),
    "keyboard_input_failed": (
        "Text konnte nicht eingegeben werden",
        "Auf Wayland: Stellen Sie sicher, dass ydotool-Daemon läuft und "
        "Sie zur Gruppe 'input' gehören."
    ),
}

def show_error(self, error_type: str):
    """Zeigt typisierten Fehler"""
    title, message = ERROR_MESSAGES.get(
        error_type,
        ("Unbekannter Fehler", "Ein unerwarteter Fehler ist aufgetreten.")
    )
    self.error_banner.show_error(f"<b>{title}</b><br>{message}")
```

---

## Implementierungs-Checkliste

### Phase 1: Grundgerüst
- [ ] Hauptfenster-Klasse mit Basis-Layout
- [ ] Push-to-Talk Button (ohne Funktion)
- [ ] Status-Label
- [ ] Transkriptions-Vorschau
- [ ] Basis-Styling (GNOME-Farben)

### Phase 2: Interaktivität
- [ ] State-Management implementieren
- [ ] Button Click → State-Wechsel
- [ ] Lautstärke-Indikator mit Animation
- [ ] Button-Animationen (Hover, Pressed, Pulse)

### Phase 3: Einstellungen
- [ ] Einstellungs-Dialog-Layout
- [ ] Config-Loading/Saving
- [ ] Modell-Dropdown mit Beschreibungen
- [ ] Audio-Geräte-Auswahl
- [ ] Hotkey-Recorder

### Phase 4: System-Integration
- [ ] System-Tray-Icon
- [ ] Tray-Kontextmenü
- [ ] Notifications
- [ ] Globaler Hotkey (X11/Wayland)

### Phase 5: Barrierefreiheit
- [ ] Alle AccessibleNames/Descriptions setzen
- [ ] Tastatur-Navigation testen
- [ ] Fokus-Indikatoren prüfen
- [ ] Kontrast-Verhältnisse verifizieren
- [ ] Screen Reader testen (Orca)

### Phase 6: Theme-Integration
- [ ] GNOME-Session-Erkennung
- [ ] Header Bar (GNOME)
- [ ] Standard-Menüleiste (KDE)
- [ ] Dark-Theme-Unterstützung
- [ ] Icon-Theme-Integration

### Phase 7: Polish
- [ ] Fehler-Banner implementieren
- [ ] Alle Error-Messages definieren
- [ ] Smooth-Transitions überall
- [ ] Responsive-Tests (min/max Größen)
- [ ] UX-Review mit echten Benutzern

---

## Design-Assets

### Benötigte Icons

#### Anwendungs-Icon (SVG)

```xml
<!-- resources/icons/transcribrai.svg -->
<!-- Mikrofon-Symbol in GNOME-Stil -->
<svg width="48" height="48" xmlns="http://www.w3.org/2000/svg">
  <!-- Simplified microphone shape -->
  <path d="M24 2c-3.3 0-6 2.7-6 6v12c0 3.3 2.7 6 6 6s6-2.7 6-6V8c0-3.3-2.7-6-6-6z"
        fill="#3584e4"/>
  <path d="M12 18v2c0 6.6 5.4 12 12 12s12-5.4 12-12v-2h-2v2c0 5.5-4.5 10-10 10s-10-4.5-10-10v-2h-2z"
        fill="#3584e4"/>
  <rect x="22" y="32" width="4" height="12" fill="#3584e4"/>
  <rect x="16" y="44" width="16" height="2" fill="#3584e4"/>
</svg>
```

#### Tray-Icons (Monochrom)

```
resources/icons/tray/
├── idle.svg         # Mikrofon-Outline
├── recording.svg    # Mikrofon-Filled + roter Punkt
├── transcribing.svg # Mikrofon + kleines Zahnrad
├── sending.svg      # Mikrofon + Pfeil →
└── error.svg        # Mikrofon + Warnsymbol
```

### Schriftarten

**Primär:** System-Default (Cantarell auf GNOME, Noto Sans auf KDE)

```python
from PyQt6.QtGui import QFont, QFontDatabase

# System-Font verwenden
app_font = QApplication.font()

# Monospace für Code/Transkriptionen
mono_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
```

---

## Testing-Richtlinien

### Manuelle UI-Tests

**Test-Matrix:**

| Test-Fall | GNOME/X11 | GNOME/Wayland | KDE/X11 | KDE/Wayland |
|-----------|-----------|---------------|---------|-------------|
| Button-Klick | ✓ | ✓ | ✓ | ✓ |
| Hotkey (Global) | ✓ | ⚠ | ✓ | ⚠ |
| Tray-Icon | ✓ | ✓ | ✓ | ✓ |
| Notifications | ✓ | ✓ | ✓ | ✓ |
| Dark Theme | ✓ | ✓ | ✓ | ✓ |
| HiDPI (200%) | ✓ | ✓ | ✓ | ✓ |

⚠ = Benötigt spezielle Konfiguration (evdev-Gruppe)

### Accessibility-Tests

**Orca Screen Reader:**
```bash
# Orca starten
orca

# Testen:
# 1. Tab-Navigation → Alle Elemente erreichbar?
# 2. Button-Beschreibung → Wird korrekt vorgelesen?
# 3. Status-Updates → Werden neue Status angesagt?
```

**Kontrast-Tools:**
```bash
# Contrast-Ratio prüfen
# https://webaim.org/resources/contrastchecker/

# Oder automatisch mit:
pip install accessibility-checker
python -m accessibility_checker gui_screenshot.png
```

### Visuelle Regression-Tests

```python
# Optional: pytest + pytest-qt + pixelmatch

def test_button_idle_state(qtbot):
    """Prüft Button im Idle-Zustand"""
    window = MainWindow()
    qtbot.addWidget(window)

    # Screenshot machen
    pixmap = window.grab()

    # Mit Referenz vergleichen
    assert compare_images(pixmap, "references/button_idle.png")
```

---

## Anhang

### Referenzen

- [GNOME Human Interface Guidelines](https://developer.gnome.org/hig/)
- [KDE Human Interface Guidelines](https://develop.kde.org/hig/)
- [freedesktop.org Specifications](https://www.freedesktop.org/wiki/Specifications/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### Beispiel-Anwendungen (Linux-native UIs)

- **GNOME Apps:** Nautilus, GNOME Clocks, GNOME Weather
- **KDE Apps:** Dolphin, Spectacle, Okular
- **PyQt Apps:** Calibre, Anki (teilweise)

### Design-Tools

- **Figma/Inkscape:** Icon-Design
- **GIMP:** Screenshot-Editing
- **Glade:** GTK-UI-Prototyping (zur Inspiration)
- **Qt Designer:** PyQt-Layout-Prototyping

---

**Dokumentversion:** 1.0
**Autor:** Linux UI/UX Expert für TranscribrAI
**Lizenz:** Same as project (MIT)
