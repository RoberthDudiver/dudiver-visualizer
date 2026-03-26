"""Panel de spot publicitario."""

import os
import customtkinter as ctk
from tkinter import filedialog

from app.config import ACCENT, ACCENT_H, GOLD, DIM, CARD, INPUT_BG
from app.i18n import t
from app.ui.components import create_section, short_path


class SpotPanel(ctk.CTkFrame):
    def __init__(self, parent, *, spot_enabled, spot_type, spot_file,
                 spot_text, spot_subtext, spot_duration, all_inputs):
        super().__init__(parent, fg_color="transparent", corner_radius=0)

        self._spot_enabled = spot_enabled
        self._spot_type = spot_type
        self._spot_file = spot_file

        create_section(self, t("spot.title"))
        spot = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        spot.pack(fill="x", padx=4, pady=(0, 4))

        spot_enable = ctk.CTkSwitch(spot, text=t("spot.enable"),
                                    variable=spot_enabled,
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
        ctk.CTkLabel(sf1, text=t("spot.type"), font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        self.spot_type_menu = ctk.CTkSegmentedButton(
            sf1, values=["Texto", "Imagen", "Video"],
            variable=spot_type, font=("Segoe UI", 10),
            fg_color=INPUT_BG, selected_color=ACCENT,
            selected_hover_color=ACCENT_H,
            command=self._on_spot_type_change)
        self.spot_type_menu.pack(side="left", fill="x", expand=True, padx=4)

        # Texto spot
        self.spot_text_frame = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        self.spot_text_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(self.spot_text_frame, text=t("spot.line1"), font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        ctk.CTkEntry(self.spot_text_frame, textvariable=spot_text,
                     font=("Segoe UI", 11), fg_color=INPUT_BG,
                     corner_radius=6, height=30).pack(side="left", fill="x", expand=True, padx=4)

        sf_sub = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        sf_sub.pack(fill="x", pady=2)
        ctk.CTkLabel(sf_sub, text=t("spot.line2"), font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        ctk.CTkEntry(sf_sub, textvariable=spot_subtext,
                     font=("Segoe UI", 11), fg_color=INPUT_BG,
                     corner_radius=6, height=30).pack(side="left", fill="x", expand=True, padx=4)

        # Archivo spot (imagen/video)
        self.spot_file_frame = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        # No pack yet — shown when tipo=Imagen or Video

        sf_file = ctk.CTkFrame(self.spot_file_frame, fg_color="transparent")
        sf_file.pack(fill="x", pady=2)
        ctk.CTkLabel(sf_file, text=t("spot.file"), font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        self.spot_file_label = ctk.CTkLabel(sf_file, text=t("spot.none"),
                                            font=("Segoe UI", 10), text_color=GOLD)
        self.spot_file_label.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(sf_file, text="...", width=32, height=28,
                      fg_color=INPUT_BG, hover_color=ACCENT,
                      command=self._pick_spot_file).pack(side="right")

        # Duracion spot
        sf_dur = ctk.CTkFrame(self.spot_frame, fg_color="transparent")
        sf_dur.pack(fill="x", pady=2)
        ctk.CTkLabel(sf_dur, text=t("spot.duration"), font=("Segoe UI", 10),
                     text_color=DIM, width=60).pack(side="left")
        ctk.CTkSegmentedButton(sf_dur, values=["3 seg", "5 seg", "8 seg", "10 seg"],
                               variable=spot_duration, font=("Segoe UI", 10),
                               fg_color=INPUT_BG, selected_color=ACCENT,
                               selected_hover_color=ACCENT_H).pack(side="left", fill="x",
                                                                     expand=True, padx=4)

        # Initially hidden
        self.spot_frame.pack_forget()

    def _toggle_spot(self):
        if self._spot_enabled.get():
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
        if self._spot_type.get() == "Imagen":
            ft = [(t("spot.images"), "*.jpg *.png *.bmp"), (t("spot.all"), "*.*")]
        else:
            ft = [("Video", "*.mp4 *.mov *.avi"), (t("spot.all"), "*.*")]
        p = filedialog.askopenfilename(title=t("spot.select_file"), filetypes=ft)
        if p:
            self._spot_file.set(p)
            self.spot_file_label.configure(text=short_path(p))
