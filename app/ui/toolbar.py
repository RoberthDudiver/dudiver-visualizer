"""Toolbar: header con botones, progress bar, status label."""

import os
import customtkinter as ctk
from PIL import Image

from app.config import ACCENT, ACCENT_H, GOLD, GREEN, DIM, INPUT_BG, DARK


class Toolbar(ctk.CTkFrame):
    def __init__(self, parent, *, on_timestamps, on_preview, on_generate,
                 on_cancel, on_open_folder, on_settings, on_about,
                 all_inputs):
        super().__init__(parent, fg_color=DARK, height=56, corner_radius=0)
        self.pack_propagate(False)

        # Logo icon al lado del nombre
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        png = os.path.join(base_dir, "icon.png")
        if os.path.exists(png):
            logo_img = ctk.CTkImage(Image.open(png), size=(36, 36))
            ctk.CTkLabel(self, image=logo_img, text="").pack(side="left", padx=(12, 4))

        ctk.CTkLabel(self, text="DUDIVER", font=("Segoe UI Black", 20),
                     text_color=ACCENT).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(self, text="VISUALIZER", font=("Segoe UI Light", 20),
                     text_color="white").pack(side="left", padx=(6, 0))

        # Separator
        ctk.CTkFrame(self, fg_color="#2a2a4a", width=2, height=30,
                     corner_radius=0).pack(side="left", padx=12)

        # Toolbar buttons
        ts_btn = ctk.CTkButton(self, text="\u27f3 Timestamps", height=34, width=130,
                               font=("Segoe UI Semibold", 11),
                               fg_color="#2a2a4a", hover_color="#3a3a5a",
                               corner_radius=8, command=on_timestamps)
        ts_btn.pack(side="left", padx=3)
        all_inputs.append(ts_btn)

        pv_btn = ctk.CTkButton(self, text="\U0001f441 Preview", height=34, width=110,
                               font=("Segoe UI Semibold", 11),
                               fg_color="#2a2a4a", hover_color="#3a3a5a",
                               text_color=GOLD, corner_radius=8,
                               command=on_preview)
        pv_btn.pack(side="left", padx=3)
        all_inputs.append(pv_btn)

        # GENERAR button
        self.gen_btn = ctk.CTkButton(self, text="\u25b6  GENERAR VIDEO", height=38, width=200,
                                     font=("Segoe UI Black", 13),
                                     fg_color=ACCENT, hover_color=ACCENT_H,
                                     corner_radius=10, command=on_generate)
        self.gen_btn.pack(side="left", padx=(8, 3))
        all_inputs.append(self.gen_btn)

        self.cancel_btn = ctk.CTkButton(self, text="\u2715", height=34, width=40,
                                        font=("Segoe UI Bold", 13),
                                        fg_color="#2a2a4a", hover_color=ACCENT,
                                        text_color=DIM, corner_radius=8,
                                        state="disabled", command=on_cancel)
        self.cancel_btn.pack(side="left", padx=3)

        # Separator
        ctk.CTkFrame(self, fg_color="#2a2a4a", width=2, height=30,
                     corner_radius=0).pack(side="left", padx=8)

        # Progress in toolbar
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
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

        self.status_label = ctk.CTkLabel(prog_col, text="\u2713 Listo",
                                         font=("Segoe UI", 9), text_color=DIM,
                                         anchor="w", height=14)
        self.status_label.pack(fill="x")

        # Right side buttons
        ctk.CTkButton(self, text="?", height=34, width=34,
                      font=("Segoe UI Bold", 13), fg_color="#2a2a4a",
                      hover_color="#3a3a5a", text_color=GOLD, corner_radius=8,
                      command=on_about).pack(side="right", padx=(3, 12))
        ctk.CTkButton(self, text="\u2699", height=34, width=34,
                      font=("Segoe UI", 16), fg_color="#2a2a4a",
                      hover_color="#3a3a5a", text_color=DIM, corner_radius=8,
                      command=on_settings).pack(side="right", padx=3)
        ctk.CTkButton(self, text="\U0001f4c2", height=34, width=40,
                      font=("Segoe UI", 14), fg_color="#2a2a4a",
                      hover_color="#3a3a5a", corner_radius=8,
                      command=on_open_folder).pack(side="right", padx=3)

    def set_status(self, msg, pct=None):
        """Actualiza barra de progreso y status label."""
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

    def set_generating(self):
        """Desactiva el boton generar, activa cancel."""
        self.cancel_btn.configure(state="normal", text_color=ACCENT)
        self.gen_btn.configure(text="\u27f3  GENERANDO...", fg_color="#3a3a5a",
                              state="disabled")

    def set_idle(self):
        """Restaura boton generar, desactiva cancel."""
        self.cancel_btn.configure(state="disabled", text_color=DIM)
        self.gen_btn.configure(text="\u25b6  GENERAR VIDEO", fg_color=ACCENT,
                              state="normal")
