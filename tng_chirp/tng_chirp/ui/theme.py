import tkinter as tk
from tkinter import ttk

# Light palette only (dark mode removed)
LIGHT = {
    "bg": "#F5F5F5",
    "bg2": "#FFFFFF",
    "btn": "#EFEFEF",
    "edge": "#CCCCCC",
    "fg": "#202020",
    "muted": "#777777",
    "accent": "#2962FF",
    "grid": "#DDDDDD",
    "spine": "#9A9A9A",
}

def apply_theme(root: tk.Misc):
    """Apply a clean light ttk style (no dark mode)."""
    style = ttk.Style(root)
    # Prefer system theme if available; fallback to 'clam'
    try:
        # On Windows, 'vista' or 'xpnative' often exist; otherwise use 'clam'
        style.theme_use(style.theme_use())
    except Exception:
        try:
            style.theme_use('clam')
        except Exception:
            pass

    pal = LIGHT
    try:
        root.configure(bg=pal["bg"])
    except Exception:
        pass

    # Base
    style.configure(".", background=pal["bg"], foreground=pal["fg"])

    # Common widgets
    style.configure("TFrame", background=pal["bg"])
    style.configure("TLabelframe", background=pal["bg"], foreground=pal["fg"])
    style.configure("TLabelframe.Label", background=pal["bg"], foreground=pal["fg"])
    style.configure("TLabel", background=pal["bg"], foreground=pal["fg"])

    style.configure("TButton", background=pal["btn"], foreground=pal["fg"],
                    padding=6, relief="flat", bordercolor=pal["edge"])
    style.map("TButton", background=[("active", pal["btn"]), ("pressed", pal["btn"])],
              foreground=[("disabled", pal["muted"])])

    style.configure("TEntry", fieldbackground=pal["bg2"], background=pal["bg2"],
                    foreground=pal["fg"], relief="flat", insertcolor=pal["fg"])
    style.configure("TCombobox", fieldbackground=pal["bg2"], background=pal["btn"],
                    foreground=pal["fg"], arrowsize=14)
    style.configure("TSpinbox", fieldbackground=pal["bg2"], background=pal["btn"],
                    foreground=pal["fg"], arrowsize=14)
    style.configure("TNotebook", background=pal["bg"])
    style.configure("TNotebook.Tab", background=pal["btn"], foreground=pal["fg"], padding=[10,6])
    style.map("TNotebook.Tab", background=[("selected", pal["bg2"])])

def style_mpl(ax):
    """Light styling for Matplotlib axes."""
    pal = LIGHT
    fig = ax.get_figure()
    try:
        fig.patch.set_facecolor(pal["bg"])
        ax.set_facecolor(pal["bg"])
        for s in ax.spines.values():
            s.set_color(pal["spine"])
        ax.tick_params(colors=pal["fg"])
        ax.grid(True, color=pal["grid"], linestyle=":", alpha=0.35)
    except Exception:
        pass
