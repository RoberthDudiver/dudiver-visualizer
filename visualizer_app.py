#!/usr/bin/env python3
"""
Dudiver Visualizer Studio v3
Thin launcher — delegates to app.main.
"""

# Forzar icono propio en taskbar de Windows (no el de Python)
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dudiver.visualizer.studio.3")
except Exception:
    pass

from app.main import main

if __name__ == "__main__":
    main()
