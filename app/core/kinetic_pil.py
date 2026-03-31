"""Kinetic Typography renderer usando PIL + FFmpeg raw pipe.

15-20x más rápido que Manim. Genera video frame-by-frame con PIL
y lo pipea directo a FFmpeg sin escribir frames a disco.
"""

import json
import math
import os
import random
import subprocess
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.utils.paths import get_ffmpeg, get_ffprobe

from app.utils.fonts import resolve_font_path, load_pil_font


# ── Esquemas de color ─────────────────────────────────────────────────────────

ESQUEMAS = {
    "neon": {
        "activo": "#00f5ff", "glow": "#ff00ff",
        "pasado": "#7a7aaa", "futuro": "#4a4a6a",
    },
    "fuego": {
        "activo": "#ff6b35", "glow": "#ffd460",
        "pasado": "#8b4513", "futuro": "#5a3a1a",
    },
    "nocturno": {
        "activo": "#e94560", "glow": "#ff6b81",
        "pasado": "#7a7a9a", "futuro": "#4a4a6a",
    },
    "elegante": {
        "activo": "#ffd700", "glow": "#ffed4a",
        "pasado": "#b8860b", "futuro": "#5a4a0a",
    },
    "oceano": {
        "activo": "#00bcd4", "glow": "#4dd0e1",
        "pasado": "#006064", "futuro": "#003a3a",
    },
}


# ── Easing functions ──────────────────────────────────────────────────────────

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_out_bounce(t):
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375

def ease_in_out(t):
    return t * t * (3 - 2 * t)


# ── Text cache ────────────────────────────────────────────────────────────────

class TextCache:
    """Cache de texto renderizado para evitar re-renderizar la misma palabra."""

    def __init__(self):
        self._cache = {}

    def get(self, text, font_path, size, color, bold=True):
        key = (text, font_path, size, color, bold)
        if key in self._cache:
            return self._cache[key]

        font, _ = load_pil_font(
            os.path.basename(font_path) if font_path else "Arial",
            size, bold=bold)

        # Renderizar texto con transparencia
        dummy = Image.new("RGBA", (10, 10))
        dd = ImageDraw.Draw(dummy)
        bbox = dd.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad = max(8, size // 4)

        img = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((pad - bbox[0], pad - bbox[1]), text, fill=color, font=font)

        self._cache[key] = img
        return img

    def clear(self):
        self._cache.clear()


# ── Beat detection ────────────────────────────────────────────────────────────

def detect_beats(audio_path):
    try:
        import librosa
        y, sr = librosa.load(audio_path, sr=22050)
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        return librosa.frames_to_time(beat_frames, sr=sr).tolist()
    except Exception:
        return []


def beat_intensity(t, beat_times, decay=0.15):
    for bt in beat_times:
        if bt > t + 0.01:
            break
        dt = t - bt
        if 0 <= dt < decay:
            return min(math.exp(-dt / (decay * 0.3)), 1.0)
    return 0.0


# ── Cargar timestamps ─────────────────────────────────────────────────────────

def load_timestamps(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "palabras" in data:
        palabras = [{"palabra": w["palabra"].strip(), "inicio": float(w["inicio"]),
                      "fin": float(w["fin"])}
                     for w in data["palabras"] if w.get("palabra", "").strip()]
        segmentos = [{"linea": s["texto"].strip(), "inicio": float(s["inicio"]),
                       "fin": float(s["fin"])}
                      for s in data.get("segmentos", []) if s.get("texto", "").strip()]
        return palabras, segmentos

    if isinstance(data, list):
        items = []
        for item in data:
            texto = item.get("linea") or item.get("texto") or item.get("palabra", "")
            if texto.strip():
                items.append({"linea": texto.strip(),
                              "inicio": float(item.get("inicio", 0)),
                              "fin": float(item.get("fin", 0))})
        if data and "palabra" in data[0]:
            return [{"palabra": i["linea"], "inicio": i["inicio"], "fin": i["fin"]}
                    for i in items], []
        return [], items

    return [], []


def group_smart_oneword(palabras, min_word_len=3, max_group=4, max_gap=0.3):
    """Agrupa palabras cortas con sus vecinas para formar frases con sentido.

    Whisper a veces divide palabras como 'así' en 'a' + 'sí', o deja
    palabras sueltas de 1-2 caracteres. Esta función las agrupa.
    """
    if not palabras:
        return []
    groups = []
    i = 0
    while i < len(palabras):
        group = [palabras[i]]
        # Si la palabra actual es corta, intentar agrupar con las siguientes
        while (len(group) < max_group and i + len(group) < len(palabras)):
            next_w = palabras[i + len(group)]
            last_w = group[-1]
            gap = next_w["inicio"] - last_w["fin"]
            # Agrupar si: palabra actual corta, o próxima corta, y gap pequeño
            current_text = " ".join(w["palabra"] for w in group)
            if (gap <= max_gap and
                (len(current_text) < min_word_len or
                 len(next_w["palabra"].strip()) < min_word_len)):
                group.append(next_w)
            else:
                break
        # Crear entrada agrupada
        texto = " ".join(w["palabra"].strip() for w in group)
        groups.append({
            "palabra": texto,
            "inicio": group[0]["inicio"],
            "fin": group[-1]["fin"],
        })
        i += len(group)
    return groups


def group_into_phrases(palabras, max_words=5, max_gap=0.8):
    if not palabras:
        return []
    frases = []
    current = [palabras[0]]
    for w in palabras[1:]:
        gap = w["inicio"] - current[-1]["fin"]
        if gap > max_gap or len(current) >= max_words:
            frases.append(current)
            current = [w]
        else:
            current.append(w)
    if current:
        frases.append(current)
    return frases


# ── Animation styles ──────────────────────────────────────────────────────────

def _anim_wave(progress, idx, ancho, alto):
    """Word rises from below with wave motion."""
    t = ease_out_cubic(min(1, progress * 3))
    y_off = int((1 - t) * 80)
    alpha = min(255, int(t * 255))
    x_off = int(math.sin(idx * 0.7) * 10 * (1 - t))
    return x_off, -y_off, 1.0, alpha

def _anim_zoom(progress, idx, ancho, alto):
    """Words pop in with scale + bounce."""
    t = ease_out_bounce(min(1, progress * 3))
    scale = 0.3 + 0.7 * t
    alpha = min(255, int(min(1, progress * 4) * 255))
    return 0, 0, scale, alpha

def _anim_slide(progress, idx, ancho, alto):
    """Text slides from alternating sides."""
    t = ease_out_cubic(min(1, progress * 3))
    direction = 1 if idx % 2 == 0 else -1
    x_off = int((1 - t) * ancho * 0.3 * direction)
    alpha = min(255, int(t * 255))
    return x_off, 0, 1.0, alpha

def _anim_fade(progress, idx, ancho, alto):
    """Soft fade-in with upward drift."""
    t = ease_in_out(min(1, progress * 2.5))
    y_off = int((1 - t) * 20)
    alpha = min(255, int(t * 255))
    return 0, -y_off, 1.0, alpha

def _anim_glitch(progress, idx, ancho, alto):
    """Digital distortion flash."""
    if progress < 0.15:
        random.seed(int(progress * 1000) + idx)
        x_off = random.randint(-15, 15)
        y_off = random.randint(-8, 8)
        alpha = random.randint(100, 255)
        return x_off, y_off, 1.0, alpha
    return 0, 0, 1.0, 255

def _anim_bounce(progress, idx, ancho, alto):
    """Words fall from above with physics."""
    t = ease_out_bounce(min(1, progress * 2.5))
    y_off = int((1 - t) * -200)
    alpha = min(255, int(min(1, progress * 3) * 255))
    return 0, y_off, 1.0, alpha

def _anim_typewriter(progress, idx, ancho, alto):
    """Letters appear one by one — handled specially in renderer."""
    return 0, 0, 1.0, 255

def _anim_cinematic(progress, idx, ancho, alto):
    """Dramatic word-by-word reveal with scale."""
    t = ease_out_cubic(min(1, progress * 2))
    scale = 1.3 - 0.3 * t
    alpha = min(255, int(t * 255))
    return 0, 0, scale, alpha

def _anim_oneword(progress, idx, ancho, alto):
    """Single word zoom-in."""
    t = ease_out_cubic(min(1, progress * 3))
    scale = 0.5 + 0.5 * t
    alpha = min(255, int(t * 255))
    return 0, 0, scale, alpha


ANIM_STYLES = {
    "wave": _anim_wave,
    "zoom": _anim_zoom,
    "slide": _anim_slide,
    "fade": _anim_fade,
    "glitch": _anim_glitch,
    "bounce": _anim_bounce,
    "typewriter": _anim_typewriter,
    "cinematic": _anim_cinematic,
    "oneword": _anim_oneword,
}


# ── Main renderer ─────────────────────────────────────────────────────────────

class KineticPILRenderer:
    """Renderiza kinetic typography frame-by-frame con PIL + FFmpeg pipe."""

    def __init__(self, config, on_progress=None, on_log=None, is_cancelled=None):
        self.cfg = config
        self.on_progress = on_progress or (lambda msg, pct: None)
        self.on_log = on_log or (lambda msg: None)
        self.is_cancelled = is_cancelled or (lambda: False)

        self.ancho = config["ancho"]
        self.alto = config["alto"]
        self.fps = config["fps"]
        self.font_path = resolve_font_path(config.get("fuente", "Arial")) or "arial.ttf"
        self.font_size = config.get("font_size", 50)
        self.estilo = config.get("estilo", "wave")
        self.esquema = ESQUEMAS.get(config.get("color", "neon"), ESQUEMAS["neon"])
        self.fondo_path = config.get("fondo_path")
        self.alpha_mode = config.get("alpha_mode", False)
        self.effects = config.get("effects")
        self.lyrics_pos = config.get("lyrics_pos", "Centro")
        self.lyrics_align = config.get("lyrics_align", "Centro")
        self.lyrics_margin = config.get("lyrics_margin", 40)
        self.lyrics_extra_y = config.get("lyrics_extra_y", 0)
        self._bg_is_video = False
        self._bg_cap = None
        self._bg_video_fps = 30
        self._bg_video_dur = 0
        self.cache = TextCache()

    @staticmethod
    def _get_audio_duration(audio_path):
        """Obtiene la duración real del audio usando ffprobe."""
        try:
            ffprobe = get_ffprobe()
            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", audio_path],
                capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def render(self):
        """Render completo: carga datos, genera frames, pipea a FFmpeg."""
        import time
        start = time.time()

        # Cargar timestamps
        ts_path = self.cfg["timestamps"]
        palabras, segmentos = load_timestamps(ts_path)
        total = len(palabras) + len(segmentos)
        if total == 0:
            self.on_log("ERROR: No hay timestamps")
            return None

        self.on_log(f"Modo: Kinetic PIL ({self.estilo})")
        self.on_log(f"{len(palabras)} palabras, {len(segmentos)} segmentos")

        # Detectar beats
        audio_path = self.cfg["audio"]
        self.on_progress("Analizando beats...", None)
        beat_times = detect_beats(audio_path)
        self.on_log(f"{len(beat_times)} beats detectados")

        # Calcular duración total basada en el audio real
        audio_dur = self._get_audio_duration(audio_path)
        if palabras:
            ts_dur = palabras[-1]["fin"] + 0.5
        elif segmentos:
            ts_dur = segmentos[-1]["fin"] + 0.5
        else:
            ts_dur = 10

        # Usar la mayor entre audio y timestamps
        total_dur = max(audio_dur, ts_dur) if audio_dur > 0 else ts_dur

        # Punto de inicio (desde dónde empieza el clip)
        start_offset = self.cfg.get("start_time", 0)

        # Limitar duración si el usuario lo configuró
        max_dur = self.cfg.get("max_dur", 0)
        is_completo = (max_dur <= 0)
        if max_dur > 0:
            # Si la canción es más corta que la duración elegida, usar la canción
            if max_dur > total_dur:
                self.on_log(f"Canción ({total_dur:.0f}s) más corta que {max_dur}s, "
                            f"usando duración real")
            else:
                total_dur = max_dur
            self.on_log(f"Duración: {total_dur:.0f}s desde {start_offset:.1f}s")
        end_time = start_offset + total_dur

        # Spot publicitario al final
        spot_on = self.cfg.get("spot_on", False)
        spot_secs = self.cfg.get("spot_secs", 5) if spot_on else 0
        song_dur = total_dur  # duración de la canción sin spot
        total_dur += spot_secs  # duración total con spot

        total_frames = int(total_dur * self.fps)
        self.on_log(f"Duración: {song_dur:.1f}s + {spot_secs}s spot "
                    f"= {total_dur:.1f}s (audio={audio_dur:.1f}s)")

        # Preparar fondo
        bg_img = self._load_background()

        # Agrupar palabras inteligentemente
        if self.estilo == "oneword":
            if palabras:
                palabras = group_smart_oneword(palabras)
                self.on_log(f"Oneword inteligente: {len(palabras)} grupos")
            elif segmentos:
                palabras = [{"inicio": s["inicio"], "fin": s["fin"],
                             "palabra": s.get("linea", s.get("texto", ""))}
                            for s in segmentos
                            if s.get("linea", s.get("texto", "")).strip()]
                self.on_log(f"Oneword fallback (segmentos): {len(palabras)} entradas")
        frases = group_into_phrases(palabras) if palabras else []

        # Output
        output = self.cfg["output"]
        ext = os.path.splitext(output)[1].lower()

        # FFmpeg command
        ffmpeg_cmd = self._build_ffmpeg_cmd(output, ext, audio_path, start_offset)
        self.on_log(f"Resolución: {self.ancho}x{self.alto} @ {self.fps}fps")
        self.on_log(f"Frames: {total_frames}")

        # Abrir pipe — stderr a DEVNULL para evitar deadlock
        # (FFmpeg llena el buffer stderr → bloquea stdin → deadlock)
        stderr_log = os.path.splitext(output)[0] + "_ffmpeg.log"
        stderr_file = open(stderr_log, "w", encoding="utf-8")
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=stderr_file)

        try:
            anim_fn = ANIM_STYLES.get(self.estilo, _anim_wave)
            mode = "RGBA" if self.alpha_mode else "RGB"
            update_every = max(1, self.fps)  # Actualizar progreso cada segundo

            for frame_idx in range(total_frames):
                if self.is_cancelled():
                    proc.stdin.close()
                    proc.terminate()
                    proc.wait()
                    stderr_file.close()
                    self.on_log("Cancelado")
                    self.on_progress("Cancelado", 0)
                    return None

                t = start_offset + frame_idx / self.fps

                if frame_idx % update_every == 0:
                    pct = int(frame_idx / total_frames * 100)
                    elapsed = int(time.time() - start)
                    self.on_progress(f"Renderizando... {pct}% ({elapsed}s)", pct)

                # Generar frame: spot o canción
                if spot_on and t >= song_dur:
                    from app.core.spot import create_spot_frame
                    frame = create_spot_frame(
                        self.ancho, self.alto, t - song_dur,
                        self.cfg.get("spot_type", "Texto"),
                        self.cfg.get("spot_text", ""),
                        self.cfg.get("spot_subtext", ""),
                        self.cfg.get("spot_file", ""),
                        platform_urls=self.cfg.get("platform_urls"))
                else:
                    if self.estilo == "oneword":
                        frame = self._render_oneword_frame(
                            t, bg_img, palabras, beat_times, anim_fn)
                    elif self.estilo == "oneline":
                        lineas_display = segmentos if segmentos else [
                            {"linea": " ".join(w["palabra"] for w in frase),
                             "inicio": frase[0]["inicio"], "fin": frase[-1]["fin"]}
                            for frase in frases]
                        frame = self._render_oneline_frame(
                            t, bg_img, lineas_display, beat_times, anim_fn)
                    else:
                        # Usar segmentos (líneas) para display multi-línea fiel al preview
                        lineas_display = segmentos if segmentos else [
                            {"linea": " ".join(w["palabra"] for w in frase),
                             "inicio": frase[0]["inicio"], "fin": frase[-1]["fin"]}
                            for frase in frases]
                        frame = self._render_phrase_frame(
                            t, bg_img, lineas_display, beat_times, anim_fn)

                    # Aplicar efectos
                    frame = self._apply_effects(frame, t, total_dur, beat_times)

                    remaining = song_dur - t

                    # Fade out en los últimos 2s (solo cuando NO es Completo)
                    if not is_completo:
                        fade_dur = 2.0
                        if remaining < fade_dur and remaining > 0:
                            fade_alpha = remaining / fade_dur
                            frame = Image.blend(
                                Image.new(frame.mode, frame.size, (0, 0, 0)),
                                frame, fade_alpha)
                    # Fade in al spot (transición suave)
                    elif spot_on and remaining <= 0 and remaining > -0.5:
                        fade_alpha = abs(remaining) / 0.5
                        from app.core.spot import create_spot_frame
                        spot_f = create_spot_frame(
                            self.ancho, self.alto, 0,
                            self.cfg.get("spot_type", "Texto"),
                            self.cfg.get("spot_text", ""),
                            self.cfg.get("spot_subtext", ""),
                            self.cfg.get("spot_file", ""),
                            platform_urls=self.cfg.get("platform_urls"))
                        frame = Image.blend(frame, spot_f, fade_alpha)

                # Asegurar modo correcto antes de escribir
                if frame.mode != mode:
                    frame = frame.convert(mode)

                # Escribir frame raw a pipe
                try:
                    proc.stdin.write(frame.tobytes())
                except (BrokenPipeError, OSError):
                    self.on_log("FFmpeg cerró el pipe (posible error)")
                    break

            proc.stdin.close()
            self.on_progress("Finalizando video (FFmpeg)...", 99)
            self.on_log("Frames enviados, esperando FFmpeg...")
            # Esperar con timeout para no colgarse infinitamente
            try:
                proc.wait(timeout=120)  # 2 min max para finalizar
            except subprocess.TimeoutExpired:
                self.on_log("FFmpeg tardó demasiado, terminando...")
                proc.terminate()
                proc.wait(timeout=10)
            stderr_file.close()

            # Liberar cap de video si se usó
            if self._bg_cap is not None:
                try:
                    self._bg_cap.release()
                except Exception:
                    pass
                self._bg_cap = None

            elapsed = int(time.time() - start)
            if proc.returncode == 0 and os.path.isfile(output):
                self.on_log(f"Completado en {elapsed}s")
                self.on_progress("Completado!", 100)
                # Limpiar log si todo OK
                try:
                    os.remove(stderr_log)
                except OSError:
                    pass
                return output
            else:
                # Leer log de error
                try:
                    with open(stderr_log, "r", encoding="utf-8") as f:
                        err = f.read()[-500:]
                    self.on_log(f"FFmpeg error: {err}")
                except Exception:
                    self.on_log("FFmpeg error: código de salida "
                                f"{proc.returncode}")
                self.on_progress("Error", 0)
                return None

        except Exception as ex:
            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.terminate()
            proc.wait()
            stderr_file.close()
            self.on_log(f"Error: {ex}")
            raise

    def _build_ffmpeg_cmd(self, output, ext, audio_path, start_offset=0):
        pix_fmt_in = "rgba" if self.alpha_mode else "rgb24"
        max_dur = self.cfg.get("max_dur", 0)
        spot_on = self.cfg.get("spot_on", False)

        cmd = [
            get_ffmpeg(),
            "-y", "-f", "rawvideo",
            "-pix_fmt", pix_fmt_in,
            "-s", f"{self.ancho}x{self.alto}",
            "-r", str(self.fps),
            "-i", "-",  # stdin
        ]
        # Audio: seek si hay start_offset
        if start_offset > 0:
            cmd += ["-ss", f"{start_offset:.3f}"]
        cmd += ["-i", audio_path, "-shortest"]

        # Audio fade out (3s) cuando no es completo o hay spot
        fade_dur = 3.0
        total_audio = max_dur if max_dur > 0 else 0
        if total_audio > 0 or spot_on:
            fade_start = max(0, (total_audio or 999) - fade_dur)
            cmd += ["-af", f"afade=t=out:st={fade_start:.2f}:d={fade_dur:.1f}"]

        if ext == ".webm":
            cmd += ["-c:v", "libvpx-vp9", "-b:v", "2M", "-c:a", "libvorbis"]
            if self.alpha_mode:
                cmd += ["-pix_fmt", "yuva420p", "-auto-alt-ref", "0"]
            else:
                cmd += ["-pix_fmt", "yuv420p"]
        elif ext == ".mov":
            cmd += ["-c:v", "prores_ks", "-profile:v", "4444",
                    "-c:a", "aac", "-pix_fmt", "yuva444p10le"]
        elif ext == ".avi":
            cmd += ["-c:v", "mpeg4", "-q:v", "5", "-c:a", "mp3"]
        else:  # mp4
            cmd += ["-c:v", "libx264", "-preset", "fast",
                    "-crf", "18", "-c:a", "aac", "-pix_fmt", "yuv420p"]

        cmd.append(output)
        return cmd

    def _load_background(self):
        mode = "RGBA" if self.alpha_mode else "RGB"
        bg_color = (0, 0, 0, 0) if self.alpha_mode else (8, 8, 16)

        if self.fondo_path and os.path.isfile(self.fondo_path):
            ext = os.path.splitext(self.fondo_path)[1].lower()

            # Video de fondo
            if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
                try:
                    import cv2
                    cap = cv2.VideoCapture(self.fondo_path)
                    if cap.isOpened():
                        self._bg_is_video = True
                        self._bg_cap = cap
                        self._bg_video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
                        total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        self._bg_video_dur = total_f / self._bg_video_fps if self._bg_video_fps > 0 else 1
                        self._bg_mode = mode
                        self._bg_size = (self.ancho, self.alto)
                        # Imagen de relleno para _fast_bg_copy (no se usa en video mode)
                        fallback = Image.new(mode, (self.ancho, self.alto), bg_color)
                        self._bg_bytes = fallback.tobytes()
                        return fallback
                except Exception:
                    pass

            # Imagen de fondo
            try:
                bg = Image.open(self.fondo_path).resize(
                    (self.ancho, self.alto), Image.LANCZOS).convert(mode)
                from PIL import ImageEnhance
                dim = self.effects.get("dim_bg", True) if self.effects else True
                brightness = 0.2 if dim else 1.0
                bg = ImageEnhance.Brightness(bg).enhance(brightness)
                self._bg_bytes = bg.tobytes()
                self._bg_mode = mode
                self._bg_size = (self.ancho, self.alto)
                return bg
            except Exception:
                pass

        bg = Image.new(mode, (self.ancho, self.alto), bg_color)
        self._bg_bytes = bg.tobytes()
        self._bg_mode = mode
        self._bg_size = (self.ancho, self.alto)
        return bg

    def _fast_bg_copy(self):
        """Copia rápida del fondo usando frombytes (más rápido que PIL .copy())."""
        return Image.frombytes(self._bg_mode, self._bg_size, self._bg_bytes)

    def _get_bg_frame(self, t):
        """Retorna el frame de fondo para el tiempo t (con loop para videos)."""
        if self._bg_is_video and self._bg_cap is not None:
            try:
                import cv2
                from PIL import ImageEnhance
                t_video = t % self._bg_video_dur if self._bg_video_dur > 0 else 0
                frame_idx = int(t_video * self._bg_video_fps)
                self._bg_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self._bg_cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame).resize(
                        (self.ancho, self.alto), Image.LANCZOS)
                    dim = self.effects.get("dim_bg", True) if self.effects else True
                    brightness = 0.2 if dim else 1.0
                    img = ImageEnhance.Brightness(img.convert(self._bg_mode)).enhance(brightness)
                    return img
            except Exception:
                pass
        return self._fast_bg_copy()

    def _calc_lyrics_y(self, total_h):
        """Calcula el Y de inicio del bloque de letras según posición configurada."""
        pos = self.lyrics_pos
        margin = self.lyrics_margin
        offset = self.lyrics_extra_y
        if pos == "Arriba":
            base_y = margin
        elif pos == "Abajo":
            base_y = self.alto - total_h - margin
        else:
            base_y = (self.alto - total_h) // 2
        base_y += offset
        return max(0, min(self.alto - max(total_h, 1), base_y))

    def _calc_lyrics_x(self, text_w):
        """Calcula (cx, anchor_h) según alineación horizontal configurada.

        Retorna (cx, anchor_h) donde anchor_h es 'l', 'm' o 'r' (PIL).
        """
        align = getattr(self, 'lyrics_align', 'Centro')
        margin = self.lyrics_margin
        if align == "Izquierda":
            cx = margin
            anchor_h = "l"
        elif align == "Derecha":
            cx = self.ancho - margin
            anchor_h = "r"
        else:
            cx = self.ancho // 2
            anchor_h = "m"
        cx = max(margin, min(self.ancho - margin, cx))
        return cx, anchor_h

    def _draw_kinetic_text_box(self, frame, cx, y, text_w, text_h):
        """Dibuja recuadro detrás del texto kinetic si está activado."""
        if not (self.effects and self.effects.get("text_box", False)):
            return frame
        opacity = int(self.effects.get("text_box_opacity", 70) * 2.55)
        radius = int(self.effects.get("text_box_radius", 8))
        pad_x, pad_y = 18, 6
        x1 = cx - text_w // 2 - pad_x
        y1 = y - pad_y
        x2 = cx + text_w // 2 + pad_x
        y2 = y + text_h + pad_y
        # Color oscuro de fondo para kinetic
        box_color = (0, 0, 0)
        overlay = Image.new('RGBA', frame.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        r_min = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
        fill = (*box_color, opacity)
        if r_min > 0:
            odraw.rounded_rectangle([x1, y1, x2, y2], radius=r_min, fill=fill)
        else:
            odraw.rectangle([x1, y1, x2, y2], fill=fill)
        if frame.mode == 'RGBA':
            return Image.alpha_composite(frame, overlay)
        return Image.alpha_composite(frame.convert('RGBA'), overlay).convert('RGB')

    def _make_font(self, size):
        try:
            return ImageFont.truetype(self.font_path, size)
        except Exception:
            return ImageFont.truetype("arial.ttf", size)

    def _render_text_img(self, text, size, color):
        """Renderiza texto como imagen RGBA con cache."""
        return self.cache.get(text, self.font_path, size, color)

    def _composite_text(self, base, text_img, cx, cy, scale=1.0, alpha=255):
        """Compone texto centrado en (cx, cy) con escala y alpha."""
        if scale != 1.0:
            nw = max(1, int(text_img.width * scale))
            nh = max(1, int(text_img.height * scale))
            text_img = text_img.resize((nw, nh), Image.BILINEAR)

        if alpha < 255:
            text_img = text_img.copy()
            a = text_img.split()[3]
            a = a.point(lambda p: int(p * alpha / 255))
            text_img.putalpha(a)

        x = cx - text_img.width // 2
        y = cy - text_img.height // 2
        base.paste(text_img, (x, y), text_img)

    def _render_oneword_frame(self, t, bg_img, palabras, beat_times, anim_fn):
        """Frame para estilo One Word: una palabra gigante centrada."""
        frame = self._get_bg_frame(t)
        if not palabras:
            return frame

        # Encontrar palabra activa
        word = None
        prev_word = None
        for w in palabras:
            if w["inicio"] <= t <= w["fin"]:
                word = w
                break
            if w["inicio"] > t:
                # Entre palabras: mostrar la anterior
                if prev_word:
                    word = prev_word
                else:
                    word = w  # antes del inicio: mostrar la primera
                break
            prev_word = w
        if not word and palabras:
            word = palabras[-1]  # después del final: mostrar la última

        if not word:
            return frame

        texto = word["palabra"].strip(" ,.:;!?")
        if not texto:
            return frame

        dur = word["fin"] - word["inicio"]
        progress = (t - word["inicio"]) / max(dur, 0.05)
        x_off, y_off, scale, alpha = anim_fn(progress, 0, self.ancho, self.alto)

        # Tamaño grande proporcional al font_size del slider
        big_size = self.font_size * 2

        # Renderizar
        text_img = self._render_text_img(texto, big_size, self.esquema["activo"])

        # Verificar que no exceda el ancho
        if text_img.width * scale > self.ancho * 0.85:
            scale *= (self.ancho * 0.85) / (text_img.width * scale)

        cx = self.ancho // 2 + x_off
        base_cy = self._calc_lyrics_y(big_size) + big_size // 2
        cy = base_cy + y_off

        # Beat pulse
        bi = beat_intensity(t, beat_times)
        if bi > 0.3:
            scale *= 1.0 + bi * 0.12

        # Recuadro detrás del texto
        actual_w = int(text_img.width * scale)
        actual_h = int(text_img.height * scale)
        frame = self._draw_kinetic_text_box(frame, cx, cy - actual_h // 2, actual_w, actual_h)

        # Glow (cacheado: blur es costoso)
        if alpha > 50:
            glow_key = (texto, big_size, "glow_blur")
            if glow_key not in self.cache._cache:
                glow_img = self._render_text_img(
                    texto, big_size, self.esquema["glow"])
                self.cache._cache[glow_key] = glow_img.filter(
                    ImageFilter.GaussianBlur(radius=8))
            glow_blurred = self.cache._cache[glow_key]
            self._composite_text(frame, glow_blurred, cx, cy,
                                 scale=scale, alpha=min(alpha, 80))

        self._composite_text(frame, text_img, cx, cy, scale=scale, alpha=alpha)

        return frame

    def _render_oneline_frame(self, t, bg_img, lineas, beat_times, anim_fn):
        """Frame One Line: solo la línea activa, centrada, las demás invisibles."""
        frame = self._get_bg_frame(t)
        if not lineas:
            return frame

        # Buscar línea activa
        activa = None
        for linea in lineas:
            ini = linea.get("inicio", 0)
            fin = linea.get("fin", 0)
            if ini <= t <= fin:
                activa = linea
                break

        if not activa:
            return frame

        texto = (activa.get("linea") or activa.get("texto") or "").strip()
        if not texto:
            return frame

        dur = max(activa["fin"] - activa["inicio"], 0.05)
        progress = (t - activa["inicio"]) / dur
        progress = max(0.0, min(1.0, progress))
        x_off, y_off, scale, alpha = anim_fn(progress, 0, self.ancho, self.alto)

        # Renderizar texto al tamaño normal del slider
        text_img = self._render_text_img(texto, self.font_size, self.esquema["activo"])

        # Ajustar si el texto es más ancho que la pantalla
        max_w = self.ancho * 0.9
        if text_img.width * scale > max_w:
            scale *= max_w / (text_img.width * scale)

        cx_base, _anchor_h = self._calc_lyrics_x(int(text_img.width * scale))
        cx = cx_base + x_off
        base_cy = self._calc_lyrics_y(self.font_size) + self.font_size // 2
        cy = base_cy + y_off

        # Beat pulse
        bi = beat_intensity(t, beat_times)
        if bi > 0.3:
            scale *= 1.0 + bi * 0.08

        # Recuadro
        actual_w = int(text_img.width * scale)
        actual_h = int(text_img.height * scale)
        frame = self._draw_kinetic_text_box(frame, cx, cy - actual_h // 2, actual_w, actual_h)

        # Glow
        if self.effects and self.effects.get("glow") and alpha > 50:
            glow_key = (texto, self.font_size, "oneline_glow")
            if glow_key not in self.cache._cache:
                glow_img = self._render_text_img(texto, self.font_size, self.esquema["glow"])
                self.cache._cache[glow_key] = glow_img.filter(
                    ImageFilter.GaussianBlur(radius=6))
            self._composite_text(frame, self.cache._cache[glow_key], cx, cy,
                                 scale=scale, alpha=min(alpha, 80))

        self._composite_text(frame, text_img, cx, cy, scale=scale, alpha=alpha)
        return frame

    def _render_phrase_frame(self, t, bg_img, lineas, beat_times, anim_fn):
        """Frame multi-línea: muestra ventana de líneas con la activa destacada (idéntico al preview)."""
        frame = self._get_bg_frame(t)
        if not lineas:
            return frame

        # Encontrar línea activa
        active_idx = 0
        for i, ln in enumerate(lineas):
            inicio = float(ln.get("inicio", 0))
            fin = float(ln.get("fin", 0))
            if inicio <= t <= fin + 0.5:
                active_idx = i
                break
            if inicio > t:
                active_idx = max(0, i - 1)
                break
        else:
            active_idx = len(lineas) - 1

        # Ventana de líneas visibles (igual que preview: 2 líneas antes de la activa)
        max_visible = 7
        start = max(0, active_idx - 2)
        end = min(len(lineas), start + max_visible)

        line_h = int(self.font_size * 1.6)
        total_h = (end - start) * line_h
        y_start = self._calc_lyrics_y(total_h)

        font = self._make_font(self.font_size)
        bi = beat_intensity(t, beat_times)

        for vi, li in enumerate(range(start, end)):
            ln = lineas[li]
            texto = ln.get("linea", ln.get("texto", ""))
            if not texto.strip():
                continue
            y = y_start + vi * line_h

            is_active = (li == active_idx)
            is_past = li < active_idx

            # Escalar fuente si el texto es muy ancho
            tmp = self._render_text_img(texto, self.font_size,
                                        self.esquema["activo"])
            scale = min(1.0, (self.ancho * 0.88) / tmp.width) if tmp.width > 0 else 1.0
            sz = int(self.font_size * scale)
            if is_active:
                # Tamaño ligeramente mayor para la línea activa
                sz = int(sz * 1.15)

            # Alineación horizontal
            cx_line, _ah = self._calc_lyrics_x(int(tmp.width * scale))

            # Recuadro detrás del texto
            if self.effects and self.effects.get("text_box", False):
                text_w = int(tmp.width * scale)
                if is_active:
                    text_w = int(text_w * 1.15)  # Igualar al tamaño real de la línea activa
                frame = self._draw_kinetic_text_box(frame, cx_line,
                                                    y, text_w, line_h)

            if is_active:
                color = self.esquema["activo"]
                # Progreso dentro de la línea activa para la animación
                ln_inicio = float(ln.get("inicio", 0))
                ln_fin = float(ln.get("fin", ln_inicio + 1))
                dur_ln = max(ln_fin - ln_inicio, 0.05)
                progress = min(1.0, max(0.0, (t - ln_inicio) / dur_ln))
                x_off, y_off, anim_scale, anim_alpha = anim_fn(progress, 0,
                                                                self.ancho, self.alto)

                # Typewriter: mostrar texto parcialmente
                if self.estilo == "typewriter" and progress < 1.0:
                    chars = max(1, int(progress * len(texto)))
                    texto_anim = texto[:chars]
                else:
                    texto_anim = texto

                final_sz = int(sz * anim_scale)
                # Beat pulse
                if bi > 0.3:
                    final_sz = int(final_sz * (1.0 + bi * 0.06))
                alpha = max(60, int(anim_alpha))

                # Glow
                glow_key = (texto_anim, final_sz, "glow_ml")
                if glow_key not in self.cache._cache:
                    gi = self._render_text_img(texto_anim, final_sz,
                                               self.esquema["glow"])
                    self.cache._cache[glow_key] = gi.filter(
                        ImageFilter.GaussianBlur(radius=6))
                self._composite_text(frame, self.cache._cache[glow_key],
                                     cx_line + x_off,
                                     y + line_h // 2 + y_off,
                                     scale=1.0, alpha=60)

                text_img = self._render_text_img(texto_anim, final_sz, color)
                self._composite_text(frame, text_img,
                                     cx_line + x_off,
                                     y + line_h // 2 + y_off,
                                     scale=1.0, alpha=alpha)
            elif is_past:
                color = self.esquema["pasado"]
                alpha = 160
                text_img = self._render_text_img(texto, sz, color)
                self._composite_text(frame, text_img,
                                     cx_line, y + line_h // 2,
                                     scale=1.0, alpha=alpha)
            else:
                color = self.esquema["futuro"]
                alpha = 110
                text_img = self._render_text_img(texto, sz, color)
                self._composite_text(frame, text_img,
                                     cx_line, y + line_h // 2,
                                     scale=1.0, alpha=alpha)

        return frame

    def _draw_phrase_text(self, frame, frase, y, color, alpha):
        """Dibuja una frase completa en color uniforme."""
        texto = " ".join(w["palabra"] for w in frase)
        text_img = self._render_text_img(texto, self.font_size, color)

        # Escalar si muy ancho
        scale = 1.0
        if text_img.width > self.ancho * 0.85:
            scale = (self.ancho * 0.85) / text_img.width

        self._composite_text(frame, text_img, self.ancho // 2, y,
                             scale=scale, alpha=alpha)

    def _draw_active_phrase(self, frame, frase, y, t, beat_times, anim_fn):
        """Dibuja la frase activa con animación por palabra."""
        # Calcular posiciones de cada palabra (cacheado por frase)
        frase_key = tuple(w["palabra"] for w in frase)
        if not hasattr(self, "_phrase_metrics_cache"):
            self._phrase_metrics_cache = {}
        if frase_key not in self._phrase_metrics_cache:
            font = self._make_font(self.font_size)
            dummy_img = Image.new("RGBA", (10, 10))
            dd = ImageDraw.Draw(dummy_img)
            space_w = dd.textlength(" ", font=font)
            word_widths = []
            for w in frase:
                bbox = dd.textbbox((0, 0), w["palabra"], font=font)
                word_widths.append(bbox[2] - bbox[0])
            self._phrase_metrics_cache[frase_key] = (word_widths, space_w)
        word_widths, space_w = self._phrase_metrics_cache[frase_key]

        total_w = sum(word_widths) + space_w * (len(frase) - 1)

        # Escalar si muy ancho
        scale_factor = 1.0
        if total_w > self.ancho * 0.85:
            scale_factor = (self.ancho * 0.85) / total_w

        x_start = (self.ancho - total_w * scale_factor) / 2

        x = x_start
        for i, w in enumerate(frase):
            texto = w["palabra"]
            w_inicio = w["inicio"]
            w_fin = w["fin"]
            dur = max(w_fin - w_inicio, 0.05)
            ww = word_widths[i] * scale_factor

            cx = int(x + ww / 2)

            if t >= w_inicio:
                # Palabra activa o pasada
                progress = min(1.0, (t - w_inicio) / dur)
                x_off, y_off, anim_scale, alpha = anim_fn(progress, i,
                                                            self.ancho, self.alto)

                # Typewriter: mostrar parcialmente
                if self.estilo == "typewriter" and t < w_fin:
                    chars_shown = max(1, int(progress * len(texto)))
                    texto = texto[:chars_shown]

                color = self.esquema["activo"]
                text_img = self._render_text_img(texto, self.font_size, color)

                # Beat pulse
                bi = beat_intensity(t, beat_times)
                final_scale = scale_factor * anim_scale
                if bi > 0.4 and t <= w_fin:
                    final_scale *= 1.0 + bi * 0.08

                # Glow para palabra activa (cacheado)
                if t <= w_fin and alpha > 100:
                    glow_key = (texto, self.font_size, "glow_blur_phrase")
                    if glow_key not in self.cache._cache:
                        glow_img = self._render_text_img(
                            texto, self.font_size, self.esquema["glow"])
                        self.cache._cache[glow_key] = glow_img.filter(
                            ImageFilter.GaussianBlur(6))
                    glow_b = self.cache._cache[glow_key]
                    self._composite_text(frame, glow_b,
                                         cx + x_off, y + y_off,
                                         scale=final_scale,
                                         alpha=min(alpha, 60))

                self._composite_text(frame, text_img,
                                     cx + x_off, y + y_off,
                                     scale=final_scale, alpha=alpha)
            else:
                # Palabra futura — dimmed
                text_img = self._render_text_img(
                    texto, self.font_size, self.esquema["futuro"])
                self._composite_text(frame, text_img, cx, y,
                                     scale=scale_factor, alpha=80)

            x += ww + space_w * scale_factor

    def _build_vignette(self):
        """Pre-renderiza viñeta una sola vez (cacheada como RGBA para paste).
        Parámetros idénticos al preview (_apply_kinetic_effects)."""
        if hasattr(self, "_vignette_cache"):
            return self._vignette_cache
        vignette = Image.new("RGBA", (self.ancho, self.alto), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        for i in range(40):
            a = int(180 * (1 - i / 40))  # Idéntico al preview (_apply_kinetic_effects)
            vd.rectangle([i, i, self.ancho - i, self.alto - i],
                         outline=(0, 0, 0, a))
        self._vignette_cache = vignette
        return self._vignette_cache

    def _apply_effects(self, frame, t, total_dur, beat_times):
        """Aplica efectos visuales (viñeta, partículas, onda, barra)."""
        effects = self.effects
        if not effects:
            return frame

        draw = ImageDraw.Draw(frame)

        # Viñeta (pre-cacheada, paste directo sin alpha_composite)
        if effects.get("vineta", False):
            vignette = self._build_vignette()
            frame.paste(vignette, (0, 0), vignette)

        # Glow global (downscale → blur → upscale, cada 3 frames para performance)
        # Parámetros alineados con preview: blend factor 0.15
        if effects.get("glow", False):
            frame_idx = int(t * self.fps)
            if frame_idx % 3 == 0 or not hasattr(self, "_glow_cache"):
                gw, gh = self.ancho // 4, self.alto // 4
                small = frame.resize((gw, gh), Image.BILINEAR)
                small = small.filter(ImageFilter.GaussianBlur(3))
                self._glow_cache = small.resize(
                    (self.ancho, self.alto), Image.BILINEAR)
            frame = Image.blend(frame, self._glow_cache, 0.15)

        # Partículas — idéntico al preview: 25 partículas con alpha variable
        if effects.get("particulas", False):
            draw = ImageDraw.Draw(frame)
            random.seed(int(t * 10))
            color_p = self.esquema.get("activo", "#ffffff") if isinstance(self.esquema, dict) else "#ffffff"
            for _ in range(25):
                px = random.randint(0, self.ancho)
                py = random.randint(0, self.alto)
                sz = random.randint(1, 3)
                alpha_hex = format(random.randint(40, 160), '02x')
                draw.ellipse([px, py, px + sz, py + sz],
                             fill=color_p + alpha_hex)

        # Onda — parámetros idénticos al preview
        if effects.get("onda", False):
            draw = ImageDraw.Draw(frame)
            y_base = self.alto - 30
            color_w = self.esquema.get("glow", "#4040ff") if isinstance(self.esquema, dict) else "#4040ff"
            for x in range(0, self.ancho, 2):
                y_w = y_base + int(8 * math.sin((x + t * 100) * 0.03))
                draw.line([(x, y_w), (x + 2, y_w)],
                          fill=color_w + "60", width=2)

        # Barra de progreso
        if effects.get("barra", False):
            draw = ImageDraw.Draw(frame)
            progress = min(1.0, t / total_dur) if total_dur > 0 else 0
            bar_y = self.alto - 5
            bar_w = int(self.ancho * progress)
            draw.rectangle([0, bar_y, self.ancho, self.alto], fill="#1a1a2e")
            if bar_w > 0:
                draw.rectangle([0, bar_y, bar_w, self.alto],
                               fill=self.esquema.get("activo", "#e94560"))

        return frame


    def render_single_frame(self, t, ts_path, total_dur=180):
        """Renderiza UN frame en el tiempo t — idéntico al video real (para preview)."""
        # Cargar timestamps
        if ts_path and os.path.isfile(ts_path):
            palabras, segmentos = load_timestamps(ts_path)
        else:
            palabras, segmentos = [], []

        # Agrupar igual que en render()
        if self.estilo == "oneword":
            if palabras:
                palabras = group_smart_oneword(palabras)
            elif segmentos:
                palabras = [{"inicio": s["inicio"], "fin": s["fin"],
                             "palabra": s.get("linea", s.get("texto", ""))}
                            for s in segmentos
                            if s.get("linea", s.get("texto", "")).strip()]
        frases = group_into_phrases(palabras) if palabras else []

        # Preparar fondo (inicializa _bg_is_video, _bg_cap, etc.)
        self._load_background()

        # Beat times vacíos para preview (sin análisis de audio)
        beat_times = []

        # Función de animación
        anim_fn = ANIM_STYLES.get(self.estilo, _anim_wave)

        # Líneas para display (segmentos > frases)
        lineas_display = segmentos if segmentos else [
            {"linea": " ".join(w["palabra"] for w in frase),
             "inicio": frase[0]["inicio"], "fin": frase[-1]["fin"]}
            for frase in frases]

        # Generar frame
        if not palabras and not lineas_display:
            frame = self._get_bg_frame(t)
        elif self.estilo == "oneword":
            frame = self._render_oneword_frame(t, None, palabras, beat_times, anim_fn)
        elif self.estilo == "oneline":
            frame = self._render_oneline_frame(t, None, lineas_display, beat_times, anim_fn)
        else:
            frame = self._render_phrase_frame(t, None, lineas_display, beat_times, anim_fn)

        # Efectos visuales
        frame = self._apply_effects(frame, t, total_dur, beat_times)

        # Liberar captura de video si la hay
        if self._bg_cap:
            self._bg_cap.release()
            self._bg_cap = None

        return frame


# ── Entry point ───────────────────────────────────────────────────────────────

def render_kinetic_pil(config, on_progress=None, on_log=None, is_cancelled=None):
    """Función principal para llamar desde video.py."""
    renderer = KineticPILRenderer(config, on_progress, on_log, is_cancelled)
    return renderer.render()
