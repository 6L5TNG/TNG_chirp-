# -*- coding: utf-8 -*-
"""
JSON Patch Tool - tkinter based utility for applying JSON patches.
Backs up existing files before overwriting.
"""
import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime


class PatchTool(tk.Tk):
    """Main application window for JSON patch tool."""

    def __init__(self):
        super().__init__()
        self.title("MPDA Patch Tool")
        self.geometry("600x400")
        self.resizable(True, True)

        self._build_ui()

    def _build_ui(self):
        """Build the user interface."""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Patch file selection
        file_frame = ttk.LabelFrame(main_frame, text="Patch File", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        self.patch_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.patch_path_var, width=60).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(file_frame, text="Browse...", command=self._browse_patch).pack(
            side=tk.RIGHT
        )

        # Target directory selection
        target_frame = ttk.LabelFrame(main_frame, text="Target Directory", padding="5")
        target_frame.pack(fill=tk.X, pady=(0, 10))

        self.target_path_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(target_frame, textvariable=self.target_path_var, width=60).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(target_frame, text="Browse...", command=self._browse_target).pack(
            side=tk.RIGHT
        )

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Create backup before overwriting",
            variable=self.backup_var,
        ).pack(anchor=tk.W)

        self.verbose_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Show detailed log", variable=self.verbose_var
        ).pack(anchor=tk.W)

        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(
            log_frame, orient=tk.VERTICAL, command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Apply Patch", command=self._apply_patch).pack(
            side=tk.RIGHT, padx=(5, 0)
        )
        ttk.Button(button_frame, text="Clear Log", command=self._clear_log).pack(
            side=tk.RIGHT
        )

    def _browse_patch(self):
        """Browse for patch JSON file."""
        path = filedialog.askopenfilename(
            title="Select Patch File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.patch_path_var.set(path)

    def _browse_target(self):
        """Browse for target directory."""
        path = filedialog.askdirectory(title="Select Target Directory")
        if path:
            self.target_path_var.set(path)

    def _log(self, message: str):
        """Add message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def _clear_log(self):
        """Clear the log area."""
        self.log_text.delete("1.0", tk.END)

    def _apply_patch(self):
        """Apply the JSON patch to target files."""
        patch_path = self.patch_path_var.get().strip()
        target_dir = self.target_path_var.get().strip()

        if not patch_path:
            messagebox.showerror("Error", "Please select a patch file.")
            return

        if not os.path.isfile(patch_path):
            messagebox.showerror("Error", f"Patch file not found: {patch_path}")
            return

        if not os.path.isdir(target_dir):
            messagebox.showerror("Error", f"Target directory not found: {target_dir}")
            return

        try:
            with open(patch_path, "r", encoding="utf-8") as f:
                patch_data = json.load(f)
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON in patch file: {e}")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read patch file: {e}")
            return

        if not isinstance(patch_data, dict) or "files" not in patch_data:
            messagebox.showerror(
                "Error", 'Patch file must contain a "files" object.'
            )
            return

        files = patch_data["files"]
        if not isinstance(files, dict):
            messagebox.showerror("Error", '"files" must be an object.')
            return

        self._log(f"Applying patch from: {patch_path}")
        self._log(f"Target directory: {target_dir}")
        self._log(f"Files to patch: {len(files)}")

        success_count = 0
        error_count = 0

        for rel_path, content in files.items():
            target_file = os.path.join(target_dir, rel_path)

            try:
                # Create directory if needed
                target_dirname = os.path.dirname(target_file)
                if target_dirname and not os.path.exists(target_dirname):
                    os.makedirs(target_dirname, exist_ok=True)
                    if self.verbose_var.get():
                        self._log(f"  Created directory: {target_dirname}")

                # Backup existing file
                if self.backup_var.get() and os.path.exists(target_file):
                    backup_path = f"{target_file}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(target_file, backup_path)
                    if self.verbose_var.get():
                        self._log(f"  Backed up: {rel_path} -> {os.path.basename(backup_path)}")

                # Write new content
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(content)

                if self.verbose_var.get():
                    self._log(f"  Patched: {rel_path}")
                success_count += 1

            except Exception as e:
                self._log(f"  ERROR patching {rel_path}: {e}")
                error_count += 1

        self._log(f"Patch complete: {success_count} succeeded, {error_count} failed")

        if error_count == 0:
            messagebox.showinfo(
                "Success", f"Patch applied successfully!\n{success_count} files patched."
            )
        else:
            messagebox.showwarning(
                "Partial Success",
                f"{success_count} files patched, {error_count} errors occurred.",
            )


def main():
    """Main entry point."""
    app = PatchTool()
    app.mainloop()


if __name__ == "__main__":
    main()
