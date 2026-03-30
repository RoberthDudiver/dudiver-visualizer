"""Entry point: app + splash."""

import os
import customtkinter as ctk

from app.utils.paths import asset_path


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    from app.ui.app import VisualizerApp
    app = VisualizerApp()

    splash_path = asset_path("splash.png")

    if os.path.exists(splash_path):
        from app.ui.splash import show_splash
        show_splash(app, splash_path, seconds=3)
    else:
        app.state("zoomed")

    app.mainloop()


if __name__ == "__main__":
    main()
