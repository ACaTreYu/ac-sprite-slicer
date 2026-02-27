"""
ac-sprite-slicer - Simple Windows GUI
Tkinter interface for the sprite slicing pipeline.
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import os
import sys
from pathlib import Path

from batch_auto_slicer import batch_auto_slice, find_sprite_sheets
from tile_categorizer import categorize_tiles
from generate_ue5_meshes import process_tiles, process_ships, SCALE_CONFIGS
from version import VERSION


class SlicerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"ac-sprite-slicer v{VERSION}")
        self.root.geometry("700x650")
        self.root.resizable(True, True)

        self.is_running = False
        self.create_widgets()

    def create_widgets(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Folder Section ---
        input_frame = ttk.LabelFrame(main_frame, text="Input Folder", padding="5")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        input_inner = ttk.Frame(input_frame)
        input_inner.pack(fill=tk.X, padx=5, pady=5)

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_inner, textvariable=self.input_var, width=60)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(input_inner, text="Browse...", command=self.browse_input).pack(side=tk.LEFT, padx=(5, 0))

        # Detected sheets preview
        self.sheets_preview_var = tk.StringVar(value="")
        self.sheets_preview = ttk.Label(input_frame, textvariable=self.sheets_preview_var, foreground="gray")
        self.sheets_preview.pack(anchor=tk.W, padx=10, pady=(0, 5))

        # --- Output Folder Section ---
        output_frame = ttk.LabelFrame(main_frame, text="Output Folder", padding="5")
        output_frame.pack(fill=tk.X, pady=(0, 10))

        output_inner = ttk.Frame(output_frame)
        output_inner.pack(fill=tk.X, padx=5, pady=5)

        self.output_var = tk.StringVar()
        self.output_entry = ttk.Entry(output_inner, textvariable=self.output_var, width=60)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(output_inner, text="Browse...", command=self.browse_output).pack(side=tk.LEFT, padx=(5, 0))

        # Auto-output checkbox
        self.auto_output_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            output_frame, text="Auto-generate from input path (input/sliced_output)",
            variable=self.auto_output_var
        ).pack(anchor=tk.W, padx=5, pady=(0, 5))

        # --- Pipeline Steps Section ---
        steps_frame = ttk.LabelFrame(main_frame, text="Pipeline Steps", padding="5")
        steps_frame.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Steps
        steps_row = ttk.Frame(steps_frame)
        steps_row.pack(fill=tk.X, padx=5, pady=5)

        self.step_slice_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            steps_row, text="1. Slice Sprites",
            variable=self.step_slice_var
        ).pack(side=tk.LEFT, padx=(0, 15))

        self.step_categorize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            steps_row, text="2. Categorize Tiles",
            variable=self.step_categorize_var
        ).pack(side=tk.LEFT, padx=(0, 15))

        self.step_meshes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            steps_row, text="3. Generate UE5 Meshes",
            variable=self.step_meshes_var
        ).pack(side=tk.LEFT)

        # Row 2: Options
        opts_row = ttk.Frame(steps_frame)
        opts_row.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.preview_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts_row, text="Create category preview sheets",
            variable=self.preview_var
        ).pack(side=tk.LEFT)

        # --- Buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(btn_frame, text="Run Pipeline", command=self.start_pipeline)
        self.start_btn.pack(side=tk.LEFT)

        self.scan_btn = ttk.Button(btn_frame, text="Scan Input", command=self.scan_input)
        self.scan_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.clear_btn = ttk.Button(btn_frame, text="Clear Log", command=self.clear_log)
        self.clear_btn.pack(side=tk.RIGHT)

        # --- Log Section ---
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # ---- Browse / Scan ----

    def browse_input(self):
        path = filedialog.askdirectory(title="Select folder containing sprite sheets")
        if path:
            self.input_var.set(path)
            if self.auto_output_var.get():
                self.output_var.set(os.path.join(path, "sliced_output"))
            self.update_sheets_preview()

    def browse_output(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_var.set(path)
            self.auto_output_var.set(False)

    def update_sheets_preview(self):
        input_path = self.input_var.get().strip()
        if not input_path or not os.path.exists(input_path):
            self.sheets_preview_var.set("")
            return

        sheets = find_sprite_sheets(input_path)
        if sheets:
            types = {}
            for s in sheets:
                t = s['type'].upper()
                types[t] = types.get(t, 0) + 1
            summary = ", ".join(f"{count} {t}" for t, count in types.items())
            self.sheets_preview_var.set(f"Found: {len(sheets)} sheets ({summary})")
        else:
            self.sheets_preview_var.set("No imgTiles.png or imgTuna.png found")

    def scan_input(self):
        input_path = self.input_var.get().strip()
        if not input_path or not os.path.exists(input_path):
            self.log("[ERROR] Please select a valid input folder first")
            return

        sheets = find_sprite_sheets(input_path)
        if not sheets:
            self.log(f"[SCAN] No imgTiles.png or imgTuna.png found in: {input_path}")
            return

        self.log("=" * 50)
        self.log(f"[SCAN] Found {len(sheets)} sprite sheet(s):")
        for s in sheets:
            rel = s['path'].relative_to(input_path)
            self.log(f"  [{s['type'].upper():5s}] {rel}")
        self.log("=" * 50)
        self.update_sheets_preview()

    # ---- Log ----

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ---- Pipeline ----

    def start_pipeline(self):
        input_path = self.input_var.get().strip()
        if not input_path:
            self.log("[ERROR] Please select an input folder")
            return
        if not os.path.exists(input_path):
            self.log(f"[ERROR] Input folder does not exist: {input_path}")
            return

        output_path = self.output_var.get().strip()
        if not output_path:
            output_path = os.path.join(input_path, "sliced_output")
            self.output_var.set(output_path)

        if not self.step_slice_var.get() and not self.step_categorize_var.get() and not self.step_meshes_var.get():
            self.log("[ERROR] Select at least one pipeline step")
            return

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.scan_btn.config(state=tk.DISABLED)

        thread = threading.Thread(
            target=self.run_pipeline,
            args=(input_path, output_path),
            daemon=True
        )
        thread.start()

    def run_pipeline(self, input_path, output_path):
        # Redirect print to log
        class LogRedirector:
            def __init__(self, gui):
                self.gui = gui
            def write(self, text):
                if text.strip():
                    self.gui.root.after(0, lambda t=text.strip(): self.gui.log(t))
            def flush(self):
                pass

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = LogRedirector(self)
        sys.stderr = LogRedirector(self)

        try:
            output_dir = Path(output_path)

            # Step 1: Slice
            if self.step_slice_var.get():
                self.root.after(0, lambda: self.log("=" * 50))
                self.root.after(0, lambda: self.log("[STEP 1] Batch Auto-Slice"))
                self.root.after(0, lambda: self.log("=" * 50))
                batch_auto_slice(input_path, output_path)

            # Step 2: Categorize
            if self.step_categorize_var.get():
                self.root.after(0, lambda: self.log(""))
                self.root.after(0, lambda: self.log("=" * 50))
                self.root.after(0, lambda: self.log("[STEP 2] Tile Categorizer"))
                self.root.after(0, lambda: self.log("=" * 50))

                preview = self.preview_var.get()
                tiles_dirs = self._find_dirs(output_dir, "tiles_")
                if tiles_dirs:
                    for td in tiles_dirs:
                        categorize_tiles(str(td), create_preview=preview)
                else:
                    print("No tiles directories found to categorize.")

            # Step 3: Meshes
            if self.step_meshes_var.get():
                self.root.after(0, lambda: self.log(""))
                self.root.after(0, lambda: self.log("=" * 50))
                self.root.after(0, lambda: self.log("[STEP 3] UE5 Mesh Generator"))
                self.root.after(0, lambda: self.log("=" * 50))

                self._generate_meshes(output_dir)

            self.root.after(0, lambda: self.log(""))
            self.root.after(0, lambda: self.log("=" * 50))
            self.root.after(0, lambda: self.log("[DONE] Pipeline complete!"))
            self.root.after(0, lambda: self.log(f"Output: {output_dir}"))
            self.root.after(0, lambda: self.log("=" * 50))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"[ERROR] {e}"))
            import traceback
            tb = traceback.format_exc()
            self.root.after(0, lambda: self.log(tb))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.root.after(0, self.pipeline_finished)

    def pipeline_finished(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.scan_btn.config(state=tk.NORMAL)

    def _find_dirs(self, output_dir, prefix):
        """Find subdirectories matching prefix that contain manifest.json."""
        results = []
        if not output_dir.exists():
            return results
        for root, dirs, files in os.walk(output_dir):
            root_p = Path(root)
            if root_p.name.startswith(prefix) and "manifest.json" in files:
                results.append(root_p)
        return sorted(results)

    def _generate_meshes(self, output_dir):
        tiles_dirs = self._find_dirs(output_dir, "tiles_")
        ships_dirs = self._find_dirs(output_dir, "ships_")

        if not tiles_dirs and not ships_dirs:
            print("No tiles or ships directories found for mesh generation.")
            return

        for td in tiles_dirs:
            mesh_out = td.parent / f"meshes_{td.name}"
            scale_key = "4x" if "4x" in td.name else "1x"
            cfg = SCALE_CONFIGS.get(scale_key, SCALE_CONFIGS["1x"])
            print(f"Generating tile meshes: {td.name} -> {mesh_out.name}")
            count = process_tiles(str(td), str(mesh_out), cfg["tile_size_uu"])
            print(f"  Generated {count} tile meshes")

        for sd in ships_dirs:
            mesh_out = sd.parent / f"meshes_{sd.name}"
            scale_key = "4x" if "4x" in sd.name else "1x"
            cfg = SCALE_CONFIGS.get(scale_key, SCALE_CONFIGS["1x"])
            print(f"Generating ship meshes: {sd.name} -> {mesh_out.name}")
            count = process_ships(str(sd), str(mesh_out), cfg["ship_size_uu"])
            print(f"  Generated {count} ship meshes")


def main():
    root = tk.Tk()
    app = SlicerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
