from typing import List
import numpy as np
from scipy.signal import chirp
from .chirpmap import CHIRP_MAP

def _fade_window(N: int, fade_samples: int) -> np.ndarray:
    if fade_samples <= 0:
        return np.ones(N, dtype=np.float32)
    fade_samples = min(fade_samples, N // 2)
    if fade_samples <= 0:
        return np.ones(N, dtype=np.float32)
    ramp = 0.5 * (1.0 - np.cos(np.pi * np.linspace(0.0, 1.0, fade_samples)))
    win = np.ones(N, dtype=np.float32)
    win[:fade_samples] = ramp
    win[-fade_samples:] = ramp[::-1]
    return win

def make_single_chirp(f_start: float, f_end: float, duration: float, sr: int, fade_ms: float = 3.0) -> np.ndarray:
    N = int(round(duration * sr))
    if N <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.linspace(0.0, duration, N, endpoint=False)
    if abs(f_start - f_end) < 1e-6:
        sig = np.sin(2.0 * np.pi * f_start * t).astype(np.float32)
    else:
        sig = chirp(t, f_start, duration, f_end, method="linear").astype(np.float32)
    win = _fade_window(N, int(round((fade_ms/1000.0)*sr)))
    sig = (sig * win).astype(np.float32)
    m = float(np.max(np.abs(sig))) or 1.0
    return (sig / m).astype(np.float32)

def make_sine_tone(freq: float, duration: float, sr: int, amp: float = 1.0, fade_ms: float = 4.0) -> np.ndarray:
    N = int(round(duration * sr))
    if N <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.linspace(0.0, duration, N, endpoint=False)
    sig = (np.sin(2.0 * np.pi * freq * t) * float(amp)).astype(np.float32)
    win = _fade_window(N, int(round((fade_ms/1000.0)*sr)))
    return (sig * win).astype(np.float32)

def make_dual_tone(freqs: List[float], duration: float, sr: int, fade_ms: float = 5.0, amp: float = 1.0) -> np.ndarray:
    N = int(round(duration * sr))
    if N <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.linspace(0.0, duration, N, endpoint=False)
    sig = np.zeros(N, dtype=np.float32)
    for f in freqs:
        sig += np.sin(2.0 * np.pi * f * t).astype(np.float32)
    peak = float(np.max(np.abs(sig))) or 1.0
    if peak > 0:
        sig = sig / peak
    sig *= float(amp)
    win = _fade_window(N, int(round((fade_ms/1000.0)*sr)))
    return (sig * win).astype(np.float32)

def text_to_wave(text: str, sr: int, duration: float, gap: float, amplitude: float,
                 direction: str = "up", preamble: int = 0) -> np.ndarray:
    gap_samples = int(round(sr * gap))
    gap_wave = np.zeros(gap_samples, dtype=np.float32)
    pieces: List[np.ndarray] = []
    for _ in range(preamble):
        f0, f1 = CHIRP_MAP.get(" ", next(iter(CHIRP_MAP.values())))
        pieces.append(make_single_chirp(f0, f1, duration, sr))
        pieces.append(gap_wave)
    for ch in text:
        key = ch if ch in CHIRP_MAP else ch.upper()
        if key not in CHIRP_MAP:
            continue
        f0, f1 = CHIRP_MAP[key]
        sig = make_single_chirp(f0, f1, duration, sr) if direction == "up" else make_single_chirp(f1, f0, duration, sr)
        pieces.append(sig * float(amplitude))
        pieces.append(gap_wave)
    if not pieces:
        return np.zeros(0, dtype=np.float32)
    out = np.concatenate(pieces).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    if peak > 1.0:
        out = out / peak * 0.99
    return out
