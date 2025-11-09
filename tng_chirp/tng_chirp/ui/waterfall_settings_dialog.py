import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
from tng_chirp.core.settings import save_settings, WF_PRESETS

class WaterfallSettingsDialog(tk.Toplevel):
    """Separate dialog for waterfall presets & advanced parameters."""
    def __init__(self, parent: tk.Tk, settings: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.settings = dict(settings)
        self.title("Waterfall Settings")
        self.geometry("420x460")
        self.resizable(False, False)
        self.columnconfigure(0, weight=1)
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Preset selector
        ttk.Label(frm, text="Preset:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.preset_var = tk.StringVar(value=self.settings.get("wf_preset","Standard"))
        self.preset_combo = ttk.Combobox(frm, values=list(WF_PRESETS.keys())+["Custom"], state="readonly",
                                         textvariable=self.preset_var, width=14)
        self.preset_combo.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        # Advanced entries
        self.chunk_var = tk.DoubleVar(value=float(self.settings.get("wf_chunk_seconds",0.4)))
        self.rows_var  = tk.IntVar(value=int(self.settings.get("wf_max_rows",240)))
        self.nper_var  = tk.IntVar(value=int(self.settings.get("wf_nperseg",512)))
        self.nover_var = tk.IntVar(value=int(self.settings.get("wf_noverlap",384)))
        self.drange_var= tk.DoubleVar(value=float(self.settings.get("wf_drange_db",60.0)))
        self.cmap_var  = tk.StringVar(value=self.settings.get("wf_colormap","magma"))

        labels = [
            ("Chunk seconds:", self.chunk_var),
            ("Rows (history):", self.rows_var),
            ("FFT nperseg:", self.nper_var),
            ("FFT overlap:", self.nover_var),
            ("Dynamic range dB:", self.drange_var),
            ("Colormap:", self.cmap_var),
        ]

        cmaps = ["magma","inferno","plasma","viridis","turbo","cividis","gray","jet","plasma","twilight","coolwarm"]

        for i,(lab,var) in enumerate(labels, start=1):
            ttk.Label(frm, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=4)
            if lab == "Colormap:":
                ttk.Combobox(frm, values=cmaps, state="readonly", textvariable=var, width=14)\
                    .grid(row=i, column=1, sticky="w", padx=4, pady=4)
            else:
                ttk.Entry(frm, textvariable=var, width=16).grid(row=i, column=1, sticky="w", padx=4, pady=4)

        sep = ttk.Separator(frm)
        sep.grid(row=8, column=0, columnspan=2, sticky="we", pady=8)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=9, column=0, columnspan=2, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=4)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    def _on_preset_change(self, *_):
        preset = self.preset_var.get()
        if preset in WF_PRESETS:
            data = WF_PRESETS[preset]
            self.chunk_var.set(data["wf_chunk_seconds"])
            self.rows_var.set(data["wf_max_rows"])
            self.nper_var.set(data["wf_nperseg"])
            self.nover_var.set(data["wf_noverlap"])
            self.drange_var.set(data["wf_drange_db"])
            self.cmap_var.set(data["wf_colormap"])
        # If "Custom" do nothing

    def _on_save(self):
        try:
            # Validate basic ranges quickly
            if self.chunk_var.get() <= 0.05:
                raise ValueError("Chunk seconds too small")
            if self.rows_var.get() < 50:
                raise ValueError("Rows too small")
            if self.nper_var.get() < 64:
                raise ValueError("nperseg too small")
            if self.nover_var.get() >= self.nper_var.get():
                raise ValueError("overlap >= nperseg")
            # Commit
            self.settings["wf_preset"] = self.preset_var.get()
            self.settings["wf_chunk_seconds"] = float(self.chunk_var.get())
            self.settings["wf_max_rows"] = int(self.rows_var.get())
            self.settings["wf_nperseg"] = int(self.nper_var.get())
            self.settings["wf_noverlap"] = int(self.nover_var.get())
            self.settings["wf_drange_db"] = float(self.drange_var.get())
            self.settings["wf_colormap"] = self.cmap_var.get()

            # If user changed values away from preset, mark as Custom
            preset = self.settings["wf_preset"]
            if preset in WF_PRESETS:
                mismatch = False
                for k,v in WF_PRESETS[preset].items():
                    if self.settings.get(k) != v:
                        mismatch = True
                        break
                if mismatch:
                    self.settings["wf_preset"] = "Custom"

            save_settings(self.settings)
            if hasattr(self.parent,"apply_settings"):
                self.parent.apply_settings(self.settings)
            if hasattr(self.parent,"reinit_waterfall"):
                self.parent.reinit_waterfall()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Waterfall Settings", f"Invalid value: {e}")
