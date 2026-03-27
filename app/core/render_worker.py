"""Worker para render en proceso separado — NO importa tkinter."""

import os
import sys
import traceback


def render_subprocess(config):
    """Función top-level para multiprocessing.Process.

    Hace TODO dentro del proceso: fonts, timestamps, render.
    Se puede matar en cualquier momento con kill().
    """
    progress_file = config.pop("_progress_file", None)

    def on_progress(msg, pct):
        if progress_file:
            try:
                with open(progress_file, "w") as f:
                    f.write(f"{pct}|{msg}")
            except Exception:
                pass

    def on_log(msg):
        pass

    try:
        on_progress("Preparando fuentes...", 2)

        # Recrear fonts PIL
        font_name = config.pop("_font_name", None)
        font_size_base = config.pop("_font_size_base", 40)
        lines = config.get("lines", [])
        ancho = config.get("ancho", 1920)
        alto = config.get("alto", 1080)

        from app.utils.fonts import adapted_fonts
        fuente, fuente_titulo, fuente_peq, _ = adapted_fonts(
            font_size_base, ancho, alto, lines, font_name=font_name)
        config["fuente"] = fuente
        config["fuente_titulo"] = fuente_titulo
        config["fuente_peq"] = fuente_peq

        # Timestamps (Whisper si es necesario)
        timing = config.get("timing")
        if not timing:
            on_progress("Ejecutando Whisper...", 5)
            audio = config["audio_path"]
            from app.core.timestamps import generate_new
            ts_path = os.path.splitext(audio)[0] + "_timestamps.json"
            timing, _ = generate_new(
                audio, ts_path, lines,
                modelo=config.get("whisper_model", "small"))
            config["timing"] = timing

        on_progress("Iniciando render...", 10)

        from app.core.video import VideoGenerator
        gen = VideoGenerator(
            config,
            on_progress=on_progress,
            on_log=on_log,
            is_cancelled=lambda: False,
        )
        gen.run()

        on_progress("Completado", 100)
    except Exception:
        err_log = config.get("output_path", "output") + ".error.log"
        with open(err_log, "w") as f:
            traceback.print_exc(file=f)
        sys.exit(1)
