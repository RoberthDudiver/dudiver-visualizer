"""Adaptacion de tamano de fuentes al ancho del video."""

import os
from PIL import ImageFont

from app.config import cargar_fuente

# Cache de resolución nombre → path
_font_path_cache = {}

# Cache global de fuentes del sistema (lazy, se construye una vez)
_SYSTEM_FONTS = None
_warned_fonts = set()


def _build_system_font_map():
    """Construye un mapa completo nombre→path de todas las fuentes del sistema.

    Usa el registro de Windows para obtener el mapeo real nombre→archivo.
    Fallback: escaneo de C:/Windows/Fonts.
    """
    global _SYSTEM_FONTS
    if _SYSTEM_FONTS is not None:
        return _SYSTEM_FONTS

    _SYSTEM_FONTS = {}
    fonts_dir = "C:/Windows/Fonts"

    # Método 1: Registro de Windows (el más preciso)
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
        i = 0
        while True:
            try:
                reg_name, filename, _ = winreg.EnumValue(key, i)
                i += 1
                # reg_name = "Bodoni MT (TrueType)", filename = "BOD_R.TTF"
                # Extraer nombre limpio: quitar " (TrueType)", " (OpenType)", etc.
                clean = reg_name.split(" (")[0].strip()
                # Quitar variantes de estilo para mapeo genérico
                clean_lower = clean.lower()

                # Path completo
                if os.path.isabs(filename):
                    path = filename
                else:
                    path = os.path.join(fonts_dir, filename)

                if not os.path.isfile(path):
                    continue

                # Guardar por nombre completo limpio
                _SYSTEM_FONTS[clean_lower] = path
                # Sin espacios
                _SYSTEM_FONTS[clean_lower.replace(" ", "")] = path

                # Para "Bodoni MT Negrita" → también guardar "Bodoni MT" como base
                # (solo si no hay una entrada más específica ya)
                parts = clean_lower.split()
                # Variantes de estilo a excluir del nombre base
                style_words = {"bold", "negrita", "cursiva", "italic", "light",
                               "black", "condensed", "poster", "compressed",
                               "thin", "semibold", "extrabold", "medium"}
                base_parts = [p for p in parts if p not in style_words]
                if base_parts and len(base_parts) < len(parts):
                    base_name = " ".join(base_parts)
                    if base_name not in _SYSTEM_FONTS:
                        _SYSTEM_FONTS[base_name] = path
            except OSError:
                break
        key.Close()
    except Exception:
        pass

    # Método 2: escanear C:/Windows/Fonts como fallback
    if not _SYSTEM_FONTS:
        try:
            for f in os.listdir(fonts_dir):
                if f.lower().endswith((".ttf", ".otf")):
                    path = os.path.join(fonts_dir, f)
                    base = os.path.splitext(f)[0].lower()
                    _SYSTEM_FONTS[base] = path
        except OSError:
            pass

    return _SYSTEM_FONTS


def resolve_font_path(font_name):
    """Resuelve un nombre de fuente al path .ttf en el sistema.

    Acepta: "Arial", "Impact", "Bodoni MT", path completo, etc.
    Retorna: path absoluto al .ttf, o None si no se encuentra.
    """
    if not font_name:
        return None

    if font_name in _font_path_cache:
        return _font_path_cache[font_name]

    # Si ya es un path válido
    if os.path.isfile(font_name):
        _font_path_cache[font_name] = font_name
        return font_name

    # Consultar mapa de fuentes del sistema
    sys_fonts = _build_system_font_map()
    name_lower = font_name.lower()

    # Búsqueda exacta
    if name_lower in sys_fonts:
        _font_path_cache[font_name] = sys_fonts[name_lower]
        return sys_fonts[name_lower]

    # Sin espacios
    no_spaces = name_lower.replace(" ", "")
    if no_spaces in sys_fonts:
        _font_path_cache[font_name] = sys_fonts[no_spaces]
        return sys_fonts[no_spaces]

    # Búsqueda parcial (para variantes como "Bodoni MT" → "bodoni mt")
    for key, path in sys_fonts.items():
        if name_lower in key or key in name_lower:
            _font_path_cache[font_name] = path
            return path

    # Fallback: buscar directamente en C:/Windows/Fonts
    fonts_dir = "C:/Windows/Fonts"
    for ext in [".ttf", ".otf"]:
        for candidate in [font_name, font_name.lower(), font_name.replace(" ", "")]:
            path = os.path.join(fonts_dir, candidate + ext)
            if os.path.isfile(path):
                _font_path_cache[font_name] = path
                return path

    _font_path_cache[font_name] = None
    return None


def load_pil_font(font_name, size, bold=False):
    """Carga un PIL ImageFont por nombre de fuente y tamaño.

    Intenta resolver el nombre a un path .ttf.
    Si falla, usa la fuente por defecto del sistema.
    Retorna: (font, found) — found=True si se resolvió la fuente pedida.
    """
    found = False

    # Intentar nombre bold si aplica
    if bold:
        bold_path = resolve_font_path(font_name + " Bold")
        if bold_path:
            try:
                return ImageFont.truetype(bold_path, size), True
            except Exception:
                pass

    path = resolve_font_path(font_name)
    if path:
        try:
            return ImageFont.truetype(path, size), True
        except Exception:
            pass

    # Intentar directamente (PIL a veces resuelve nombres del sistema)
    try:
        font = ImageFont.truetype(font_name, size)
        return font, True
    except Exception:
        pass

    # Warning (una vez por fuente)
    if font_name and font_name not in _warned_fonts:
        _warned_fonts.add(font_name)
        print(f"[DVS] Fuente '{font_name}' no encontrada, usando Arial")

    # Fallback
    try:
        return ImageFont.truetype("arial.ttf", size), False
    except Exception:
        return ImageFont.load_default(), False


def adapted_fonts(font_size, ancho, alto, lines, font_name=None):
    """Adapta fuentes: solo reduce si el texto no cabe en el ancho.

    Si font_name se provee, usa esa fuente. Si no, usa la por defecto.
    Retorna: (fuente, fuente_titulo, fuente_peq, font_found)
    """
    fs = font_size

    if font_name:
        _found_flag = [True]

        def _load(sz, bold=True):
            font, found = load_pil_font(font_name, sz, bold=bold)
            if not found:
                _found_flag[0] = False
            return font
    else:
        _found_flag = [True]
        _load = lambda sz, bold=True: cargar_fuente(sz, bold)

    if lines:
        from PIL import Image, ImageDraw
        test_font = _load(fs, True)
        test_img = Image.new("RGB", (10, 10))
        test_draw = ImageDraw.Draw(test_img)
        max_tw = 0
        for l in lines:
            bbox = test_draw.textbbox((0, 0), l, font=test_font)
            max_tw = max(max_tw, bbox[2] - bbox[0])
        max_allowed = ancho * 0.9
        if max_tw > max_allowed:
            fs = max(20, int(fs * (max_allowed / max_tw)))
    return (_load(fs, True),
            _load(max(16, fs // 2), False),
            _load(max(12, fs // 3), False),
            _found_flag[0])
