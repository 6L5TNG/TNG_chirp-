# -*- coding: utf-8 -*-
"""
MPDA (Multi-Parallel Differential ASK) Protocol Implementation
Modulation and demodulation algorithms.
"""
import numpy as np
from typing import Optional, List, Tuple
from enum import Enum

# Protocol Constants
SAMPLE_RATE = 44100
PILOT_FREQ = 2200
SYNC_BYTE = 0xAA
EOT_BYTE = 0xFF

# Frequency Maps for different track configurations
FREQ_MAP_1_TRACK = {
    "base": 1500,
}

FREQ_MAP_4_TRACKS = {
    0: 800,
    1: 1200,
    2: 1600,
    3: 2000,
}

FREQ_MAP_8_TRACKS = {
    0: 600,
    1: 800,
    2: 1000,
    3: 1200,
    4: 1400,
    5: 1600,
    6: 1800,
    7: 2000,
}


class ReceiverState(Enum):
    """State machine states for MPDA receiver."""
    IDLE = "IDLE"
    SEARCH_PILOT = "SEARCH_PILOT"
    WAIT_END = "WAIT_END"
    DECODE = "DECODE"


def _cosine_interpolation(start_val: float, end_val: float, num_samples: int) -> np.ndarray:
    """
    Generate S-Curve (cosine interpolation) for smooth amplitude transitions.
    This is MANDATORY for spurious suppression.

    Args:
        start_val: Starting amplitude value
        end_val: Ending amplitude value
        num_samples: Number of samples in the transition

    Returns:
        Array of interpolated values following cosine curve
    """
    if num_samples <= 0:
        return np.array([], dtype=np.float32)

    # Cosine interpolation: 0.5 * (1 - cos(pi * t))
    t = np.linspace(0, 1, num_samples, endpoint=True)
    blend = 0.5 * (1.0 - np.cos(np.pi * t))
    return (start_val + (end_val - start_val) * blend).astype(np.float32)


def _generate_tone(
    freq: float,
    duration_samples: int,
    sample_rate: int,
    amplitude: float = 1.0,
    phase: float = 0.0,
) -> Tuple[np.ndarray, float]:
    """
    Generate a pure sine tone.

    Returns:
        Tuple of (samples, end_phase)
    """
    if duration_samples <= 0:
        return np.array([], dtype=np.float32), phase

    t = np.arange(duration_samples) / sample_rate
    samples = (np.sin(2.0 * np.pi * freq * t + phase) * amplitude).astype(np.float32)
    end_phase = (phase + 2.0 * np.pi * freq * duration_samples / sample_rate) % (2.0 * np.pi)
    return samples, end_phase


def _apply_fade(samples: np.ndarray, fade_samples: int) -> np.ndarray:
    """
    Apply cosine fade-in and fade-out to samples.

    Args:
        samples: Audio samples
        fade_samples: Number of samples for fade

    Returns:
        Samples with fades applied
    """
    if len(samples) == 0 or fade_samples <= 0:
        return samples

    fade_samples = min(fade_samples, len(samples) // 2)
    result = samples.copy()

    # Fade in (S-curve)
    fade_in = _cosine_interpolation(0.0, 1.0, fade_samples)
    result[:fade_samples] *= fade_in

    # Fade out (S-curve)
    fade_out = _cosine_interpolation(1.0, 0.0, fade_samples)
    result[-fade_samples:] *= fade_out

    return result


def _get_frequency_map(tracks: int) -> dict:
    """Get frequency map for specified number of tracks."""
    if tracks == 1:
        return FREQ_MAP_1_TRACK
    elif tracks == 4:
        return FREQ_MAP_4_TRACKS
    elif tracks == 8:
        return FREQ_MAP_8_TRACKS
    else:
        return FREQ_MAP_4_TRACKS


def _bytes_to_bits(data: bytes) -> List[int]:
    """Convert bytes to list of bits."""
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_bytes(bits: List[int]) -> bytes:
    """Convert list of bits to bytes."""
    result = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(min(8, len(bits) - i)):
            byte = (byte << 1) | bits[i + j]
        result.append(byte)
    return bytes(result)


class MPDATransmitter:
    """
    MPDA Transmitter class for generating modulated signals.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def generate_signal(
        self,
        text: str,
        tracks: int = 4,
        speed: int = 10,
        amplitude: float = 0.89,  # -1dB normalization
    ) -> np.ndarray:
        """
        Generate MPDA modulated signal from text.

        Args:
            text: Text to encode
            tracks: Number of parallel tracks (1, 4, or 8)
            speed: Transmission speed (5, 10, or 15 symbols/second)
            amplitude: Maximum amplitude (default -1dB = 0.89)

        Returns:
            NumPy array of float32 audio samples
        """
        # Validate parameters
        if tracks not in [1, 4, 8]:
            tracks = 4
        if speed not in [5, 10, 15]:
            speed = 10

        # Calculate symbol duration
        symbol_duration = 1.0 / speed
        symbol_samples = int(symbol_duration * self.sample_rate)

        # Fade samples for S-curve transitions (5% of symbol duration)
        fade_samples = max(1, int(symbol_samples * 0.05))

        # Get frequency map
        freq_map = _get_frequency_map(tracks)

        # Encode text to bytes
        text_bytes = text.encode("utf-8")

        # Build signal parts
        parts = []

        # 1. Pilot tone (500ms)
        pilot_samples = int(0.5 * self.sample_rate)
        pilot, _ = _generate_tone(PILOT_FREQ, pilot_samples, self.sample_rate, amplitude)
        pilot = _apply_fade(pilot, fade_samples)
        parts.append(pilot)

        # 2. Gap after pilot (100ms)
        gap_samples = int(0.1 * self.sample_rate)
        parts.append(np.zeros(gap_samples, dtype=np.float32))

        # 3. Sync byte
        sync_signal = self._encode_byte(SYNC_BYTE, tracks, symbol_samples, fade_samples, freq_map, amplitude)
        parts.append(sync_signal)

        # 4. Data bytes
        for byte in text_bytes:
            byte_signal = self._encode_byte(byte, tracks, symbol_samples, fade_samples, freq_map, amplitude)
            parts.append(byte_signal)
            # Small gap between bytes
            parts.append(np.zeros(int(0.01 * self.sample_rate), dtype=np.float32))

        # 5. EOT byte
        eot_signal = self._encode_byte(EOT_BYTE, tracks, symbol_samples, fade_samples, freq_map, amplitude)
        parts.append(eot_signal)

        # 6. Gap before end beep (100ms)
        parts.append(np.zeros(gap_samples, dtype=np.float32))

        # 7. End beep (two short tones)
        beep_samples = int(0.1 * self.sample_rate)
        beep1, _ = _generate_tone(800, beep_samples, self.sample_rate, amplitude * 0.8)
        beep1 = _apply_fade(beep1, fade_samples)
        beep2, _ = _generate_tone(1200, beep_samples, self.sample_rate, amplitude * 0.8)
        beep2 = _apply_fade(beep2, fade_samples)
        parts.append(beep1)
        parts.append(np.zeros(int(0.05 * self.sample_rate), dtype=np.float32))
        parts.append(beep2)

        # Concatenate all parts
        signal = np.concatenate(parts)

        # Final amplitude normalization to -1dB (0.89)
        peak = np.max(np.abs(signal))
        if peak > 0:
            signal = signal * (amplitude / peak)

        return signal.astype(np.float32)

    def _encode_byte(
        self,
        byte: int,
        tracks: int,
        symbol_samples: int,
        fade_samples: int,
        freq_map: dict,
        amplitude: float,
    ) -> np.ndarray:
        """
        Encode a single byte using MPDA modulation.
        """
        if tracks == 1:
            # Single track ASK modulation
            return self._encode_byte_1track(byte, symbol_samples, fade_samples, freq_map, amplitude)
        else:
            # Multi-track parallel modulation
            return self._encode_byte_multitrack(byte, tracks, symbol_samples, fade_samples, freq_map, amplitude)

    def _encode_byte_1track(
        self,
        byte: int,
        symbol_samples: int,
        fade_samples: int,
        freq_map: dict,
        amplitude: float,
    ) -> np.ndarray:
        """Encode byte using single track ASK."""
        base_freq = freq_map.get("base", 1500)
        parts = []

        for i in range(7, -1, -1):
            bit = (byte >> i) & 1
            amp = amplitude if bit else amplitude * 0.3  # ASK: full/30% amplitude

            tone, _ = _generate_tone(base_freq, symbol_samples, self.sample_rate, amp)
            tone = _apply_fade(tone, fade_samples)
            parts.append(tone)

        return np.concatenate(parts)

    def _encode_byte_multitrack(
        self,
        byte: int,
        tracks: int,
        symbol_samples: int,
        fade_samples: int,
        freq_map: dict,
        amplitude: float,
    ) -> np.ndarray:
        """Encode byte using multi-track parallel modulation."""
        # For 4 tracks, encode 4 bits at a time (2 symbols per byte)
        # For 8 tracks, encode 8 bits at once (1 symbol per byte)

        if tracks == 8:
            # All 8 bits in parallel
            return self._encode_symbol_parallel(byte, tracks, symbol_samples, fade_samples, freq_map, amplitude)
        else:
            # 4 tracks: upper nibble then lower nibble
            upper = (byte >> 4) & 0x0F
            lower = byte & 0x0F

            sym1 = self._encode_symbol_parallel(upper, tracks, symbol_samples, fade_samples, freq_map, amplitude)
            sym2 = self._encode_symbol_parallel(lower, tracks, symbol_samples, fade_samples, freq_map, amplitude)

            return np.concatenate([sym1, sym2])

    def _encode_symbol_parallel(
        self,
        value: int,
        tracks: int,
        symbol_samples: int,
        fade_samples: int,
        freq_map: dict,
        amplitude: float,
    ) -> np.ndarray:
        """Encode a symbol using parallel tones."""
        # Generate multi-tone signal
        signal = np.zeros(symbol_samples, dtype=np.float32)

        for track_idx in range(min(tracks, 8)):
            freq = freq_map.get(track_idx, 1000)
            bit = (value >> (tracks - 1 - track_idx)) & 1 if tracks <= 8 else 0

            # Differential ASK: amplitude varies with bit value
            track_amp = amplitude / tracks if bit else amplitude / tracks * 0.3

            tone, _ = _generate_tone(freq, symbol_samples, self.sample_rate, track_amp)
            signal += tone

        # Apply S-curve fade
        signal = _apply_fade(signal, fade_samples)

        # Normalize
        peak = np.max(np.abs(signal))
        if peak > amplitude:
            signal = signal * (amplitude / peak)

        return signal


class MPDAReceiver:
    """
    MPDA Receiver class for demodulating signals.
    Uses correlation-based demodulation.
    """

    def __init__(self, tracks: int = 4, speed: int = 10, sample_rate: int = SAMPLE_RATE):
        self.tracks = tracks
        self.speed = speed
        self.sample_rate = sample_rate
        self.state = ReceiverState.IDLE
        self._buffer = np.array([], dtype=np.float32)
        self._decoded_bytes = bytearray()
        self._pilot_detected = False

        # Calculate detection thresholds
        self.symbol_samples = int((1.0 / speed) * sample_rate)
        self.pilot_threshold = 0.5
        self.sync_detected = False

    def reset(self):
        """Reset receiver state."""
        self.state = ReceiverState.IDLE
        self._buffer = np.array([], dtype=np.float32)
        self._decoded_bytes = bytearray()
        self._pilot_detected = False
        self.sync_detected = False

    def process_audio(self, audio_chunk: np.ndarray) -> Optional[str]:
        """
        Process incoming audio chunk.

        Args:
            audio_chunk: NumPy array of audio samples

        Returns:
            Decoded text if EOT received, None otherwise.
            Returns "<EOT>" when end of transmission is detected.
        """
        # Add to buffer
        self._buffer = np.concatenate([self._buffer, audio_chunk.astype(np.float32)])

        # Limit buffer size
        max_buffer = self.sample_rate * 5  # 5 seconds max
        if len(self._buffer) > max_buffer:
            self._buffer = self._buffer[-max_buffer:]

        # State machine processing
        if self.state == ReceiverState.IDLE:
            return self._process_idle()
        elif self.state == ReceiverState.SEARCH_PILOT:
            return self._process_search_pilot()
        elif self.state == ReceiverState.WAIT_END:
            return self._process_wait_end()
        elif self.state == ReceiverState.DECODE:
            return self._process_decode()

        return None

    def _process_idle(self) -> Optional[str]:
        """Process in IDLE state - looking for pilot tone."""
        # Check for pilot tone presence
        if len(self._buffer) < self.sample_rate * 0.1:
            return None

        # Detect pilot frequency using Goertzel algorithm
        pilot_power = self._goertzel_power(self._buffer[-int(self.sample_rate * 0.1):], PILOT_FREQ)

        if pilot_power > self.pilot_threshold:
            self.state = ReceiverState.SEARCH_PILOT
            self._pilot_detected = True

        return None

    def _process_search_pilot(self) -> Optional[str]:
        """Process in SEARCH_PILOT state - waiting for pilot to end."""
        if len(self._buffer) < self.sample_rate * 0.1:
            return None

        # Check if pilot has ended
        pilot_power = self._goertzel_power(self._buffer[-int(self.sample_rate * 0.1):], PILOT_FREQ)

        if pilot_power < self.pilot_threshold * 0.5:
            # Pilot ended, look for sync byte
            self.state = ReceiverState.DECODE
            self._buffer = np.array([], dtype=np.float32)

        return None

    def _process_wait_end(self) -> Optional[str]:
        """Process in WAIT_END state."""
        return None

    def _process_decode(self) -> Optional[str]:
        """Process in DECODE state - decoding data symbols."""
        # Need enough samples for at least one symbol
        required_samples = self.symbol_samples * (2 if self.tracks == 4 else 1)

        while len(self._buffer) >= required_samples:
            # Extract symbol samples
            symbol_data = self._buffer[:required_samples]
            self._buffer = self._buffer[required_samples:]

            # Decode byte
            decoded_byte = self._decode_byte(symbol_data)

            if decoded_byte == SYNC_BYTE and not self.sync_detected:
                self.sync_detected = True
                continue

            if decoded_byte == EOT_BYTE:
                # End of transmission
                result = self._decoded_bytes.decode("utf-8", errors="replace")
                self.reset()
                return "<EOT>"

            if self.sync_detected:
                self._decoded_bytes.append(decoded_byte)

        return None

    def _decode_byte(self, samples: np.ndarray) -> int:
        """Decode a byte from samples."""
        freq_map = _get_frequency_map(self.tracks)

        if self.tracks == 1:
            return self._decode_byte_1track(samples, freq_map)
        elif self.tracks == 4:
            return self._decode_byte_4track(samples, freq_map)
        else:  # 8 tracks
            return self._decode_byte_8track(samples, freq_map)

    def _decode_byte_1track(self, samples: np.ndarray, freq_map: dict) -> int:
        """Decode byte from single track ASK."""
        base_freq = freq_map.get("base", 1500)
        samples_per_bit = len(samples) // 8
        byte_value = 0

        for i in range(8):
            start = i * samples_per_bit
            end = start + samples_per_bit
            bit_samples = samples[start:end]

            power = self._goertzel_power(bit_samples, base_freq)
            bit = 1 if power > 0.5 else 0
            byte_value = (byte_value << 1) | bit

        return byte_value

    def _decode_byte_4track(self, samples: np.ndarray, freq_map: dict) -> int:
        """Decode byte from 4-track parallel modulation."""
        symbol_samples = len(samples) // 2

        # Decode upper nibble
        upper_samples = samples[:symbol_samples]
        upper = self._decode_nibble(upper_samples, freq_map, 4)

        # Decode lower nibble
        lower_samples = samples[symbol_samples:]
        lower = self._decode_nibble(lower_samples, freq_map, 4)

        return (upper << 4) | lower

    def _decode_byte_8track(self, samples: np.ndarray, freq_map: dict) -> int:
        """Decode byte from 8-track parallel modulation."""
        return self._decode_nibble(samples, freq_map, 8)

    def _decode_nibble(self, samples: np.ndarray, freq_map: dict, tracks: int) -> int:
        """Decode a nibble from parallel tones."""
        value = 0

        for track_idx in range(tracks):
            freq = freq_map.get(track_idx, 1000)
            power = self._goertzel_power(samples, freq)
            bit = 1 if power > 0.3 else 0
            value = (value << 1) | bit

        return value

    def _goertzel_power(self, samples: np.ndarray, freq: float) -> float:
        """
        Calculate power at specific frequency using Goertzel algorithm.
        More efficient than FFT for single frequency detection.
        """
        if len(samples) == 0:
            return 0.0

        N = len(samples)
        k = int(0.5 + (N * freq) / self.sample_rate)
        omega = 2.0 * np.pi * k / N
        coeff = 2.0 * np.cos(omega)

        s0 = 0.0
        s1 = 0.0
        s2 = 0.0

        for sample in samples:
            s0 = sample + coeff * s1 - s2
            s2 = s1
            s1 = s0

        power = s1 * s1 + s2 * s2 - coeff * s1 * s2
        # Normalize
        return power / (N * N)

    def get_decoded_text(self) -> str:
        """Get currently decoded text."""
        return self._decoded_bytes.decode("utf-8", errors="replace")

    def get_state(self) -> str:
        """Get current receiver state as string."""
        return self.state.value
