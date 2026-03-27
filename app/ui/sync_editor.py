"""Editor avanzado de sincronización de timestamps.

Permite editar manualmente los timestamps palabra por palabra,
y opcionalmente re-sincronizar con IA (Claude API, OpenAI, etc.)
o ejecutando Claude Code en terminal.
"""

import json
import os
import subprocess
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog

from app.config import ACCENT, ACCENT_H, DARK, CARD, DIM, INPUT_BG, GOLD, GREEN
from app.i18n import t
from app.ui.components import SpinnerLabel


class SyncEditorWindow(ctk.CTkToplevel):
    """Ventana de edición avanzada de timestamps."""

    def __init__(self, parent, audio_path, ts_path, on_save=None):
        super().__init__(parent)
        self.title(t("sync.title"))
        self.geometry("900x650")
        self.configure(fg_color=DARK)
        self.attributes("-topmost", True)
        self.lift()

        # Icono
        from app.utils.paths import asset_path
        ico = asset_path("icon.ico")
        if os.path.exists(ico):
            self.after(100, lambda: self.iconbitmap(ico))

        self._audio_path = audio_path
        self._ts_path = ts_path
        self._on_save = on_save
        self._palabras = []
        self._segmentos = []
        self._raw_data = None
        self._rows = []  # (word_label, start_entry, end_entry)

        self._load_data()
        self._build()

    def _load_data(self):
        """Carga el archivo de timestamps."""
        if not self._ts_path or not os.path.isfile(self._ts_path):
            return

        with open(self._ts_path, "r", encoding="utf-8") as f:
            self._raw_data = json.load(f)

        if isinstance(self._raw_data, dict) and "palabras" in self._raw_data:
            self._palabras = self._raw_data.get("palabras", [])
            self._segmentos = self._raw_data.get("segmentos", [])
        elif isinstance(self._raw_data, list):
            # Formato directo de líneas
            self._segmentos = self._raw_data

    def _build(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=CARD, height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="SYNC EDITOR", font=("Segoe UI", 16, "bold"),
                     text_color=ACCENT).pack(side="left", padx=12)

        info = f"{len(self._palabras)} palabras" if self._palabras else f"{len(self._segmentos)} líneas"
        ctk.CTkLabel(header, text=info, font=("Segoe UI", 11),
                     text_color=DIM).pack(side="left", padx=8)

        # Botones header
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=8)

        ctk.CTkButton(btn_frame, text="Guardar", width=80, height=30,
                      fg_color=GREEN, hover_color="#2ecc71", text_color="#000",
                      command=self._save).pack(side="right", padx=4)

        ctk.CTkButton(btn_frame, text="Exportar JSON", width=100, height=30,
                      fg_color=CARD, hover_color="#2a2a4e",
                      border_width=1, border_color=DIM,
                      command=self._export).pack(side="right", padx=4)

        # Accent line
        ctk.CTkFrame(self, fg_color=ACCENT, height=2, corner_radius=0).pack(fill="x")

        # ── Tabs: Palabras | Líneas | IA Sync ──
        self._tabs = ctk.CTkTabview(self, fg_color=DARK,
                                     segmented_button_fg_color=CARD,
                                     segmented_button_selected_color=ACCENT,
                                     segmented_button_selected_hover_color=ACCENT_H)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=8)

        tab_words = self._tabs.add("Palabras")
        tab_lines = self._tabs.add("Líneas")
        tab_ai = self._tabs.add("IA Sync")

        self._build_words_tab(tab_words)
        self._build_lines_tab(tab_lines)
        self._build_ai_tab(tab_ai)

    # ── Tab: Palabras ──

    def _build_words_tab(self, parent):
        if not self._palabras:
            ctk.CTkLabel(parent, text="No hay timestamps de palabras.\n"
                         "Ejecuta Whisper primero con word_timestamps=True.",
                         text_color=DIM, font=("Segoe UI", 12)).pack(pady=30)
            return

        # Toolbar
        tb = ctk.CTkFrame(parent, fg_color="transparent", height=35)
        tb.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(tb, text="+ 50ms todo", width=90, height=28,
                      fg_color=CARD, hover_color="#2a2a4e",
                      command=lambda: self._shift_all(0.05)).pack(side="left", padx=2)
        ctk.CTkButton(tb, text="- 50ms todo", width=90, height=28,
                      fg_color=CARD, hover_color="#2a2a4e",
                      command=lambda: self._shift_all(-0.05)).pack(side="left", padx=2)
        ctk.CTkButton(tb, text="Autofix gaps", width=90, height=28,
                      fg_color=CARD, hover_color="#2a2a4e",
                      command=self._autofix_gaps).pack(side="left", padx=2)

        info_lbl = ctk.CTkLabel(tb, text=f"{len(self._palabras)} palabras",
                                 font=("Segoe UI", 10), text_color=DIM)
        info_lbl.pack(side="right", padx=8)

        # Virtualizado: solo una Treeview nativa (ultraligera, sin CTk overhead)
        import tkinter.ttk as ttk

        # Estilo oscuro para Treeview
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Sync.Treeview",
                         background="#0a0a14", foreground="#ffffff",
                         fieldbackground="#0a0a14", rowheight=26,
                         font=("Consolas", 10))
        style.configure("Sync.Treeview.Heading",
                         background=CARD, foreground=ACCENT,
                         font=("Consolas", 10, "bold"))
        style.map("Sync.Treeview",
                   background=[("selected", ACCENT)],
                   foreground=[("selected", "#000000")])

        tree_frame = ctk.CTkFrame(parent, fg_color="#0a0a14", corner_radius=8)
        tree_frame.pack(fill="both", expand=True)

        cols = ("palabra", "inicio", "fin", "duracion")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                   style="Sync.Treeview", selectmode="browse")
        self._tree.heading("palabra", text="Palabra")
        self._tree.heading("inicio", text="Inicio (s)")
        self._tree.heading("fin", text="Fin (s)")
        self._tree.heading("duracion", text="Duración")

        self._tree.column("palabra", width=200, minwidth=120)
        self._tree.column("inicio", width=100, minwidth=80)
        self._tree.column("fin", width=100, minwidth=80)
        self._tree.column("duracion", width=80, minwidth=60)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True, padx=2, pady=2)

        # Insertar todas las palabras (Treeview maneja virtualización nativa)
        for i, w in enumerate(self._palabras):
            dur = w.get("fin", 0) - w.get("inicio", 0)
            self._tree.insert("", "end", iid=str(i), values=(
                w.get("palabra", ""),
                f"{w.get('inicio', 0):.3f}",
                f"{w.get('fin', 0):.3f}",
                f"{dur:.3f}s",
            ))

        # Alternar colores de filas
        self._tree.tag_configure("even", background="#0a0a14")
        self._tree.tag_configure("odd", background="#12121e")
        for i, item in enumerate(self._tree.get_children()):
            self._tree.item(item, tags=("even" if i % 2 == 0 else "odd",))

        # Doble-click para editar
        self._tree.bind("<Double-1>", self._on_tree_edit)
        self._edit_entry = None

    def _on_tree_edit(self, event):
        """Edición in-line al hacer doble click en una celda."""
        item = self._tree.identify_row(event.y)
        col = self._tree.identify_column(event.x)
        if not item or not col:
            return

        col_idx = int(col.replace("#", "")) - 1
        col_name = ("palabra", "inicio", "fin", "duracion")[col_idx]

        # Solo editar inicio y fin
        if col_name not in ("inicio", "fin"):
            return

        # Posición de la celda
        x, y, w, h = self._tree.bbox(item, col)
        val = self._tree.set(item, col_name)

        # Destruir editor previo
        if self._edit_entry:
            self._edit_entry.destroy()

        entry = tk.Entry(self._tree, font=("Consolas", 10),
                         bg="#1a1a2e", fg="#ffffff", insertbackground="#ffffff",
                         relief="flat", borderwidth=1)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, val)
        entry.select_range(0, "end")
        entry.focus_set()
        self._edit_entry = entry

        def _commit(ev=None):
            new_val = entry.get().strip()
            try:
                float(new_val)  # Validar
                self._tree.set(item, col_name, new_val)
                # Actualizar duración
                inicio = float(self._tree.set(item, "inicio"))
                fin = float(self._tree.set(item, "fin"))
                self._tree.set(item, "duracion", f"{fin - inicio:.3f}s")
                # Actualizar datos internos
                idx = int(item)
                self._palabras[idx]["inicio"] = inicio
                self._palabras[idx]["fin"] = fin
            except ValueError:
                pass
            entry.destroy()
            self._edit_entry = None

        def _cancel(ev=None):
            entry.destroy()
            self._edit_entry = None

        entry.bind("<Return>", _commit)
        entry.bind("<Escape>", _cancel)
        entry.bind("<FocusOut>", _commit)

    # ── Tab: Líneas ──

    def _build_lines_tab(self, parent):
        if not self._segmentos:
            ctk.CTkLabel(parent, text="No hay timestamps de líneas.",
                         text_color=DIM, font=("Segoe UI", 12)).pack(pady=30)
            return

        scroll = ctk.CTkScrollableFrame(parent, fg_color=INPUT_BG, corner_radius=8)
        scroll.pack(fill="both", expand=True)

        self._line_rows = []
        for i, seg in enumerate(self._segmentos):
            texto = seg.get("texto", seg.get("linea", ""))
            row = ctk.CTkFrame(scroll, fg_color=DARK if i % 2 == 0 else CARD,
                               corner_radius=4)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=f"{i+1}", width=30, font=("Consolas", 10),
                         text_color=DIM).pack(side="left", padx=4)

            ctk.CTkLabel(row, text=texto, font=("Segoe UI", 11),
                         text_color="#ffffff", anchor="w",
                         wraplength=400).pack(side="left", padx=4, fill="x", expand=True)

            s_var = ctk.StringVar(value=f"{seg.get('inicio', 0):.3f}")
            ctk.CTkEntry(row, textvariable=s_var, width=80, height=24,
                         font=("Consolas", 10), fg_color=INPUT_BG,
                         border_width=1, border_color="#2a2a4e").pack(side="left", padx=2)

            e_var = ctk.StringVar(value=f"{seg.get('fin', 0):.3f}")
            ctk.CTkEntry(row, textvariable=e_var, width=80, height=24,
                         font=("Consolas", 10), fg_color=INPUT_BG,
                         border_width=1, border_color="#2a2a4e").pack(side="left", padx=2)

            self._line_rows.append((s_var, e_var))

    # ── Tab: IA Sync ──

    def _build_ai_tab(self, parent):
        # Explicación
        info = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        info.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(info, text="Sincronización con IA",
                     font=("Segoe UI", 14, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(info, text="Usa una IA para analizar el audio y mejorar la\n"
                     "sincronización de los timestamps automáticamente.",
                     font=("Segoe UI", 11), text_color=DIM,
                     justify="left").pack(anchor="w", padx=12, pady=(0, 8))

        # Proveedor de IA
        config_frame = ctk.CTkFrame(parent, fg_color="transparent")
        config_frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(config_frame, text="Proveedor:", font=("Segoe UI", 11),
                     text_color=DIM).grid(row=0, column=0, padx=4, pady=4, sticky="w")

        self._ai_provider = ctk.StringVar(value="Claude Code (Terminal)")
        providers = ["Claude Code (Terminal)", "Claude API", "OpenAI API", "Whisper (re-run)"]
        ctk.CTkComboBox(config_frame, variable=self._ai_provider,
                        values=providers, width=220, height=30,
                        fg_color=INPUT_BG, border_color="#2a2a4e",
                        dropdown_fg_color=CARD,
                        command=self._on_provider_change).grid(row=0, column=1, padx=4, pady=4)

        # API Key (oculto por defecto)
        ctk.CTkLabel(config_frame, text="API Key:", font=("Segoe UI", 11),
                     text_color=DIM).grid(row=1, column=0, padx=4, pady=4, sticky="w")

        self._api_key_var = ctk.StringVar()
        self._api_key_entry = ctk.CTkEntry(config_frame, textvariable=self._api_key_var,
                                            width=220, height=30, show="*",
                                            fg_color=INPUT_BG, border_width=1,
                                            border_color="#2a2a4e",
                                            placeholder_text="sk-... (opcional)")
        self._api_key_entry.grid(row=1, column=1, padx=4, pady=4)

        # Prompt personalizado
        ctk.CTkLabel(config_frame, text="Instrucciones:", font=("Segoe UI", 11),
                     text_color=DIM).grid(row=2, column=0, padx=4, pady=4, sticky="nw")

        self._prompt_text = ctk.CTkTextbox(config_frame, width=400, height=100,
                                            fg_color=INPUT_BG, font=("Consolas", 10),
                                            corner_radius=6, border_width=1,
                                            border_color="#2a2a4e")
        self._prompt_text.grid(row=2, column=1, padx=4, pady=4, columnspan=2, sticky="ew")
        self._prompt_text.insert("1.0",
            "Analiza el audio y los timestamps existentes.\n"
            "Mejora la sincronización palabra por palabra.\n"
            "Asegúrate de que cada palabra coincida exactamente con cuando se canta.")

        config_frame.columnconfigure(1, weight=1)

        # Botón ejecutar
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=8)

        self._ai_btn = ctk.CTkButton(btn_frame, text="Ejecutar Sincronización IA",
                                      width=250, height=40,
                                      fg_color=ACCENT, hover_color=ACCENT_H,
                                      font=("Segoe UI", 12, "bold"),
                                      command=self._run_ai_sync)
        self._ai_btn.pack(side="left", pady=4, padx=(0, 8))

        self._ai_cancel_btn = ctk.CTkButton(btn_frame, text="Cancelar", width=80, height=40,
                                             fg_color="#2a2a4a", hover_color=ACCENT,
                                             font=("Segoe UI", 11),
                                             command=self._cancel_ai, state="disabled")
        self._ai_cancel_btn.pack(side="left", pady=4)

        # Spinner
        self._ai_spinner = SpinnerLabel(btn_frame, base_text="Procesando")
        self._ai_spinner.pack(side="left", padx=12)

        self._ai_process = None  # referencia al Popen activo

        # Log de IA
        self._ai_log = ctk.CTkTextbox(parent, height=150, font=("Consolas", 9),
                                       fg_color="#080810", text_color=GREEN,
                                       corner_radius=8, border_width=1,
                                       border_color="#1a1a2a")
        self._ai_log.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._ai_log.configure(state="disabled")

        self._on_provider_change(self._ai_provider.get())

    def _on_provider_change(self, provider):
        """Muestra/oculta API key según el proveedor."""
        needs_key = provider in ("Claude API", "OpenAI API")
        state = "normal" if needs_key else "disabled"
        self._api_key_entry.configure(state=state)
        if not needs_key:
            self._api_key_var.set("")

    # ── Acciones de edición ──

    def _shift_all(self, delta):
        """Desplaza todos los timestamps por delta segundos."""
        if hasattr(self, '_tree'):
            for item in self._tree.get_children():
                try:
                    s = max(0, float(self._tree.set(item, "inicio")) + delta)
                    e = max(s + 0.01, float(self._tree.set(item, "fin")) + delta)
                    self._tree.set(item, "inicio", f"{s:.3f}")
                    self._tree.set(item, "fin", f"{e:.3f}")
                    self._tree.set(item, "duracion", f"{e - s:.3f}s")
                    idx = int(item)
                    self._palabras[idx]["inicio"] = s
                    self._palabras[idx]["fin"] = e
                except (ValueError, IndexError):
                    pass

    def _autofix_gaps(self):
        """Corrige gaps negativos o solapamientos entre palabras consecutivas."""
        if not hasattr(self, '_tree'):
            return
        items = self._tree.get_children()
        fixed = 0
        for i in range(1, len(items)):
            try:
                prev_end = float(self._tree.set(items[i-1], "fin"))
                curr_start = float(self._tree.set(items[i], "inicio"))
                if curr_start < prev_end:
                    mid = (prev_end + curr_start) / 2
                    self._tree.set(items[i-1], "fin", f"{mid:.3f}")
                    self._tree.set(items[i], "inicio", f"{mid:.3f}")
                    # Update durations
                    prev_s = float(self._tree.set(items[i-1], "inicio"))
                    curr_e = float(self._tree.set(items[i], "fin"))
                    self._tree.set(items[i-1], "duracion", f"{mid - prev_s:.3f}s")
                    self._tree.set(items[i], "duracion", f"{curr_e - mid:.3f}s")
                    self._palabras[i-1]["fin"] = mid
                    self._palabras[i]["inicio"] = mid
                    fixed += 1
            except (ValueError, IndexError):
                pass

        self._ai_log_msg(f"Autofix: {fixed} solapamientos corregidos")

    # ── IA Sync ──

    def _run_ai_sync(self):
        provider = self._ai_provider.get()
        self._ai_btn.configure(state="disabled", text="Sincronizando...")
        self._ai_cancel_btn.configure(state="normal")
        self._ai_spinner.start(f"Ejecutando {provider}")

        thread = threading.Thread(target=self._ai_sync_thread,
                                  args=(provider,), daemon=True)
        thread.start()

    def _cancel_ai(self):
        """Cancela el proceso de IA en curso."""
        if self._ai_process and self._ai_process.poll() is None:
            self._ai_process.kill()
            self._ai_log_msg("Proceso cancelado por el usuario.")
        self._ai_spinner.stop("Cancelado")
        self._ai_btn.configure(state="normal", text="Ejecutar Sincronización IA")
        self._ai_cancel_btn.configure(state="disabled")

    def _ai_sync_thread(self, provider):
        try:
            if provider == "Claude Code (Terminal)":
                self._sync_with_claude_code()
            elif provider == "Claude API":
                self._sync_with_claude_api()
            elif provider == "OpenAI API":
                self._sync_with_openai_api()
            elif provider == "Whisper (re-run)":
                self._sync_with_whisper()
        except Exception as ex:
            self._ai_log_msg(f"ERROR: {ex}")
        finally:
            def _done():
                self._ai_spinner.stop("")
                self._ai_btn.configure(state="normal", text="Ejecutar Sincronización IA")
                self._ai_cancel_btn.configure(state="disabled")
            self.after(0, _done)

    def _sync_with_claude_code(self):
        """Ejecuta Claude Code en terminal para mejorar timestamps."""
        self._ai_log_msg("Ejecutando Claude Code...")

        # Verificar que claude está disponible
        claude_cmd = self._find_claude_cmd()
        if not claude_cmd:
            self._ai_log_msg("ERROR: Claude Code no encontrado en PATH.\n"
                             "Instálalo con: npm install -g @anthropic-ai/claude-code")
            return

        self._ai_log_msg(f"Usando: {claude_cmd}")

        # Guardar timestamps actuales a un archivo temporal para que Claude lo lea
        ts_json = self._build_current_json()
        ts_temp = os.path.join(os.path.dirname(self._audio_path), "_sync_temp.json")
        with open(ts_temp, "w", encoding="utf-8") as f:
            json.dump(ts_json, f, ensure_ascii=False, indent=2)

        prompt_extra = self._prompt_text.get("1.0", "end").strip()

        # Prompt detallado que le dice exactamente qué hacer
        prompt = (
            f"TAREA: Mejorar la sincronización de timestamps de una canción.\n\n"
            f"ARCHIVOS:\n"
            f"- Audio: {self._audio_path}\n"
            f"- Timestamps actuales: {ts_temp}\n\n"
            f"INSTRUCCIONES:\n"
            f"1. Lee el archivo de timestamps con Read tool\n"
            f"2. Usa Whisper para re-analizar el audio y obtener timestamps precisos "
            f"palabra por palabra. Ejecuta este código Python:\n"
            f"   import whisper; model = whisper.load_model('base'); "
            f"result = model.transcribe(r'{self._audio_path}', language='es', "
            f"word_timestamps=True)\n"
            f"3. Compara los timestamps de Whisper con los existentes\n"
            f"4. Genera un JSON corregido con el formato exacto:\n"
            f'   {{"palabras": [{{"palabra": "texto", "inicio": 0.0, "fin": 0.5}}, ...], '
            f'"segmentos": [...]}}\n'
            f"5. Escribe el resultado en: {ts_temp}\n\n"
            f"CONTEXTO ADICIONAL DEL USUARIO:\n{prompt_extra}\n\n"
            f"IMPORTANTE: Escribe el JSON corregido directamente en {ts_temp}. "
            f"No pidas confirmación, solo hazlo."
        )

        self._ai_log_msg("Enviando prompt con instrucciones completas...")
        self._ai_log_msg(f"Timestamps temp: {ts_temp}")

        try:
            # Usar --allowedTools para dar permisos y evitar que pregunte
            cmd = [
                claude_cmd, "-p", prompt,
                "--allowedTools", "Read,Write,Bash",
                "--output-format", "text",
            ]

            # Ejecutar con Popen para leer output en tiempo real
            self._ai_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=os.path.dirname(self._audio_path) or ".",
            )

            process = self._ai_process
            output_lines = []
            for line in iter(process.stdout.readline, ""):
                line = line.rstrip()
                if line:
                    output_lines.append(line)
                    self._ai_log_msg(line[:200])

            process.wait(timeout=300)
            output = "\n".join(output_lines)

            self._ai_log_msg(f"Proceso terminado (código: {process.returncode})")
            self._ai_log_msg(f"Respuesta: {len(output)} chars")

            # Claude debería haber escrito el resultado en ts_temp
            # Intentar leer el archivo actualizado
            if os.path.isfile(ts_temp):
                try:
                    with open(ts_temp, "r", encoding="utf-8") as f:
                        updated = json.load(f)
                    if isinstance(updated, dict) and "palabras" in updated:
                        new_words = updated["palabras"]
                        if new_words and len(new_words) > 0:
                            self._ai_log_msg(f"Timestamps actualizados: {len(new_words)} palabras")
                            self._palabras = new_words
                            self._segmentos = updated.get("segmentos", self._segmentos)
                            self.after(0, self._rebuild_words_tab)

                            # Limpiar temp
                            try:
                                os.remove(ts_temp)
                            except OSError:
                                pass
                            return
                except (json.JSONDecodeError, KeyError):
                    pass

            # Fallback: intentar parsear del output directo
            self._ai_log_msg("Intentando parsear respuesta directa...")
            if output.strip():
                self._parse_ai_response(output)
            else:
                self._ai_log_msg("No se recibió respuesta útil.")

            # Limpiar temp
            try:
                os.remove(ts_temp)
            except OSError:
                pass

        except subprocess.TimeoutExpired:
            self._ai_log_msg("ERROR: Timeout (5 min).")
            process.kill()
        except FileNotFoundError:
            self._ai_log_msg("ERROR: No se pudo ejecutar Claude Code.")

    def _sync_with_claude_api(self):
        """Usa Claude API directamente."""
        api_key = self._api_key_var.get().strip()
        if not api_key:
            # Buscar en variables de entorno
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            self._ai_log_msg("ERROR: Necesitas una API key de Anthropic.\n"
                             "Ingresa tu key o define ANTHROPIC_API_KEY en el entorno.")
            return

        self._ai_log_msg("Conectando con Claude API...")

        try:
            import anthropic
        except ImportError:
            self._ai_log_msg("ERROR: pip install anthropic")
            return

        ts_json = self._build_current_json()
        prompt_extra = self._prompt_text.get("1.0", "end").strip()

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    f"Estos son timestamps de sincronización de una canción.\n"
                    f"```json\n{json.dumps(ts_json, ensure_ascii=False, indent=2)[:3000]}\n```\n\n"
                    f"{prompt_extra}\n\n"
                    f"Responde SOLO con el JSON corregido. Sin explicaciones adicionales."
                )
            }]
        )

        output = msg.content[0].text.strip()
        self._ai_log_msg(f"Respuesta: {len(output)} chars")
        self._parse_ai_response(output)

    def _sync_with_openai_api(self):
        """Usa OpenAI API."""
        api_key = self._api_key_var.get().strip()
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self._ai_log_msg("ERROR: Necesitas una API key de OpenAI.")
            return

        self._ai_log_msg("Conectando con OpenAI API...")

        try:
            import openai
        except ImportError:
            self._ai_log_msg("ERROR: pip install openai")
            return

        ts_json = self._build_current_json()
        prompt_extra = self._prompt_text.get("1.0", "end").strip()

        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": (
                    f"Estos son timestamps de sincronización de una canción.\n"
                    f"```json\n{json.dumps(ts_json, ensure_ascii=False, indent=2)[:3000]}\n```\n\n"
                    f"{prompt_extra}\n\n"
                    f"Responde SOLO con el JSON corregido. Sin explicaciones."
                )
            }],
            max_tokens=4096,
        )

        output = resp.choices[0].message.content.strip()
        self._ai_log_msg(f"Respuesta: {len(output)} chars")
        self._parse_ai_response(output)

    def _sync_with_whisper(self):
        """Re-ejecuta Whisper para regenerar timestamps."""
        if not self._audio_path or not os.path.isfile(self._audio_path):
            self._ai_log_msg("ERROR: No hay audio.")
            return

        self._ai_log_msg("Re-ejecutando Whisper...")

        from app.config import whisper_generar_timestamps
        res = whisper_generar_timestamps(self._audio_path, modelo="base", idioma="es")

        if "palabras" in res:
            self._palabras = res["palabras"]
            self._segmentos = res.get("segmentos", [])
            self._ai_log_msg(f"{len(self._palabras)} palabras detectadas")

            # Guardar
            with open(self._ts_path, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
            self._ai_log_msg(f"Guardado en {os.path.basename(self._ts_path)}")

            # Reconstruir UI
            self.after(0, self._rebuild_words_tab)
        else:
            self._ai_log_msg("ERROR: Whisper no retornó palabras.")

    # ── Utilidades ──

    def _find_claude_cmd(self):
        """Busca el ejecutable de Claude Code."""
        import shutil
        # Buscar en PATH
        cmd = shutil.which("claude")
        if cmd:
            return cmd
        # Rutas comunes en Windows
        for p in [
            os.path.expanduser("~\\.claude\\local\\claude.EXE"),
            os.path.expanduser("~\\.claude\\local\\claude.exe"),
            os.path.expanduser("~\\AppData\\Local\\bin\\claude.EXE"),
            os.path.expanduser("~\\AppData\\Local\\bin\\claude.exe"),
            os.path.expanduser("~\\AppData\\Roaming\\npm\\claude.cmd"),
            os.path.expanduser("~\\AppData\\Roaming\\npm\\claude"),
            "C:\\Users\\rober\\.local\\bin\\claude.EXE",
        ]:
            if os.path.isfile(p):
                return p
        return None

    def _build_current_json(self):
        """Construye JSON con los valores actuales de la UI."""
        if hasattr(self, '_tree') and self._tree.get_children():
            palabras = []
            for item in self._tree.get_children():
                try:
                    palabras.append({
                        "palabra": self._tree.set(item, "palabra"),
                        "inicio": float(self._tree.set(item, "inicio")),
                        "fin": float(self._tree.set(item, "fin")),
                    })
                except ValueError:
                    pass
            return {"palabras": palabras, "segmentos": self._segmentos}

        if self._line_rows:
            segmentos = []
            for i, (s_var, e_var) in enumerate(self._line_rows):
                texto = self._segmentos[i].get("texto", self._segmentos[i].get("linea", ""))
                try:
                    segmentos.append({
                        "texto": texto,
                        "inicio": float(s_var.get()),
                        "fin": float(e_var.get()),
                    })
                except ValueError:
                    pass
            return segmentos

        return self._raw_data or {}

    def _parse_ai_response(self, text):
        """Intenta extraer JSON de la respuesta de IA y actualizar la UI."""
        # Buscar bloque JSON
        import re
        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)

        # Limpiar
        text = text.strip()
        if not text.startswith(("{", "[")):
            # Buscar inicio de JSON
            for ch in ("{", "["):
                idx = text.find(ch)
                if idx >= 0:
                    text = text[idx:]
                    break

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            self._ai_log_msg(f"ERROR: No se pudo parsear JSON: {e}")
            self._ai_log_msg(f"Respuesta:\n{text[:500]}")
            return

        # Actualizar datos
        if isinstance(data, dict) and "palabras" in data:
            new_words = data["palabras"]
            items = self._tree.get_children() if hasattr(self, '_tree') else []
            if len(new_words) == len(items):
                for i, w in enumerate(new_words):
                    item = items[i]
                    self._tree.set(item, "inicio", f"{w.get('inicio', 0):.3f}")
                    self._tree.set(item, "fin", f"{w.get('fin', 0):.3f}")
                    dur = w.get("fin", 0) - w.get("inicio", 0)
                    self._tree.set(item, "duracion", f"{dur:.3f}s")
                self._palabras = new_words
                self._ai_log_msg(f"Actualizado: {len(new_words)} palabras")
            else:
                self._ai_log_msg(f"WARN: IA retornó {len(new_words)} palabras, "
                                 f"esperaba {len(items)}")
                self._palabras = new_words
                self.after(0, self._rebuild_words_tab)
        elif isinstance(data, list):
            self._ai_log_msg(f"Recibido: {len(data)} items")
        else:
            self._ai_log_msg("WARN: Formato de respuesta no reconocido")

    def _rebuild_words_tab(self):
        """Reconstruye la pestaña de palabras con datos actualizados."""
        tab = self._tabs.tab("Palabras")
        for w in tab.winfo_children():
            w.destroy()
        self._rows = []
        self._build_words_tab(tab)

    def _ai_log_msg(self, msg):
        """Escribe mensaje en el log de IA."""
        def _write():
            self._ai_log.configure(state="normal")
            self._ai_log.insert("end", msg + "\n")
            self._ai_log.see("end")
            self._ai_log.configure(state="disabled")
        self.after(0, _write)

    # ── Guardar / Exportar ──

    def _save(self):
        """Guarda los timestamps editados al archivo original."""
        data = self._build_current_json()

        with open(self._ts_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._ai_log_msg(f"Guardado: {os.path.basename(self._ts_path)}")

        if self._on_save:
            self._on_save(data)

        messagebox.showinfo("Sync Editor", f"Timestamps guardados en:\n{self._ts_path}",
                            parent=self)

    def _export(self):
        """Exporta a un archivo JSON nuevo."""
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar timestamps",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=os.path.dirname(self._ts_path) if self._ts_path else None,
        )
        if not path:
            return

        data = self._build_current_json()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._ai_log_msg(f"Exportado: {os.path.basename(path)}")
