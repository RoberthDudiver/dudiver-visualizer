"""
VisualizerApp — CTk window, slim orchestrator.
Owns all tkinter variables, creates panels, wires callbacks.
"""

import os
import re
import json
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

from app.config import (
    ACCENT, DARK, GREEN, DIM, CARD, INPUT_BG,
    TAMANOS, ESQUEMAS_GUI, DURACIONES, ESQUEMAS,
    whisper_generar_timestamps,
    alinear_letra_con_whisper,
)
from app.core.timestamps import get_ts_path, load_existing, generate_new, fallback_timing
from app.core.renderer import render_preview_frame
from app.core.video import VideoGenerator
from app.utils.fonts import adapted_fonts
from app.ui.toolbar import Toolbar
from app.ui.panels.files_panel import FilesPanel
from app.ui.panels.config_panel import ConfigPanel
from app.ui.panels.spot_panel import SpotPanel
from app.ui.panels.preview_panel import PreviewPanel
from app.ui.components import short_path


class VisualizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dudiver Visualizer Studio")
        self.configure(fg_color=DARK)
        self.state("zoomed")

        # Icono — forzar el nuestro, bloquear el default de customtkinter
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ico = os.path.join(base_dir, "icon.ico")
        png = os.path.join(base_dir, "icon.png")
        self._iconbitmap_method_called = True  # bloquea CTk override

        # Cargar icono PNG en múltiples tamaños para taskbar + title bar
        if os.path.exists(png):
            img = Image.open(png)
            self._icon_photos = []
            for sz in [16, 32, 48, 64, 128, 256]:
                self._icon_photos.append(ImageTk.PhotoImage(img.resize((sz, sz), Image.LANCZOS)))
            self.wm_iconphoto(True, *self._icon_photos)

        # .ico para title bar (Windows lo prefiere)
        if os.path.exists(ico):
            self.iconbitmap(ico)

        # Forzar de nuevo después del timer de CTk (200ms)
        def _reforce():
            try:
                self._iconbitmap_method_called = True
                if os.path.exists(ico):
                    self.iconbitmap(ico)
            except Exception:
                pass
        self.after(500, _reforce)

        # ── Variables ──
        self.audio_path = ctk.StringVar()
        self.letra_path = ctk.StringVar()
        self.fondo_path = ctk.StringVar()
        self.titulo_var = ctk.StringVar()
        self.tamano_var = ctk.StringVar(value="YouTube 1920\u00d71080")
        self.fps_var = ctk.StringVar(value="30")
        self.esquema_var = ctk.StringVar(value="Noche")
        self.whisper_var = ctk.StringVar(value="base")
        self.duracion_var = ctk.StringVar(value="Completo")
        self.font_size_var = ctk.IntVar(value=50)
        self.alpha_var = ctk.BooleanVar(value=False)
        self.chk_particulas = ctk.BooleanVar(value=True)
        self.chk_onda = ctk.BooleanVar(value=True)
        self.chk_vineta = ctk.BooleanVar(value=True)
        self.chk_glow = ctk.BooleanVar(value=True)
        self.chk_barra = ctk.BooleanVar(value=True)
        # Spot
        self.spot_enabled = ctk.BooleanVar(value=False)
        self.spot_type = ctk.StringVar(value="Texto")
        self.spot_file = ctk.StringVar()
        self.spot_text = ctk.StringVar(value="Escuchala en todas las plataformas")
        self.spot_subtext = ctk.StringVar(value="@dudiver")
        self.spot_duration = ctk.StringVar(value="5 seg")

        self.preview_time = ctk.DoubleVar(value=0.0)

        self._cancel = False
        self._worker = None
        self._lineas = None
        self._dur = 0.0
        self._pimg = None
        self._all_inputs = []

        self._build()

    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        # ── Toolbar ──
        self.toolbar = Toolbar(self,
                               on_timestamps=self._run_timestamps,
                               on_preview=self._preview_frame,
                               on_generate=self._run_generate,
                               on_cancel=self._do_cancel,
                               on_open_folder=self._open_folder,
                               all_inputs=self._all_inputs)
        self.toolbar.pack(fill="x")

        # Accent line
        ctk.CTkFrame(self, fg_color=ACCENT, height=2, corner_radius=0).pack(fill="x")

        # ── Body: 3 columnas ──
        body = ctk.CTkFrame(self, fg_color=DARK, corner_radius=0)
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.columnconfigure(0, weight=3, minsize=280)
        body.columnconfigure(1, weight=3, minsize=300)
        body.columnconfigure(2, weight=5, minsize=400)

        # COL 0: Files + Lyrics
        self.files_panel = FilesPanel(body,
                                      audio_path=self.audio_path,
                                      letra_path=self.letra_path,
                                      fondo_path=self.fondo_path,
                                      titulo_var=self.titulo_var,
                                      alpha_var=self.alpha_var,
                                      all_inputs=self._all_inputs)
        self.files_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # COL 1: Config + Spot + Log
        col1 = ctk.CTkFrame(body, fg_color=DARK, corner_radius=0)
        col1.grid(row=0, column=1, sticky="nsew", padx=6)

        self.config_panel = ConfigPanel(col1,
                                        tamano_var=self.tamano_var,
                                        fps_var=self.fps_var,
                                        esquema_var=self.esquema_var,
                                        whisper_var=self.whisper_var,
                                        duracion_var=self.duracion_var,
                                        font_size_var=self.font_size_var,
                                        chk_particulas=self.chk_particulas,
                                        chk_onda=self.chk_onda,
                                        chk_vineta=self.chk_vineta,
                                        chk_glow=self.chk_glow,
                                        chk_barra=self.chk_barra,
                                        all_inputs=self._all_inputs)
        self.config_panel.pack(fill="x")

        self.spot_panel = SpotPanel(col1,
                                    spot_enabled=self.spot_enabled,
                                    spot_type=self.spot_type,
                                    spot_file=self.spot_file,
                                    spot_text=self.spot_text,
                                    spot_subtext=self.spot_subtext,
                                    spot_duration=self.spot_duration,
                                    all_inputs=self._all_inputs)
        self.spot_panel.pack(fill="x")

        # Log
        self.log_text = ctk.CTkTextbox(col1, height=60, font=("Consolas", 9),
                                       fg_color="#080810", text_color=GREEN,
                                       corner_radius=8, border_width=1,
                                       border_color="#1a1a2a")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=(6, 0))
        self.log_text.configure(state="disabled")

        # COL 2: Preview
        self.preview_panel = PreviewPanel(body,
                                          preview_time=self.preview_time,
                                          on_time_change=self._on_time_change)
        self.preview_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        # Watchers
        self.audio_path.trace_add("write", self._on_audio_change)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _resolution(self):
        return TAMANOS.get(self.tamano_var.get(), (1920, 1080))

    def _max_duration(self):
        return DURACIONES.get(self.duracion_var.get(), 0)

    def _lyrics(self):
        text = self.files_panel.letra_text.get("1.0", "end").strip()
        if text:
            return [l.strip() for l in text.splitlines()
                    if l.strip() and not l.strip().startswith("#")]
        lp = self.letra_path.get()
        if lp and os.path.isfile(lp):
            with open(lp, "r", encoding="utf-8") as f:
                return [l.strip() for l in f
                        if l.strip() and not l.strip().startswith("#")]
        return []

    def _output_path(self):
        audio = self.audio_path.get()
        titulo = self.titulo_var.get().strip() or "output"
        safe = "".join(c if (c.isalnum() or c in " _-") else "_" for c in titulo).strip()
        ext = ".webm" if self.alpha_var.get() else ".mp4"
        folder = os.path.dirname(audio) if audio else os.path.expanduser("~/Desktop")
        return os.path.join(folder, f"{safe}_visualizer{ext}")

    def _esquema(self):
        key = ESQUEMAS_GUI.get(self.esquema_var.get(), "nocturno")
        return ESQUEMAS.get(key, ESQUEMAS["nocturno"])

    def _spot_seconds(self):
        return int(self.spot_duration.get().split()[0])

    def _ensure_timing(self, lines):
        if self._lineas and len(self._lineas) > 0:
            return self._lineas
        ts_path = get_ts_path(self.audio_path.get())
        timing = load_existing(ts_path, lines)
        if timing:
            self._lineas = timing
        return timing

    # ── Logging & Status ────────────────────────────────────────────────────

    def _log(self, msg):
        def _a():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _a)

    def _set_status(self, msg, pct=None):
        self.after(0, lambda: self.toolbar.set_status(msg, pct))

    def _disable_ui(self):
        def _d():
            for w in self._all_inputs:
                try:
                    w.configure(state="disabled")
                except Exception:
                    pass
            self.toolbar.set_generating()
        self.after(0, _d)

    def _enable_ui(self):
        def _e():
            for w in self._all_inputs:
                try:
                    w.configure(state="normal")
                except Exception:
                    pass
            self.toolbar.set_idle()
        self.after(0, _e)

    # ── Events ──────────────────────────────────────────────────────────────

    def _on_time_change(self, val):
        m, s = divmod(int(val), 60)
        self.preview_panel.time_label.configure(text=f"{m}:{s:02d}")

    def _on_audio_change(self, *_):
        p = self.audio_path.get()
        if p and os.path.isfile(p):
            self.preview_panel.info_label.configure(text=f"\U0001f3b5 {short_path(p, 50)}")
            if not self.titulo_var.get().strip():
                name = os.path.splitext(os.path.basename(p))[0]
                name = re.sub(r'\s*\((?:Remastered|Master|Final|Mix|v\d+)\)', '', name, flags=re.IGNORECASE)
                name = re.sub(r'[-_]\d+$', '', name)
                name = re.sub(r'[-_](v\d+|final|master|mix)$', '', name, flags=re.IGNORECASE)
                self.titulo_var.set(name.strip())
            threading.Thread(target=self._load_audio_info, daemon=True).start()

    def _load_audio_info(self):
        try:
            from moviepy import AudioFileClip
            ac = AudioFileClip(self.audio_path.get())
            self._dur = ac.duration
            ac.close()
            m, s = divmod(int(self._dur), 60)
            self.after(0, lambda: self.preview_panel.timeline.configure(to=self._dur))
            self.after(0, lambda: self.preview_panel.dur_label.configure(text=f"/ {m}:{s:02d}"))
            self.after(0, lambda: self.preview_panel.info_label.configure(
                text=f"\U0001f3b5 {short_path(self.audio_path.get(), 40)} \u2014 {m}:{s:02d}"))
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  TIMESTAMPS
    # ══════════════════════════════════════════════════════════════════════════

    def _run_timestamps(self):
        audio = self.audio_path.get()
        if not audio or not os.path.isfile(audio):
            messagebox.showwarning("Aviso", "Selecciona un audio primero.")
            return
        if self._worker and self._worker.is_alive():
            return
        self._cancel = False
        self._disable_ui()
        self._worker = threading.Thread(target=self._ts_worker, daemon=True)
        self._worker.start()

    def _ts_worker(self):
        audio = self.audio_path.get()
        ts_path = get_ts_path(audio)
        modelo = self.whisper_var.get()
        self._set_status(f"\u27f3 Whisper ({modelo})...", 10)
        self._log(f"Generando timestamps... modelo={modelo}")
        try:
            lines = self._lyrics()
            timing, n = generate_new(audio, ts_path, lines, modelo=modelo)
            self._lineas = timing
            self._log(f"\u2713 {n} palabras -> {os.path.basename(ts_path)}")
            self._set_status(f"\u2713 Timestamps listos ({n} palabras)", 100)
        except Exception as ex:
            self._log(f"\u2715 ERROR: {ex}")
            self._set_status(f"\u2715 Error: {ex}", 0)
        self._enable_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  PREVIEW
    # ══════════════════════════════════════════════════════════════════════════

    def _preview_frame(self):
        lines = self._lyrics()
        if not lines:
            messagebox.showinfo("Info", "Agrega la letra primero.")
            return

        ancho, alto = self._resolution()
        t = self.preview_time.get()
        titulo = self.titulo_var.get().strip()
        fuente, fuente_titulo, fuente_peq = adapted_fonts(
            self.font_size_var.get(), ancho, alto, lines)
        timing = self._ensure_timing(lines) or fallback_timing(lines, self._dur or 180)

        img = render_preview_frame(
            ancho=ancho, alto=alto, timing=timing, t=t,
            dur=self._dur or 180, titulo=titulo,
            fuente=fuente, fuente_titulo=fuente_titulo, fuente_peq=fuente_peq,
            esquema_key=self.esquema_var.get(),
            alpha_mode=self.alpha_var.get(),
            fondo_path=self.fondo_path.get())

        # Resize for canvas
        canvas = self.preview_panel.preview_canvas
        self.update_idletasks()
        cw = max(canvas.winfo_width(), 200)
        ch = max(canvas.winfo_height(), 200)
        ratio = min(cw / ancho, ch / alto)
        nw, nh = max(1, int(ancho * ratio)), max(1, int(alto * ratio))
        img_r = img.resize((nw, nh), Image.Resampling.LANCZOS)

        self._pimg = ImageTk.PhotoImage(img_r)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=self._pimg, anchor="center")

    # ══════════════════════════════════════════════════════════════════════════
    #  GENERAR VIDEO
    # ══════════════════════════════════════════════════════════════════════════

    def _run_generate(self):
        audio = self.audio_path.get()
        if not audio or not os.path.isfile(audio):
            messagebox.showwarning("Aviso", "Selecciona un audio.")
            return
        lines = self._lyrics()
        if not lines:
            messagebox.showwarning("Aviso", "Agrega la letra.")
            return
        if self._worker and self._worker.is_alive():
            return
        self._cancel = False
        self._disable_ui()
        self._set_status("\u27f3 Preparando...", 1)
        self._worker = threading.Thread(target=self._gen_worker, args=(lines,), daemon=True)
        self._worker.start()

    def _gen_worker(self, lines):
        ancho, alto = self._resolution()
        fuente, fuente_titulo, fuente_peq = adapted_fonts(
            self.font_size_var.get(), ancho, alto, lines)

        # Ensure timing
        self._set_status("\u27f3 Timestamps...", 5)
        timing = self._ensure_timing(lines)
        if not timing:
            self._set_status("\u27f3 Ejecutando Whisper...", 8)
            self._log("Sin timestamps, generando...")
            audio = self.audio_path.get()
            ts_path = get_ts_path(audio)
            modelo = self.whisper_var.get()
            t, n = generate_new(audio, ts_path, lines, modelo=modelo)
            self._lineas = t
            timing = t
            self._log(f"\u2713 Timestamps: {n} palabras")

        config = {
            "audio_path": self.audio_path.get(),
            "ancho": ancho,
            "alto": alto,
            "fps": int(self.fps_var.get()),
            "titulo": self.titulo_var.get().strip(),
            "alpha_mode": self.alpha_var.get(),
            "esquema": self._esquema(),
            "fondo_path": self.fondo_path.get(),
            "output_path": self._output_path(),
            "max_dur": self._max_duration(),
            "timing": timing,
            "lines": lines,
            "fuente": fuente,
            "fuente_titulo": fuente_titulo,
            "fuente_peq": fuente_peq,
            "spot_on": self.spot_enabled.get(),
            "spot_type": self.spot_type.get(),
            "spot_text": self.spot_text.get(),
            "spot_subtext": self.spot_subtext.get(),
            "spot_file": self.spot_file.get(),
            "spot_secs": self._spot_seconds(),
        }

        def on_progress(msg, pct):
            self._set_status(f"\u27f3 {msg}", pct)

        gen = VideoGenerator(
            config,
            on_progress=on_progress,
            on_log=self._log,
            is_cancelled=lambda: self._cancel,
        )
        gen.run()

        # Update timeline with actual duration if available
        if self._dur > 0:
            m, s = divmod(int(self._dur), 60)
            self.after(0, lambda: self.preview_panel.timeline.configure(to=self._dur))
            self.after(0, lambda: self.preview_panel.dur_label.configure(text=f"/ {m}:{s:02d}"))

        self._enable_ui()

    def _do_cancel(self):
        self._cancel = True
        self._set_status("\u27f3 Cancelando...", None)
        self._log("Cancelando...")

    def _open_folder(self):
        out = self._output_path()
        folder = os.path.dirname(out)
        if os.path.isdir(folder):
            os.startfile(folder)
