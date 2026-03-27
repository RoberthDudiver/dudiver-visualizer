"""Sistema de proyectos .dudi — archivo único con todo embebido.

Un .dudi es un ZIP renombrado que contiene:
  - project.json  (configuración)
  - audio.*       (archivo de audio)
  - fondo.*       (imagen/video de fondo)
  - timestamps.json (timestamps de Whisper)
  - spot.*        (archivo del spot publicitario)
"""

import json
import os
import shutil
import tempfile
import zipfile


DUDI_EXT = ".dudi"
# Carpeta temporal donde se extraen los archivos del proyecto activo
_EXTRACT_DIR = os.path.join(tempfile.gettempdir(), "dudiver_project")


def save_dudi(dudi_path, config):
    """Guarda todo en un solo archivo .dudi (ZIP).

    config: dict con rutas absolutas a archivos y settings.
    """
    data = dict(config)
    embedded = {}

    # Embeber archivos
    for key in ("audio_path", "letra_path", "fondo_path", "spot_file",
                "timestamps_file"):
        src = data.get(key, "")
        if src and os.path.isfile(src):
            arc_name = f"{key}_{os.path.basename(src)}"
            embedded[key] = (src, arc_name)
            data[key] = arc_name
        else:
            data[key] = ""

    with zipfile.ZipFile(dudi_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Escribir config
        zf.writestr("project.json", json.dumps(data, ensure_ascii=False, indent=2))
        # Escribir archivos
        for key, (src, arc_name) in embedded.items():
            zf.write(src, arc_name)

    return dudi_path


def load_dudi(dudi_path):
    """Carga un .dudi: extrae archivos a temp y retorna config con rutas absolutas."""
    # Limpiar extracción anterior
    if os.path.isdir(_EXTRACT_DIR):
        shutil.rmtree(_EXTRACT_DIR, ignore_errors=True)
    os.makedirs(_EXTRACT_DIR, exist_ok=True)

    with zipfile.ZipFile(dudi_path, "r") as zf:
        zf.extractall(_EXTRACT_DIR)

    config_path = os.path.join(_EXTRACT_DIR, "project.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Resolver rutas a archivos extraídos
    for key in ("audio_path", "letra_path", "fondo_path", "spot_file",
                "timestamps_file"):
        val = config.get(key, "")
        if val:
            abs_path = os.path.join(_EXTRACT_DIR, val)
            if os.path.isfile(abs_path):
                config[key] = abs_path
            else:
                config[key] = ""

    config["_dudi_path"] = dudi_path
    config["_project_folder"] = _EXTRACT_DIR
    return config


def save_dudi_quick(dudi_path, config):
    """Auto-save rápido: solo actualiza project.json dentro del .dudi.

    Si el .dudi no existe aún, hace save completo.
    """
    if not os.path.isfile(dudi_path):
        return save_dudi(dudi_path, config)

    data = dict(config)

    # Convertir rutas absolutas de archivos extraídos a nombres internos del zip
    try:
        with zipfile.ZipFile(dudi_path, "r") as zf:
            existing = zf.namelist()
    except Exception:
        return save_dudi(dudi_path, config)

    for key in ("audio_path", "letra_path", "fondo_path", "spot_file",
                "timestamps_file"):
        src = data.get(key, "")
        if src:
            basename = os.path.basename(src)
            # Buscar en el zip por el nombre del archivo
            match = None
            for name in existing:
                if name.endswith(basename):
                    match = name
                    break
            if match:
                data[key] = match
            elif os.path.isfile(src):
                # Archivo nuevo que no estaba en el zip — rebuild completo
                return save_dudi(dudi_path, config)
            else:
                data[key] = ""

    # Reescribir solo el project.json
    # zipfile no permite actualizar in-place, hay que reconstruir
    tmp_path = dudi_path + ".tmp"
    with zipfile.ZipFile(dudi_path, "r") as zf_in:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.infolist():
                if item.filename == "project.json":
                    zf_out.writestr("project.json",
                                    json.dumps(data, ensure_ascii=False, indent=2))
                else:
                    zf_out.writestr(item, zf_in.read(item.filename))

    # Reemplazar original
    os.replace(tmp_path, dudi_path)
    return dudi_path


def find_dudi(folder):
    """Busca un archivo .dudi en la carpeta. Retorna ruta o None."""
    if not folder or not os.path.isdir(folder):
        return None
    for f in os.listdir(folder):
        if f.lower().endswith(DUDI_EXT):
            return os.path.join(folder, f)
    return None


def get_project_config(app):
    """Extrae la configuración actual de la app como dict de proyecto."""
    audio = app.audio_path.get()

    # Timing embebido directamente en el proyecto (sin archivo suelto)
    timing_data = None
    with app._data_lock:
        if app._lineas and len(app._lineas) > 0:
            timing_data = app._lineas
    # Fallback: leer del JSON externo si existe (compat con proyectos viejos)
    if not timing_data and audio:
        candidate = os.path.splitext(audio)[0] + "_timestamps.json"
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    timing_data = json.load(f)
            except Exception:
                pass

    # Whisper raw data (palabras individuales) para Kinetic mode
    whisper_raw = None
    if audio:
        whisper_file = os.path.splitext(audio)[0] + "_timestamps.json"
        if os.path.isfile(whisper_file):
            try:
                with open(whisper_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and "palabras" in raw:
                    whisper_raw = raw
            except Exception:
                pass

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
        "whisper_model": app.whisper_var.get(),  # Label amigable (Normal/Alta/etc)
        "duracion": app.duracion_var.get(),
        "alpha": app.alpha_var.get(),
        "spot_enabled": app.spot_enabled.get(),
        "spot_type": app.spot_type.get(),
        "spot_text": app.spot_text.get(),
        "spot_subtext": app.spot_subtext.get(),
        "spot_file": app.spot_file.get(),
        "spot_duration": app.spot_duration.get(),
        "timestamps_file": "",  # Ya no usamos archivo suelto
        "timing_data": timing_data,  # Timing embebido en el proyecto
        "whisper_raw": whisper_raw,  # Datos Whisper raw para Kinetic
        "lyrics_text": app.files_panel.letra_text.get("1.0", "end").strip(),
        # Efectos
        "efx_particulas": app.chk_particulas.get(),
        "efx_onda": app.chk_onda.get(),
        "efx_vineta": app.chk_vineta.get(),
        "efx_glow": app.chk_glow.get(),
        "efx_barra": app.chk_barra.get(),
        "formato": app.formato_var.get(),
        # Plataformas
        "platforms": {k: v.get() for k, v in app.platform_vars.items()},
    }


def apply_project(app, config):
    """Aplica la configuración de un proyecto a la app."""
    # Desactivar auto-save temporalmente para no disparar saves en cascada
    app._loading_project = True
    try:
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
            wm = config["whisper_model"]
            # Compat: proyectos viejos guardan "base"/"small" → convertir a label
            from app.config import _WHISPER_REV
            app.whisper_var.set(_WHISPER_REV.get(wm, wm))
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
            # Recordar archivo para el tipo de spot actual
            st = config.get("spot_type", "")
            if st and hasattr(app, 'spot_panel'):
                app.spot_panel.remember_file_for_type(st, config["spot_file"])
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

        # Plataformas
        platforms = config.get("platforms", {})
        for k, v in platforms.items():
            var = app.platform_vars.get(k)
            if var:
                if isinstance(v, bool):
                    var.set(v)
                else:
                    var.set(v)

        # Cargar letra
        lyrics_text = config.get("lyrics_text", "")
        if lyrics_text:
            app.files_panel.letra_text.delete("1.0", "end")
            app.files_panel.letra_text.insert("1.0", lyrics_text)

        # Cargar timestamps embebidos en el proyecto
        timing_data = config.get("timing_data")
        if timing_data and isinstance(timing_data, list) and len(timing_data) > 0:
            app._lineas = timing_data
        else:
            # Compat: cargar desde archivo externo si existe
            ts_file = config.get("timestamps_file", "")
            if ts_file and os.path.isfile(ts_file):
                from app.core.timestamps import load_existing
                lines = [l.strip() for l in lyrics_text.splitlines() if l.strip()]
                timing = load_existing(ts_file, lines)
                if timing:
                    app._lineas = timing

        # Guardar Whisper raw data para Kinetic mode
        whisper_raw = config.get("whisper_raw")
        if whisper_raw:
            app._whisper_raw = whisper_raw
    finally:
        app._loading_project = False


# ── Compatibilidad con formato viejo (dudiver_project.json) ──

def find_project_legacy(folder):
    """Busca un dudiver_project.json viejo en la carpeta."""
    if not folder or not os.path.isdir(folder):
        return None
    path = os.path.join(folder, "dudiver_project.json")
    return path if os.path.isfile(path) else None


def load_project_legacy(project_path):
    """Carga un proyecto viejo (JSON suelto) y resuelve rutas."""
    with open(project_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    folder = os.path.dirname(os.path.abspath(project_path))

    for key in ("audio_path", "letra_path", "fondo_path", "spot_file",
                "timestamps_file"):
        val = config.get(key, "")
        if val and not os.path.isabs(val):
            abs_path = os.path.join(folder, val)
            if os.path.isfile(abs_path):
                config[key] = abs_path

    config["_project_folder"] = folder
    return config
