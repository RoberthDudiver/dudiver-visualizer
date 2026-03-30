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


def _extract_video_frame(video_path, t, ancho, alto):
    """Extrae un frame de un video en el tiempo t (con loop si es más corto).

    Retorna PIL Image RGB redimensionada a (ancho, alto), o None si falla.
    """
    try:
        import cv2
    except ImportError:
        return None

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_dur = total_frames / video_fps if video_fps > 0 else 1

        # Loop si el video es más corto que la canción
        t_video = t % video_dur if video_dur > 0 else 0
        frame_idx = min(int(t_video * video_fps), total_frames - 1)

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return None

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame).resize((ancho, alto), Image.Resampling.LANCZOS)
    except Exception:
        return None


def render_preview_frame(*, ancho, alto, timing, t, dur, titulo,
                         fuente, fuente_titulo, fuente_peq,
                         esquema_key, alpha_mode, fondo_path,
                         lyrics_pos="Centro", lyrics_margin=40, lyrics_extra_y=0,
                         effects=None):
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
        elif ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
            bg_image = _extract_video_frame(fondo_path, t, ancho, alto)

    if alpha_mode:
        img = crear_frame_alpha(ancho, alto, timing, t, dur,
                                beat_times, fuente, fuente_titulo, titulo,
                                lyrics_pos=lyrics_pos, lyrics_margin=lyrics_margin,
                                lyrics_extra_y=lyrics_extra_y, effects=effects)
        base = bg_image.convert("RGBA") if bg_image else Image.new("RGBA", (ancho, alto), (20, 20, 40, 255))
        img = Image.alpha_composite(base, img).convert("RGB")
    else:
        rms_data = (np.zeros(100), list(range(100)))
        img = crear_frame_normal(ancho, alto, timing, t, dur,
                                 beat_times, rms_data, esquema, fuente,
                                 fuente_titulo, fuente_peq, parts, titulo, bg_image,
                                 lyrics_pos=lyrics_pos, lyrics_margin=lyrics_margin,
                                 lyrics_extra_y=lyrics_extra_y, effects=effects)

    # Ensure PIL Image
    if not isinstance(img, Image.Image):
        img = Image.fromarray(img)

    return img
