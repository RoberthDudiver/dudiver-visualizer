"""Gestion de timestamps: cargar existentes, generar nuevos, fallback."""

import os
import json

from app.config import (
    alinear_letra_con_whisper,
    cargar_timestamps_directos,
    whisper_generar_timestamps,
)


def get_ts_path(audio_path):
    """Retorna la ruta del archivo de timestamps para un audio dado."""
    if not audio_path:
        return None
    return os.path.splitext(audio_path)[0] + "_timestamps.json"


def load_existing(ts_path, lines):
    """Intenta cargar timestamps existentes. Retorna lista de lineas o None."""
    if not ts_path or not os.path.isfile(ts_path):
        return None
    try:
        with open(ts_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, list):
            return cargar_timestamps_directos(ts_path)
        elif isinstance(d, dict) and "palabras" in d:
            return alinear_letra_con_whisper(lines, d["palabras"])
        return None
    except Exception:
        return None


def generate_new(audio_path, ts_path, lines, modelo="base", idioma="es"):
    """Genera timestamps con Whisper. Retorna (timing, n_palabras)."""
    res = whisper_generar_timestamps(audio_path, modelo=modelo, idioma=idioma)
    with open(ts_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    timing = alinear_letra_con_whisper(lines, res["palabras"])
    n = len(res.get("palabras", []))
    return timing, n


def fallback_timing(lines, dur):
    """Genera timing uniforme cuando no hay timestamps."""
    gap = dur / max(len(lines), 1)
    return [{"texto": l, "inicio": i * gap, "fin": (i + 1) * gap - 0.1, "score": 0.5}
            for i, l in enumerate(lines)]
