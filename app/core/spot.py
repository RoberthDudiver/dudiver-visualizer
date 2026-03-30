"""Generacion de frames para spot publicitario."""

import os
from PIL import Image, ImageDraw, ImageFont

from app.utils.fonts import load_pil_font


def _load_ui_fonts(ancho):
    """Carga fuentes UI para spots de forma portable."""
    font_big, _ = load_pil_font("Segoe UI", max(30, int(ancho * 0.04)), bold=True)
    font_small, _ = load_pil_font("Segoe UI", max(20, int(ancho * 0.025)))
    return font_big, font_small


_spot_clip_cache = {}  # path → (clip, resized_clip)


def _get_spot_clip(spot_file, ancho, alto):
    """Retorna un VideoFileClip cacheado y redimensionado."""
    key = (spot_file, ancho, alto)
    if key in _spot_clip_cache:
        clip = _spot_clip_cache[key]
        if clip is not None:
            return clip
    from moviepy import VideoFileClip
    clip = VideoFileClip(spot_file)
    if clip.size != [ancho, alto]:
        clip = clip.resized((ancho, alto))
    _spot_clip_cache[key] = clip
    return clip


def close_spot_clips():
    """Cierra todos los clips cacheados. Llamar al finalizar render."""
    for clip in _spot_clip_cache.values():
        try:
            if clip:
                clip.close()
        except Exception:
            pass
    _spot_clip_cache.clear()


def create_spot_frame(ancho, alto, t_spot, spot_type, spot_text, spot_subtext,
                      spot_file, platform_urls=None):
    """Genera un frame del spot publicitario."""
    img = Image.new("RGB", (ancho, alto), (0, 0, 0))

    if spot_type == "Texto":
        draw = ImageDraw.Draw(img)
        font_big, font_small = _load_ui_fonts(ancho)

        # Fade in
        alpha = min(1.0, t_spot / 1.5)

        # Texto principal centrado
        bbox1 = draw.textbbox((0, 0), spot_text, font=font_big)
        tw1 = bbox1[2] - bbox1[0]
        y1 = int(alto * 0.12)
        c = int(255 * alpha)
        draw.text(((ancho - tw1) // 2, y1), spot_text,
                  fill=(c, c, c), font=font_big)

        # Subtexto
        if spot_subtext:
            bbox2 = draw.textbbox((0, 0), spot_subtext, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            ca = int(233 * alpha)
            cr = int(0.91 * c)
            draw.text(((ancho - tw2) // 2, y1 + int(alto * 0.07)), spot_subtext,
                      fill=(ca, cr, int(0.37 * c)), font=font_small)

        # Linea decorativa
        lw = int(ancho * 0.3 * alpha)
        cx = ancho // 2
        ly = y1 - 15
        draw.line([(cx - lw, ly), (cx + lw, ly)],
                  fill=(int(233 * alpha), int(69 * alpha), int(96 * alpha)), width=2)

        # QR codes de plataformas
        if platform_urls:
            _draw_platform_qrs(img, ancho, alto, alpha, platform_urls)

    elif spot_type == "Imagen" and spot_file and os.path.isfile(spot_file):
        spot_img = Image.open(spot_file).convert("RGB").resize(
            (ancho, alto), Image.Resampling.LANCZOS)
        alpha = min(1.0, t_spot / 1.5)
        img = Image.blend(img, spot_img, alpha)
        # Solo QR codes si están configurados (sin texto — la imagen ya tiene su diseño)
        if platform_urls:
            _draw_platform_qrs(img, ancho, alto, alpha, platform_urls)

    elif spot_type == "Video" and spot_file and os.path.isfile(spot_file):
        try:
            clip = _get_spot_clip(spot_file, ancho, alto)
            t_video = min(t_spot, clip.duration - 0.1)
            frame = clip.get_frame(max(0, t_video))
            spot_img = Image.fromarray(frame)
            alpha = min(1.0, t_spot / 1.5)
            img = Image.blend(img, spot_img, alpha)
        except Exception:
            pass
        # Solo QR codes si están configurados (sin texto — el video ya tiene su diseño)
        if platform_urls:
            alpha = min(1.0, t_spot / 1.5)
            _draw_platform_qrs(img, ancho, alto, alpha, platform_urls)

    return img


def _draw_spot_overlay(img, ancho, alto, alpha, spot_text, spot_subtext,
                       platform_urls):
    """Dibuja texto + QR codes encima de una imagen/video de fondo."""
    draw = ImageDraw.Draw(img)
    font_big, font_small = _load_ui_fonts(ancho)

    c = int(255 * alpha)

    # Semitransparente detrás del texto para legibilidad
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([0, 0, ancho, int(alto * 0.18)],
                      fill=(0, 0, 0, int(160 * alpha)))
    img.paste(Image.alpha_composite(
        img.convert("RGBA"), overlay).convert("RGB"))

    # Texto principal
    y1 = int(alto * 0.12)
    if spot_text:
        bbox1 = draw.textbbox((0, 0), spot_text, font=font_big)
        tw1 = bbox1[2] - bbox1[0]
        draw.text(((ancho - tw1) // 2, y1 - int(alto * 0.06)),
                  spot_text, fill=(c, c, c), font=font_big)

    # Subtexto
    if spot_subtext:
        bbox2 = draw.textbbox((0, 0), spot_subtext, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        ca = int(233 * alpha)
        draw.text(((ancho - tw2) // 2, y1),
                  spot_subtext, fill=(ca, int(0.91 * c), int(0.37 * c)),
                  font=font_small)

    # Linea decorativa
    lw = int(ancho * 0.3 * alpha)
    cx = ancho // 2
    ly = y1 - int(alto * 0.08)
    draw.line([(cx - lw, ly), (cx + lw, ly)],
              fill=(int(233 * alpha), int(69 * alpha), int(96 * alpha)),
              width=2)

    # QR codes de plataformas
    if platform_urls:
        _draw_platform_qrs(img, ancho, alto, alpha, platform_urls)


def _draw_platform_qrs(img, ancho, alto, alpha, platform_urls):
    """Dibuja QR codes en grilla 2x2 con logos de plataformas — grandes y bonitos."""
    try:
        import qrcode
    except ImportError:
        return

    active = [(k, v) for k, v in platform_urls.items() if v and v.strip()]
    if not active:
        return

    from app.core.platforms import PLATFORMS, create_qr_with_logo, _hex_to_rgb

    n = len(active)

    # QR grandes — 2 columnas
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols

    # Tamaño QR grande — sin límite fijo
    qr_size = min(int(ancho * 0.35), int(alto * 0.28))
    if n > 2:
        qr_size = min(int(ancho * 0.30), int(alto * 0.24))
    spacing_x = int(qr_size * 0.2)
    spacing_y = int(qr_size * 0.12)

    font_label, _ = load_pil_font("Segoe UI", max(16, int(ancho * 0.022)), bold=True)

    draw = ImageDraw.Draw(img)
    label_h = int(ancho * 0.04)  # espacio para label debajo
    pad = max(8, int(qr_size * 0.06))  # padding del card

    # Calcular dimensiones totales de la grilla
    card_w = qr_size + pad * 2
    card_h = qr_size + pad * 2 + label_h
    grid_w = cols * card_w + (cols - 1) * spacing_x
    grid_h = rows * card_h + (rows - 1) * spacing_y

    # Centrar la grilla (debajo del texto)
    start_x = (ancho - grid_w) // 2
    start_y = int(alto * 0.28)
    if start_y + grid_h > alto - 30:
        start_y = max(int(alto * 0.20), alto - grid_h - 30)

    # Una sola overlay RGBA para todas las cards (evita N alpha_composites full-size)
    cards_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cards_draw = ImageDraw.Draw(cards_overlay)
    r = max(8, int(qr_size * 0.05))

    for i, (platform_key, url) in enumerate(active):
        col = i % cols
        row = i // cols
        cx = start_x + col * (card_w + spacing_x)
        cy = start_y + row * (card_h + spacing_y)
        info = PLATFORMS.get(platform_key, PLATFORMS.get("custom", {}))
        rgb = _hex_to_rgb(info.get("color", "#FFFFFF"))
        # Sombra
        cards_draw.rounded_rectangle(
            [cx + 3, cy + 3, cx + card_w + 3, cy + card_h + 3],
            radius=r, fill=(0, 0, 0, int(120 * alpha)))
        # Fondo del card
        cards_draw.rounded_rectangle(
            [cx, cy, cx + card_w, cy + card_h],
            radius=r, fill=(20, 20, 30, int(220 * alpha)),
            outline=rgb + (int(200 * alpha),), width=2)

    # Un solo composite para todas las cards
    img.paste(Image.alpha_composite(
        img.convert("RGBA"), cards_overlay).convert("RGB"))

    for i, (platform_key, url) in enumerate(active):
        col = i % cols
        row = i // cols
        cx = start_x + col * (card_w + spacing_x)
        cy = start_y + row * (card_h + spacing_y)
        info = PLATFORMS.get(platform_key, PLATFORMS.get("custom", {}))
        color = info.get("color", "#FFFFFF")
        rgb = _hex_to_rgb(color)

        # QR centrado en el card
        qr_x = cx + pad
        qr_y = cy + pad
        qr_img = create_qr_with_logo(url, platform_key, qr_size)

        if alpha < 1.0:
            qr_rgba = qr_img.convert("RGBA")
            a_ch = qr_rgba.split()[3]
            a_ch = a_ch.point(lambda p: int(p * alpha))
            qr_rgba.putalpha(a_ch)
            qr_img = qr_rgba

        img.paste(qr_img.convert("RGB"), (qr_x, qr_y),
                  qr_img.convert("RGBA"))

        # Label con color de la plataforma
        label_c = tuple(int(ch * alpha) for ch in rgb)
        draw = ImageDraw.Draw(img)
        draw.text((cx + card_w // 2, qr_y + qr_size + pad // 2 + 2),
                  info.get("name", platform_key),
                  fill=label_c, font=font_label, anchor="mt")
