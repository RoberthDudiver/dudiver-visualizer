"""Panel de preview (col 2): tabs Preview/Video, canvas, timeline, reproductor."""

import os
import threading
import tkinter as tk
import customtkinter as ctk

from app.config import ACCENT, ACCENT_H, GOLD, GREEN, DIM, CARD, INPUT_BG, DARK
from app.i18n import t
from app.ui.components import create_section


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, parent, *, preview_time, on_time_change):
        super().__init__(parent, fg_color=DARK, corner_radius=0)

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

        self.preview_canvas = tk.Canvas(pv_outer, bg="#080810", highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True, padx=4, pady=4)

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

        # ── Timeline (shared, below tabs) ──
        tl = ctk.CTkFrame(self, fg_color=DARK, corner_radius=0)
        tl.pack(fill="x", padx=4)

        tl_info = ctk.CTkFrame(tl, fg_color="transparent")
        tl_info.pack(fill="x")
        self.time_label = ctk.CTkLabel(tl_info, text="0:00",
                                       font=("Segoe UI Black", 14), text_color=GOLD)
        self.time_label.pack(side="left")
        self.dur_label = ctk.CTkLabel(tl_info, text="/ 0:00",
                                      font=("Segoe UI", 12), text_color=DIM)
        self.dur_label.pack(side="left", padx=(4, 0))

        self.timeline = ctk.CTkSlider(tl, from_=0, to=300, variable=preview_time,
                                      fg_color=INPUT_BG, progress_color=ACCENT,
                                      button_color=GOLD, button_hover_color=ACCENT_H,
                                      command=on_time_change)
        self.timeline.pack(fill="x", pady=(2, 4))

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
