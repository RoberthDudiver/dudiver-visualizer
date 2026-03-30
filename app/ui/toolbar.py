"""Toolbar: header con botones, progress bar, status label."""

import os
import customtkinter as ctk
from PIL import Image

from app.config import ACCENT, ACCENT_H, GOLD, GREEN, DIM, INPUT_BG, DARK
from app.i18n import t


class Toolbar(ctk.CTkFrame):
    def __init__(self, parent, *, on_timestamps, on_preview, on_generate,
                 on_cancel, on_open_folder, on_settings, on_about,
                 on_sync_editor=None, on_help=None,
                 on_save_project=None, on_open_project=None,
                 on_new_project=None,
                 all_inputs):
        super().__init__(parent, fg_color=DARK, height=56, corner_radius=0)
        self.pack_propagate(False)
        self._anim_active = False

        # Logo icon al lado del nombre
        from app.utils.paths import asset_path
        png = asset_path("icon.png")
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
        ts_btn = ctk.CTkButton(self, text=t("toolbar.timestamps"), height=34, width=130,
                               font=("Segoe UI Semibold", 11),
                               fg_color="#2a2a4a", hover_color="#3a3a5a",
                               corner_radius=8, command=on_timestamps)
        ts_btn.pack(side="left", padx=3)
        all_inputs.append(ts_btn)

        if on_sync_editor:
            sync_btn = ctk.CTkButton(self, text=t("toolbar.sync"), height=34, width=80,
                                     font=("Segoe UI Semibold", 11),
                                     fg_color="#2a2a4a", hover_color="#3a3a5a",
                                     text_color="#ff9f43", corner_radius=8,
                                     command=on_sync_editor)
            sync_btn.pack(side="left", padx=3)
            all_inputs.append(sync_btn)

        pv_btn = ctk.CTkButton(self, text=t("toolbar.preview"), height=34, width=110,
                               font=("Segoe UI Semibold", 11),
                               fg_color="#2a2a4a", hover_color="#3a3a5a",
                               text_color=GOLD, corner_radius=8,
                               command=on_preview)
        pv_btn.pack(side="left", padx=3)
        all_inputs.append(pv_btn)

        # GENERAR button
        self.gen_btn = ctk.CTkButton(self, text=t("toolbar.generate"), height=38, width=200,
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

        # Right side buttons — pack BEFORE progress so expand doesn't steal space
        # Orden visual (izq→der): 📂 📾 ⚙ About ?
        if on_help:
            ctk.CTkButton(self, text="?", height=34, width=34,
                          font=("Segoe UI Bold", 13), fg_color="#2a2a4a",
                          hover_color="#3a3a5a", text_color=GOLD, corner_radius=8,
                          command=on_help).pack(side="right", padx=(3, 12))

        ctk.CTkButton(self, text="About", height=34, width=56,
                      font=("Segoe UI", 10), fg_color="#2a2a4a",
                      hover_color="#3a3a5a", text_color=DIM, corner_radius=8,
                      command=on_about).pack(side="right", padx=3)

        ctk.CTkButton(self, text="\u2699", height=34, width=34,
                      font=("Segoe UI", 16), fg_color="#2a2a4a",
                      hover_color="#3a3a5a", text_color=DIM, corner_radius=8,
                      command=on_settings).pack(side="right", padx=3)

        if on_save_project:
            ctk.CTkButton(self, text="\U0001f4be", height=34, width=34,
                          font=("Segoe UI Emoji", 16), fg_color="#2a2a4a",
                          hover_color="#3a3a5a",
                          corner_radius=8, command=on_save_project
                          ).pack(side="right", padx=3)
        if on_open_project:
            ctk.CTkButton(self, text="\U0001f4c2", height=34, width=34,
                          font=("Segoe UI Emoji", 16), fg_color="#2a2a4a",
                          hover_color="#3a3a5a",
                          corner_radius=8, command=on_open_project
                          ).pack(side="right", padx=3)

        if on_new_project:
            ctk.CTkButton(self, text="\U0001f4c4", height=34, width=34,
                          font=("Segoe UI Emoji", 16), fg_color="#2a2a4a",
                          hover_color="#3a3a5a",
                          corner_radius=8, command=on_new_project
                          ).pack(side="right", padx=3)

        # Progress in toolbar — packed last so it fills remaining space
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

        self.status_label = ctk.CTkLabel(prog_col, text=t("toolbar.ready"),
                                         font=("Segoe UI", 9), text_color=DIM,
                                         anchor="w", height=14)
        self.status_label.pack(fill="x")

    def set_status(self, msg, pct=None):
        """Actualiza barra de progreso y status label."""
        self.status_label.configure(text=msg)
        if pct is not None:
            # Detener animación cíclica si hay progreso real
            self._anim_active = False
            try:
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            except Exception:
                pass
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
        """Desactiva el boton generar, activa cancel, inicia animación."""
        self.cancel_btn.configure(state="normal", text_color=ACCENT)
        self.gen_btn.configure(text=t("toolbar.generating"), fg_color="#3a3a5a",
                              state="disabled")
        # Animación manual: barra que va y viene
        self._anim_active = True
        self._anim_pos = 0.0
        self._anim_dir = 1  # 1=forward, -1=backward
        self.progress_bar.configure(mode="determinate")
        self._animate_progress()

    def _animate_progress(self):
        """Ciclo de animación: barra que se mueve de 0→1→0 continuamente."""
        if not self._anim_active:
            return
        self._anim_pos += 0.03 * self._anim_dir
        if self._anim_pos >= 1.0:
            self._anim_pos = 1.0
            self._anim_dir = -1
        elif self._anim_pos <= 0.0:
            self._anim_pos = 0.0
            self._anim_dir = 1
        self.progress_bar.set(self._anim_pos)
        self.after(30, self._animate_progress)

    def set_idle(self):
        """Restaura boton generar, desactiva cancel, para animación."""
        self._anim_active = False
        self.cancel_btn.configure(state="disabled", text_color=DIM)
        self.gen_btn.configure(text=t("toolbar.generate"), fg_color=ACCENT,
                              state="normal")
        try:
            self.progress_bar.stop()
        except Exception:
            pass
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
