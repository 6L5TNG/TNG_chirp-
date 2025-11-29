# -*- coding: utf-8 -*-
"""
MPDA Settings Dialog
Tab-based settings with Windows MME device filtering.
"""
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from mpda_app.core.audio import get_audio_devices


class SettingsDialog(QDialog):
    """
    Settings dialog with tabbed interface.
    Filters audio devices to show only Windows MME devices.
    """

    # Signal emitted when settings are applied
    settings_changed = pyqtSignal(dict)

    def __init__(self, settings: dict = None, parent=None):
        super().__init__(parent)
        self.settings = settings or {}
        self._original_settings = dict(self.settings)

        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()
        self._setup_audio_tab()
        self._setup_protocol_tab()
        self._setup_display_tab()

        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(self.apply_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_ok)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        # Apply dark theme
        self._apply_style()

    def _apply_style(self):
        """Apply VS Code dark theme styling."""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 8px 16px;
                border: 1px solid #3c3c3c;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #0e639c;
            }
            QTabBar::tab:hover {
                background-color: #3c3c3c;
            }
            QGroupBox {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #9cdcfe;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #cccccc;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 5px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                color: #cccccc;
                selection-background-color: #0e639c;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 5px;
            }
            QCheckBox {
                color: #cccccc;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3c3c3c;
                border: 1px solid #555555;
            }
            QCheckBox::indicator:checked {
                background-color: #0e639c;
                border: 1px solid #0e639c;
            }
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #094771;
            }
        """
        )

    def _setup_audio_tab(self):
        """Set up audio settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Device selection group
        device_group = QGroupBox("Audio Devices")
        device_layout = QFormLayout(device_group)

        # Input device (MME filtered)
        self.input_device_combo = QComboBox()
        self._populate_input_devices()
        device_layout.addRow("Input Device:", self.input_device_combo)

        # Output device (MME filtered)
        self.output_device_combo = QComboBox()
        self._populate_output_devices()
        device_layout.addRow("Output Device:", self.output_device_combo)

        layout.addWidget(device_group)

        # Sample rate
        sr_group = QGroupBox("Sample Rate")
        sr_layout = QFormLayout(sr_group)

        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000"])
        sr_layout.addRow("Sample Rate (Hz):", self.sample_rate_combo)

        layout.addWidget(sr_group)

        layout.addStretch()
        self.tabs.addTab(tab, "Audio")

    def _setup_protocol_tab(self):
        """Set up protocol settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # MPDA settings
        mpda_group = QGroupBox("MPDA Protocol")
        mpda_layout = QFormLayout(mpda_group)

        # Default tracks
        self.tracks_combo = QComboBox()
        self.tracks_combo.addItems(["1", "4", "8"])
        self.tracks_combo.setCurrentText("4")
        mpda_layout.addRow("Default Tracks:", self.tracks_combo)

        # Default speed
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["5", "10", "15"])
        self.speed_combo.setCurrentText("10")
        mpda_layout.addRow("Default Speed:", self.speed_combo)

        layout.addWidget(mpda_group)

        # Gain settings
        gain_group = QGroupBox("Gain Settings")
        gain_layout = QFormLayout(gain_group)

        # TX Gain
        self.tx_gain_spin = QSpinBox()
        self.tx_gain_spin.setRange(0, 100)
        self.tx_gain_spin.setValue(80)
        self.tx_gain_spin.setSuffix("%")
        gain_layout.addRow("TX Gain:", self.tx_gain_spin)

        # RX Gain
        self.rx_gain_spin = QSpinBox()
        self.rx_gain_spin.setRange(0, 200)
        self.rx_gain_spin.setValue(50)
        self.rx_gain_spin.setSuffix("%")
        gain_layout.addRow("RX Gain:", self.rx_gain_spin)

        layout.addWidget(gain_group)

        layout.addStretch()
        self.tabs.addTab(tab, "Protocol")

    def _setup_display_tab(self):
        """Set up display settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Visualization
        vis_group = QGroupBox("Visualization")
        vis_layout = QFormLayout(vis_group)

        # FFT size
        self.fft_size_combo = QComboBox()
        self.fft_size_combo.addItems(["512", "1024", "2048", "4096"])
        self.fft_size_combo.setCurrentText("1024")
        vis_layout.addRow("FFT Size:", self.fft_size_combo)

        # Update rate
        self.update_rate_spin = QSpinBox()
        self.update_rate_spin.setRange(5, 60)
        self.update_rate_spin.setValue(30)
        self.update_rate_spin.setSuffix(" Hz")
        vis_layout.addRow("Update Rate:", self.update_rate_spin)

        layout.addWidget(vis_group)

        layout.addStretch()
        self.tabs.addTab(tab, "Display")

    def _populate_input_devices(self):
        """Populate input device combo with MME-filtered devices."""
        self.input_device_combo.clear()
        self.input_device_combo.addItem("Default", None)

        input_devices, _ = get_audio_devices(filter_mme=True)
        for idx, name in input_devices:
            self.input_device_combo.addItem(name, idx)

    def _populate_output_devices(self):
        """Populate output device combo with MME-filtered devices."""
        self.output_device_combo.clear()
        self.output_device_combo.addItem("Default", None)

        _, output_devices = get_audio_devices(filter_mme=True)
        for idx, name in output_devices:
            self.output_device_combo.addItem(name, idx)

    def _load_settings(self):
        """Load current settings into UI."""
        # Audio
        input_idx = self.settings.get("input_device")
        if input_idx is not None:
            for i in range(self.input_device_combo.count()):
                if self.input_device_combo.itemData(i) == input_idx:
                    self.input_device_combo.setCurrentIndex(i)
                    break

        output_idx = self.settings.get("output_device")
        if output_idx is not None:
            for i in range(self.output_device_combo.count()):
                if self.output_device_combo.itemData(i) == output_idx:
                    self.output_device_combo.setCurrentIndex(i)
                    break

        sample_rate = self.settings.get("sample_rate", 44100)
        self.sample_rate_combo.setCurrentText(str(sample_rate))

        # Protocol
        tracks = self.settings.get("default_tracks", 4)
        self.tracks_combo.setCurrentText(str(tracks))

        speed = self.settings.get("default_speed", 10)
        self.speed_combo.setCurrentText(str(speed))

        self.tx_gain_spin.setValue(self.settings.get("tx_gain", 80))
        self.rx_gain_spin.setValue(self.settings.get("rx_gain", 50))

        # Display
        fft_size = self.settings.get("fft_size", 1024)
        self.fft_size_combo.setCurrentText(str(fft_size))

        update_rate = self.settings.get("update_rate", 30)
        self.update_rate_spin.setValue(update_rate)

    def _gather_settings(self) -> dict:
        """Gather settings from UI into dictionary."""
        return {
            "input_device": self.input_device_combo.currentData(),
            "output_device": self.output_device_combo.currentData(),
            "sample_rate": int(self.sample_rate_combo.currentText()),
            "default_tracks": int(self.tracks_combo.currentText()),
            "default_speed": int(self.speed_combo.currentText()),
            "tx_gain": self.tx_gain_spin.value(),
            "rx_gain": self.rx_gain_spin.value(),
            "fft_size": int(self.fft_size_combo.currentText()),
            "update_rate": self.update_rate_spin.value(),
        }

    def _on_apply(self):
        """Handle Apply button click."""
        self.settings = self._gather_settings()
        self.settings_changed.emit(self.settings)

    def _on_ok(self):
        """Handle OK button click."""
        self._on_apply()
        self.accept()

    def get_settings(self) -> dict:
        """Get current settings."""
        return self.settings
