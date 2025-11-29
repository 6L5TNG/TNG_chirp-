# -*- coding: utf-8 -*-
"""
MPDA Main Window
Modern Dark IDE Style (VS Code Dark Theme) main application window.
"""
import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTextEdit,
    QSlider,
    QComboBox,
    QPushButton,
    QLabel,
    QGroupBox,
    QProgressBar,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont

from mpda_app.core.audio import (
    AudioEngine,
    TuneGenerator,
    AudioInputMonitor,
)
from mpda_app.core.protocol import (
    MPDATransmitter,
    MPDAReceiver,
    SAMPLE_RATE,
)
from mpda_app.ui.visuals import VisualWidget
from mpda_app.ui.settings_dialog import SettingsDialog


# VS Code Dark Theme Colors
COLORS = {
    "window_bg": "#1e1e1e",
    "text": "#cccccc",
    "input_bg": "#111111",
    "groupbox_bg": "#252526",
    "groupbox_border": "#3c3c3c",
    "groupbox_title": "#9cdcfe",
    "rx_data": "#dcdcaa",  # Soft Gold
    "system": "#569cd6",  # Soft Blue
    "error": "#f44747",  # Soft Red
    "button_primary": "#0e639c",
    "button_hover": "#1177bb",
    "tune_active": "#d16969",
}

SETTINGS_FILE = "mpda_settings.json"


class MainWindow(QMainWindow):
    """
    Main application window with VS Code Dark theme styling.

    Layout:
    - Top: Menu bar (File, Settings, Help)
    - Visualization area: 280px fixed height
    - Center splitter: RX (4) : TX (6) ratio
    - Bottom: Status bar with audio level meter
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize settings
        self.settings = self._load_settings()

        # Initialize protocol classes
        self.transmitter = MPDATransmitter(SAMPLE_RATE)
        self.receiver = MPDAReceiver(
            tracks=self.settings.get("default_tracks", 4),
            speed=self.settings.get("default_speed", 10),
        )

        # Audio threads
        self.audio_engine: Optional[AudioEngine] = None
        self.tune_generator: Optional[TuneGenerator] = None
        self.input_monitor: Optional[AudioInputMonitor] = None

        # State
        self.is_transmitting = False
        self.is_tuning = False

        # Setup UI
        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._setup_status_bar()
        self._apply_style()

        # Setup timers
        self._setup_timers()

        # Start input monitor
        self._start_input_monitor()

    def _load_settings(self) -> dict:
        """Load settings from file."""
        defaults = {
            "input_device": None,
            "output_device": None,
            "sample_rate": SAMPLE_RATE,
            "default_tracks": 4,
            "default_speed": 10,
            "tx_gain": 80,
            "rx_gain": 50,
            "fft_size": 1024,
            "update_rate": 30,
        }

        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
        except Exception:
            pass

        return defaults

    def _save_settings(self):
        """Save settings to file."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def _setup_window(self):
        """Setup main window properties."""
        self.setWindowTitle("MPDA Terminal")
        self.setMinimumSize(900, 700)
        self.resize(1200, 800)

    def _setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        open_settings = QAction("Open Dialog...", self)
        open_settings.setShortcut("Ctrl+,")
        open_settings.triggered.connect(self._open_settings)
        settings_menu.addAction(open_settings)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_ui(self):
        """Setup main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Visualization area (280px fixed height)
        self.visual_widget = VisualWidget(
            sample_rate=self.settings.get("sample_rate", SAMPLE_RATE),
            fft_size=self.settings.get("fft_size", 1024),
        )
        self.visual_widget.setFixedHeight(280)
        main_layout.addWidget(self.visual_widget)

        # Main splitter (RX:TX = 4:6)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # RX Panel (left)
        rx_panel = self._create_rx_panel()
        splitter.addWidget(rx_panel)

        # TX Panel (right)
        tx_panel = self._create_tx_panel()
        splitter.addWidget(tx_panel)

        # Set splitter sizes (4:6 ratio)
        splitter.setSizes([400, 600])

        main_layout.addWidget(splitter, 1)

    def _create_rx_panel(self) -> QGroupBox:
        """Create RX (receive) panel."""
        group = QGroupBox("RX - Received Data")
        layout = QVBoxLayout(group)

        # RX text display (read-only)
        self.rx_text = QTextEdit()
        self.rx_text.setReadOnly(True)
        self.rx_text.setFont(QFont("Consolas", 11))
        self.rx_text.setPlaceholderText("Received data will appear here...")
        layout.addWidget(self.rx_text, 1)

        # RX Gain slider
        gain_layout = QHBoxLayout()
        gain_label = QLabel("RX Gain:")
        gain_layout.addWidget(gain_label)

        self.rx_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.rx_gain_slider.setRange(0, 200)
        self.rx_gain_slider.setValue(self.settings.get("rx_gain", 50))
        self.rx_gain_slider.valueChanged.connect(self._on_rx_gain_changed)
        gain_layout.addWidget(self.rx_gain_slider, 1)

        self.rx_gain_label = QLabel(f"{self.rx_gain_slider.value()}%")
        self.rx_gain_label.setMinimumWidth(40)
        gain_layout.addWidget(self.rx_gain_label)

        layout.addLayout(gain_layout)

        return group

    def _create_tx_panel(self) -> QGroupBox:
        """Create TX (transmit) panel."""
        group = QGroupBox("TX - Transmit")
        layout = QVBoxLayout(group)

        # TX text input (editable)
        self.tx_text = QTextEdit()
        self.tx_text.setFont(QFont("Consolas", 11))
        self.tx_text.setPlaceholderText("Enter text to transmit...")
        self.tx_text.setMinimumHeight(80)
        layout.addWidget(self.tx_text, 1)

        # Quick Controls
        quick_layout = QHBoxLayout()

        # Tracks selection
        quick_layout.addWidget(QLabel("Trk:"))
        self.tracks_combo = QComboBox()
        self.tracks_combo.addItems(["1", "4", "8"])
        self.tracks_combo.setCurrentText(str(self.settings.get("default_tracks", 4)))
        self.tracks_combo.setFixedWidth(60)
        quick_layout.addWidget(self.tracks_combo)

        quick_layout.addSpacing(10)

        # Speed selection
        quick_layout.addWidget(QLabel("Spd:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["5", "10", "15"])
        self.speed_combo.setCurrentText(str(self.settings.get("default_speed", 10)))
        self.speed_combo.setFixedWidth(60)
        quick_layout.addWidget(self.speed_combo)

        quick_layout.addSpacing(10)

        # TUNE button (checkable)
        self.tune_btn = QPushButton("TUNE")
        self.tune_btn.setCheckable(True)
        self.tune_btn.setFixedWidth(80)
        self.tune_btn.clicked.connect(self._on_tune_clicked)
        quick_layout.addWidget(self.tune_btn)

        quick_layout.addStretch()
        layout.addLayout(quick_layout)

        # TX Actions
        action_layout = QHBoxLayout()

        # TX button
        self.tx_btn = QPushButton("TX")
        self.tx_btn.setFixedWidth(80)
        self.tx_btn.clicked.connect(self._on_tx_clicked)
        action_layout.addWidget(self.tx_btn)

        # Halt button
        self.halt_btn = QPushButton("Halt")
        self.halt_btn.setFixedWidth(80)
        self.halt_btn.setEnabled(False)
        self.halt_btn.clicked.connect(self._on_halt_clicked)
        action_layout.addWidget(self.halt_btn)

        action_layout.addSpacing(20)

        # TX Gain slider
        action_layout.addWidget(QLabel("TX Gain:"))
        self.tx_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.tx_gain_slider.setRange(0, 100)
        self.tx_gain_slider.setValue(self.settings.get("tx_gain", 80))
        self.tx_gain_slider.valueChanged.connect(self._on_tx_gain_changed)
        action_layout.addWidget(self.tx_gain_slider, 1)

        self.tx_gain_label = QLabel(f"{self.tx_gain_slider.value()}%")
        self.tx_gain_label.setMinimumWidth(40)
        action_layout.addWidget(self.tx_gain_label)

        layout.addLayout(action_layout)

        return group

    def _setup_status_bar(self):
        """Setup status bar with level meter."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status message
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)

        # Audio input level meter
        level_label = QLabel("Input Level:")
        self.status_bar.addPermanentWidget(level_label)

        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setValue(0)
        self.level_meter.setFixedWidth(150)
        self.level_meter.setTextVisible(False)
        self.status_bar.addPermanentWidget(self.level_meter)

    def _apply_style(self):
        """Apply VS Code Dark theme styling."""
        style = f"""
            QMainWindow {{
                background-color: {COLORS['window_bg']};
            }}
            QWidget {{
                background-color: {COLORS['window_bg']};
                color: {COLORS['text']};
            }}
            QMenuBar {{
                background-color: {COLORS['groupbox_bg']};
                color: {COLORS['text']};
            }}
            QMenuBar::item:selected {{
                background-color: {COLORS['button_primary']};
            }}
            QMenu {{
                background-color: {COLORS['groupbox_bg']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['groupbox_border']};
            }}
            QMenu::item:selected {{
                background-color: {COLORS['button_primary']};
            }}
            QGroupBox {{
                background-color: {COLORS['groupbox_bg']};
                border: 1px solid {COLORS['groupbox_border']};
                margin-top: 12px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                color: {COLORS['groupbox_title']};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QTextEdit {{
                background-color: {COLORS['input_bg']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['groupbox_border']};
                font-family: Consolas, monospace;
            }}
            QComboBox {{
                background-color: {COLORS['groupbox_bg']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['groupbox_border']};
                padding: 5px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['groupbox_bg']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['button_primary']};
            }}
            QPushButton {{
                background-color: {COLORS['button_primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_hover']};
            }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #888888;
            }}
            QPushButton:checked {{
                background-color: {COLORS['tune_active']};
            }}
            QSlider::groove:horizontal {{
                background-color: {COLORS['groupbox_border']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background-color: {COLORS['button_primary']};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: {COLORS['button_hover']};
            }}
            QProgressBar {{
                background-color: {COLORS['groupbox_border']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['system']};
                border-radius: 3px;
            }}
            QStatusBar {{
                background-color: {COLORS['groupbox_bg']};
                color: {COLORS['text']};
            }}
            QSplitter::handle {{
                background-color: {COLORS['groupbox_border']};
            }}
        """
        self.setStyleSheet(style)

    def _setup_timers(self):
        """Setup update timers."""
        # Visualization update timer
        update_rate = self.settings.get("update_rate", 30)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(1000 // update_rate)

    def _start_input_monitor(self):
        """Start audio input monitoring."""
        self.input_monitor = AudioInputMonitor(
            sample_rate=self.settings.get("sample_rate", SAMPLE_RATE),
            device=self.settings.get("input_device"),
            chunk_size=1024,
        )
        self.input_monitor.gain = self.rx_gain_slider.value() / 100.0
        self.input_monitor.level_update.connect(self._on_input_level)
        self.input_monitor.samples_ready.connect(self._on_samples_ready)
        self.input_monitor.error.connect(self._on_audio_error)
        self.input_monitor.start()

    def _stop_input_monitor(self):
        """Stop audio input monitoring."""
        if self.input_monitor:
            self.input_monitor.stop()
            self.input_monitor.wait(1000)
            self.input_monitor.cleanup()
            self.input_monitor = None

    # Event handlers
    def _on_rx_gain_changed(self, value: int):
        """Handle RX gain slider change."""
        self.rx_gain_label.setText(f"{value}%")
        if self.input_monitor:
            self.input_monitor.gain = value / 100.0
        self.settings["rx_gain"] = value

    def _on_tx_gain_changed(self, value: int):
        """Handle TX gain slider change."""
        self.tx_gain_label.setText(f"{value}%")
        if self.audio_engine:
            self.audio_engine.current_gain = value / 100.0
        self.settings["tx_gain"] = value

    def _on_tune_clicked(self, checked: bool):
        """Handle TUNE button click."""
        if checked:
            self._start_tune()
        else:
            self._stop_tune()

    def _on_tx_clicked(self):
        """Handle TX button click."""
        if self.is_transmitting:
            return

        text = self.tx_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Warning", "Please enter text to transmit.")
            return

        self._start_transmission(text)

    def _on_halt_clicked(self):
        """Handle Halt button click."""
        self._stop_transmission()

    def _on_input_level(self, db: float):
        """Handle input level update."""
        # Convert dB to percentage (-60dB to 0dB range)
        level = int((db + 60) / 60 * 100)
        level = max(0, min(100, level))
        self.level_meter.setValue(level)

    def _on_samples_ready(self, samples: np.ndarray):
        """Handle incoming audio samples."""
        # Update visualization
        self.visual_widget.update_spectrum(samples)

        # Process with receiver
        result = self.receiver.process_audio(samples)
        if result:
            if result == "<EOT>":
                # End of transmission
                decoded = self.receiver.get_decoded_text()
                self._append_rx_text(decoded)
                self._set_status("Received: End of transmission")
            else:
                self._append_rx_text(result)

    def _on_audio_error(self, error: str):
        """Handle audio error."""
        self._set_status(f"Audio error: {error}")

    def _on_tx_finished(self):
        """Handle TX completion."""
        self.is_transmitting = False
        self.tx_btn.setEnabled(True)
        self.halt_btn.setEnabled(False)
        self._set_status("Transmission complete")

    def _on_tx_progress(self, progress: float):
        """Handle TX progress update."""
        self._set_status(f"Transmitting... {int(progress * 100)}%")

    # Actions
    def _start_tune(self):
        """Start TUNE tone."""
        if self.is_tuning:
            return

        self.is_tuning = True
        self.tune_generator = TuneGenerator(
            sample_rate=self.settings.get("sample_rate", SAMPLE_RATE),
            device=self.settings.get("output_device"),
            amplitude=self.tx_gain_slider.value() / 100.0,
        )
        self.tune_generator.error.connect(self._on_audio_error)
        self.tune_generator.start()
        self._set_status("TUNE active (1500Hz)")

    def _stop_tune(self):
        """Stop TUNE tone."""
        if not self.is_tuning:
            return

        if self.tune_generator:
            self.tune_generator.stop()
            self.tune_generator.wait(1000)
            self.tune_generator.cleanup()
            self.tune_generator = None

        self.is_tuning = False
        self.tune_btn.setChecked(False)
        self._set_status("TUNE stopped")

    def _start_transmission(self, text: str):
        """Start transmitting text."""
        if self.is_transmitting:
            return

        # Stop tune if active
        if self.is_tuning:
            self._stop_tune()

        self.is_transmitting = True
        self.tx_btn.setEnabled(False)
        self.halt_btn.setEnabled(True)

        # Generate signal
        tracks = int(self.tracks_combo.currentText())
        speed = int(self.speed_combo.currentText())

        samples = self.transmitter.generate_signal(text, tracks=tracks, speed=speed)

        # Start audio engine
        self.audio_engine = AudioEngine(
            samples=samples,
            sample_rate=self.settings.get("sample_rate", SAMPLE_RATE),
            device=self.settings.get("output_device"),
        )
        self.audio_engine.current_gain = self.tx_gain_slider.value() / 100.0
        self.audio_engine.finished.connect(self._on_tx_finished)
        self.audio_engine.progress.connect(self._on_tx_progress)
        self.audio_engine.error.connect(self._on_audio_error)
        self.audio_engine.start()

        self._set_status("Transmitting...")

    def _stop_transmission(self):
        """Stop current transmission."""
        if not self.is_transmitting:
            return

        if self.audio_engine:
            self.audio_engine.stop()
            self.audio_engine.wait(1000)
            self.audio_engine.cleanup()
            self.audio_engine = None

        self.is_transmitting = False
        self.tx_btn.setEnabled(True)
        self.halt_btn.setEnabled(False)
        self._set_status("Transmission halted")

    def _append_rx_text(self, text: str):
        """Append text to RX display."""
        self.rx_text.append(text)

    def _set_status(self, message: str):
        """Set status bar message."""
        self.status_label.setText(message)

    def _update_display(self):
        """Periodic display update."""
        # Update receiver state display if needed
        pass

    def _open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, new_settings: dict):
        """Handle settings change."""
        self.settings.update(new_settings)
        self._save_settings()

        # Apply changes
        self.visual_widget.set_sample_rate(self.settings.get("sample_rate", SAMPLE_RATE))

        # Update combos
        self.tracks_combo.setCurrentText(str(self.settings.get("default_tracks", 4)))
        self.speed_combo.setCurrentText(str(self.settings.get("default_speed", 10)))

        # Update gain sliders
        self.rx_gain_slider.setValue(self.settings.get("rx_gain", 50))
        self.tx_gain_slider.setValue(self.settings.get("tx_gain", 80))

        # Restart input monitor with new settings
        self._stop_input_monitor()
        self._start_input_monitor()

        self._set_status("Settings applied")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About MPDA Terminal",
            "MPDA Terminal v1.0.0\n\n"
            "Multi-Parallel Differential ASK Protocol\n"
            "Amateur Radio Digital Modem\n\n"
            "GitHub: https://github.com/6L5TNG/TNG_chirp-",
        )

    def closeEvent(self, event):
        """Handle window close event."""
        # Stop all audio threads
        self._stop_transmission()
        self._stop_tune()
        self._stop_input_monitor()

        # Save settings
        self._save_settings()

        event.accept()
