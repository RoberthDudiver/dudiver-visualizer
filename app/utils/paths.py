"""Resolución de rutas compatible con PyInstaller --onefile."""

import os
import shutil
import sys


def get_base_dir():
    """Retorna la raíz del proyecto, funciona tanto en dev como en PyInstaller."""
    if getattr(sys, "frozen", False):
        # PyInstaller --onefile extrae a sys._MEIPASS
        return sys._MEIPASS
    # Dev: subir desde app/utils/ → raíz
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def asset_path(*parts):
    """Construye ruta a un asset relativo a la raíz del proyecto."""
    return os.path.join(get_base_dir(), *parts)


def get_ffmpeg():
    """Busca ffmpeg: bundled → WinGet → PATH → fallback."""
    # 1. Bundled junto al exe (installer)
    if getattr(sys, "frozen", False):
        bundled = os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe")
        if os.path.isfile(bundled):
            return bundled
    # 2. WinGet
    winff = os.path.expanduser("~/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe")
    if os.path.isfile(winff):
        return winff
    # 3. PATH
    return shutil.which("ffmpeg") or "ffmpeg"


def get_ffprobe():
    """Busca ffprobe: bundled → PATH → fallback."""
    if getattr(sys, "frozen", False):
        bundled = os.path.join(os.path.dirname(sys.executable), "ffprobe.exe")
        if os.path.isfile(bundled):
            return bundled
    return shutil.which("ffprobe") or "ffprobe"
