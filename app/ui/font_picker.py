"""Font Picker — dropdown nativo (tk.Menu) con cada fuente en su propia tipografía.

Flujo:
  1. Al importar el módulo, preload_fonts() se puede llamar desde el hilo principal
     con after() para cargar las fuentes sin bloquear la UI.
  2. FontMenuButton es un CTkButton que, al hacer clic, abre un tk.Menu
     posicionado justo debajo del botón (sensación de combo real).
  3. El menú se construye UNA sola vez y se reutiliza (caché).
"""

import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from app.config import ACCENT, DARK, CARD, INPUT_BG, DIM

# ── Estado global del módulo ──────────────────────────────────────────────────
_ALL_FONTS: list[str] = []       # lista ordenada de nombres de fuente
_TK_FONTS: dict[str, object] = {}  # nombre → tkfont.Font (o None si no disponible)
_PRELOAD_DONE = False


def _collect_font_names() -> list[str]:
    """Recopila fuentes de manimpango + tkinter, elimina duplicados y @-fuentes."""
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
                 "Consolas", "Georgia", "Tahoma", "Verdana", "Comic Sans MS"}
    return sorted(f for f in names if not f.startswith("@"))


def preload_fonts(root: tk.Misc, batch: int = 40, delay_ms: int = 10) -> None:
    """Pre-carga todas las fuentes en el hilo principal usando after() por lotes.

    Llamar una sola vez desde el hilo principal (ej. en VisualizerApp.__init__
    después de construir la ventana).  No bloquea la UI.
    """
    global _ALL_FONTS, _PRELOAD_DONE

    if _PRELOAD_DONE:
        return

    _ALL_FONTS = _collect_font_names()
    names = list(_ALL_FONTS)
    idx = [0]  # mutable para capturar en closure

    def _load_batch():
        start = idx[0]
        end = min(start + batch, len(names))
        for name in names[start:end]:
            if name not in _TK_FONTS:
                try:
                    f = tkfont.Font(family=name, size=11)
                    _TK_FONTS[name] = f if f.actual()["family"].lower() == name.lower() else None
                except Exception:
                    _TK_FONTS[name] = None
        idx[0] = end
        if end < len(names):
            root.after(delay_ms, _load_batch)
        else:
            global _PRELOAD_DONE
            _PRELOAD_DONE = True

    root.after(50, _load_batch)   # empieza 50ms después del inicio


# ── Widget ────────────────────────────────────────────────────────────────────

class FontMenuButton(ctk.CTkFrame):
    """Botón + dropdown-menu: cada fuente renderizada en sí misma."""

    def __init__(self, parent, fuente_var: ctk.StringVar,
                 all_inputs: list, **frame_kw):
        super().__init__(parent, fg_color="transparent", **frame_kw)
        self._var = fuente_var
        self._menu: tk.Menu | None = None     # se construye la primera vez
        self._menu_built = False

        # Botón principal
        self._btn = ctk.CTkButton(
            self,
            textvariable=fuente_var,
            height=28, corner_radius=6,
            fg_color=INPUT_BG, hover_color="#2a2a4a",
            text_color="white",
            anchor="w",
            command=self._toggle_menu,
        )
        self._btn.pack(fill="x")
        all_inputs.append(self._btn)

        # Actualizar la fuente del botón cuando cambia la selección
        fuente_var.trace_add("write", lambda *_: self._refresh_btn_font())
        self._refresh_btn_font()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh_btn_font(self):
        """Muestra el nombre de la fuente en la propia tipografía."""
        name = self._var.get()
        try:
            self._btn.configure(font=(name, 11))
        except Exception:
            self._btn.configure(font=("Segoe UI", 11))

    def _build_menu(self):
        """Construye el tk.Menu una sola vez con todas las fuentes."""
        root = self.winfo_toplevel()
        menu = tk.Menu(root, tearoff=0,
                       bg="#12122a", fg="white",
                       activebackground=ACCENT, activeforeground="white",
                       bd=0, relief="flat")

        fonts = _ALL_FONTS if _ALL_FONTS else _collect_font_names()

        # Agrupar por letra inicial en sub-menús (hace el menú más manejable)
        groups: dict[str, list[str]] = {}
        for name in fonts:
            key = name[0].upper()
            groups.setdefault(key, []).append(name)

        for letter in sorted(groups):
            sub = tk.Menu(menu, tearoff=0,
                          bg="#12122a", fg="white",
                          activebackground=ACCENT, activeforeground="white",
                          bd=0, relief="flat")
            for font_name in groups[letter]:
                tk_font = _TK_FONTS.get(font_name)
                kw = {"font": tk_font} if tk_font else {}
                sub.add_command(
                    label=font_name,
                    command=lambda fn=font_name: self._select(fn),
                    **kw,
                )
            menu.add_cascade(label=f"  {letter}", menu=sub,
                             font=("Segoe UI Bold", 10))

        self._menu = menu
        self._menu_built = True

    def _toggle_menu(self):
        if not self._menu_built:
            self._build_menu()

        try:
            # Posicionar justo debajo del botón
            x = self._btn.winfo_rootx()
            y = self._btn.winfo_rooty() + self._btn.winfo_height()
            self._menu.tk_popup(x, y)
        finally:
            self._menu.grab_release()

    def _select(self, font_name: str):
        self._var.set(font_name)
