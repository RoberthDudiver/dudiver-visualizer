"""Helpers reutilizables para construir la UI."""

import os
import customtkinter as ctk
from tkinter import filedialog

from app.config import ACCENT, ACCENT_H, GOLD, DIM, CARD, INPUT_BG
from app.i18n import t


def short_path(p, mx=35):
    if not p:
        return ""
    n = os.path.basename(p)
    return n[:mx-3] + "..." if len(n) > mx else n


def create_section(parent, text):
    """Crea un label de seccion con estilo ACCENT."""
    if text:
        ctk.CTkLabel(parent, text=text, font=("Segoe UI Semibold", 11),
                     text_color=ACCENT, anchor="w").pack(fill="x", padx=8, pady=(10, 3))


def create_file_row(parent, label, var, ftypes, all_inputs):
    """Crea una fila para seleccionar archivo. Retorna el boton."""
    row = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8, height=36)
    row.pack(fill="x", padx=6, pady=2)
    row.pack_propagate(False)

    ctk.CTkLabel(row, text=label, font=("Segoe UI", 10),
                 text_color=DIM, width=60).pack(side="left", padx=(10, 0))

    name_lbl = ctk.CTkLabel(row, text="", font=("Segoe UI", 10),
                            text_color=GOLD, anchor="w")
    name_lbl.pack(side="left", fill="x", expand=True, padx=6)

    def pick():
        p = filedialog.askopenfilename(title=t("files.select", label=label),
                                       filetypes=ftypes + [(t("files.all"), "*.*")])
        if p:
            var.set(p)

    btn = ctk.CTkButton(row, text="...", width=32, height=26,
                        font=("Segoe UI Bold", 10), fg_color=INPUT_BG,
                        hover_color=ACCENT, corner_radius=6, command=pick)
    btn.pack(side="right", padx=6)
    all_inputs.append(btn)

    var.trace_add("write", lambda *_: name_lbl.configure(text=short_path(var.get())))
    return btn


class SpinnerLabel(ctk.CTkLabel):
    """Label animado que muestra actividad: texto + dots pulsantes.

    Uso:
        spinner = SpinnerLabel(parent, base_text="Procesando")
        spinner.pack(...)
        spinner.start()   # empieza animación
        spinner.stop("Listo!")  # para y muestra mensaje final
    """

    FRAMES = ["", ".", "..", "...", "....", "...."]

    def __init__(self, parent, base_text="Procesando", **kw):
        kw.setdefault("font", ("Segoe UI", 11))
        kw.setdefault("text_color", GOLD)
        kw.setdefault("text", "")
        super().__init__(parent, **kw)
        self._base = base_text
        self._idx = 0
        self._running = False
        self._after_id = None
        self._elapsed = 0

    def start(self, text=None):
        if text:
            self._base = text
        self._idx = 0
        self._elapsed = 0
        self._running = True
        self._tick()

    def stop(self, final_text=None):
        self._running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.configure(text=final_text or "")

    def _tick(self):
        if not self._running:
            return
        dots = self.FRAMES[self._idx % len(self.FRAMES)]
        elapsed_s = self._elapsed // 2  # cada tick ~500ms
        time_str = f" ({elapsed_s}s)" if elapsed_s >= 3 else ""
        self.configure(text=f"{self._base}{dots}{time_str}")
        self._idx += 1
        self._elapsed += 1
        self._after_id = self.after(500, self._tick)


def create_dropdown(parent, label, var, values, all_inputs):
    """Crea una fila dropdown (OptionMenu)."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=12, pady=3)
    ctk.CTkLabel(row, text=label, font=("Segoe UI", 10),
                 text_color=DIM, width=70, anchor="w").pack(side="left")
    dd = ctk.CTkOptionMenu(row, variable=var, values=values,
                           font=("Segoe UI", 10), fg_color=INPUT_BG,
                           button_color="#2a2a4a", button_hover_color=ACCENT,
                           dropdown_fg_color=CARD, dropdown_hover_color=ACCENT,
                           corner_radius=6, height=28)
    dd.pack(side="right", fill="x", expand=True)
    all_inputs.append(dd)
    return dd
