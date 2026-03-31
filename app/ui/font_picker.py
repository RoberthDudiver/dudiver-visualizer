"""Font Picker — ventana emergente que muestra cada fuente en sí misma."""

import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from app.config import ACCENT, ACCENT_H, DARK, CARD, INPUT_BG, DIM, GOLD


# Texto de muestra que se muestra junto al nombre de cada fuente
_PREVIEW_TEXT = "Aa Bb 123"


def _get_fonts():
    """Retorna lista de fuentes disponibles (tkinter + manimpango unificados)."""
    fonts = set()
    try:
        import manimpango
        fonts.update(manimpango.list_fonts())
    except Exception:
        pass
    try:
        fonts.update(tkfont.families())
    except Exception:
        pass
    # Excluir fuentes que empiezan con @ (orientales verticales)
    fonts = sorted(f for f in fonts if not f.startswith("@"))
    return fonts


class FontPickerDialog(ctk.CTkToplevel):
    """Diálogo modal para seleccionar fuente con preview visual."""

    def __init__(self, parent, fuente_var, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.fuente_var = fuente_var
        self.title("Seleccionar Fuente")
        self.geometry("520x580")
        self.resizable(True, True)
        self.configure(fg_color=DARK)
        self.grab_set()   # modal
        self.focus_set()

        self._all_fonts = _get_fonts()
        self._visible_fonts = list(self._all_fonts)
        self._font_cache = {}   # nombre → tkFont instance (o None si falla)
        self._selected = fuente_var.get()
        self._item_height = 52
        self._items_on_screen = []

        self._build()
        self._filter("")
        # Scroll hasta la fuente seleccionada
        self.after(100, self._scroll_to_selected)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Fuente", font=("Segoe UI Black", 14),
                     text_color=ACCENT).pack(side="left", padx=14, pady=10)

        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color="#12121e", corner_radius=0, height=42)
        search_frame.pack(fill="x")
        search_frame.pack_propagate(False)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter(self._search_var.get()))

        search_entry = ctk.CTkEntry(search_frame, textvariable=self._search_var,
                                    placeholder_text="Buscar fuente...",
                                    font=("Segoe UI", 11), fg_color=INPUT_BG,
                                    border_color="#2a2a4a", height=30,
                                    corner_radius=6)
        search_entry.pack(fill="x", padx=10, pady=6)
        search_entry.focus_set()

        # Canvas + scrollbar (lista virtual)
        list_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        list_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self._canvas = tk.Canvas(list_frame, bg="#0c0c18", highlightthickness=0,
                                 bd=0)
        vsb = tk.Scrollbar(list_frame, orient="vertical",
                           command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # Frame interior del canvas
        self._inner = tk.Frame(self._canvas, bg="#0c0c18")
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._inner.bind("<MouseWheel>", self._on_mousewheel)

        # Footer con botón cancelar
        footer = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=44)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        ctk.CTkButton(footer, text="Cancelar", width=90, height=30,
                      font=("Segoe UI", 10), fg_color="#2a2a4a",
                      hover_color="#3a3a5a", corner_radius=6,
                      command=self.destroy).pack(side="right", padx=10, pady=7)
        self._count_label = ctk.CTkLabel(footer, text="",
                                         font=("Segoe UI", 9), text_color=DIM)
        self._count_label.pack(side="left", padx=10)

    # ── Font cache ─────────────────────────────────────────────────────────────

    def _get_tk_font(self, name, size=14):
        key = (name, size)
        if key not in self._font_cache:
            try:
                f = tkfont.Font(family=name, size=size)
                # Verificar que realmente se aplicó la fuente pedida
                if f.actual()["family"].lower() != name.lower():
                    self._font_cache[key] = None
                else:
                    self._font_cache[key] = f
            except Exception:
                self._font_cache[key] = None
        return self._font_cache[key]

    # ── Filter ─────────────────────────────────────────────────────────────────

    def _filter(self, query):
        q = query.strip().lower()
        if q:
            self._visible_fonts = [f for f in self._all_fonts
                                    if q in f.lower()]
        else:
            self._visible_fonts = list(self._all_fonts)
        self._count_label.configure(
            text=f"{len(self._visible_fonts)} fuentes")
        self._rebuild_list()

    # ── List ───────────────────────────────────────────────────────────────────

    def _rebuild_list(self):
        # Destruir items anteriores
        for w in self._inner.winfo_children():
            w.destroy()
        self._items_on_screen.clear()

        selected = self._selected

        for font_name in self._visible_fonts:
            is_sel = font_name == selected
            bg = "#1e1e3a" if is_sel else "#0c0c18"
            hover_bg = "#252540"

            row = tk.Frame(self._inner, bg=bg, cursor="hand2",
                           height=self._item_height)
            row.pack(fill="x", pady=1, padx=2)
            row.pack_propagate(False)

            # Preview del texto en la propia fuente
            tk_font = self._get_tk_font(font_name, 16)
            if tk_font:
                preview = tk.Label(row, text=_PREVIEW_TEXT,
                                   font=tk_font,
                                   bg=bg, fg="#e0e0ff",
                                   anchor="w", padx=12)
                preview.pack(side="left")
            else:
                # Fuente no disponible para tkinter — mostrar con fuente por defecto
                tk.Label(row, text=_PREVIEW_TEXT,
                         font=("Segoe UI", 14),
                         bg=bg, fg="#555568",
                         anchor="w", padx=12).pack(side="left")

            # Nombre de la fuente (pequeño, tenue)
            name_lbl = tk.Label(row, text=font_name,
                                font=("Segoe UI", 9),
                                bg=bg, fg=ACCENT if is_sel else "#9090b0",
                                anchor="e", padx=10)
            name_lbl.pack(side="right", fill="x", expand=True)

            # Barra de selección izquierda
            if is_sel:
                bar = tk.Frame(row, bg=ACCENT, width=3)
                bar.place(x=0, y=0, relheight=1)

            # Bind eventos
            def _select(e, fn=font_name):
                self._choose(fn)

            def _enter(e, r=row, fn=font_name):
                for w in r.winfo_children():
                    try:
                        w.configure(bg=hover_bg)
                    except Exception:
                        pass
                r.configure(bg=hover_bg)

            def _leave(e, r=row, fn=font_name, b=bg):
                for w in r.winfo_children():
                    try:
                        w.configure(bg=b)
                    except Exception:
                        pass
                r.configure(bg=b)

            for widget in [row] + list(row.winfo_children()):
                widget.bind("<Button-1>", _select)
                widget.bind("<Enter>", _enter)
                widget.bind("<Leave>", _leave)
                widget.bind("<MouseWheel>", self._on_mousewheel)

            self._items_on_screen.append((font_name, row))

        # Actualizar scroll
        self._inner.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _choose(self, font_name):
        self._selected = font_name
        self.fuente_var.set(font_name)
        self.destroy()

    # ── Scroll helpers ─────────────────────────────────────────────────────────

    def _scroll_to_selected(self):
        if not self._visible_fonts:
            return
        try:
            idx = self._visible_fonts.index(self._selected)
        except ValueError:
            return
        total = len(self._visible_fonts)
        if total == 0:
            return
        frac = idx / total
        self._canvas.yview_moveto(max(0, frac - 0.1))

    def _on_inner_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
