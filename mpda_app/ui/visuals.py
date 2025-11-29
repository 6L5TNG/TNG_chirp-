# -*- coding: utf-8 -*-
"""
MPDA Visualization Widget
PyQtGraph-based spectrum analyzer and waterfall display.
"""
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from PyQt6.QtCore import Qt, QTimer

try:
    import pyqtgraph as pg

    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False


class VisualWidget(QWidget):
    """
    Visualization widget with spectrum and waterfall display modes.

    Features:
    - Waterfall mode: ImageItem with invertY(True), newest data at top
    - Spectrum mode: Simple line graph
    - No mouse interaction, hidden axis labels
    - Background color: #000000
    """

    # Display modes
    MODE_SPECTRUM = "Spectrum"
    MODE_WATERFALL = "Waterfall"

    def __init__(
        self, sample_rate: int = 44100, fft_size: int = 1024, parent=None
    ):
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.history_size = 100  # Number of rows in waterfall

        # Waterfall data storage
        self.waterfall_data = np.zeros(
            (self.history_size, self.fft_size // 2), dtype=np.float32
        )

        self._current_mode = self.MODE_WATERFALL
        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Mode selector
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(5, 2, 5, 2)

        mode_label = QLabel("Display:")
        mode_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([self.MODE_WATERFALL, self.MODE_SPECTRUM])
        self.mode_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 2px 5px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                color: #cccccc;
                selection-background-color: #0e639c;
            }
        """
        )
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        # Plot widget
        if PYQTGRAPH_AVAILABLE:
            self._setup_pyqtgraph()
        else:
            # Fallback if pyqtgraph not available
            self._setup_fallback()

        layout.addWidget(self.plot_widget)

    def _setup_pyqtgraph(self):
        """Set up PyQtGraph plot widget."""
        # Configure pyqtgraph defaults
        pg.setConfigOptions(antialias=False, background="#000000", foreground="#cccccc")

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#000000")

        # Disable mouse interaction
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()

        # Hide axis labels
        self.plot_widget.getAxis("left").hide()
        self.plot_widget.getAxis("bottom").hide()

        # Set up for waterfall mode initially
        self._setup_waterfall_mode()

    def _setup_fallback(self):
        """Set up fallback widget when pyqtgraph is not available."""
        from PyQt6.QtWidgets import QLabel

        self.plot_widget = QLabel("PyQtGraph not installed")
        self.plot_widget.setStyleSheet(
            "background-color: #000000; color: #cccccc; padding: 20px;"
        )
        self.plot_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _setup_waterfall_mode(self):
        """Set up waterfall display mode."""
        if not PYQTGRAPH_AVAILABLE:
            return

        self.plot_widget.clear()

        # Create ImageItem for waterfall
        self.image_item = pg.ImageItem()
        self.plot_widget.addItem(self.image_item)

        # Invert Y axis so newest data flows from top to bottom
        self.plot_widget.invertY(True)

        # Set colormap (plasma-like)
        colormap = pg.colormap.get("plasma")
        self.image_item.setLookupTable(colormap.getLookupTable())

        # Initialize with zeros
        self.image_item.setImage(
            self.waterfall_data.T, autoLevels=False, levels=(-80, 0)
        )

    def _setup_spectrum_mode(self):
        """Set up spectrum display mode."""
        if not PYQTGRAPH_AVAILABLE:
            return

        self.plot_widget.clear()
        self.plot_widget.invertY(False)

        # Create spectrum curve
        self.spectrum_curve = self.plot_widget.plot(
            pen=pg.mkPen(color="#00ff00", width=1)
        )

        # Set Y axis range
        self.plot_widget.setYRange(-100, 0)
        self.plot_widget.setXRange(0, self.sample_rate // 2)

    def _on_mode_changed(self, mode: str):
        """Handle display mode change."""
        self._current_mode = mode

        if mode == self.MODE_WATERFALL:
            self._setup_waterfall_mode()
        else:
            self._setup_spectrum_mode()

    def update_spectrum(self, samples: np.ndarray):
        """
        Update visualization with new audio samples.

        Args:
            samples: NumPy array of audio samples
        """
        if not PYQTGRAPH_AVAILABLE:
            return

        if len(samples) == 0:
            return

        # Compute FFT
        fft_data = self._compute_fft(samples)

        if self._current_mode == self.MODE_WATERFALL:
            self._update_waterfall(fft_data)
        else:
            self._update_spectrum(fft_data)

    def _compute_fft(self, samples: np.ndarray) -> np.ndarray:
        """Compute FFT magnitude in dB."""
        # Ensure we have enough samples
        if len(samples) < self.fft_size:
            samples = np.pad(samples, (0, self.fft_size - len(samples)))
        elif len(samples) > self.fft_size:
            samples = samples[-self.fft_size:]

        # Apply Hann window
        window = np.hanning(len(samples))
        windowed = samples * window

        # Compute FFT
        fft = np.fft.rfft(windowed)
        magnitude = np.abs(fft[: self.fft_size // 2])

        # Convert to dB
        magnitude_db = 20 * np.log10(magnitude + 1e-10)

        return magnitude_db.astype(np.float32)

    def _update_waterfall(self, fft_data: np.ndarray):
        """Update waterfall display."""
        # Ensure correct size
        if len(fft_data) != self.fft_size // 2:
            fft_data = np.interp(
                np.linspace(0, 1, self.fft_size // 2),
                np.linspace(0, 1, len(fft_data)),
                fft_data,
            )

        # Roll waterfall data down (newest at index 0)
        self.waterfall_data = np.roll(self.waterfall_data, 1, axis=0)
        self.waterfall_data[0, :] = fft_data

        # Update image
        if hasattr(self, "image_item"):
            self.image_item.setImage(
                self.waterfall_data.T, autoLevels=False, levels=(-80, 0)
            )

    def _update_spectrum(self, fft_data: np.ndarray):
        """Update spectrum display."""
        if hasattr(self, "spectrum_curve"):
            freqs = np.linspace(0, self.sample_rate // 2, len(fft_data))
            self.spectrum_curve.setData(freqs, fft_data)

    def clear(self):
        """Clear the display."""
        self.waterfall_data = np.zeros(
            (self.history_size, self.fft_size // 2), dtype=np.float32
        )

        if PYQTGRAPH_AVAILABLE and hasattr(self, "image_item"):
            self.image_item.setImage(
                self.waterfall_data.T, autoLevels=False, levels=(-80, 0)
            )

    def set_sample_rate(self, sample_rate: int):
        """Update sample rate."""
        self.sample_rate = sample_rate
        if self._current_mode == self.MODE_SPECTRUM and hasattr(
            self, "plot_widget"
        ):
            self.plot_widget.setXRange(0, sample_rate // 2)
