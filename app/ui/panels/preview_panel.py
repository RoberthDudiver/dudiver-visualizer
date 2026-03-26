"""Panel de preview (col 2): canvas, timeline, time labels."""

import tkinter as tk
import customtkinter as ctk

from app.config import ACCENT, ACCENT_H, GOLD, DIM, CARD, INPUT_BG, DARK
from app.ui.components import create_section


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, parent, *, preview_time, on_time_change):
        super().__init__(parent, fg_color=DARK, corner_radius=0)

        create_section(self, "\U0001f5bc  PREVIEW")

        # Preview frame con borde
        pv_outer = ctk.CTkFrame(self, fg_color="#080810", corner_radius=12,
                                border_width=1, border_color="#2a2a4a")
        pv_outer.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.preview_canvas = tk.Canvas(pv_outer, bg="#080810", highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Timeline
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
        self.info_label = ctk.CTkLabel(self, text="Selecciona un audio para comenzar",
                                       font=("Segoe UI", 10), text_color=DIM,
                                       fg_color=CARD, corner_radius=8, height=30)
        self.info_label.pack(fill="x", padx=4, pady=(0, 2))
