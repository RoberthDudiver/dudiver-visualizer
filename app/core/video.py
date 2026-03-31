"""VideoGenerator — genera el video completo con callbacks para UI."""

import os
import random
import subprocess
import shutil
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from app.config import (
    crear_frame_normal,
    crear_frame_alpha,
    Particula,
)
from app.core.audio import analyze_beats
from app.core.spot import create_spot_frame, close_spot_clips
from app.core.kinetic_pil import render_kinetic_pil


def _kinetic_subprocess(config_dict):
    """Top-level function para multiprocessing: renderiza kinetic con Manim (fallback).

    Debe ser top-level (no método) para que Windows pueda pickle-arlo.
    """
    import sys
    from types import SimpleNamespace

    from app.scripts.lyric_video_manim import render_kinetic

    args = SimpleNamespace(**config_dict)
    render_kinetic(args)


class VideoGenerator:
    """
    Genera un video de lyrics. Recibe un dict de config + callbacks.

    config keys:
        audio_path, ancho, alto, fps, titulo, alpha_mode, esquema,
        fondo_path, output_path, max_dur, timing, lines,
        fuente, fuente_titulo, fuente_peq,
        spot_on, spot_type, spot_text, spot_subtext, spot_file, spot_secs

    callbacks:
        on_progress(msg, pct)   — actualizar barra de progreso
        on_log(msg)             — escribir al log
        is_cancelled()          — retorna True si el usuario cancelo
    """

    def __init__(self, config, on_progress, on_log, is_cancelled):
        self.cfg = config
        self.on_progress = on_progress
        self.on_log = on_log
        self.is_cancelled = is_cancelled

    def run(self):
        """Ejecuta la generacion completa. Llamar desde un thread."""
        cfg = self.cfg

        # Si es modo Kinetic, usar pipeline de Manim
        if cfg.get("modo") == "Kinetic Typography":
            self._render_kinetic()
            return

        audio_path = cfg["audio_path"]
        ancho = cfg["ancho"]
        alto = cfg["alto"]
        fps = cfg["fps"]
        titulo = cfg["titulo"]
        alpha_mode = cfg["alpha_mode"]
        esquema = cfg["esquema"]
        fondo = cfg["fondo_path"]
        output = cfg["output_path"]
        max_dur = cfg["max_dur"]
        timing = cfg["timing"]
        lines = cfg["lines"]
        fuente = cfg["fuente"]
        fuente_titulo = cfg["fuente_titulo"]
        fuente_peq = cfg["fuente_peq"]
        start_time = cfg.get("start_time", 0)
        spot_on = cfg["spot_on"]
        spot_type = cfg["spot_type"]
        spot_text = cfg["spot_text"]
        spot_subtext = cfg["spot_subtext"]
        spot_file = cfg["spot_file"]
        spot_secs = cfg["spot_secs"]

        from moviepy import AudioFileClip, VideoClip, VideoFileClip
        import moviepy.audio.fx as afx

        self.on_progress("Cargando audio...", 2)
        self.on_log(f"Audio: {os.path.basename(audio_path)}")
        audio_clip = AudioFileClip(audio_path)
        duracion = audio_clip.duration

        if max_dur > 0 and duracion > max_dur:
            duracion = max_dur
            self.on_log(f"Duracion limitada a {max_dur}s")

        # Audio fade out (3s) cuando no es completo o hay spot
        # MoviePy v2.x: audio_clip.audio_fadeout(dur) → with_effects([afx.AudioFadeOut(dur)])
        fade_dur = 3.0
        if max_dur > 0 and max_dur < audio_clip.duration:
            audio_clip = audio_clip.subclipped(start_time, start_time + duracion)
            audio_clip = audio_clip.with_effects([afx.AudioFadeOut(fade_dur)])
            self.on_log(f"Audio fade out: {fade_dur}s")
        elif spot_on:
            audio_clip = audio_clip.with_effects([afx.AudioFadeOut(fade_dur)])

        total_dur = duracion + (spot_secs if spot_on else 0)

        # Beats
        self.on_progress("Analizando beats...", 12)
        beat_times, rms, rms_times = analyze_beats(audio_path)

        # Background
        bg_image = None
        bg_video = None
        bg_is_video = False
        if not alpha_mode and fondo and os.path.isfile(fondo):
            ext = os.path.splitext(fondo)[1].lower()
            if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
                bg_video = VideoFileClip(fondo)
                if bg_video.size != [ancho, alto]:
                    bg_video = bg_video.resized((ancho, alto))
                bg_is_video = True
            elif ext in (".jpg", ".jpeg", ".png", ".bmp"):
                bg_image = Image.open(fondo).resize((ancho, alto), Image.Resampling.LANCZOS)

        random.seed(42)
        parts = [Particula(ancho, alto) for _ in range(60)]
        total_frames = int(total_dur * fps)
        song_frames = int(duracion * fps)
        self.on_log(f"\U0001f4d0 {ancho}x{alto} @ {fps}fps \u2014 {total_frames} frames")
        if spot_on:
            self.on_log(f"\U0001f4e2 Spot: {spot_type} \u2014 {spot_secs}s al final")

        try:
            if alpha_mode:
                self._render_alpha(
                    audio_path, audio_clip, ancho, alto, fps, duracion, total_dur,
                    total_frames, timing, beat_times, fuente, fuente_titulo, titulo,
                    output, spot_on, spot_type, spot_text, spot_subtext, spot_file, spot_secs)
            else:
                self._render_normal(
                    audio_clip, ancho, alto, fps, duracion, total_dur,
                    timing, beat_times, rms, rms_times, esquema, fuente,
                    fuente_titulo, fuente_peq, parts, titulo, bg_image,
                    bg_video, bg_is_video, output, spot_on, spot_type,
                    spot_text, spot_subtext, spot_file, spot_secs)

            if bg_video:
                bg_video.close()
            audio_clip.close()
            close_spot_clips()

        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            self.on_log(f"\u2715 ERROR: {ex}")
            self.on_log(tb)
            self._save_error_log(ex, tb)
            short_err = str(ex)[:80]
            self.on_progress(f"\u2715 Error (ver dudiver_error.log): {short_err}", 0)
            try:
                audio_clip.close()
            except Exception:
                pass

    def _render_alpha(self, audio_path, audio_clip, ancho, alto, fps,
                      duracion, total_dur, total_frames, timing, beat_times,
                      fuente, fuente_titulo, titulo, output,
                      spot_on, spot_type, spot_text, spot_subtext, spot_file, spot_secs):
        """Render en modo alpha (WebM + preview MP4) via FFmpeg pipe."""
        self.on_progress("Generando video...", 15)

        from app.utils.paths import get_ffmpeg
        ff = get_ffmpeg()

        webm = output if output.endswith(".webm") else os.path.splitext(output)[0] + ".webm"
        mp4 = os.path.splitext(output)[0] + "_preview.mp4"

        # Pipe RGBA frames directamente a FFmpeg (sin escribir PNGs a disco)
        webm_cmd = [
            ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
            "-s", f"{ancho}x{alto}", "-r", str(fps), "-i", "-",
            "-i", audio_path, "-t", str(total_dur),
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
            "-b:v", "4M", "-c:a", "libopus", "-b:a", "128k",
            "-shortest", "-auto-alt-ref", "0", webm,
        ]

        stderr_log = os.path.splitext(output)[0] + "_ffmpeg_alpha.log"
        stderr_file = open(stderr_log, "w", encoding="utf-8")
        proc = subprocess.Popen(webm_cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=stderr_file)

        update_every = max(1, fps)
        try:
            for fn in range(total_frames):
                if self.is_cancelled():
                    proc.stdin.close()
                    proc.terminate()
                    proc.wait()
                    stderr_file.close()
                    self.on_progress("\u2715 Cancelado", 0)
                    return
                t = fn / fps
                if t < duracion:
                    frame = crear_frame_alpha(ancho, alto, timing, t, duracion,
                                              beat_times, fuente, fuente_titulo, titulo,
                                              lyrics_pos=self.cfg.get("lyrics_pos", "Centro"),
                                              lyrics_margin=self.cfg.get("lyrics_margin", 40),
                                              lyrics_extra_y=self.cfg.get("lyrics_extra_y", 0),
                                              effects=self.cfg.get("effects"))
                    if spot_on and (duracion - t) < 2.0:
                        fade = (duracion - t) / 2.0
                        arr = np.array(frame)
                        arr[:, :, 3] = (arr[:, :, 3] * fade).astype(np.uint8)
                        frame = Image.fromarray(arr)
                else:
                    frame = Image.new("RGBA", (ancho, alto), (0, 0, 0, 255))
                    spot_f = create_spot_frame(ancho, alto, t - duracion,
                                               spot_type, spot_text, spot_subtext, spot_file,
                                               platform_urls=self.cfg.get("platform_urls"))
                    frame.paste(spot_f)

                if frame.mode != "RGBA":
                    frame = frame.convert("RGBA")

                try:
                    proc.stdin.write(frame.tobytes())
                except (BrokenPipeError, OSError):
                    self.on_log("FFmpeg cerró el pipe")
                    break

                if fn % update_every == 0:
                    pct = 15 + (fn / total_frames) * 70
                    self.on_progress(f"Frame {fn}/{total_frames}", pct)

            proc.stdin.close()
            proc.wait(timeout=120)
        except Exception:
            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.terminate()
            proc.wait()
        stderr_file.close()

        # Preview MP4 desde el WebM (rápido, no re-renderiza frames)
        if os.path.isfile(webm):
            self.on_progress("Generando preview MP4...", 90)
            subprocess.run([ff, "-y", "-i", webm,
                            "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-b:v", "5M", "-c:a", "aac", "-b:a", "192k",
                            "-movflags", "+faststart", mp4],
                           capture_output=True)

        # Limpiar log si OK
        if proc.returncode == 0:
            try:
                os.remove(stderr_log)
            except OSError:
                pass

        self.on_log(f"\u2713 {os.path.basename(webm)}")
        if os.path.isfile(mp4):
            self.on_log(f"\u2713 {os.path.basename(mp4)}")
        self.on_progress("\u2713 Completado!", 100)

    def _render_normal(self, audio_clip, ancho, alto, fps, duracion, total_dur,
                       timing, beat_times, rms, rms_times, esquema, fuente,
                       fuente_titulo, fuente_peq, parts, titulo, bg_image,
                       bg_video, bg_is_video, output, spot_on, spot_type,
                       spot_text, spot_subtext, spot_file, spot_secs):
        """Render en modo normal (MP4 con moviepy)."""
        from moviepy import VideoClip
        import time as _time_mod

        self.on_progress("Generando video...", 15)
        _last_progress_wall = [0.0]
        _render_start = [_time_mod.time()]

        def make_frame(t):
            if self.is_cancelled():
                raise KeyboardInterrupt

            if t >= duracion and spot_on:
                img = create_spot_frame(ancho, alto, t - duracion,
                                        spot_type, spot_text, spot_subtext, spot_file,
                                        platform_urls=self.cfg.get("platform_urls"))
                return np.array(img)

            cur_bg = bg_image
            if bg_is_video and bg_video:
                cur_bg = Image.fromarray(bg_video.get_frame(t % bg_video.duration))

            img = crear_frame_normal(ancho, alto, timing, t, duracion,
                                     beat_times, (rms, rms_times), esquema,
                                     fuente, fuente_titulo, fuente_peq,
                                     parts, titulo, cur_bg,
                                     effects=self.cfg.get("effects"),
                                     lyrics_pos=self.cfg.get("lyrics_pos", "Centro"),
                                     lyrics_margin=self.cfg.get("lyrics_margin", 40),
                                     lyrics_extra_y=self.cfg.get("lyrics_extra_y", 0))

            left = duracion - t
            if spot_on and left < 2.0:
                fa = int(255 * (1 - left / 2.0))
                ov = Image.new("RGBA", (ancho, alto), (0, 0, 0, fa))
                img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
            elif not spot_on and left < 3.0:
                fa = int(255 * (1 - left / 3.0))
                ov = Image.new("RGBA", (ancho, alto), (0, 0, 0, fa))
                img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

            # Actualizar progreso cada 0.25s de tiempo real (no de video)
            now = _time_mod.time()
            if now - _last_progress_wall[0] >= 0.25:
                _last_progress_wall[0] = now
                pct = 15 + (t / total_dur) * 80
                elapsed = now - _render_start[0]
                if t > 0 and elapsed > 0:
                    fps_real = t / elapsed
                    remaining = (total_dur - t) / fps_real if fps_real > 0 else 0
                    msg = f"{t:.0f}s/{total_dur:.0f}s  — {remaining:.0f}s restantes"
                else:
                    msg = f"{t:.0f}s / {total_dur:.0f}s"
                self.on_progress(msg, pct)

            return np.array(img)

        try:
            video = VideoClip(make_frame, duration=total_dur)
            video = video.with_audio(audio_clip)
            self.on_log(f"Escribiendo: {os.path.basename(output)}")
            # Codec según formato de salida
            ext = os.path.splitext(output)[1].lower()
            if ext == ".webm":
                codec, audio_codec = "libvpx-vp9", "libvorbis"
            elif ext == ".avi":
                codec, audio_codec = "mpeg4", "mp3"
            elif ext == ".mov":
                codec, audio_codec = "prores_ks", "aac"
            else:
                codec, audio_codec = "libx264", "aac"
            write_kwargs = dict(fps=fps, codec=codec,
                                audio_codec=audio_codec, bitrate="8000k",
                                logger=None)
            if codec == "libx264":
                write_kwargs["preset"] = "medium"
            video.write_videofile(output, **write_kwargs)
            video.close()
            self.on_log(f"\u2713 {os.path.basename(output)}")
            self.on_progress("\u2713 Completado!", 100)
        except KeyboardInterrupt:
            self.on_progress("\u2715 Cancelado", 0)

    def _render_kinetic(self):
        """Render kinetic typography usando PIL + FFmpeg (rápido, cancelable).

        Fallback a Manim via subprocess si PIL falla.
        """
        import json

        cfg = self.cfg
        audio_path = cfg["audio_path"]
        output = cfg["output_path"]

        try:
            self.on_progress("Preparando kinetic...", None)
            self.on_log("Modo: Kinetic Typography (PIL + FFmpeg)")
            self.on_log(f"Estilo: {cfg.get('estilo_kinetic', 'wave')}")

            # Buscar timestamps: primero whisper_raw embebido, luego archivo externo
            ts_path = None
            whisper_ts = None  # ruta a archivo externo (puede ser None si no existe)
            whisper_raw = cfg.get("whisper_raw")

            # Extraer líneas reales del usuario para forzar sobre Whisper
            lineas_reales = [
                item["texto"] for item in (cfg.get("timing") or [])
                if isinstance(item, dict) and item.get("texto", "").strip()
            ]

            if whisper_raw and isinstance(whisper_raw, dict) and whisper_raw.get("palabras"):
                # Forzar letra real sobre timestamps de Whisper
                palabras_forzadas = whisper_raw["palabras"]
                if lineas_reales:
                    from app.config import forzar_letra_sobre_timestamps
                    palabras_forzadas = forzar_letra_sobre_timestamps(
                        lineas_reales, whisper_raw["palabras"]
                    )
                    self.on_log(f"  Letra forzada: {len(palabras_forzadas)} palabras reales")
                raw_forzado = dict(whisper_raw)
                raw_forzado["palabras"] = palabras_forzadas
                # Escribir a temp para el renderer
                ts_path = os.path.join(tempfile.gettempdir(), "dvs_kinetic_ts.json")
                with open(ts_path, "w", encoding="utf-8") as f:
                    json.dump(raw_forzado, f, ensure_ascii=False)
                self.on_log(f"  {len(palabras_forzadas)} palabras (letra del usuario)")
            else:
                # Fallback: archivo externo
                whisper_ts = os.path.splitext(audio_path)[0] + "_timestamps.json"
                if os.path.isfile(whisper_ts):
                    with open(whisper_ts, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "palabras" in data and data["palabras"]:
                        # Forzar letra real sobre los timestamps del archivo externo
                        if lineas_reales:
                            from app.config import forzar_letra_sobre_timestamps
                            data["palabras"] = forzar_letra_sobre_timestamps(
                                lineas_reales, data["palabras"]
                            )
                        ts_forced = os.path.join(tempfile.gettempdir(), "dvs_kinetic_ts.json")
                        with open(ts_forced, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False)
                        ts_path = ts_forced
                        self.on_log(f"  {len(data['palabras'])} palabras (letra forzada)")

            if not ts_path:
                ts_path = os.path.join(tempfile.gettempdir(), "dvs_kinetic_ts.json")
                with open(ts_path, "w", encoding="utf-8") as f:
                    json.dump(cfg["timing"], f, ensure_ascii=False)
                self.on_log("  Usando timestamps de líneas (sin palabras individuales)")

            # Config para PIL renderer
            pil_config = {
                "audio": audio_path,
                "timestamps": ts_path,
                "output": output,
                "estilo": cfg.get("estilo_kinetic", "wave"),
                "ancho": cfg["ancho"],
                "alto": cfg["alto"],
                "fps": cfg["fps"],
                "color": cfg.get("esquema_kinetic", "neon"),
                "fuente": cfg.get("fuente_nombre", "Arial"),
                "font_size": cfg.get("font_size", 72),
                "alpha_mode": cfg.get("alpha_mode", False),
                "fondo_path": cfg.get("fondo_path", None),
                "effects": cfg.get("effects"),
                "max_dur": cfg.get("max_dur", 0),
                "spot_on": cfg.get("spot_on", False),
                "spot_type": cfg.get("spot_type", "Texto"),
                "spot_text": cfg.get("spot_text", ""),
                "spot_subtext": cfg.get("spot_subtext", ""),
                "spot_file": cfg.get("spot_file", ""),
                "spot_secs": cfg.get("spot_secs", 5),
                "start_time": cfg.get("start_time", 0),
                "platform_urls": cfg.get("platform_urls"),
                # Posición de letra (crítico para que render = preview)
                "lyrics_pos": cfg.get("lyrics_pos", "Centro"),
                "lyrics_margin": cfg.get("lyrics_margin", 40),
                "lyrics_extra_y": cfg.get("lyrics_extra_y", 0),
            }

            self.on_log(f"Fuente: {pil_config['fuente']}")
            self.on_log(f"Resolución: {pil_config['ancho']}x{pil_config['alto']} "
                        f"@ {pil_config['fps']}fps")

            # Ejecutar PIL renderer (directo, ya soporta cancelación)
            result = render_kinetic_pil(
                pil_config,
                on_progress=self.on_progress,
                on_log=self.on_log,
                is_cancelled=self.is_cancelled,
            )

            # Limpiar temp
            if ts_path != whisper_ts and os.path.exists(ts_path):
                os.remove(ts_path)

            if result and os.path.isfile(result):
                self.on_log(f"\u2713 {os.path.basename(result)}")
                self.on_progress("\u2713 Completado!", 100)
            elif not self.is_cancelled():
                self.on_log("\u2715 PIL render falló, intentando Manim...")
                self._render_kinetic_manim(audio_path, output, ts_path,
                                           whisper_ts, cfg)

        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            self.on_log(f"\u2715 ERROR: {ex}")
            self.on_log(tb)
            self._save_error_log(ex, tb)
            short_err = str(ex)[:80]
            self.on_progress(f"\u2715 Error (ver dudiver_error.log): {short_err}", 0)

    def _render_kinetic_manim(self, audio_path, output, ts_path, whisper_ts, cfg):
        """Fallback: render kinetic con Manim en subprocess cancelable."""
        import time
        import multiprocessing

        self.on_progress("Renderizando con Manim (fallback)...", None)

        kinetic_config = {
            "audio": audio_path,
            "timestamps": ts_path or whisper_ts,
            "output": output,
            "estilo": cfg.get("estilo_kinetic", "wave"),
            "resolucion": f"{cfg['ancho']}x{cfg['alto']}",
            "fps": cfg["fps"],
            "color": cfg.get("esquema_kinetic", "neon"),
            "color_texto": None,
            "color_glow": None,
            "fuente": cfg.get("fuente_nombre", "Arial"),
            "font_size": cfg.get("font_size", 72),
            "alpha": cfg.get("alpha_mode", False),
            "fondo": cfg.get("fondo_path", None),
        }

        proc = multiprocessing.Process(
            target=_kinetic_subprocess, args=(kinetic_config,))
        proc.start()
        start_time = time.time()

        while proc.is_alive():
            if self.is_cancelled():
                self.on_log("Cancelando render Manim...")
                proc.terminate()
                proc.join(timeout=5)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=3)
                self.on_progress("\u2715 Cancelado", 0)
                return
            elapsed = int(time.time() - start_time)
            self.on_progress(f"Renderizando Manim... ({elapsed}s)", None)
            proc.join(timeout=0.5)

        if proc.exitcode == 0 and os.path.isfile(output):
            self.on_log(f"\u2713 {os.path.basename(output)}")
            self.on_progress("\u2713 Completado!", 100)
        else:
            self.on_log(f"\u2715 Manim terminó con código {proc.exitcode}")
            self.on_progress("\u2715 Error en render (ver log)", 0)

    def _save_error_log(self, ex, tb):
        """Guarda log de error a archivo."""
        try:
            _out = self.cfg.get("output_path", "")
            _aud = self.cfg.get("audio_path", "")
            log_dir = os.path.dirname(_out) or os.path.dirname(_aud) or "."
            log_path = os.path.join(log_dir, "dudiver_error.log")
            with open(log_path, "w", encoding="utf-8") as _f:
                _f.write("Dudiver Visualizer Studio — Error Log\n")
                _f.write("=" * 50 + "\n")
                _f.write(f"Modo: {self.cfg.get('modo', '?')}\n")
                _f.write(f"Audio: {_aud}\n")
                _f.write(f"Output: {_out}\n")
                _f.write(f"Resolucion: {self.cfg.get('ancho', '?')}x"
                         f"{self.cfg.get('alto', '?')}\n")
                _f.write(f"Fuente: {self.cfg.get('fuente_nombre', '?')}\n")
                _f.write(f"Estilo kinetic: {self.cfg.get('estilo_kinetic', 'N/A')}\n\n")
                _f.write(f"ERROR:\n{ex}\n\n")
                _f.write(f"TRACEBACK:\n{tb}\n")
            self.on_log(f"Log guardado en: {log_path}")
        except Exception:
            pass
