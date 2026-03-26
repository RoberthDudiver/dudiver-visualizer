"""
Constantes globales, colores, esquemas, y setup de SKILLS_DIR.
Centraliza todas las imports de lyric_video / generar_timestamps.
"""

import sys
import os

# ── Skills dir setup (lyric_video, generar_timestamps) ───────────────────────
SKILLS_DIR = os.path.normpath("C:/Users/rober/.claude/skills/music/scripts")
if SKILLS_DIR not in sys.path:
    sys.path.insert(0, SKILLS_DIR)

from lyric_video import (
    alinear_letra_con_whisper,
    cargar_timestamps_directos,
    crear_frame_normal,
    crear_frame_alpha,
    Particula,
    cargar_fuente,
    ESQUEMAS,
)
from generar_timestamps import generar_timestamps as whisper_generar_timestamps

# ── Theme colors ─────────────────────────────────────────────────────────────
ACCENT = "#e94560"
ACCENT_H = "#ff6b81"
GOLD = "#ffd460"
GREEN = "#4ade80"
DIM = "#7a7a9a"
CARD = "#1a1a2e"
INPUT_BG = "#12122a"
DARK = "#0e0e1a"

# ── Lookups ──────────────────────────────────────────────────────────────────
TAMANOS = {
    "YouTube 1920×1080": (1920, 1080),
    "TikTok 1080×1920": (1080, 1920),
    "Instagram 1080×1080": (1080, 1080),
    "Story 720×1280": (720, 1280),
}
ESQUEMAS_GUI = {
    "Noche": "nocturno", "Fuego": "fuego", "Oceano": "oscuro",
    "Neon": "neon", "Oro": "elegante",
}
DURACIONES = {
    "Completo": 0, "30 seg": 30, "1 min": 60, "1:30 min": 90,
    "2 min": 120, "3 min": 180,
}

# ── Modos de video ────────────────────────────────────────────────────────────
MODOS_VIDEO = ["Karaoke", "Kinetic Typography"]

ESTILOS_KINETIC = {
    "Wave": "wave",
    "Typewriter": "typewriter",
    "Zoom Bounce": "zoom",
    "Slide": "slide",
    "Fade & Float": "fade",
    "Glitch": "glitch",
    "Bounce Drop": "bounce",
    "Cinematic": "cinematic",
}

ESQUEMAS_KINETIC_GUI = {
    "Neon": "neon",
    "Fuego": "fuego",
    "Nocturno": "nocturno",
    "Elegante": "elegante",
    "Oceano": "oceano",
}
