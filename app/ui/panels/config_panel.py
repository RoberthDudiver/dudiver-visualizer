"""Panel de configuracion (parte superior de col 1): dropdowns, slider, efectos."""

import customtkinter as ctk

from app.config import (
    ACCENT, ACCENT_H, GOLD, DIM, CARD, INPUT_BG, DARK,
    TAMANOS, ESQUEMAS_GUI, DURACIONES,
)
from app.ui.components import create_section, create_dropdown


class ConfigPanel(ctk.CTkFrame):
    def __init__(self, parent, *, tamano_var, fps_var, esquema_var,
                 whisper_var, duracion_var, font_size_var,
                 chk_particulas, chk_onda, chk_vineta, chk_glow, chk_barra,
                 all_inputs):
        super().__init__(parent, fg_color=DARK, corner_radius=0)

        # ── Video Config ──
        create_section(self, "\U0001f3ac  VIDEO")
        cfg = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        cfg.pack(fill="x", padx=4, pady=(0, 4))

        create_dropdown(cfg, "Tama\u00f1o", tamano_var, list(TAMANOS.keys()), all_inputs)
        create_dropdown(cfg, "FPS", fps_var, ["24", "30", "60"], all_inputs)
        create_dropdown(cfg, "Colores", esquema_var, list(ESQUEMAS_GUI.keys()), all_inputs)
        create_dropdown(cfg, "Whisper", whisper_var, ["tiny", "base", "small", "medium"], all_inputs)
        create_dropdown(cfg, "Duracion", duracion_var, list(DURACIONES.keys()), all_inputs)

        # Font slider
        fs_frame = ctk.CTkFrame(cfg, fg_color="transparent")
        fs_frame.pack(fill="x", padx=12, pady=4)
        self.fs_label = ctk.CTkLabel(fs_frame, text=f"Fuente: {font_size_var.get()}px",
                                     font=("Segoe UI", 11), text_color=DIM)
        self.fs_label.pack(anchor="w")
        fs_slider = ctk.CTkSlider(fs_frame, from_=20, to=80, variable=font_size_var,
                                  fg_color=INPUT_BG, progress_color=ACCENT,
                                  button_color=GOLD, button_hover_color=ACCENT_H,
                                  command=lambda v: self.fs_label.configure(
                                      text=f"Fuente: {int(v)}px"))
        fs_slider.pack(fill="x", pady=(0, 4))
        all_inputs.append(fs_slider)

        # Efectos
        create_section(self, "\u2728  EFECTOS")
        efx = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        efx.pack(fill="x", padx=4, pady=(0, 4))
        efx_grid = ctk.CTkFrame(efx, fg_color="transparent")
        efx_grid.pack(fill="x", padx=8, pady=6)
        efx_grid.columnconfigure((0, 1), weight=1)
        for i, (txt, var) in enumerate([
            ("Particulas", chk_particulas), ("Onda", chk_onda),
            ("Vi\u00f1eta", chk_vineta), ("Glow", chk_glow),
            ("Barra progreso", chk_barra)
        ]):
            cb = ctk.CTkCheckBox(efx_grid, text=txt, variable=var,
                                 font=("Segoe UI", 10), fg_color=ACCENT,
                                 hover_color=ACCENT_H, corner_radius=4)
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=2)
            all_inputs.append(cb)
