"""Ventana de ayuda — guía de uso bilingüe (ES/EN)."""

import os
import customtkinter as ctk

from app.config import ACCENT, ACCENT_H, DARK, CARD, DIM, INPUT_BG, GOLD, GREEN

HELP_ES = {
    "title": "Ayuda — Dudiver Visualizer Studio",
    "sections": [
        ("Inicio rápido", [
            "1. Selecciona un archivo de audio (MP3, WAV, FLAC)",
            "2. Escribe o pega la letra de la canción",
            "3. Haz clic en 'Timestamps' para sincronizar con Whisper AI",
            "4. Ajusta la configuración del video",
            "5. Haz clic en 'GENERAR VIDEO'",
        ]),
        ("Modos de video", [
            "Karaoke — Texto estático con efectos de karaoke clásico. "
            "Las líneas se iluminan al cantarse. Incluye partículas, onda, viñeta y glow.",
            "",
            "Kinetic Typography — Animaciones dinámicas palabra por palabra. "
            "Cada palabra aparece con efectos cuando se canta. "
            "Requiere Manim instalado (pip install manim).",
        ]),
        ("Estilos Kinetic", [
            "Wave — Las palabras entran desde abajo con efecto ola",
            "Typewriter — Letras aparecen una por una como máquina de escribir",
            "Zoom Bounce — Las palabras aparecen con zoom y rebote",
            "Slide — Texto entra deslizando desde los lados",
            "Fade & Float — Las palabras aparecen suavemente flotando",
            "Glitch — Efecto de distorsión digital",
            "Bounce Drop — Las palabras caen desde arriba con rebote",
            "Cinematic — Aparición dramática palabra por palabra",
        ]),
        ("Sync Editor (Avanzado)", [
            "Después de generar timestamps, haz clic en 'Sync' para abrir "
            "el editor avanzado donde puedes:",
            "  - Editar manualmente el tiempo de cada palabra",
            "  - Desplazar todos los tiempos (+/- 50ms)",
            "  - Corregir solapamientos automáticamente",
            "  - Re-sincronizar con IA (Claude, OpenAI, Whisper)",
            "",
            "Para IA Sync puedes usar:",
            "  - Claude Code (Terminal) — ejecuta claude en tu terminal",
            "  - Claude API — necesitas una API key de Anthropic",
            "  - OpenAI API — necesitas una API key de OpenAI",
            "  - Whisper (re-run) — vuelve a ejecutar Whisper",
        ]),
        ("Configuración de video", [
            "Tamaño — YouTube (1920x1080), TikTok (1080x1920), Instagram (1080x1080)",
            "FPS — 24, 30, o 60 cuadros por segundo",
            "Colores — Noche, Fuego, Océano, Neón, Oro",
            "Whisper — Modelo de IA para timestamps (tiny/base/small/medium/large)",
            "Duración — Limitar la duración del video",
            "Fuente — Selecciona cualquier fuente instalada en tu sistema",
        ]),
        ("Spot publicitario", [
            "Agrega un segmento promocional al final del video:",
            "  - Texto — Mensaje con subtexto y línea decorativa",
            "  - Imagen — Una imagen que aparece con fade",
            "  - Video — Un clip de video que se reproduce",
        ]),
        ("Fondo transparente (Alpha)", [
            "Activa 'Alpha' para generar video con fondo transparente (WebM/MOV).",
            "Útil para superponer en editores de video como Premiere, DaVinci, etc.",
        ]),
        ("GPU y rendimiento", [
            "En Configuración (⚙) puedes activar aceleración GPU:",
            "  - NVENC para GPUs NVIDIA",
            "  - QSV para GPUs Intel",
            "  - AMF para GPUs AMD",
        ]),
        ("Atajos de teclado", [
            "No hay atajos de teclado configurados actualmente.",
            "Usa los botones de la barra de herramientas.",
        ]),
    ]
}

HELP_EN = {
    "title": "Help — Dudiver Visualizer Studio",
    "sections": [
        ("Quick Start", [
            "1. Select an audio file (MP3, WAV, FLAC)",
            "2. Type or paste the song lyrics",
            "3. Click 'Timestamps' to sync with Whisper AI",
            "4. Adjust video settings",
            "5. Click 'GENERATE VIDEO'",
        ]),
        ("Video Modes", [
            "Karaoke — Static text with classic karaoke effects. "
            "Lines highlight as they are sung. Includes particles, wave, vignette and glow.",
            "",
            "Kinetic Typography — Dynamic word-by-word animations. "
            "Each word appears with effects exactly when it's sung. "
            "Requires Manim installed (pip install manim).",
        ]),
        ("Kinetic Styles", [
            "Wave — Words enter from below with a wave effect",
            "Typewriter — Letters appear one by one like a typewriter",
            "Zoom Bounce — Words appear with zoom and bounce",
            "Slide — Text slides in from the sides",
            "Fade & Float — Words appear softly while floating",
            "Glitch — Digital distortion effect",
            "Bounce Drop — Words drop from above with bounce",
            "Cinematic — Dramatic word-by-word appearance",
        ]),
        ("Sync Editor (Advanced)", [
            "After generating timestamps, click 'Sync' to open "
            "the advanced editor where you can:",
            "  - Manually edit each word's timing",
            "  - Shift all times (+/- 50ms)",
            "  - Auto-fix overlapping timestamps",
            "  - Re-sync with AI (Claude, OpenAI, Whisper)",
            "",
            "For AI Sync you can use:",
            "  - Claude Code (Terminal) — runs claude in your terminal",
            "  - Claude API — requires an Anthropic API key",
            "  - OpenAI API — requires an OpenAI API key",
            "  - Whisper (re-run) — re-runs Whisper detection",
        ]),
        ("Video Settings", [
            "Size — YouTube (1920x1080), TikTok (1080x1920), Instagram (1080x1080)",
            "FPS — 24, 30, or 60 frames per second",
            "Colors — Night, Fire, Ocean, Neon, Gold",
            "Whisper — AI model for timestamps (tiny/base/small/medium/large)",
            "Duration — Limit video duration",
            "Font — Select any font installed on your system",
        ]),
        ("Promo Spot", [
            "Add a promotional segment at the end of the video:",
            "  - Text — Message with subtext and decorative line",
            "  - Image — An image that appears with fade",
            "  - Video — A video clip that plays",
        ]),
        ("Transparent Background (Alpha)", [
            "Enable 'Alpha' to generate video with transparent background (WebM/MOV).",
            "Useful for overlaying in video editors like Premiere, DaVinci, etc.",
        ]),
        ("GPU & Performance", [
            "In Settings (⚙) you can enable GPU acceleration:",
            "  - NVENC for NVIDIA GPUs",
            "  - QSV for Intel GPUs",
            "  - AMF for AMD GPUs",
        ]),
        ("Keyboard Shortcuts", [
            "No keyboard shortcuts are currently configured.",
            "Use the toolbar buttons.",
        ]),
    ]
}


class HelpWindow(ctk.CTkToplevel):
    """Ventana de ayuda bilingüe."""

    def __init__(self, parent):
        super().__init__(parent)
        self.geometry("650x550")
        self.configure(fg_color=DARK)
        self.attributes("-topmost", True)
        self.lift()

        # Icono
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ico = os.path.join(base_dir, "icon.ico")
        if os.path.exists(ico):
            self.after(100, lambda: self.iconbitmap(ico))

        self._lang = "es"
        self._build()

    def _build(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=CARD, height=45, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="?", font=("Segoe UI Bold", 18),
                     text_color=GOLD).pack(side="left", padx=12)

        self._title_label = ctk.CTkLabel(header, text="",
                                          font=("Segoe UI", 14, "bold"),
                                          text_color="white")
        self._title_label.pack(side="left", padx=4)

        # Language toggle
        self._lang_btn = ctk.CTkButton(header, text="EN", width=40, height=28,
                                        fg_color="#2a2a4a", hover_color="#3a3a5a",
                                        font=("Segoe UI Bold", 10),
                                        corner_radius=6,
                                        command=self._toggle_lang)
        self._lang_btn.pack(side="right", padx=12)

        ctk.CTkFrame(self, fg_color=ACCENT, height=2, corner_radius=0).pack(fill="x")

        # Content
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=DARK, corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._render_content()

    def _toggle_lang(self):
        self._lang = "en" if self._lang == "es" else "es"
        self._lang_btn.configure(text="ES" if self._lang == "en" else "EN")
        self._render_content()

    def _render_content(self):
        # Clear
        for w in self._scroll.winfo_children():
            w.destroy()

        data = HELP_ES if self._lang == "es" else HELP_EN
        self.title(data["title"])
        self._title_label.configure(text=data["title"])

        for section_title, lines in data["sections"]:
            # Section header
            sec = ctk.CTkFrame(self._scroll, fg_color=CARD, corner_radius=6)
            sec.pack(fill="x", padx=8, pady=(8, 2))

            ctk.CTkLabel(sec, text=section_title,
                         font=("Segoe UI", 13, "bold"),
                         text_color=ACCENT).pack(anchor="w", padx=12, pady=6)

            # Lines
            content_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
            content_frame.pack(fill="x", padx=20, pady=(0, 4))

            for line in lines:
                if not line:
                    ctk.CTkFrame(content_frame, height=4, fg_color="transparent").pack()
                    continue
                ctk.CTkLabel(content_frame, text=line,
                             font=("Segoe UI", 11),
                             text_color="#cccccc",
                             anchor="w", justify="left",
                             wraplength=560).pack(anchor="w", pady=1)
