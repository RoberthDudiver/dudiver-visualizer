"""Render de un frame de preview — wraps lyric_video calls."""

import os
import random
import numpy as np
from PIL import Image, ImageTk

from app.config import (
    crear_frame_normal,
    crear_frame_alpha,
    Particula,
    ESQUEMAS,
    ESQUEMAS_GUI,
)


def render_preview_frame(*, ancho, alto, timing, t, dur, titulo,
                         fuente, fuente_titulo, fuente_peq,
                         esquema_key, alpha_mode, fondo_path):
    """Renderiza un solo frame de preview y retorna un PIL Image (RGB)."""
    esquema_name = ESQUEMAS_GUI.get(esquema_key, "nocturno")
    esquema = ESQUEMAS.get(esquema_name, ESQUEMAS["nocturno"])

    beat_times = []

    random.seed(42)
    parts = [Particula(ancho, alto) for _ in range(60)]
    for _ in range(int(t * 24)):
        for p in parts:
            p.actualizar(1 / 24, 0)

    # Background
    bg_image = None
    if fondo_path and os.path.isfile(fondo_path):
        ext = os.path.splitext(fondo_path)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".bmp"):
            bg_image = Image.open(fondo_path).resize((ancho, alto), Image.Resampling.LANCZOS)

    if alpha_mode:
        img = crear_frame_alpha(ancho, alto, timing, t, dur,
                                beat_times, fuente, fuente_titulo, titulo)
        base = bg_image.convert("RGBA") if bg_image else Image.new("RGBA", (ancho, alto), (20, 20, 40, 255))
        img = Image.alpha_composite(base, img).convert("RGB")
    else:
        rms_data = (np.zeros(100), list(range(100)))
        img = crear_frame_normal(ancho, alto, timing, t, dur,
                                 beat_times, rms_data, esquema, fuente,
                                 fuente_titulo, fuente_peq, parts, titulo, bg_image)

    # Ensure PIL Image
    if not isinstance(img, Image.Image):
        img = Image.fromarray(img)

    return img
