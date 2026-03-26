"""Adaptacion de tamano de fuentes al ancho del video."""

from app.config import cargar_fuente


def adapted_fonts(font_size, ancho, alto, lines):
    """Adapta fuentes: solo reduce si el texto no cabe en el ancho."""
    fs = font_size
    if lines:
        from PIL import ImageFont, Image, ImageDraw
        test_font = cargar_fuente(fs, True)
        test_img = Image.new("RGB", (10, 10))
        test_draw = ImageDraw.Draw(test_img)
        max_tw = 0
        for l in lines:
            bbox = test_draw.textbbox((0, 0), l, font=test_font)
            max_tw = max(max_tw, bbox[2] - bbox[0])
        max_allowed = ancho * 0.9
        if max_tw > max_allowed:
            fs = max(20, int(fs * (max_allowed / max_tw)))
    return (cargar_fuente(fs, True),
            cargar_fuente(max(16, fs // 2), False),
            cargar_fuente(max(12, fs // 3), False))
