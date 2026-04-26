"""
ImageSqueezer - Compressore di immagini batch con drag & drop
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from PIL import Image, ImageTk

# Drag & drop support (optional, graceful fallback)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

APP_NAME = "Glu2k-Image-Resizer"
APP_VERSION = "1.0.0"
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
DEFAULT_QUALITY = 10
DEFAULT_RESIZE = 100


class ImageSqueezer:
    def __init__(self):
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("820x700")
        self.root.minsize(700, 600)
        self.root.configure(bg="#1e1e2e")

        # App icon
        self._set_icon()

        # State
        self.file_list = []
        self.processing = False
        self.output_dir = tk.StringVar(value="")
        self.quality = tk.IntVar(value=DEFAULT_QUALITY)
        self.resize_pct = tk.IntVar(value=DEFAULT_RESIZE)
        self.output_format = tk.StringVar(value="JPEG")
        self.prefix = tk.StringVar(value="compressed_")
        self.overwrite = tk.BooleanVar(value=False)

        self._build_ui()

    def _set_icon(self):
        try:
            icon_path = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Colors
        bg = "#1e1e2e"
        fg = "#cdd6f4"
        accent = "#89b4fa"
        surface = "#313244"
        green = "#a6e3a1"
        red = "#f38ba8"

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=bg, foreground=accent, font=("Segoe UI", 16, "bold"))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))
        style.configure("TCheckbutton", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=accent, font=("Segoe UI", 10, "bold"))

        main = ttk.Frame(self.root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main, text=f"{APP_NAME}", style="Title.TLabel").pack(pady=(0, 5))
        ttk.Label(main, text="Comprimi immagini in batch mantenendo l'aspect ratio").pack(pady=(0, 10))

        # Drop zone
        self.drop_frame = tk.Frame(main, bg=surface, highlightbackground=accent,
                                   highlightthickness=2, height=120, relief="groove")
        self.drop_frame.pack(fill=tk.X, pady=(0, 10))
        self.drop_frame.pack_propagate(False)

        drop_text = "Trascina qui le immagini o le cartelle"
        if not HAS_DND:
            drop_text = "Drag & Drop non disponibile - usa i pulsanti sotto"
        self.drop_label = tk.Label(self.drop_frame, text=drop_text,
                                   bg=surface, fg=fg, font=("Segoe UI", 12))
        self.drop_label.pack(expand=True)

        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_frame.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.drop_frame.dnd_bind("<<DragLeave>>", self._on_drag_leave)

        # Buttons row: add files / add folder / clear
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_row, text="Aggiungi File", command=self._add_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Aggiungi Cartella", command=self._add_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Rimuovi Selezionati", command=self._remove_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Svuota Lista", command=self._clear_list).pack(side=tk.LEFT)

        # File list
        list_frame = ttk.Frame(main)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("file", "size", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        self.tree.heading("file", text="File")
        self.tree.heading("size", text="Dimensione")
        self.tree.heading("status", text="Stato")
        self.tree.column("file", width=400)
        self.tree.column("size", width=100, anchor=tk.CENTER)
        self.tree.column("status", width=150, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_count_label = ttk.Label(main, text="0 immagini in lista")
        self.file_count_label.pack(anchor=tk.W, pady=(0, 5))

        # Settings
        settings = ttk.LabelFrame(main, text="Impostazioni", padding=10)
        settings.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Quality + Resize
        row1 = ttk.Frame(settings)
        row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row1, text="Qualita JPEG (%):").pack(side=tk.LEFT)
        self.quality_scale = ttk.Scale(row1, from_=1, to=100, variable=self.quality,
                                        orient=tk.HORIZONTAL, length=150,
                                        command=lambda v: self._update_quality_label())
        self.quality_scale.pack(side=tk.LEFT, padx=(5, 0))
        self.quality_label = ttk.Label(row1, text=f"{DEFAULT_QUALITY}%", width=5)
        self.quality_label.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(row1, text="Ridimensiona (%):").pack(side=tk.LEFT)
        self.resize_scale = ttk.Scale(row1, from_=5, to=100, variable=self.resize_pct,
                                       orient=tk.HORIZONTAL, length=150,
                                       command=lambda v: self._update_resize_label())
        self.resize_scale.pack(side=tk.LEFT, padx=(5, 0))
        self.resize_label = ttk.Label(row1, text=f"{DEFAULT_RESIZE}%", width=5)
        self.resize_label.pack(side=tk.LEFT, padx=(5, 0))

        # Row 2: Format + Prefix
        row2 = ttk.Frame(settings)
        row2.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row2, text="Formato output:").pack(side=tk.LEFT)
        fmt_combo = ttk.Combobox(row2, textvariable=self.output_format,
                                  values=["JPEG", "PNG", "WEBP"], state="readonly", width=8)
        fmt_combo.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(row2, text="Prefisso:").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.prefix, width=20).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Checkbutton(row2, text="Sovrascrivi originali", variable=self.overwrite).pack(side=tk.LEFT)

        # Row 3: Output directory
        row3 = ttk.Frame(settings)
        row3.pack(fill=tk.X)

        ttk.Label(row3, text="Cartella output:").pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.output_dir, width=45).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row3, text="Sfoglia", command=self._browse_output).pack(side=tk.LEFT)
        ttk.Label(row3, text="(vuoto = stessa cartella)", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(10, 0))

        # Progress
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(main, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 5))

        self.status_label = ttk.Label(main, text="Pronto", font=("Segoe UI", 9))
        self.status_label.pack(anchor=tk.W, pady=(0, 5))

        # Compress button
        self.compress_btn = ttk.Button(main, text="COMPRIMI TUTTO", style="Accent.TButton",
                                        command=self._start_compression)
        self.compress_btn.pack(fill=tk.X, ipady=8)

    def _update_quality_label(self):
        self.quality_label.config(text=f"{self.quality.get()}%")

    def _update_resize_label(self):
        self.resize_label.config(text=f"{self.resize_pct.get()}%")

    def _format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    def _add_files_to_list(self, paths):
        added = 0
        existing = {f for f in self.file_list}
        for p in paths:
            p = Path(p.strip().strip('{}').strip('"'))
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.suffix.lower() in SUPPORTED_FORMATS and str(f) not in existing:
                        self.file_list.append(str(f))
                        existing.add(str(f))
                        added += 1
            elif p.is_file() and p.suffix.lower() in SUPPORTED_FORMATS:
                if str(p) not in existing:
                    self.file_list.append(str(p))
                    existing.add(str(p))
                    added += 1

        self._refresh_tree()
        return added

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for fp in self.file_list:
            try:
                size = os.path.getsize(fp)
                size_str = self._format_size(size)
            except OSError:
                size_str = "?"
            self.tree.insert("", tk.END, values=(os.path.basename(fp), size_str, "In attesa"))
        self.file_count_label.config(text=f"{len(self.file_list)} immagini in lista")

    def _on_drop(self, event):
        self.drop_frame.configure(highlightbackground="#89b4fa")
        # Parse dropped data - tkdnd returns space-separated paths, braces around paths with spaces
        data = event.data
        paths = []
        # Handle brace-enclosed paths
        i = 0
        while i < len(data):
            if data[i] == '{':
                end = data.index('}', i)
                paths.append(data[i + 1:end])
                i = end + 2
            elif data[i] == ' ':
                i += 1
            else:
                end = data.find(' ', i)
                if end == -1:
                    end = len(data)
                paths.append(data[i:end])
                i = end + 1

        count = self._add_files_to_list(paths)
        self.status_label.config(text=f"{count} immagini aggiunte tramite drag & drop")

    def _on_drag_enter(self, event):
        self.drop_frame.configure(highlightbackground="#a6e3a1")

    def _on_drag_leave(self, event):
        self.drop_frame.configure(highlightbackground="#89b4fa")

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona immagini",
            filetypes=[
                ("Immagini", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
                ("Tutti i file", "*.*")
            ]
        )
        if files:
            count = self._add_files_to_list(files)
            self.status_label.config(text=f"{count} immagini aggiunte")

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Seleziona cartella con immagini")
        if folder:
            count = self._add_files_to_list([folder])
            self.status_label.config(text=f"{count} immagini trovate nella cartella")

    def _remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        indices = sorted([self.tree.index(item) for item in selected], reverse=True)
        for idx in indices:
            del self.file_list[idx]
        self._refresh_tree()

    def _clear_list(self):
        self.file_list.clear()
        self._refresh_tree()
        self.progress_var.set(0)
        self.status_label.config(text="Lista svuotata")

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Seleziona cartella di output")
        if folder:
            self.output_dir.set(folder)

    def _start_compression(self):
        if self.processing:
            return
        if not self.file_list:
            messagebox.showwarning("Nessuna immagine", "Aggiungi almeno un'immagine alla lista.")
            return

        self.processing = True
        self.compress_btn.config(state=tk.DISABLED)
        thread = threading.Thread(target=self._compress_all, daemon=True)
        thread.start()

    def _compress_all(self):
        total = len(self.file_list)
        quality = self.quality.get()
        resize_pct = self.resize_pct.get()
        out_format = self.output_format.get()
        prefix = self.prefix.get()
        overwrite = self.overwrite.get()
        output_dir = self.output_dir.get().strip()

        ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
        out_ext = ext_map.get(out_format, ".jpg")

        success = 0
        errors = 0
        total_saved = 0

        for i, filepath in enumerate(self.file_list):
            try:
                self.root.after(0, self._update_status,
                                f"Comprimendo {i + 1}/{total}: {os.path.basename(filepath)}")

                original_size = os.path.getsize(filepath)

                img = Image.open(filepath)

                # Convert RGBA to RGB for JPEG
                if out_format == "JPEG" and img.mode in ("RGBA", "P", "LA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                    img = background
                elif out_format == "JPEG" and img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize maintaining aspect ratio
                if resize_pct < 100:
                    new_w = max(1, int(img.width * resize_pct / 100))
                    new_h = max(1, int(img.height * resize_pct / 100))
                    img = img.resize((new_w, new_h), Image.LANCZOS)

                # Determine output path
                src_path = Path(filepath)
                if overwrite:
                    out_path = src_path.with_suffix(out_ext)
                elif output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    out_path = Path(output_dir) / f"{prefix}{src_path.stem}{out_ext}"
                else:
                    out_path = src_path.parent / f"{prefix}{src_path.stem}{out_ext}"

                # Save with compression
                save_kwargs = {}
                if out_format == "JPEG":
                    save_kwargs = {"quality": quality, "optimize": True}
                elif out_format == "PNG":
                    save_kwargs = {"optimize": True}
                elif out_format == "WEBP":
                    save_kwargs = {"quality": quality, "method": 6}

                img.save(str(out_path), out_format, **save_kwargs)

                new_size = os.path.getsize(str(out_path))
                saved = original_size - new_size
                total_saved += max(0, saved)
                pct = (new_size / original_size * 100) if original_size > 0 else 0

                self.root.after(0, self._update_item, i,
                                f"{self._format_size(new_size)} ({pct:.0f}%)")
                success += 1

            except Exception as e:
                self.root.after(0, self._update_item, i, f"Errore: {str(e)[:30]}")
                errors += 1

            self.root.after(0, self._update_progress, (i + 1) / total * 100)

        saved_str = self._format_size(total_saved)
        msg = f"Completato! {success}/{total} compressi, {saved_str} risparmiati"
        if errors:
            msg += f", {errors} errori"
        self.root.after(0, self._update_status, msg)
        self.root.after(0, self._finish_compression)

    def _update_status(self, text):
        self.status_label.config(text=text)

    def _update_progress(self, value):
        self.progress_var.set(value)

    def _update_item(self, index, status_text):
        items = self.tree.get_children()
        if index < len(items):
            item = items[index]
            values = self.tree.item(item, "values")
            self.tree.item(item, values=(values[0], values[1], status_text))

    def _finish_compression(self):
        self.processing = False
        self.compress_btn.config(state=tk.NORMAL)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageSqueezer()
    app.run()
