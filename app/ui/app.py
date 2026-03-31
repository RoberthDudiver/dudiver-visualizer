"""
VisualizerApp — CTk window, slim orchestrator.
Owns all tkinter variables, creates panels, wires callbacks.
"""

import os
import re
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

from app.config import (
    ACCENT, DARK, GREEN, DIM, CARD, INPUT_BG,
    TAMANOS, ESQUEMAS_GUI, DURACIONES, ESQUEMAS,
    ESTILOS_KINETIC, ESQUEMA_GUI_TO_KINETIC,
    whisper_generar_timestamps,
    alinear_letra_con_whisper,
)
from app.core.timestamps import get_ts_path, load_existing, generate_new, fallback_timing
from app.core.renderer import render_preview_frame
from app.core.video import VideoGenerator
from app.utils.fonts import adapted_fonts, load_pil_font, resolve_font_path
from app.ui.toolbar import Toolbar
from app.ui.panels.files_panel import FilesPanel
from app.ui.panels.config_panel import ConfigPanel
from app.ui.panels.spot_panel import SpotPanel
from app.ui.panels.preview_panel import PreviewPanel
from app.ui.components import short_path
from app.ui.about import AboutWindow
from app.ui.settings import SettingsWindow
from app.ui.sync_editor import SyncEditorWindow
from app.ui.help_window import HelpWindow
from app.i18n import t
from app.core.project import (
    save_dudi, load_dudi, save_dudi_quick, find_dudi,
    get_project_config, apply_project,
    find_project_legacy, load_project_legacy,
)


class VisualizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dudiver Visualizer Studio")
        self.configure(fg_color=DARK)

        # Icono — forzar el nuestro, bloquear el default de customtkinter
        from app.utils.paths import asset_path
        ico = asset_path("icon.ico")
        png = asset_path("icon.png")
        self._iconbitmap_method_called = True  # bloquea CTk override

        # Windows: AppUserModelID propio para que taskbar use nuestro icono
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "dudiver.visualizer.studio.1")
        except Exception:
            pass

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

        # Forzar de nuevo después del timer de CTk (200ms y 1s)
        def _reforce():
            try:
                self._iconbitmap_method_called = True
                if os.path.exists(ico):
                    self.iconbitmap(ico)
                if os.path.exists(png):
                    self.wm_iconphoto(True, *self._icon_photos)
            except Exception:
                pass
        self.after(300, _reforce)
        self.after(1000, _reforce)

        # ── Variables ──
        self.audio_path = ctk.StringVar()
        self.letra_path = ctk.StringVar()
        self.fondo_path = ctk.StringVar()
        self.titulo_var = ctk.StringVar()
        self.tamano_var = ctk.StringVar(value="YouTube 1920\u00d71080")
        self.fps_var = ctk.StringVar(value="30")
        self.esquema_var = ctk.StringVar(value="Noche")
        self.whisper_var = ctk.StringVar(value="Normal")
        self.duracion_var = ctk.StringVar(value="Completo")
        self.font_size_var = ctk.IntVar(value=50)
        self.alpha_var = ctk.BooleanVar(value=False)
        self.chk_particulas = ctk.BooleanVar(value=True)
        self.chk_onda = ctk.BooleanVar(value=True)
        self.chk_vineta = ctk.BooleanVar(value=True)
        self.chk_glow = ctk.BooleanVar(value=True)
        self.chk_barra = ctk.BooleanVar(value=True)
        # Modo
        self.modo_var = ctk.StringVar(value="Karaoke")
        self.estilo_kinetic_var = ctk.StringVar(value="Wave")
        self.fuente_var = ctk.StringVar(value="Arial")
        # Spot
        self.spot_enabled = ctk.BooleanVar(value=False)
        self.spot_type = ctk.StringVar(value="Texto")
        self.spot_file = ctk.StringVar()
        self.spot_text = ctk.StringVar(value="Escuchala en todas las plataformas")
        self.spot_subtext = ctk.StringVar(value="@dudiver")
        self.spot_duration = ctk.StringVar(value="5 seg")

        # Plataformas de streaming
        self.platform_vars = {}
        for key in ("spotify", "apple_music", "youtube_music", "amazon_music", "custom"):
            self.platform_vars[f"{key}_enabled"] = ctk.BooleanVar(value=False)
            self.platform_vars[f"{key}_url"] = ctk.StringVar(value="")

        self.formato_var = ctk.StringVar(value="MP4")
        self.preview_time = ctk.DoubleVar(value=0.0)
        # Posición de letras
        self.lyrics_pos_var = ctk.StringVar(value="Centro")
        self.lyrics_margin_var = ctk.IntVar(value=40)
        self._lyrics_drag_offset = 0   # offset acumulado en píxeles de video
        self._preview_scale = 1.0      # ratio canvas/video para convertir drag
        # Recuadro de texto
        self.chk_text_box = ctk.BooleanVar(value=False)
        self.text_box_opacity_var = ctk.IntVar(value=70)
        self.text_box_radius_var = ctk.IntVar(value=8)
        self.chk_dim_bg = ctk.BooleanVar(value=True)

        self._cancel = False
        self._worker = None
        self._lineas = None
        self._whisper_raw = None  # Datos Whisper crudos (palabras individuales)
        self._dur = 0.0
        self._data_lock = threading.Lock()  # protege _lineas y _dur
        self._preview_pool = ThreadPoolExecutor(max_workers=1)
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
                               on_settings=self._open_settings,
                               on_about=self._open_about,
                               on_sync_editor=self._open_sync_editor,
                               on_help=self._open_help,
                               on_save_project=self._save_project,
                               on_open_project=self._open_project,
                               on_new_project=self._new_project,
                               all_inputs=self._all_inputs)
        self.toolbar.pack(fill="x")

        # Accent line
        ctk.CTkFrame(self, fg_color=ACCENT, height=2, corner_radius=0).pack(fill="x")

        # ── Body: 3 columnas ──
        body = ctk.CTkFrame(self, fg_color=DARK, corner_radius=0)
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.rowconfigure(0, weight=1)
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

        # COL 1: Config + Spot + Log (scrollable)
        col1 = ctk.CTkFrame(body, fg_color=DARK, corner_radius=0)
        col1.grid(row=0, column=1, sticky="nsew", padx=6)

        col1_scroll = ctk.CTkScrollableFrame(col1, fg_color=DARK, corner_radius=0,
                                              scrollbar_button_color="#2a2a4a",
                                              scrollbar_button_hover_color=ACCENT)
        col1_scroll.pack(fill="both", expand=True)

        self.config_panel = ConfigPanel(col1_scroll,
                                        tamano_var=self.tamano_var,
                                        fps_var=self.fps_var,
                                        esquema_var=self.esquema_var,
                                        whisper_var=self.whisper_var,
                                        duracion_var=self.duracion_var,
                                        font_size_var=self.font_size_var,
                                        modo_var=self.modo_var,
                                        estilo_kinetic_var=self.estilo_kinetic_var,
                                        fuente_var=self.fuente_var,
                                        formato_var=self.formato_var,
                                        chk_particulas=self.chk_particulas,
                                        chk_onda=self.chk_onda,
                                        chk_vineta=self.chk_vineta,
                                        chk_glow=self.chk_glow,
                                        chk_barra=self.chk_barra,
                                        lyrics_pos_var=self.lyrics_pos_var,
                                        lyrics_margin_var=self.lyrics_margin_var,
                                        chk_text_box=self.chk_text_box,
                                        text_box_opacity_var=self.text_box_opacity_var,
                                        text_box_radius_var=self.text_box_radius_var,
                                        chk_dim_bg=self.chk_dim_bg,
                                        all_inputs=self._all_inputs)
        self.config_panel.pack(fill="x")

        self.spot_panel = SpotPanel(col1_scroll,
                                    spot_enabled=self.spot_enabled,
                                    spot_type=self.spot_type,
                                    spot_file=self.spot_file,
                                    spot_text=self.spot_text,
                                    spot_subtext=self.spot_subtext,
                                    spot_duration=self.spot_duration,
                                    platform_vars=self.platform_vars,
                                    all_inputs=self._all_inputs)
        self.spot_panel.pack(fill="x")

        # Log
        self.log_text = ctk.CTkTextbox(col1_scroll, height=60, font=("Consolas", 9),
                                       fg_color="#080810", text_color=GREEN,
                                       corner_radius=8, border_width=1,
                                       border_color="#1a1a2a")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=(6, 0))
        self.log_text.configure(state="disabled")
        # Tags para colorear errores y warnings
        self.log_text._textbox.tag_config("error", foreground="#ff4444")
        self.log_text._textbox.tag_config("warn", foreground="#ffaa00")

        # COL 2: Preview
        self.preview_panel = PreviewPanel(body,
                                          preview_time=self.preview_time,
                                          on_time_change=self._on_time_change,
                                          on_lyrics_drag=self._on_lyrics_drag)
        self.preview_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        # Watchers — auto-preview + auto-save al cambiar configuración
        self.audio_path.trace_add("write", self._on_audio_change)
        for var in [self.modo_var, self.fuente_var, self.estilo_kinetic_var,
                    self.esquema_var, self.font_size_var, self.tamano_var,
                    self.fps_var, self.duracion_var, self.alpha_var,
                    self.fondo_path, self.titulo_var,
                    self.chk_particulas, self.chk_onda, self.chk_vineta,
                    self.chk_glow, self.chk_barra,
                    self.spot_enabled, self.spot_type, self.spot_text,
                    self.spot_subtext, self.spot_duration, self.formato_var,
                    self.lyrics_margin_var,
                    self.chk_text_box, self.text_box_opacity_var,
                    self.text_box_radius_var, self.chk_dim_bg,
                    *self.platform_vars.values()]:
            var.trace_add("write", self._auto_preview)
            var.trace_add("write", self._auto_save_project)
        # Al cambiar preset de posición, resetear el offset de drag
        self.lyrics_pos_var.trace_add("write", self._on_lyrics_pos_change)
        self.audio_path.trace_add("write", self._auto_save_project)
        self.fondo_path.trace_add("write", self._auto_save_project)
        self.spot_file.trace_add("write", self._auto_save_project)
        self._preview_pending = None
        self._save_pending = None
        self._dudi_path = None  # Ruta al .dudi activo
        self._loading_project = False
        self._new_project_mode = False  # True tras "Nuevo": ignora auto-load de .dudi
        self.duracion_var.trace_add("write", self._on_duration_change)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _resolution(self):
        return TAMANOS.get(self.tamano_var.get(), (1920, 1080))

    def _max_duration(self):
        """Retorna duración del clip basada en rango Desde/Hasta."""
        start, end = self.preview_panel.get_range()
        if end > start:
            return end - start
        return 0  # Completo

    def _start_time(self):
        start, end = self.preview_panel.get_range()
        return start if end > start else 0

    def _on_duration_change(self, *_):
        dur = DURACIONES.get(self.duracion_var.get(), 0)
        if dur > 0:
            audio_dur = getattr(self, '_dur', 300) or 300
            self.preview_panel.show_range(dur, audio_dur)
        else:
            self.preview_panel.hide_range()

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
        fmt = self.formato_var.get()
        EXT_MAP = {"MP4": ".mp4", "WebM": ".webm", "MOV (ProRes)": ".mov", "AVI": ".avi"}
        ext = EXT_MAP.get(fmt, ".mp4")
        # Preferir carpeta del .dudi activo, luego del audio, luego Desktop
        if self._dudi_path and os.path.isfile(self._dudi_path):
            folder = os.path.dirname(self._dudi_path)
        elif audio:
            folder = os.path.dirname(audio)
        else:
            folder = os.path.expanduser("~/Desktop")
        return os.path.join(folder, f"{safe}_visualizer{ext}")

    def _esquema(self):
        key = ESQUEMAS_GUI.get(self.esquema_var.get(), "nocturno")
        return ESQUEMAS.get(key, ESQUEMAS["nocturno"])

    def _spot_seconds(self):
        return int(self.spot_duration.get().split()[0])

    def _active_platform_urls(self):
        """Retorna dict de plataformas activas {key: url}."""
        urls = {}
        for key in ("spotify", "apple_music", "youtube_music", "amazon_music", "custom"):
            enabled = self.platform_vars.get(f"{key}_enabled")
            url_var = self.platform_vars.get(f"{key}_url")
            if enabled and enabled.get() and url_var and url_var.get().strip():
                urls[key] = url_var.get().strip()
        return urls

    def _ensure_timing(self, lines):
        with self._data_lock:
            if self._lineas and len(self._lineas) > 0:
                return self._lineas
        ts_path = get_ts_path(self.audio_path.get())
        timing = load_existing(ts_path, lines)
        if timing:
            with self._data_lock:
                self._lineas = timing
        return timing

    # ── Logging & Status ────────────────────────────────────────────────────

    def _log(self, msg):
        def _a():
            self.log_text.configure(state="normal")
            # Detectar errores/warnings para colorear
            is_error = any(k in msg.lower() for k in ["error", "\u2715", "traceback", "exception"])
            is_warn = any(k in msg.lower() for k in ["warn", "advertencia"])
            if is_error:
                self.log_text._textbox.insert("end", msg + "\n", "error")
            elif is_warn:
                self.log_text._textbox.insert("end", msg + "\n", "warn")
            else:
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

    def _build_effects(self):
        """Construye el dict de efectos unificado para render y preview."""
        return {
            "particulas": self.chk_particulas.get(),
            "onda": self.chk_onda.get(),
            "vineta": self.chk_vineta.get(),
            "glow": self.chk_glow.get(),
            "barra": self.chk_barra.get(),
            "dim_bg": self.chk_dim_bg.get(),
            "text_box": self.chk_text_box.get(),
            "text_box_opacity": self.text_box_opacity_var.get(),
            "text_box_radius": self.text_box_radius_var.get(),
        }

    def _kinetic_base_y(self, total_h, alto):
        """Calcula el Y de inicio del bloque de texto kinetic según la posición configurada."""
        pos = self.lyrics_pos_var.get()
        margin = self.lyrics_margin_var.get()
        offset = self._lyrics_drag_offset
        if pos == "Arriba":
            base_y = margin
        elif pos == "Abajo":
            base_y = alto - total_h - margin
        else:
            base_y = (alto - total_h) // 2
        base_y += offset
        return max(0, min(alto - max(total_h, 1), base_y))

    def _on_lyrics_pos_change(self, *_):
        """Al cambiar preset (Arriba/Centro/Abajo), resetea el offset de drag."""
        self._lyrics_drag_offset = 0
        self._auto_preview()

    def _on_lyrics_drag(self, dy_canvas):
        """Convierte delta de canvas a píxeles de video y acumula offset."""
        scale = self._preview_scale
        if scale > 0:
            dy_video = int(dy_canvas / scale)
            self._lyrics_drag_offset += dy_video
            # Disparar preview inmediato (sin debounce para drag fluido)
            if self._preview_pending:
                self.after_cancel(self._preview_pending)
            self._preview_pending = None
            self.preview_panel.switch_to_preview()
            self._preview_pool.submit(self._preview_thread)

    def _on_time_change(self, val):
        m, s = divmod(int(float(val)), 60)
        self.preview_panel.time_label.configure(text=f"{m}:{s:02d}")
        # Reproducir audio al mover slider
        self.preview_panel.play_audio_at(float(val))
        # Preview con debounce (no en cada pixel del slider)
        self._auto_preview()

    def _on_audio_change(self, *_):
        p = self.audio_path.get()
        if p and os.path.isfile(p):
            self.preview_panel.info_label.configure(text=f"\U0001f3b5 {short_path(p, 50)}")
            # Auto-cargar proyecto .dudi si existe en la carpeta del audio
            # (se omite si venimos de "Nuevo proyecto" para no restaurar el anterior)
            folder = os.path.dirname(p)
            dudi = find_dudi(folder)
            new_project_mode = getattr(self, '_new_project_mode', False)
            if new_project_mode:
                # Consumir el flag — ya no bloquear en carga siguiente
                self._new_project_mode = False
            if dudi and not new_project_mode:
                try:
                    config = load_dudi(dudi)
                    self._dudi_path = dudi
                    apply_project(self, config)
                    name = os.path.splitext(os.path.basename(dudi))[0]
                    self._log(f"Proyecto cargado: {name}")
                except Exception:
                    pass
            elif not self.titulo_var.get().strip():
                name = os.path.splitext(os.path.basename(p))[0]
                name = re.sub(r'\s*\((?:Remastered|Master|Final|Mix|v\d+)\)', '', name, flags=re.IGNORECASE)
                name = re.sub(r'[-_]\d+$', '', name)
                name = re.sub(r'[-_](v\d+|final|master|mix)$', '', name, flags=re.IGNORECASE)
                self.titulo_var.set(name.strip())
            self.preview_panel.set_audio(p)
            threading.Thread(target=self._load_audio_info, daemon=True).start()

    def _load_audio_info(self):
        try:
            from moviepy import AudioFileClip
            ac = AudioFileClip(self.audio_path.get())
            dur = ac.duration
            ac.close()
            with self._data_lock:
                self._dur = dur
            m, s = divmod(int(dur), 60)
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
            messagebox.showwarning(t("app.warn"), t("app.select_audio"))
            return
        if self._worker and self._worker.is_alive():
            return

        # Verificar si ya existen timestamps
        ts_path = get_ts_path(audio)
        already_has = False
        if ts_path and os.path.isfile(ts_path):
            already_has = True
        # También verificar si ya hay timing en memoria (sync editor, AI, etc.)
        with self._data_lock:
            if self._lineas and len(self._lineas) > 0:
                already_has = True

        if already_has:
            # Preguntar si quiere re-ejecutar
            resp = messagebox.askyesno(
                "Sincronización existente",
                "Ya hay sincronización de letra.\n"
                "¿Quieres re-analizar el audio?\n\n"
                "(Esto reemplazará la sincronización actual)")
            if not resp:
                # Cargar los existentes si no están en memoria
                lines = self._lyrics()
                timing = self._ensure_timing(lines)
                if timing:
                    self._set_status(
                        f"\u2713 Timestamps cargados ({len(timing)} líneas)", 100)
                return

        self._cancel = False
        self._disable_ui()
        self._worker = threading.Thread(target=self._ts_worker, daemon=True)
        self._worker.start()

    def _ts_worker(self):
        audio = self.audio_path.get()
        from app.config import whisper_model_name
        label = self.whisper_var.get()
        modelo = whisper_model_name(label)
        self._set_status(f"\u27f3 Analizando audio ({label})...", 10)
        self._log(f"Sincronizando letra... precisión={label} (modelo={modelo})")
        try:
            lines = self._lyrics()
            # Ejecutar Whisper
            res = whisper_generar_timestamps(audio, modelo=modelo, idioma="es")
            n = len(res.get("palabras", []))
            # Alinear con la letra
            timing = alinear_letra_con_whisper(lines, res["palabras"])
            with self._data_lock:
                self._lineas = timing
            # Guardar raw data en memoria para Kinetic y para embeber en .dudi
            self._whisper_raw = res
            # También guardar JSON externo para compatibilidad
            ts_path = get_ts_path(audio)
            if ts_path:
                import json
                with open(ts_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
            self._log(f"\u2713 {n} palabras detectadas")
            self._set_status(f"\u2713 Timestamps listos ({n} palabras)", 100)
            # Auto-save al .dudi
            self._auto_save_project()
        except Exception as ex:
            self._log(f"\u2715 ERROR: {ex}")
            self._set_status(f"\u2715 Error: {ex}", 0)
        self._enable_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  PREVIEW
    # ══════════════════════════════════════════════════════════════════════════

    def _auto_save_project(self, *_):
        """Auto-guarda el proyecto con debounce de 1s."""
        if getattr(self, '_loading_project', False):
            return
        if self._save_pending:
            self.after_cancel(self._save_pending)
        self._save_pending = self.after(1000, self._do_auto_save)

    def _do_auto_save(self):
        """Guarda el proyecto al .dudi activo."""
        if not self._dudi_path:
            # Si no hay .dudi activo, crear uno en la carpeta del audio
            audio = self.audio_path.get()
            if not audio or not os.path.isfile(audio):
                return
            titulo = self.titulo_var.get().strip() or "proyecto"
            safe = "".join(c if (c.isalnum() or c in " _-") else "_" for c in titulo).strip()
            self._dudi_path = os.path.join(os.path.dirname(audio), f"{safe}.dudi")
        try:
            config = get_project_config(self)
            save_dudi_quick(self._dudi_path, config)
        except Exception as e:
            # Si quick save falla, intentar save completo
            try:
                config = get_project_config(self)
                save_dudi(self._dudi_path, config)
            except Exception:
                pass

    def _auto_preview(self, *_):
        """Dispara preview automático con debounce de 300ms."""
        if self._preview_pending:
            self.after_cancel(self._preview_pending)
        # Cambiar a tab Preview y pausar video si estaba reproduciéndose
        self.preview_panel.switch_to_preview()
        self._preview_pending = self.after(300, self._do_auto_preview)

    def _do_auto_preview(self):
        """Ejecuta preview si hay letra disponible."""
        self._preview_pending = None
        lines = self._lyrics()
        if not lines:
            return
        # Mostrar "Cargando..." y generar en pool (max 1 thread, evita acumulación)
        self._show_loading()
        self._preview_pool.submit(self._preview_thread)

    def _show_loading(self):
        """Muestra indicador de carga en el canvas."""
        canvas = self.preview_panel.preview_canvas
        canvas.delete("all")
        cw = max(canvas.winfo_width(), 200)
        ch = max(canvas.winfo_height(), 200)
        canvas.create_text(cw // 2, ch // 2, text="Generando preview...",
                           fill="#7a7a9a", font=("Segoe UI", 12))

    def _preview_thread(self):
        """Genera preview en background thread."""
        try:
            lines = self._lyrics()
            if not lines:
                return
            modo = self.modo_var.get()
            ancho, alto = self._resolution()
            t = self.preview_time.get()
            titulo = self.titulo_var.get().strip()

            if modo == "Kinetic Typography":
                img = self._preview_kinetic(ancho, alto, lines, t, titulo)
            else:
                fuente, fuente_titulo, fuente_peq, _ff = adapted_fonts(
                    self.font_size_var.get(), ancho, alto, lines,
                    font_name=self.fuente_var.get())
                if not _ff:
                    self._log(f"\u26a0 Fuente '{self.fuente_var.get()}' no encontrada, usando Arial")
                timing = self._ensure_timing(lines) or fallback_timing(lines, self._dur or 180)
                img = render_preview_frame(
                    ancho=ancho, alto=alto, timing=timing, t=t,
                    dur=self._dur or 180, titulo=titulo,
                    fuente=fuente, fuente_titulo=fuente_titulo, fuente_peq=fuente_peq,
                    esquema_key=self.esquema_var.get(),
                    alpha_mode=self.alpha_var.get(),
                    fondo_path=self.fondo_path.get(),
                    lyrics_pos=self.lyrics_pos_var.get(),
                    lyrics_margin=self.lyrics_margin_var.get(),
                    lyrics_extra_y=self._lyrics_drag_offset,
                    effects=self._build_effects())

            self.after(0, lambda: self._show_preview_image(img, ancho, alto))
        except Exception:
            pass

    def _preview_frame(self):
        lines = self._lyrics()
        if not lines:
            messagebox.showinfo(t("app.info"), t("app.add_lyrics_first"))
            return

        modo = self.modo_var.get()
        ancho, alto = self._resolution()
        t = self.preview_time.get()
        titulo = self.titulo_var.get().strip()

        if modo == "Kinetic Typography":
            img = self._preview_kinetic(ancho, alto, lines, t, titulo)
        else:
            fuente, fuente_titulo, fuente_peq, _ff = adapted_fonts(
                self.font_size_var.get(), ancho, alto, lines,
                font_name=self.fuente_var.get())
            timing = self._ensure_timing(lines) or fallback_timing(lines, self._dur or 180)
            img = render_preview_frame(
                ancho=ancho, alto=alto, timing=timing, t=t,
                dur=self._dur or 180, titulo=titulo,
                fuente=fuente, fuente_titulo=fuente_titulo, fuente_peq=fuente_peq,
                esquema_key=self.esquema_var.get(),
                alpha_mode=self.alpha_var.get(),
                fondo_path=self.fondo_path.get(),
                lyrics_pos=self.lyrics_pos_var.get(),
                lyrics_margin=self.lyrics_margin_var.get(),
                lyrics_extra_y=self._lyrics_drag_offset,
                effects=self._build_effects())

        self._show_preview_image(img, ancho, alto)

    def _load_palabras_whisper(self):
        """Carga palabras individuales del JSON de Whisper si existe."""
        audio = self.audio_path.get()
        if not audio:
            return None
        ts_file = os.path.splitext(audio)[0] + "_timestamps.json"
        if not os.path.isfile(ts_file):
            return None
        try:
            import json as _json
            with open(ts_file, "r", encoding="utf-8") as f:
                data = _json.load(f)
            if isinstance(data, dict) and "palabras" in data and data["palabras"]:
                return data["palabras"]
        except Exception:
            pass
        return None

    def _preview_kinetic(self, ancho, alto, lines, t, titulo):
        """Genera preview de Kinetic Typography con estilo multi-línea."""
        from PIL import ImageDraw, ImageFont
        esquema_key = ESQUEMA_GUI_TO_KINETIC.get(self.esquema_var.get(), "neon")
        from app.core.kinetic_pil import ESQUEMAS as ESQUEMAS_KINETIC
        esquema = ESQUEMAS_KINETIC.get(esquema_key, ESQUEMAS_KINETIC["neon"])

        _efx_prev = self._build_effects()
        _dim = _efx_prev.get("dim_bg", True)
        _bg_brightness = 0.2 if _dim else 1.0
        fondo = self.fondo_path.get()
        if fondo and os.path.isfile(fondo):
            ext = os.path.splitext(fondo)[1].lower()
            from PIL import ImageEnhance
            if ext in (".jpg", ".jpeg", ".png", ".bmp"):
                bg = Image.open(fondo).resize((ancho, alto), Image.LANCZOS).convert("RGB")
                img = ImageEnhance.Brightness(bg).enhance(_bg_brightness)
            elif ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
                from app.core.renderer import _extract_video_frame
                bg = _extract_video_frame(fondo, t, ancho, alto)
                if bg:
                    img = ImageEnhance.Brightness(bg.convert("RGB")).enhance(_bg_brightness)
                else:
                    img = Image.new("RGB", (ancho, alto), (8, 8, 16))
            else:
                img = Image.new("RGB", (ancho, alto), (8, 8, 16))
        else:
            img = Image.new("RGB", (ancho, alto), (8, 8, 16))
        draw = ImageDraw.Draw(img)

        font_name = self.fuente_var.get()
        font_size = self.font_size_var.get()
        font_path = resolve_font_path(font_name)
        if not font_path:
            font_path = "arial.ttf"

        def _make_font(sz):
            try:
                return ImageFont.truetype(font_path, sz)
            except Exception:
                try:
                    return ImageFont.truetype("arial.ttf", sz)
                except Exception:
                    return ImageFont.load_default()

        fuente = _make_font(font_size)
        fuente_peq = _make_font(14)

        color_activo = esquema["activo"]
        color_pasado = esquema["pasado"]
        color_futuro = esquema["futuro"]
        glow_color = esquema["glow"]

        estilo = self.estilo_kinetic_var.get()
        draw.text((ancho // 2, 30), f"KINETIC  ·  {estilo.upper()}",
                  fill="#3a3a5a", font=fuente_peq, anchor="mt")
        if titulo:
            draw.text((ancho // 2, alto - 40), titulo, fill="#4a4a6a",
                      font=_make_font(18), anchor="mb")

        palabras = self._load_palabras_whisper()
        estilo_val = ESTILOS_KINETIC.get(estilo, "wave")

        if estilo_val == "oneword":
            if palabras:
                from app.core.kinetic_pil import group_smart_oneword
                palabras = group_smart_oneword(palabras)
                img = self._draw_kinetic_oneword(img, palabras, t, ancho, alto,
                                                 font_path, font_size, color_activo,
                                                 glow_color, effects=_efx_prev)
            else:
                timing_fb = self._ensure_timing(lines) or fallback_timing(lines, self._dur or 180)
                pseudo = [{"inicio": ts.get("inicio", 0), "fin": ts.get("fin", 0),
                           "palabra": ts.get("texto", ts.get("linea", ""))}
                          for ts in timing_fb if ts.get("texto", ts.get("linea", "")).strip()]
                img = self._draw_kinetic_oneword(img, pseudo, t, ancho, alto,
                                                 font_path, font_size, color_activo,
                                                 glow_color, effects=_efx_prev)
        elif palabras:
            img = self._draw_kinetic_words(img, palabras, t, ancho, alto,
                                           fuente, font_path, font_size,
                                           color_activo, color_pasado,
                                           color_futuro, glow_color, effects=_efx_prev)
        else:
            img = self._draw_kinetic_lines(img, lines, t, ancho, alto,
                                           fuente, font_path, font_size,
                                           color_activo, color_pasado,
                                           color_futuro, glow_color, effects=_efx_prev)

        img = self._apply_kinetic_effects(img, ancho, alto, t, _efx_prev, esquema)
        return img

    def _draw_kinetic_oneword(self, img, palabras, t, ancho, alto,
                              font_path, font_size, color_activo, glow_color,
                              effects=None):
        """Una sola palabra grande centrada que cambia según el tiempo."""
        from PIL import ImageFont, ImageDraw

        draw = ImageDraw.Draw(img)

        def _font(sz):
            try:
                return ImageFont.truetype(font_path, sz)
            except Exception:
                return ImageFont.truetype("arial.ttf", sz)

        # Encontrar la palabra activa
        palabra_actual = None
        palabra_next = None
        for i, w in enumerate(palabras):
            if w["inicio"] <= t <= w["fin"]:
                palabra_actual = w
                if i + 1 < len(palabras):
                    palabra_next = palabras[i + 1]
                break
            if w["inicio"] > t:
                if i > 0:
                    palabra_actual = palabras[i - 1]
                palabra_next = w
                break
        else:
            if palabras and t > palabras[-1]["fin"]:
                palabra_actual = palabras[-1]

        # Si no hay activa (antes del inicio o entre palabras), mostrar la próxima
        if not palabra_actual:
            if palabra_next:
                palabra_actual = palabra_next
            else:
                return img

        texto = palabra_actual["palabra"].strip(" ,.:;!?")
        if not texto:
            return img

        # Tamaño grande — slider × 2, proporcional al canvas
        big_size = max(font_size * 2, 60)

        f_big = _font(big_size)
        bbox = draw.textbbox((0, 0), texto, font=f_big)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw > ancho * 0.85:
            scale = (ancho * 0.85) / tw
            f_big = _font(int(big_size * scale))
            bbox = draw.textbbox((0, 0), texto, font=f_big)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

        cx = ancho // 2
        cy = self._kinetic_base_y(big_size, alto) + big_size // 2

        # Recuadro detrás del texto
        if effects and effects.get("text_box", False):
            from app.scripts.lyric_video import _draw_text_box
            opacity = int(effects.get("text_box_opacity", 70) * 2.55)
            radius = int(effects.get("text_box_radius", 8))
            pad_x, pad_y = 20, 12
            x1 = cx - tw // 2 - pad_x
            y1 = cy - th // 2 - pad_y
            x2 = cx + tw // 2 + pad_x
            y2 = cy + th // 2 + pad_y
            img = _draw_text_box(img, x1, y1, x2, y2, (0, 0, 0), opacity, radius)
            draw = ImageDraw.Draw(img)

        # Glow
        for dx in [-3, -2, -1, 1, 2, 3]:
            for dy in [-3, -2, -1, 1, 2, 3]:
                draw.text((cx + dx, cy + dy), texto,
                          fill=glow_color + "25", font=f_big, anchor="mm")

        draw.text((cx, cy), texto, fill=color_activo, font=f_big, anchor="mm")

        # Palabra siguiente en pequeño abajo
        if palabra_next:
            next_txt = palabra_next["palabra"].strip(" ,.:;!?")
            if next_txt:
                f_sm = _font(max(16, int(big_size * 0.35)))
                draw.text((cx, cy + big_size * 0.7), next_txt,
                          fill="#3a3a5a", font=f_sm, anchor="mm")

        return img

    def _draw_kinetic_words(self, img, palabras, t, ancho, alto,
                            fuente, font_path, font_size, color_activo,
                            color_pasado, color_futuro, glow_color, effects=None):
        """Dibuja preview word-by-word con la palabra activa resaltada."""
        from PIL import ImageFont, ImageDraw

        draw = ImageDraw.Draw(img)

        def _font(sz):
            try:
                return ImageFont.truetype(font_path, sz)
            except Exception:
                return ImageFont.truetype("arial.ttf", sz)

        # Agrupar palabras en frases (gap > 0.8s = nueva frase)
        frases = []
        frase_actual = []
        for w in palabras:
            if frase_actual and (w["inicio"] - frase_actual[-1]["fin"]) > 0.8:
                frases.append(frase_actual)
                frase_actual = []
            frase_actual.append(w)
        if frase_actual:
            frases.append(frase_actual)

        # Encontrar frase activa
        active_frase = 0
        for i, frase in enumerate(frases):
            if frase[0]["inicio"] <= t <= frase[-1]["fin"]:
                active_frase = i
                break
            if frase[0]["inicio"] > t:
                active_frase = max(0, i - 1)
                break
        else:
            if frases and t > frases[-1][-1]["fin"]:
                active_frase = len(frases) - 1

        # Mostrar ventana de frases alrededor de la activa
        max_frases = 6
        start = max(0, active_frase - 2)
        end = min(len(frases), start + max_frases)
        visible = frases[start:end]

        line_h = int(font_size * 1.6)
        total_h = len(visible) * line_h
        y_start = self._kinetic_base_y(total_h, alto)

        # Recuadro detrás de cada frase
        use_box = effects and effects.get("text_box", False)
        if use_box:
            from app.scripts.lyric_video import _draw_text_box
            box_opacity = int(effects.get("text_box_opacity", 70) * 2.55)
            box_radius = int(effects.get("text_box_radius", 8))

        for fi, frase in enumerate(visible):
            real_fi = start + fi
            y = y_start + fi * line_h

            texto_frase = " ".join(w["palabra"] for w in frase)

            # Escalar fuente si la frase es muy ancha
            bbox = draw.textbbox((0, 0), texto_frase, font=fuente)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if tw > ancho * 0.85:
                f_used = _font(int(font_size * (ancho * 0.85) / tw))
                bbox = draw.textbbox((0, 0), texto_frase, font=f_used)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            else:
                f_used = fuente

            if use_box and texto_frase.strip():
                x1 = ancho // 2 - tw // 2 - 18
                img = _draw_text_box(img, x1, y - 6, x1 + tw + 36, y + th + 6,
                                     (0, 0, 0), box_opacity, box_radius)
                draw = ImageDraw.Draw(img)

            if real_fi != active_frase:
                color = color_pasado if real_fi < active_frase else color_futuro
                draw.text((ancho // 2, y), texto_frase, fill=color,
                          font=f_used, anchor="mt")
            else:
                total_w = 0
                word_widths = []
                space_w = draw.textlength(" ", font=f_used)
                for w in frase:
                    ww = draw.textlength(w["palabra"], font=f_used)
                    word_widths.append(ww)
                    total_w += ww
                total_w += space_w * (len(frase) - 1)

                x = (ancho - total_w) / 2

                for wi, w in enumerate(frase):
                    if t >= w["inicio"] and t <= w["fin"]:
                        for dx in [-2, -1, 1, 2]:
                            for dy in [-2, -1, 1, 2]:
                                draw.text((x + dx, y + dy), w["palabra"],
                                          fill=glow_color + "30", font=f_used, anchor="lt")
                        draw.text((x, y), w["palabra"], fill=color_activo,
                                  font=f_used, anchor="lt")
                    elif t > w["fin"]:
                        draw.text((x, y), w["palabra"], fill=color_pasado,
                                  font=f_used, anchor="lt")
                    else:
                        draw.text((x, y), w["palabra"], fill=color_futuro,
                                  font=f_used, anchor="lt")

                    x += word_widths[wi] + space_w

        return img

    def _draw_kinetic_lines(self, img, lines, t, ancho, alto,
                            fuente, font_path, font_size, color_activo,
                            color_pasado, color_futuro, glow_color, effects=None):
        """Fallback: dibuja preview por líneas cuando no hay datos de palabras."""
        from PIL import ImageFont, ImageDraw

        draw = ImageDraw.Draw(img)

        def _font(sz):
            try:
                return ImageFont.truetype(font_path, sz)
            except Exception:
                return ImageFont.truetype("arial.ttf", sz)

        timing = self._ensure_timing(lines) or fallback_timing(lines, self._dur or 180)

        active_idx = 0
        for i, ts in enumerate(timing):
            if ts.get("inicio", 0) <= t <= ts.get("fin", 0):
                active_idx = i
                break
            if ts.get("inicio", 0) > t:
                active_idx = max(0, i - 1)
                break

        max_lines = 7
        start = max(0, active_idx - 2)
        end = min(len(timing), start + max_lines)
        visible = timing[start:end]

        line_h = int(font_size * 1.6)
        total_h = len(visible) * line_h
        y_start = self._kinetic_base_y(total_h, alto)

        use_box = effects and effects.get("text_box", False)
        if use_box:
            from app.scripts.lyric_video import _draw_text_box
            box_opacity = int(effects.get("text_box_opacity", 70) * 2.55)
            box_radius = int(effects.get("text_box_radius", 8))

        for i, ts in enumerate(visible):
            real_idx = start + i
            linea = ts.get("linea", ts.get("texto", ""))
            y = y_start + i * line_h

            if real_idx < active_idx:
                color = color_pasado
            elif real_idx == active_idx:
                color = color_activo
            else:
                color = color_futuro

            bbox = draw.textbbox((0, 0), linea, font=fuente)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if tw > ancho * 0.85:
                f_scaled = _font(int(font_size * (ancho * 0.85) / tw))
                bbox = draw.textbbox((0, 0), linea, font=f_scaled)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            else:
                f_scaled = fuente

            if use_box and linea.strip():
                x1 = ancho // 2 - tw // 2 - 18
                img = _draw_text_box(img, x1, y - 6, x1 + tw + 36, y + th + 6,
                                     (0, 0, 0), box_opacity, box_radius)
                draw = ImageDraw.Draw(img)

            if real_idx == active_idx:
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((ancho // 2 + dx, y + dy), linea,
                                  fill=glow_color + "30", font=f_scaled, anchor="mt")

            draw.text((ancho // 2, y), linea, fill=color, font=f_scaled, anchor="mt")

        return img

    def _apply_kinetic_effects(self, img, ancho, alto, t, effects, esquema):
        """Aplica efectos visuales (viñeta, glow, partículas, barra) a la preview Kinetic."""
        from PIL import ImageDraw, ImageFilter
        import random

        # Viñeta
        if effects.get("vineta", False):
            vignette = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vignette)
            for i in range(40):
                alpha = int(180 * (1 - i / 40))
                vdraw.rectangle([i, i, ancho - i, alto - i],
                                outline=(0, 0, 0, alpha))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, vignette).convert("RGB")

        # Glow global (bloom suave)
        if effects.get("glow", False):
            glow = img.filter(ImageFilter.GaussianBlur(radius=15))
            from PIL import ImageEnhance
            glow = ImageEnhance.Brightness(glow).enhance(1.3)
            img = Image.blend(img, glow, 0.15)

        # Partículas simples
        if effects.get("particulas", False):
            draw = ImageDraw.Draw(img)
            random.seed(int(t * 10))
            color_p = esquema.get("activo", "#ffffff")
            for _ in range(25):
                px = random.randint(0, ancho)
                py = random.randint(0, alto)
                sz = random.randint(1, 3)
                alpha_hex = format(random.randint(40, 160), '02x')
                draw.ellipse([px, py, px + sz, py + sz],
                             fill=color_p + alpha_hex)

        # Onda decorativa inferior
        if effects.get("onda", False):
            draw = ImageDraw.Draw(img)
            import math
            y_base = alto - 30
            color_w = esquema.get("glow", "#4040ff")
            for x in range(0, ancho, 2):
                y = y_base + int(8 * math.sin((x + t * 100) * 0.03))
                draw.line([(x, y), (x + 2, y)], fill=color_w + "60", width=2)

        # Barra de progreso
        if effects.get("barra", False):
            draw = ImageDraw.Draw(img)
            dur = self._dur or 180
            progress = min(1.0, t / dur) if dur > 0 else 0
            bar_y = alto - 6
            bar_w = int(ancho * progress)
            draw.rectangle([0, bar_y, ancho, alto], fill="#1a1a2e")
            if bar_w > 0:
                draw.rectangle([0, bar_y, bar_w, alto],
                               fill=esquema.get("activo", "#e94560"))

        return img

    def _show_preview_image(self, img, ancho, alto):
        """Muestra imagen en el canvas de preview."""
        canvas = self.preview_panel.preview_canvas
        self.update_idletasks()
        cw = max(canvas.winfo_width(), 200)
        ch = max(canvas.winfo_height(), 200)
        ratio = min(cw / ancho, ch / alto)
        self._preview_scale = ratio  # guardar para convertir drag canvas→video
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
            messagebox.showwarning(t("app.warn"), t("app.select_audio_short"))
            return
        lines = self._lyrics()
        if not lines:
            messagebox.showwarning(t("app.warn"), t("app.add_lyrics"))
            return

        # Advertir si no hay timestamps procesados
        has_timing = False
        with self._data_lock:
            has_timing = bool(self._lineas and len(self._lineas) > 0)
        if not has_timing:
            ts_path = get_ts_path(audio)
            has_timing = bool(ts_path and os.path.isfile(ts_path))
        if not has_timing:
            resp = messagebox.askyesno(
                "⚠️ Sin timestamps de letra",
                "No se han procesado los timestamps con IA (botón Timestamps).\n\n"
                "Si continúas, se generará el video con fondo musical e imagen/video,\n"
                "pero SIN letra sincronizada.\n\n"
                "¿Deseas continuar de todas formas?",
                icon="warning"
            )
            if not resp:
                return

        if self._worker and self._worker.is_alive():
            return

        # Preguntar dónde guardar
        from tkinter import filedialog
        default_name = self._output_path()
        ext = os.path.splitext(default_name)[1] or ".mp4"
        ftypes = [("Video", f"*{ext}"), ("MP4", "*.mp4"), ("WebM", "*.webm"),
                  ("MOV", "*.mov"), ("AVI", "*.avi"), (t("files.all"), "*.*")]
        output = filedialog.asksaveasfilename(
            title=t("app.save_as"),
            initialdir=os.path.dirname(default_name),
            initialfile=os.path.basename(default_name),
            defaultextension=ext,
            filetypes=ftypes,
        )
        if not output:
            return

        self._custom_output = output
        self._cancel = False
        self._render_proc = None  # multiprocessing.Process
        self._disable_ui()
        self._set_status("\u27f3 Preparando...", 1)
        self._worker = threading.Thread(target=self._gen_worker, args=(lines,), daemon=True)
        self._worker.start()

    def _gen_worker(self, lines):
        ancho, alto = self._resolution()

        # Pre-cargar timing si ya existe (evita Whisper en subprocess)
        timing = self._ensure_timing(lines)

        # Resolver estilo kinetic
        estilo_k = ESTILOS_KINETIC.get(self.estilo_kinetic_var.get(), "wave")
        esquema_k = ESQUEMA_GUI_TO_KINETIC.get(self.esquema_var.get(), "neon")

        config = {
            "audio_path": self.audio_path.get(),
            "ancho": ancho,
            "alto": alto,
            "fps": int(self.fps_var.get()),
            "titulo": self.titulo_var.get().strip(),
            "alpha_mode": self.alpha_var.get(),
            "esquema": self._esquema(),
            "fondo_path": self.fondo_path.get(),
            "output_path": getattr(self, '_custom_output', self._output_path()),
            "max_dur": self._max_duration(),
            "start_time": self._start_time(),
            "timing": timing,
            "lines": lines,
            "whisper_model": self.whisper_var.get(),
            "whisper_raw": getattr(self, '_whisper_raw', None),
            # Fonts como info serializable (se recrean en subprocess)
            "_font_name": self.fuente_var.get(),
            "_font_size_base": self.font_size_var.get(),
            "spot_on": self.spot_enabled.get(),
            "spot_type": self.spot_type.get(),
            "spot_text": self.spot_text.get(),
            "spot_subtext": self.spot_subtext.get(),
            "spot_file": self.spot_file.get(),
            "spot_secs": self._spot_seconds(),
            "platform_urls": self._active_platform_urls(),
            # Kinetic
            "modo": self.modo_var.get(),
            "estilo_kinetic": estilo_k,
            "esquema_kinetic": esquema_k,
            "fuente_nombre": self.fuente_var.get(),
            "font_size": self.font_size_var.get(),
            # Efectos
            "effects": self._build_effects(),
            # Posición letra
            "lyrics_pos": self.lyrics_pos_var.get(),
            "lyrics_margin": self.lyrics_margin_var.get(),
            "lyrics_extra_y": self._lyrics_drag_offset,
        }

        import multiprocessing
        import time as _time

        # Crear pipes para comunicación
        progress_file = os.path.join(os.path.dirname(config["output_path"]),
                                      ".render_progress.txt")
        config["_progress_file"] = progress_file

        # Lanzar en proceso separado (se puede matar)
        from app.core.render_worker import render_subprocess
        self._render_proc = multiprocessing.Process(
            target=render_subprocess, args=(config,), daemon=True)
        self._render_proc.start()
        self._log(f"Proceso de render iniciado (PID: {self._render_proc.pid})")

        # Monitorear progreso
        last_pct = 0
        last_msg = ""
        while self._render_proc.is_alive():
            if self._cancel:
                self._kill_process_tree(self._render_proc.pid)
                self._render_proc.join(timeout=2)
                self._log("✗ Render cancelado")
                self._set_status("Cancelado", 0)
                self._enable_ui()
                # Limpiar archivo parcial
                out = config.get("output_path", "")
                if out and os.path.isfile(out):
                    try:
                        os.remove(out)
                    except Exception:
                        pass
                return
            # Leer progreso del archivo
            try:
                if os.path.isfile(progress_file):
                    with open(progress_file, "r") as f:
                        line = f.read().strip()
                    if line:
                        parts = line.split("|", 1)
                        pct = int(float(parts[0])) if parts[0] else last_pct
                        msg = parts[1] if len(parts) > 1 else "Renderizando..."
                        if pct != last_pct or msg != last_msg:
                            self._set_status(f"\u27f3 {msg}", pct)
                            last_pct = pct
                            last_msg = msg
            except Exception:
                pass
            _time.sleep(0.15)

        # Proceso terminó — verificar éxito
        exit_code = self._render_proc.exitcode
        self._render_proc = None

        # Limpiar archivo de progreso
        try:
            if os.path.isfile(progress_file):
                os.remove(progress_file)
        except Exception:
            pass

        out_path = config.get("output_path", "")
        # Verificar que el archivo realmente se generó (aunque exit_code == 0)
        output_exists = bool(out_path and os.path.isfile(out_path))

        if exit_code == 0 and output_exists:
            self._set_status("✓ Video generado", 100)

            # Update timeline
            if self._dur > 0:
                m, s = divmod(int(self._dur), 60)
                self.after(0, lambda: self.preview_panel.timeline.configure(
                    to=self._dur))
                self.after(0, lambda: self.preview_panel.dur_label.configure(
                    text=f"/ {m}:{s:02d}"))

            # Cargar video generado
            self.after(0, lambda: self.preview_panel.load_video(out_path))
            self._log(f"✓ Video generado: {os.path.basename(out_path)}")
        elif exit_code == 0 and not output_exists:
            # Render reportó éxito pero el archivo no existe → error interno
            self._set_status("✗ Error generando video (ver log)", 0)
            self._log("✗ Error: el proceso terminó sin generar el video")
            err_log = out_path + ".error.log" if out_path else "dudiver_error.log"
            if os.path.isfile(err_log):
                try:
                    with open(err_log, "r") as f:
                        self._log(f.read()[:500])
                except Exception:
                    pass
        else:
            self._log(f"✗ Error en render (código: {exit_code})")
            # Revisar si hay log de error
            err_log = config.get("output_path", "") + ".error.log"
            if os.path.isfile(err_log):
                try:
                    with open(err_log, "r") as f:
                        self._log(f.read()[:500])
                except Exception:
                    pass

        self._enable_ui()

    def _do_cancel(self):
        self._cancel = True
        self._set_status("Cancelando...", None)
        # Matar proceso y todos sus hijos (FFmpeg) inmediatamente
        proc = getattr(self, '_render_proc', None)
        if proc and proc.is_alive():
            self._kill_process_tree(proc.pid)
            self._log("Proceso de render terminado")

    def _kill_process_tree(self, pid):
        """Mata un proceso y todos sus hijos (FFmpeg, etc.) de forma brutal."""
        try:
            import psutil
            parent = psutil.Process(pid)
            # Primero matar hijos (FFmpeg)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except Exception:
                    pass
            # Luego matar padre
            parent.kill()
        except Exception:
            # Fallback: Windows taskkill
            try:
                import subprocess
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True, timeout=5)
            except Exception:
                pass
        self._set_status("\u27f3 Cancelando...", None)

    def _open_folder(self):
        out = self._output_path()
        folder = os.path.dirname(out)
        if os.path.isdir(folder):
            os.startfile(folder)

    def _open_settings(self):
        SettingsWindow(self)

    def _open_about(self):
        AboutWindow(self)

    def _open_sync_editor(self):
        audio = self.audio_path.get()
        if not audio or not os.path.isfile(audio):
            messagebox.showwarning(t("app.warn"), t("app.select_audio"))
            return
        ts_path = get_ts_path(audio)

        # Si el archivo no existe en disco pero hay datos en memoria
        # (proyecto cargado desde .dudi), escribirlos al archivo
        if not ts_path or not os.path.isfile(ts_path):
            lineas_mem = None
            with self._data_lock:
                if self._lineas and len(self._lineas) > 0:
                    lineas_mem = self._lineas

            if lineas_mem and ts_path:
                # Guardar en disco para que el SyncEditor pueda abrirlos
                import json as _json
                # Usar whisper_raw si existe (formato completo), sino formato simple
                if self._whisper_raw:
                    data_to_save = self._whisper_raw
                else:
                    data_to_save = lineas_mem
                try:
                    with open(ts_path, "w", encoding="utf-8") as f:
                        _json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        if not ts_path or not os.path.isfile(ts_path):
            messagebox.showwarning(t("app.warn"), t("app.no_ts_run_whisper"))
            return

        def on_save(data):
            # Recargar timestamps en la app
            lines = self._lyrics()
            self._lineas = load_existing(ts_path, lines)
            self._auto_preview()

        SyncEditorWindow(self, audio, ts_path, on_save=on_save)

    def _open_help(self):
        HelpWindow(self)

    def _new_project(self):
        """Cierra el proyecto actual (guardando) y limpia todo para una canción nueva."""
        # ── 1. Guardar proyecto actual silenciosamente ──────────────────────────
        if self._save_pending:
            self.after_cancel(self._save_pending)
            self._save_pending = None
        # Auto-guardar si hay un .dudi activo o hay audio cargado
        audio_actual = self.audio_path.get()
        if audio_actual and os.path.isfile(audio_actual):
            try:
                self._do_auto_save()
            except Exception:
                pass

        # ── 2. Advertencia ─────────────────────────────────────────────────────
        titulo_actual = self.titulo_var.get().strip() or "el proyecto actual"
        respuesta = messagebox.askyesno(
            "Nuevo proyecto",
            f"Se cerrará «{titulo_actual}».\n\n"
            "El proyecto se ha guardado automáticamente.\n\n"
            "¿Deseas continuar y empezar una canción nueva?",
            icon="warning",
        )
        if not respuesta:
            return

        # ── 3. Limpiar toda la memoria interna ─────────────────────────────────
        self._loading_project = True
        try:
            with self._data_lock:
                self._lineas = None
                self._whisper_raw = None
                self._dur = 0.0
            self._dudi_path = None
            self._lyrics_drag_offset = 0
            self._preview_scale = 1.0
            if self._preview_pending:
                self.after_cancel(self._preview_pending)
                self._preview_pending = None

            # ── 4. Resetear todas las variables a valores por defecto ──────────
            self.audio_path.set("")
            self.letra_path.set("")
            self.fondo_path.set("")
            self.titulo_var.set("")
            self.tamano_var.set("YouTube 1920×1080")
            self.fps_var.set("30")
            self.esquema_var.set("Noche")
            self.whisper_var.set("Normal")
            self.duracion_var.set("Completo")
            self.font_size_var.set(50)
            self.alpha_var.set(False)
            self.modo_var.set("Karaoke")
            self.estilo_kinetic_var.set("Wave")
            self.fuente_var.set("Arial")
            self.formato_var.set("MP4")
            self.lyrics_pos_var.set("Centro")
            self.lyrics_margin_var.set(40)
            self.chk_particulas.set(True)
            self.chk_onda.set(True)
            self.chk_vineta.set(True)
            self.chk_glow.set(True)
            self.chk_barra.set(True)
            self.chk_text_box.set(False)
            self.text_box_opacity_var.set(70)
            self.text_box_radius_var.set(8)
            self.chk_dim_bg.set(True)
            # Spot
            self.spot_enabled.set(False)
            self.spot_type.set("Texto")
            self.spot_file.set("")
            self.spot_text.set("Escuchala en todas las plataformas")
            self.spot_subtext.set("@dudiver")
            self.spot_duration.set("5 seg")
            # Plataformas
            for k, v in self.platform_vars.items():
                if k.endswith("_enabled"):
                    v.set(False)
                else:
                    v.set("")

            # ── 5. Limpiar widgets de texto ────────────────────────────────────
            self.files_panel.letra_text.delete("1.0", "end")

            # Limpiar log
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

            # Limpiar preview
            self.preview_panel.clear_preview()
            self.preview_panel.hide_range()

        finally:
            self._loading_project = False

        # Marcar que el próximo audio cargado NO debe restaurar el .dudi anterior
        self._new_project_mode = True

        self._set_status("Listo — proyecto nuevo", 0)
        self.toolbar.set_status("Listo — proyecto nuevo")
        self._log("✓ Proyecto cerrado. Listo para nueva canción.")

    def _save_project(self):
        from tkinter import filedialog
        audio = self.audio_path.get()
        initial = os.path.dirname(audio) if audio else os.path.expanduser("~/Desktop")
        titulo = self.titulo_var.get().strip() or "proyecto"
        safe = "".join(c if (c.isalnum() or c in " _-") else "_" for c in titulo).strip()
        path = filedialog.asksaveasfilename(
            title="Guardar proyecto .dudi",
            initialdir=initial,
            initialfile=f"{safe}.dudi",
            defaultextension=".dudi",
            filetypes=[("Dudiver Project", "*.dudi")],
        )
        if not path:
            return
        config = get_project_config(self)
        save_dudi(path, config)
        self._dudi_path = path
        self._log(f"Proyecto guardado: {os.path.basename(path)}")
        messagebox.showinfo("Proyecto", f"Guardado: {os.path.basename(path)}")

    def _open_project(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Abrir proyecto",
            filetypes=[("Dudiver Project", "*.dudi"),
                       ("Legacy Project", "dudiver_project.json"),
                       (t("files.all"), "*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".dudi"):
                config = load_dudi(path)
                self._dudi_path = path
            else:
                config = load_project_legacy(path)
                self._dudi_path = None
            apply_project(self, config)
            name = os.path.splitext(os.path.basename(path))[0]
            self._log(f"Proyecto cargado: {name}")
            self._auto_preview()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
