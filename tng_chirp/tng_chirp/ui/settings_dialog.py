# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import sounddevice as sd
from typing import Dict, Any

from tng_chirp.core.settings import save_settings
from tng_chirp.core.i18n import Translator
from tng_chirp.core.presets import DEFAULT_PRESETS

# WF_PRESETS fallback
try:
    from tng_chirp.core.settings import WF_PRESETS
except Exception:
    WF_PRESETS = {"Standard": {"wf_fps":12,"wf_max_rows":240,"wf_nperseg":512,"wf_noverlap":384,"wf_drange_db":60.0,"wf_colormap":"magma"}}

class SettingsDialog(tk.Toplevel):
    """
    Settings dialog with live language switching.
    Tabs: General / Screen / Receive / Transmit / Log (labels provided via Translator)
    Submenus: Screen -> Waterfall, Transmit -> TNG_Chirp
    """

    def __init__(self, parent: tk.Tk, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.settings = dict(settings)

        self.lang = self.settings.get("language", "ko")
        try:
            self.trans = Translator(self.lang)
        except Exception:
            class _T:
                def tr(self, k, d): return d
            self.trans = _T()

        self.title(self.trans.tr("menu.settings", "Settings"))
        self.geometry("1000x760")
        self.resizable(True, True)

        self._build_ui()

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def t(self, key, default):
        try:
            return self.trans.tr(key, default)
        except Exception:
            return default

    def _build_ui(self):
        # destroy existing notebook/footer if present
        if hasattr(self, "notebook") and self.notebook:
            try:
                self.notebook.destroy()
            except Exception:
                pass
        if hasattr(self, "_footer") and self._footer:
            try:
                self._footer.destroy()
            except Exception:
                pass

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Use Translator for tab labels so they change with language
        self._build_general_tab()
        self._build_screen_tab()
        self._build_receive_tab()
        self._build_transmit_tab()
        self._build_log_tab()

        # Footer with translated buttons
        self._footer = ttk.Frame(self)
        self._footer.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(self._footer, text=self.t("button.cancel", "Cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(self._footer, text=self.t("button.save", "Save"), command=self._on_save).pack(side=tk.RIGHT, padx=6)

    # ---------------- General tab ----------------
    def _build_general_tab(self):
        gen = ttk.Frame(self.notebook)
        self.notebook.add(gen, text=self.t("tabs.general","일반"))

        ttk.Label(gen, text=self.t("menu.language","메뉴 언어:")).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.lang_var = tk.StringVar(value=self.settings.get("language", self.lang))
        self.lang_combo = ttk.Combobox(gen, textvariable=self.lang_var, values=["en","jp","ko"], state="readonly", width=10)
        self.lang_combo.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        try:
            self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._on_language_change())
        except Exception:
            self.lang_var.trace_add("write", lambda *a: self._on_language_change())

        ttk.Label(gen, text=self.t("general.callsign","Callsign:")).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.callsign_var = tk.StringVar(value=self.settings.get("callsign",""))
        ttk.Entry(gen, textvariable=self.callsign_var, width=30).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(gen, text=self.t("general.grid","Grid:")).grid(row=2, column=0, sticky="e", padx=6, pady=6)
        self.grid_var = tk.StringVar(value=self.settings.get("grid",""))
        ttk.Entry(gen, textvariable=self.grid_var, width=30).grid(row=2, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(gen, text=self.t("general.input","Input device:")).grid(row=3, column=0, sticky="e", padx=6, pady=6)
        self.input_device_combo = ttk.Combobox(gen, state="readonly", width=50)
        self.input_device_combo.grid(row=3, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(gen, text=self.t("general.output","Output device:")).grid(row=4, column=0, sticky="e", padx=6, pady=6)
        self.output_device_combo = ttk.Combobox(gen, state="readonly", width=50)
        self.output_device_combo.grid(row=4, column=1, sticky="w", padx=6, pady=6)

        self._populate_devices()

    def _populate_devices(self):
        try:
            devs = sd.query_devices()
            inputs=[]; outputs=[]
            for idx,d in enumerate(devs):
                if d.get('max_input_channels',0)>0: inputs.append(f"{idx}: {d.get('name')}")
                if d.get('max_output_channels',0)>0: outputs.append(f"{idx}: {d.get('name')}")
            self.input_device_combo['values'] = inputs or ["(None)"]
            self.output_device_combo['values'] = outputs or ["(None)"]
            i_saved = self.settings.get("audio_input_index")
            o_saved = self.settings.get("audio_output_index")
            if i_saved is not None:
                for it in inputs:
                    if it.startswith(f"{i_saved}:"): self.input_device_combo.set(it); break
            if o_saved is not None:
                for it in outputs:
                    if it.startswith(f"{o_saved}:"): self.output_device_combo.set(it); break
            if not self.input_device_combo.get(): self.input_device_combo.set(inputs[0] if inputs else "(None)")
            if not self.output_device_combo.get(): self.output_device_combo.set(outputs[0] if outputs else "(None)")
        except Exception:
            self.input_device_combo['values'] = ["(Error)"]; self.input_device_combo.set("(Error)")
            self.output_device_combo['values'] = ["(Error)"]; self.output_device_combo.set("(Error)")

    # ---------------- Screen tab (contains Waterfall submenu) ----------------
    def _build_screen_tab(self):
        screen = ttk.Frame(self.notebook)
        self.notebook.add(screen, text=self.t("tabs.screen","화면"))

        subbar = ttk.Frame(screen)
        subbar.pack(fill=tk.X, padx=8, pady=(8,4))
        wf_btn = tk.Button(subbar, text=self.t("submenu.waterfall","워터폴"), width=18, relief="raised", command=lambda: self._show_screen_sub("Waterfall"))
        wf_btn.pack(side=tk.LEFT, padx=8, pady=4)

        self.screen_sub_container = ttk.Frame(screen)
        self.screen_sub_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self.screen_wf_frame = ttk.Frame(self.screen_sub_container)
        self.screen_wf_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        ttk.Label(self.screen_wf_frame, text=self.t("wf.fps","FPS:")).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.wf_fps_var = tk.IntVar(value=self.settings.get("wf_fps",12))
        ttk.Entry(self.screen_wf_frame, textvariable=self.wf_fps_var, width=10).grid(row=0, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(self.screen_wf_frame, text=self.t("wf.rows","Rows (history):")).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.wf_rows_var = tk.IntVar(value=self.settings.get("wf_max_rows",240))
        ttk.Entry(self.screen_wf_frame, textvariable=self.wf_rows_var, width=10).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(self.screen_wf_frame, text=self.t("waterfall.maxf","Max frequency (Hz):")).grid(row=2, column=0, sticky="e", padx=6, pady=6)
        self.max_freq_entry = ttk.Entry(self.screen_wf_frame, width=12)
        self.max_freq_entry.grid(row=2, column=1, sticky="w", padx=6, pady=6)
        self.max_freq_entry.insert(0, str(self.settings.get("max_freq",3000)))

        ttk.Label(self.screen_wf_frame, text=self.t("wf.fft","FFT nperseg:")).grid(row=3, column=0, sticky="e", padx=6, pady=6)
        self.wf_nper_var = tk.IntVar(value=self.settings.get("wf_nperseg",512))
        ttk.Entry(self.screen_wf_frame, textvariable=self.wf_nper_var, width=10).grid(row=3, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(self.screen_wf_frame, text=self.t("wf.overlap","FFT overlap:")).grid(row=4, column=0, sticky="e", padx=6, pady=6)
        self.wf_nover_var = tk.IntVar(value=self.settings.get("wf_noverlap",384))
        ttk.Entry(self.screen_wf_frame, textvariable=self.wf_nover_var, width=10).grid(row=4, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(self.screen_wf_frame, text=self.t("waterfall.cmap","Colormap:")).grid(row=5, column=0, sticky="e", padx=6, pady=6)
        cmaps = ["magma","inferno","plasma","viridis","turbo","cividis","gray","jet"]
        self.cmap_var = tk.StringVar(value=self.settings.get("wf_colormap", self.settings.get("colormap","magma")))
        ttk.Combobox(self.screen_wf_frame, values=cmaps, textvariable=self.cmap_var, state="readonly", width=14).grid(row=5, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(self.screen_wf_frame, text=self.t("waterfall.drange","Dynamic range (dB):")).grid(row=6, column=0, sticky="e", padx=6, pady=6)
        self.drange_entry = ttk.Entry(self.screen_wf_frame, width=12)
        self.drange_entry.grid(row=6, column=1, sticky="w", padx=6, pady=6)
        self.drange_entry.insert(0, str(self.settings.get("wf_drange_db", self.settings.get("drange_db",60.0))))

        ttk.Label(self.screen_wf_frame, text=self.t("wf.quality","Plot quality:")).grid(row=7, column=0, sticky="e", padx=6, pady=6)
        qvals = [self.t("quality.off","off"), self.t("quality.light","light"), self.t("quality.full","full")]
        internal = ["off","light","full"]
        init = self.settings.get("waterfall_quality","light")
        idx = internal.index(init) if init in internal else 1
        self.quality_combo = ttk.Combobox(self.screen_wf_frame, values=qvals, state="readonly", width=12)
        self.quality_combo.set(qvals[idx])
        self.quality_combo.grid(row=7, column=1, sticky="w", padx=6, pady=6)

        self._show_screen_sub("Waterfall")

    def _show_screen_sub(self, name: str):
        if name == "Waterfall":
            self.screen_wf_frame.lift()

    # ---------------- Receive (empty) ----------------
    def _build_receive_tab(self):
        recv = ttk.Frame(self.notebook)
        self.notebook.add(recv, text=self.t("tabs.receive","수신"))

    # ---------------- Transmit (with TNG_Chirp submenu) ----------------
    def _build_transmit_tab(self):
        tx = ttk.Frame(self.notebook)
        self.notebook.add(tx, text=self.t("tabs.transmit","송신"))

        subbar = ttk.Frame(tx)
        subbar.grid(row=0, column=0, columnspan=2, sticky="we", padx=6, pady=(6,4))
        tk.Button(subbar, text=self.t("submenu.tng_chirp","TNG_Chirp"), width=18, relief="raised", command=lambda: self._show_tx_subframe("TNG_Chirp")).pack(side=tk.LEFT, padx=8, pady=4)

        self.tx_sub_container = ttk.Frame(tx)
        self.tx_sub_container.grid(row=1, column=0, columnspan=2, sticky="nsew")
        tx.grid_rowconfigure(1, weight=1)
        tx.grid_columnconfigure(0, weight=1)

        self.tx_tng_chirp_frame = ttk.Frame(self.tx_sub_container)
        self.tx_tng_chirp_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._populate_tx_tng_chirp(self.tx_tng_chirp_frame)
        self._show_tx_subframe("TNG_Chirp")

    def _show_tx_subframe(self, name: str):
        if name == "TNG_Chirp":
            self.tx_tng_chirp_frame.lift()

    def _populate_tx_tng_chirp(self, root: ttk.Frame):
        try:
            from tng_chirp.core.i18n import Translator as _TR
            tr_local = _TR(self.lang)
            disp_list = tr_local.preset_display_list() if hasattr(tr_local, "preset_display_list") else ["Slow","Normal","Fast","VeryFast"]
        except Exception:
            disp_list = ["Slow","Normal","Fast","VeryFast"]
            tr_local = None

        top = ttk.Frame(root)
        top.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(top, text=self.t("chirp.default","Default preset:")).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.default_preset_var = tk.StringVar()
        cur_key = self.settings.get("default_preset","Normal")
        try:
            display_value = tr_local.preset_key_to_display(cur_key) if tr_local else cur_key
        except Exception:
            display_value = cur_key
        self.default_preset_combo = ttk.Combobox(top, values=disp_list, textvariable=self.default_preset_var, state="readonly", width=16)
        self.default_preset_var.set(display_value)
        self.default_preset_combo.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        try:
            self.default_preset_combo.bind("<<ComboboxSelected>>", self._on_default_preset_change)
        except Exception:
            pass

        self._build_presets(top)

        ttk.Label(top, text=self.t("beeps.enable","Enable pre/post beeps:")).grid(row=6, column=0, sticky="e", padx=6, pady=4)
        self.enable_beeps_var = tk.BooleanVar(value=self.settings.get("enable_beeps", True))
        ttk.Checkbutton(top, variable=self.enable_beeps_var).grid(row=6, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(top, text=self.t("beep.start","Start beep (f0:f1:dur_ms):")).grid(row=7, column=0, sticky="e", padx=6, pady=4)
        self.start_beep_entry = ttk.Entry(top, width=40)
        self.start_beep_entry.grid(row=7, column=1, sticky="w", padx=6, pady=4)
        self.start_beep_entry.insert(0, self.settings.get("start_beep","250:400:250"))

        ttk.Label(top, text=self.t("beep.end","End beep (comma-sep):")).grid(row=8, column=0, sticky="e", padx=6, pady=4)
        self.end_beep_entry = ttk.Entry(top, width=40)
        self.end_beep_entry.grid(row=8, column=1, sticky="w", padx=6, pady=4)
        self.end_beep_entry.insert(0, self.settings.get("end_beep","250:400:250,100:300:250"))

        ttk.Label(top, text=self.t("dur.ms","Symbol duration (ms):")).grid(row=9, column=0, sticky="e", padx=6, pady=4)
        self.dur_ms_var = tk.DoubleVar(value=self.settings.get("slider_dur_ms",60.0))
        ttk.Scale(top, from_=5.0, to=300.0, orient=tk.HORIZONTAL, variable=self.dur_ms_var).grid(row=9, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(top, text=self.t("gap.ms","Gap (ms):")).grid(row=10, column=0, sticky="e", padx=6, pady=4)
        self.gap_ms_var = tk.DoubleVar(value=self.settings.get("slider_gap_ms",8.0))
        ttk.Scale(top, from_=0.0, to=200.0, orient=tk.HORIZONTAL, variable=self.gap_ms_var).grid(row=10, column=1, sticky="we", padx=6, pady=4)

        ttk.Separator(top).grid(row=11, column=0, columnspan=2, sticky="we", pady=8)

        ttk.Label(top, text=self.t("sig.enable","Enable recognition signature:")).grid(row=15, column=0, sticky="e", padx=6, pady=4)
        self.enable_signature_var = tk.BooleanVar(value=self.settings.get("enable_signature", True))
        ttk.Checkbutton(top, variable=self.enable_signature_var).grid(row=15, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(top, text=self.t("sig.mode","Signature mode:")).grid(row=16, column=0, sticky="e", padx=6, pady=4)
        self.signature_mode_var = tk.StringVar(value=self.settings.get("signature_mode","chirp_bounce"))
        ttk.Combobox(top, textvariable=self.signature_mode_var, values=["chirp_bounce","dual_pulse"], state="readonly", width=14).grid(row=16, column=1, sticky="w", padx=6, pady=4)

        self.sig_low_var = tk.DoubleVar(value=self.settings.get("signature_low_hz",600.0))
        ttk.Label(top, text=self.t("sig.low","Sig. low Hz:")).grid(row=17, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.sig_low_var, width=10).grid(row=17, column=1, sticky="w", padx=6, pady=4)

        self.sig_high_var = tk.DoubleVar(value=self.settings.get("signature_high_hz",1200.0))
        ttk.Label(top, text=self.t("sig.high","Sig. high Hz:")).grid(row=18, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.sig_high_var, width=10).grid(row=18, column=1, sticky="w", padx=6, pady=4)

        self.sig_ms_var = tk.DoubleVar(value=self.settings.get("signature_ms",180.0))
        ttk.Label(top, text=self.t("sig.ms","Sig. ms:")).grid(row=19, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.sig_ms_var, width=10).grid(row=19, column=1, sticky="w", padx=6, pady=4)

        self.sig_repeats_var = tk.IntVar(value=self.settings.get("signature_repeats",2))
        ttk.Label(top, text=self.t("sig.repeats","Sig. repeats:")).grid(row=20, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.sig_repeats_var, width=10).grid(row=20, column=1, sticky="w", padx=6, pady=4)

        ttk.Separator(top).grid(row=21, column=0, columnspan=2, sticky="we", pady=8)

        ttk.Label(top, text=self.t("marker.enable","Enable frequency marker:")).grid(row=22, column=0, sticky="e", padx=6, pady=4)
        self.enable_marker_var = tk.BooleanVar(value=self.settings.get("enable_marker", True))
        ttk.Checkbutton(top, variable=self.enable_marker_var).grid(row=22, column=1, sticky="w", padx=6, pady=4)

        self.marker_mode_var = tk.StringVar(value=self.settings.get("marker_mode","simul"))
        ttk.Label(top, text=self.t("marker.mode","Marker mode:")).grid(row=23, column=0, sticky="e", padx=6, pady=4)
        mode_disp = [self.t("mode.simul","simul"), self.t("mode.seq","seq")]
        self.marker_mode_combo = ttk.Combobox(top, values=mode_disp, state="readonly", width=10)
        self.marker_mode_combo.grid(row=23, column=1, sticky="w", padx=6, pady=4)
        try:
            if self.marker_mode_var.get() == "seq":
                self.marker_mode_combo.set(self.t("mode.seq","seq"))
            else:
                self.marker_mode_combo.set(self.t("mode.simul","simul"))
        except Exception:
            pass

        self.marker_low_var = tk.DoubleVar(value=self.settings.get("marker_low_hz",300.0))
        ttk.Label(top, text=self.t("marker.low","Low F (Hz):")).grid(row=24, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.marker_low_var, width=10).grid(row=24, column=1, sticky="w", padx=6, pady=4)

        self.marker_high_var = tk.DoubleVar(value=self.settings.get("marker_high_hz",1500.0))
        ttk.Label(top, text=self.t("marker.high","High F (Hz):")).grid(row=25, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.marker_high_var, width=10).grid(row=25, column=1, sticky="w", padx=6, pady=4)

        self.marker_tone_ms_var = tk.DoubleVar(value=self.settings.get("marker_tone_ms",350.0))
        ttk.Label(top, text=self.t("marker.tone.ms","Tone ms:")).grid(row=26, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.marker_tone_ms_var, width=10).grid(row=26, column=1, sticky="w", padx=6, pady=4)

        self.marker_gap_ms_var = tk.DoubleVar(value=self.settings.get("marker_gap_ms",120.0))
        ttk.Label(top, text=self.t("marker.gap.ms","Gap ms:")).grid(row=27, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.marker_gap_ms_var, width=10).grid(row=27, column=1, sticky="w", padx=6, pady=4)

        self.marker_repeats_var = tk.IntVar(value=self.settings.get("marker_repeats",2))
        ttk.Label(top, text=self.t("marker.repeats","Repeats:")).grid(row=28, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.marker_repeats_var, width=10).grid(row=28, column=1, sticky="w", padx=6, pady=4)

    def _build_presets(self, parent):
        ttk.Label(parent, text=self.t("preset.slow.lbl","Slow (dur s, gap s):")).grid(row=1, column=0, sticky="e", padx=6)
        self.slow_dur_var = tk.DoubleVar(value=self.settings.get("preset_slow",(0.12,0.03))[0])
        self.slow_gap_var = tk.DoubleVar(value=self.settings.get("preset_slow",(0.12,0.03))[1])
        ttk.Entry(parent, textvariable=self.slow_dur_var, width=8).grid(row=1, column=1, sticky="w", padx=60)
        ttk.Entry(parent, textvariable=self.slow_gap_var, width=8).grid(row=1, column=1, sticky="w", padx=140)

        ttk.Label(parent, text=self.t("preset.normal.lbl","Normal (dur s, gap s):")).grid(row=2, column=0, sticky="e", padx=6)
        self.norm_dur_var = tk.DoubleVar(value=self.settings.get("preset_normal",(0.06,0.008))[0])
        self.norm_gap_var = tk.DoubleVar(value=self.settings.get("preset_normal",(0.06,0.008))[1])
        ttk.Entry(parent, textvariable=self.norm_dur_var, width=8).grid(row=2, column=1, sticky="w", padx=60)
        ttk.Entry(parent, textvariable=self.norm_gap_var, width=8).grid(row=2, column=1, sticky="w", padx=140)

        ttk.Label(parent, text=self.t("preset.fast.lbl","Fast (dur s, gap s):")).grid(row=3, column=0, sticky="e", padx=6)
        self.fast_dur_var = tk.DoubleVar(value=self.settings.get("preset_fast",(0.02,0.002))[0])
        self.fast_gap_var = tk.DoubleVar(value=self.settings.get("preset_fast",(0.02,0.002))[1])
        ttk.Entry(parent, textvariable=self.fast_dur_var, width=8).grid(row=3, column=1, sticky="w", padx=60)
        ttk.Entry(parent, textvariable=self.fast_gap_var, width=8).grid(row=3, column=1, sticky="w", padx=140)

        ttk.Label(parent, text=self.t("preset.vfast.lbl","VeryFast (dur s, gap s):")).grid(row=4, column=0, sticky="e", padx=6)
        self.vfast_dur_var = tk.DoubleVar(value=self.settings.get("preset_veryfast",(0.012,0.0015))[0])
        self.vfast_gap_var = tk.DoubleVar(value=self.settings.get("preset_veryfast",(0.012,0.0015))[1])
        ttk.Entry(parent, textvariable=self.vfast_dur_var, width=8).grid(row=4, column=1, sticky="w", padx=60)
        ttk.Entry(parent, textvariable=self.vfast_gap_var, width=8).grid(row=4, column=1, sticky="w", padx=140)

    def _on_language_change(self):
        # save visible inputs to self.settings to preserve user edits, then rebuild UI with new language
        try:
            if hasattr(self, "callsign_var"): self.settings["callsign"] = self.callsign_var.get()
            if hasattr(self, "grid_var"): self.settings["grid"] = self.grid_var.get()
            if hasattr(self, "input_device_combo"): self.settings["audio_input_index"] = self._parse_index(self.input_device_combo.get())
            if hasattr(self, "output_device_combo"): self.settings["audio_output_index"] = self._parse_index(self.output_device_combo.get())
            if hasattr(self, "wf_fps_var"): self.settings["wf_fps"] = int(self.wf_fps_var.get())
            if hasattr(self, "wf_rows_var"): self.settings["wf_max_rows"] = int(self.wf_rows_var.get())
            if hasattr(self, "max_freq_entry"): self.settings["max_freq"] = int(self.max_freq_entry.get())
            if hasattr(self, "cmap_var"): self.settings["wf_colormap"] = self.cmap_var.get()
            if hasattr(self, "dur_ms_var"): self.settings["slider_dur_ms"] = float(self.dur_ms_var.get())
            if hasattr(self, "gap_ms_var"): self.settings["slider_gap_ms"] = float(self.gap_ms_var.get())
        except Exception:
            pass

        try:
            new_lang = self.lang_var.get() if hasattr(self, "lang_var") else self.settings.get("language", self.lang)
            self.settings["language"] = new_lang
            self.lang = new_lang
            try:
                self.trans = Translator(self.lang)
            except Exception:
                class _T:
                    def tr(self, k, d): return d
                self.trans = _T()
            # rebuild UI so translated tab labels appear
            self._build_ui()
        except Exception:
            pass

    def _parse_index(self, txt):
        try:
            return int(str(txt).split(":")[0].strip())
        except Exception:
            return None

    def _on_default_preset_change(self, *_):
        try:
            from tng_chirp.core.i18n import Translator as _TR
            tr_local = _TR(self.lang_var.get()) if hasattr(self, "lang_var") else _TR(self.lang)
            key = tr_local.preset_display_to_key(self.default_preset_var.get())
        except Exception:
            key = self.default_preset_var.get()
        mapping = {
            "Slow": (float(self.slow_dur_var.get()), float(self.slow_gap_var.get())),
            "Normal": (float(self.norm_dur_var.get()), float(self.norm_gap_var.get())),
            "Fast": (float(self.fast_dur_var.get()), float(self.fast_gap_var.get())),
            "VeryFast": (float(self.vfast_dur_var.get()), float(self.vfast_gap_var.get())),
        }
        dur, gap = mapping.get(key, mapping["Normal"])
        self.dur_ms_var.set(dur * 1000.0)
        self.gap_ms_var.set(gap * 1000.0)

    def _on_save(self):
        try:
            # persist fields to settings then save
            self.settings["language"] = self.lang_var.get() if hasattr(self, "lang_var") else self.settings.get("language", self.lang)
            self.settings["callsign"] = self.callsign_var.get()
            self.settings["grid"] = self.grid_var.get()
            self.settings["audio_input_index"] = self._parse_index(self.input_device_combo.get())
            self.settings["audio_output_index"] = self._parse_index(self.output_device_combo.get())

            try:
                self.settings["wf_fps"] = int(self.wf_fps_var.get())
            except Exception:
                pass
            try:
                self.settings["wf_max_rows"] = int(self.wf_rows_var.get())
            except Exception:
                pass
            try:
                self.settings["wf_nperseg"] = int(self.wf_nper_var.get()); self.settings["wf_noverlap"] = int(self.wf_nover_var.get())
            except Exception:
                pass
            try:
                self.settings["max_freq"] = int(self.max_freq_entry.get())
            except Exception:
                pass
            self.settings["wf_colormap"] = str(self.cmap_var.get())
            try:
                self.settings["wf_drange_db"] = float(self.drange_entry.get())
            except Exception:
                pass
            q_display = self.quality_combo.get()
            q_map = {self.t("quality.off","off"):"off", self.t("quality.light","light"):"light", self.t("quality.full","full"):"full"}
            self.settings["waterfall_quality"] = q_map.get(q_display,"light")

            self.settings["preset_slow"] = (float(self.slow_dur_var.get()), float(self.slow_gap_var.get()))
            self.settings["preset_normal"] = (float(self.norm_dur_var.get()), float(self.norm_gap_var.get()))
            self.settings["preset_fast"] = (float(self.fast_dur_var.get()), float(self.fast_gap_var.get()))
            self.settings["preset_veryfast"] = (float(self.vfast_dur_var.get()), float(self.vfast_gap_var.get()))

            try:
                from tng_chirp.core.i18n import Translator as _TR
                tr_local = _TR(self.lang_var.get())
                self.settings["default_preset"] = tr_local.preset_display_to_key(self.default_preset_var.get())
            except Exception:
                self.settings["default_preset"] = self.default_preset_var.get()

            self.settings["start_beep"] = self.start_beep_entry.get().strip()
            self.settings["end_beep"] = self.end_beep_entry.get().strip()
            self.settings["enable_beeps"] = bool(self.enable_beeps_var.get())
            self.settings["slider_dur_ms"] = float(self.dur_ms_var.get())
            self.settings["slider_gap_ms"] = float(self.gap_ms_var.get())

            self.settings["link_sig_marker_speed"] = bool(getattr(self, "link_speed_var", tk.BooleanVar(value=self.settings.get("link_sig_marker_speed", True))).get())
            self.settings["link_beeps_speed"] = bool(getattr(self, "link_beeps_var", tk.BooleanVar(value=self.settings.get("link_beeps_speed", True))).get())

            self.settings["enable_signature"] = bool(self.enable_signature_var.get())
            self.settings["signature_mode"] = self.signature_mode_var.get()
            self.settings["signature_low_hz"] = float(self.sig_low_var.get())
            self.settings["signature_high_hz"] = float(self.sig_high_var.get())
            self.settings["signature_ms"] = float(self.sig_ms_var.get())
            self.settings["signature_repeats"] = int(self.sig_repeats_var.get())

            mode_txt = self.marker_mode_combo.get()
            if mode_txt == self.t("mode.seq","seq"):
                m_key = "seq"
            else:
                m_key = "simul"
            self.settings["enable_marker"] = bool(self.enable_marker_var.get())
            self.settings["marker_mode"] = m_key
            self.settings["marker_low_hz"] = float(self.marker_low_var.get())
            self.settings["marker_high_hz"] = float(self.marker_high_var.get())
            self.settings["marker_tone_ms"] = float(self.marker_tone_ms_var.get())
            self.settings["marker_gap_ms"] = float(self.marker_gap_ms_var.get())
            self.settings["marker_repeats"] = int(self.marker_repeats_var.get())

            self.settings["show_log_timestamp"] = bool(self.show_ts_var.get())
            self.settings["log_font_size"] = int(self.log_font_var.get())
            self.settings["log_autoscroll"] = bool(self.autoscroll_var.get())

            save_settings(self.settings)

            if getattr(self, "clear_log_flag", None) and self.clear_log_flag.get() and hasattr(self.parent, "clear_log"):
                self.parent.clear_log()

            if hasattr(self.parent, "apply_settings"):
                try: self.parent.apply_settings(self.settings)
                except Exception: pass
            if hasattr(self.parent, "update_menu_language"):
                try: self.parent.update_menu_language()
                except Exception: pass

            self.destroy()
        except Exception as e:
            messagebox.showerror(self.t("menu.settings","Settings"), f"Invalid value: {e}")



    # --- Fallback log tab builder (added by patcher) ---
    def _build_log_tab(self):
        logt = ttk.Frame(self.notebook)
        self.notebook.add(logt, text=self.t("tabs.log","로그"))

        self.show_ts_var = tk.BooleanVar(value=self.settings.get("show_log_timestamp", True))
        ttk.Checkbutton(logt, text=self.t("log.timestamp","Show timestamps"), variable=self.show_ts_var).grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.autoscroll_var = tk.BooleanVar(value=self.settings.get("log_autoscroll", True))
        ttk.Checkbutton(logt, text=self.t("log.autoscroll","Auto scroll"), variable=self.autoscroll_var).grid(row=1, column=0, sticky="w", padx=6, pady=6)

        ttk.Label(logt, text=self.t("log.fontsize","Log font size:")).grid(row=2, column=0, sticky="w", padx=6, pady=6)
        self.log_font_var = tk.IntVar(value=self.settings.get("log_font_size", 11))
        ttk.Spinbox(logt, from_=8, to=18, width=6, textvariable=self.log_font_var).grid(row=2, column=1, sticky="w", padx=6, pady=6)

        self.clear_log_flag = tk.BooleanVar(value=False)
        ttk.Button(logt, text=self.t("log.clear","Clear log now"), command=lambda: self.clear_log_flag.set(True)).grid(row=3, column=0, sticky="w", padx=6, pady=6)
    