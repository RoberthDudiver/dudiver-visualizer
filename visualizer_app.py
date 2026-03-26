#!/usr/bin/env python3
"""
Dudiver Visualizer Studio v3
CustomTkinter — UI profesional, progress real, spot publicitario.
"""

import sys
import os
import json
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

SKILLS_DIR = os.path.normpath("C:/Users/rober/.claude/skills/music/scripts")
if SKILLS_DIR not in sys.path:
    sys.path.insert(0, SKILLS_DIR)

from lyric_video import (
    alinear_letra_con_whisper,
    cargar_timestamps_directos,
    crear_frame_normal,
    crear_frame_alpha,
    Particula,
    cargar_fuente,
    ESQUEMAS,
)
from generar_timestamps import generar_timestamps as whisper_generar_timestamps

# ── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = "#e94560"
ACCENT_H = "#ff6b81"
GOLD = "#ffd460"
GREEN = "#4ade80"
DIM = "#7a7a9a"
CARD = "#1a1a2e"
INPUT_BG = "#12122a"
DARK = "#0e0e1a"

TAMANOS = {
    "YouTube 1920×1080": (1920, 1080),
    "TikTok 1080×1920": (1080, 1920),
    "Instagram 1080×1080": (1080, 1080),
    "Story 720×1280": (720, 1280),
}
ESQUEMAS_GUI = {
    "Noche": "nocturno", "Fuego": "fuego", "Oceano": "oscuro",
    "Neon": "neon", "Oro": "elegante",
}
DURACIONES = {
    "Completo": 0, "30 seg": 30, "1 min": 60, "1:30 min": 90,
    "2 min": 120, "3 min": 180,
}


def short_path(p, mx=35):
    if not p:
        return ""
    n = os.path.basename(p)
    return n[:mx-3] + "..." if len(n) > mx else n


class VisualizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dudiver Visualizer Studio")
        self.configure(fg_color=DARK)
        self.state("zoomed")

        # Icono
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(ico):
            self.after(200, lambda: self.iconbitmap(ico))

        # ── Variables ──
        self.audio_path = ctk.StringVar()
        self.letra_path = ctk.StringVar()
        self.fondo_path = ctk.StringVar()
        self.titulo_var = ctk.StringVar()
        self.tamano_var = ctk.StringVar(value="YouTube 1920×1080")
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
        # Spot publicitario
        self.spot_enabled = ctk.BooleanVar(value=False)
        self.spot_type = ctk.StringVar(value="Texto")
        self.spot_file = ctk.StringVar()
        self.spot_text = ctk.StringVar(value="Escuchala en todas las plataformas")
        self.spot_subtext = ctk.StringVar(value="@dudiver")
        self.spot_duration = ctk.StringVar(value="5 seg")

        self.preview_time = ctk.DoubleVar(value=0.0)

        self._cancel = False
        self._worker = None
        self._ts_data = None
        self._lineas = None
        self._dur = 0.0
        self._pimg = None
        self._all_inputs = []  # widgets to disable during generation

        self._build()

    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        # ── Header + Toolbar ──
        header = ctk.CTkFrame(self, fg_color=DARK, height=56, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="DUDIVER", font=("Segoe UI Black", 20),
                     text_color=ACCENT).pack(side="left", padx=(16, 0))
        ctk.CTkLabel(header, text="VISUALIZER", font=("Segoe UI Light", 20),
                     text_color="white").pack(side="left", padx=(6, 0))

        # Separator
        ctk.CTkFrame(header, fg_color="#2a2a4a", width=2, height=30,
                     corner_radius=0).pack(side="left", padx=12)

        # ── Toolbar buttons ──
        ts_btn = ctk.CTkButton(header, text="⟳ Timestamps", height=34, width=130,
                               font=("Segoe UI Semibold", 11),
                               fg_color="#2a2a4a", hover_color="#3a3a5a",
                               corner_radius=8, command=self._run_timestamps)
        ts_btn.pack(side="left", padx=3)
        self._all_inputs.append(ts_btn)

        pv_btn = ctk.CTkButton(header, text="👁 Preview", height=34, width=110,
                               font=("Segoe UI Semibold", 11),
                               fg_color="#2a2a4a", hover_color="#3a3a5a",
                               text_color=GOLD, corner_radius=8,
                               command=self._preview_frame)
        pv_btn.pack(side="left", padx=3)
        self._all_inputs.append(pv_btn)

        # GENERAR button in toolbar
        self.gen_btn = ctk.CTkButton(header, text="▶  GENERAR VIDEO", height=38, width=200,
                                     font=("Segoe UI Black", 13),
                                     fg_color=ACCENT, hover_color=ACCENT_H,
                                     corner_radius=10, command=self._run_generate)
        self.gen_btn.pack(side="left", padx=(8, 3))
        self._all_inputs.append(self.gen_btn)

        self.cancel_btn = ctk.CTkButton(header, text="✕", height=34, width=40,
                                        font=("Segoe UI Bold", 13),
                                        fg_color="#2a2a4a", hover_color=ACCENT,
                                        text_color=DIM, corner_radius=8,
                                        state="disabled", command=self._do_cancel)
        self.cancel_btn.pack(side="left", padx=3)

        # Separator
        ctk.CTkFrame(header, fg_color="#2a2a4a", width=2, height=30,
                     corner_radius=0).pack(side="left", padx=8)

        # Progress in toolbar
        prog_frame = ctk.CTkFrame(header, fg_color="transparent")
        prog_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.pct_label = ctk.CTkLabel(prog_frame, text="", font=("Segoe UI Black", 14),
                                      text_color=ACCENT, width=50)
        self.pct_label.pack(side="left")

        prog_col = ctk.CTkFrame(prog_frame, fg_color="transparent")
        prog_col.pack(side="left", fill="x", expand=True, padx=(4, 8))

        self.progress_bar = ctk.CTkProgressBar(prog_col, height=8, corner_radius=4,
                                               fg_color=INPUT_BG,
                                               progress_color=ACCENT)
        self.progress_bar.pack(fill="x", pady=(0, 1))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(prog_col, text="✓ Listo",
                                         font=("Segoe UI", 9), text_color=DIM,
                                         anchor="w", height=14)
        self.status_label.pack(fill="x")

        # Abrir carpeta (right side)
        ctk.CTkButton(header, text="📂", height=34, width=40,
                      font=("Segoe UI", 14), fg_color="#2a2a4a",
                      hover_color="#3a3a5a", corner_radius=8,
                      command=self._open_folder).pack(side="right", padx=(3, 12))

        # Accent line
        ctk.CTkFrame(self, fg_color=ACCENT, height=2, corner_radius=0).pack(fill="x")

        # ── Body: 3 columnas ──
        body = ctk.CTkFrame(self, fg_color=DARK, corner_radius=0)
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.columnconfigure(0, weight=3, minsize=280)
        body.columnconfigure(1, weight=3, minsize=300)
        body.columnconfigure(2, weight=5, minsize=400)

        # ════════════════════════════════════════════════════
        # COL 0: Archivos + Letra
        # ════════════════════════════════════════════════════
        col0 = ctk.CTkFrame(body, fg_color=DARK, corner_radius=0)
        col0.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._section(col0, "🎵  ARCHIVOS")
        self._file_row(col0, "Cancion", self.audio_path,
                       [("Audio", "*.mp3 *.wav *.flac *.ogg")])
        self._file_row(col0, "Letra", self.letra_path,
                       [("Texto", "*.txt *.md")])
        self._file_row(col0, "Fondo", self.fondo_path,
                       [("Media", "*.jpg *.png *.mp4 *.mov")])

        alpha_cb = ctk.CTkCheckBox(col0, text="Transparente (alpha/WebM)",
                                   variable=self.alpha_var, font=("Segoe UI", 11),
                                   fg_color=ACCENT, hover_color=ACCENT_H)
        alpha_cb.pack(fill="x", padx=8, pady=(2, 6))
        self._all_inputs.append(alpha_cb)

        self._section(col0, "✏️  TITULO")
        te = ctk.CTkEntry(col0, textvariable=self.titulo_var, height=36,
                          font=("Segoe UI", 12), fg_color=INPUT_BG,
                          border_color=DIM, corner_radius=8)
        te.pack(fill="x", padx=8, pady=(0, 6))
        self._all_inputs.append(te)

        self._section(col0, "📝  LETRA (o pega aqui)")
        self.letra_text = ctk.CTkTextbox(col0, font=("Consolas", 10),
                                         fg_color=INPUT_BG, border_color=DIM,
                                         corner_radius=8, border_width=1)
        self.letra_text.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self._all_inputs.append(self.letra_text)

        # ════════════════════════════════════════════════════
        # COL 1: Config + Spot + Acciones
        # ════════════════════════════════════════════════════
        col1 = ctk.CTkFrame(body, fg_color=DARK, corner_radius=0)
        col1.grid(row=0, column=1, sticky="nsew", padx=6)

        # ── Video Config ──
        self._section(col1, "🎬  VIDEO")
        cfg = ctk.CTkFrame(col1, fg_color=CARD, corner_radius=10)
        cfg.pack(fill="x", padx=4, pady=(0, 4))

        self._dropdown(cfg, "Tamaño", self.tamano_var, list(TAMANOS.keys()))
        self._dropdown(cfg, "FPS", self.fps_var, ["24", "30", "60"])
        self._dropdown(cfg, "Colores", self.esquema_var, list(ESQUEMAS_GUI.keys()))
        self._dropdown(cfg, "Whisper", self.whisper_var, ["tiny", "base", "small", "medium"])
        self._dropdown(cfg, "Duracion", self.duracion_var, list(DURACIONES.keys()))

        # Font slider
        fs_frame = ctk.CTkFrame(cfg, fg_color="transparent")
        fs_frame.pack(fill="x", padx=12, pady=4)
        self.fs_label = ctk.CTkLabel(fs_frame, text=f"Fuente: {self.font_size_var.get()}px",
                                     font=("Segoe UI", 11), text_color=DIM)
        self.fs_label.pack(anchor="w")
        fs_slider = ctk.CTkSlider(fs_frame, from_=20, to=80, variable=self.font_size_var,
                                  fg_color=INPUT_BG, progress_color=ACCENT,
                                  button_color=GOLD, button_hover_color=ACCENT_H,
                                  command=lambda v: self.fs_label.configure(
                                      text=f"Fuente: {int(v)}px"))
        fs_slider.pack(fill="x", pady=(0, 4))
        self._all_inputs.append(fs_slider)

        # Efectos
        self._section(col1, "✨  EFECTOS")
        efx = ctk.CTkFrame(col1, fg_color=CARD, corner_radius=10)
        efx.pack(fill="x", padx=4, pady=(0, 4))
        efx_grid = ctk.CTkFrame(efx, fg_color="transparent")
        efx_grid.pack(fill="x", padx=8, pady=6)
        efx_grid.columnconfigure((0, 1), weight=1)
        for i, (txt, var) in enumerate([
            ("Particulas", self.chk_particulas), ("Onda", self.chk_onda),
            ("Viñeta", self.chk_vineta), ("Glow", self.chk_glow),
            ("Barra progreso", self.chk_barra)
        ]):
            cb = ctk.CTkCheckBox(efx_grid, text=txt, variable=var,
                                 font=("Segoe UI", 10), fg_color=ACCENT,
                                 hover_color=ACCENT_H, corner_radius=4)
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=2)
            self._all_inputs.append(cb)

        # ── SPOT PUBLICITARIO ──
        self._section(col1, "📢  SPOT PUBLICITARIO")
        spot = ctk.CTkFrame(col1, fg_color=CARD, corner_radius=10)
        spot.pack(fill="x", padx=4, pady=(0, 4))

        spot_enable = ctk.CTkSwitch(spot, text="Activar spot al final",
                                    variable=self.spot_enabled,
                                    font=("Segoe UI Semibold", 11),
                                    fg_color=DIM, progress_color=ACCENT,
                                    button_color=GOLD,
                                    command=self._toggle_spot)
        spot_enable.pack(fill="x", padx=12, pady=(8, 4))

        self.spot_frame = ctk.CTkFrame(spot, fg_color="transparent")
        self.spot_frame.pack(fill="x", padx=12, pady=(0, 8))

        # Tipo de spot
        sf1 = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        sf1.pack(fill="x", pady=2)
        ctk.CTkLabel(sf1, text="Tipo:", font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        self.spot_type_menu = ctk.CTkSegmentedButton(
            sf1, values=["Texto", "Imagen", "Video"],
            variable=self.spot_type, font=("Segoe UI", 10),
            fg_color=INPUT_BG, selected_color=ACCENT,
            selected_hover_color=ACCENT_H,
            command=self._on_spot_type_change)
        self.spot_type_menu.pack(side="left", fill="x", expand=True, padx=4)

        # Texto spot
        self.spot_text_frame = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        self.spot_text_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(self.spot_text_frame, text="Linea 1:", font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        ctk.CTkEntry(self.spot_text_frame, textvariable=self.spot_text,
                     font=("Segoe UI", 11), fg_color=INPUT_BG,
                     corner_radius=6, height=30).pack(side="left", fill="x", expand=True, padx=4)

        sf_sub = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        sf_sub.pack(fill="x", pady=2)
        ctk.CTkLabel(sf_sub, text="Linea 2:", font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        ctk.CTkEntry(sf_sub, textvariable=self.spot_subtext,
                     font=("Segoe UI", 11), fg_color=INPUT_BG,
                     corner_radius=6, height=30).pack(side="left", fill="x", expand=True, padx=4)

        # Archivo spot (imagen/video)
        self.spot_file_frame = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        # No pack yet — shown when tipo=Imagen or Video

        sf_file = ctk.CTkFrame(self.spot_file_frame, fg_color="transparent")
        sf_file.pack(fill="x", pady=2)
        ctk.CTkLabel(sf_file, text="Archivo:", font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        self.spot_file_label = ctk.CTkLabel(sf_file, text="ninguno",
                                            font=("Segoe UI", 10), text_color=GOLD)
        self.spot_file_label.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(sf_file, text="...", width=32, height=28,
                      fg_color=INPUT_BG, hover_color=ACCENT,
                      command=self._pick_spot_file).pack(side="right")

        # Duracion spot
        sf_dur = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        sf_dur.pack(fill="x", pady=2)
        ctk.CTkLabel(sf_dur, text="Duracion:", font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        ctk.CTkSegmentedButton(sf_dur, values=["3 seg", "5 seg", "8 seg", "10 seg"],
                               variable=self.spot_duration, font=("Segoe UI", 10),
                               fg_color=INPUT_BG, selected_color=ACCENT,
                               selected_hover_color=ACCENT_H).pack(side="left", fill="x",
                                                                     expand=True, padx=4)

        # Initially hidden
        self.spot_frame.pack_forget()

        # ── LOG (compact, at bottom of col1) ──
        self.log_text = ctk.CTkTextbox(col1, height=60, font=("Consolas", 9),
                                       fg_color="#080810", text_color=GREEN,
                                       corner_radius=8, border_width=1,
                                       border_color="#1a1a2a")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=(6, 0))
        self.log_text.configure(state="disabled")

        # ════════════════════════════════════════════════════
        # COL 2: Preview
        # ════════════════════════════════════════════════════
        col2 = ctk.CTkFrame(body, fg_color=DARK, corner_radius=0)
        col2.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        self._section(col2, "🖼  PREVIEW")

        # Preview frame con borde
        pv_outer = ctk.CTkFrame(col2, fg_color="#080810", corner_radius=12,
                                border_width=1, border_color="#2a2a4a")
        pv_outer.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.preview_canvas = tk.Canvas(pv_outer, bg="#080810", highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Timeline
        tl = ctk.CTkFrame(col2, fg_color=DARK, corner_radius=0)
        tl.pack(fill="x", padx=4)

        tl_info = ctk.CTkFrame(tl, fg_color="transparent")
        tl_info.pack(fill="x")
        self.time_label = ctk.CTkLabel(tl_info, text="0:00",
                                       font=("Segoe UI Black", 14), text_color=GOLD)
        self.time_label.pack(side="left")
        self.dur_label = ctk.CTkLabel(tl_info, text="/ 0:00",
                                      font=("Segoe UI", 12), text_color=DIM)
        self.dur_label.pack(side="left", padx=(4, 0))

        self.timeline = ctk.CTkSlider(tl, from_=0, to=300, variable=self.preview_time,
                                      fg_color=INPUT_BG, progress_color=ACCENT,
                                      button_color=GOLD, button_hover_color=ACCENT_H,
                                      command=self._on_time_change)
        self.timeline.pack(fill="x", pady=(2, 4))

        # Info bar
        self.info_label = ctk.CTkLabel(col2, text="Selecciona un audio para comenzar",
                                       font=("Segoe UI", 10), text_color=DIM,
                                       fg_color=CARD, corner_radius=8, height=30)
        self.info_label.pack(fill="x", padx=4, pady=(0, 2))

        # ── Watchers ──
        self.audio_path.trace_add("write", self._on_audio_change)

    # ── UI Helpers ──────────────────────────────────────────────────────────

    def _section(self, parent, text):
        if text:
            ctk.CTkLabel(parent, text=text, font=("Segoe UI Semibold", 11),
                         text_color=ACCENT, anchor="w").pack(fill="x", padx=8, pady=(10, 3))

    def _file_row(self, parent, label, var, ftypes):
        row = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8, height=36)
        row.pack(fill="x", padx=6, pady=2)
        row.pack_propagate(False)

        ctk.CTkLabel(row, text=label, font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left", padx=(10, 0))

        name_lbl = ctk.CTkLabel(row, text="", font=("Segoe UI", 10),
                                text_color=GOLD, anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True, padx=6)

        btn = ctk.CTkButton(row, text="...", width=32, height=26,
                            font=("Segoe UI Bold", 10), fg_color=INPUT_BG,
                            hover_color=ACCENT, corner_radius=6,
                            command=lambda: self._pick_file(var, ftypes, label))
        btn.pack(side="right", padx=6)
        self._all_inputs.append(btn)

        var.trace_add("write", lambda *_: name_lbl.configure(text=short_path(var.get())))

    def _dropdown(self, parent, label, var, values):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label, font=("Segoe UI", 10),
                     text_color=DIM, width=70, anchor="w").pack(side="left")
        dd = ctk.CTkOptionMenu(row, variable=var, values=values,
                               font=("Segoe UI", 10), fg_color=INPUT_BG,
                               button_color="#2a2a4a", button_hover_color=ACCENT,
                               dropdown_fg_color=CARD, dropdown_hover_color=ACCENT,
                               corner_radius=6, height=28)
        dd.pack(side="right", fill="x", expand=True)
        self._all_inputs.append(dd)

    def _pick_file(self, var, ftypes, title):
        p = filedialog.askopenfilename(title=f"Seleccionar {title}",
                                       filetypes=ftypes + [("Todos", "*.*")])
        if p:
            var.set(p)

    # ── Spot Publicitario helpers ──

    def _toggle_spot(self):
        if self.spot_enabled.get():
            self.spot_frame.pack(fill="x", padx=12, pady=(0, 8))
        else:
            self.spot_frame.pack_forget()

    def _on_spot_type_change(self, val):
        if val == "Texto":
            self.spot_text_frame.pack(fill="x", pady=2)
            self.spot_file_frame.pack_forget()
        else:
            self.spot_text_frame.pack_forget()
            self.spot_file_frame.pack(fill="x", pady=2)

    def _pick_spot_file(self):
        if self.spot_type.get() == "Imagen":
            ft = [("Imagenes", "*.jpg *.png *.bmp"), ("Todos", "*.*")]
        else:
            ft = [("Video", "*.mp4 *.mov *.avi"), ("Todos", "*.*")]
        p = filedialog.askopenfilename(title="Seleccionar archivo spot", filetypes=ft)
        if p:
            self.spot_file.set(p)
            self.spot_file_label.configure(text=short_path(p))

    # ── Events ──────────────────────────────────────────────────────────────

    def _on_time_change(self, val):
        m, s = divmod(int(val), 60)
        self.time_label.configure(text=f"{m}:{s:02d}")

    def _on_audio_change(self, *_):
        p = self.audio_path.get()
        if p and os.path.isfile(p):
            self.info_label.configure(text=f"🎵 {short_path(p, 50)}")
            # Auto-fill titulo con nombre del archivo (sin extension)
            if not self.titulo_var.get().strip():
                name = os.path.splitext(os.path.basename(p))[0]
                # Limpiar sufijos comunes de audio: (Remastered), -v2, _01, etc.
                import re
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
            self.after(0, lambda: self.timeline.configure(to=self._dur))
            self.after(0, lambda: self.dur_label.configure(text=f"/ {m}:{s:02d}"))
            self.after(0, lambda: self.info_label.configure(
                text=f"🎵 {short_path(self.audio_path.get(), 40)} — {m}:{s:02d}"))
        except Exception:
            pass

    # ── Logging & Status ────────────────────────────────────────────────────

    def _log(self, msg):
        def _a():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _a)

    def _set_status(self, msg, pct=None):
        def _u():
            self.status_label.configure(text=msg)
            if pct is not None:
                self.progress_bar.set(pct / 100.0)
                self.pct_label.configure(text=f"{int(pct)}%")
                if pct >= 100:
                    self.progress_bar.configure(progress_color=GREEN)
                    self.pct_label.configure(text_color=GREEN)
                    self.status_label.configure(text_color=GREEN)
                else:
                    self.progress_bar.configure(progress_color=ACCENT)
                    self.pct_label.configure(text_color=ACCENT)
                    self.status_label.configure(text_color=DIM)
        self.after(0, _u)

    def _disable_ui(self):
        """Deshabilita todos los inputs durante generacion."""
        def _d():
            for w in self._all_inputs:
                try:
                    w.configure(state="disabled")
                except Exception:
                    pass
            self.cancel_btn.configure(state="normal", text_color=ACCENT)
            self.gen_btn.configure(text="⟳  GENERANDO...", fg_color="#3a3a5a",
                                  state="disabled")
        self.after(0, _d)

    def _enable_ui(self):
        """Rehabilita todos los inputs."""
        def _e():
            for w in self._all_inputs:
                try:
                    w.configure(state="normal")
                except Exception:
                    pass
            self.cancel_btn.configure(state="disabled", text_color=DIM)
            self.gen_btn.configure(text="▶  GENERAR VIDEO", fg_color=ACCENT,
                                  state="normal")
        self.after(0, _e)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _resolution(self):
        return TAMANOS.get(self.tamano_var.get(), (1920, 1080))

    def _max_duration(self):
        return DURACIONES.get(self.duracion_var.get(), 0)

    def _lyrics(self):
        text = self.letra_text.get("1.0", "end").strip()
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

    def _ts_path(self):
        a = self.audio_path.get()
        return os.path.splitext(a)[0] + "_timestamps.json" if a else None

    def _ensure_timing(self, lines):
        if self._lineas and len(self._lineas) > 0:
            return self._lineas
        tp = self._ts_path()
        if tp and os.path.isfile(tp):
            try:
                with open(tp, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, list):
                    self._lineas = cargar_timestamps_directos(tp)
                elif isinstance(d, dict) and "palabras" in d:
                    self._lineas = alinear_letra_con_whisper(lines, d["palabras"])
                return self._lineas
            except Exception:
                pass
        return None

    def _fallback_timing(self, lines, dur):
        gap = dur / max(len(lines), 1)
        return [{"texto": l, "inicio": i * gap, "fin": (i + 1) * gap - 0.1, "score": 0.5}
                for i, l in enumerate(lines)]

    def _adapted_fonts(self, ancho, alto, lines):
        fs = self.font_size_var.get()
        width_scale = ancho / 1920.0
        height_scale = alto / 1080.0
        scale = min(1.0, max(0.35, min(width_scale, height_scale)))
        if lines:
            max_len = max(len(l) for l in lines)
            chars_fit = ancho / (fs * scale * 0.55)
            if max_len > chars_fit:
                scale *= max(0.5, chars_fit / max_len)
        fs_a = max(18, int(fs * scale))
        return (cargar_fuente(fs_a, True),
                cargar_fuente(max(14, fs_a // 2), False),
                cargar_fuente(max(10, fs_a // 3), False))

    def _spot_seconds(self):
        return int(self.spot_duration.get().split()[0])

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
        out = self._ts_path()
        modelo = self.whisper_var.get()
        self._set_status(f"⟳ Whisper ({modelo})...", 10)
        self._log(f"Generando timestamps... modelo={modelo}")
        try:
            res = whisper_generar_timestamps(audio, modelo=modelo, idioma="es")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
            self._ts_data = res
            self._lineas = None
            n = len(res.get("palabras", []))
            self._log(f"✓ {n} palabras -> {os.path.basename(out)}")
            self._set_status(f"✓ Timestamps listos ({n} palabras)", 100)
        except Exception as ex:
            self._log(f"✕ ERROR: {ex}")
            self._set_status(f"✕ Error: {ex}", 0)
        self._enable_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  PREVIEW
    # ══════════════════════════════════════════════════════════════════════════

    def _preview_frame(self):
        import random
        import numpy as np
        from PIL import Image, ImageTk

        lines = self._lyrics()
        if not lines:
            messagebox.showinfo("Info", "Agrega la letra primero.")
            return

        ancho, alto = self._resolution()
        t = self.preview_time.get()
        titulo = self.titulo_var.get().strip()
        fuente, fuente_titulo, fuente_peq = self._adapted_fonts(ancho, alto, lines)
        timing = self._ensure_timing(lines) or self._fallback_timing(lines, self._dur or 180)
        beat_times = []

        random.seed(42)
        parts = [Particula(ancho, alto) for _ in range(60)]
        for _ in range(int(t * 24)):
            for p in parts:
                p.actualizar(1 / 24, 0)

        # Background
        bg_image = None
        fondo = self.fondo_path.get()
        if fondo and os.path.isfile(fondo):
            ext = os.path.splitext(fondo)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".bmp"):
                bg_image = Image.open(fondo).resize((ancho, alto), Image.Resampling.LANCZOS)

        if self.alpha_var.get():
            img = crear_frame_alpha(ancho, alto, timing, t, self._dur or 180,
                                    beat_times, fuente, fuente_titulo, titulo)
            base = bg_image.convert("RGBA") if bg_image else Image.new("RGBA", (ancho, alto), (20, 20, 40, 255))
            img = Image.alpha_composite(base, img).convert("RGB")
        else:
            rms_data = (np.zeros(100), list(range(100)))
            img = crear_frame_normal(ancho, alto, timing, t, self._dur or 180,
                                     beat_times, rms_data, self._esquema(), fuente,
                                     fuente_titulo, fuente_peq, parts, titulo, bg_image)

        # Resize for canvas
        self.update_idletasks()
        cw = max(self.preview_canvas.winfo_width(), 200)
        ch = max(self.preview_canvas.winfo_height(), 200)
        ratio = min(cw / ancho, ch / alto)
        nw, nh = max(1, int(ancho * ratio)), max(1, int(alto * ratio))
        if isinstance(img, Image.Image):
            img_r = img.resize((nw, nh), Image.Resampling.LANCZOS)
        else:
            img_r = Image.fromarray(img).resize((nw, nh), Image.Resampling.LANCZOS)

        self._pimg = ImageTk.PhotoImage(img_r)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(cw // 2, ch // 2, image=self._pimg, anchor="center")

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
        self._set_status("⟳ Preparando...", 1)
        self._worker = threading.Thread(target=self._gen_worker, args=(lines,), daemon=True)
        self._worker.start()

    def _gen_worker(self, lines):
        import random
        import subprocess
        import shutil
        import tempfile

        audio_path = self.audio_path.get()
        ancho, alto = self._resolution()
        fps = int(self.fps_var.get())
        titulo = self.titulo_var.get().strip()
        alpha_mode = self.alpha_var.get()
        esquema = self._esquema()
        fondo = self.fondo_path.get()
        output = self._output_path()
        max_dur = self._max_duration()
        spot_on = self.spot_enabled.get()
        spot_type = self.spot_type.get()
        spot_text = self.spot_text.get()
        spot_subtext = self.spot_subtext.get()
        spot_file = self.spot_file.get()
        spot_secs = self._spot_seconds()

        try:
            from moviepy import AudioFileClip, VideoClip, VideoFileClip
            import librosa
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont, ImageFilter

            self._set_status("⟳ Cargando audio...", 2)
            self._log(f"Audio: {os.path.basename(audio_path)}")
            audio_clip = AudioFileClip(audio_path)
            duracion = audio_clip.duration

            if max_dur > 0 and duracion > max_dur:
                duracion = max_dur
                self._log(f"Duracion limitada a {max_dur}s")

            # Add spot duration to total
            total_dur = duracion + (spot_secs if spot_on else 0)

            self._dur = duracion
            self.after(0, lambda: self.timeline.configure(to=duracion))

            # Timestamps
            self._set_status("⟳ Timestamps...", 5)
            timing = self._ensure_timing(lines)
            if not timing:
                self._set_status("⟳ Ejecutando Whisper...", 8)
                self._log("Sin timestamps, generando...")
                modelo = self.whisper_var.get()
                res = whisper_generar_timestamps(audio_path, modelo=modelo, idioma="es")
                ts_path = self._ts_path()
                with open(ts_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
                timing = alinear_letra_con_whisper(lines, res["palabras"])
                self._lineas = timing
                self._log(f"✓ Timestamps: {len(res['palabras'])} palabras")

            # Beats
            self._set_status("⟳ Analizando beats...", 12)
            y_audio, sr = librosa.load(audio_path, sr=22050)
            tempo, beat_frames = librosa.beat.beat_track(y=y_audio, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
            rms = librosa.feature.rms(y=y_audio)[0]
            rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr).tolist()

            fuente, fuente_titulo, fuente_peq = self._adapted_fonts(ancho, alto, lines)

            # Background
            bg_image = None
            bg_video = None
            bg_is_video = False
            if not alpha_mode and fondo and os.path.isfile(fondo):
                ext = os.path.splitext(fondo)[1].lower()
                if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
                    bg_video = VideoFileClip(fondo)
                    if bg_video.size != [ancho, alto]:
                        bg_video = bg_video.resized((ancho, alto))
                    bg_is_video = True
                elif ext in (".jpg", ".jpeg", ".png", ".bmp"):
                    bg_image = Image.open(fondo).resize((ancho, alto), Image.Resampling.LANCZOS)

            random.seed(42)
            parts = [Particula(ancho, alto) for _ in range(60)]
            total_frames = int(total_dur * fps)
            song_frames = int(duracion * fps)
            self._log(f"📐 {ancho}x{alto} @ {fps}fps — {total_frames} frames")
            if spot_on:
                self._log(f"📢 Spot: {spot_type} — {spot_secs}s al final")

            # ── Preparar spot frame ──
            def make_spot_frame(t_spot):
                """Genera un frame del spot publicitario."""
                img = Image.new("RGB", (ancho, alto), (0, 0, 0))

                if spot_type == "Texto":
                    draw = ImageDraw.Draw(img)
                    # Fuente grande para texto principal
                    try:
                        font_big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf",
                                                      max(30, int(ancho * 0.04)))
                        font_small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",
                                                        max(20, int(ancho * 0.025)))
                    except Exception:
                        font_big = ImageFont.load_default()
                        font_small = font_big

                    # Fade in
                    alpha = min(1.0, t_spot / 1.5)

                    # Texto principal centrado
                    bbox1 = draw.textbbox((0, 0), spot_text, font=font_big)
                    tw1 = bbox1[2] - bbox1[0]
                    y1 = alto // 2 - 40
                    c = int(255 * alpha)
                    draw.text(((ancho - tw1) // 2, y1), spot_text,
                              fill=(c, c, c), font=font_big)

                    # Subtexto
                    if spot_subtext:
                        bbox2 = draw.textbbox((0, 0), spot_subtext, font=font_small)
                        tw2 = bbox2[2] - bbox2[0]
                        ca = int(233 * alpha)
                        cr = int(0.91 * c)
                        draw.text(((ancho - tw2) // 2, y1 + 60), spot_subtext,
                                  fill=(ca, cr, int(0.37 * c)), font=font_small)

                    # Linea decorativa
                    lw = int(ancho * 0.3 * alpha)
                    cx = ancho // 2
                    ly = y1 - 20
                    draw.line([(cx - lw, ly), (cx + lw, ly)],
                              fill=(int(233 * alpha), int(69 * alpha), int(96 * alpha)), width=2)

                elif spot_type == "Imagen" and spot_file and os.path.isfile(spot_file):
                    spot_img = Image.open(spot_file).resize((ancho, alto),
                                                            Image.Resampling.LANCZOS)
                    alpha = min(1.0, t_spot / 1.5)
                    img = Image.blend(img, spot_img, alpha)

                return img

            # ── RENDER ──
            self._set_status("⟳ Generando video...", 15)

            if alpha_mode:
                temp_dir = tempfile.mkdtemp(prefix="dvs_")
                for fn in range(total_frames):
                    if self._cancel:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        self._set_status("✕ Cancelado", 0)
                        self._enable_ui()
                        return
                    t = fn / fps
                    if t < duracion:
                        # Fade out last 2s of song if spot follows
                        frame = crear_frame_alpha(ancho, alto, timing, t, duracion,
                                                  beat_times, fuente, fuente_titulo, titulo)
                        if spot_on and (duracion - t) < 2.0:
                            fade = (duracion - t) / 2.0
                            # reduce alpha of all pixels
                            arr = np.array(frame)
                            arr[:, :, 3] = (arr[:, :, 3] * fade).astype(np.uint8)
                            frame = Image.fromarray(arr)
                    else:
                        frame = Image.new("RGBA", (ancho, alto), (0, 0, 0, 255))
                        spot_f = make_spot_frame(t - duracion)
                        frame.paste(spot_f)

                    frame.save(os.path.join(temp_dir, f"f_{fn:06d}.png"), "PNG")
                    if fn % (fps * 2) == 0:
                        pct = 15 + (fn / total_frames) * 70
                        self._set_status(f"⟳ Frame {fn}/{total_frames}", pct)

                self._set_status("⟳ Codificando...", 88)
                ff = shutil.which("ffmpeg") or "ffmpeg"
                winff = os.path.expanduser("~/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe")
                if os.path.exists(winff):
                    ff = winff

                webm = output if output.endswith(".webm") else os.path.splitext(output)[0] + ".webm"
                subprocess.run([ff, "-y", "-framerate", str(fps),
                                "-i", os.path.join(temp_dir, "f_%06d.png"),
                                "-i", audio_path, "-t", str(total_dur),
                                "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                                "-b:v", "4M", "-c:a", "libopus", "-b:a", "128k",
                                "-shortest", "-auto-alt-ref", "0", webm],
                               capture_output=True)

                mp4 = os.path.splitext(output)[0] + "_preview.mp4"
                subprocess.run([ff, "-y", "-framerate", str(fps),
                                "-i", os.path.join(temp_dir, "f_%06d.png"),
                                "-i", audio_path, "-t", str(total_dur),
                                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-b:v", "5M", "-c:a", "aac", "-b:a", "192k",
                                "-shortest", "-movflags", "+faststart", mp4],
                               capture_output=True)

                shutil.rmtree(temp_dir, ignore_errors=True)
                self._log(f"✓ {os.path.basename(webm)}")
                self._log(f"✓ {os.path.basename(mp4)}")
                self._set_status("✓ Completado!", 100)

            else:
                # ── NORMAL MODE: moviepy ──
                count = [0]

                def make_frame(t):
                    if self._cancel:
                        raise KeyboardInterrupt

                    # Spot section
                    if t >= duracion and spot_on:
                        img = make_spot_frame(t - duracion)
                        return np.array(img)

                    cur_bg = bg_image
                    if bg_is_video and bg_video:
                        cur_bg = Image.fromarray(bg_video.get_frame(t % bg_video.duration))

                    img = crear_frame_normal(ancho, alto, timing, t, duracion,
                                             beat_times, (rms, rms_times), esquema,
                                             fuente, fuente_titulo, fuente_peq,
                                             parts, titulo, cur_bg)

                    # Fade to black/spot transition
                    left = duracion - t
                    if spot_on and left < 2.0:
                        fa = int(255 * (1 - left / 2.0))
                        ov = Image.new("RGBA", (ancho, alto), (0, 0, 0, fa))
                        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
                    elif not spot_on and left < 3.0:
                        fa = int(255 * (1 - left / 3.0))
                        ov = Image.new("RGBA", (ancho, alto), (0, 0, 0, fa))
                        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

                    count[0] += 1
                    if count[0] % (fps * 2) == 0:
                        pct = 15 + (t / total_dur) * 80
                        self._set_status(f"⟳ {t:.0f}s / {total_dur:.0f}s", pct)

                    return np.array(img)

                try:
                    video = VideoClip(make_frame, duration=total_dur)
                    video = video.with_audio(audio_clip)
                    self._log(f"Escribiendo: {os.path.basename(output)}")
                    video.write_videofile(output, fps=fps, codec="libx264",
                                          audio_codec="aac", bitrate="8000k",
                                          preset="medium", logger=None)
                    video.close()
                    self._log(f"✓ {os.path.basename(output)}")
                    self._set_status("✓ Completado!", 100)
                except KeyboardInterrupt:
                    self._set_status("✕ Cancelado", 0)

                if bg_video:
                    bg_video.close()

            audio_clip.close()

        except Exception as ex:
            import traceback
            self._log(f"✕ ERROR: {ex}")
            self._log(traceback.format_exc())
            self._set_status(f"✕ Error: {ex}", 0)

        self._enable_ui()

    def _do_cancel(self):
        self._cancel = True
        self._set_status("⟳ Cancelando...", None)
        self._log("Cancelando...")

    def _open_folder(self):
        out = self._output_path()
        folder = os.path.dirname(out)
        if os.path.isdir(folder):
            os.startfile(folder)


if __name__ == "__main__":
    app = VisualizerApp()
    app.mainloop()
