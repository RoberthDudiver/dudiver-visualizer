"""Plataformas de streaming — logos, QR codes, y configuración."""

import math
from PIL import Image, ImageDraw, ImageFont


# Colores oficiales de cada plataforma
PLATFORMS = {
    "spotify": {
        "name": "Spotify",
        "color": "#1DB954",
        "bg": "#191414",
    },
    "apple_music": {
        "name": "Apple Music",
        "color": "#FC3C44",
        "bg": "#000000",
    },
    "youtube_music": {
        "name": "YouTube Music",
        "color": "#FF0000",
        "bg": "#000000",
    },
    "amazon_music": {
        "name": "Amazon Music",
        "color": "#25D1DA",
        "bg": "#232F3E",
    },
    "custom": {
        "name": "Custom",
        "color": "#FFFFFF",
        "bg": "#1a1a2e",
    },
}


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def create_platform_icon(platform_key, size=64):
    """Carga el logo de la plataforma desde assets, o genera uno fallback."""
    from app.utils.paths import asset_path
    assets_dir = asset_path("app", "assets")
    logo_path = os.path.join(assets_dir, f"{platform_key}.png")

    if os.path.isfile(logo_path):
        try:
            img = Image.open(logo_path).convert("RGBA")
            img = img.resize((size, size), Image.LANCZOS)
            return img
        except Exception:
            pass

    # Fallback: icono generado
    info = PLATFORMS.get(platform_key, PLATFORMS["custom"])
    color = _hex_to_rgb(info["color"])
    bg = _hex_to_rgb(info["bg"])

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 2
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill=bg + (255,), outline=color + (255,), width=2)
    cx, cy = size // 2, size // 2
    from app.utils.fonts import load_pil_font
    font, _ = load_pil_font("Segoe UI", size // 3, bold=True)
    symbol = {"spotify": "♪", "apple_music": "♪", "youtube_music": "▶",
              "amazon_music": "♫"}.get(platform_key, "★")
    draw.text((cx, cy), symbol, fill=color, font=font, anchor="mm")
    return img


def create_qr_with_logo(url, platform_key, qr_size=200):
    """Genera QR code con el logo de la plataforma en el centro."""
    import qrcode

    info = PLATFORMS.get(platform_key, PLATFORMS["custom"])
    color = _hex_to_rgb(info["color"])

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # Alta corrección para logo
        box_size=10,
        border=3,  # Borde blanco más ancho para que la cámara lo detecte
    )
    qr.add_data(url)
    qr.make(fit=True)

    # QR estándar: módulos NEGROS sobre fondo BLANCO (máxima legibilidad)
    qr_img = qr.make_image(fill_color=(0, 0, 0), back_color=(255, 255, 255))
    qr_img = qr_img.convert("RGBA").resize((qr_size, qr_size), Image.LANCZOS)

    # Bordes redondeados para estética
    corner_r = qr_size // 12
    rounded = Image.new("RGBA", (qr_size, qr_size), (0, 0, 0, 0))
    rounded_draw = ImageDraw.Draw(rounded)
    rounded_draw.rounded_rectangle([0, 0, qr_size - 1, qr_size - 1],
                                    radius=corner_r, fill=(255, 255, 255, 255))
    # Aplicar máscara redondeada
    qr_img = Image.composite(qr_img, rounded, rounded.split()[3])

    # Logo de la plataforma en el centro (20% del QR)
    logo_size = qr_size // 5
    logo = create_platform_icon(platform_key, logo_size)

    # Fondo blanco cuadrado redondeado detrás del logo
    pad = 6
    mask_size = logo_size + pad * 2
    mx = (qr_size - mask_size) // 2
    logo_bg = ImageDraw.Draw(qr_img)
    logo_bg.rounded_rectangle([mx, mx, mx + mask_size, mx + mask_size],
                               radius=4, fill=(255, 255, 255, 255))

    # Pegar logo centrado
    lx = (qr_size - logo_size) // 2
    qr_img.paste(logo, (lx, lx), logo)

    return qr_img


def create_spot_with_platforms(ancho, alto, t_spot, spot_text, spot_subtext,
                                platform_urls):
    """Genera frame de spot con QR codes de plataformas.

    platform_urls: dict {"spotify": "url", "apple_music": "url", ...}
    """
    img = Image.new("RGB", (ancho, alto), (10, 10, 20))
    draw = ImageDraw.Draw(img)

    # Fade in
    alpha = min(1.0, t_spot / 1.0)
    c = int(255 * alpha)

    # Fonts
    from app.utils.fonts import load_pil_font
    font_big, _ = load_pil_font("Segoe UI", max(28, int(ancho * 0.035)), bold=True)
    font_small, _ = load_pil_font("Segoe UI", max(16, int(ancho * 0.02)))
    font_label, _ = load_pil_font("Segoe UI", max(12, int(ancho * 0.014)))

    # Texto principal arriba
    y_text = int(alto * 0.08)
    if spot_text:
        draw.text((ancho // 2, y_text), spot_text,
                  fill=(c, c, c), font=font_big, anchor="mt")
    if spot_subtext:
        ca = int(233 * alpha)
        draw.text((ancho // 2, y_text + int(alto * 0.06)), spot_subtext,
                  fill=(ca, int(0.3 * c), int(0.38 * c)), font=font_small, anchor="mt")

    # Línea decorativa
    lw = int(ancho * 0.25 * alpha)
    ly = y_text - 10
    draw.line([(ancho // 2 - lw, ly), (ancho // 2 + lw, ly)],
              fill=(int(233 * alpha), int(69 * alpha), int(96 * alpha)), width=2)

    # Filtrar plataformas con URL
    active = [(k, v) for k, v in platform_urls.items()
              if v and v.strip() and k in PLATFORMS]

    if not active:
        return img

    # Calcular layout de QR codes
    n = len(active)
    # Tamaño QR proporcional al video
    qr_size = min(int(ancho * 0.18), int(alto * 0.3), 200)
    if n > 3:
        qr_size = min(int(ancho * 0.14), int(alto * 0.25), 160)

    # Posicionar QRs en fila centrada
    spacing = int(qr_size * 0.3)
    total_w = n * qr_size + (n - 1) * spacing
    start_x = (ancho - total_w) // 2
    qr_y = int(alto * 0.3)

    for i, (platform_key, url) in enumerate(active):
        x = start_x + i * (qr_size + spacing)

        # Generar QR
        qr_img = create_qr_with_logo(url, platform_key, qr_size)

        # Aplicar fade
        if alpha < 1.0:
            qr_rgba = qr_img.convert("RGBA")
            a_channel = qr_rgba.split()[3]
            a_channel = a_channel.point(lambda p: int(p * alpha))
            qr_rgba.putalpha(a_channel)
            qr_img = qr_rgba

        # Pegar QR
        img.paste(qr_img.convert("RGB"), (x, qr_y),
                  qr_img.convert("RGBA") if qr_img.mode == "RGBA" else None)

        # Label debajo del QR
        info = PLATFORMS[platform_key]
        label_color = _hex_to_rgb(info["color"])
        label_alpha = tuple(int(ch * alpha) for ch in label_color)
        draw.text((x + qr_size // 2, qr_y + qr_size + 8),
                  info["name"], fill=label_alpha, font=font_label, anchor="mt")

    return img
