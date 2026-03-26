"""Sistema de proyectos — guardar/cargar estado completo del workspace."""

import json
import os
import shutil


PROJECT_FILE = "dudiver_project.json"


def save_project(folder, config):
    """Guarda el estado del proyecto en una carpeta.

    config: dict con todas las variables del proyecto:
        audio_path, letra_path, fondo_path, titulo, modo, estilo_kinetic,
        fuente, font_size, tamano, fps, esquema, whisper_model, duracion,
        alpha, spot_enabled, spot_type, spot_text, spot_subtext, spot_file,
        spot_duration, timestamps_file
    """
    os.makedirs(folder, exist_ok=True)
    project_path = os.path.join(folder, PROJECT_FILE)

    # Copiar archivos al proyecto si no están allí
    for key in ("audio_path", "letra_path", "fondo_path", "spot_file"):
        src = config.get(key, "")
        if src and os.path.isfile(src):
            dst = os.path.join(folder, os.path.basename(src))
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copy2(src, dst)
            config[key] = os.path.basename(src)

    # Copiar timestamps si existen
    ts = config.get("timestamps_file", "")
    if ts and os.path.isfile(ts):
        dst = os.path.join(folder, os.path.basename(ts))
        if os.path.abspath(ts) != os.path.abspath(dst):
            shutil.copy2(ts, dst)
        config["timestamps_file"] = os.path.basename(ts)

    with open(project_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return project_path


def load_project(project_path):
    """Carga un proyecto y resuelve rutas relativas.

    Returns dict con rutas absolutas.
    """
    with open(project_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    folder = os.path.dirname(os.path.abspath(project_path))

    # Resolver rutas relativas
    for key in ("audio_path", "letra_path", "fondo_path", "spot_file", "timestamps_file"):
        val = config.get(key, "")
        if val and not os.path.isabs(val):
            abs_path = os.path.join(folder, val)
            if os.path.isfile(abs_path):
                config[key] = abs_path
            # Si no existe, dejar como está

    config["_project_folder"] = folder
    return config


def find_project(folder):
    """Busca un archivo de proyecto en la carpeta. Retorna ruta o None."""
    if not folder or not os.path.isdir(folder):
        return None
    path = os.path.join(folder, PROJECT_FILE)
    return path if os.path.isfile(path) else None


def get_project_config(app):
    """Extrae la configuración actual de la app como dict de proyecto."""
    ts_path = None
    audio = app.audio_path.get()
    if audio:
        candidate = os.path.splitext(audio)[0] + "_timestamps.json"
        if os.path.isfile(candidate):
            ts_path = candidate

    return {
        "audio_path": audio,
        "letra_path": app.letra_path.get(),
        "fondo_path": app.fondo_path.get(),
        "titulo": app.titulo_var.get(),
        "modo": app.modo_var.get(),
        "estilo_kinetic": app.estilo_kinetic_var.get(),
        "fuente": app.fuente_var.get(),
        "font_size": app.font_size_var.get(),
        "tamano": app.tamano_var.get(),
        "fps": app.fps_var.get(),
        "esquema": app.esquema_var.get(),
        "whisper_model": app.whisper_var.get(),
        "duracion": app.duracion_var.get(),
        "alpha": app.alpha_var.get(),
        "spot_enabled": app.spot_enabled.get(),
        "spot_type": app.spot_type.get(),
        "spot_text": app.spot_text.get(),
        "spot_subtext": app.spot_subtext.get(),
        "spot_file": app.spot_file.get(),
        "spot_duration": app.spot_duration.get(),
        "timestamps_file": ts_path or "",
        "lyrics_text": app.files_panel.letra_text.get("1.0", "end").strip(),
        # Efectos
        "efx_particulas": app.chk_particulas.get(),
        "efx_onda": app.chk_onda.get(),
        "efx_vineta": app.chk_vineta.get(),
        "efx_glow": app.chk_glow.get(),
        "efx_barra": app.chk_barra.get(),
        "formato": app.formato_var.get(),
    }


def apply_project(app, config):
    """Aplica la configuración de un proyecto a la app."""
    if config.get("audio_path"):
        app.audio_path.set(config["audio_path"])
    if config.get("letra_path"):
        app.letra_path.set(config["letra_path"])
    if config.get("fondo_path"):
        app.fondo_path.set(config["fondo_path"])
    if config.get("titulo"):
        app.titulo_var.set(config["titulo"])
    if config.get("modo"):
        app.modo_var.set(config["modo"])
    if config.get("estilo_kinetic"):
        app.estilo_kinetic_var.set(config["estilo_kinetic"])
    if config.get("fuente"):
        app.fuente_var.set(config["fuente"])
    if config.get("font_size"):
        app.font_size_var.set(int(config["font_size"]))
    if config.get("tamano"):
        app.tamano_var.set(config["tamano"])
    if config.get("fps"):
        app.fps_var.set(str(config["fps"]))
    if config.get("esquema"):
        app.esquema_var.set(config["esquema"])
    if config.get("whisper_model"):
        app.whisper_var.set(config["whisper_model"])
    if config.get("duracion"):
        app.duracion_var.set(config["duracion"])
    if "alpha" in config:
        app.alpha_var.set(config["alpha"])
    if "spot_enabled" in config:
        app.spot_enabled.set(config["spot_enabled"])
    if config.get("spot_type"):
        app.spot_type.set(config["spot_type"])
    if config.get("spot_text"):
        app.spot_text.set(config["spot_text"])
    if config.get("spot_subtext"):
        app.spot_subtext.set(config["spot_subtext"])
    if config.get("spot_file"):
        app.spot_file.set(config["spot_file"])
    if config.get("spot_duration"):
        app.spot_duration.set(config["spot_duration"])

    # Efectos
    if "efx_particulas" in config:
        app.chk_particulas.set(config["efx_particulas"])
    if "efx_onda" in config:
        app.chk_onda.set(config["efx_onda"])
    if "efx_vineta" in config:
        app.chk_vineta.set(config["efx_vineta"])
    if "efx_glow" in config:
        app.chk_glow.set(config["efx_glow"])
    if "efx_barra" in config:
        app.chk_barra.set(config["efx_barra"])
    if config.get("formato"):
        app.formato_var.set(config["formato"])

    # Cargar letra
    lyrics_text = config.get("lyrics_text", "")
    if lyrics_text:
        app.files_panel.letra_text.delete("1.0", "end")
        app.files_panel.letra_text.insert("1.0", lyrics_text)

    # Cargar timestamps si existen
    ts_file = config.get("timestamps_file", "")
    if ts_file and os.path.isfile(ts_file):
        from app.core.timestamps import load_existing
        lines = [l.strip() for l in lyrics_text.splitlines() if l.strip()]
        timing = load_existing(ts_file, lines)
        if timing:
            app._lineas = timing
