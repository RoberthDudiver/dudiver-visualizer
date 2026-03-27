#!/usr/bin/env python3
"""
Kinetic Typography Lyric Video Generator
=========================================
Palabra por palabra sincronizada con el canto.
Cada palabra aparece con su efecto exactamente cuando se canta.
8 estilos: typewriter, wave, zoom, slide, fade, glitch, bounce, cinematic.
Beat-reactive: pulse sincronizado con la música.

Soporta:
  - Timestamps de palabras individuales: [{"palabra", "inicio", "fin"}]
  - Timestamps de líneas: [{"linea"/"texto", "inicio", "fin"}]

Uso:
  python lyric_video_manim.py audio.wav timestamps.json -o output.mp4 --estilo wave
"""

import argparse
import json
import math
import os
import random
import subprocess
import shutil
from pathlib import Path

import numpy as np

from manim import (
    Scene, Text, VGroup, config as manim_config,
    FadeIn, FadeOut,
    UP, DOWN, LEFT, RIGHT, ORIGIN,
    linear, smooth, there_and_back,
    RED, BLUE, GREEN, YELLOW, PURPLE,
)

# ── Esquemas de color ────────────────────────────────────────────────────────
ESQUEMAS_KINETIC = {
    "neon": {
        "activo": "#00f5ff", "glow": "#ff00ff",
        "pasado": "#7a7aaa", "futuro": "#4a4a6a", "flash": "#ffffff",
    },
    "fuego": {
        "activo": "#ff6b35", "glow": "#ffd460",
        "pasado": "#8b4513", "futuro": "#5a3a1a", "flash": "#ffff00",
    },
    "nocturno": {
        "activo": "#e94560", "glow": "#ff6b81",
        "pasado": "#7a7a9a", "futuro": "#4a4a6a", "flash": "#ffffff",
    },
    "elegante": {
        "activo": "#ffd700", "glow": "#ffed4a",
        "pasado": "#b8860b", "futuro": "#5a4a0a", "flash": "#ffffff",
    },
    "oceano": {
        "activo": "#00bcd4", "glow": "#4dd0e1",
        "pasado": "#006064", "futuro": "#003a3a", "flash": "#e0f7fa",
    },
}


# ── Beat detection ───────────────────────────────────────────────────────────

def detectar_beats(audio_path):
    """Detecta beats del audio."""
    import librosa
    y, sr = librosa.load(audio_path, sr=22050)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    return beat_times


def get_beat_intensity(t, beat_times, decay=0.15):
    """Intensidad del beat en tiempo t (0-1)."""
    for bt in beat_times:
        if bt > t + 0.01:
            break
        dt = t - bt
        if 0 <= dt < decay:
            return min(math.exp(-dt / (decay * 0.3)), 1.0)
    return 0.0


# ── Cargar timestamps ────────────────────────────────────────────────────────

def cargar_timestamps(path):
    """Carga timestamps. Soporta palabras individuales y líneas."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Formato Whisper: {"palabras": [...], "segmentos": [...]}
    if isinstance(data, dict) and "palabras" in data:
        palabras = []
        for w in data["palabras"]:
            texto = w.get("palabra", "").strip()
            if texto:
                palabras.append({
                    "palabra": texto,
                    "inicio": float(w["inicio"]),
                    "fin": float(w["fin"]),
                })
        segmentos = []
        for s in data.get("segmentos", []):
            texto = s.get("texto", "").strip()
            if texto:
                segmentos.append({
                    "linea": texto,
                    "inicio": float(s["inicio"]),
                    "fin": float(s["fin"]),
                })
        return palabras, segmentos

    # Formato directo: [{linea/texto, inicio, fin}]
    if isinstance(data, list):
        # Verificar si son palabras individuales (cortas) o líneas
        lineas = []
        for item in data:
            texto = item.get("linea") or item.get("texto") or item.get("palabra", "")
            if texto.strip():
                lineas.append({
                    "linea": texto.strip(),
                    "inicio": float(item.get("inicio", 0)),
                    "fin": float(item.get("fin", 0)),
                })
        # Si tienen key "palabra", son palabras individuales
        if data and "palabra" in data[0]:
            palabras = [{"palabra": l["linea"], "inicio": l["inicio"], "fin": l["fin"]}
                        for l in lineas]
            return palabras, []
        return [], lineas

    return [], []


# ── Agrupar palabras en frases para display ──────────────────────────────────

def agrupar_palabras_en_frases(palabras, max_palabras=5, max_gap=0.8):
    """Agrupa palabras cercanas en frases para mostrar juntas.
    Cada frase tiene sus palabras con timestamps individuales."""
    if not palabras:
        return []

    frases = []
    frase_actual = [palabras[0]]

    for i in range(1, len(palabras)):
        w = palabras[i]
        prev = frase_actual[-1]
        gap = w["inicio"] - prev["fin"]

        # Nueva frase si: mucho gap, o ya tiene suficientes palabras
        if gap > max_gap or len(frase_actual) >= max_palabras:
            frases.append(frase_actual)
            frase_actual = [w]
        else:
            frase_actual.append(w)

    if frase_actual:
        frases.append(frase_actual)

    return frases


# ── Utilidades de texto ──────────────────────────────────────────────────────

def crear_palabra(texto, fuente, color, font_size, ancho_px):
    """Crea objeto Text de Manim para una palabra."""
    t = Text(texto, font=fuente, font_size=font_size, color=color, weight="BOLD")
    max_w = ancho_px * 0.85 / 155
    if t.width > max_w:
        t.scale(max_w / t.width)
    return t


def bounce_ease(t):
    if t < 0.5:
        return smooth(t * 2) * 1.15
    elif t < 0.7:
        return 1.15 - (t - 0.5) * 0.75
    else:
        return 1.0


# ── Animaciones de ENTRADA por palabra ───────────────────────────────────────

def entrada_wave(scene, obj, dur, **kw):
    pos = obj.get_center().copy()
    obj.shift(DOWN * 1.0).set_opacity(0)
    scene.play(obj.animate.move_to(pos).set_opacity(1),
               run_time=max(0.05, min(0.25, dur * 0.5)), rate_func=smooth)

def entrada_zoom(scene, obj, dur, **kw):
    scene.play(FadeIn(obj, scale=0.1),
               run_time=max(0.05, min(0.3, dur * 0.5)), rate_func=bounce_ease)

def entrada_slide(scene, obj, dur, idx=0, **kw):
    pos = obj.get_center().copy()
    offset = LEFT * 12 if idx % 2 == 0 else RIGHT * 12
    obj.shift(offset).set_opacity(0)
    scene.play(obj.animate.move_to(pos).set_opacity(1),
               run_time=max(0.05, min(0.3, dur * 0.5)), rate_func=smooth)

def entrada_fade(scene, obj, dur, **kw):
    obj.set_opacity(0).shift(DOWN * 0.2)
    pos = obj.get_center() + UP * 0.2
    scene.play(obj.animate.move_to(pos).set_opacity(1),
               run_time=max(0.05, min(0.3, dur * 0.5)), rate_func=smooth)

def entrada_glitch(scene, obj, dur, **kw):
    pos = obj.get_center().copy()
    color_orig = obj.color
    scene.add(obj)
    for _ in range(min(4, int(dur * 8))):
        off = np.array([random.uniform(-0.3, 0.3), random.uniform(-0.15, 0.15), 0])
        obj.move_to(pos + off)
        obj.set_color(random.choice([RED, BLUE, GREEN, YELLOW]))
        obj.set_opacity(random.uniform(0.4, 1.0))
        scene.wait(0.03)
    obj.move_to(pos).set_color(color_orig).set_opacity(1)

def entrada_bounce(scene, obj, dur, **kw):
    pos = obj.get_center().copy()
    obj.shift(UP * 4)
    scene.add(obj)
    for target, rt in [(pos, 0.15), (pos + UP * 0.3, 0.07), (pos, 0.05)]:
        scene.play(obj.animate.move_to(target), run_time=rt, rate_func=linear)

def entrada_typewriter(scene, obj, dur, **kw):
    chars = VGroup(*[c for c in obj])
    for c in chars:
        c.set_opacity(0)
    scene.add(obj)
    delay = min(dur * 0.6 / max(len(chars), 1), 0.06)
    for c in chars:
        c.set_opacity(1)
        scene.wait(delay)

def entrada_cinematic(scene, obj, dur, **kw):
    obj.scale(1.3).set_opacity(0)
    scene.play(obj.animate.scale(1 / 1.3).set_opacity(1),
               run_time=max(0.05, min(0.25, dur * 0.5)), rate_func=smooth)


def entrada_oneword(scene, obj, dur, **kw):
    """One Word: aparece con scale-in rápido."""
    obj.scale(0.5).set_opacity(0)
    scene.play(obj.animate.scale(2.0).set_opacity(1),
               run_time=max(0.05, min(0.15, dur * 0.4)), rate_func=smooth)


ESTILOS = {
    "wave": entrada_wave,
    "zoom": entrada_zoom,
    "slide": entrada_slide,
    "fade": entrada_fade,
    "glitch": entrada_glitch,
    "bounce": entrada_bounce,
    "typewriter": entrada_typewriter,
    "cinematic": entrada_cinematic,
    "oneword": entrada_oneword,
}


# ── Escena principal ─────────────────────────────────────────────────────────

class KineticLyricScene(Scene):
    """Palabra por palabra sincronizada con el audio."""

    palabras = []
    segmentos = []
    beat_times = []
    estilo = "wave"
    esquema_nombre = "neon"
    fuente = "Arial"
    font_size = 72
    ancho_px = 1920
    alto_px = 1080
    color_override = None
    fondo_path = None

    def construct(self):
        esquema = ESQUEMAS_KINETIC.get(self.esquema_nombre, ESQUEMAS_KINETIC["neon"])
        color = self.color_override or esquema["activo"]
        color_dim = esquema["pasado"]
        animar_fn = ESTILOS.get(self.estilo, entrada_wave)

        # Imagen de fondo si existe
        if self.fondo_path and os.path.isfile(self.fondo_path):
            try:
                from manim import ImageMobject
                bg = ImageMobject(self.fondo_path)
                # Escalar para cubrir el frame completo
                bg.height = self.alto_px / 155 * 2
                bg.width = self.ancho_px / 155 * 2
                bg.set_opacity(0.3)
                bg.move_to(ORIGIN)
                self.add(bg)
            except Exception as e:
                print(f"[DVS] No se pudo cargar fondo: {e}")

        if self.estilo == "oneword" and self.palabras:
            self._render_oneword(color, esquema)
        elif self.palabras:
            self._render_palabras(animar_fn, color, color_dim, esquema)
        elif self.segmentos:
            self._render_lineas(animar_fn, color, color_dim, esquema)

        self.wait(0.5)

    def _render_palabras(self, animar_fn, color, color_dim, esquema):
        """Render palabra por palabra — el modo principal."""
        frases = agrupar_palabras_en_frases(self.palabras)
        current_time = 0.0
        word_idx = 0

        for frase in frases:
            t_inicio_frase = frase[0]["inicio"]
            t_fin_frase = frase[-1]["fin"]

            # Esperar hasta el inicio de la frase
            wait = t_inicio_frase - current_time
            if wait > 0.01:
                self.wait(wait)
                current_time = t_inicio_frase

            # Crear todos los objetos de la frase (dimmed)
            word_objs = []
            for w in frase:
                obj = crear_palabra(w["palabra"], self.fuente, color_dim,
                                    self.font_size, self.ancho_px)
                word_objs.append(obj)

            # Arreglar en fila
            grupo = VGroup(*word_objs).arrange(RIGHT, buff=0.3)

            # Escalar si se sale del ancho
            max_w = self.ancho_px * 0.85 / 155
            if grupo.width > max_w:
                grupo.scale(max_w / grupo.width)

            grupo.move_to(ORIGIN)

            # Animar cada palabra cuando llega su tiempo
            for i, w in enumerate(frase):
                obj = word_objs[i]
                t_word = w["inicio"]
                dur_word = max(w["fin"] - w["inicio"], 0.05)

                # Esperar hasta esta palabra
                wait = t_word - current_time
                if wait > 0.01:
                    self.wait(wait)
                    current_time = t_word

                # Animación de entrada — la palabra se ilumina
                # Calcular run_time de la animación para trackear
                anim_rt = max(0.05, min(0.25, dur_word * 0.5))
                animar_fn(self, obj, dur_word, idx=word_idx)
                obj.set_color(color)
                current_time += anim_rt

                # Beat pulse durante la palabra
                intensity = get_beat_intensity(t_word, self.beat_times)
                if intensity > 0.4:
                    sf = 1.0 + intensity * 0.1
                    pulse_t = 0.08
                    self.play(obj.animate.scale(sf), run_time=pulse_t,
                              rate_func=there_and_back)
                    current_time += pulse_t

                # Esperar resto de la palabra
                remaining = w["fin"] - current_time
                if remaining > 0.01:
                    self.wait(remaining)
                current_time = w["fin"]
                word_idx += 1

            # Mantener frase visible un momento después de la última palabra
            hold = 0.3
            self.wait(hold)
            current_time += hold

            # Fade out de toda la frase
            self.play(FadeOut(grupo), run_time=0.2)
            current_time += 0.2

    def _render_oneword(self, color, esquema):
        """One Word: una sola palabra gigante centrada, cambia con cada palabra."""
        current_time = 0.0
        prev_obj = None

        for w in self.palabras:
            texto = w["palabra"].strip(" ,.:;!?")
            if not texto:
                continue

            t_inicio = w["inicio"]
            t_fin = w["fin"]
            dur = max(t_fin - t_inicio, 0.05)

            # Esperar hasta esta palabra
            if prev_obj:
                # Calcular cuánto tiempo tenemos para fade + espera
                available = t_inicio - current_time
                if available > 0.15:
                    fade_t = min(0.15, available * 0.4)
                    self.play(FadeOut(prev_obj), run_time=fade_t)
                    current_time += fade_t
                    remaining = t_inicio - current_time
                    if remaining > 0.01:
                        self.wait(remaining)
                        current_time = t_inicio
                elif available > 0.01:
                    self.play(FadeOut(prev_obj), run_time=available)
                    current_time = t_inicio
                else:
                    self.remove(prev_obj)
                prev_obj = None
            else:
                wait = t_inicio - current_time
                if wait > 0.01:
                    self.wait(wait)
                    current_time = t_inicio

            # Crear palabra grande (crear_palabra ya ajusta al ancho)
            obj = crear_palabra(texto, self.fuente, color,
                                self.font_size * 2, self.ancho_px)
            obj.move_to(ORIGIN)

            # Entrada rápida con scale (0.5 → 2.0 = tamaño original)
            entry_time = max(0.05, min(0.12, dur * 0.3))
            obj.scale(0.5).set_opacity(0)
            self.play(obj.animate.scale(2.0).set_opacity(1),
                      run_time=entry_time, rate_func=smooth)
            current_time += entry_time

            # Beat pulse
            intensity = get_beat_intensity(t_inicio, self.beat_times)
            if intensity > 0.4:
                sf = 1.0 + intensity * 0.15
                pulse_t = 0.08
                self.play(obj.animate.scale(sf), run_time=pulse_t,
                          rate_func=there_and_back)
                current_time += pulse_t

            # Esperar el resto de la duración de la palabra
            remaining = t_fin - current_time
            if remaining > 0.01:
                self.wait(remaining)
            current_time = t_fin
            prev_obj = obj

        # Fade out última palabra
        if prev_obj:
            self.play(FadeOut(prev_obj), run_time=0.3)

    def _render_lineas(self, animar_fn, color, color_dim, esquema):
        """Fallback: render por líneas si no hay palabras individuales."""
        current_time = 0.0

        for idx, linea_data in enumerate(self.segmentos):
            texto = linea_data["linea"]
            t_inicio = linea_data["inicio"]
            t_fin = linea_data["fin"]
            dur = t_fin - t_inicio

            if dur <= 0.1:
                continue

            wait = t_inicio - current_time
            if wait > 0.01:
                self.wait(wait)
                current_time = t_inicio

            # Crear palabras de la línea
            words = texto.split()
            word_objs = []
            for w in words:
                obj = crear_palabra(w, self.fuente, color_dim,
                                    self.font_size, self.ancho_px)
                word_objs.append(obj)

            grupo = VGroup(*word_objs).arrange(RIGHT, buff=0.25)
            max_w = self.ancho_px * 0.85 / 155
            if grupo.width > max_w:
                grupo.scale(max_w / grupo.width)
            grupo.move_to(ORIGIN)

            # Animar palabra por palabra distribuidas en la duración
            delay_per = dur * 0.7 / max(len(words), 1)
            for i, obj in enumerate(word_objs):
                animar_fn(self, obj, delay_per, idx=idx * 100 + i)
                obj.set_color(color)

                intensity = get_beat_intensity(current_time, self.beat_times)
                if intensity > 0.4:
                    sf = 1.0 + intensity * 0.1
                    self.play(obj.animate.scale(sf), run_time=0.06, rate_func=there_and_back)

                current_time += delay_per

            # Hold
            remaining = t_fin - current_time
            if remaining > 0.1:
                self.wait(remaining)
                current_time = t_fin

            self.play(FadeOut(grupo), run_time=0.2)
            current_time += 0.2


# ── Render pipeline ──────────────────────────────────────────────────────────

def render_kinetic(args):
    """Configura Manim y renderiza."""
    palabras, segmentos = cargar_timestamps(args.timestamps)
    total = len(palabras) + len(segmentos)
    if total == 0:
        print("ERROR: No hay timestamps válidos.")
        return None

    if palabras:
        print(f"  {len(palabras)} palabras individuales cargadas")
    if segmentos:
        print(f"  {len(segmentos)} segmentos/líneas cargados")
    print(f"  Estilo: {args.estilo}")

    print("  Analizando beats...")
    beat_times = detectar_beats(args.audio)
    print(f"  {len(beat_times)} beats detectados")

    if "x" in args.resolucion:
        ancho, alto = map(int, args.resolucion.split("x"))
    else:
        ancho, alto = 1920, 1080

    manim_config.pixel_width = ancho
    manim_config.pixel_height = alto
    manim_config.frame_rate = args.fps
    manim_config.background_color = "#000000"
    if args.alpha:
        manim_config.background_opacity = 0.0

    output = args.output or "kinetic_output.mp4"
    output_dir = os.path.dirname(os.path.abspath(output)) or "."
    output_name = Path(output).stem

    manim_config.output_file = output_name
    manim_config.media_dir = os.path.join(output_dir, "manim_media")
    # No usar quality preset — sobreescribe pixel_width/height
    # En su lugar, configurar manualmente para respetar la resolución elegida
    manim_config.pixel_width = ancho
    manim_config.pixel_height = alto
    manim_config.frame_rate = args.fps

    KineticLyricScene.palabras = palabras
    KineticLyricScene.segmentos = segmentos
    KineticLyricScene.beat_times = beat_times
    KineticLyricScene.estilo = args.estilo
    KineticLyricScene.esquema_nombre = args.color
    KineticLyricScene.fuente = args.fuente
    KineticLyricScene.font_size = args.font_size
    KineticLyricScene.ancho_px = ancho
    KineticLyricScene.alto_px = alto
    KineticLyricScene.color_override = args.color_texto
    KineticLyricScene.fondo_path = getattr(args, "fondo", None)

    print("  Renderizando kinetic typography...")
    scene = KineticLyricScene()
    scene.render()

    video_manim = str(scene.renderer.file_writer.movie_file_path)
    print(f"  Video Manim: {video_manim}")

    final_output = os.path.abspath(output)
    all_ts = palabras or segmentos
    dur_max = max(t.get("fin", t.get("fin", 0)) for t in all_ts) + 2.0

    print(f"  Combinando con audio...")
    ext = Path(final_output).suffix.lower()

    if args.alpha:
        if ext != ".mov":
            final_output = str(Path(final_output).with_suffix(".mov"))
        cmd = [
            "ffmpeg", "-y", "-i", video_manim, "-i", args.audio,
            "-c:v", "prores_ks", "-profile:v", "4444",
            "-pix_fmt", "yuva444p10le",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(dur_max), "-shortest", final_output,
        ]
    elif ext == ".webm":
        cmd = [
            "ffmpeg", "-y", "-i", video_manim, "-i", args.audio,
            "-c:v", "libvpx-vp9", "-crf", "20", "-b:v", "0",
            "-c:a", "libvorbis", "-b:a", "192k",
            "-t", str(dur_max), "-shortest", final_output,
        ]
    elif ext == ".avi":
        cmd = [
            "ffmpeg", "-y", "-i", video_manim, "-i", args.audio,
            "-c:v", "mpeg4", "-q:v", "3",
            "-c:a", "mp3", "-b:a", "192k",
            "-t", str(dur_max), "-shortest", final_output,
        ]
    elif ext == ".mov":
        cmd = [
            "ffmpeg", "-y", "-i", video_manim, "-i", args.audio,
            "-c:v", "prores_ks", "-profile:v", "3",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(dur_max), "-shortest", final_output,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", video_manim, "-i", args.audio,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(dur_max), "-shortest",
            "-pix_fmt", "yuv420p", final_output,
        ]

    subprocess.run(cmd, check=True, capture_output=True)

    media_dir = os.path.join(output_dir, "manim_media")
    if os.path.exists(media_dir):
        shutil.rmtree(media_dir, ignore_errors=True)

    print(f"\n  Video final: {final_output}")
    return final_output


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Kinetic Typography — palabra por palabra sincronizada"
    )
    parser.add_argument("audio", help="Archivo de audio (WAV/MP3)")
    parser.add_argument("timestamps", help="JSON de timestamps (palabras o líneas)")
    parser.add_argument("-o", "--output", default="kinetic_output.mp4")
    parser.add_argument("--estilo", default="wave", choices=list(ESTILOS.keys()))
    parser.add_argument("--resolucion", default="1920x1080")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--color", default="neon", choices=list(ESQUEMAS_KINETIC.keys()))
    parser.add_argument("--color-texto", default=None)
    parser.add_argument("--fuente", default="Arial")
    parser.add_argument("--font-size", type=int, default=72)
    parser.add_argument("--alpha", action="store_true")

    args = parser.parse_args()
    render_kinetic(args)


if __name__ == "__main__":
    main()
