"""Sistema de internacionalización (i18n) — Español/English."""

import json
import os

_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "settings.json"
)

_current_lang = "es"

STRINGS = {
    # ── Toolbar ──
    "toolbar.timestamps": {"es": "\u27f3 Timestamps", "en": "\u27f3 Timestamps"},
    "toolbar.sync": {"es": "\u270e Sync", "en": "\u270e Sync"},
    "toolbar.preview": {"es": "\U0001f441 Preview", "en": "\U0001f441 Preview"},
    "toolbar.generate": {"es": "\u25b6  GENERAR VIDEO", "en": "\u25b6  GENERATE VIDEO"},
    "toolbar.generating": {"es": "\u27f3  GENERANDO...", "en": "\u27f3  GENERATING..."},
    "toolbar.ready": {"es": "\u2713 Listo", "en": "\u2713 Ready"},

    # ── App / window ──
    "app.title": {"es": "Dudiver Visualizer Studio", "en": "Dudiver Visualizer Studio"},
    "app.warn": {"es": "Aviso", "en": "Warning"},
    "app.info": {"es": "Info", "en": "Info"},
    "app.select_audio": {"es": "Selecciona un audio primero.", "en": "Select an audio file first."},
    "app.select_audio_short": {"es": "Selecciona un audio.", "en": "Select an audio file."},
    "app.add_lyrics": {"es": "Agrega la letra.", "en": "Add the lyrics."},
    "app.add_lyrics_first": {"es": "Agrega la letra primero.", "en": "Add the lyrics first."},
    "app.save_as": {"es": "Guardar video como...", "en": "Save video as..."},
    "app.preparing": {"es": "Preparando...", "en": "Preparing..."},
    "app.timestamps_status": {"es": "Timestamps...", "en": "Timestamps..."},
    "app.running_whisper": {"es": "Ejecutando Whisper...", "en": "Running Whisper..."},
    "app.no_timestamps": {"es": "Sin timestamps, generando...", "en": "No timestamps, generating..."},
    "app.timestamps_done": {"es": "\u2713 Timestamps: {n} palabras", "en": "\u2713 Timestamps: {n} words"},
    "app.cancelling": {"es": "Cancelando...", "en": "Cancelling..."},
    "app.generating_preview": {"es": "Generando preview...", "en": "Generating preview..."},
    "app.no_ts_run_whisper": {
        "es": "No hay timestamps. Ejecuta Whisper primero.",
        "en": "No timestamps found. Run Whisper first.",
    },

    # ── Files panel ──
    "files.title": {"es": "\U0001f3b5 ARCHIVOS", "en": "\U0001f3b5 FILES"},
    "files.audio": {"es": "Audio", "en": "Audio"},
    "files.lyrics": {"es": "Letra", "en": "Lyrics"},
    "files.background": {"es": "Fondo", "en": "Background"},
    "files.transparent": {"es": "Transparente (alpha/WebM)", "en": "Transparent (alpha/WebM)"},
    "files.song_title": {"es": "\u270f\ufe0f TITULO", "en": "\u270f\ufe0f TITLE"},
    "files.lyrics_paste": {"es": "\U0001f4dd LETRA (o pega aqui)", "en": "\U0001f4dd LYRICS (or paste here)"},
    "files.select": {"es": "Seleccionar {label}", "en": "Select {label}"},
    "files.text": {"es": "Texto", "en": "Text"},
    "files.media": {"es": "Media", "en": "Media"},
    "files.all": {"es": "Todos", "en": "All"},

    # ── Config panel ──
    "config.mode_title": {"es": "\U0001f3a8 MODO", "en": "\U0001f3a8 MODE"},
    "config.mode": {"es": "Modo", "en": "Mode"},
    "config.style": {"es": "Estilo", "en": "Style"},
    "config.font": {"es": "Fuente", "en": "Font"},
    "config.effects_title": {"es": "\u2728 EFECTOS", "en": "\u2728 EFFECTS"},
    "config.video_title": {"es": "\U0001f3ac VIDEO", "en": "\U0001f3ac VIDEO"},
    "config.size": {"es": "Tama\u00f1o", "en": "Size"},
    "config.colors": {"es": "Colores", "en": "Colors"},
    "config.duration": {"es": "Duraci\u00f3n", "en": "Duration"},
    "config.font_px": {"es": "Fuente {n}px", "en": "Font {n}px"},
    "config.particles": {"es": "Part\u00edculas", "en": "Particles"},
    "config.wave": {"es": "Onda", "en": "Wave"},
    "config.vignette": {"es": "Vi\u00f1eta", "en": "Vignette"},
    "config.progress_bar": {"es": "Barra progreso", "en": "Progress bar"},

    # ── Spot panel ──
    "spot.title": {"es": "\U0001f4e2 SPOT PUBLICITARIO", "en": "\U0001f4e2 PROMO SPOT"},
    "spot.enable": {"es": "Activar spot al final", "en": "Enable spot at end"},
    "spot.type": {"es": "Tipo:", "en": "Type:"},
    "spot.text": {"es": "Texto", "en": "Text"},
    "spot.image": {"es": "Imagen", "en": "Image"},
    "spot.video": {"es": "Video", "en": "Video"},
    "spot.line1": {"es": "Linea 1:", "en": "Line 1:"},
    "spot.line2": {"es": "Linea 2:", "en": "Line 2:"},
    "spot.file": {"es": "Archivo:", "en": "File:"},
    "spot.none": {"es": "ninguno", "en": "none"},
    "spot.duration": {"es": "Duracion:", "en": "Duration:"},
    "spot.select_file": {"es": "Seleccionar archivo spot", "en": "Select spot file"},
    "spot.images": {"es": "Imagenes", "en": "Images"},
    "spot.all": {"es": "Todos", "en": "All"},

    # ── Preview panel ──
    "preview.title": {"es": "\U0001f5bc PREVIEW", "en": "\U0001f5bc PREVIEW"},
    "preview.select_audio": {
        "es": "Selecciona un audio para comenzar",
        "en": "Select an audio to start",
    },

    # ── Settings ──
    "settings.title": {"es": "Configuraci\u00f3n \u2014 GPU & Rendimiento", "en": "Settings \u2014 GPU & Performance"},
    "settings.header": {"es": "\u2699 CONFIGURACI\u00d3N", "en": "\u2699 SETTINGS"},
    "settings.gpu_detected": {"es": "GPU Detectada", "en": "GPU Detected"},
    "settings.no_gpu": {"es": "No se detect\u00f3 GPU dedicada", "en": "No dedicated GPU detected"},
    "settings.use_gpu": {"es": "Usar GPU para renderizar", "en": "Use GPU for rendering"},
    "settings.video_encoding": {"es": "Codificaci\u00f3n de Video", "en": "Video Encoding"},
    "settings.acceleration": {"es": "Aceleraci\u00f3n:", "en": "Acceleration:"},
    "settings.quality": {"es": "Calidad Manim:", "en": "Manim Quality:"},
    "settings.threads": {"es": "Threads:", "en": "Threads:"},
    "settings.accelerators": {"es": "Aceleradores disponibles:", "en": "Available accelerators:"},
    "settings.save": {"es": "Guardar", "en": "Save"},
    "settings.cancel": {"es": "Cancelar", "en": "Cancel"},

    # ── About ──
    "about.title": {"es": "Acerca de \u2014 Dudiver Visualizer", "en": "About \u2014 Dudiver Visualizer"},
    "about.bio": {"es": "Venezolano \u00b7 Sin g\u00e9nero definido", "en": "Venezuelan \u00b7 No defined genre"},
    "about.footer": {"es": "Hecho con \u2665 desde Venezuela", "en": "Made with \u2665 from Venezuela"},

    # ── Splash ──
    "splash.loading": {"es": "Cargando...", "en": "Loading..."},

    # ── Sync Editor ──
    "sync.title": {"es": "Sync Editor \u2014 Timestamps Avanzado", "en": "Sync Editor \u2014 Advanced Timestamps"},
    "sync.header": {"es": "SYNC EDITOR", "en": "SYNC EDITOR"},
    "sync.words": {"es": "{n} palabras", "en": "{n} words"},
    "sync.lines": {"es": "{n} l\u00edneas", "en": "{n} lines"},
    "sync.save": {"es": "Guardar", "en": "Save"},
    "sync.export": {"es": "Exportar JSON", "en": "Export JSON"},
    "sync.tab_words": {"es": "Palabras", "en": "Words"},
    "sync.tab_lines": {"es": "L\u00edneas", "en": "Lines"},
    "sync.tab_ai": {"es": "IA Sync", "en": "AI Sync"},
    "sync.no_words": {
        "es": "No hay timestamps de palabras.\nEjecuta Whisper primero.",
        "en": "No word timestamps found.\nRun Whisper first.",
    },
    "sync.no_lines": {"es": "No hay timestamps de l\u00edneas.", "en": "No line timestamps found."},
    "sync.shift_plus": {"es": "+ 50ms todo", "en": "+ 50ms all"},
    "sync.shift_minus": {"es": "- 50ms todo", "en": "- 50ms all"},
    "sync.autofix": {"es": "Autofix gaps", "en": "Autofix gaps"},
    "sync.word": {"es": "Palabra", "en": "Word"},
    "sync.start": {"es": "Inicio (s)", "en": "Start (s)"},
    "sync.end": {"es": "Fin (s)", "en": "End (s)"},
    "sync.dur": {"es": "Duraci\u00f3n", "en": "Duration"},
    "sync.ai_title": {"es": "Sincronizaci\u00f3n con IA", "en": "AI Synchronization"},
    "sync.ai_desc": {
        "es": "Usa una IA para analizar el audio y mejorar la\nsincronizaci\u00f3n de los timestamps autom\u00e1ticamente.",
        "en": "Use AI to analyze the audio and improve\ntimestamp synchronization automatically.",
    },
    "sync.provider": {"es": "Proveedor:", "en": "Provider:"},
    "sync.api_key": {"es": "API Key:", "en": "API Key:"},
    "sync.instructions": {"es": "Instrucciones:", "en": "Instructions:"},
    "sync.default_prompt": {
        "es": "Analiza el audio y los timestamps existentes.\nMejora la sincronizaci\u00f3n palabra por palabra.\nAseg\u00farate de que cada palabra coincida exactamente con cuando se canta.",
        "en": "Analyze the audio and existing timestamps.\nImprove word-by-word synchronization.\nMake sure each word matches exactly when it is sung.",
    },
    "sync.run_ai": {"es": "Ejecutar Sincronizaci\u00f3n IA", "en": "Run AI Sync"},
    "sync.syncing": {"es": "Sincronizando...", "en": "Syncing..."},
    "sync.saved_to": {"es": "Timestamps guardados en:\n{path}", "en": "Timestamps saved to:\n{path}"},
    "sync.export_title": {"es": "Exportar timestamps", "en": "Export timestamps"},

    # ── Video generator messages ──
    "video.loading_audio": {"es": "Cargando audio...", "en": "Loading audio..."},
    "video.analyzing_beats": {"es": "Analizando beats...", "en": "Analyzing beats..."},
    "video.generating": {"es": "Generando video...", "en": "Generating video..."},
    "video.encoding": {"es": "Codificando...", "en": "Encoding..."},
    "video.cancelled": {"es": "\u2715 Cancelado", "en": "\u2715 Cancelled"},
    "video.completed": {"es": "\u2713 Completado!", "en": "\u2713 Completed!"},
    "video.error": {"es": "\u2715 Error: {e}", "en": "\u2715 Error: {e}"},
    "video.preparing_manim": {"es": "Preparando Manim...", "en": "Preparing Manim..."},
    "video.rendering_kinetic": {"es": "Renderizando kinetic...", "en": "Rendering kinetic..."},
    "video.render_error": {"es": "\u2715 Error en render", "en": "\u2715 Render error"},

    # ── Project ──
    "project.save": {"es": "Guardar Proyecto", "en": "Save Project"},
    "project.open": {"es": "Abrir Proyecto", "en": "Open Project"},
    "project.saved": {"es": "Proyecto guardado en:\n{path}", "en": "Project saved to:\n{path}"},
    "project.loaded": {"es": "Proyecto cargado: {name}", "en": "Project loaded: {name}"},
    "project.select_folder": {"es": "Seleccionar carpeta del proyecto", "en": "Select project folder"},
    "project.select_file": {"es": "Abrir proyecto", "en": "Open project"},
    "project.no_project": {"es": "No se encontr\u00f3 proyecto en esa carpeta.", "en": "No project found in that folder."},
    "project.ts_location": {
        "es": "Timestamps: {path}",
        "en": "Timestamps: {path}",
    },
}


def get_lang():
    """Retorna el idioma actual."""
    return _current_lang


def set_lang(lang):
    """Cambia el idioma ('es' o 'en')."""
    global _current_lang
    _current_lang = lang
    _save_lang(lang)


def _save_lang(lang):
    """Persiste el idioma en settings.json."""
    data = {}
    if os.path.exists(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            pass
    data["language"] = lang
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _load_lang():
    """Carga el idioma de settings.json."""
    global _current_lang
    if os.path.exists(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r") as f:
                data = json.load(f)
            _current_lang = data.get("language", "es")
        except Exception:
            pass


def t(key, **kwargs):
    """Traduce una clave. Soporta {placeholders} via kwargs."""
    entry = STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(_current_lang, entry.get("es", key))
    if kwargs:
        text = text.format(**kwargs)
    return text


# Cargar idioma al importar
_load_lang()
