"""Ventana About compacta con avatar, redes y efectos."""

import os
import math
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter

from app.config import ACCENT, ACCENT_H, DARK, DIM, GOLD


class AboutWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About — Dudiver Visualizer")
        self.configure(fg_color="#080810")
        self.resizable(False, False)
        # Evitar que minimice la ventana principal
        self.after(100, lambda: self.attributes("-topmost", True))
        self.after(200, lambda: self.lift())

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))

        # Icono de la ventana
        ico_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(ico_path):
            self.after(50, lambda: self.iconbitmap(ico_path))
        author_path = os.path.join(base_dir, "author.png")
        icon_path = os.path.join(base_dir, "icon.png")

        w, h = 360, 480
        self.geometry(f"{w}x{h}")
        # Centrar en pantalla
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Canvas de fondo para partículas
        self._canvas = tk.Canvas(self, bg="#080810", highlightthickness=0,
                                 width=w, height=h)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)

        import random
        self._particles = [
            {"x": random.uniform(0, w), "y": random.uniform(0, h),
             "vy": random.uniform(-0.4, -0.1), "r": random.uniform(1, 2.5),
             "phase": random.uniform(0, 6.28)}
            for _ in range(25)
        ]
        self._tick = 0

        # Frame principal
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.place(relx=0.5, rely=0.5, anchor="center")

        # Logo + título en una fila
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(pady=(0, 6))
        if os.path.exists(icon_path):
            logo = ctk.CTkImage(Image.open(icon_path), size=(40, 40))
            ctk.CTkLabel(header, image=logo, text="").pack(side="left", padx=(0, 8))
        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left")
        ctk.CTkLabel(title_col, text="DUDIVER VISUALIZER",
                     font=("Segoe UI Black", 16), text_color=ACCENT).pack(anchor="w")
        from app import __version__
        ctk.CTkLabel(title_col, text=f"Studio v{__version__}",
                     font=("Segoe UI Light", 11), text_color=DIM).pack(anchor="w")

        # Avatar circular
        if os.path.exists(author_path):
            avatar = self._circular_avatar(author_path, 100)
            self._avatar_ref = ImageTk.PhotoImage(avatar)
            tk.Label(main, image=self._avatar_ref, bg="#080810", bd=0).pack(pady=(8, 4))

        ctk.CTkLabel(main, text="Dudiver", font=("Segoe UI Black", 16),
                     text_color=GOLD).pack()
        ctk.CTkLabel(main, text="Venezuelan · No defined genre",
                     font=("Segoe UI", 10), text_color=DIM).pack(pady=(0, 8))

        # Redes — compactas
        redes = [
            ("Instagram", "@dudivermusic", "https://www.instagram.com/dudivermusic/"),
            ("TikTok", "@dudivermusic", "https://www.tiktok.com/@dudivermusic"),
            ("YouTube", "@Dudiver", "https://www.youtube.com/@Dudiver"),
            ("Spotify", "Dudiver", "https://open.spotify.com/intl-es/artist/1Eaivk6y1bOzfcje76FFYd"),
            ("Apple Music", "Dudiver", "https://music.apple.com/us/artist/dudiver/1886584603"),
            ("GitHub", "RoberthDudiver", "https://github.com/RoberthDudiver"),
        ]
        for plat, handle, url in redes:
            row = ctk.CTkFrame(main, fg_color="transparent", height=24)
            row.pack(fill="x")
            ctk.CTkLabel(row, text=plat, font=("Segoe UI Semibold", 10),
                         text_color=ACCENT, width=55, anchor="e").pack(side="left")
            btn = ctk.CTkButton(row, text=handle, font=("Segoe UI", 10),
                                text_color=GOLD, fg_color="transparent",
                                hover_color="#1a1a2e", height=22, anchor="w",
                                command=lambda u=url: self._open(u) if u else None)
            btn.pack(side="left", padx=4)

        # Footer
        ctk.CTkFrame(main, fg_color="#1a1a2e", height=1, width=240,
                     corner_radius=0).pack(pady=(8, 4))
        ctk.CTkLabel(main, text="Hecho con ♥ desde Venezuela",
                     font=("Segoe UI", 9), text_color="#3a3a5a").pack()

        # Animar partículas
        self._animate()

    def _circular_avatar(self, path, size):
        img = Image.open(path).resize((size, size), Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)

        pad = 8
        total = size + pad * 2
        canvas = Image.new("RGBA", (total, total), (0, 0, 0, 0))
        # Glow
        glow = Image.new("RGBA", (total, total), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for i in range(6, 0, -1):
            a = int(40 * (1 - i / 6))
            gd.ellipse((pad - i, pad - i, pad + size + i, pad + size + i),
                       outline=(233, 69, 96, a), width=2)
        glow = glow.filter(ImageFilter.GaussianBlur(3))
        canvas = Image.alpha_composite(canvas, glow)
        ImageDraw.Draw(canvas).ellipse(
            (pad - 2, pad - 2, pad + size + 2, pad + size + 2),
            outline=(233, 69, 96, 180), width=2)
        canvas.paste(img, (pad, pad), img)
        return canvas

    def _animate(self):
        if not self.winfo_exists():
            return
        self._canvas.delete("p")
        self._tick += 1
        for p in self._particles:
            p["y"] += p["vy"]
            if p["y"] < -5:
                p["y"] = 490
            flicker = 0.5 + 0.5 * math.sin(self._tick * 0.06 + p["phase"])
            a = int(flicker * 180)
            color = f"#{a:02x}{a//4:02x}{a:02x}"
            r = p["r"]
            self._canvas.create_oval(p["x"]-r, p["y"]-r, p["x"]+r, p["y"]+r,
                                     fill=color, outline="", tags="p")
        self.after(33, self._animate)

    def _open(self, url):
        import webbrowser
        webbrowser.open(url)
