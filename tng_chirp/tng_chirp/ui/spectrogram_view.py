import numpy as np
from scipy.signal import spectrogram
from typing import Optional

def compute_spectrogram(samples: np.ndarray, sr: int, max_freq: int, quality: str):
    quality = (quality or "light").lower()
    if quality == "off":
        return None, None, None, sr
    if quality == "light":
        target_sr = 16000
        decim = max(1, int(sr // target_sr))
    else:
        decim = 1
    samp = samples[::decim] if decim > 1 else samples
    sr_eff = sr // decim if decim > 1 else sr
    nperseg = 1024 if sr_eff >= 32000 else 512
    if quality == "light":
        nperseg = max(256, nperseg // 2)
    noverlap = int(nperseg * 0.75)
    f, t, Sxx = spectrogram(samp, fs=sr_eff, window='hann',
                            nperseg=nperseg, noverlap=noverlap, mode='magnitude')
    Sxx_db = 20.0 * np.log10(Sxx + 1e-12)
    freq_mask = f <= max(100, int(max_freq))
    if not freq_mask.any():
        freq_mask = np.ones_like(f, dtype=bool)
    return f[freq_mask], t, Sxx_db[freq_mask, :], sr_eff

def draw_program_waterfall(ax, f: Optional[np.ndarray], t: Optional[np.ndarray], Sxx_db: Optional[np.ndarray],
                           max_freq: int, cmap: str, drange_db: float, theme: str = "dark"):
    ax.clear()
    if f is None or t is None or Sxx_db is None:
        ax.set_title("Waterfall (disabled)")
        return
    f_min = float(f[0]) if len(f) else 0.0
    f_max = float(f[-1]) if len(f) else max_freq
    t_min = float(t[0]) if len(t) else 0.0
    t_max = float(t[-1]) if len(t) else 0.0
    vmin = float(Sxx_db.max()) - float(drange_db)
    vmax = float(Sxx_db.max())
    ax.imshow(Sxx_db.T, aspect='auto', origin='lower', interpolation='nearest',
              extent=[f_min, f_max, t_min, t_max], cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xlim(0, max_freq)
    ax.set_xlabel(""); ax.set_ylabel(""); ax.set_title("")
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for s in ax.spines.values():
        s.set_visible(False)
    try:
        trans = ax.get_xaxis_transform()
        step = 1000 if max_freq > 3500 else (500 if max_freq > 1500 else 250)
        for xf in range(0, max_freq + 1, step):
            ax.text(xf, 1.02, f"{xf}", transform=trans, color="#BBBBBB",
                    fontsize=8, ha="center", va="bottom")
    except Exception:
        pass
    try:
        ax.invert_yaxis()
    except Exception:
        pass
