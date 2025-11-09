from typing import List, Tuple
import numpy as np
from .synth import make_dual_tone

def parse_beep_spec_ms(spec: str) -> List[Tuple[float, float, float]]:
    seq = []
    if not spec:
        return seq
    for part in spec.split(","):
        p = part.strip()
        if not p:
            continue
        fields = p.split(":")
        if len(fields) != 3:
            continue
        try:
            f0 = float(fields[0]); f1 = float(fields[1]); dur = float(fields[2])
            if dur > 10:
                dur = dur / 1000.0
            seq.append((f0, f1, dur))
        except Exception:
            continue
    return seq

def build_beeps_sequence(seq: List[Tuple[float, float, float]], sr: int, amp: float, speed_scale: float = 1.0) -> np.ndarray:
    parts = []
    scale = float(speed_scale) if speed_scale > 0 else 1.0
    for (f0, f1, d) in seq:
        dur = float(d) * scale
        freqs = [f0] if abs(f0 - f1) < 1e-8 else [f0, f1]
        parts.append(make_dual_tone(freqs, dur, sr, amp=amp))
        parts.append(np.zeros(int(round(0.01 * sr)), dtype=np.float32))
    if not parts:
        return np.zeros(0, dtype=np.float32)
    out = np.concatenate(parts).astype(np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    if peak > 1.0:
        out = out / peak * 0.99
    return out
