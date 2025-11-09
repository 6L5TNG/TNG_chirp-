# -*- coding: utf-8 -*-
# Double-click to launch the TNG_Chirp app without console.
import os, sys, traceback
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

def main():
    root_dir = Path(__file__).parent.resolve()
    # Ensure working directory is the project root (for resources, settings file, etc.)
    try:
        os.chdir(root_dir)
    except Exception:
        pass
    # Ensure local packages are importable
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    try:
        from tng_chirp import app as _app
        _app.main()
    except Exception as e:
        tb = traceback.format_exc()
        try:
            tk.Tk().withdraw()
            messagebox.showerror("TNG_Chirp", f"Failed to launch app:\n{e}\n\n{tb}")
        except Exception:
            pass
        raise

if __name__ == "__main__":
    main()