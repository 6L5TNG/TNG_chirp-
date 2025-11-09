# Unified settings with user waterfall presets + FPS.
import json, os
from typing import Dict, Any
from .presets import DEFAULT_PRESETS

SETTINGS_FILE = "ssb_chirp_settings.json"

WF_PRESETS = {
    "LowCPU": {
        "wf_fps": 6,
        "wf_max_rows": 180,
        "wf_nperseg": 256,
        "wf_noverlap": 128,
        "wf_drange_db": 50.0,
        "wf_colormap": "plasma"
    },
    "Standard": {
        "wf_fps": 12,
        "wf_max_rows": 240,
        "wf_nperseg": 512,
        "wf_noverlap": 384,
        "wf_drange_db": 60.0,
        "wf_colormap": "magma"
    },
    "HighRes": {
        "wf_fps": 18,
        "wf_max_rows": 300,
        "wf_nperseg": 1024,
        "wf_noverlap": 768,
        "wf_drange_db": 70.0,
        "wf_colormap": "inferno"
    }
}

def _defaults() -> Dict[str, Any]:
    base = WF_PRESETS["Standard"].copy()
    return {
        "language": "ko",
        "theme": "light",
        "callsign": "",
        "grid": "",
        "sr": 48000,
        "audio_input_index": None,
        "audio_output_index": None,

        # View waterfall
        "max_freq": 3000,
        "colormap": "magma",
        "drange_db": 60.0,
        "waterfall_quality": "light",

        # Live waterfall advanced
        "wf_preset": "Standard",
        **base,
        "wf_user_presets": {},

        # Legacy compatibility
        "wf_chunk_seconds": 0.4,

        # Amplitudes
        "amp": 0.8,
        "beep_amp": 0.7,

        # Speed presets
        "preset_slow": DEFAULT_PRESETS["Slow"],
        "preset_normal": DEFAULT_PRESETS["Normal"],
        "preset_fast": DEFAULT_PRESETS["Fast"],
        "preset_veryfast": DEFAULT_PRESETS["VeryFast"],
        "default_preset": "Normal",
        "slider_dur_ms": DEFAULT_PRESETS["Normal"][0]*1000.0,
        "slider_gap_ms": DEFAULT_PRESETS["Normal"][1]*1000.0,

        # Beeps
        "start_beep": "250:400:250",
        "end_beep": "250:400:250,100:300:250",
        "enable_beeps": True,
        "link_beeps_speed": True,

        # Signature
        "enable_signature": True,
        "signature_mode": "chirp_bounce",
        "signature_ms": 180.0,
        "signature_repeats": 2,
        "signature_low_hz": 600.0,
        "signature_high_hz": 1200.0,

        # Marker
        "enable_marker": True,
        "marker_mode": "simul",
        "marker_low_hz": 300.0,
        "marker_high_hz": 1500.0,
        "marker_tone_ms": 350.0,
        "marker_gap_ms": 120.0,
        "marker_repeats": 2,
        "link_sig_marker_speed": True,

        # Log
        "show_log_timestamp": True,
        "log_font_size": 11,
        "log_autoscroll": True,
    }

def load_settings(path: str = SETTINGS_FILE) -> Dict[str, Any]:
    cfg = _defaults()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                disk = json.load(f)

            # Convert chunk_seconds -> fps
            if "wf_fps" not in disk:
                chunk = disk.get("wf_chunk_seconds", cfg["wf_chunk_seconds"])
                try:
                    fps = int(round(1.0/float(chunk))) if chunk > 0 else cfg["wf_fps"]
                    fps = max(4, min(30, fps))
                except Exception:
                    fps = cfg["wf_fps"]
                disk["wf_fps"] = fps

            if "wf_user_presets" not in disk or not isinstance(disk["wf_user_presets"], dict):
                disk["wf_user_presets"] = {}

            for k,v in cfg.items():
                if k not in disk:
                    disk[k] = v

            preset = disk.get("wf_preset","Standard")
            if preset in WF_PRESETS:
                for pk,pv in WF_PRESETS[preset].items():
                    if pk not in disk:
                        disk[pk] = pv

            cfg.update(disk)
        except Exception:
            pass
    return cfg

def save_settings(cfg: Dict[str, Any], path: str = SETTINGS_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
