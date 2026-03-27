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
        self.cache = TextCache()

    @staticmethod
    def _get_audio_duration(audio_path):
        """Obtiene la duración real del audio usando ffprobe."""
        try:
            ffprobe = shutil.which("ffprobe") or "ffprobe"
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
            palabras = group_smart_oneword(palabras)
            self.on_log(f"Oneword inteligente: {len(palabras)} grupos")
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
                    else:
                        frame = self._render_phrase_frame(
                            t, bg_img, frases, beat_times, anim_fn)

                    # Aplicar efectos
                    frame = self._apply_effects(frame, t, total_dur, beat_times)

                    # Fade out en los últimos 2s (solo cuando NO es Completo)
                    if not is_completo:
                        fade_dur = 2.0
                        remaining = song_dur - t
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

        cmd = [
            shutil.which("ffmpeg") or "ffmpeg",
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
            try:
                bg = Image.open(self.fondo_path).resize(
                    (self.ancho, self.alto), Image.LANCZOS).convert(mode)
                from PIL import ImageEnhance
                bg = ImageEnhance.Brightness(bg).enhance(0.25)
                return bg
            except Exception:
                pass
        return Image.new(mode, (self.ancho, self.alto), bg_color)

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
            text_img = text_img.resize((nw, nh), Image.LANCZOS)

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
        frame = bg_img.copy()
        if not palabras:
            return frame

        # Encontrar palabra activa
        word = None
        for w in palabras:
            if w["inicio"] <= t <= w["fin"]:
                word = w
                break
            if w["inicio"] > t:
                break

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
        cy = self.alto // 2 + y_off

        # Beat pulse
        bi = beat_intensity(t, beat_times)
        if bi > 0.3:
            scale *= 1.0 + bi * 0.12

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

    def _render_phrase_frame(self, t, bg_img, frases, beat_times, anim_fn):
        """Frame para estilos por frase (wave, zoom, slide, etc.)."""
        frame = bg_img.copy()
        if not frases:
            return frame

        # Encontrar frase activa
        active_frase_idx = 0
        for i, frase in enumerate(frases):
            if frase[0]["inicio"] <= t <= frase[-1]["fin"] + 0.3:
                active_frase_idx = i
                break
            if frase[0]["inicio"] > t:
                active_frase_idx = max(0, i - 1)
                break
        else:
            if frases and t > frases[-1][-1]["fin"]:
                active_frase_idx = len(frases) - 1

        # Ventana de frases visibles
        max_visible = 5
        start = max(0, active_frase_idx - 1)
        end = min(len(frases), start + max_visible)
        visible = list(range(start, end))

        line_h = int(self.font_size * 1.8)
        y_center = self.alto // 2
        y_start = y_center - (len(visible) * line_h) // 2

        for vi, fi in enumerate(visible):
            frase = frases[fi]
            y_line = y_start + vi * line_h

            if fi < active_frase_idx:
                # Frase pasada
                self._draw_phrase_text(frame, frase, y_line,
                                       self.esquema["pasado"], 150)
            elif fi > active_frase_idx:
                # Frase futura
                self._draw_phrase_text(frame, frase, y_line,
                                       self.esquema["futuro"], 100)
            else:
                # Frase activa — word by word
                self._draw_active_phrase(frame, frase, y_line, t,
                                         beat_times, anim_fn)

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
        # Calcular posiciones de cada palabra
        font = self._make_font(self.font_size)
        dummy_img = Image.new("RGBA", (10, 10))
        dd = ImageDraw.Draw(dummy_img)
        space_w = dd.textlength(" ", font=font)

        word_widths = []
        for w in frase:
            bbox = dd.textbbox((0, 0), w["palabra"], font=font)
            word_widths.append(bbox[2] - bbox[0])

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

                # Glow para palabra activa
                if t <= w_fin and alpha > 100:
                    glow_img = self._render_text_img(
                        texto, self.font_size, self.esquema["glow"])
                    glow_b = glow_img.filter(ImageFilter.GaussianBlur(6))
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
        """Pre-renderiza viñeta una sola vez (cacheada)."""
        if hasattr(self, "_vignette_cache"):
            return self._vignette_cache
        vignette = Image.new("RGBA", (self.ancho, self.alto), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        for i in range(30):
            a = int(150 * (1 - i / 30))
            vd.rectangle([i, i, self.ancho - i, self.alto - i],
                         outline=(0, 0, 0, a))
        self._vignette_cache = vignette
        return vignette

    def _apply_effects(self, frame, t, total_dur, beat_times):
        """Aplica efectos visuales (viñeta, partículas, onda, barra)."""
        effects = self.effects
        if not effects:
            return frame

        draw = ImageDraw.Draw(frame)

        # Viñeta (pre-cacheada, no recalcular cada frame)
        if effects.get("vineta", False):
            vignette = self._build_vignette()
            frame = Image.alpha_composite(frame.convert("RGBA"), vignette)
            if not self.alpha_mode:
                frame = frame.convert("RGB")

        # Glow global
        if effects.get("glow", False):
            glow = frame.filter(ImageFilter.GaussianBlur(12))
            from PIL import ImageEnhance
            glow = ImageEnhance.Brightness(glow).enhance(1.2)
            frame = Image.blend(frame, glow, 0.12)

        # Partículas
        if effects.get("particulas", False):
            draw = ImageDraw.Draw(frame)
            random.seed(int(t * 10))
            for _ in range(20):
                px = random.randint(0, self.ancho)
                py = random.randint(0, self.alto)
                sz = random.randint(1, 3)
                draw.ellipse([px, py, px + sz, py + sz],
                             fill=self.esquema["activo"])

        # Onda
        if effects.get("onda", False):
            draw = ImageDraw.Draw(frame)
            y_base = self.alto - 25
            for x in range(0, self.ancho, 3):
                y = y_base + int(6 * math.sin((x + t * 80) * 0.03))
                draw.line([(x, y), (x + 3, y)],
                          fill=self.esquema["glow"], width=2)

        # Barra de progreso
        if effects.get("barra", False):
            draw = ImageDraw.Draw(frame)
            progress = min(1.0, t / total_dur) if total_dur > 0 else 0
            bar_y = self.alto - 5
            bar_w = int(self.ancho * progress)
            draw.rectangle([0, bar_y, self.ancho, self.alto], fill="#1a1a2e")
            if bar_w > 0:
                draw.rectangle([0, bar_y, bar_w, self.alto],
                               fill=self.esquema["activo"])

        return frame


# ── Entry point ───────────────────────────────────────────────────────────────

def render_kinetic_pil(config, on_progress=None, on_log=None, is_cancelled=None):
    """Función principal para llamar desde video.py."""
    renderer = KineticPILRenderer(config, on_progress, on_log, is_cancelled)
    return renderer.render()
