"""Entry point: creates and runs VisualizerApp."""

import customtkinter as ctk


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    from app.ui.app import VisualizerApp
    app = VisualizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
