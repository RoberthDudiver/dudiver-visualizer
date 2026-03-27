#!/usr/bin/env python3
"""
Generador de Lyric Video v3 — Suite de Composición Musical
- Sincronización: timestamps directos (JSON) o matching fuzzy con Whisper
- Modo Alpha: fondo 100% transparente (WebM VP9 con canal alpha)
- Modo Normal: gradientes animados, partículas, ondas, viñeta
- Fondo personalizado: imagen o video
- Efecto karaoke: iluminación progresiva palabra por palabra
"""
import argparse
import json
import sys
import os
import math
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from app.utils.fonts import load_pil_font


# ============ SINCRONIZACIÓN ============

def normalizar(texto):
    """Normaliza texto para comparación"""
    import unicodedata
    t = unicodedata.normalize('NFD', texto.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = ''.join(c for c in t if c.isalnum() or c == ' ')
    return t.strip()


def similitud(a, b):
    """Similitud simple entre dos palabras"""
    a, b = normalizar(a), normalizar(b)
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.8
    comunes = sum(1 for c in a if c in b)
    return comunes / max(len(a), len(b), 1)


def alinear_letra_con_whisper(lineas_reales, palabras_whisper):
    """
    Alinea cada línea de la letra real con timestamps de Whisper
    usando matching fuzzy palabra por palabra.
    """
    lineas_con_tiempo = []
    w_idx = 0

    for linea in lineas_reales:
        palabras_linea = linea.split()
        if not palabras_linea:
            continue

        mejor_inicio_idx = w_idx
        mejor_score = -1

        rango_busqueda = min(len(palabras_whisper) - w_idx, len(palabras_linea) * 3 + 10)
        for start in range(w_idx, min(w_idx + rango_busqueda, len(palabras_whisper))):
            score = 0
            for j, pw in enumerate(palabras_linea):
                wi = start + j
                if wi < len(palabras_whisper):
                    score += similitud(pw, palabras_whisper[wi]["palabra"])
            score /= len(palabras_linea)
            if score > mejor_score:
                mejor_score = score
                mejor_inicio_idx = start

        fin_idx = min(mejor_inicio_idx + len(palabras_linea) - 1, len(palabras_whisper) - 1)

        if mejor_inicio_idx < len(palabras_whisper) and fin_idx < len(palabras_whisper):
            inicio_t = palabras_whisper[mejor_inicio_idx]["inicio"]
            fin_t = palabras_whisper[fin_idx]["fin"]

            lineas_con_tiempo.append({
                "texto": linea,
                "inicio": inicio_t,
                "fin": fin_t,
                "score": mejor_score
            })

            w_idx = fin_idx + 1
        else:
            if lineas_con_tiempo:
                ultimo = lineas_con_tiempo[-1]["fin"]
                lineas_con_tiempo.append({
                    "texto": linea,
                    "inicio": ultimo + 0.3,
                    "fin": ultimo + 2.5,
                    "score": 0
                })

    return lineas_con_tiempo


def cargar_timestamps_directos(ruta_timestamps):
    """
    Carga timestamps directos (formato tiempos-v3.json):
    [{"linea": "texto", "inicio": 12.6, "fin": 16.96}, ...]
    """
    with open(ruta_timestamps, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lineas_con_tiempo = []
    for item in data:
        lineas_con_tiempo.append({
            "texto": item.get("linea", item.get("texto", "")),
            "inicio": item["inicio"],
            "fin": item["fin"],
            "score": 1.0
        })

    return lineas_con_tiempo


# ============ EFECTOS VISUALES (modo normal) ============

class Particula:
    def __init__(self, ancho, alto):
        self.x = random.randint(0, ancho)
        self.y = random.randint(0, alto)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.8, -0.2)
        self.size = random.uniform(1.5, 4)
        self.alpha = random.randint(40, 120)
        self.vida = random.uniform(0.5, 1.0)
        self.ancho = ancho
        self.alto = alto

    def actualizar(self, dt, beat_intensity=0):
        self.x += self.vx + beat_intensity * random.uniform(-1, 1)
        self.y += self.vy
        self.vida -= dt * 0.1

        if self.y < -10 or self.vida <= 0:
            self.y = self.alto + 10
            self.x = random.randint(0, self.ancho)
            self.vida = random.uniform(0.5, 1.0)


def crear_gradiente(ancho, alto, tiempo, esquema):
    """Crea un fondo con gradiente animado"""
    img = Image.new('RGB', (ancho, alto))
    draw = ImageDraw.Draw(img)

    r1, g1, b1 = esquema["grad_top"]
    r2, g2, b2 = esquema["grad_bottom"]

    shift = math.sin(tiempo * 0.3) * 15
    shift2 = math.cos(tiempo * 0.2) * 10

    for y in range(alto):
        ratio = y / alto
        ratio = ratio ** 1.3
        r = int(r1 + (r2 - r1) * ratio + shift * (1 - ratio))
        g = int(g1 + (g2 - g1) * ratio + shift2 * ratio)
        b = int(b1 + (b2 - b1) * ratio - shift * ratio)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        draw.line([(0, y), (ancho, y)], fill=(r, g, b))

    return img


def dibujar_particulas(draw, particulas, color_base, beat_intensity=0):
    """Dibuja las partículas con brillo variable"""
    for p in particulas:
        alpha = int(p.alpha * p.vida * (1 + beat_intensity * 2))
        alpha = max(0, min(255, alpha))
        size = p.size * (1 + beat_intensity * 1.5)
        color = (
            min(255, color_base[0] + int(beat_intensity * 80)),
            min(255, color_base[1] + int(beat_intensity * 40)),
            min(255, color_base[2])
        )
        x, y = int(p.x), int(p.y)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=color)


def dibujar_onda(draw, ancho, alto, tiempo, color, beat_intensity=0):
    """Dibuja una onda decorativa en la parte inferior"""
    amplitude = 8 + beat_intensity * 15
    y_base = alto - 40
    points = []
    for x in range(0, ancho, 3):
        y = y_base + math.sin(x * 0.02 + tiempo * 2) * amplitude
        y += math.sin(x * 0.01 + tiempo * 1.3) * amplitude * 0.5
        points.append((x, int(y)))

    points.append((ancho, alto))
    points.append((0, alto))

    if len(points) > 2:
        draw.polygon(points, fill=color)


# ============ RENDERIZADO ============

def cargar_fuente(size, bold=True):
    """Carga la mejor fuente disponible usando load_pil_font portable."""
    font, _ = load_pil_font("Segoe UI", size, bold=bold)
    return font


def crear_frame_alpha(ancho, alto, lineas_con_tiempo, tiempo_actual, duracion_total,
                      beat_times, fuente, fuente_titulo, titulo=""):
    """
    Crea un frame con fondo 100% TRANSPARENTE (RGBA).
    Solo renderiza texto con efectos de glow y karaoke.
    Sin gradiente, sin partículas, sin onda, sin viñeta.
    """
    img = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Beat intensity para efectos en texto
    beat_intensity = 0
    for bt in beat_times:
        diff = abs(tiempo_actual - bt)
        if diff < 0.12:
            beat_intensity = max(beat_intensity, 1.0 - diff / 0.12)

    # Encontrar línea activa
    linea_activa_idx = -1
    for i, lt in enumerate(lineas_con_tiempo):
        if lt["inicio"] - 0.5 <= tiempo_actual <= lt["fin"] + 1.0:
            linea_activa_idx = i
            break

    if linea_activa_idx == -1:
        for i, lt in enumerate(lineas_con_tiempo):
            if tiempo_actual > lt["fin"]:
                linea_activa_idx = i
            elif tiempo_actual < lt["inicio"]:
                break

    # Ventana de líneas visibles
    max_visible = 7
    mitad = max_visible // 2
    inicio_v = max(0, linea_activa_idx - mitad)
    fin_v = min(len(lineas_con_tiempo), inicio_v + max_visible)
    inicio_v = max(0, fin_v - max_visible)

    # Adaptar altura de linea al tamaño real de la fuente
    _bbox = draw.textbbox((0, 0), "Ay", font=fuente)
    linea_alto = int((_bbox[3] - _bbox[1]) * 1.5)
    total_h = (fin_v - inicio_v) * linea_alto
    base_y = (alto - total_h) // 2

    # Colores para alpha mode (blancos/dorados brillantes sobre transparente)
    color_activo = (255, 220, 60, 255)
    color_activo_dim = (255, 200, 50, 180)
    color_pasado = (200, 200, 210, 130)
    color_siguiente = (220, 220, 230, 160)
    color_futuro = (180, 180, 190, 100)
    color_sombra = (0, 0, 0, 180)
    color_glow = (255, 180, 0, 80)

    for idx in range(inicio_v, fin_v):
        lt = lineas_con_tiempo[idx]
        texto = lt["texto"]
        y = base_y + (idx - inicio_v) * linea_alto

        es_activa = (idx == linea_activa_idx) and (tiempo_actual >= lt["inicio"] - 0.3)
        es_pasada = idx < linea_activa_idx
        es_siguiente = idx == linea_activa_idx + 1

        bbox = draw.textbbox((0, 0), texto, font=fuente)
        tw = bbox[2] - bbox[0]
        x = (ancho - tw) // 2

        if es_activa:
            line_progress = 0
            if lt["fin"] > lt["inicio"]:
                line_progress = (tiempo_actual - lt["inicio"]) / (lt["fin"] - lt["inicio"])
                line_progress = max(0, min(1, line_progress))

            # Sombra
            draw.text((x + 3, y + 3), texto, fill=color_sombra, font=fuente)

            # Glow detrás del texto
            glow_size = 2 + int(beat_intensity * 2)
            for offset in range(glow_size, 0, -1):
                draw.text((x - offset, y), texto, fill=color_glow, font=fuente)
                draw.text((x + offset, y), texto, fill=color_glow, font=fuente)
                draw.text((x, y - offset), texto, fill=color_glow, font=fuente)
                draw.text((x, y + offset), texto, fill=color_glow, font=fuente)

            # Texto dim (lo que falta por cantar)
            draw.text((x, y), texto, fill=color_activo_dim, font=fuente)

            # Efecto karaoke: parte ya cantada en color brillante
            if line_progress > 0:
                mask = Image.new('L', (ancho, alto), 0)
                mask_draw = ImageDraw.Draw(mask)
                clip_x = x + int(tw * line_progress)
                mask_draw.rectangle([x - 5, y - 5, clip_x, y + linea_alto], fill=255)

                texto_img = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
                texto_draw = ImageDraw.Draw(texto_img)
                texto_draw.text((x, y), texto, fill=color_activo, font=fuente)

                # Componer solo la parte cantada sobre el frame
                img = Image.composite(texto_img, img, mask)
                draw = ImageDraw.Draw(img)

        elif es_pasada:
            draw.text((x + 2, y + 2), texto, fill=(0, 0, 0, 100), font=fuente)
            draw.text((x, y), texto, fill=color_pasado, font=fuente)

        elif es_siguiente:
            draw.text((x, y), texto, fill=color_siguiente, font=fuente)

        else:
            draw.text((x, y), texto, fill=color_futuro, font=fuente)

    # Barra de progreso sutil
    progreso = tiempo_actual / duracion_total if duracion_total > 0 else 0
    barra_h = 3
    barra_y = alto - barra_h - 10
    barra_ancho = int(ancho * 0.6)
    barra_x = (ancho - barra_ancho) // 2

    # Fondo de barra
    draw.rectangle([barra_x, barra_y, barra_x + barra_ancho, barra_y + barra_h],
                    fill=(255, 255, 255, 40))
    # Progreso
    if progreso > 0:
        draw.rectangle([barra_x, barra_y, barra_x + int(barra_ancho * progreso), barra_y + barra_h],
                        fill=(255, 220, 60, 180))

    return img


def crear_frame_normal(ancho, alto, lineas_con_tiempo, tiempo_actual, duracion_total,
                       beat_times, rms_data, esquema, fuente, fuente_titulo, fuente_peq,
                       particulas, titulo="", bg_image=None, solo_fondo=False, effects=None):
    """Crea un frame con efectos visuales completos (modo normal con fondo)"""

    # Calcular beat intensity
    beat_intensity = 0
    for bt in beat_times:
        diff = abs(tiempo_actual - bt)
        if diff < 0.12:
            beat_intensity = max(beat_intensity, 1.0 - diff / 0.12)

    # Fondo
    if bg_image is not None:
        img = bg_image.copy()
        darkness = max(140, 180 - int(beat_intensity * 40))
        overlay = Image.new('RGBA', img.size, (0, 0, 0, darkness))
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay).convert('RGB')
    else:
        img = crear_gradiente(ancho, alto, tiempo_actual, esquema)

    draw = ImageDraw.Draw(img)

    # Partículas
    if effects is None or effects.get("particulas", True):
        dt = 1.0 / 24
        for p in particulas:
            p.actualizar(dt, beat_intensity)
        dibujar_particulas(draw, particulas, esquema["particula"], beat_intensity)

    # Onda inferior
    if effects is None or effects.get("onda", True):
        onda_color = tuple(max(0, min(255, c + int(beat_intensity * 30))) for c in esquema["onda"])
        dibujar_onda(draw, ancho, alto, tiempo_actual, onda_color, beat_intensity)

    # Barra de progreso
    if effects is None or effects.get("barra", True):
        progreso = tiempo_actual / duracion_total if duracion_total > 0 else 0
        barra_h = 4
        barra_y = alto - barra_h
        for x in range(int(ancho * progreso)):
            ratio = x / max(1, ancho)
            r = int(esquema["activo"][0] * (1 - ratio * 0.3))
            g = int(esquema["activo"][1] * (1 - ratio * 0.5))
            b = int(esquema["activo"][2] + ratio * 50)
            draw.line([(x, barra_y), (x, alto)], fill=(min(255, r), min(255, g), min(255, b)))

    # Título
    if titulo:
        bbox = draw.textbbox((0, 0), titulo, font=fuente_titulo)
        tw = bbox[2] - bbox[0]
        tx = (ancho - tw) // 2
        ty = 25
        titulo_alpha = int(70 + beat_intensity * 30)
        draw.text((tx, ty), titulo, fill=(titulo_alpha, titulo_alpha, titulo_alpha + 20), font=fuente_titulo)

    # === LETRA === (omitir si solo_fondo=True, para modo combinado con Manim)
    if solo_fondo:
        # Viñeta
        vignette = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
        vdraw = ImageDraw.Draw(vignette)
        for i in range(80):
            alpha = int(60 * (1 - i / 80))
            vdraw.rectangle([i, i, ancho - i, alto - i], outline=(0, 0, 0, alpha))
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, vignette).convert('RGB')
        return img

    linea_activa_idx = -1
    for i, lt in enumerate(lineas_con_tiempo):
        if lt["inicio"] - 0.5 <= tiempo_actual <= lt["fin"] + 1.0:
            linea_activa_idx = i
            break

    if linea_activa_idx == -1:
        for i, lt in enumerate(lineas_con_tiempo):
            if tiempo_actual > lt["fin"]:
                linea_activa_idx = i
            elif tiempo_actual < lt["inicio"]:
                break

    max_visible = 7
    mitad = max_visible // 2
    inicio_v = max(0, linea_activa_idx - mitad)
    fin_v = min(len(lineas_con_tiempo), inicio_v + max_visible)
    inicio_v = max(0, fin_v - max_visible)

    # Adaptar altura de linea al tamaño real de la fuente
    _bbox2 = draw.textbbox((0, 0), "Ay", font=fuente)
    linea_alto = int((_bbox2[3] - _bbox2[1]) * 1.5)
    total_h = (fin_v - inicio_v) * linea_alto
    base_y = (alto - total_h) // 2

    for idx in range(inicio_v, fin_v):
        lt = lineas_con_tiempo[idx]
        texto = lt["texto"]
        y = base_y + (idx - inicio_v) * linea_alto

        es_activa = (idx == linea_activa_idx) and (tiempo_actual >= lt["inicio"] - 0.3)
        es_pasada = idx < linea_activa_idx
        es_siguiente = idx == linea_activa_idx + 1

        bbox = draw.textbbox((0, 0), texto, font=fuente)
        tw = bbox[2] - bbox[0]
        x = (ancho - tw) // 2

        if es_activa:
            line_progress = 0
            if lt["fin"] > lt["inicio"]:
                line_progress = (tiempo_actual - lt["inicio"]) / (lt["fin"] - lt["inicio"])
                line_progress = max(0, min(1, line_progress))

            draw.text((x + 3, y + 3), texto, fill=(0, 0, 0), font=fuente)

            if effects is None or effects.get("glow", True):
                glow_size = 2 + int(beat_intensity * 2)
                glow_color = (
                    max(0, esquema["activo"][0] - 80),
                    max(0, esquema["activo"][1] - 60),
                    max(0, esquema["activo"][2] - 40)
                )
                for offset in range(glow_size, 0, -1):
                    draw.text((x - offset, y), texto, fill=glow_color, font=fuente)
                    draw.text((x + offset, y), texto, fill=glow_color, font=fuente)

            color_cantado = esquema["activo"]
            color_por_cantar = esquema["activo_dim"]

            draw.text((x, y), texto, fill=color_por_cantar, font=fuente)

            if line_progress > 0:
                mask = Image.new('L', (ancho, alto), 0)
                mask_draw = ImageDraw.Draw(mask)
                clip_x = x + int(tw * line_progress)
                mask_draw.rectangle([x - 5, y - 5, clip_x, y + linea_alto], fill=255)

                texto_img = Image.new('RGB', (ancho, alto), (0, 0, 0))
                texto_draw = ImageDraw.Draw(texto_img)
                texto_draw.text((x, y), texto, fill=color_cantado, font=fuente)

                img.paste(texto_img, mask=mask)
                draw = ImageDraw.Draw(img)

        elif es_pasada:
            draw.text((x + 2, y + 2), texto, fill=(0, 0, 0), font=fuente)
            draw.text((x, y), texto, fill=esquema["pasado"], font=fuente)

        elif es_siguiente:
            draw.text((x, y), texto, fill=esquema["siguiente"], font=fuente)

        else:
            draw.text((x, y), texto, fill=esquema["futuro"], font=fuente)

    # Viñeta
    if effects is None or effects.get("vineta", True):
        vignette = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
        vdraw = ImageDraw.Draw(vignette)
        for i in range(80):
            alpha = int(60 * (1 - i / 80))
            vdraw.rectangle([i, i, ancho - i, alto - i], outline=(0, 0, 0, alpha))
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, vignette).convert('RGB')

    return img


# ============ ESQUEMAS DE COLOR ============

ESQUEMAS = {
    "nocturno": {
        "grad_top": (8, 4, 25),
        "grad_bottom": (20, 8, 45),
        "pasado": (90, 75, 110),
        "activo": (255, 200, 50),
        "activo_dim": (180, 140, 40),
        "siguiente": (120, 100, 150),
        "futuro": (50, 40, 70),
        "particula": (180, 140, 220),
        "onda": (25, 15, 50),
    },
    "oscuro": {
        "grad_top": (8, 10, 20),
        "grad_bottom": (15, 20, 40),
        "pasado": (90, 100, 120),
        "activo": (0, 200, 255),
        "activo_dim": (0, 130, 180),
        "siguiente": (80, 110, 150),
        "futuro": (35, 40, 55),
        "particula": (100, 160, 220),
        "onda": (10, 20, 45),
    },
    "elegante": {
        "grad_top": (20, 12, 5),
        "grad_bottom": (35, 20, 10),
        "pasado": (140, 115, 80),
        "activo": (255, 215, 0),
        "activo_dim": (200, 170, 0),
        "siguiente": (160, 130, 70),
        "futuro": (60, 48, 30),
        "particula": (200, 170, 100),
        "onda": (40, 25, 10),
    },
    "neon": {
        "grad_top": (5, 2, 18),
        "grad_bottom": (15, 5, 35),
        "pasado": (80, 60, 120),
        "activo": (255, 0, 140),
        "activo_dim": (180, 0, 100),
        "siguiente": (120, 60, 160),
        "futuro": (35, 25, 55),
        "particula": (200, 50, 180),
        "onda": (30, 10, 50),
    },
    "fuego": {
        "grad_top": (18, 5, 2),
        "grad_bottom": (40, 12, 5),
        "pasado": (130, 80, 50),
        "activo": (255, 100, 0),
        "activo_dim": (200, 70, 0),
        "siguiente": (160, 90, 40),
        "futuro": (55, 30, 15),
        "particula": (220, 120, 50),
        "onda": (45, 15, 5),
    }
}


# ============ GENERACIÓN DE VIDEO ============

def generar_video(ruta_audio, ruta_timestamps, ruta_salida,
                  ancho=1920, alto=1080, fps=24, titulo="",
                  esquema_nombre="nocturno", bg_path=None,
                  alpha_mode=False, ruta_letra=None, bg_start=0.0,
                  solo_fondo=False):
    """Genera el video lírico completo"""
    from moviepy import AudioFileClip, VideoClip, VideoFileClip
    import librosa

    esquema = ESQUEMAS.get(esquema_nombre, ESQUEMAS["nocturno"])

    print("Cargando audio...")
    audio = AudioFileClip(ruta_audio)
    duracion = audio.duration

    # Cargar timestamps
    print("Cargando timestamps...")
    with open(ruta_timestamps, 'r', encoding='utf-8') as f:
        ts_data = json.load(f)

    # Detectar formato de timestamps
    if isinstance(ts_data, list):
        # Formato directo: [{"linea": "...", "inicio": ..., "fin": ...}, ...]
        print("Formato: timestamps directos (línea por línea)")
        lineas_con_tiempo = cargar_timestamps_directos(ruta_timestamps)
    elif isinstance(ts_data, dict) and "palabras" in ts_data:
        # Formato Whisper: {"palabras": [...]}
        print("Formato: Whisper word-level — alineando con fuzzy matching...")
        if not ruta_letra:
            print("ERROR: Se necesita --letra para alinear con timestamps de Whisper")
            sys.exit(1)
        lineas = []
        with open(ruta_letra, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith('#'):
                    lineas.append(linea)
        lineas_con_tiempo = alinear_letra_con_whisper(lineas, ts_data["palabras"])
    else:
        print("ERROR: Formato de timestamps no reconocido")
        sys.exit(1)

    print(f"  Líneas sincronizadas: {len(lineas_con_tiempo)}")
    for i, lt in enumerate(lineas_con_tiempo[:5]):
        print(f"  [{lt['inicio']:.1f}s - {lt['fin']:.1f}s] {lt['texto'][:60]}")
    if len(lineas_con_tiempo) > 5:
        print(f"  ... y {len(lineas_con_tiempo) - 5} más")

    # Beats para efectos
    print("Analizando beats...")
    y_audio, sr = librosa.load(ruta_audio, sr=22050)
    tempo, beat_frames = librosa.beat.beat_track(y=y_audio, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    # Fuentes
    fuente = cargar_fuente(50, bold=True)
    fuente_titulo = cargar_fuente(26, bold=False)
    fuente_peq = cargar_fuente(20, bold=False)

    if alpha_mode:
        # ========== MODO ALPHA: Fondo transparente ==========
        print(f"\n*** MODO ALPHA — Fondo 100% transparente ***")
        print(f"  Líneas: {len(lineas_con_tiempo)}")
        print(f"  Duración: {duracion:.1f}s")
        print(f"  Beats: {len(beat_times)}")
        print(f"  Resolución: {ancho}x{alto} @ {fps}fps")
        print(f"  Formato salida: WebM VP9 con canal alpha\n")

        # Generar secuencia de PNGs con alpha y luego encode con ffmpeg
        import tempfile
        import subprocess
        import shutil

        temp_dir = tempfile.mkdtemp(prefix="lyric_alpha_")
        print(f"Frames temporales en: {temp_dir}")

        total_frames = int(duracion * fps)
        print(f"Total frames: {total_frames}")

        for frame_num in range(total_frames):
            t = frame_num / fps

            img = crear_frame_alpha(
                ancho, alto, lineas_con_tiempo, t, duracion,
                beat_times, fuente, fuente_titulo, titulo
            )

            frame_path = os.path.join(temp_dir, f"frame_{frame_num:06d}.png")
            img.save(frame_path, 'PNG')

            if frame_num % (fps * 5) == 0:
                pct = (frame_num / total_frames) * 100
                print(f"  Frame {frame_num}/{total_frames} ({pct:.0f}%) — t={t:.1f}s")

        print(f"\nTodos los frames generados. Encodando ProRes 4444 con alpha...")

        # Encontrar ffmpeg
        ffmpeg_bin = 'ffmpeg'
        ffmpeg_winget = os.path.expanduser('~/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe')
        if os.path.exists(ffmpeg_winget):
            ffmpeg_bin = ffmpeg_winget
        else:
            found = shutil.which('ffmpeg')
            if found:
                ffmpeg_bin = found

        # Encode con ffmpeg: ProRes 4444 con alpha channel (.mov)
        mov_output = ruta_salida
        if not mov_output.endswith('.mov'):
            mov_output = ruta_salida.rsplit('.', 1)[0] + '.mov'

        ffmpeg_cmd = [
            ffmpeg_bin, '-y',
            '-framerate', str(fps),
            '-i', os.path.join(temp_dir, 'frame_%06d.png'),
            '-i', ruta_audio,
            '-c:v', 'prores_ks',
            '-profile:v', '4444',
            '-pix_fmt', 'yuva444p10le',
            '-c:a', 'pcm_s16le',
            '-shortest',
            mov_output
        ]

        print(f"Ejecutando: {' '.join(ffmpeg_cmd[:8])}...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"ERROR ffmpeg: {result.stderr[-500:]}")
            # Intentar sin audio
            print("Reintentando sin audio...")
            ffmpeg_cmd_noaudio = [
                ffmpeg_bin, '-y',
                '-framerate', str(fps),
                '-i', os.path.join(temp_dir, 'frame_%06d.png'),
                '-c:v', 'prores_ks',
                '-profile:v', '4444',
                '-pix_fmt', 'yuva444p10le',
                mov_output
            ]
            result = subprocess.run(ffmpeg_cmd_noaudio, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ERROR: {result.stderr[-500:]}")
            else:
                print(f"MOV sin audio generado: {mov_output}")
        else:
            print(f"\nMOV ProRes 4444 con alpha generado: {mov_output}")

        # También generar MP4 con fondo negro (para previsualización)
        mp4_output = ruta_salida.rsplit('.', 1)[0] + '-preview-black.mp4'
        print(f"\nGenerando preview MP4 (fondo negro)...")
        ffmpeg_mp4 = [
            ffmpeg_bin, '-y',
            '-framerate', str(fps),
            '-i', os.path.join(temp_dir, 'frame_%06d.png'),
            '-i', ruta_audio,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-b:v', '5000k',
            '-preset', 'medium',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            '-shortest',
            mp4_output
        ]
        result_mp4 = subprocess.run(ffmpeg_mp4, capture_output=True, text=True)
        if result_mp4.returncode == 0:
            print(f"Preview MP4 generado: {mp4_output}")
        else:
            print(f"Error generando MP4: {result_mp4.stderr[-300:]}")

        # Limpiar frames temporales
        print("Limpiando frames temporales...")
        shutil.rmtree(temp_dir, ignore_errors=True)

        print("\n=== COMPLETADO ===")
        print(f"  Alpha (transparente): {mov_output}")
        print(f"  Preview (fondo negro): {mp4_output}")
        print(f"\n  El .mov se puede importar en DaVinci Resolve, Premiere, CapCut")
        print(f"  con fondo 100% transparente para montar sobre video/foto.")

    else:
        # ========== MODO NORMAL: Fondo con efectos ==========
        bg_image = None
        bg_video = None
        bg_is_video = False

        if bg_path and os.path.exists(bg_path):
            ext = os.path.splitext(bg_path)[1].lower()
            if ext in ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv'):
                print(f"Fondo VIDEO: {bg_path}")
                bg_video = VideoFileClip(bg_path)
                if bg_video.size != [ancho, alto]:
                    bg_video = bg_video.resized((ancho, alto))
                bg_is_video = True
                print(f"  Duración fondo: {bg_video.duration:.1f}s")
            else:
                print(f"Fondo IMAGEN: {bg_path}")
                bg_image = Image.open(bg_path).resize((ancho, alto), Image.Resampling.LANCZOS)

        rms = librosa.feature.rms(y=y_audio)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr).tolist()

        random.seed(42)
        particulas = [Particula(ancho, alto) for _ in range(60)]

        # Crossfade y fade config
        crossfade_dur = 2.0  # segundos de crossfade en el loop
        fade_out_dur = 3.0   # segundos de fade to black al final

        print(f"\nConfiguración:")
        print(f"  Líneas: {len(lineas_con_tiempo)}")
        print(f"  Duración: {duracion:.1f}s")
        print(f"  Beats: {len(beat_times)}")
        print(f"  Esquema: {esquema_nombre}")
        print(f"  Fondo: {'video' if bg_is_video else 'imagen' if bg_image else 'gradiente'}")
        if bg_is_video:
            usable_dur = bg_video.duration - bg_start
            if usable_dur < duracion:
                loops = duracion / usable_dur
                print(f"  Video fondo: {bg_video.duration:.1f}s (desde {bg_start:.1f}s -> {usable_dur:.1f}s usable)")
                print(f"  Audio: {duracion:.1f}s -> loop x{loops:.1f} con crossfade de {crossfade_dur}s")
            else:
                print(f"  Video fondo: {bg_video.duration:.1f}s (desde {bg_start:.1f}s) -> audio {duracion:.1f}s -> sin loop")
            if bg_start > 0:
                print(f"  Inicio en video: {bg_start:.1f}s")
        print(f"  Fade out final: {fade_out_dur}s")
        print(f"  Resolución: {ancho}x{alto} @ {fps}fps")

        def make_frame(t):
            # Si hay video de fondo, extraer frame actual
            current_bg = bg_image
            if bg_is_video and bg_video is not None:
                bg_total_dur = bg_video.duration
                # Duración usable = desde bg_start hasta el final del video
                usable_dur = bg_total_dur - bg_start

                if usable_dur > 0:
                    if usable_dur >= duracion:
                        # Video más largo que audio: simplemente avanzar desde bg_start
                        bg_t = bg_start + t
                        bg_t = min(bg_t, bg_total_dur - 0.01)
                        current_bg = Image.fromarray(bg_video.get_frame(bg_t))
                    else:
                        # Video más corto que audio: loop con crossfade
                        time_in_usable = t % usable_dur
                        bg_t = bg_start + time_in_usable

                        # Crossfade en la zona de transición del loop
                        if usable_dur > crossfade_dur * 2 and t >= usable_dur:
                            if time_in_usable < crossfade_dur:
                                alpha_cf = time_in_usable / crossfade_dur  # 0→1
                                frame_new = bg_video.get_frame(bg_start + time_in_usable)
                                frame_old = bg_video.get_frame(bg_total_dur - crossfade_dur + time_in_usable)
                                blended = (frame_new.astype(float) * alpha_cf +
                                           frame_old.astype(float) * (1 - alpha_cf)).astype(np.uint8)
                                current_bg = Image.fromarray(blended)
                            else:
                                current_bg = Image.fromarray(bg_video.get_frame(bg_t))
                        else:
                            current_bg = Image.fromarray(bg_video.get_frame(bg_t))
                else:
                    current_bg = Image.fromarray(bg_video.get_frame(0))

            img = crear_frame_normal(
                ancho, alto, lineas_con_tiempo, t, duracion,
                beat_times, (rms, rms_times), esquema, fuente,
                fuente_titulo, fuente_peq, particulas, titulo, current_bg,
                solo_fondo=solo_fondo
            )

            # Fade to black en los últimos segundos
            time_left = duracion - t
            if time_left < fade_out_dur:
                fade_alpha = int(255 * (1 - time_left / fade_out_dur))  # 0→255
                fade_overlay = Image.new('RGBA', (ancho, alto), (0, 0, 0, fade_alpha))
                img = img.convert('RGBA')
                img = Image.alpha_composite(img, fade_overlay).convert('RGB')

            return np.array(img)

        print("\nGenerando video...")
        video = VideoClip(make_frame, duration=duracion)
        video = video.with_audio(audio)

        video.write_videofile(
            ruta_salida,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            bitrate='8000k',
            preset='medium',
            logger='bar'
        )

        print(f"\nVideo generado: {ruta_salida}")
        video.close()
        if bg_video is not None:
            bg_video.close()

    audio.close()


def main():
    parser = argparse.ArgumentParser(description="Lyric Video Generator v3")
    parser.add_argument("audio", help="Audio file (wav/mp3)")
    parser.add_argument("timestamps", help="Timestamps JSON (directo o Whisper)")
    parser.add_argument("-o", "--output", required=True, help="Output video (.mp4 o .webm)")
    parser.add_argument("--letra", help="Lyrics file (solo necesario con timestamps Whisper)")
    parser.add_argument("--titulo", default="", help="Título mostrado arriba")
    parser.add_argument("--ancho", type=int, default=1920)
    parser.add_argument("--alto", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--color", default="nocturno",
                        choices=["nocturno", "oscuro", "elegante", "neon", "fuego"])
    parser.add_argument("--bg", help="Background image or video (optional)")
    parser.add_argument("--bg-start", type=float, default=0.0,
                        help="Segundo de inicio en el video de fondo (default: 0)")
    parser.add_argument("--alpha", action="store_true",
                        help="Fondo 100%% transparente (ProRes 4444 con alpha)")
    parser.add_argument("--solo-fondo", action="store_true",
                        help="Solo renderizar fondo (particulas, glow, caratula) sin texto. Para modo combinado con Manim.")

    args = parser.parse_args()

    generar_video(
        args.audio, args.timestamps, args.output,
        args.ancho, args.alto, args.fps, args.titulo, args.color, args.bg,
        args.alpha, args.letra, getattr(args, 'bg_start', 0.0),
        getattr(args, 'solo_fondo', False)
    )


if __name__ == "__main__":
    main()
