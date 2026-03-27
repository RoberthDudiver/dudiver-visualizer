"""Panel de configuracion: modo, video (compacto 2 col), efectos."""

import customtkinter as ctk

from app.config import (
    ACCENT, ACCENT_H, GOLD, DIM, CARD, INPUT_BG, DARK,
    TAMANOS, ESQUEMAS_GUI, DURACIONES, WHISPER_MODELS,
    MODOS_VIDEO, ESTILOS_KINETIC, ESQUEMAS_KINETIC_GUI,
)
from app.i18n import t
from app.ui.components import create_section


def _list_system_fonts():
    fonts = []
    try:
        import manimpango
        fonts = sorted(set(manimpango.list_fonts()))
    except ImportError:
        pass
    if not fonts:
        fonts = ["Arial", "Impact", "Segoe UI", "Roboto", "Calibri",
                 "Consolas", "Georgia", "Tahoma", "Verdana", "Comic Sans MS"]
    return fonts


def _mini_dropdown(parent, label, var, values, all_inputs, row, col):
    """Dropdown compacto para grid layout."""
    cell = ctk.CTkFrame(parent, fg_color="transparent")
    cell.grid(row=row, column=col, sticky="ew", padx=3, pady=2)
    ctk.CTkLabel(cell, text=label, font=("Segoe UI", 9),
                 text_color=DIM, anchor="w").pack(anchor="w")
    dd = ctk.CTkOptionMenu(cell, variable=var, values=values,
                           font=("Segoe UI", 10), fg_color=INPUT_BG,
                           button_color="#2a2a4a", button_hover_color=ACCENT,
                           dropdown_fg_color=CARD, dropdown_hover_color=ACCENT,
                           corner_radius=6, height=26)
    dd.pack(fill="x")
    all_inputs.append(dd)
    return dd


def _full_dropdown(parent, label, var, values, all_inputs):
    """Dropdown ancho completo."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=8, pady=2)
    ctk.CTkLabel(row, text=label, font=("Segoe UI", 9),
                 text_color=DIM, width=50, anchor="w").pack(side="left")
    dd = ctk.CTkOptionMenu(row, variable=var, values=values,
                           font=("Segoe UI", 10), fg_color=INPUT_BG,
                           button_color="#2a2a4a", button_hover_color=ACCENT,
                           dropdown_fg_color=CARD, dropdown_hover_color=ACCENT,
                           corner_radius=6, height=26)
    dd.pack(side="right", fill="x", expand=True)
    all_inputs.append(dd)
    return dd


class ConfigPanel(ctk.CTkFrame):
    def __init__(self, parent, *, tamano_var, fps_var, esquema_var,
                 whisper_var, duracion_var, font_size_var,
                 modo_var, estilo_kinetic_var, fuente_var,
                 formato_var=None,
                 chk_particulas, chk_onda, chk_vineta, chk_glow, chk_barra,
                 all_inputs):
        super().__init__(parent, fg_color=DARK, corner_radius=0)

        # ── MODO ──
        create_section(self, t("config.mode_title"))
        modo_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        modo_card.pack(fill="x", padx=4, pady=(0, 4))

        _full_dropdown(modo_card, t("config.mode"), modo_var, MODOS_VIDEO, all_inputs)

        # Kinetic sub-options
        self.kinetic_frame = ctk.CTkFrame(modo_card, fg_color="transparent")
        _full_dropdown(self.kinetic_frame, t("config.style"), estilo_kinetic_var,
                       list(ESTILOS_KINETIC.keys()), all_inputs)

        # Fuente
        fonts = _list_system_fonts()
        _full_dropdown(modo_card, t("config.font"), fuente_var, fonts, all_inputs)

        # Karaoke effects frame
        self.karaoke_efx_frame = ctk.CTkFrame(self, fg_color=DARK, corner_radius=0)

        self._modo_var = modo_var
        modo_var.trace_add("write", lambda *_: self._update_mode(modo_var.get()))

        # ── VIDEO (grid 2 columnas) ──
        create_section(self, t("config.video_title"))
        vid_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        vid_card.pack(fill="x", padx=4, pady=(0, 4))

        grid = ctk.CTkFrame(vid_card, fg_color="transparent")
        grid.pack(fill="x", padx=6, pady=4)
        grid.columnconfigure((0, 1), weight=1)

        _mini_dropdown(grid, t("config.size"), tamano_var, list(TAMANOS.keys()), all_inputs, 0, 0)
        _mini_dropdown(grid, "FPS", fps_var, ["24", "30", "60"], all_inputs, 0, 1)
        _mini_dropdown(grid, t("config.colors"), esquema_var, list(ESQUEMAS_GUI.keys()), all_inputs, 1, 0)
        _mini_dropdown(grid, t("config.ai_precision"), whisper_var,
                       list(WHISPER_MODELS.keys()), all_inputs, 1, 1)
        _mini_dropdown(grid, t("config.duration"), duracion_var, list(DURACIONES.keys()), all_inputs, 2, 0)

        if formato_var:
            _mini_dropdown(grid, "Formato", formato_var,
                           ["MP4", "WebM", "MOV (ProRes)", "AVI"],
                           all_inputs, 3, 0)

        # Font size slider en la celda derecha de row 2
        fs_cell = ctk.CTkFrame(grid, fg_color="transparent")
        fs_cell.grid(row=2, column=1, sticky="ew", padx=3, pady=2)
        self.fs_label = ctk.CTkLabel(fs_cell, text=t("config.font_px", n=font_size_var.get()),
                                     font=("Segoe UI", 9), text_color=DIM, anchor="w")
        self.fs_label.pack(anchor="w")
        fs_slider = ctk.CTkSlider(fs_cell, from_=20, to=80, variable=font_size_var,
                                  fg_color=INPUT_BG, progress_color=ACCENT,
                                  button_color=GOLD, button_hover_color=ACCENT_H,
                                  height=14,
                                  command=lambda v: self.fs_label.configure(
                                      text=t("config.font_px", n=int(v))))
        fs_slider.pack(fill="x")
        all_inputs.append(fs_slider)

        # ── EFECTOS (karaoke only) ──
        create_section(self.karaoke_efx_frame, t("config.effects_title"))
        efx = ctk.CTkFrame(self.karaoke_efx_frame, fg_color=CARD, corner_radius=10)
        efx.pack(fill="x", padx=4, pady=(0, 4))
        efx_grid = ctk.CTkFrame(efx, fg_color="transparent")
        efx_grid.pack(fill="x", padx=8, pady=4)
        efx_grid.columnconfigure((0, 1), weight=1)
        for i, (txt, var) in enumerate([
            (t("config.particles"), chk_particulas), (t("config.wave"), chk_onda),
            (t("config.vignette"), chk_vineta), ("Glow", chk_glow),
            (t("config.progress_bar"), chk_barra)
        ]):
            cb = ctk.CTkCheckBox(efx_grid, text=txt, variable=var,
                                 font=("Segoe UI", 10), fg_color=ACCENT,
                                 hover_color=ACCENT_H, corner_radius=4,
                                 checkbox_width=18, checkbox_height=18)
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=1)
            all_inputs.append(cb)

        # Init visibility
        self._update_mode(modo_var.get())

    def _update_mode(self, modo):
        if modo == "Kinetic Typography":
            self.kinetic_frame.pack(fill="x", padx=8, pady=(0, 2))
        else:
            self.kinetic_frame.pack_forget()
        # Efectos siempre visibles (aplican a Karaoke, informativo en Kinetic)
        self.karaoke_efx_frame.pack(fill="x")
