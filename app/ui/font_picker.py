"""FontComboBox — combo de fuentes con preview tipográfico.

Flujo:
  1. App abre → combo CERRADO, muestra nombre de fuente en su tipografía.
  2. Click en ▾ → dropdown abre.  Scroll solo dentro del dropdown.
  3. Click en fuente → selecciona, cierra dropdown.
  4. Click en CUALQUIER otro lado → cierra dropdown.
  5. Escape → cierra dropdown.
  6. Dropdown cerrado → scroll normal del panel padre.

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
    _ITEM_H      = 26
    _MAX_VISIBLE = 12
    _POLL_MS     = 40

    def __init__(self, parent, fuente_var: ctk.StringVar,
                 all_inputs: list, **kw):
        super().__init__(parent, fg_color="transparent", **kw)

        self._var         = fuente_var
        self._search_var  = tk.StringVar(value=fuente_var.get())
        self._filtered:   list[str] = []
        self._popup:      tk.Toplevel | None = None
        self._txt:        tk.Text     | None = None
        self._tags_built  = False
        self._last_pos    = (0, 0)
        self._selecting   = False
        self._ready       = False       # impide abrir durante __init__
        self._patched_sf  = None
        self._patched_orig = None

        # ── Layout ────────────────────────────────────────────────────────
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

        # ── Bindings ──────────────────────────────────────────────────────
        self._search_var.trace_add("write", self._on_type)
        self._entry.bind("<Return>", lambda e: self._commit())
        self._entry.bind("<Escape>", lambda e: self._close())
        self._entry.bind("<Down>",   lambda e: self._move(+1))
        self._entry.bind("<Up>",     lambda e: self._move(-1))
        fuente_var.trace_add("write", lambda *_: self._sync())

        # Clic global: se bindea UNA SOLA VEZ en __init__.
        # Si popup no existe, el handler retorna sin hacer nada.
        self.after(100, self._bind_global_click)

        # Marcar como listo después de que la app termine de construir el UI
        self.after(500, self._mark_ready)

    def _mark_ready(self):
        self._ready = True

    def _bind_global_click(self):
        """Bindea <Button-1> en toda la app UNA VEZ. Handler chequea si popup está abierto."""
        try:
            self.winfo_toplevel().bind_all("<Button-1>", self._on_any_click, add="+")
        except Exception:
            pass

    # ── Sync ──────────────────────────────────────────────────────────────────

    def _sync(self):
        name = self._var.get()
        if self._search_var.get() != name:
            self._selecting = True
            self._search_var.set(name)
            self._selecting = False
        self._set_entry_font(name)

    def _set_entry_font(self, name: str):
        try:
            self._entry.configure(font=(name, 11))
        except Exception:
            self._entry.configure(font=("Segoe UI", 11))

    # ── Abrir / cerrar ────────────────────────────────────────────────────────

    def _is_open(self):
        return self._popup is not None and self._popup.winfo_exists()

    def _toggle(self):
        if self._is_open():
            self._close()
        else:
            self._open()

    def _open(self):
        global _ALL_FONTS
        if self._is_open():
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

        # Scroll solo en el popup
        txt.bind("<MouseWheel>",
                 lambda e: txt.yview_scroll(int(-e.delta / 120), "units"))

        self._build_all_tags()
        self._place_popup()
        self._filter("")

        popup.bind("<Escape>", lambda e: self._close())

        # Bloquear scroll del panel padre
        self._patch_parent_scroll()

        # Polling de posición: detecta scroll del panel y cierra
        self.update_idletasks()
        self._last_pos = (self.winfo_rootx(), self.winfo_rooty())
        self._poll_position()

    def _place_popup(self):
        if not self._popup:
            return
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        n = min(len(self._filtered) if self._filtered else len(_ALL_FONTS),
                self._MAX_VISIBLE)
        h = n * self._ITEM_H + 4
        self._popup.geometry(f"{w}x{h}+{x}+{y}")

    def _poll_position(self):
        if not self._is_open():
            return
        try:
            cur = (self.winfo_rootx(), self.winfo_rooty())
        except Exception:
            self._close()
            return
        if cur != self._last_pos:
            self._close()
            return
        self.after(self._POLL_MS, self._poll_position)

    def _patch_parent_scroll(self):
        """Bloquea scroll del CTkScrollableFrame padre mientras popup esté abierto."""
        self._patched_sf = None
        w = self.master
        while w is not None:
            if hasattr(w, "_mouse_wheel_all") and hasattr(w, "check_if_master_is_canvas"):
                orig = w.check_if_master_is_canvas
                popup_ref = self._popup

                def _blocked(widget, _orig=orig, _pop=popup_ref):
                    try:
                        if _pop and _pop.winfo_exists():
                            return False
                    except Exception:
                        pass
                    return _orig(widget)

                w.check_if_master_is_canvas = _blocked
                self._patched_sf = w
                self._patched_orig = orig
                break
            try:
                w = w.master
            except Exception:
                break

    def _unpatch_parent_scroll(self):
        try:
            if self._patched_sf and self._patched_orig:
                self._patched_sf.check_if_master_is_canvas = self._patched_orig
        except Exception:
            pass
        self._patched_sf = None
        self._patched_orig = None

    # ── Contenido ─────────────────────────────────────────────────────────────

    def _build_all_tags(self):
        txt = self._txt
        if not txt:
            return
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        for i, name in enumerate(_ALL_FONTS):
            tag = f"f{i}"
            fs = (name, 13) if name in _VALID_FONTS else ("Segoe UI", 11)
            txt.tag_configure(tag, font=fs, foreground="white",
                              spacing1=4, spacing3=4)
            txt.insert("end", f"  {name}\n", tag)
            txt.tag_bind(tag, "<Button-1>",
                         lambda e, n=name: self._select(n))
            txt.tag_bind(tag, "<Enter>",
                         lambda e, t=tag, l=i+1: self._hover_on(t, l))
            txt.tag_bind(tag, "<Leave>",
                         lambda e, t=tag, l=i+1: self._hover_off(t, l))
        txt.configure(state="disabled")

    def _filter(self, query: str):
        if not self._txt:
            return
        txt = self._txt
        q = query.strip().lower()
        fonts = [f for f in _ALL_FONTS if q in f.lower()] if q else list(_ALL_FONTS)
        self._filtered = fonts

        txt.configure(state="normal")
        txt.delete("1.0", "end")
        for name in fonts:
            gi = _ALL_FONTS.index(name) if name in _ALL_FONTS else 0
            tag = f"f{gi}"
            fs = (name, 13) if name in _VALID_FONTS else ("Segoe UI", 11)
            txt.tag_configure(tag, font=fs, foreground="white",
                              spacing1=4, spacing3=4)
            txt.tag_bind(tag, "<Button-1>",
                         lambda e, n=name: self._select(n))
            txt.insert("end", f"  {name}\n", tag)
        txt.configure(state="disabled")

        # Scroll a la fuente actual
        cur = self._var.get()
        if cur in fonts:
            idx = fonts.index(cur)
            total = max(len(fonts), 1)
            txt.yview_moveto(max(0.0, (idx - 2) / total))

        # Ajustar tamaño
        if self._is_open():
            n = min(len(fonts), self._MAX_VISIBLE)
            h = max(n * self._ITEM_H + 4, 40)
            self._popup.geometry(
                f"{self.winfo_width()}x{h}"
                f"+{self.winfo_rootx()}"
                f"+{self.winfo_rooty() + self.winfo_height()}")

    # ── Hover ─────────────────────────────────────────────────────────────────

    def _hover_on(self, tag, line):
        if not self._txt:
            return
        try:
            self._txt.configure(state="normal")
            ht = tag + "h"
            self._txt.tag_configure(ht, foreground=ACCENT, background="#1e1e3a")
            self._txt.tag_add(ht, f"{line}.0", f"{line}.end")
            self._txt.configure(state="disabled")
        except Exception:
            pass

    def _hover_off(self, tag, line):
        if not self._txt:
            return
        try:
            self._txt.configure(state="normal")
            self._txt.tag_remove(tag + "h", f"{line}.0", f"{line}.end")
            self._txt.configure(state="disabled")
        except Exception:
            pass

    # ── Selección ─────────────────────────────────────────────────────────────

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

    def _move(self, delta):
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
        if self._selecting or not self._ready:
            return
        q = self._search_var.get()
        if self._is_open():
            self._filter(q)
        # NO abrir automáticamente al tipear — solo con el botón ▾

    # ── Clic global → cerrar si fuera ─────────────────────────────────────────

    def _on_any_click(self, event):
        """Se ejecuta en CADA clic de la app. Si popup abierto y clic afuera, cierra."""
        if not self._is_open():
            return

        # ¿Clic dentro del popup?
        try:
            px = self._popup.winfo_rootx()
            py = self._popup.winfo_rooty()
            pw = self._popup.winfo_width()
            ph = self._popup.winfo_height()
            if px <= event.x_root <= px + pw and py <= event.y_root <= py + ph:
                return  # dentro del popup → no cerrar
        except Exception:
            pass

        # ¿Clic en el botón ▾? → _toggle se encarga, no cerrar aquí
        try:
            bx = self._btn.winfo_rootx()
            by = self._btn.winfo_rooty()
            bw = self._btn.winfo_width()
            bh = self._btn.winfo_height()
            if bx <= event.x_root <= bx + bw and by <= event.y_root <= by + bh:
                return
        except Exception:
            pass

        # Clic fuera → cerrar
        self._close()

    # ── Cerrar ────────────────────────────────────────────────────────────────

    def _close(self):
        self._unpatch_parent_scroll()
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup     = None
        self._txt       = None
        self._tags_built = False
