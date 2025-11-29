# -*- coding: utf-8 -*-
"""
MPDA Audio Engine
QThread-based real-time audio streaming using sounddevice OutputStream.
Uses stream.write(chunk) for TX (no sd.play()!).
"""
import numpy as np
import sounddevice as sd
from typing import Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal


class AudioEngine(QThread):
    """
    QThread-based audio streaming engine for transmitting audio.
    Uses OutputStream.write(chunk) for chunk-based transmission.
    Allows real-time gain adjustment via current_gain.
    """

    # Signals
    progress = pyqtSignal(float)  # Progress 0.0 - 1.0
    finished = pyqtSignal()
    error = pyqtSignal(str)
    level_update = pyqtSignal(float)  # RMS level in dB

    def __init__(
        self,
        samples: np.ndarray,
        sample_rate: int = 44100,
        device: Optional[int] = None,
        chunk_size: int = 1024,
        parent=None,
    ):
        super().__init__(parent)
        self.samples = samples.astype(np.float32)
        self.sample_rate = sample_rate
        self.device = device
        self.chunk_size = chunk_size
        self._current_gain = 1.0
        self._stop_flag = False
        self._stream: Optional[sd.OutputStream] = None

    @property
    def current_gain(self) -> float:
        """Get current gain value."""
        return self._current_gain

    @current_gain.setter
    def current_gain(self, value: float):
        """Set gain value for real-time volume adjustment (0.0 - 2.0)."""
        self._current_gain = max(0.0, min(2.0, value))

    def stop(self):
        """Request stop of audio playback."""
        self._stop_flag = True

    def run(self):
        """Thread main function - stream audio chunks."""
        try:
            total_samples = len(self.samples)
            if total_samples == 0:
                self.finished.emit()
                return

            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device,
                blocksize=self.chunk_size,
            )

            with self._stream:
                index = 0
                while index < total_samples and not self._stop_flag:
                    end_index = min(index + self.chunk_size, total_samples)
                    chunk = self.samples[index:end_index].copy()

                    # Apply real-time gain
                    chunk *= self._current_gain

                    # Clip to prevent distortion
                    chunk = np.clip(chunk, -1.0, 1.0)

                    # Calculate RMS level
                    if len(chunk) > 0:
                        rms = np.sqrt(np.mean(chunk**2))
                        db = 20.0 * np.log10(max(rms, 1e-10))
                        self.level_update.emit(db)

                    # Write chunk to stream
                    self._stream.write(chunk.reshape(-1, 1))

                    # Update progress
                    progress = end_index / total_samples
                    self.progress.emit(progress)

                    index = end_index

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def cleanup(self):
        """Clean up resources."""
        self._stop_flag = True
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None


class TuneGenerator(QThread):
    """
    Continuous tune tone generator.
    Outputs 1500Hz sine wave for TUNE mode.
    """

    level_update = pyqtSignal(float)
    error = pyqtSignal(str)

    TUNE_FREQUENCY = 1500.0  # Hz

    def __init__(
        self,
        sample_rate: int = 44100,
        device: Optional[int] = None,
        amplitude: float = 0.8,
        parent=None,
    ):
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.device = device
        self._amplitude = amplitude
        self._stop_flag = False
        self._stream: Optional[sd.OutputStream] = None
        self._phase = 0.0

    @property
    def amplitude(self) -> float:
        """Get current amplitude."""
        return self._amplitude

    @amplitude.setter
    def amplitude(self, value: float):
        """Set amplitude for real-time adjustment (0.0 - 1.0)."""
        self._amplitude = max(0.0, min(1.0, value))

    def stop(self):
        """Request stop of tune tone."""
        self._stop_flag = True

    def run(self):
        """Thread main function - generate continuous tune tone."""
        chunk_size = 1024
        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device,
                blocksize=chunk_size,
            )

            with self._stream:
                while not self._stop_flag:
                    # Generate sine wave chunk
                    t = (np.arange(chunk_size) + self._phase) / self.sample_rate
                    chunk = (
                        np.sin(2.0 * np.pi * self.TUNE_FREQUENCY * t) * self._amplitude
                    ).astype(np.float32)

                    # Update phase for continuity
                    self._phase = (self._phase + chunk_size) % self.sample_rate

                    # Calculate RMS level
                    rms = np.sqrt(np.mean(chunk**2))
                    db = 20.0 * np.log10(max(rms, 1e-10))
                    self.level_update.emit(db)

                    # Write to stream
                    self._stream.write(chunk.reshape(-1, 1))

        except Exception as e:
            self.error.emit(str(e))

    def cleanup(self):
        """Clean up resources."""
        self._stop_flag = True
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None


class AudioInputMonitor(QThread):
    """
    Audio input monitoring thread for RX level display.
    """

    level_update = pyqtSignal(float)  # RMS level in dB
    samples_ready = pyqtSignal(np.ndarray)  # Raw samples for processing
    error = pyqtSignal(str)

    def __init__(
        self,
        sample_rate: int = 44100,
        device: Optional[int] = None,
        chunk_size: int = 1024,
        parent=None,
    ):
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.device = device
        self.chunk_size = chunk_size
        self._stop_flag = False
        self._stream: Optional[sd.InputStream] = None
        self._gain = 1.0

    @property
    def gain(self) -> float:
        """Get current RX gain."""
        return self._gain

    @gain.setter
    def gain(self, value: float):
        """Set RX gain (0.0 - 2.0)."""
        self._gain = max(0.0, min(2.0, value))

    def stop(self):
        """Request stop of monitoring."""
        self._stop_flag = True

    def run(self):
        """Thread main function - monitor audio input."""
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device,
                blocksize=self.chunk_size,
            )

            with self._stream:
                while not self._stop_flag:
                    data, overflowed = self._stream.read(self.chunk_size)
                    if data.size > 0:
                        samples = data[:, 0].astype(np.float32) * self._gain

                        # Calculate RMS level
                        rms = np.sqrt(np.mean(samples**2))
                        db = 20.0 * np.log10(max(rms, 1e-10))
                        self.level_update.emit(db)

                        # Emit samples for processing
                        self.samples_ready.emit(samples)

        except Exception as e:
            self.error.emit(str(e))

    def cleanup(self):
        """Clean up resources."""
        self._stop_flag = True
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None


def get_audio_devices(filter_mme: bool = True):
    """
    Get list of audio devices.

    Args:
        filter_mme: If True, only return Windows MME devices.

    Returns:
        Tuple of (input_devices, output_devices) where each is a list of
        (index, name) tuples.
    """
    try:
        devices = sd.query_devices()
        host_apis = sd.query_hostapis()

        # Build host API name lookup
        api_names = {i: api["name"] for i, api in enumerate(host_apis)}

        input_devices = []
        output_devices = []

        for idx, dev in enumerate(devices):
            api_name = api_names.get(dev.get("hostapi", -1), "")

            # Filter for MME on Windows if requested
            if filter_mme and "MME" not in api_name:
                continue

            name = dev.get("name", f"Device {idx}")
            if dev.get("max_input_channels", 0) > 0:
                input_devices.append((idx, name))
            if dev.get("max_output_channels", 0) > 0:
                output_devices.append((idx, name))

        return input_devices, output_devices

    except Exception:
        return [], []
