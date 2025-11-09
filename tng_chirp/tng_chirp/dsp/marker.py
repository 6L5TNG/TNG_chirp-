import numpy as np
from .synth import make_sine_tone, make_dual_tone

def build_marker_sequence(settings: dict, sr: int, amp: float, speed_scale: float) -> np.ndarray:
    if not settings.get("enable_marker", True):
        return np.zeros(0, dtype=np.float32)
    mode = settings.get("marker_mode", "simul")
    fL = float(settings.get("marker_low_hz", 300.0))
    fH = float(settings.get("marker_high_hz", 1500.0))
    tone_d = float(settings.get("marker_tone_ms", 350.0)) / 1000.0
    gap_d  = float(settings.get("marker_gap_ms", 120.0)) / 1000.0
    if settings.get("link_sig_marker_speed", True):
        tone_d *= speed_scale
        gap_d  *= speed_scale
    rep = int(settings.get("marker_repeats", 2))
    gap = np.zeros(int(round(gap_d * sr)), dtype=np.float32)
    parts = []
    for _ in range(max(1, rep)):
        if mode == "simul":
            parts.append(make_dual_tone([fL, fH], tone_d, sr, amp=amp))
            parts.append(gap)
        else:
            parts.append(make_sine_tone(fL, tone_d, sr, amp=amp)); parts.append(gap)
            parts.append(make_sine_tone(fH, tone_d, sr, amp=amp)); parts.append(gap)
    if not parts:
        return np.zeros(0, dtype=np.float32)
    out = np.concatenate(parts).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    if peak > 1.0: out = out/peak*0.99
    return out
