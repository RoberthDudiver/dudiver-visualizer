"""Splash screen como Toplevel — imagen + barra de carga animada."""

import os
import tkinter as tk
from PIL import Image, ImageTk
from app.i18n import t


def show_splash(parent, image_path, seconds=3):
    """Muestra splash como Toplevel. parent se oculta y se restaura al cerrar."""
    parent.withdraw()

    splash = tk.Toplevel()
    splash.overrideredirect(True)
    splash.configure(bg="#0e0e1a")
    splash.attributes("-topmost", True)

    sw = splash.winfo_screenwidth()
    sh = splash.winfo_screenheight()

    img = Image.open(image_path)
    # Más pequeña y elegante
    max_w = min(560, sw - 200)
    ratio = max_w / img.width
    new_h = int(img.height * ratio)
    img = img.resize((max_w, new_h), Image.LANCZOS)

    total_h = new_h + 40
    x = (sw - max_w) // 2
    y = (sh - total_h) // 2
    splash.geometry(f"{max_w}x{total_h}+{x}+{y}")

    photo = ImageTk.PhotoImage(img)
    lbl = tk.Label(splash, image=photo, bg="#0e0e1a", bd=0)
    lbl.image = photo
    lbl.pack()

    # Barra de progreso + "Cargando..."
    bar_frame = tk.Frame(splash, bg="#0e0e1a", height=40)
    bar_frame.pack(fill="x")
    bar_frame.pack_propagate(False)

    bar_w = max_w - 60
    canvas = tk.Canvas(bar_frame, bg="#0e0e1a", height=5,
                       highlightthickness=0, bd=0, width=bar_w)
    canvas.pack(pady=(10, 0))

    tk.Label(bar_frame, text=t("splash.loading"), font=("Segoe UI", 8),
             fg="#7a7a9a", bg="#0e0e1a").pack(pady=(4, 0))

    duration_ms = seconds * 1000
    state = {"p": 0, "steps": duration_ms // 30, "closed": False}

    def animate():
        if state["closed"]:
            return
        state["p"] += 1
        pct = state["p"] / state["steps"]
        w = int(bar_w * pct)
        canvas.delete("all")
        canvas.create_rectangle(0, 0, bar_w, 5, fill="#1a1a2e", outline="")
        if w > 0:
            canvas.create_rectangle(0, 0, w, 5, fill="#e94560", outline="")
            canvas.create_rectangle(max(0, w - 20), 0, w, 5, fill="#ff6b81", outline="")
        if state["p"] < state["steps"]:
            splash.after(30, animate)

    def close():
        state["closed"] = True
        splash.destroy()
        parent.deiconify()
        parent.state("zoomed")

    splash.after(50, animate)
    splash.after(duration_ms, close)
