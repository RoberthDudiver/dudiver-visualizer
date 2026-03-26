"""Generacion de frames para spot publicitario."""

import os
from PIL import Image, ImageDraw, ImageFont


def create_spot_frame(ancho, alto, t_spot, spot_type, spot_text, spot_subtext, spot_file):
    """Genera un frame del spot publicitario."""
    img = Image.new("RGB", (ancho, alto), (0, 0, 0))

    if spot_type == "Texto":
        draw = ImageDraw.Draw(img)
        try:
            font_big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf",
                                          max(30, int(ancho * 0.04)))
            font_small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",
                                            max(20, int(ancho * 0.025)))
        except Exception:
            font_big = ImageFont.load_default()
            font_small = font_big

        # Fade in
        alpha = min(1.0, t_spot / 1.5)

        # Texto principal centrado
        bbox1 = draw.textbbox((0, 0), spot_text, font=font_big)
        tw1 = bbox1[2] - bbox1[0]
        y1 = alto // 2 - 40
        c = int(255 * alpha)
        draw.text(((ancho - tw1) // 2, y1), spot_text,
                  fill=(c, c, c), font=font_big)

        # Subtexto
        if spot_subtext:
            bbox2 = draw.textbbox((0, 0), spot_subtext, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            ca = int(233 * alpha)
            cr = int(0.91 * c)
            draw.text(((ancho - tw2) // 2, y1 + 60), spot_subtext,
                      fill=(ca, cr, int(0.37 * c)), font=font_small)

        # Linea decorativa
        lw = int(ancho * 0.3 * alpha)
        cx = ancho // 2
        ly = y1 - 20
        draw.line([(cx - lw, ly), (cx + lw, ly)],
                  fill=(int(233 * alpha), int(69 * alpha), int(96 * alpha)), width=2)

    elif spot_type == "Imagen" and spot_file and os.path.isfile(spot_file):
        spot_img = Image.open(spot_file).resize((ancho, alto),
                                                Image.Resampling.LANCZOS)
        alpha = min(1.0, t_spot / 1.5)
        img = Image.blend(img, spot_img, alpha)

    return img
