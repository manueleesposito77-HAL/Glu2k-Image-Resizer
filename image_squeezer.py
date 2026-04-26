"""
Glu2k-Image-Resizer - Compressore di immagini batch con drag & drop
Auto-rotazione EXIF, anteprima live, target dimensione file, tasto STOP
"""

import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
from io import BytesIO

from PIL import Image, ImageTk, ImageOps

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

APP_NAME = "Glu2k-Image-Resizer"
APP_VERSION = "1.4.0"
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
DEFAULT_TARGET_PCT = 10
DEFAULT_RESIZE = 50

C = {
    "base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b",
    "s0": "#313244", "s1": "#45475a", "s2": "#585b70",
    "text": "#cdd6f4", "sub": "#a6adc8", "overlay": "#6c7086",
    "blue": "#89b4fa", "green": "#a6e3a1", "red": "#f38ba8",
    "yellow": "#f9e2af", "lavender": "#b4befe", "peach": "#fab387",
    "teal": "#94e2d5", "pink": "#f5c2e7",
}

LOG_DIR = os.path.join(os.path.expanduser("~"), ".glu2k-image-resizer")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"resizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logger = logging.getLogger("Glu2k-Image-Resizer")
logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(_fh)
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_ch)
logger.info(f"=== {APP_NAME} v{APP_VERSION} ===")
logger.info(f"Log: {LOG_FILE} | DnD: {HAS_DND}")


def _rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class ModernButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, bg=C["s1"], fg=C["text"],
                 hover_bg=C["s2"], canvas_bg=None, font=("Segoe UI", 10),
                 width=120, height=36, radius=10):
        if canvas_bg is not None:
            cbg = canvas_bg
        else:
            try:
                cbg = parent.cget("bg")
            except Exception:
                cbg = C["base"]
        super().__init__(parent, width=width, height=height, bg=cbg, highlightthickness=0)
        self._cmd = command
        self._bg = bg
        self._fg = fg
        self._bhover = hover_bg
        self._text = text
        self._font = font
        self._r = radius
        self._bw = width
        self._bh = height
        self._on = True
        self._draw(bg)
        self.bind("<Enter>", lambda e: self._draw(self._bhover) if self._on else None)
        self.bind("<Leave>", lambda e: self._draw(self._bg) if self._on else None)
        self.bind("<ButtonRelease-1>", self._click)

    def _draw(self, fill):
        self.delete("all")
        _rounded_rect(self, 1, 1, self._bw - 1, self._bh - 1, self._r, fill=fill, outline=fill)
        c = self._fg if self._on else C["s2"]
        self.create_text(self._bw // 2, self._bh // 2, text=self._text, fill=c, font=self._font)

    def _click(self, e):
        if self._on and self._cmd:
            self._cmd()

    def set_enabled(self, on):
        self._on = on
        self._draw(self._bg)


class ImageSqueezer:
    def __init__(self):
        self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1100x920")
        self.root.minsize(1000, 800)
        self.root.configure(bg=C["base"])
        self._set_icon()

        self.file_list = []
        self.processing = False
        self.stop_requested = False
        self.output_dir = tk.StringVar(value="")
        self.target_pct = tk.IntVar(value=DEFAULT_TARGET_PCT)
        self.resize_pct = tk.IntVar(value=100)
        self.output_format = tk.StringVar(value="JPEG")
        self.prefix = tk.StringVar(value="compressed_")
        self.overwrite = tk.BooleanVar(value=False)
        self.strip_metadata = tk.BooleanVar(value=True)
        self.max_width = tk.IntVar(value=1920)
        self.use_max_width = tk.BooleanVar(value=True)
        self.auto_rotate = tk.BooleanVar(value=True)

        self._preview_before = None
        self._preview_after = None

        self._build_ui()
        logger.info("UI inizializzata")

    def _set_icon(self):
        try:
            p = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(__file__)), "icon.ico")
            if os.path.exists(p):
                self.root.iconbitmap(p)
        except Exception:
            pass

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview", background=C["mantle"], foreground=C["text"],
                        fieldbackground=C["mantle"], borderwidth=0, font=("Segoe UI", 9), rowheight=24)
        style.configure("Dark.Treeview.Heading", background=C["s0"], foreground=C["blue"],
                        font=("Segoe UI", 9, "bold"), borderwidth=0, relief="flat")
        style.map("Dark.Treeview.Heading", background=[("active", C["s1"])])
        style.map("Dark.Treeview", background=[("selected", C["s1"])], foreground=[("selected", C["blue"])])
        style.configure("Dark.Horizontal.TScale", background=C["mantle"], troughcolor=C["s0"], sliderlength=18)
        style.configure("Blue.Horizontal.TProgressbar", background=C["blue"], troughcolor=C["s0"],
                        borderwidth=0, lightcolor=C["blue"], darkcolor=C["blue"])
        style.configure("Dark.Vertical.TScrollbar", background=C["s0"], troughcolor=C["mantle"],
                        borderwidth=0, arrowsize=0)
        style.configure("Dark.TCombobox", fieldbackground=C["s0"], background=C["s0"],
                        foreground=C["text"], selectbackground=C["s1"], selectforeground=C["text"])
        style.map("Dark.TCombobox", fieldbackground=[("readonly", C["s0"])],
                  foreground=[("readonly", C["text"])])

        root = self.root

        # ── Top bar ──
        topbar = tk.Frame(root, bg=C["crust"], height=50)
        topbar.pack(fill=tk.X)
        topbar.pack_propagate(False)
        tk.Label(topbar, text=f"  {APP_NAME}", bg=C["crust"], fg=C["blue"],
                 font=("Segoe UI Semibold", 16)).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(topbar, text=f"v{APP_VERSION}", bg=C["crust"], fg=C["overlay"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 0), pady=(6, 0))
        ModernButton(topbar, text="Apri Log", command=self._open_log, width=80, height=30,
                     font=("Segoe UI", 9), bg=C["s0"], hover_bg=C["s1"],
                     canvas_bg=C["crust"]).pack(side=tk.RIGHT, padx=12, pady=10)

        content = tk.Frame(root, bg=C["base"], padx=16, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        # ── Top section: drop zone (left) + settings (right) ──
        top_section = tk.Frame(content, bg=C["base"])
        top_section.pack(fill=tk.X, pady=(0, 8))

        self._build_drop_zone(top_section)
        self._build_settings_panel(top_section)

        # ── Action buttons ──
        self._build_action_buttons(content)

        # ── File list ──
        self._build_file_list(content)

        # ── Estimate row ──
        est_row = tk.Frame(content, bg=C["base"])
        est_row.pack(fill=tk.X, pady=(0, 6))
        self.estimate_label = tk.Label(est_row, text="", bg=C["base"], fg=C["peach"],
                                        font=("Segoe UI", 10, "bold"), anchor="w")
        self.estimate_label.pack(side=tk.LEFT)

        # ── Preview panel (full width, big) ──
        self._build_preview_panel(content)

        # ── Bottom: progress + buttons ──
        self._build_bottom(content)

    # ── Drop zone ──

    def _build_drop_zone(self, parent):
        frame = tk.Frame(parent, bg=C["mantle"], highlightthickness=2, highlightbackground=C["s1"])
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        inner = tk.Frame(frame, bg=C["mantle"], height=140)
        inner.pack(fill=tk.BOTH, expand=True)
        inner.pack_propagate(False)

        center = tk.Frame(inner, bg=C["mantle"])
        center.place(relx=0.5, rely=0.5, anchor="center")

        ic = tk.Canvas(center, width=44, height=44, bg=C["mantle"], highlightthickness=0)
        ic.pack()
        ic.create_oval(2, 2, 42, 42, fill=C["s0"], outline=C["s1"])
        ic.create_text(22, 22, text="\u2b07", fill=C["blue"], font=("Segoe UI", 16))

        txt = "Trascina qui immagini o cartelle" if HAS_DND else "Usa i pulsanti per aggiungere"
        tk.Label(center, text=txt, bg=C["mantle"], fg=C["sub"], font=("Segoe UI", 10)).pack(pady=(6, 0))
        tk.Label(center, text="JPG, PNG, BMP, TIFF, WEBP", bg=C["mantle"],
                 fg=C["overlay"], font=("Segoe UI", 8)).pack()

        self.drop_frame = frame
        if HAS_DND:
            for w in [frame, inner, center, ic]:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)
                w.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                w.dnd_bind("<<DragLeave>>", self._on_drag_leave)

    # ── Settings panel (top right) ──

    def _build_settings_panel(self, parent):
        outer = tk.Frame(parent, bg=C["mantle"], highlightthickness=1,
                         highlightbackground=C["s1"], width=560)
        outer.pack(side=tk.RIGHT, fill=tk.Y)
        outer.pack_propagate(False)

        tb = tk.Frame(outer, bg=C["s0"])
        tb.pack(fill=tk.X)
        tk.Label(tb, text="  IMPOSTAZIONI", bg=C["s0"], fg=C["blue"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=3)

        body = tk.Frame(outer, bg=C["mantle"], padx=10, pady=6)
        body.pack(fill=tk.BOTH, expand=True)

        # Row 1: Target + Scale
        r1 = tk.Frame(body, bg=C["mantle"])
        r1.pack(fill=tk.X, pady=(0, 4))
        tk.Label(r1, text="Dimensione finale:", bg=C["mantle"], fg=C["text"], font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Scale(r1, from_=1, to=100, variable=self.target_pct, orient=tk.HORIZONTAL, length=180,
                  style="Dark.Horizontal.TScale", command=lambda v: self._on_settings_change()).pack(side=tk.LEFT, padx=(4, 0))
        self.target_label = tk.Label(r1, text=f"{DEFAULT_TARGET_PCT}%", bg=C["mantle"],
                                      fg=C["yellow"], font=("Segoe UI", 10, "bold"), width=4)
        self.target_label.pack(side=tk.LEFT, padx=(4, 0))

        # Row 2: Max width + EXIF + Rotate
        r2 = tk.Frame(body, bg=C["mantle"])
        r2.pack(fill=tk.X, pady=(0, 4))
        self._check(r2, "Max W:", self.use_max_width).pack(side=tk.LEFT)
        tk.Entry(r2, textvariable=self.max_width, width=5, bg=C["s0"], fg=C["text"],
                 insertbackground=C["text"], relief="flat", font=("Segoe UI", 10),
                 highlightthickness=1, highlightcolor=C["blue"],
                 highlightbackground=C["s1"]).pack(side=tk.LEFT, padx=(2, 12))
        self._check(r2, "No EXIF", self.strip_metadata).pack(side=tk.LEFT, padx=(0, 12))
        self._check(r2, "Auto-rotazione", self.auto_rotate).pack(side=tk.LEFT)

        # Row 3: Format + Prefix + Overwrite
        r3 = tk.Frame(body, bg=C["mantle"])
        r3.pack(fill=tk.X, pady=(0, 4))
        tk.Label(r3, text="Fmt:", bg=C["mantle"], fg=C["text"], font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Combobox(r3, textvariable=self.output_format, values=["JPEG", "PNG", "WEBP"],
                     state="readonly", width=6, style="Dark.TCombobox",
                     font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(4, 12))
        tk.Label(r3, text="Prefisso:", bg=C["mantle"], fg=C["text"], font=("Segoe UI", 10)).pack(side=tk.LEFT)
        tk.Entry(r3, textvariable=self.prefix, width=14, bg=C["s0"], fg=C["text"],
                 insertbackground=C["text"], relief="flat", font=("Segoe UI", 10),
                 highlightthickness=1, highlightcolor=C["blue"],
                 highlightbackground=C["s1"]).pack(side=tk.LEFT, padx=(4, 12))
        self._check(r3, "Sovrascrivi", self.overwrite).pack(side=tk.LEFT)

        # Row 4: Output dir
        r4 = tk.Frame(body, bg=C["mantle"])
        r4.pack(fill=tk.X)
        tk.Label(r4, text="Output:", bg=C["mantle"], fg=C["text"], font=("Segoe UI", 10)).pack(side=tk.LEFT)
        tk.Entry(r4, textvariable=self.output_dir, width=28, bg=C["s0"], fg=C["text"],
                 insertbackground=C["text"], relief="flat", font=("Segoe UI", 10),
                 highlightthickness=1, highlightcolor=C["blue"],
                 highlightbackground=C["s1"]).pack(side=tk.LEFT, padx=(4, 4))
        ModernButton(r4, text="...", command=self._browse_output, width=32, height=26,
                     font=("Segoe UI", 10), bg=C["s0"], hover_bg=C["s1"],
                     canvas_bg=C["mantle"]).pack(side=tk.LEFT)

    # ── Action buttons ──

    def _build_action_buttons(self, parent):
        row = tk.Frame(parent, bg=C["base"])
        row.pack(fill=tk.X, pady=(0, 6))
        for text, cmd in [("Aggiungi File", self._add_files), ("Aggiungi Cartella", self._add_folder),
                          ("Rimuovi Selezionati", self._remove_selected), ("Svuota Lista", self._clear_list),
                          ("Trova Duplicati", self._find_duplicates)]:
            ModernButton(row, text=text, command=cmd, width=135, height=30,
                         font=("Segoe UI", 9), radius=8).pack(side=tk.LEFT, padx=(0, 6))
        self.file_count_label = tk.Label(row, text="0 immagini", bg=C["base"],
                                          fg=C["sub"], font=("Segoe UI", 9))
        self.file_count_label.pack(side=tk.RIGHT, padx=(0, 4))

    # ── File list ──

    def _build_file_list(self, parent):
        frame = tk.Frame(parent, bg=C["s0"], highlightthickness=1, highlightbackground=C["s1"])
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        cols = ("file", "dims", "size", "estimate", "status")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=6, style="Dark.Treeview")
        self.tree.heading("file", text="File")
        self.tree.heading("dims", text="Dimensioni")
        self.tree.heading("size", text="Peso")
        self.tree.heading("estimate", text="Stima output")
        self.tree.heading("status", text="Stato")
        self.tree.column("file", width=280)
        self.tree.column("dims", width=100, anchor=tk.CENTER)
        self.tree.column("size", width=80, anchor=tk.CENTER)
        self.tree.column("estimate", width=90, anchor=tk.CENTER)
        self.tree.column("status", width=200, anchor=tk.CENTER)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview, style="Dark.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Show preview when selecting a file
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    # ── Preview panel (full width, bottom) ──

    def _build_preview_panel(self, parent):
        outer = tk.Frame(parent, bg=C["mantle"], highlightthickness=1, highlightbackground=C["s1"])
        outer.pack(fill=tk.X, pady=(0, 8))

        tb = tk.Frame(outer, bg=C["s0"])
        tb.pack(fill=tk.X)
        tk.Label(tb, text="  ANTEPRIMA", bg=C["s0"], fg=C["teal"],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6, pady=3)
        self.preview_title_info = tk.Label(tb, text="", bg=C["s0"], fg=C["sub"],
                                            font=("Segoe UI", 8))
        self.preview_title_info.pack(side=tk.LEFT, padx=(10, 0))

        preview_body = tk.Frame(outer, bg=C["mantle"], padx=10, pady=8)
        preview_body.pack(fill=tk.X)

        # PRIMA (left half)
        before_frame = tk.Frame(preview_body, bg=C["mantle"])
        before_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        before_header = tk.Frame(before_frame, bg=C["mantle"])
        before_header.pack(fill=tk.X)
        tk.Label(before_header, text="PRIMA", bg=C["mantle"], fg=C["red"],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.preview_before_info = tk.Label(before_header, text="", bg=C["mantle"],
                                             fg=C["sub"], font=("Segoe UI", 8))
        self.preview_before_info.pack(side=tk.RIGHT)

        self.preview_before_canvas = tk.Canvas(before_frame, bg=C["crust"],
                                                highlightthickness=0, height=160)
        self.preview_before_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # DOPO (right half)
        after_frame = tk.Frame(preview_body, bg=C["mantle"])
        after_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        after_header = tk.Frame(after_frame, bg=C["mantle"])
        after_header.pack(fill=tk.X)
        tk.Label(after_header, text="DOPO", bg=C["mantle"], fg=C["green"],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.preview_after_info = tk.Label(after_header, text="", bg=C["mantle"],
                                            fg=C["sub"], font=("Segoe UI", 8))
        self.preview_after_info.pack(side=tk.RIGHT)

        self.preview_after_canvas = tk.Canvas(after_frame, bg=C["crust"],
                                               highlightthickness=0, height=160)
        self.preview_after_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    # ── Bottom ──

    def _build_bottom(self, parent):
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(parent, variable=self.progress_var, maximum=100,
                        style="Blue.Horizontal.TProgressbar").pack(fill=tk.X, pady=(0, 4))

        status_row = tk.Frame(parent, bg=C["base"])
        status_row.pack(fill=tk.X, pady=(0, 6))
        self.status_label = tk.Label(status_row, text="Pronto — seleziona un file per l'anteprima",
                                      bg=C["base"], fg=C["sub"], font=("Segoe UI", 9), anchor="w")
        self.status_label.pack(side=tk.LEFT)
        tk.Label(status_row, text=f"Log: ...{LOG_FILE[-40:]}", bg=C["base"],
                 fg=C["overlay"], font=("Segoe UI", 7), anchor="e").pack(side=tk.RIGHT)

        btn_row = tk.Frame(parent, bg=C["base"])
        btn_row.pack(fill=tk.X)

        self.compress_btn = ModernButton(
            btn_row, text="COMPRIMI  TUTTO", command=self._start_compression,
            width=940, height=48, font=("Segoe UI", 14, "bold"),
            bg=C["blue"], fg=C["crust"], hover_bg=C["lavender"], radius=12
        )
        self.compress_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.stop_btn = ModernButton(
            btn_row, text="STOP", command=self._stop_compression,
            width=120, height=48, font=("Segoe UI", 14, "bold"),
            bg=C["s1"], fg=C["s2"], hover_bg=C["s1"], radius=12
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=(8, 0))

    # ── Helpers ──

    def _check(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var, bg=C["mantle"],
                              fg=C["text"], selectcolor=C["s0"], activebackground=C["mantle"],
                              activeforeground=C["text"], font=("Segoe UI", 10), highlightthickness=0)

    def _on_settings_change(self):
        self.target_label.config(text=f"{self.target_pct.get()}%")
        self._update_estimates()

    @staticmethod
    def _format_size(b):
        if b < 1024:
            return f"{b} B"
        if b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        return f"{b / (1024 * 1024):.2f} MB"

    def _open_log(self):
        try:
            os.startfile(LOG_FILE)
        except Exception:
            try:
                os.startfile(LOG_DIR)
            except Exception:
                messagebox.showinfo("Log", f"File di log:\n{LOG_FILE}")

    # ── Estimates ──

    def _update_estimates(self):
        if not self.file_list:
            self.estimate_label.config(text="")
            return
        target = self.target_pct.get() / 100.0
        total_orig = total_est = 0
        items = self.tree.get_children()
        for i, fp in enumerate(self.file_list):
            try:
                size = os.path.getsize(fp)
                est = int(size * target)
                total_orig += size
                total_est += est
                if i < len(items):
                    vals = list(self.tree.item(items[i], "values"))
                    vals[3] = self._format_size(est)
                    self.tree.item(items[i], values=vals)
            except OSError:
                pass
        self.estimate_label.config(
            text=f"Stima: {self._format_size(total_orig)} -> {self._format_size(total_est)} "
                 f"(target {self.target_pct.get()}%)")

    # ── Preview ──

    def _on_tree_select(self, event):
        """Show preview of selected file from the list (before compression)."""
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if idx >= len(self.file_list):
            return
        filepath = self.file_list[idx]

        try:
            img = Image.open(filepath)
            # Apply EXIF rotation for correct preview
            if self.auto_rotate.get():
                try:
                    img = ImageOps.exif_transpose(img) or img
                except Exception:
                    pass

            orig_size = os.path.getsize(filepath)
            self.preview_title_info.config(text=os.path.basename(filepath))

            # Show "before" preview
            self._render_canvas(self.preview_before_canvas, img, "before")
            self.preview_before_info.config(
                text=f"{img.width}x{img.height} | {self._format_size(orig_size)}")

            # Generate a quick "after" simulation
            target_pct = self.target_pct.get()
            resize_pct = self.resize_pct.get()
            est_size = int(orig_size * target_pct / 100)

            sim = img.copy()
            if sim.mode in ("RGBA", "P", "LA", "PA"):
                bg = Image.new("RGB", sim.size, (255, 255, 255))
                if sim.mode == "P":
                    sim = sim.convert("RGBA")
                if "A" in sim.mode:
                    bg.paste(sim, mask=sim.split()[-1])
                else:
                    bg.paste(sim)
                sim = bg
            elif sim.mode != "RGB":
                sim = sim.convert("RGB")

            if resize_pct < 100:
                nw = max(1, int(sim.width * resize_pct / 100))
                nh = max(1, int(sim.height * resize_pct / 100))
                sim = sim.resize((nw, nh), Image.LANCZOS)

            if self.use_max_width.get() and sim.width > self.max_width.get():
                ratio = self.max_width.get() / sim.width
                sim = sim.resize((self.max_width.get(), max(1, int(sim.height * ratio))), Image.LANCZOS)

            # Quick compress to show approximate result
            fmt = self.output_format.get()
            if fmt in ("JPEG", "WEBP"):
                buf = BytesIO()
                kw = {"quality": max(1, target_pct), "optimize": True}
                if fmt == "JPEG":
                    kw["subsampling"] = "4:2:0"
                sim.save(buf, fmt, **kw)
                sim_data = buf.getvalue()
                sim_preview = Image.open(BytesIO(sim_data))
                sim_size = len(sim_data)
            else:
                sim_preview = sim
                sim_size = est_size

            self._render_canvas(self.preview_after_canvas, sim_preview, "after")
            self.preview_after_info.config(
                text=f"{sim.width}x{sim.height} | ~{self._format_size(sim_size)}")

        except Exception as e:
            logger.debug(f"Preview error: {e}")

    def _show_preview(self, before_img, after_img, orig_size, new_size):
        """Update preview during compression."""
        self._render_canvas(self.preview_before_canvas, before_img, "before")
        self.preview_before_info.config(
            text=f"{before_img.width}x{before_img.height} | {self._format_size(orig_size)}")
        self._render_canvas(self.preview_after_canvas, after_img, "after")
        self.preview_after_info.config(
            text=f"{after_img.width}x{after_img.height} | {self._format_size(new_size)}")

    def _render_canvas(self, canvas, img, tag):
        """Render an image centered on a canvas, fitting it."""
        canvas.update_idletasks()
        cw = max(canvas.winfo_width(), 200)
        ch = max(canvas.winfo_height(), 120)
        thumb = img.copy()
        thumb.thumbnail((cw - 8, ch - 8), Image.LANCZOS)
        photo = ImageTk.PhotoImage(thumb)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center")
        # Store ref to prevent GC
        if tag == "before":
            self._preview_before = photo
        else:
            self._preview_after = photo

    def _clear_preview(self):
        for canvas in [self.preview_before_canvas, self.preview_after_canvas]:
            canvas.delete("all")
        self.preview_before_info.config(text="")
        self.preview_after_info.config(text="")
        self.preview_title_info.config(text="")
        self._preview_before = None
        self._preview_after = None

    # ── File management ──

    def _add_files_to_list(self, paths):
        added = 0
        existing = set(self.file_list)
        for p in paths:
            p = Path(p.strip().strip('{}').strip('"'))
            if p.is_dir():
                logger.info(f"Scansione: {p}")
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
        logger.info(f"+{added}, totale: {len(self.file_list)}")
        self._refresh_tree()
        self._update_estimates()
        return added

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for fp in self.file_list:
            try:
                size = os.path.getsize(fp)
                size_str = self._format_size(size)
            except OSError:
                size_str = "?"
            dims = ""
            try:
                with Image.open(fp) as im:
                    dims = f"{im.width}x{im.height}"
            except Exception:
                pass
            self.tree.insert("", tk.END, values=(os.path.basename(fp), dims, size_str, "", "In attesa"))
        self.file_count_label.config(text=f"{len(self.file_list)} immagini")

    def _on_drop(self, event):
        self.drop_frame.configure(highlightbackground=C["s1"])
        data = event.data
        paths = []
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
        logger.info(f"Drop: {len(paths)} elementi")
        count = self._add_files_to_list(paths)
        self.status_label.config(text=f"{count} immagini aggiunte via drag & drop")

    def _on_drag_enter(self, event):
        self.drop_frame.configure(highlightbackground=C["green"])

    def _on_drag_leave(self, event):
        self.drop_frame.configure(highlightbackground=C["s1"])

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona immagini",
            filetypes=[("Immagini", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"), ("Tutti", "*.*")])
        if files:
            n = self._add_files_to_list(files)
            self.status_label.config(text=f"{n} immagini aggiunte")

    def _add_folder(self):
        d = filedialog.askdirectory(title="Seleziona cartella")
        if d:
            n = self._add_files_to_list([d])
            self.status_label.config(text=f"{n} immagini trovate")

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        for idx in sorted([self.tree.index(s) for s in sel], reverse=True):
            del self.file_list[idx]
        self._refresh_tree()
        self._update_estimates()
        self._clear_preview()

    def _clear_list(self):
        self.file_list.clear()
        self._refresh_tree()
        self.progress_var.set(0)
        self._clear_preview()
        self.estimate_label.config(text="")
        self.status_label.config(text="Lista svuotata")

    def _browse_output(self):
        d = filedialog.askdirectory(title="Cartella di output")
        if d:
            self.output_dir.set(d)

    # ── Compression ──

    def _start_compression(self):
        if self.processing or not self.file_list:
            if not self.file_list:
                messagebox.showwarning("Nessuna immagine", "Aggiungi almeno un'immagine.")
            return
        self.processing = True
        self.stop_requested = False
        self.compress_btn.set_enabled(False)
        self.stop_btn._bg = C["red"]
        self.stop_btn._fg = C["crust"]
        self.stop_btn._bhover = C["pink"]
        self.stop_btn._draw(C["red"])
        threading.Thread(target=self._compress_all, daemon=True).start()

    def _stop_compression(self):
        if self.processing:
            self.stop_requested = True
            logger.info("STOP richiesto")
            self.status_label.config(text="Fermando...")

    def _compress_to_target(self, img, out_format, target_bytes):
        details = []
        if out_format == "PNG":
            if img.mode == "RGB":
                img_q = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            else:
                img_q = img
            buf = BytesIO()
            img_q.save(buf, "PNG", optimize=True)
            data = buf.getvalue()
            details.append(f"PNG opt: {self._format_size(len(data))}")
            return data, 0, details

        lo, hi = 1, 95
        best_data = None
        best_q = lo
        for _ in range(12):
            q = (lo + hi) // 2
            buf = BytesIO()
            kw = {"quality": q, "optimize": True}
            if out_format == "JPEG":
                kw["subsampling"] = "4:2:0"
            elif out_format == "WEBP":
                kw["method"] = 4
            img.save(buf, out_format, **kw)
            size = buf.tell()
            data = buf.getvalue()
            if best_data is None or abs(size - target_bytes) < abs(len(best_data) - target_bytes):
                best_data = data
                best_q = q
            if size > target_bytes:
                hi = q - 1
            elif size < target_bytes:
                lo = q + 1
            else:
                break
            if lo > hi:
                break
        details.append(f"{out_format} q={best_q} -> {self._format_size(len(best_data))}")
        return best_data, best_q, details

    def _compress_image(self, filepath, target_pct, resize_pct, out_format,
                        strip_meta, use_max_w, max_w, do_rotate):
        original_size = os.path.getsize(filepath)
        target_bytes = int(original_size * target_pct / 100)
        details = []
        img = Image.open(filepath)
        orig_mode = img.mode
        details.append(f"Input: {img.width}x{img.height} {orig_mode} {self._format_size(original_size)}")
        details.append(f"Target: {self._format_size(target_bytes)} ({target_pct}%)")

        if do_rotate:
            try:
                rotated = ImageOps.exif_transpose(img)
                if rotated is not img:
                    img = rotated
                    details.append(f"Ruotato EXIF: {img.width}x{img.height}")
            except Exception:
                pass

        before_preview = img.copy()

        if strip_meta:
            c = img.copy()
            img.close()
            img = c
            details.append("EXIF rimossi")

        if out_format == "JPEG":
            if img.mode in ("RGBA", "P", "LA", "PA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if "A" in img.mode:
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
                details.append(f"Modo: {orig_mode} -> RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")
                details.append(f"Modo: {orig_mode} -> RGB")

        if resize_pct < 100:
            nw = max(1, int(img.width * resize_pct / 100))
            nh = max(1, int(img.height * resize_pct / 100))
            img = img.resize((nw, nh), Image.LANCZOS)
            details.append(f"Scala {resize_pct}%: {nw}x{nh}")

        if use_max_w and img.width > max_w:
            ratio = max_w / img.width
            nw, nh = max_w, max(1, int(img.height * ratio))
            img = img.resize((nw, nh), Image.LANCZOS)
            details.append(f"Max W {max_w}px: {nw}x{nh}")

        data, q_used, comp_details = self._compress_to_target(img, out_format, target_bytes)
        details.extend(comp_details)

        new_size = len(data)
        pct = (new_size / original_size * 100) if original_size > 0 else 0
        details.append(f"Risultato: {self._format_size(new_size)} ({pct:.1f}%)")
        if new_size >= original_size:
            details.append("WARNING: output >= originale!")

        after_preview = Image.open(BytesIO(data)).copy()
        return original_size, new_size, data, before_preview, after_preview, details

    def _compress_all(self):
        total = len(self.file_list)
        target_pct = self.target_pct.get()
        resize_pct = self.resize_pct.get()
        out_format = self.output_format.get()
        prefix = self.prefix.get()
        overwrite = self.overwrite.get()
        output_dir = self.output_dir.get().strip()
        strip_meta = self.strip_metadata.get()
        use_max_w = self.use_max_width.get()
        max_w = self.max_width.get()
        do_rotate = self.auto_rotate.get()

        ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
        out_ext = ext_map.get(out_format, ".jpg")

        logger.info("=" * 60)
        logger.info(f"COMPRESSIONE: {total} file | fmt={out_format} target={target_pct}% "
                     f"scala={resize_pct}% maxw={'%d' % max_w if use_max_w else 'off'}")
        logger.info("=" * 60)

        success = errors = warnings = 0
        total_orig = total_comp = 0

        for i, filepath in enumerate(self.file_list):
            if self.stop_requested:
                logger.info(f"STOP dopo {i}/{total}")
                self.root.after(0, self._update_status, f"Interrotto! {success} compressi su {total}")
                break
            try:
                self.root.after(0, self._update_status, f"[{i + 1}/{total}] {os.path.basename(filepath)}")
                self.root.after(0, self._update_preview_title, os.path.basename(filepath))

                src = Path(filepath)
                if overwrite:
                    out_path = src.with_suffix(out_ext)
                elif output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    out_path = Path(output_dir) / f"{prefix}{src.stem}{out_ext}"
                else:
                    out_path = src.parent / f"{prefix}{src.stem}{out_ext}"

                logger.info(f"[{i + 1}/{total}] {filepath}")

                orig_size, new_size, data, before_img, after_img, details = \
                    self._compress_image(filepath, target_pct, resize_pct, out_format,
                                         strip_meta, use_max_w, max_w, do_rotate)

                with open(str(out_path), "wb") as f:
                    f.write(data)

                for d in details:
                    logger.debug(f"  {d}")

                self.root.after(0, self._show_preview, before_img, after_img, orig_size, new_size)

                total_orig += orig_size
                total_comp += new_size
                pct = (new_size / orig_size * 100) if orig_size > 0 else 0

                if new_size >= orig_size:
                    warnings += 1
                    st = f"{self._format_size(new_size)} ({pct:.0f}%) WARN"
                else:
                    st = f"{self._format_size(new_size)} ({pct:.0f}%) -{self._format_size(orig_size - new_size)}"

                self.root.after(0, self._update_item, i, st)
                success += 1
            except Exception as e:
                logger.error(f"  ERRORE: {e}", exc_info=True)
                self.root.after(0, self._update_item, i, f"Errore: {str(e)[:30]}")
                errors += 1
            self.root.after(0, self._update_progress, (i + 1) / total * 100)

        if not self.stop_requested:
            total_saved = total_orig - total_comp
            pct = (total_comp / total_orig * 100) if total_orig > 0 else 0
            logger.info(f"DONE: {success}/{total} | -{self._format_size(max(0, total_saved))}")
            msg = (f"Completato! {success}/{total} | "
                   f"{self._format_size(total_orig)} -> {self._format_size(total_comp)} | "
                   f"-{self._format_size(max(0, total_saved))} ({100 - pct:.0f}%)")
            if errors:
                msg += f" | {errors} errori"
            self.root.after(0, self._update_status, msg)
            self.root.after(0, self._show_completion_dialog,
                            success, total, errors, warnings,
                            total_orig, total_comp)

        self.root.after(0, self._finish)

    def _update_status(self, text):
        self.status_label.config(text=text)

    def _update_progress(self, value):
        self.progress_var.set(value)

    def _update_preview_title(self, name):
        self.preview_title_info.config(text=name)

    def _update_item(self, index, status_text):
        items = self.tree.get_children()
        if index < len(items):
            vals = list(self.tree.item(items[index], "values"))
            vals[4] = status_text
            self.tree.item(items[index], values=vals)
            self.tree.see(items[index])

    def _finish(self):
        self.processing = False
        self.stop_requested = False
        self.compress_btn.set_enabled(True)
        self.stop_btn._bg = C["s1"]
        self.stop_btn._fg = C["s2"]
        self.stop_btn._bhover = C["s1"]
        self.stop_btn._draw(C["s1"])

    # ── Completion dialog ──

    def _show_completion_dialog(self, success, total, errors, warnings,
                                total_orig, total_comp):
        total_saved = total_orig - total_comp
        pct_saved = (100 - (total_comp / total_orig * 100)) if total_orig > 0 else 0

        dlg = tk.Toplevel(self.root)
        dlg.title("Compressione completata")
        dlg.configure(bg=C["base"])
        dlg.geometry("420x320")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        # Center on parent
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 420) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 320) // 2
        dlg.geometry(f"+{x}+{y}")

        # Icon check
        tk.Label(dlg, text="\u2705", bg=C["base"], fg=C["green"],
                 font=("Segoe UI", 36)).pack(pady=(20, 5))

        tk.Label(dlg, text="Compressione completata!", bg=C["base"], fg=C["text"],
                 font=("Segoe UI", 14, "bold")).pack()

        # Stats frame
        stats = tk.Frame(dlg, bg=C["mantle"], padx=20, pady=12)
        stats.pack(fill=tk.X, padx=20, pady=(12, 0))

        rows = [
            ("File compressi:", f"{success} / {total}"),
            ("Dimensione originale:", self._format_size(total_orig)),
            ("Dimensione finale:", self._format_size(total_comp)),
            ("Spazio recuperato:", f"{self._format_size(max(0, total_saved))} ({pct_saved:.0f}%)"),
        ]
        if errors:
            rows.append(("Errori:", str(errors)))

        for label, value in rows:
            row = tk.Frame(stats, bg=C["mantle"])
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label, bg=C["mantle"], fg=C["sub"],
                     font=("Segoe UI", 10), anchor="w", width=22).pack(side=tk.LEFT)
            color = C["green"] if "recuperato" in label.lower() else C["text"]
            if "errori" in label.lower():
                color = C["red"]
            tk.Label(row, text=value, bg=C["mantle"], fg=color,
                     font=("Segoe UI", 10, "bold"), anchor="e").pack(side=tk.RIGHT)

        ModernButton(dlg, text="OK", command=dlg.destroy, width=120, height=36,
                     font=("Segoe UI", 11, "bold"), bg=C["blue"], fg=C["crust"],
                     hover_bg=C["lavender"], radius=10).pack(pady=(16, 0))

    # ── Duplicate detection ──

    @staticmethod
    def _image_hash(filepath, hash_size=16):
        """Compute a perceptual hash (average hash) for an image."""
        try:
            img = Image.open(filepath)
            try:
                img = ImageOps.exif_transpose(img) or img
            except Exception:
                pass
            img = img.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            return tuple(1 if p > avg else 0 for p in pixels)
        except Exception:
            return None

    @staticmethod
    def _hash_similarity(h1, h2):
        """Return similarity 0.0-1.0 between two hashes."""
        if h1 is None or h2 is None or len(h1) != len(h2):
            return 0.0
        matching = sum(1 for a, b in zip(h1, h2) if a == b)
        return matching / len(h1)

    def _find_duplicates(self):
        if len(self.file_list) < 2:
            messagebox.showinfo("Duplicati", "Servono almeno 2 immagini per cercare duplicati.")
            return

        self.status_label.config(text="Analisi duplicati in corso...")
        self.root.update_idletasks()

        # Compute hashes
        hashes = {}
        for fp in self.file_list:
            h = self._image_hash(fp)
            if h is not None:
                hashes[fp] = h

        # Find groups of similar images (>= 92% similarity)
        threshold = 0.92
        processed = set()
        groups = []

        files = list(hashes.keys())
        for i in range(len(files)):
            if files[i] in processed:
                continue
            group = [files[i]]
            for j in range(i + 1, len(files)):
                if files[j] in processed:
                    continue
                sim = self._hash_similarity(hashes[files[i]], hashes[files[j]])
                if sim >= threshold:
                    group.append(files[j])
                    processed.add(files[j])
            if len(group) > 1:
                processed.add(files[i])
                groups.append(group)

        if not groups:
            self.status_label.config(text="Nessun duplicato trovato")
            messagebox.showinfo("Duplicati", "Nessuna immagine simile trovata.")
            return

        total_dupes = sum(len(g) - 1 for g in groups)
        self.status_label.config(text=f"Trovati {total_dupes} possibili duplicati in {len(groups)} gruppi")
        logger.info(f"Duplicati: {total_dupes} in {len(groups)} gruppi")

        self._show_duplicates_dialog(groups)

    def _show_duplicates_dialog(self, groups):
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Immagini simili trovate - {sum(len(g) - 1 for g in groups)} duplicati")
        dlg.configure(bg=C["base"])
        dlg.geometry("800x600")
        dlg.minsize(700, 500)
        dlg.transient(self.root)

        # Center
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 800) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
        dlg.geometry(f"+{x}+{y}")

        # Header
        header = tk.Frame(dlg, bg=C["crust"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text=f"  {sum(len(g) - 1 for g in groups)} immagini simili in {len(groups)} gruppi",
                 bg=C["crust"], fg=C["peach"], font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Label(header, text="Seleziona le immagini da ELIMINARE", bg=C["crust"],
                 fg=C["sub"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(20, 0))

        # Scrollable content
        container = tk.Frame(dlg, bg=C["base"])
        container.pack(fill=tk.BOTH, expand=True)

        canvas_scroll = tk.Canvas(container, bg=C["base"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas_scroll.yview,
                                   style="Dark.Vertical.TScrollbar")
        scroll_frame = tk.Frame(canvas_scroll, bg=C["base"])

        scroll_frame.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scroll
        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel)

        # Track checkbuttons and PhotoImage refs
        check_vars = {}
        photo_refs = []

        for gi, group in enumerate(groups):
            # Group header
            gf = tk.Frame(scroll_frame, bg=C["mantle"], highlightthickness=1,
                          highlightbackground=C["s1"])
            gf.pack(fill=tk.X, pady=(0, 10), padx=5)

            gh = tk.Frame(gf, bg=C["s0"])
            gh.pack(fill=tk.X)
            tk.Label(gh, text=f"  Gruppo {gi + 1} — {len(group)} immagini simili",
                     bg=C["s0"], fg=C["blue"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=3)

            img_row = tk.Frame(gf, bg=C["mantle"], padx=8, pady=8)
            img_row.pack(fill=tk.X)

            for fi, fp in enumerate(group):
                card = tk.Frame(img_row, bg=C["crust"], padx=4, pady=4)
                card.pack(side=tk.LEFT, padx=(0, 8))

                # Thumbnail
                try:
                    img = Image.open(fp)
                    try:
                        img = ImageOps.exif_transpose(img) or img
                    except Exception:
                        pass
                    img.thumbnail((140, 100), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    photo_refs.append(photo)

                    lbl_img = tk.Label(card, image=photo, bg=C["crust"])
                    lbl_img.pack()
                except Exception:
                    tk.Label(card, text="[errore]", bg=C["crust"], fg=C["red"],
                             font=("Segoe UI", 8)).pack()

                # File info
                fname = os.path.basename(fp)
                if len(fname) > 20:
                    fname = fname[:17] + "..."
                tk.Label(card, text=fname, bg=C["crust"], fg=C["text"],
                         font=("Segoe UI", 8), wraplength=140).pack()

                try:
                    size = os.path.getsize(fp)
                    tk.Label(card, text=self._format_size(size), bg=C["crust"],
                             fg=C["sub"], font=("Segoe UI", 7)).pack()
                except OSError:
                    pass

                # Checkbox to mark for deletion (first image unchecked by default)
                var = tk.BooleanVar(value=(fi > 0))
                check_vars[fp] = var
                cb = tk.Checkbutton(card, text="Elimina", variable=var,
                                    bg=C["crust"], fg=C["red"], selectcolor=C["s0"],
                                    activebackground=C["crust"], activeforeground=C["red"],
                                    font=("Segoe UI", 8, "bold"), highlightthickness=0)
                cb.pack()

        # Bottom buttons
        bottom = tk.Frame(dlg, bg=C["base"], pady=8)
        bottom.pack(fill=tk.X)

        count_label = tk.Label(bottom, text="", bg=C["base"], fg=C["sub"], font=("Segoe UI", 9))
        count_label.pack(side=tk.LEFT, padx=20)

        def update_count(*args):
            n = sum(1 for v in check_vars.values() if v.get())
            count_label.config(text=f"{n} immagini selezionate per l'eliminazione")

        for v in check_vars.values():
            v.trace_add("write", update_count)
        update_count()

        def do_delete():
            to_delete = [fp for fp, v in check_vars.items() if v.get()]
            if not to_delete:
                messagebox.showinfo("Nessuna selezione", "Nessuna immagine selezionata per l'eliminazione.")
                return
            if not messagebox.askyesno("Conferma eliminazione",
                                        f"Eliminare {len(to_delete)} immagini?\n\n"
                                        "I file verranno eliminati definitivamente."):
                return
            deleted = 0
            freed = 0
            for fp in to_delete:
                try:
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    deleted += 1
                    freed += size
                    logger.info(f"Duplicato eliminato: {fp}")
                    if fp in self.file_list:
                        self.file_list.remove(fp)
                except Exception as e:
                    logger.error(f"Errore eliminazione {fp}: {e}")

            self._refresh_tree()
            self._update_estimates()
            canvas_scroll.unbind_all("<MouseWheel>")
            dlg.destroy()
            self.status_label.config(
                text=f"{deleted} duplicati eliminati, {self._format_size(freed)} liberati")
            messagebox.showinfo("Eliminazione completata",
                                f"{deleted} immagini eliminate\n"
                                f"Spazio liberato: {self._format_size(freed)}")

        def cancel():
            canvas_scroll.unbind_all("<MouseWheel>")
            dlg.destroy()

        ModernButton(bottom, text="Annulla", command=cancel, width=100, height=34,
                     font=("Segoe UI", 10), bg=C["s1"], hover_bg=C["s2"]).pack(side=tk.RIGHT, padx=(0, 20))
        ModernButton(bottom, text="Elimina selezionati", command=do_delete, width=160, height=34,
                     font=("Segoe UI", 10, "bold"), bg=C["red"], fg=C["crust"],
                     hover_bg=C["pink"]).pack(side=tk.RIGHT, padx=(0, 8))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageSqueezer()
    app.run()
