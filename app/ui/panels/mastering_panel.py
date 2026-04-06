"""
MasteringPanel — UI para Dudiver Master.
Análisis automático + procesamiento + reporte.
"""

import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.config import ACCENT, ACCENT_H, GOLD, GREEN, DIM, CARD, INPUT_BG, DARK
from app.core.mastering import MasteringEngine


PRESET_LABELS = {
    "auto":         "Auto (recomendado)",
    "warm_air":     "Warm + Air",
    "warm_punchy":  "Warm Punchy",
    "bright_tame":  "Bright Tame",
    "balanced":     "Balanced",
}
PRESET_REV = {v: k for k, v in PRESET_LABELS.items()}


class MasteringPanel(ctk.CTkFrame):
    def __init__(self, parent, *, log_cb=None, status_cb=None):
        super().__init__(parent, fg_color=DARK, corner_radius=0)
        self._log = log_cb or (lambda msg: None)
        self._status = status_cb or (lambda msg, pct=None: None)
        self.engine = MasteringEngine()
        self.analysis = None
        self._busy = False

        self._build()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # ── Columna izquierda: input + controles ────────────────────────────
        left = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        ctk.CTkLabel(left, text="DUDIVER MASTER",
                     font=("Segoe UI Black", 18),
                     text_color=ACCENT).pack(pady=(16, 2), padx=16, anchor="w")
        ctk.CTkLabel(left, text="Análisis + mastering automático",
                     font=("Segoe UI", 10), text_color=DIM
                     ).pack(padx=16, anchor="w")

        ctk.CTkFrame(left, fg_color=ACCENT, height=2,
                     corner_radius=0).pack(fill="x", padx=16, pady=(8, 12))

        # Audio in
        ctk.CTkLabel(left, text="Audio de entrada",
                     font=("Segoe UI Semibold", 11),
                     text_color="white").pack(padx=16, anchor="w")

        self.in_var = ctk.StringVar(value="")
        in_row = ctk.CTkFrame(left, fg_color="transparent")
        in_row.pack(fill="x", padx=16, pady=(4, 8))
        self.in_entry = ctk.CTkEntry(in_row, textvariable=self.in_var,
                                     fg_color=INPUT_BG, border_color="#2a2a4a",
                                     height=32, font=("Segoe UI", 10))
        self.in_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(in_row, text="\U0001f4c2", width=36, height=32,
                      font=("Segoe UI Emoji", 14),
                      fg_color="#2a2a4a", hover_color=ACCENT,
                      command=self._pick_in).pack(side="left", padx=(4, 0))

        # Audio out
        ctk.CTkLabel(left, text="Salida (master)",
                     font=("Segoe UI Semibold", 11),
                     text_color="white").pack(padx=16, anchor="w")

        self.out_var = ctk.StringVar(value="")
        out_row = ctk.CTkFrame(left, fg_color="transparent")
        out_row.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkEntry(out_row, textvariable=self.out_var,
                     fg_color=INPUT_BG, border_color="#2a2a4a",
                     height=32, font=("Segoe UI", 10)
                     ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(out_row, text="\U0001f4be", width=36, height=32,
                      font=("Segoe UI Emoji", 14),
                      fg_color="#2a2a4a", hover_color=ACCENT,
                      command=self._pick_out).pack(side="left", padx=(4, 0))

        # Botón analizar
        self.analyze_btn = ctk.CTkButton(
            left, text="\U0001f50d  ANALIZAR", height=40,
            font=("Segoe UI Black", 12),
            fg_color="#2a2a4a", hover_color=ACCENT_H,
            text_color=GOLD, corner_radius=10,
            command=self._on_analyze)
        self.analyze_btn.pack(fill="x", padx=16, pady=(4, 8))

        # Preset
        ctk.CTkLabel(left, text="Preset",
                     font=("Segoe UI Semibold", 11),
                     text_color="white").pack(padx=16, anchor="w", pady=(8, 2))
        self.preset_var = ctk.StringVar(value=PRESET_LABELS["auto"])
        ctk.CTkOptionMenu(
            left, values=list(PRESET_LABELS.values()),
            variable=self.preset_var,
            fg_color=INPUT_BG, button_color="#2a2a4a",
            button_hover_color=ACCENT, height=32
        ).pack(fill="x", padx=16, pady=(0, 8))

        # Target LUFS
        lufs_label_row = ctk.CTkFrame(left, fg_color="transparent")
        lufs_label_row.pack(fill="x", padx=16, pady=(8, 0))
        ctk.CTkLabel(lufs_label_row, text="LUFS objetivo",
                     font=("Segoe UI Semibold", 11),
                     text_color="white").pack(side="left")
        self.lufs_value_lbl = ctk.CTkLabel(
            lufs_label_row, text="-10.0", font=("Segoe UI Black", 13),
            text_color=ACCENT)
        self.lufs_value_lbl.pack(side="right")

        self.target_var = ctk.DoubleVar(value=-10.0)
        self.lufs_slider = ctk.CTkSlider(
            left, from_=-16, to=-7, number_of_steps=18,
            variable=self.target_var, button_color=ACCENT,
            button_hover_color=ACCENT_H, progress_color=ACCENT,
            command=self._on_slider)
        self.lufs_slider.pack(fill="x", padx=16, pady=(4, 12))

        # Botón masterizar
        self.master_btn = ctk.CTkButton(
            left, text="\u2728  MASTERIZAR", height=46,
            font=("Segoe UI Black", 14),
            fg_color=ACCENT, hover_color=ACCENT_H,
            corner_radius=12, command=self._on_master)
        self.master_btn.pack(fill="x", padx=16, pady=(4, 16))

        # Progress
        self.prog_label = ctk.CTkLabel(
            left, text="", font=("Segoe UI", 10),
            text_color=DIM, anchor="w")
        self.prog_label.pack(fill="x", padx=16)
        self.prog = ctk.CTkProgressBar(
            left, height=8, corner_radius=4,
            fg_color=INPUT_BG, progress_color=ACCENT)
        self.prog.pack(fill="x", padx=16, pady=(2, 16))
        self.prog.set(0)

        # ── Columna derecha: reporte ────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

        ctk.CTkLabel(right, text="REPORTE",
                     font=("Segoe UI Black", 18),
                     text_color=GOLD).pack(pady=(16, 2), padx=16, anchor="w")
        ctk.CTkLabel(right, text="Análisis técnico y resultado del master",
                     font=("Segoe UI", 10), text_color=DIM
                     ).pack(padx=16, anchor="w")
        ctk.CTkFrame(right, fg_color=GOLD, height=2,
                     corner_radius=0).pack(fill="x", padx=16, pady=(8, 12))

        self.report = ctk.CTkTextbox(
            right, fg_color="#080810", text_color="#cfd3ff",
            font=("Consolas", 10), corner_radius=8,
            border_width=1, border_color="#1a1a2a", wrap="word")
        self.report.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._set_report(
            "Esperando archivo…\n\n"
            "1) Selecciona un audio (WAV preferido)\n"
            "2) Pulsa ANALIZAR\n"
            "3) Ajusta preset y LUFS objetivo (o deja Auto)\n"
            "4) Pulsa MASTERIZAR"
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _pick_in(self):
        path = filedialog.askopenfilename(
            title="Audio de entrada",
            filetypes=[("Audio", "*.wav *.flac *.mp3 *.aiff *.ogg"),
                       ("Todos", "*.*")])
        if path:
            self.in_var.set(path)
            if not self.out_var.get():
                base, ext = os.path.splitext(path)
                self.out_var.set(f"{base}_MASTER.wav")

    def _pick_out(self):
        path = filedialog.asksaveasfilename(
            title="Guardar master",
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav")])
        if path:
            self.out_var.set(path)

    def _on_slider(self, val):
        self.lufs_value_lbl.configure(text=f"{float(val):.1f}")

    def _set_report(self, text):
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.configure(state="disabled")

    def _append_report(self, text):
        self.report.configure(state="normal")
        self.report.insert("end", text)
        self.report.see("end")
        self.report.configure(state="disabled")

    def _set_progress(self, msg, pct):
        def _a():
            self.prog_label.configure(text=msg)
            self.prog.set(pct / 100.0)
            self._status(msg, pct)
        self.after(0, _a)

    def _set_busy(self, busy: bool):
        self._busy = busy
        state = "disabled" if busy else "normal"
        for w in (self.analyze_btn, self.master_btn,
                  self.in_entry, self.lufs_slider):
            try:
                w.configure(state=state)
            except Exception:
                pass

    # ── Acciones ────────────────────────────────────────────────────────────

    def _on_analyze(self):
        if self._busy:
            return
        path = self.in_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("Audio", "Selecciona un archivo de audio válido.")
            return
        self._set_busy(True)
        self._set_report(f"Analizando: {os.path.basename(path)}\n\n")

        def work():
            try:
                info = self.engine.analyze(path, progress_cb=self._set_progress)
                self.analysis = info
                self.after(0, lambda: self._show_analysis(info))
            except Exception as e:
                self.after(0, lambda: self._show_error("Análisis falló", e))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=work, daemon=True).start()

    def _show_analysis(self, info):
        # Actualizar slider con recomendado
        self.target_var.set(info.recommended_target_lufs)
        self.lufs_value_lbl.configure(text=f"{info.recommended_target_lufs:.1f}")
        # Actualizar preset
        rec_label = PRESET_LABELS.get(info.recommended_preset, PRESET_LABELS["auto"])
        self.preset_var.set(rec_label)

        bands = info.bands_db
        text = (
            f"━━━ ANÁLISIS ━━━\n"
            f"Archivo:    {os.path.basename(info.path)}\n"
            f"Duración:   {info.duration_sec:.1f}s\n"
            f"Sample:     {info.sample_rate} Hz · {info.channels}ch\n"
            f"\n"
            f"━━━ LOUDNESS ━━━\n"
            f"LUFS integ:  {info.lufs_integrated:+.2f}\n"
            f"LUFS short:  {info.lufs_short_term:+.2f}\n"
            f"Peak:        {info.peak_dbfs:+.2f} dBFS\n"
            f"True peak:   {info.true_peak_dbfs:+.2f} dBFS\n"
            f"RMS:         {info.rms_dbfs:+.2f} dBFS\n"
            f"Crest:       {info.crest_factor_db:.2f} dB\n"
            f"DC offset:   {info.dc_offset:+.5f}\n"
            f"\n"
            f"━━━ ESPECTRO ━━━\n"
            f"BPM:         {info.bpm:.1f}\n"
            f"Centroide:   {info.spectral_centroid_hz:.0f} Hz\n"
            f"Carácter:    {info.character.upper()}\n"
            f"\n"
            f"━━━ BANDAS (dB rel) ━━━\n"
            f"Sub      (20-60):     {bands['sub']:+.2f}\n"
            f"Bass     (60-200):    {bands['bass']:+.2f}\n"
            f"Lowmid   (200-500):   {bands['lowmid']:+.2f}\n"
            f"Mid      (500-2k):    {bands['mid']:+.2f}\n"
            f"Highmid  (2k-5k):     {bands['highmid']:+.2f}\n"
            f"Presence (5k-10k):    {bands['presence']:+.2f}\n"
            f"Air      (10k-20k):   {bands['air']:+.2f}\n"
            f"\n"
            f"━━━ DIAGNÓSTICO ━━━\n"
        )
        if info.deficiencies:
            for d in info.deficiencies:
                text += f"  · {d}\n"
        else:
            text += "  · sin problemas detectados\n"
        text += (
            f"\n━━━ RECOMENDACIÓN ━━━\n"
            f"Preset:        {PRESET_LABELS.get(info.recommended_preset, info.recommended_preset)}\n"
            f"LUFS objetivo: {info.recommended_target_lufs:+.1f}\n"
            f"\nListo para masterizar →\n"
        )
        self._set_report(text)
        self._log(f"[Master] Análisis: {info.character} · {info.lufs_integrated:+.2f} LUFS · {info.bpm:.0f} BPM")

    def _on_master(self):
        if self._busy:
            return
        in_path = self.in_var.get().strip()
        out_path = self.out_var.get().strip()
        if not in_path or not os.path.isfile(in_path):
            messagebox.showwarning("Audio", "Selecciona un archivo de audio válido.")
            return
        if not out_path:
            base, _ = os.path.splitext(in_path)
            out_path = f"{base}_MASTER.wav"
            self.out_var.set(out_path)

        # Si no hay análisis, hacer uno rápido primero
        if self.analysis is None or self.analysis.path != in_path:
            self._set_report("Análisis previo necesario, ejecutando…\n\n")

        target = float(self.target_var.get())
        preset_key = PRESET_REV.get(self.preset_var.get(), "auto")

        self._set_busy(True)

        def work():
            try:
                if self.analysis is None or self.analysis.path != in_path:
                    info = self.engine.analyze(in_path, progress_cb=self._set_progress)
                    self.analysis = info
                else:
                    info = self.analysis

                chain = self.engine.chain_by_name(preset_key, info, target)
                result = self.engine.master(
                    in_path, out_path, chain,
                    target_lufs=target,
                    progress_cb=self._set_progress)
                self.after(0, lambda: self._show_master_result(result, preset_key))
            except Exception as e:
                self.after(0, lambda: self._show_error("Mastering falló", e))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=work, daemon=True).start()

    def _show_master_result(self, r, preset_key):
        text = (
            f"━━━ MASTER COMPLETADO ━━━\n"
            f"Salida:      {os.path.basename(r.output_path)}\n"
            f"Carpeta:     {os.path.dirname(r.output_path)}\n"
            f"Duración:    {r.duration_sec:.1f}s\n"
            f"Preset:      {PRESET_LABELS.get(preset_key, preset_key)}\n"
            f"\n"
            f"━━━ ANTES → DESPUÉS ━━━\n"
            f"LUFS:    {r.lufs_in:+.2f}  →  {r.lufs_out:+.2f}   (objetivo {r.target_lufs:+.1f})\n"
            f"Peak:    {r.peak_in_dbfs:+.2f}  →  {r.peak_out_dbfs:+.2f}  dBFS\n"
            f"Δ Gain:  {r.gain_applied_db:+.2f}  LU\n"
            f"\n"
            f"━━━ CADENA APLICADA ━━━\n"
        )
        for i, p in enumerate(r.chain_summary, 1):
            name = p.pop("plugin")
            params = " · ".join(f"{k}={v}" for k, v in p.items())
            text += f"  {i:>2}. {name:<16} {params}\n"
        text += "\n✓ Master listo en disco.\n"
        self._set_report(text)
        self._log(f"[Master] OK: {os.path.basename(r.output_path)} · {r.lufs_out:+.2f} LUFS")
        self._set_progress("Master completado", 100)

    def _show_error(self, title, e):
        self._append_report(f"\n\n✗ ERROR: {e}\n")
        self._log(f"[Master] ERROR: {e}")
        messagebox.showerror(title, str(e))
        self._set_progress("Error", 0)
