import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
from tng_chirp.core.settings import save_settings
from tng_chirp.core.presets import DEFAULT_PRESETS

class TransmitAdvancedDialog(tk.Toplevel):
    """
    Advanced Transmit (TNG_Chirp) settings: presets dur/gap, signature, marker, beeps, links.
    """
    def __init__(self, parent, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.settings = settings
        self.title("TNG_Chirp Transmit Settings")
        self.geometry("620x640")
        self.resizable(False, False)

        self._build_ui()
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def _build_ui(self):
        main = ttk.Frame(self); main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Default preset
        top = ttk.Frame(main); top.pack(fill=tk.X)
        ttk.Label(top, text="Default preset:").grid(row=0,column=0,sticky="e",padx=4,pady=4)
        self.default_preset_var = tk.StringVar(value=self.settings.get("default_preset","Normal"))
        ttk.Combobox(top, values=["Slow","Normal","Fast","VeryFast"], textvariable=self.default_preset_var,
                     state="readonly", width=12).grid(row=0,column=1,sticky="w",padx=4,pady=4)
        ttk.Button(top, text="Apply Preset Now", command=self._apply_current_default_to_sliders)\
            .grid(row=0,column=2,sticky="w",padx=8,pady=4)

        # Preset durations
        pf = ttk.LabelFrame(main, text="Preset durations (s) / gaps (s)")
        pf.pack(fill=tk.X, padx=4, pady=8)

        def row(label,key_default,key,row):
            val = self.settings.get(key, DEFAULT_PRESETS.get(key_default, DEFAULT_PRESETS["Normal"]))
            dur_var = tk.DoubleVar(value=val[0])
            gap_var = tk.DoubleVar(value=val[1])
            ttk.Label(pf, text=label).grid(row=row,column=0,sticky="e",padx=6,pady=4)
            ttk.Entry(pf, textvariable=dur_var, width=8).grid(row=row,column=1,sticky="w",padx=(6,2),pady=4)
            ttk.Entry(pf, textvariable=gap_var, width=8).grid(row=row,column=2,sticky="w",padx=(2,6),pady=4)
            return dur_var, gap_var

        self.slow_dur_var,self.slow_gap_var = row("Slow","Slow","preset_slow",0)
        self.norm_dur_var,self.norm_gap_var = row("Normal","Normal","preset_normal",1)
        self.fast_dur_var,self.fast_gap_var = row("Fast","Fast","preset_fast",2)
        self.vfast_dur_var,self.vfast_gap_var = row("VeryFast","VeryFast","preset_veryfast",3)

        # Live slider overrides
        lf = ttk.LabelFrame(main, text="Live slider overrides")
        lf.pack(fill=tk.X, padx=4, pady=8)
        ttk.Label(lf, text="Symbol duration (ms):").grid(row=0,column=0,sticky="e",padx=6,pady=4)
        self.slider_dur_var = tk.DoubleVar(value=self.settings.get("slider_dur_ms",60.0))
        ttk.Entry(lf, textvariable=self.slider_dur_var, width=10).grid(row=0,column=1,sticky="w",padx=6,pady=4)

        ttk.Label(lf, text="Gap (ms):").grid(row=1,column=0,sticky="e",padx=6,pady=4)
        self.slider_gap_var = tk.DoubleVar(value=self.settings.get("slider_gap_ms",8.0))
        ttk.Entry(lf, textvariable=self.slider_gap_var, width=10).grid(row=1,column=1,sticky="w",padx=6,pady=4)

        # Beeps
        bf = ttk.LabelFrame(main, text="Beeps")
        bf.pack(fill=tk.X, padx=4, pady=8)
        self.enable_beeps_var = tk.BooleanVar(value=self.settings.get("enable_beeps",True))
        ttk.Checkbutton(bf, text="Enable pre/post beeps", variable=self.enable_beeps_var)\
            .grid(row=0,column=0,sticky="w",padx=6,pady=4)
        ttk.Label(bf, text="Start beep (f0:f1:dur_ms):").grid(row=1,column=0,sticky="e",padx=6,pady=4)
        self.start_beep_entry = ttk.Entry(bf, width=38)
        self.start_beep_entry.insert(0,self.settings.get("start_beep","250:400:250"))
        self.start_beep_entry.grid(row=1,column=1,sticky="w",padx=6,pady=4)
        ttk.Label(bf, text="End beep (comma-sep):").grid(row=2,column=0,sticky="e",padx=6,pady=4)
        self.end_beep_entry = ttk.Entry(bf, width=38)
        self.end_beep_entry.insert(0,self.settings.get("end_beep","250:400:250,100:300:250"))
        self.end_beep_entry.grid(row=2,column=1,sticky="w",padx=6,pady=4)

        self.link_beeps_var = tk.BooleanVar(value=self.settings.get("link_beeps_speed",True))
        ttk.Checkbutton(bf, text="Link beep speed to preset", variable=self.link_beeps_var)\
            .grid(row=3,column=0,columnspan=2,sticky="w",padx=6,pady=4)

        # Signature
        sf = ttk.LabelFrame(main, text="Recognition signature")
        sf.pack(fill=tk.X, padx=4, pady=8)
        self.enable_signature_var = tk.BooleanVar(value=self.settings.get("enable_signature",True))
        ttk.Checkbutton(sf, text="Enable signature", variable=self.enable_signature_var)\
            .grid(row=0,column=0,sticky="w",padx=6,pady=4)
        ttk.Label(sf, text="Mode:").grid(row=0,column=1,sticky="e",padx=6,pady=4)
        self.signature_mode_var = tk.StringVar(value=self.settings.get("signature_mode","chirp_bounce"))
        ttk.Combobox(sf, values=["chirp_bounce","dual_pulse"], state="readonly",
                     textvariable=self.signature_mode_var, width=14)\
            .grid(row=0,column=2,sticky="w",padx=6,pady=4)

        self.sig_low_var = tk.DoubleVar(value=self.settings.get("signature_low_hz",600.0))
        self.sig_high_var = tk.DoubleVar(value=self.settings.get("signature_high_hz",1200.0))
        self.sig_ms_var = tk.DoubleVar(value=self.settings.get("signature_ms",180.0))
        self.sig_repeats_var = tk.IntVar(value=self.settings.get("signature_repeats",2))

        lab_pairs = [
            ("Low Hz:", self.sig_low_var),
            ("High Hz:", self.sig_high_var),
            ("Tone ms:", self.sig_ms_var),
            ("Repeats:", self.sig_repeats_var),
        ]
        r = 1
        for label,var in lab_pairs:
            ttk.Label(sf, text=label).grid(row=r,column=0,sticky="e",padx=6,pady=4)
            w = ttk.Entry(sf, textvariable=var, width=10)
            w.grid(row=r,column=1,sticky="w",padx=6,pady=4)
            r += 1

        # Marker
        mf = ttk.LabelFrame(main, text="Frequency marker")
        mf.pack(fill=tk.X, padx=4, pady=8)
        self.enable_marker_var = tk.BooleanVar(value=self.settings.get("enable_marker",True))
        ttk.Checkbutton(mf, text="Enable marker", variable=self.enable_marker_var)\
            .grid(row=0,column=0,sticky="w",padx=6,pady=4)
        ttk.Label(mf, text="Mode:").grid(row=0,column=1,sticky="e",padx=6,pady=4)
        self.marker_mode_var = tk.StringVar(value=self.settings.get("marker_mode","simul"))
        ttk.Combobox(mf, values=["simul","seq"], state="readonly",
                     textvariable=self.marker_mode_var, width=10)\
            .grid(row=0,column=2,sticky="w",padx=6,pady=4)

        self.marker_low_var = tk.DoubleVar(value=self.settings.get("marker_low_hz",300.0))
        self.marker_high_var = tk.DoubleVar(value=self.settings.get("marker_high_hz",1500.0))
        self.marker_tone_ms_var = tk.DoubleVar(value=self.settings.get("marker_tone_ms",350.0))
        self.marker_gap_ms_var = tk.DoubleVar(value=self.settings.get("marker_gap_ms",120.0))
        self.marker_repeats_var = tk.IntVar(value=self.settings.get("marker_repeats",2))

        rows = [
            ("Low Hz:", self.marker_low_var),
            ("High Hz:", self.marker_high_var),
            ("Tone ms:", self.marker_tone_ms_var),
            ("Gap ms:", self.marker_gap_ms_var),
            ("Repeats:", self.marker_repeats_var),
        ]
        rr = 1
        for label,var in rows:
            ttk.Label(mf, text=label).grid(row=rr,column=0,sticky="e",padx=6,pady=4)
            ttk.Entry(mf, textvariable=var, width=10).grid(row=rr,column=1,sticky="w",padx=6,pady=4)
            rr += 1

        # Linking signature/marker speed
        linkf = ttk.LabelFrame(main, text="Link speeds")
        linkf.pack(fill=tk.X, padx=4, pady=8)
        self.link_sig_marker_var = tk.BooleanVar(value=self.settings.get("link_sig_marker_speed",True))
        ttk.Checkbutton(linkf, text="Link signature/marker speed to preset", variable=self.link_sig_marker_var)\
            .grid(row=0,column=0,sticky="w",padx=6,pady=4)

        # Buttons
        btn_line = ttk.Frame(main)
        btn_line.pack(fill=tk.X, pady=10)
        ttk.Button(btn_line, text="Save", width=10, command=self._on_save).pack(side=tk.LEFT,padx=4)
        ttk.Button(btn_line, text="Cancel", width=10, command=self.destroy).pack(side=tk.RIGHT,padx=4)

    def _apply_current_default_to_sliders(self):
        preset = self.default_preset_var.get()
        key_map = {
            "Slow": self.slow_dur_var,
            "Normal": self.norm_dur_var,
            "Fast": self.fast_dur_var,
            "VeryFast": self.vfast_dur_var,
        }
        gap_map = {
            "Slow": self.slow_gap_var,
            "Normal": self.norm_gap_var,
            "Fast": self.fast_gap_var,
            "VeryFast": self.vfast_gap_var,
        }
        if preset in key_map:
            self.slider_dur_var.set(key_map[preset].get() * 1000.0)
            self.slider_gap_var.set(gap_map[preset].get() * 1000.0)
            messagebox.showinfo("Preset","Applied to slider_dur_ms / slider_gap_ms")

    def _on_save(self):
        try:
            # Preset durations
            self.settings["preset_slow"] = (float(self.slow_dur_var.get()), float(self.slow_gap_var.get()))
            self.settings["preset_normal"] = (float(self.norm_dur_var.get()), float(self.norm_gap_var.get()))
            self.settings["preset_fast"] = (float(self.fast_dur_var.get()), float(self.fast_gap_var.get()))
            self.settings["preset_veryfast"] = (float(self.vfast_dur_var.get()), float(self.vfast_gap_var.get()))

            self.settings["default_preset"] = self.default_preset_var.get()
            self.settings["slider_dur_ms"] = float(self.slider_dur_var.get())
            self.settings["slider_gap_ms"] = float(self.slider_gap_var.get())

            # Beeps
            self.settings["enable_beeps"] = bool(self.enable_beeps_var.get())
            self.settings["start_beep"] = self.start_beep_entry.get().strip()
            self.settings["end_beep"] = self.end_beep_entry.get().strip()
            self.settings["link_beeps_speed"] = bool(self.link_beeps_var.get())

            # Signature
            self.settings["enable_signature"] = bool(self.enable_signature_var.get())
            self.settings["signature_mode"] = self.signature_mode_var.get()
            self.settings["signature_low_hz"] = float(self.sig_low_var.get())
            self.settings["signature_high_hz"] = float(self.sig_high_var.get())
            self.settings["signature_ms"] = float(self.sig_ms_var.get())
            self.settings["signature_repeats"] = int(self.sig_repeats_var.get())

            # Marker
            self.settings["enable_marker"] = bool(self.enable_marker_var.get())
            self.settings["marker_mode"] = self.marker_mode_var.get()
            self.settings["marker_low_hz"] = float(self.marker_low_var.get())
            self.settings["marker_high_hz"] = float(self.marker_high_var.get())
            self.settings["marker_tone_ms"] = float(self.marker_tone_ms_var.get())
            self.settings["marker_gap_ms"] = float(self.marker_gap_ms_var.get())
            self.settings["marker_repeats"] = int(self.marker_repeats_var.get())

            # Linking
            self.settings["link_sig_marker_speed"] = bool(self.link_sig_marker_var.get())

            save_settings(self.settings)
            if hasattr(self.parent,"apply_settings"):
                self.parent.apply_settings(self.settings)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Transmit","Invalid value: %s" % e)
