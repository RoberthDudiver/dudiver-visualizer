"""Panel de preview (col 2): tabs Preview/Video, canvas, timeline, reproductor."""

import os
import threading
import tkinter as tk
import customtkinter as ctk

from app.config import ACCENT, ACCENT_H, GOLD, GREEN, DIM, CARD, INPUT_BG, DARK
from app.i18n import t
from app.ui.components import create_section


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, parent, *, preview_time, on_time_change, on_lyrics_drag=None):
        super().__init__(parent, fg_color=DARK, corner_radius=0)
        self._audio_path = None
        self._audio_playing = False
        self._preview_time = preview_time
        self._on_lyrics_drag = on_lyrics_drag
        self._drag_start_y = None  # canvas Y al inicio del drag

        create_section(self, t("preview.title"))

        # ── Tabs: Preview | Video ──
        self._tabs = ctk.CTkTabview(self, fg_color=DARK, height=0,
                                     segmented_button_fg_color=CARD,
                                     segmented_button_selected_color=ACCENT,
                                     segmented_button_selected_hover_color=ACCENT_H)
        self._tabs.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        tab_preview = self._tabs.add("Preview")
        tab_video = self._tabs.add("Video")

        # ── Tab Preview ──
        pv_outer = ctk.CTkFrame(tab_preview, fg_color="#080810", corner_radius=12,
                                border_width=1, border_color="#2a2a4a")
        pv_outer.pack(fill="both", expand=True)

        self.preview_canvas = tk.Canvas(pv_outer, bg="#080810", highlightthickness=0,
                                        cursor="fleur")
        self.preview_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Drag-and-drop para mover letras
        self.preview_canvas.bind("<ButtonPress-1>", self._lyrics_drag_start)
        self.preview_canvas.bind("<B1-Motion>", self._lyrics_drag_move)
        self.preview_canvas.bind("<ButtonRelease-1>", self._lyrics_drag_end)

        # ── Tab Video ──
        self._video_path = None
        self._video_playing = False
        self._video_cap = None
        self._video_fps = 30
        self._video_total_frames = 0
        self._video_current_frame = 0
        self._video_photo = None

        vid_outer = ctk.CTkFrame(tab_video, fg_color="#080810", corner_radius=12,
                                 border_width=1, border_color="#2a2a4a")
        vid_outer.pack(fill="both", expand=True)

        self.video_canvas = tk.Canvas(vid_outer, bg="#080810", highlightthickness=0)
        self.video_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Video controls
        vid_ctrl = ctk.CTkFrame(tab_video, fg_color="transparent")
        vid_ctrl.pack(fill="x", pady=(4, 0))

        self._vid_play_btn = ctk.CTkButton(vid_ctrl, text="\u25B6", width=40, height=30,
                                            font=("Segoe UI", 14),
                                            fg_color=ACCENT, hover_color=ACCENT_H,
                                            corner_radius=8, command=self._toggle_play)
        self._vid_play_btn.pack(side="left", padx=4)

        self._vid_stop_btn = ctk.CTkButton(vid_ctrl, text="\u25A0", width=40, height=30,
                                            font=("Segoe UI", 14),
                                            fg_color="#2a2a4a", hover_color="#3a3a5a",
                                            corner_radius=8, command=self._stop_video)
        self._vid_stop_btn.pack(side="left", padx=2)

        self._vid_time_label = ctk.CTkLabel(vid_ctrl, text="0:00 / 0:00",
                                             font=("Segoe UI", 11), text_color=DIM)
        self._vid_time_label.pack(side="left", padx=8)

        self._vid_open_btn = ctk.CTkButton(vid_ctrl, text="Abrir en reproductor",
                                            width=140, height=30,
                                            font=("Segoe UI", 10),
                                            fg_color="#2a2a4a", hover_color="#3a3a5a",
                                            text_color=GOLD, corner_radius=8,
                                            command=self._open_external)
        self._vid_open_btn.pack(side="right", padx=4)

        self._vid_slider = ctk.CTkSlider(tab_video, from_=0, to=100,
                                          fg_color=INPUT_BG, progress_color=GREEN,
                                          button_color=GOLD, button_hover_color=ACCENT_H,
                                          command=self._on_vid_seek)
        self._vid_slider.pack(fill="x", pady=(2, 0))
        self._vid_slider.set(0)

        # Placeholder message
        self._vid_placeholder = ctk.CTkLabel(tab_video, text="Genera un video para verlo aqui",
                                              font=("Segoe UI", 12), text_color=DIM)
        self._vid_placeholder.place(relx=0.5, rely=0.4, anchor="center")

        # ── Reproductor de audio (below tabs) ──
        player = ctk.CTkFrame(self, fg_color=DARK, corner_radius=0)
        player.pack(fill="x", padx=4)

        # Controles: Play/Stop + tiempo
        ctrl = ctk.CTkFrame(player, fg_color="transparent")
        ctrl.pack(fill="x")

        self._play_btn = ctk.CTkButton(ctrl, text="\u25B6", width=36, height=28,
                                        font=("Segoe UI", 14),
                                        fg_color=ACCENT, hover_color=ACCENT_H,
                                        corner_radius=8, command=self._toggle_audio_play)
        self._play_btn.pack(side="left", padx=(0, 4))

        self._stop_btn = ctk.CTkButton(ctrl, text="\u25A0", width=36, height=28,
                                        font=("Segoe UI", 14),
                                        fg_color="#2a2a4a", hover_color="#3a3a5a",
                                        corner_radius=8, command=self._stop_audio_playback)
        self._stop_btn.pack(side="left", padx=(0, 8))

        self.time_label = ctk.CTkLabel(ctrl, text="0:00",
                                       font=("Segoe UI Black", 14), text_color=GOLD)
        self.time_label.pack(side="left")
        self.dur_label = ctk.CTkLabel(ctrl, text="/ 0:00",
                                      font=("Segoe UI", 12), text_color=DIM)
        self.dur_label.pack(side="left", padx=(4, 0))

        # Timeline slider — visible solo en modo Completo
        self._tl_frame = ctk.CTkFrame(player, fg_color="transparent")
        self._tl_frame.pack(fill="x")
        self.timeline = ctk.CTkSlider(self._tl_frame, from_=0, to=300,
                                      variable=preview_time,
                                      fg_color=INPUT_BG, progress_color=ACCENT,
                                      button_color=GOLD, button_hover_color=ACCENT_H,
                                      command=on_time_change)
        self.timeline.pack(fill="x", pady=(2, 4))
        self.timeline.bind("<ButtonRelease-1>", lambda e: self.stop_audio())

        # ── Rango Desde/Hasta (slider doble) ──
        self.range_frame = ctk.CTkFrame(player, fg_color="transparent")

        self.start_var = tk.DoubleVar(value=0)
        self.end_var = tk.DoubleVar(value=30)

        range_row = ctk.CTkFrame(self.range_frame, fg_color="transparent")
        range_row.pack(fill="x")
        self.range_label = ctk.CTkLabel(range_row, text="0:00 → 0:30",
                                         font=("Segoe UI", 9), text_color=GOLD)
        self.range_label.pack(side="left")

        self._range_canvas = tk.Canvas(self.range_frame, height=24,
                                        bg="#1a1a2e", highlightthickness=0)
        self._range_canvas.pack(fill="x", padx=4, pady=(2, 2))
        self._range_max = 300
        self._dragging = None  # "start", "end", or None
        self._range_canvas.bind("<ButtonPress-1>", self._range_press)
        self._range_canvas.bind("<B1-Motion>", self._range_drag)
        self._range_canvas.bind("<ButtonRelease-1>", self._range_release)
        self._range_canvas.bind("<Configure>", lambda e: self._draw_range())

        # State del reproductor
        self._on_time_change = on_time_change
        self._playback_active = False
        self._playback_after_id = None

        # Info bar
        self.info_label = ctk.CTkLabel(self, text=t("preview.select_audio"),
                                       font=("Segoe UI", 10), text_color=DIM,
                                       fg_color=CARD, corner_radius=8, height=30)
        self.info_label.pack(fill="x", padx=4, pady=(0, 2))

    # ── Video Player ──

    def load_video(self, video_path):
        """Carga un video generado para reproducir en el tab Video."""
        if not video_path or not os.path.isfile(video_path):
            return

        try:
            import cv2
        except ImportError:
            self._vid_placeholder.configure(text="pip install opencv-python para ver videos")
            return

        self._stop_video()
        self._video_path = video_path
        self._video_cap = cv2.VideoCapture(video_path)

        if not self._video_cap.isOpened():
            self._vid_placeholder.configure(text="No se pudo abrir el video")
            return

        self._video_fps = self._video_cap.get(cv2.CAP_PROP_FPS) or 30
        self._video_total_frames = int(self._video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._video_current_frame = 0

        self._vid_slider.configure(to=max(1, self._video_total_frames - 1))
        self._vid_slider.set(0)

        total_secs = self._video_total_frames / self._video_fps
        self._vid_time_label.configure(
            text=f"0:00 / {int(total_secs)//60}:{int(total_secs)%60:02d}")

        # Mostrar primer frame
        self._show_video_frame(0)
        self._vid_placeholder.place_forget()

        # Cambiar al tab Video
        self._tabs.set("Video")

    def _show_video_frame(self, frame_idx):
        """Muestra un frame específico del video en el canvas."""
        import cv2
        from PIL import Image, ImageTk

        if not self._video_cap or not self._video_cap.isOpened():
            return

        self._video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._video_cap.read()
        if not ret:
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)

        # Fit to canvas
        canvas = self.video_canvas
        self.update_idletasks()
        cw = max(canvas.winfo_width(), 200)
        ch = max(canvas.winfo_height(), 200)
        ratio = min(cw / img.width, ch / img.height)
        nw, nh = max(1, int(img.width * ratio)), max(1, int(img.height * ratio))
        img = img.resize((nw, nh), Image.LANCZOS)

        self._video_photo = ImageTk.PhotoImage(img)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=self._video_photo, anchor="center")

        # Update time label
        self._video_current_frame = frame_idx
        secs = frame_idx / self._video_fps
        total_secs = self._video_total_frames / self._video_fps
        self._vid_time_label.configure(
            text=f"{int(secs)//60}:{int(secs)%60:02d} / "
                 f"{int(total_secs)//60}:{int(total_secs)%60:02d}")

    def _toggle_play(self):
        """Play/Pause toggle."""
        if self._video_playing:
            self._video_playing = False
            self._vid_play_btn.configure(text="\u25B6")
        else:
            if not self._video_cap:
                return
            self._video_playing = True
            self._vid_play_btn.configure(text="\u275A\u275A")
            self._play_loop()

    def _play_loop(self):
        """Loop de reproducción frame a frame."""
        if not self._video_playing or not self._video_cap:
            return

        import cv2
        from PIL import Image, ImageTk

        ret, frame = self._video_cap.read()
        if not ret:
            # Fin del video
            self._video_playing = False
            self._vid_play_btn.configure(text="\u25B6")
            self._video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._video_current_frame = 0
            self._vid_slider.set(0)
            return

        self._video_current_frame = int(self._video_cap.get(cv2.CAP_PROP_POS_FRAMES))

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)

        canvas = self.video_canvas
        cw = max(canvas.winfo_width(), 200)
        ch = max(canvas.winfo_height(), 200)
        ratio = min(cw / img.width, ch / img.height)
        nw, nh = max(1, int(img.width * ratio)), max(1, int(img.height * ratio))
        img = img.resize((nw, nh), Image.LANCZOS)

        self._video_photo = ImageTk.PhotoImage(img)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=self._video_photo, anchor="center")

        # Update slider and time
        self._vid_slider.set(self._video_current_frame)
        secs = self._video_current_frame / self._video_fps
        total_secs = self._video_total_frames / self._video_fps
        self._vid_time_label.configure(
            text=f"{int(secs)//60}:{int(secs)%60:02d} / "
                 f"{int(total_secs)//60}:{int(total_secs)%60:02d}")

        # Schedule next frame
        delay = max(1, int(1000 / self._video_fps))
        self.after(delay, self._play_loop)

    def _stop_video(self):
        """Para la reproducción y vuelve al inicio."""
        self._video_playing = False
        self._vid_play_btn.configure(text="\u25B6")
        if self._video_cap:
            import cv2
            self._video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._video_current_frame = 0
            self._vid_slider.set(0)
            self._show_video_frame(0)

    def _on_vid_seek(self, val):
        """Seek manual con el slider."""
        if self._video_cap and not self._video_playing:
            self._show_video_frame(int(val))

    def _open_external(self):
        """Abre el video en el reproductor del sistema."""
        if self._video_path and os.path.isfile(self._video_path):
            os.startfile(self._video_path)

    # ── Range slider doble ──

    def _fmt_time(self, secs):
        m, s = divmod(int(secs), 60)
        return f"{m}:{s:02d}"

    def _val_to_x(self, val):
        w = self._range_canvas.winfo_width() - 20  # 10px padding each side
        return 10 + (val / max(self._range_max, 1)) * w

    def _x_to_val(self, x):
        w = self._range_canvas.winfo_width() - 20
        return max(0, min(self._range_max, ((x - 10) / max(w, 1)) * self._range_max))

    def _draw_range(self):
        c = self._range_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            return

        start = self.start_var.get()
        end = self.end_var.get()
        x1 = self._val_to_x(start)
        x2 = self._val_to_x(end)

        # Track background
        c.create_rectangle(10, h // 2 - 3, w - 10, h // 2 + 3,
                           fill="#2a2a4a", outline="")
        # Selected range (highlighted)
        c.create_rectangle(x1, h // 2 - 3, x2, h // 2 + 3,
                           fill="#e94560", outline="")
        # Start handle (green)
        c.create_oval(x1 - 7, h // 2 - 7, x1 + 7, h // 2 + 7,
                      fill="#00cc66", outline="#008844", width=1, tags="start")
        # End handle (red)
        c.create_oval(x2 - 7, h // 2 - 7, x2 + 7, h // 2 + 7,
                      fill="#e94560", outline="#b8354a", width=1, tags="end")

        # Update label
        self.range_label.configure(
            text=f"{self._fmt_time(start)} → {self._fmt_time(end)}")

    def _range_press(self, event):
        start_x = self._val_to_x(self.start_var.get())
        end_x = self._val_to_x(self.end_var.get())
        # Which handle is closer?
        d_start = abs(event.x - start_x)
        d_end = abs(event.x - end_x)
        if d_start <= d_end:
            self._dragging = "start"
        else:
            self._dragging = "end"
        self._range_drag(event)

    def _range_drag(self, event):
        val = self._x_to_val(event.x)
        if self._dragging == "start":
            val = min(val, self.end_var.get() - 1)
            self.start_var.set(max(0, val))
        elif self._dragging == "end":
            val = max(val, self.start_var.get() + 1)
            self.end_var.set(min(self._range_max, val))
        self._draw_range()

    def _range_release(self, event):
        self._dragging = None

    def show_range(self, dur_secs, audio_dur):
        """Muestra el range slider y oculta el timeline normal."""
        audio_dur = max(audio_dur, 10)
        self._range_max = audio_dur
        if self.end_var.get() <= 0 or self.end_var.get() > audio_dur:
            self.end_var.set(min(dur_secs, audio_dur))
        if self.start_var.get() >= self.end_var.get():
            self.start_var.set(0)
        self._tl_frame.pack_forget()
        self.range_frame.pack(fill="x", pady=(0, 2))
        self.after(50, self._draw_range)

    def hide_range(self):
        """Oculta el range slider y muestra el timeline normal."""
        self.start_var.set(0)
        self.end_var.set(0)
        self.range_frame.pack_forget()
        self._tl_frame.pack(fill="x")

    def get_range(self):
        """Retorna (inicio, fin) en segundos, o (0, 0) si es Completo."""
        if not self.range_frame.winfo_ismapped():
            return 0, 0
        return self.start_var.get(), self.end_var.get()

    # ── Audio playback ──

    def set_audio(self, audio_path):
        """Configura el audio para reproducción."""
        self._stop_audio_playback()
        self._audio_path = audio_path

    def play_audio_at(self, position_secs):
        """Reproduce un snippet de audio desde la posición (para scrub del slider)."""
        if not self._audio_path or not os.path.isfile(self._audio_path):
            return
        if self._playback_active:
            return  # No interrumpir reproducción continua
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)

            if not self._audio_playing:
                pygame.mixer.music.load(self._audio_path)

            pygame.mixer.music.play(start=max(0, position_secs))
            self._audio_playing = True

            # Auto-stop en 1.5s
            if hasattr(self, '_audio_stop_id') and self._audio_stop_id:
                self.after_cancel(self._audio_stop_id)
            self._audio_stop_id = self.after(1500, self.stop_audio)
        except Exception as e:
            print(f"[DVS] Audio error: {e}")

    def stop_audio(self):
        """Detiene audio sin afectar estado de playback."""
        if self._audio_playing:
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                pass
            self._audio_playing = False

    def _toggle_audio_play(self):
        """Play/Pause del reproductor con sincronización de preview."""
        if self._playback_active:
            # Pause
            self._playback_active = False
            self._play_btn.configure(text="\u25B6")
            if self._playback_after_id:
                self.after_cancel(self._playback_after_id)
                self._playback_after_id = None
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.pause()
            except Exception:
                pass
            return

        if not self._audio_path or not os.path.isfile(self._audio_path):
            return

        # Determinar rango de reproducción
        start, end = self.get_range()
        if end <= start:
            # Completo: usar posición actual del slider
            start = self._preview_time.get()
            end = self.timeline.cget("to")

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.music.load(self._audio_path)
            pygame.mixer.music.play(start=max(0, start))
            self._audio_playing = True
        except Exception as e:
            print(f"[DVS] Audio play error: {e}")
            return

        self._playback_active = True
        self._playback_start = start
        self._playback_end = end
        self._playback_t0 = start
        self._play_btn.configure(text="\u275A\u275A")

        import time as _time
        self._playback_wall_t0 = _time.time()

        # Iniciar loop de sync
        self._playback_tick()

    def _playback_tick(self):
        """Actualiza slider + preview ~20 fps mientras reproduce."""
        if not self._playback_active:
            return

        import time as _time
        elapsed = _time.time() - self._playback_wall_t0
        current = self._playback_t0 + elapsed

        if current >= self._playback_end:
            self._stop_audio_playback()
            return

        # Actualizar slider/tiempo
        self._preview_time.set(current)
        m, s = divmod(int(current), 60)
        self.time_label.configure(text=f"{m}:{s:02d}")

        # Actualizar preview (trigger callback del app)
        if self._on_time_change:
            self._on_time_change(current)

        # Siguiente tick (~20fps = 50ms)
        self._playback_after_id = self.after(50, self._playback_tick)

    def _stop_audio_playback(self):
        """Para completamente la reproducción."""
        self._playback_active = False
        self._play_btn.configure(text="\u25B6")
        if self._playback_after_id:
            self.after_cancel(self._playback_after_id)
            self._playback_after_id = None
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._audio_playing = False

    # ── Drag letras en preview ──

    def _lyrics_drag_start(self, event):
        """Guarda posición Y inicial del drag."""
        self._drag_start_y = event.y

    def _lyrics_drag_move(self, event):
        """Mientras se arrastra, notifica el delta acumulado."""
        if self._drag_start_y is None or self._on_lyrics_drag is None:
            return
        dy = event.y - self._drag_start_y
        self._drag_start_y = event.y  # delta incremental (no total)
        self._on_lyrics_drag(dy)

    def _lyrics_drag_end(self, event):
        """Fin del drag."""
        self._drag_start_y = None

    def switch_to_preview(self):
        """Cambia al tab Preview y pausa video si está reproduciéndose."""
        if self._video_playing:
            self._video_playing = False
            self._vid_play_btn.configure(text="\u25B6")
        self._tabs.set("Preview")
