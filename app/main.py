"""Entry point: app + splash."""

import os
import customtkinter as ctk


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    from app.ui.app import VisualizerApp
    app = VisualizerApp()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    splash_path = os.path.join(base_dir, "splash.png")

    if os.path.exists(splash_path):
        from app.ui.splash import show_splash
        show_splash(app, splash_path, seconds=3)
    else:
        app.state("zoomed")

    app.mainloop()


if __name__ == "__main__":
    main()
