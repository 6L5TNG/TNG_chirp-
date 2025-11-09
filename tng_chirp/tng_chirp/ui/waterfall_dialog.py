import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
from tng_chirp.core.settings import save_settings, WF_PRESETS

class WaterfallQuickDialog(tk.Toplevel):
    """Quick access mini dialog (optional)."""
    def __init__(self, parent, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.settings = settings
        self.title("Waterfall Quick")
        self.geometry("420x420")
        self.resizable(False, False)

        ttk.Label(self, text="Preset:").grid(row=0,column=0,sticky="e",padx=6,pady=6)
        self.preset_var = tk.StringVar(value=self.settings.get("wf_preset","Standard"))
        names = list(WF_PRESETS.keys()) + ["Custom"]
        ttk.Combobox(self, values=names, textvariable=self.preset_var,
                     state="readonly", width=14).grid(row=0,column=1,sticky="w",padx=6,pady=6)

        def entry(label, key, r):
            ttk.Label(self, text=label).grid(row=r,column=0,sticky="e",padx=6,pady=4)
            var = tk.StringVar(value=str(self.settings.get(key,"")))
            ttk.Entry(self, textvariable=var, width=12).grid(row=r,column=1,sticky="w",padx=6,pady=4)
            return var

        self.fps_var      = entry("FPS:", "wf_fps", 1)
        self.rows_var     = entry("Rows:", "wf_max_rows", 2)
        self.nper_var     = entry("nperseg:", "wf_nperseg", 3)
        self.nover_var    = entry("overlap:", "wf_noverlap", 4)
        self.drange_var   = entry("Live drange dB:", "wf_drange_db", 5)
        self.live_cmap_var= entry("Live cmap:", "wf_colormap", 6)
        self.maxf_var     = entry("Max freq Hz:", "max_freq", 7)
        self.view_cmap_var= entry("View cmap:", "colormap", 8)
        self.view_drange_var= entry("View drange dB:", "drange_db", 9)

        ttk.Button(self, text="Apply", command=self._apply).grid(row=10,column=0,sticky="e",padx=6,pady=10)
        ttk.Button(self, text="Cancel", command=self.destroy).grid(row=10,column=1,sticky="w",padx=6,pady=10)

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def _apply(self):
        try:
            self.settings["wf_fps"]       = int(self.fps_var.get())
            self.settings["wf_max_rows"]  = int(self.rows_var.get())
            self.settings["wf_nperseg"]   = int(self.nper_var.get())
            self.settings["wf_noverlap"]  = int(self.nover_var.get())
            self.settings["wf_drange_db"] = float(self.drange_var.get())
            self.settings["wf_colormap"]  = self.live_cmap_var.get()
            self.settings["max_freq"]     = int(self.maxf_var.get())
            self.settings["colormap"]     = self.view_cmap_var.get()
            self.settings["drange_db"]    = float(self.view_drange_var.get())
            self.settings["wf_preset"]    = self.preset_var.get()
            save_settings(self.settings)
            if hasattr(self.parent,"apply_settings"):
                self.parent.apply_settings(self.settings)
            if hasattr(self.parent,"reinit_waterfall"):
                self.parent.reinit_waterfall()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Waterfall", f"Invalid value: {e}")
