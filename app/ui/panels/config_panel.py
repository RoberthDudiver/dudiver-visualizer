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
                 lyrics_pos_var=None, lyrics_align_var=None, lyrics_margin_var=None,
                 chk_text_box=None, text_box_opacity_var=None,
                 text_box_radius_var=None, chk_dim_bg=None,
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

        # Fuente — combo estilo Office con cada fuente en su propia tipografía
        from app.ui.font_picker import FontComboBox
        font_row = ctk.CTkFrame(modo_card, fg_color="transparent")
        font_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(font_row, text=t("config.font"), font=("Segoe UI", 9),
                     text_color=DIM, width=50, anchor="w").pack(side="left")
        self._fuente_var = fuente_var
        font_combo = FontComboBox(font_row, fuente_var, all_inputs)
        font_combo.pack(side="right", fill="x", expand=True)

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

        # ── RECUADRO TEXTO ──
        if chk_text_box is not None:
            create_section(self, "Recuadro Texto")
            box_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
            box_card.pack(fill="x", padx=4, pady=(0, 4))

            # Fila 1: checkbox activar + checkbox dim video
            row1 = ctk.CTkFrame(box_card, fg_color="transparent")
            row1.pack(fill="x", padx=8, pady=(6, 2))
            cb_box = ctk.CTkCheckBox(row1, text="Activar recuadro",
                                     variable=chk_text_box,
                                     font=("Segoe UI", 10), fg_color=ACCENT,
                                     hover_color=ACCENT_H, corner_radius=4,
                                     checkbox_width=18, checkbox_height=18)
            cb_box.pack(side="left")
            all_inputs.append(cb_box)

            if chk_dim_bg is not None:
                cb_dim = ctk.CTkCheckBox(row1, text="Oscurecer fondo",
                                         variable=chk_dim_bg,
                                         font=("Segoe UI", 10), fg_color=ACCENT,
                                         hover_color=ACCENT_H, corner_radius=4,
                                         checkbox_width=18, checkbox_height=18)
                cb_dim.pack(side="right")
                all_inputs.append(cb_dim)

            # Slider opacidad
            if text_box_opacity_var is not None:
                op_cell = ctk.CTkFrame(box_card, fg_color="transparent")
                op_cell.pack(fill="x", padx=8, pady=(2, 2))
                self._op_label = ctk.CTkLabel(op_cell,
                                              text=f"Opacidad: {text_box_opacity_var.get()}%",
                                              font=("Segoe UI", 9), text_color=DIM, anchor="w")
                self._op_label.pack(anchor="w")
                op_slider = ctk.CTkSlider(op_cell, from_=0, to=100,
                                          variable=text_box_opacity_var,
                                          fg_color=INPUT_BG, progress_color=ACCENT,
                                          button_color=GOLD, button_hover_color=ACCENT_H,
                                          height=14,
                                          command=lambda v: self._op_label.configure(
                                              text=f"Opacidad: {int(v)}%"))
                op_slider.pack(fill="x")
                all_inputs.append(op_slider)

            # Slider radio esquinas
            if text_box_radius_var is not None:
                rd_cell = ctk.CTkFrame(box_card, fg_color="transparent")
                rd_cell.pack(fill="x", padx=8, pady=(2, 6))
                self._rd_label = ctk.CTkLabel(rd_cell,
                                              text=f"Redondeo: {text_box_radius_var.get()} px",
                                              font=("Segoe UI", 9), text_color=DIM, anchor="w")
                self._rd_label.pack(anchor="w")
                rd_slider = ctk.CTkSlider(rd_cell, from_=0, to=40,
                                          variable=text_box_radius_var,
                                          fg_color=INPUT_BG, progress_color=ACCENT,
                                          button_color=GOLD, button_hover_color=ACCENT_H,
                                          height=14,
                                          command=lambda v: self._rd_label.configure(
                                              text=f"Redondeo: {int(v)} px"))
                rd_slider.pack(fill="x")
                all_inputs.append(rd_slider)

        # ── POSICIÓN LETRA ──
        if lyrics_pos_var is not None and lyrics_margin_var is not None:
            create_section(self, "Posición Letra")
            pos_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
            pos_card.pack(fill="x", padx=4, pady=(0, 4))

            # Fila: dropdown vertical (Arriba / Centro / Abajo)
            pos_row = ctk.CTkFrame(pos_card, fg_color="transparent")
            pos_row.pack(fill="x", padx=8, pady=(6, 2))
            ctk.CTkLabel(pos_row, text="Vertical", font=("Segoe UI", 9),
                         text_color=DIM, width=50, anchor="w").pack(side="left")
            pos_dd = ctk.CTkOptionMenu(pos_row, variable=lyrics_pos_var,
                                       values=["Arriba", "Centro", "Abajo"],
                                       font=("Segoe UI", 10), fg_color=INPUT_BG,
                                       button_color="#2a2a4a", button_hover_color=ACCENT,
                                       dropdown_fg_color=CARD, dropdown_hover_color=ACCENT,
                                       corner_radius=6, height=26)
            pos_dd.pack(side="right", fill="x", expand=True)
            all_inputs.append(pos_dd)

            # Fila: dropdown horizontal (Izquierda / Centro / Derecha)
            if lyrics_align_var is not None:
                align_row = ctk.CTkFrame(pos_card, fg_color="transparent")
                align_row.pack(fill="x", padx=8, pady=(0, 2))
                ctk.CTkLabel(align_row, text="Alinear", font=("Segoe UI", 9),
                             text_color=DIM, width=50, anchor="w").pack(side="left")
                align_dd = ctk.CTkOptionMenu(align_row, variable=lyrics_align_var,
                                             values=["Izquierda", "Centro", "Derecha"],
                                             font=("Segoe UI", 10), fg_color=INPUT_BG,
                                             button_color="#2a2a4a", button_hover_color=ACCENT,
                                             dropdown_fg_color=CARD, dropdown_hover_color=ACCENT,
                                             corner_radius=6, height=26)
                align_dd.pack(side="right", fill="x", expand=True)
                all_inputs.append(align_dd)

            # Fila: slider margen
            mg_cell = ctk.CTkFrame(pos_card, fg_color="transparent")
            mg_cell.pack(fill="x", padx=8, pady=(2, 6))
            self._mg_label = ctk.CTkLabel(mg_cell,
                                          text=f"Margen: {lyrics_margin_var.get()} px",
                                          font=("Segoe UI", 9), text_color=DIM, anchor="w")
            self._mg_label.pack(anchor="w")
            mg_slider = ctk.CTkSlider(mg_cell, from_=0, to=200,
                                      variable=lyrics_margin_var,
                                      fg_color=INPUT_BG, progress_color=ACCENT,
                                      button_color=GOLD, button_hover_color=ACCENT_H,
                                      height=14,
                                      command=lambda v: self._mg_label.configure(
                                          text=f"Margen: {int(v)} px"))
            mg_slider.pack(fill="x")
            all_inputs.append(mg_slider)

            # Hint drag
            ctk.CTkLabel(pos_card, text="Arrastra las letras en la preview",
                         font=("Segoe UI", 8), text_color=DIM,
                         fg_color="transparent").pack(pady=(0, 4))

        # Init visibility
        self._update_mode(modo_var.get())

    def _update_mode(self, modo):
        if modo == "Kinetic Typography":
            self.kinetic_frame.pack(fill="x", padx=8, pady=(0, 2))
        else:
            self.kinetic_frame.pack_forget()
        # Efectos siempre visibles (aplican a Karaoke, informativo en Kinetic)
        self.karaoke_efx_frame.pack(fill="x")
