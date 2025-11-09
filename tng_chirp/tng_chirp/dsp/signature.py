import numpy as np
from .synth import make_single_chirp, make_dual_tone

def build_signature_sequence(settings: dict, sr: int, amp: float, speed_scale: float) -> np.ndarray:
    if not settings.get("enable_signature", True):
        return np.zeros(0, dtype=np.float32)
    mode = settings.get("signature_mode", "chirp_bounce")
    fL = float(settings.get("signature_low_hz", 600.0))
    fH = float(settings.get("signature_high_hz", 1200.0))
    dur = float(settings.get("signature_ms", 180.0)) / 1000.0
    if settings.get("link_sig_marker_speed", True):
        dur *= speed_scale
    rep = int(settings.get("signature_repeats", 2))
    parts = []
    if mode == "chirp_bounce":
        for _ in range(max(1, rep)):
            parts.append(make_single_chirp(fL, fH, dur, sr))
            parts.append(np.zeros(int(round(0.06*sr)), dtype=np.float32))
            parts.append(make_single_chirp(fH, fL, dur, sr))
            parts.append(np.zeros(int(round(0.06*sr)), dtype=np.float32))
    else:
        for _ in range(max(1, rep)):
            parts.append(make_dual_tone([fL, fH], dur, sr, amp=amp))
            parts.append(np.zeros(int(round(0.06*sr)), dtype=np.float32))
    if not parts:
        return np.zeros(0, dtype=np.float32)
    out = np.concatenate(parts).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    if peak > 1.0: out = out/peak*0.99
    return out
