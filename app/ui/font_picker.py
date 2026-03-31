"""FontComboBox — combo estilo Office: campo editable + dropdown con cada fuente
en su propia tipografía.

Estructura:
  ┌─────────────────────────┬───┐
  │  Arial          (Arial) │ ▾ │   ← CTkEntry + botón flecha
  └─────────────────────────┴───┘
  ┌─────────────────────────────┐
  │ Arial                       │  ← tk.Toplevel sin decoración (dropdown)
  │ Impact                      │    tk.Text con tag por fuente
  │ Comic Sans MS               │    Scrollbar + filtro live
  │ ...                         │
  └─────────────────────────────┘

Uso:
    combo = FontComboBox(parent, fuente_var, all_inputs)
    combo.pack(fill="x")

Preload (llamar una vez al iniciar la app):
    from app.ui.font_picker import preload_fonts
    preload_fonts(root_window)
"""

import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from app.config import ACCENT, INPUT_BG, DIM

# ── Caché global ──────────────────────────────────────────────────────────────
_ALL_FONTS: list[str] = []
_VALID_FONTS: set[str] = set()   # fuentes que tkinter reconoce realmente
_PRELOAD_DONE = False


def _collect_fonts() -> list[str]:
    names: set[str] = set()
    try:
        import manimpango
        names.update(manimpango.list_fonts())
    except Exception:
        pass
    try:
        names.update(tkfont.families())
    except Exception:
        pass
    if not names:
        names = {"Arial", "Impact", "Segoe UI", "Roboto", "Calibri",
                 "Consolas", "Georgia", "Tahoma", "Verdana"}
    return sorted(f for f in names if not f.startswith("@"))


def preload_fonts(root: tk.Misc, batch: int = 60, delay_ms: int = 8) -> None:
    """Pre-carga lista de fuentes sin bloquear la UI (lotes con after)."""
    global _ALL_FONTS, _PRELOAD_DONE
    if _PRELOAD_DONE:
        return
    _ALL_FONTS = _collect_fonts()
    names = list(_ALL_FONTS)
    idx = [0]

    def _step():
        global _PRELOAD_DONE
        end = min(idx[0] + batch, len(names))
        for name in names[idx[0]:end]:
            try:
                f = tkfont.Font(family=name, size=11)
                if f.actual()["family"].lower() == name.lower():
                    _VALID_FONTS.add(name)
            except Exception:
                pass
        idx[0] = end
        if end < len(names):
            root.after(delay_ms, _step)
        else:
            _PRELOAD_DONE = True

    root.after(30, _step)


# ── Widget principal ──────────────────────────────────────────────────────────

class FontComboBox(ctk.CTkFrame):
    """Combo estilo Office: entry editable + dropdown con fuentes en sí mismas."""

    _ITEM_H = 26        # altura de cada ítem en px
    _MAX_VISIBLE = 12   # ítems visibles antes de hacer scroll

    def __init__(self, parent, fuente_var: ctk.StringVar,
                 all_inputs: list, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._var = fuente_var
        self._dropdown: tk.Toplevel | None = None
        self._text_widget: tk.Text | None = None
        self._filtered: list[str] = []
        self._built = False
        self._hover_line: int | None = None
        self._search_var = tk.StringVar(value=fuente_var.get())

        # ── Entry + flecha ──────────────────────────────────────────────────
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        self._entry = ctk.CTkEntry(
            self, textvariable=self._search_var,
            height=28, corner_radius=6,
            fg_color=INPUT_BG, border_color="#2a2a4a",
            text_color="white", font=("Arial", 11),
        )
        self._entry.grid(row=0, column=0, sticky="ew")

        self._arrow = ctk.CTkButton(
            self, text="▾", width=28, height=28,
            corner_radius=6, fg_color=INPUT_BG,
            hover_color="#2a2a4a", text_color=DIM,
            font=("Segoe UI", 11),
            command=self._toggle_dropdown,
        )
        self._arrow.grid(row=0, column=1, padx=(2, 0))

        all_inputs.append(self._entry)
        all_inputs.append(self._arrow)

        # Bindings del entry
        self._search_var.trace_add("write", self._on_search)
        self._entry.bind("<FocusIn>",    lambda e: self._open_dropdown())
        self._entry.bind("<Return>",     lambda e: self._commit_typed())
        self._entry.bind("<Escape>",     lambda e: self._close_dropdown())
        self._entry.bind("<Down>",       lambda e: self._move(1))
        self._entry.bind("<Up>",         lambda e: self._move(-1))

        # Actualizar fuente del entry cuando cambia la variable
        fuente_var.trace_add("write", lambda *_: self._sync_from_var())

    # ── Sync ─────────────────────────────────────────────────────────────────

    def _sync_from_var(self):
        """Cuando la var externa cambia, actualizar entry y su fuente."""
        name = self._var.get()
        self._search_var.set(name)
        self._apply_entry_font(name)

    def _apply_entry_font(self, name: str):
        try:
            self._entry.configure(font=(name, 11))
        except Exception:
            self._entry.configure(font=("Segoe UI", 11))

    # ── Dropdown ─────────────────────────────────────────────────────────────

    def _toggle_dropdown(self):
        if self._dropdown and self._dropdown.winfo_exists():
            self._close_dropdown()
        else:
            self._open_dropdown()

    def _open_dropdown(self):
        if self._dropdown and self._dropdown.winfo_exists():
            return
        if not _ALL_FONTS:
            # Fuentes aún no cargadas — cargar ahora de forma síncrona
            global _ALL_FONTS
            _ALL_FONTS = _collect_fonts()

        # Crear ventana sin decoración
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)         # sin barra de título
        popup.configure(bg="#0f0f1e")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)

        # Marco con borde sutil
        frame = tk.Frame(popup, bg="#2a2a4a", bd=1, relief="flat")
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Scrollbar
        sb = tk.Scrollbar(frame, orient="vertical", bg="#1a1a2a",
                          troughcolor="#0f0f1e", activebackground=ACCENT)
        sb.pack(side="right", fill="y")

        # Text widget — soporta per-line font via tags
        txt = tk.Text(
            frame,
            yscrollcommand=sb.set,
            bg="#0f0f1e", fg="white",
            selectbackground=ACCENT,
            insertbackground="white",
            relief="flat", bd=0,
            cursor="arrow",
            wrap="none",
            state="disabled",
        )
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)
        txt.bind("<MouseWheel>", lambda e: txt.yview_scroll(
            int(-1 * e.delta / 120), "units"))

        self._text_widget = txt
        self._dropdown = popup

        # Construir contenido (sólo la primera vez se crean los tags)
        if not self._built:
            self._build_tags()
            self._built = True

        # Posicionar bajo el entry
        self._position_dropdown()
        self._filter(self._search_var.get())

        # Cerrar al hacer clic fuera
        popup.bind("<FocusOut>", lambda e: self.after(100, self._check_focus))
        popup.bind("<Escape>",   lambda e: self._close_dropdown())

    def _position_dropdown(self):
        if not self._dropdown:
            return
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        n = min(len(_ALL_FONTS), self._MAX_VISIBLE)
        h = n * self._ITEM_H + 4
        self._dropdown.geometry(f"{w}x{h}+{x}+{y}")

    def _build_tags(self):
        """Configura un tag por cada fuente (operación rápida, una sola vez)."""
        txt = self._text_widget
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        for name in _ALL_FONTS:
            tag = f"f_{id(name)}"   # tag único
            # Usar la fuente real si es válida, sino Segoe UI
            font_spec = (name, 13) if name in _VALID_FONTS else ("Segoe UI", 11)
            txt.tag_configure(tag, font=font_spec,
                              foreground="white",
                              spacing1=3, spacing3=3)
            txt.tag_configure(tag + "_h",    # hover
                              font=font_spec,
                              background="#1e1e3a",
                              foreground=ACCENT,
                              spacing1=3, spacing3=3)
            txt.tag_configure(tag + "_sel",  # seleccionado
                              font=font_spec,
                              background="#1e1e3a",
                              foreground=ACCENT,
                              spacing1=3, spacing3=3)
            txt.insert("end", f"  {name}\n", tag)

            # Bind click en cada línea
            line_no = _ALL_FONTS.index(name) + 1
            txt.tag_bind(tag, "<Button-1>",
                         lambda e, fn=name: self._select(fn))
            txt.tag_bind(tag, "<Enter>",
                         lambda e, ln=line_no: self._set_hover(ln))
            txt.tag_bind(tag, "<Leave>",
                         lambda e, ln=line_no: self._clear_hover(ln))

        txt.configure(state="disabled")

    # ── Filtrado ──────────────────────────────────────────────────────────────

    def _on_search(self, *_):
        query = self._search_var.get()
        if self._dropdown and self._dropdown.winfo_exists():
            self._filter(query)
        else:
            self._open_dropdown()

    def _filter(self, query: str):
        if not self._text_widget:
            return
        txt = self._text_widget
        q = query.strip().lower()
        fonts = [f for f in _ALL_FONTS if q in f.lower()] if q else list(_ALL_FONTS)
        self._filtered = fonts

        txt.configure(state="normal")
        txt.delete("1.0", "end")
        for name in fonts:
            tag = f"f_{id(name)}"
            font_spec = (name, 13) if name in _VALID_FONTS else ("Segoe UI", 11)
            # Re-asegurar el tag (puede haberse perdido al borrar)
            txt.tag_configure(tag, font=font_spec,
                              foreground="white", spacing1=3, spacing3=3)
            txt.tag_bind(tag, "<Button-1>",
                         lambda e, fn=name: self._select(fn))
            txt.insert("end", f"  {name}\n", tag)
        txt.configure(state="disabled")

        # Scroll hasta la fuente actual
        cur = self._var.get()
        if cur in fonts:
            idx = fonts.index(cur)
            total = max(len(fonts), 1)
            txt.yview_moveto(max(0, (idx - 2) / total))

        # Ajustar altura del dropdown
        if self._dropdown and self._dropdown.winfo_exists():
            n = min(len(fonts), self._MAX_VISIBLE)
            h = max(n * self._ITEM_H + 4, 40)
            self._dropdown.geometry(
                f"{self.winfo_width()}x{h}"
                f"+{self.winfo_rootx()}"
                f"+{self.winfo_rooty() + self.winfo_height()}")

    # ── Selección ─────────────────────────────────────────────────────────────

    def _select(self, font_name: str):
        self._var.set(font_name)
        self._search_var.set(font_name)
        self._apply_entry_font(font_name)
        self._close_dropdown()

    def _commit_typed(self):
        """Al presionar Enter, seleccionar la primera coincidencia filtrada."""
        if self._filtered:
            self._select(self._filtered[0])
        else:
            # Escribieron un nombre exacto
            typed = self._search_var.get().strip()
            if typed:
                self._select(typed)

    def _move(self, delta: int):
        """Navegar con flechas arriba/abajo."""
        if not self._filtered:
            return
        cur = self._var.get()
        try:
            idx = self._filtered.index(cur)
        except ValueError:
            idx = -1
        idx = max(0, min(len(self._filtered) - 1, idx + delta))
        self._select(self._filtered[idx])

    # ── Hover ─────────────────────────────────────────────────────────────────

    def _set_hover(self, line_no: int):
        if not self._text_widget:
            return
        self._hover_line = line_no
        try:
            self._text_widget.configure(state="normal")
            self._text_widget.tag_add(
                "hover_hi", f"{line_no}.0", f"{line_no}.end")
            self._text_widget.tag_configure(
                "hover_hi", background="#1e1e3a", foreground=ACCENT)
            self._text_widget.configure(state="disabled")
        except Exception:
            pass

    def _clear_hover(self, line_no: int):
        if not self._text_widget:
            return
        try:
            self._text_widget.configure(state="normal")
            self._text_widget.tag_remove("hover_hi", f"{line_no}.0", f"{line_no}.end")
            self._text_widget.configure(state="disabled")
        except Exception:
            pass

    # ── Cerrar ────────────────────────────────────────────────────────────────

    def _close_dropdown(self):
        if self._dropdown and self._dropdown.winfo_exists():
            self._dropdown.destroy()
        self._dropdown = None
        self._text_widget = None
        self._built = False   # forzar rebuild en siguiente apertura (filtro limpio)

    def _check_focus(self):
        """Cerrar si el foco ya no está en el combo ni en el dropdown."""
        try:
            focused = self.focus_get()
            if focused and (
                str(focused).startswith(str(self)) or
                (self._dropdown and str(focused).startswith(str(self._dropdown)))
            ):
                return
        except Exception:
            pass
        self._close_dropdown()
