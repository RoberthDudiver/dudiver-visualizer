"""Ventana de configuración: GPU, rendimiento."""

import json
import os
import customtkinter as ctk

from app.config import ACCENT, ACCENT_H, DARK, CARD, DIM, INPUT_BG, GOLD, GREEN


SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "settings.json"
)

DEFAULT_SETTINGS = {
    "gpu_enabled": False,
    "gpu_backend": "auto",  # auto, cuda, opencl
    "render_threads": 4,
    "manim_quality": "high_quality",  # low_quality, medium_quality, high_quality
    "ffmpeg_hwaccel": "auto",  # auto, nvenc, qsv, amf, none
}


def load_settings():
    """Carga settings.json o retorna defaults."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            merged = {**DEFAULT_SETTINGS, **saved}
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(data):
    """Guarda settings.json."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def detect_gpu():
    """Detecta GPUs disponibles."""
    gpus = []
    # NVIDIA
    try:
        import subprocess
        r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                if line.strip():
                    gpus.append(f"NVIDIA {line.strip()}")
    except Exception:
        pass
    # ffmpeg hwaccel
    try:
        import subprocess
        r = subprocess.run(["ffmpeg", "-hwaccels"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            accels = [l.strip() for l in r.stdout.split("\n") if l.strip() and l.strip() != "Hardware acceleration methods:"]
            return gpus, accels
    except Exception:
        pass
    return gpus, []


class SettingsWindow(ctk.CTkToplevel):
    """Ventana de configuración de GPU y rendimiento."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configuración — GPU & Rendimiento")
        self.configure(fg_color=DARK)
        self.geometry("460x520")
        self.resizable(False, False)
        self.transient(parent)
        self.focus_force()

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"460x520+{(sw-460)//2}+{(sh-520)//2}")

        # Icono
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        ico_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(ico_path):
            self.after(50, lambda: self.iconbitmap(ico_path))

        self._settings = load_settings()

        # Header
        ctk.CTkLabel(self, text="⚙  CONFIGURACIÓN", font=("Segoe UI Black", 18),
                     text_color=ACCENT).pack(pady=(16, 8))
        ctk.CTkFrame(self, fg_color=ACCENT, height=1, width=200,
                     corner_radius=0).pack(pady=(0, 12))

        # GPU Detection
        gpus, accels = detect_gpu()

        gpu_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        gpu_frame.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(gpu_frame, text="GPU Detectada", font=("Segoe UI Semibold", 12),
                     text_color=GOLD).pack(anchor="w", padx=12, pady=(8, 2))

        gpu_text = gpus[0] if gpus else "No se detectó GPU dedicada"
        gpu_color = GREEN if gpus else DIM
        ctk.CTkLabel(gpu_frame, text=gpu_text, font=("Segoe UI", 11),
                     text_color=gpu_color).pack(anchor="w", padx=12, pady=(0, 8))

        # GPU toggle
        self.gpu_var = ctk.BooleanVar(value=self._settings["gpu_enabled"])
        ctk.CTkSwitch(gpu_frame, text="Usar GPU para renderizar",
                      variable=self.gpu_var, font=("Segoe UI", 11),
                      fg_color=INPUT_BG, progress_color=ACCENT,
                      button_color=GOLD, button_hover_color=ACCENT_H
                      ).pack(anchor="w", padx=12, pady=(0, 8))

        # FFmpeg hardware acceleration
        accel_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        accel_frame.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(accel_frame, text="Codificación de Video",
                     font=("Segoe UI Semibold", 12),
                     text_color=GOLD).pack(anchor="w", padx=12, pady=(8, 4))

        hw_options = ["auto", "none"]
        if any("cuda" in a or "nvdec" in a for a in accels):
            hw_options.insert(1, "nvenc (NVIDIA)")
        if any("qsv" in a for a in accels):
            hw_options.insert(1, "qsv (Intel)")
        if any("amf" in a or "d3d11va" in a for a in accels):
            hw_options.insert(1, "amf (AMD)")

        row = ctk.CTkFrame(accel_frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(row, text="Aceleración:", font=("Segoe UI", 11),
                     text_color=DIM, width=90).pack(side="left")
        self.hwaccel_var = ctk.StringVar(value=self._settings["ffmpeg_hwaccel"])
        ctk.CTkOptionMenu(row, variable=self.hwaccel_var, values=hw_options,
                          font=("Segoe UI", 11), fg_color=INPUT_BG,
                          button_color=ACCENT, button_hover_color=ACCENT_H,
                          dropdown_fg_color=CARD, width=200).pack(side="left", padx=4)

        # Manim quality
        row2 = ctk.CTkFrame(accel_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(row2, text="Calidad Manim:", font=("Segoe UI", 11),
                     text_color=DIM, width=90).pack(side="left")
        self.quality_var = ctk.StringVar(value=self._settings["manim_quality"])
        ctk.CTkOptionMenu(row2, variable=self.quality_var,
                          values=["low_quality", "medium_quality", "high_quality"],
                          font=("Segoe UI", 11), fg_color=INPUT_BG,
                          button_color=ACCENT, button_hover_color=ACCENT_H,
                          dropdown_fg_color=CARD, width=200).pack(side="left", padx=4)

        # Threads
        row3 = ctk.CTkFrame(accel_frame, fg_color="transparent")
        row3.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(row3, text="Threads:", font=("Segoe UI", 11),
                     text_color=DIM, width=90).pack(side="left")
        self.threads_var = ctk.StringVar(value=str(self._settings["render_threads"]))
        ctk.CTkOptionMenu(row3, variable=self.threads_var,
                          values=["1", "2", "4", "8", "12", "16"],
                          font=("Segoe UI", 11), fg_color=INPUT_BG,
                          button_color=ACCENT, button_hover_color=ACCENT_H,
                          dropdown_fg_color=CARD, width=200).pack(side="left", padx=4)

        # HW accels disponibles
        if accels:
            info = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
            info.pack(fill="x", padx=20, pady=8)
            ctk.CTkLabel(info, text="Aceleradores disponibles:",
                         font=("Segoe UI Semibold", 11),
                         text_color=DIM).pack(anchor="w", padx=12, pady=(8, 2))
            ctk.CTkLabel(info, text=", ".join(accels),
                         font=("Consolas", 9), text_color="#4a4a6a",
                         wraplength=400).pack(anchor="w", padx=12, pady=(0, 8))

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=16)
        ctk.CTkButton(btn_frame, text="Guardar", font=("Segoe UI Semibold", 12),
                      fg_color=ACCENT, hover_color=ACCENT_H, width=120,
                      corner_radius=8, command=self._save).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Cancelar", font=("Segoe UI Semibold", 12),
                      fg_color="#2a2a4a", hover_color="#3a3a5a", width=120,
                      corner_radius=8, command=self.destroy).pack(side="left", padx=4)

    def _save(self):
        self._settings["gpu_enabled"] = self.gpu_var.get()
        self._settings["ffmpeg_hwaccel"] = self.hwaccel_var.get()
        self._settings["manim_quality"] = self.quality_var.get()
        self._settings["render_threads"] = int(self.threads_var.get())
        save_settings(self._settings)
        self.destroy()
