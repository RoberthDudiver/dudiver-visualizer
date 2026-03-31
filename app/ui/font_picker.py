"""FontComboBox — combo de fuentes con preview tipográfico.

Comportamiento:
  · Cada fuente se muestra en su propia tipografía en el dropdown.
  · El dropdown se cierra/reposiciona automáticamente si el entry se mueve
    (panel scrollea, ventana se mueve) — sin depender de eventos de scroll.
  · Filtro live mientras escribís.
  · Navegación con ↑↓ y Enter.
  · Cierra con Escape o clic fuera.

Preload (una vez al iniciar):
    from app.ui.font_picker import preload_fonts
    preload_fonts(root_window)
"""

import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from app.config import ACCENT, INPUT_BG, DIM

# ── Caché global ──────────────────────────────────────────────────────────────
_ALL_FONTS: list[str] = []
_VALID_FONTS: set[str] = set()
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
    """Pre-carga fuentes sin bloquear la UI (lotes con after)."""
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


# ── Widget ────────────────────────────────────────────────────────────────────

class FontComboBox(ctk.CTkFrame):
    """Combo de fuentes con preview: entry editable + dropdown tipográfico."""

    _ITEM_H      = 26
    _MAX_VISIBLE = 12
    _POLL_MS     = 40       # ms entre chequeos de posición

    def __init__(self, parent, fuente_var: ctk.StringVar,
                 all_inputs: list, **kw):
        super().__init__(parent, fg_color="transparent", **kw)

        self._var        = fuente_var
        self._search_var = tk.StringVar(value=fuente_var.get())
        self._filtered:  list[str] = []

        self._popup:     tk.Toplevel | None = None
        self._txt:       tk.Text     | None = None
        self._tags_built = False
        self._last_pos   = (0, 0)   # (x, y) del entry en pantalla
        self._selecting  = False     # flag: no reabrir cuando _select cambia la var

        # ── Entry + botón ─────────────────────────────────────────────────
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        self._entry = ctk.CTkEntry(
            self, textvariable=self._search_var,
            height=28, corner_radius=6,
            fg_color=INPUT_BG, border_color="#2a2a4a",
            text_color="white", font=("Arial", 11),
        )
        self._entry.grid(row=0, column=0, sticky="ew")

        self._btn = ctk.CTkButton(
            self, text="▾", width=28, height=28,
            corner_radius=6, fg_color=INPUT_BG,
            hover_color="#2a2a4a", text_color=DIM,
            font=("Segoe UI", 11),
            command=self._toggle,
        )
        self._btn.grid(row=0, column=1, padx=(2, 0))

        all_inputs.append(self._entry)
        all_inputs.append(self._btn)

        # ── Bindings entry ────────────────────────────────────────────────
        self._search_var.trace_add("write", self._on_type)
        self._entry.bind("<FocusIn>",  lambda e: self._open())
        self._entry.bind("<Return>",   lambda e: self._commit())
        self._entry.bind("<Escape>",   lambda e: self._close())
        self._entry.bind("<Down>",     lambda e: self._move(+1))
        self._entry.bind("<Up>",       lambda e: self._move(-1))

        fuente_var.trace_add("write", lambda *_: self._sync())

    # ── Sync ──────────────────────────────────────────────────────────────────

    def _sync(self):
        name = self._var.get()
        self._search_var.set(name)
        self._set_entry_font(name)

    def _set_entry_font(self, name: str):
        try:
            self._entry.configure(font=(name, 11))
        except Exception:
            self._entry.configure(font=("Segoe UI", 11))

    # ── Apertura / cierre ─────────────────────────────────────────────────────

    def _toggle(self):
        if self._popup and self._popup.winfo_exists():
            self._close()
        else:
            self._open()

    def _open(self):
        global _ALL_FONTS
        if self._popup and self._popup.winfo_exists():
            return
        if not _ALL_FONTS:
            _ALL_FONTS = _collect_fonts()

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg="#0f0f1e")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        self._popup = popup

        border = tk.Frame(popup, bg="#2a2a4a", bd=1, relief="flat")
        border.pack(fill="both", expand=True, padx=1, pady=1)

        sb = tk.Scrollbar(border, orient="vertical",
                          bg="#1a1a2a", troughcolor="#0f0f1e",
                          activebackground=ACCENT)
        sb.pack(side="right", fill="y")

        txt = tk.Text(border,
                      yscrollcommand=sb.set,
                      bg="#0f0f1e", fg="white",
                      selectbackground=ACCENT,
                      relief="flat", bd=0,
                      cursor="arrow", wrap="none",
                      state="disabled")
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)
        self._txt = txt

        txt.bind("<MouseWheel>",
                 lambda e: txt.yview_scroll(int(-e.delta / 120), "units"))

        if not self._tags_built:
            self._build_all_tags()
            self._tags_built = True

        self._place_popup()
        # Al abrir siempre mostrar TODAS las fuentes y scrollear a la actual.
        # Si el usuario escribe, _on_type filtra en vivo.
        self._filter("")

        # clic fuera → cerrar
        popup.bind("<FocusOut>", lambda e: self.after(80, self._check_focus))
        popup.bind("<Escape>",   lambda e: self._close())

        # guardar posición actual del entry y arrancar polling
        self.update_idletasks()
        self._last_pos = (self.winfo_rootx(), self.winfo_rooty())
        self._poll_position()

        # ── Bloquear scroll del panel mientras el popup está abierto ──────
        # CTkScrollableFrame usa bind_all + check_if_master_is_canvas para
        # scrollear. Parcheamos ese método en la instancia para que retorne
        # False mientras el popup exista → el panel no scrollea.
        self._patched_sf = None
        w = self.master
        while w is not None:
            if hasattr(w, "_mouse_wheel_all") and hasattr(w, "_parent_canvas"):
                orig = w.check_if_master_is_canvas
                popup_ref = popup

                def _patched(widget, _orig=orig, _pop=popup_ref):
                    if _pop.winfo_exists():
                        return False   # bloquear scroll del panel
                    return _orig(widget)

                w.check_if_master_is_canvas = _patched
                self._patched_sf  = w
                self._patched_orig = orig
                break
            try:
                w = w.master
            except Exception:
                break

    def _place_popup(self):
        """Posicionar popup justo debajo del entry."""
        if not self._popup:
            return
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        n = min(len(_ALL_FONTS), self._MAX_VISIBLE)
        h = n * self._ITEM_H + 4
        self._popup.geometry(f"{w}x{h}+{x}+{y}")

    def _poll_position(self):
        """Cada _POLL_MS ms: si el entry se movió, cerrar el popup."""
        if not self._popup or not self._popup.winfo_exists():
            return
        try:
            cur = (self.winfo_rootx(), self.winfo_rooty())
        except Exception:
            self._close()
            return

        if cur != self._last_pos:
            # El entry se movió (scroll del panel, ventana movida, etc.)
            self._close()
            return

        # Seguir vigilando
        self.after(self._POLL_MS, self._poll_position)

    # ── Contenido del popup ───────────────────────────────────────────────────

    def _build_all_tags(self):
        txt = self._txt
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        for i, name in enumerate(_ALL_FONTS):
            tag = f"f{i}"
            fs  = (name, 13) if name in _VALID_FONTS else ("Segoe UI", 11)
            txt.tag_configure(tag,
                              font=fs, foreground="white",
                              spacing1=4, spacing3=4)
            txt.tag_configure(tag + "h",
                              font=fs, foreground=ACCENT,
                              background="#1e1e3a",
                              spacing1=4, spacing3=4)
            txt.insert("end", f"  {name}\n", tag)
            line = i + 1
            txt.tag_bind(tag, "<Button-1>",
                         lambda e, n=name: self._select(n))
            txt.tag_bind(tag, "<Enter>",
                         lambda e, t=tag, l=line: self._hover_on(t, l))
            txt.tag_bind(tag, "<Leave>",
                         lambda e, t=tag, l=line: self._hover_off(t, l))
        txt.configure(state="disabled")

    def _filter(self, query: str):
        if not self._txt:
            return
        txt = self._txt
        q   = query.strip().lower()
        fonts = ([f for f in _ALL_FONTS if q in f.lower()]
                 if q else list(_ALL_FONTS))
        self._filtered = fonts

        txt.configure(state="normal")
        txt.delete("1.0", "end")
        for name in fonts:
            gi  = _ALL_FONTS.index(name) if name in _ALL_FONTS else 0
            tag = f"f{gi}"
            fs  = (name, 13) if name in _VALID_FONTS else ("Segoe UI", 11)
            txt.tag_configure(tag, font=fs, foreground="white",
                              spacing1=4, spacing3=4)
            txt.tag_bind(tag, "<Button-1>",
                         lambda e, n=name: self._select(n))
            txt.insert("end", f"  {name}\n", tag)
        txt.configure(state="disabled")

        cur = self._var.get()
        if cur in fonts:
            idx   = fonts.index(cur)
            total = max(len(fonts), 1)
            txt.yview_moveto(max(0.0, (idx - 2) / total))

        if self._popup and self._popup.winfo_exists():
            n = min(len(fonts), self._MAX_VISIBLE)
            h = max(n * self._ITEM_H + 4, 40)
            self._popup.geometry(
                f"{self.winfo_width()}x{h}"
                f"+{self.winfo_rootx()}"
                f"+{self.winfo_rooty() + self.winfo_height()}")

    # ── Hover ─────────────────────────────────────────────────────────────────

    def _hover_on(self, tag: str, line: int):
        if not self._txt:
            return
        try:
            self._txt.configure(state="normal")
            self._txt.tag_add(tag + "h", f"{line}.0", f"{line}.end")
            self._txt.configure(state="disabled")
        except Exception:
            pass

    def _hover_off(self, tag: str, line: int):
        if not self._txt:
            return
        try:
            self._txt.configure(state="normal")
            self._txt.tag_remove(tag + "h", f"{line}.0", f"{line}.end")
            self._txt.configure(state="disabled")
        except Exception:
            pass

    # ── Selección / navegación ────────────────────────────────────────────────

    def _select(self, name: str):
        self._selecting = True
        self._var.set(name)
        self._search_var.set(name)
        self._selecting = False
        self._set_entry_font(name)
        self._close()

    def _commit(self):
        if self._filtered:
            self._select(self._filtered[0])
        else:
            typed = self._search_var.get().strip()
            if typed:
                self._select(typed)

    def _move(self, delta: int):
        if not self._filtered:
            return
        cur = self._var.get()
        try:
            idx = self._filtered.index(cur)
        except ValueError:
            idx = -1
        idx = max(0, min(len(self._filtered) - 1, idx + delta))
        self._select(self._filtered[idx])

    def _on_type(self, *_):
        if self._selecting:
            return                          # ignorar cambios provocados por _select
        q = self._search_var.get()
        if self._popup and self._popup.winfo_exists():
            self._filter(q)
        else:
            self._open()

    # ── Cerrar ────────────────────────────────────────────────────────────────

    def _close(self):
        # Restaurar check_if_master_is_canvas del CTkScrollableFrame
        try:
            sf = getattr(self, "_patched_sf", None)
            if sf is not None:
                sf.check_if_master_is_canvas = self._patched_orig
        except Exception:
            pass
        self._patched_sf = None

        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup      = None
        self._txt        = None
        self._tags_built = False

    def _check_focus(self):
        try:
            focused = self.focus_get()
            if focused and (
                str(focused).startswith(str(self)) or
                (self._popup and str(focused).startswith(str(self._popup)))
            ):
                return
        except Exception:
            pass
        self._close()
