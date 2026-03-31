"""
Constantes globales, colores, esquemas, y imports centralizados.
Centraliza todas las imports de lyric_video / generar_timestamps.
"""

import sys
import os

from app.scripts.lyric_video import (
    alinear_letra_con_whisper,
    forzar_letra_sobre_timestamps,
    cargar_timestamps_directos,
    crear_frame_normal,
    crear_frame_alpha,
    Particula,
    cargar_fuente,
    ESQUEMAS,
)
from app.scripts.generar_timestamps import generar_timestamps as whisper_generar_timestamps

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

# Mapeo de nombre GUI → esquema kinetic (mismas keys que ESQUEMAS_GUI)
ESQUEMA_GUI_TO_KINETIC = {
    "Noche": "nocturno",
    "Fuego": "fuego",
    "Oceano": "oceano",
    "Neon": "neon",
    "Oro": "elegante",
}
DURACIONES = {
    "Completo": 0, "8 seg": 8, "15 seg": 15, "30 seg": 30, "1 min": 60,
    "1:30 min": 90, "2 min": 120, "3 min": 180,
}
# Whisper: display label → model name
WHISPER_MODELS = {
    "Rápida": "tiny",
    "Normal": "base",
    "Alta": "small",
    "Máxima": "medium",
}
# Inverso para cargar proyectos guardados con nombre interno
_WHISPER_REV = {v: k for k, v in WHISPER_MODELS.items()}


def whisper_model_name(label):
    """Convierte label de UI ('Normal') a nombre de modelo Whisper ('base')."""
    return WHISPER_MODELS.get(label, label)

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
    "One Word": "oneword",
}

ESQUEMAS_KINETIC_GUI = {
    "Neon": "neon",
    "Fuego": "fuego",
    "Nocturno": "nocturno",
    "Elegante": "elegante",
    "Oceano": "oceano",
}
