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
from app.core.spot import create_spot_frame
from app.core.kinetic_pil import render_kinetic_pil


def _kinetic_subprocess(config_dict):
    """Top-level function para multiprocessing: renderiza kinetic con Manim (fallback).

    Debe ser top-level (no método) para que Windows pueda pickle-arlo.
    """
    import sys
    from types import SimpleNamespace

    skills_dir = os.path.normpath("C:/Users/rober/.claude/skills/music/scripts")
    if skills_dir not in sys.path:
        sys.path.insert(0, skills_dir)

    from lyric_video_manim import render_kinetic

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

        self.on_progress("Cargando audio...", 2)
        self.on_log(f"Audio: {os.path.basename(audio_path)}")
        audio_clip = AudioFileClip(audio_path)
        duracion = audio_clip.duration

        if max_dur > 0 and duracion > max_dur:
            duracion = max_dur
            self.on_log(f"Duracion limitada a {max_dur}s")

        # Audio fade out (3s) cuando no es completo o hay spot
        fade_dur = 3.0
        if max_dur > 0 and max_dur < audio_clip.duration:
            audio_clip = audio_clip.subclipped(start_time, start_time + duracion)
            audio_clip = audio_clip.audio_fadeout(fade_dur)
            self.on_log(f"Audio fade out: {fade_dur}s")
        elif spot_on:
            audio_clip = audio_clip.audio_fadeout(fade_dur)

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
        """Render en modo alpha (WebM + preview MP4)."""
        self.on_progress("Generando video...", 15)
        temp_dir = tempfile.mkdtemp(prefix="dvs_")

        for fn in range(total_frames):
            if self.is_cancelled():
                shutil.rmtree(temp_dir, ignore_errors=True)
                self.on_progress("\u2715 Cancelado", 0)
                return
            t = fn / fps
            if t < duracion:
                frame = crear_frame_alpha(ancho, alto, timing, t, duracion,
                                          beat_times, fuente, fuente_titulo, titulo)
                if spot_on and (duracion - t) < 2.0:
                    fade = (duracion - t) / 2.0
                    arr = np.array(frame)
                    arr[:, :, 3] = (arr[:, :, 3] * fade).astype(np.uint8)
                    frame = Image.fromarray(arr)
            else:
                frame = Image.new("RGBA", (ancho, alto), (0, 0, 0, 255))
                spot_f = create_spot_frame(ancho, alto, t - duracion,
                                           spot_type, spot_text, spot_subtext, spot_file,
                                           platform_urls=cfg.get("platform_urls"))
                frame.paste(spot_f)

            frame.save(os.path.join(temp_dir, f"f_{fn:06d}.png"), "PNG")
            if fn % (fps * 2) == 0:
                pct = 15 + (fn / total_frames) * 70
                self.on_progress(f"Frame {fn}/{total_frames}", pct)

        self.on_progress("Codificando...", 88)
        ff = shutil.which("ffmpeg") or "ffmpeg"
        winff = os.path.expanduser("~/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe")
        if os.path.exists(winff):
            ff = winff

        webm = output if output.endswith(".webm") else os.path.splitext(output)[0] + ".webm"
        subprocess.run([ff, "-y", "-framerate", str(fps),
                        "-i", os.path.join(temp_dir, "f_%06d.png"),
                        "-i", audio_path, "-t", str(total_dur),
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                        "-b:v", "4M", "-c:a", "libopus", "-b:a", "128k",
                        "-shortest", "-auto-alt-ref", "0", webm],
                       capture_output=True)

        mp4 = os.path.splitext(output)[0] + "_preview.mp4"
        subprocess.run([ff, "-y", "-framerate", str(fps),
                        "-i", os.path.join(temp_dir, "f_%06d.png"),
                        "-i", audio_path, "-t", str(total_dur),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-b:v", "5M", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", mp4],
                       capture_output=True)

        shutil.rmtree(temp_dir, ignore_errors=True)
        self.on_log(f"\u2713 {os.path.basename(webm)}")
        self.on_log(f"\u2713 {os.path.basename(mp4)}")
        self.on_progress("\u2713 Completado!", 100)

    def _render_normal(self, audio_clip, ancho, alto, fps, duracion, total_dur,
                       timing, beat_times, rms, rms_times, esquema, fuente,
                       fuente_titulo, fuente_peq, parts, titulo, bg_image,
                       bg_video, bg_is_video, output, spot_on, spot_type,
                       spot_text, spot_subtext, spot_file, spot_secs):
        """Render en modo normal (MP4 con moviepy)."""
        from moviepy import VideoClip

        self.on_progress("Generando video...", 15)
        count = [0]

        def make_frame(t):
            if self.is_cancelled():
                raise KeyboardInterrupt

            if t >= duracion and spot_on:
                img = create_spot_frame(ancho, alto, t - duracion,
                                        spot_type, spot_text, spot_subtext, spot_file,
                                        platform_urls=cfg.get("platform_urls"))
                return np.array(img)

            cur_bg = bg_image
            if bg_is_video and bg_video:
                cur_bg = Image.fromarray(bg_video.get_frame(t % bg_video.duration))

            img = crear_frame_normal(ancho, alto, timing, t, duracion,
                                     beat_times, (rms, rms_times), esquema,
                                     fuente, fuente_titulo, fuente_peq,
                                     parts, titulo, cur_bg,
                                     effects=self.cfg.get("effects"))

            left = duracion - t
            if spot_on and left < 2.0:
                fa = int(255 * (1 - left / 2.0))
                ov = Image.new("RGBA", (ancho, alto), (0, 0, 0, fa))
                img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
            elif not spot_on and left < 3.0:
                fa = int(255 * (1 - left / 3.0))
                ov = Image.new("RGBA", (ancho, alto), (0, 0, 0, fa))
                img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

            count[0] += 1
            if count[0] % (fps * 2) == 0:
                pct = 15 + (t / total_dur) * 80
                self.on_progress(f"{t:.0f}s / {total_dur:.0f}s", pct)

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

            # Buscar timestamps Whisper con palabras individuales
            whisper_ts = os.path.splitext(audio_path)[0] + "_timestamps.json"
            ts_path = None

            if os.path.isfile(whisper_ts):
                with open(whisper_ts, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "palabras" in data and data["palabras"]:
                    ts_path = whisper_ts
                    self.on_log(f"  {len(data['palabras'])} palabras individuales")

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
