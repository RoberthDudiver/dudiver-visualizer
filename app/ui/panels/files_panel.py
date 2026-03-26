"""Panel de archivos (col 0): audio, letra, fondo, titulo, alpha, textbox."""

import customtkinter as ctk

from app.config import ACCENT, ACCENT_H, GOLD, DIM, CARD, INPUT_BG, DARK
from app.ui.components import create_section, create_file_row


class FilesPanel(ctk.CTkFrame):
    def __init__(self, parent, *, audio_path, letra_path, fondo_path,
                 titulo_var, alpha_var, all_inputs):
        super().__init__(parent, fg_color=DARK, corner_radius=0)

        create_section(self, "\U0001f3b5  ARCHIVOS")
        create_file_row(self, "Cancion", audio_path,
                        [("Audio", "*.mp3 *.wav *.flac *.ogg")], all_inputs)
        create_file_row(self, "Letra", letra_path,
                        [("Texto", "*.txt *.md")], all_inputs)
        create_file_row(self, "Fondo", fondo_path,
                        [("Media", "*.jpg *.png *.mp4 *.mov")], all_inputs)

        alpha_cb = ctk.CTkCheckBox(self, text="Transparente (alpha/WebM)",
                                   variable=alpha_var, font=("Segoe UI", 11),
                                   fg_color=ACCENT, hover_color=ACCENT_H)
        alpha_cb.pack(fill="x", padx=8, pady=(2, 6))
        all_inputs.append(alpha_cb)

        create_section(self, "\u270f\ufe0f  TITULO")
        te = ctk.CTkEntry(self, textvariable=titulo_var, height=36,
                          font=("Segoe UI", 12), fg_color=INPUT_BG,
                          border_color=DIM, corner_radius=8)
        te.pack(fill="x", padx=8, pady=(0, 6))
        all_inputs.append(te)

        create_section(self, "\U0001f4dd  LETRA (o pega aqui)")
        self.letra_text = ctk.CTkTextbox(self, font=("Consolas", 10),
                                         fg_color=INPUT_BG, border_color=DIM,
                                         corner_radius=8, border_width=1)
        self.letra_text.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        all_inputs.append(self.letra_text)
