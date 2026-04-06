"""
Mastering engine — Dudiver Master
Análisis automático + procesamiento con pedalboard.

API:
    eng = MasteringEngine()
    info = eng.analyze("song.wav")        # → AnalysisResult
    chain = eng.auto_chain(info, target_lufs=-10)
    result = eng.master("song.wav", "song_master.wav", chain,
                        target_lufs=-10, progress_cb=print)
"""

from __future__ import annotations

import os
import math
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

import numpy as np
import soundfile as sf

try:
    import librosa
except Exception:
    librosa = None

try:
    import pyloudnorm as pyln
except Exception:
    pyln = None

from pedalboard import (
    Pedalboard, HighpassFilter, PeakFilter, HighShelfFilter, LowShelfFilter,
    Compressor, Limiter, Gain, Distortion,
)


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class AnalysisResult:
    path: str
    sample_rate: int
    duration_sec: float
    channels: int
    lufs_integrated: float
    lufs_short_term: float
    peak_dbfs: float
    true_peak_dbfs: float
    rms_dbfs: float
    crest_factor_db: float
    dc_offset: float
    bpm: float
    spectral_centroid_hz: float
    bands_db: dict           # 7 bandas
    character: str           # "muy oscura" | "oscura" | "cálida" | "neutra" | "brillante" | "muy brillante"
    deficiencies: list       # ["falta aire", "lodo en lowmid", ...]
    recommended_preset: str  # "warm_air" | "warm_punchy" | "bright_tame" | "balanced"
    recommended_target_lufs: float

    def as_dict(self):
        return asdict(self)


@dataclass
class MasterResult:
    input_path: str
    output_path: str
    target_lufs: float
    lufs_in: float
    lufs_out: float
    peak_in_dbfs: float
    peak_out_dbfs: float
    gain_applied_db: float
    duration_sec: float
    chain_summary: list = field(default_factory=list)


# ── Engine ──────────────────────────────────────────────────────────────────

class MasteringEngine:
    """Motor de análisis y mastering automático."""

    BANDS = [
        ("sub",      20,    60),
        ("bass",     60,    200),
        ("lowmid",   200,   500),
        ("mid",      500,   2000),
        ("highmid",  2000,  5000),
        ("presence", 5000,  10000),
        ("air",      10000, 20000),
    ]

    # ── Análisis ────────────────────────────────────────────────────────────

    def analyze(self, path: str, progress_cb: Optional[Callable] = None) -> AnalysisResult:
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        if librosa is None or pyln is None:
            raise RuntimeError("Faltan dependencias: librosa y pyloudnorm")

        cb = progress_cb or (lambda *a, **kw: None)
        cb("Cargando audio…", 5)

        data, sr = sf.read(path, always_2d=False)
        if data.ndim == 1:
            mono = data
            channels = 1
            stereo = np.stack([data, data], axis=1)
        else:
            channels = data.shape[1]
            mono = data.mean(axis=1)
            stereo = data if channels == 2 else np.stack([mono, mono], axis=1)

        duration = len(mono) / sr

        cb("Midiendo loudness (LUFS)…", 20)
        meter = pyln.Meter(sr)
        try:
            lufs_int = float(meter.integrated_loudness(stereo))
        except Exception:
            lufs_int = -23.0
        try:
            block_len = int(sr * 3.0)
            if len(mono) >= block_len:
                lufs_st = float(meter.integrated_loudness(stereo[-block_len:]))
            else:
                lufs_st = lufs_int
        except Exception:
            lufs_st = lufs_int

        peak = float(np.max(np.abs(mono)) + 1e-12)
        peak_db = 20 * math.log10(peak)
        # True peak aproximado vía oversample 4x
        try:
            up = librosa.resample(mono.astype(np.float32), orig_sr=sr, target_sr=sr * 4)
            true_peak = float(np.max(np.abs(up)) + 1e-12)
            true_peak_db = 20 * math.log10(true_peak)
        except Exception:
            true_peak_db = peak_db

        rms = float(np.sqrt(np.mean(mono ** 2)) + 1e-12)
        rms_db = 20 * math.log10(rms)
        crest = peak_db - rms_db
        dc = float(np.mean(mono))

        cb("Detectando BPM…", 40)
        try:
            tempo, _ = librosa.beat.beat_track(y=mono.astype(np.float32), sr=sr)
            bpm = float(tempo)
        except Exception:
            bpm = 0.0

        cb("Analizando espectro…", 55)
        try:
            cent = librosa.feature.spectral_centroid(y=mono.astype(np.float32), sr=sr)
            centroid = float(np.mean(cent))
        except Exception:
            centroid = 0.0

        cb("Calculando bandas de frecuencia…", 70)
        bands_db = self._band_energy_db(mono.astype(np.float32), sr)

        cb("Evaluando carácter…", 85)
        character = self._classify_character(centroid, bands_db)
        deficiencies = self._find_deficiencies(bands_db, peak_db, lufs_int)
        preset = self._recommend_preset(character, bands_db)
        target = self._recommend_lufs(bpm)

        cb("Análisis completo", 100)

        return AnalysisResult(
            path=path,
            sample_rate=sr,
            duration_sec=duration,
            channels=channels,
            lufs_integrated=lufs_int,
            lufs_short_term=lufs_st,
            peak_dbfs=peak_db,
            true_peak_dbfs=true_peak_db,
            rms_dbfs=rms_db,
            crest_factor_db=crest,
            dc_offset=dc,
            bpm=bpm,
            spectral_centroid_hz=centroid,
            bands_db=bands_db,
            character=character,
            deficiencies=deficiencies,
            recommended_preset=preset,
            recommended_target_lufs=target,
        )

    def _band_energy_db(self, mono: np.ndarray, sr: int) -> dict:
        n = len(mono)
        # FFT magnitudes
        spec = np.abs(np.fft.rfft(mono * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        total = np.sum(spec ** 2) + 1e-12

        out = {}
        for name, lo, hi in self.BANDS:
            mask = (freqs >= lo) & (freqs < hi)
            energy = np.sum(spec[mask] ** 2)
            ratio = energy / total
            db = 10 * math.log10(ratio + 1e-12)
            out[name] = float(db)
        return out

    def _classify_character(self, centroid: float, bands_db: dict) -> str:
        air = bands_db.get("air", -30)
        presence = bands_db.get("presence", -20)
        bass = bands_db.get("bass", -10)
        if centroid < 1500:
            return "muy oscura"
        if centroid < 2500:
            return "oscura"
        if centroid < 3500:
            return "cálida"
        if centroid < 5000:
            return "neutra"
        if centroid < 7000:
            return "brillante"
        return "muy brillante"

    def _find_deficiencies(self, bands_db: dict, peak_db: float, lufs: float) -> list:
        d = []
        if bands_db.get("air", -30) < -5:
            d.append("falta aire (>10kHz)")
        if bands_db.get("presence", -20) < -7:
            d.append("falta presencia (5-10kHz)")
        if bands_db.get("lowmid", -10) > -3:
            d.append("lodo en lowmid (200-500Hz)")
        if bands_db.get("sub", -20) > -6:
            d.append("exceso de subs")
        if peak_db > -1.0:
            d.append("peaks muy altos (clip risk)")
        if lufs > -8:
            d.append("ya muy alto en loudness")
        if lufs < -20:
            d.append("muy bajo en loudness")
        return d

    def _recommend_preset(self, character: str, bands_db: dict) -> str:
        if character in ("muy oscura", "oscura", "cálida"):
            return "warm_air"
        if character in ("brillante", "muy brillante"):
            return "bright_tame"
        return "warm_punchy"

    def _recommend_lufs(self, bpm: float) -> float:
        if bpm <= 0:
            return -10.0
        if bpm < 90:
            return -12.0
        if bpm < 110:
            return -11.0
        if bpm < 140:
            return -10.0
        return -9.0

    # ── Auto chain ──────────────────────────────────────────────────────────

    def auto_chain(self, info: AnalysisResult, target_lufs: float = -10.0) -> Pedalboard:
        """Genera cadena pedalboard según análisis."""
        preset = info.recommended_preset
        if preset == "warm_air":
            return self._chain_warm_air(info, target_lufs)
        if preset == "bright_tame":
            return self._chain_bright_tame(info, target_lufs)
        return self._chain_warm_punchy(info, target_lufs)

    def chain_by_name(self, name: str, info: AnalysisResult, target_lufs: float) -> Pedalboard:
        return {
            "auto":         self.auto_chain,
            "warm_air":     self._chain_warm_air,
            "warm_punchy":  self._chain_warm_punchy,
            "bright_tame":  self._chain_bright_tame,
            "balanced":     self._chain_balanced,
        }.get(name, self.auto_chain)(info, target_lufs)

    def _gain_for_target(self, lufs_in: float, target: float) -> float:
        # Aproximación: +1 dB en gain ≈ +1 LU. Limiter compensa el resto.
        delta = target - lufs_in
        return max(-6.0, min(14.0, delta + 2.0))

    def _chain_warm_air(self, info: AnalysisResult, target: float) -> Pedalboard:
        """Para fuentes oscuras/cálidas: añade aire y mantiene calidez."""
        gain_db = self._gain_for_target(info.lufs_integrated, target)
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30),
            PeakFilter(80, gain_db=1.5, q=1.0),
            PeakFilter(180, gain_db=1.0, q=1.2),
            PeakFilter(350, gain_db=-1.5, q=1.0),
            PeakFilter(2500, gain_db=0.5, q=1.5),
            HighShelfFilter(8000, gain_db=2.5, q=0.7),
            HighShelfFilter(14000, gain_db=1.5, q=0.7),
            Distortion(drive_db=3),
            Compressor(threshold_db=-20, ratio=2.5, attack_ms=15, release_ms=120),
            Compressor(threshold_db=-12, ratio=2.0, attack_ms=5, release_ms=80),
            Gain(gain_db=gain_db),
            Limiter(threshold_db=-1.0, release_ms=80),
        ])

    def _chain_warm_punchy(self, info: AnalysisResult, target: float) -> Pedalboard:
        gain_db = self._gain_for_target(info.lufs_integrated, target)
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30),
            PeakFilter(80, gain_db=1.0, q=1.0),
            PeakFilter(350, gain_db=-1.0, q=1.0),
            PeakFilter(3000, gain_db=1.0, q=1.2),
            HighShelfFilter(10000, gain_db=1.0, q=0.7),
            Distortion(drive_db=2),
            Compressor(threshold_db=-18, ratio=2.5, attack_ms=10, release_ms=100),
            Compressor(threshold_db=-10, ratio=2.0, attack_ms=5, release_ms=80),
            Gain(gain_db=gain_db),
            Limiter(threshold_db=-1.0, release_ms=80),
        ])

    def _chain_bright_tame(self, info: AnalysisResult, target: float) -> Pedalboard:
        """Para fuentes brillantes: doma highs, añade cuerpo."""
        gain_db = self._gain_for_target(info.lufs_integrated, target)
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30),
            LowShelfFilter(120, gain_db=1.5, q=0.7),
            PeakFilter(350, gain_db=-1.0, q=1.0),
            PeakFilter(6000, gain_db=-2.0, q=1.0),
            HighShelfFilter(10000, gain_db=-1.5, q=0.7),
            Distortion(drive_db=2),
            Compressor(threshold_db=-18, ratio=2.5, attack_ms=15, release_ms=120),
            Compressor(threshold_db=-10, ratio=2.0, attack_ms=5, release_ms=80),
            Gain(gain_db=gain_db),
            Limiter(threshold_db=-1.0, release_ms=80),
        ])

    def _chain_balanced(self, info: AnalysisResult, target: float) -> Pedalboard:
        gain_db = self._gain_for_target(info.lufs_integrated, target)
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30),
            PeakFilter(80, gain_db=0.8, q=1.0),
            PeakFilter(350, gain_db=-0.8, q=1.0),
            HighShelfFilter(10000, gain_db=0.8, q=0.7),
            Compressor(threshold_db=-16, ratio=2.0, attack_ms=10, release_ms=100),
            Gain(gain_db=gain_db),
            Limiter(threshold_db=-1.0, release_ms=80),
        ])

    @staticmethod
    def chain_summary(board: Pedalboard) -> list:
        out = []
        for plug in board:
            name = type(plug).__name__
            params = {}
            for attr in ("cutoff_frequency_hz", "frequency_hz", "gain_db",
                         "threshold_db", "ratio", "attack_ms", "release_ms",
                         "drive_db", "q"):
                if hasattr(plug, attr):
                    try:
                        v = getattr(plug, attr)
                        if isinstance(v, float):
                            v = round(v, 2)
                        params[attr] = v
                    except Exception:
                        pass
            out.append({"plugin": name, **params})
        return out

    # ── Master ──────────────────────────────────────────────────────────────

    def master(
        self,
        input_path: str,
        output_path: str,
        chain: Pedalboard,
        target_lufs: float = -10.0,
        progress_cb: Optional[Callable] = None,
    ) -> MasterResult:
        cb = progress_cb or (lambda *a, **kw: None)
        cb("Cargando audio para masterizar…", 5)

        data, sr = sf.read(input_path, always_2d=True)
        # Asegurar float32 estéreo
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        audio = data.astype(np.float32)

        # Stats in
        mono_in = audio.mean(axis=1)
        peak_in = float(np.max(np.abs(mono_in)) + 1e-12)
        peak_in_db = 20 * math.log10(peak_in)
        meter = pyln.Meter(sr)
        try:
            lufs_in = float(meter.integrated_loudness(audio))
        except Exception:
            lufs_in = -23.0

        cb("Procesando cadena de mastering…", 25)
        # pedalboard espera (samples, channels) → np float32
        out = chain(audio, sr)

        cb("Midiendo loudness final…", 70)
        try:
            lufs_out = float(meter.integrated_loudness(out))
        except Exception:
            lufs_out = lufs_in

        # Ajuste fino para clavar LUFS objetivo (±0.5)
        delta = target_lufs - lufs_out
        if abs(delta) > 0.3 and abs(delta) < 6.0:
            cb("Ajuste fino a LUFS objetivo…", 80)
            gain_lin = 10 ** (delta / 20.0)
            out = out * gain_lin
            try:
                lufs_out = float(meter.integrated_loudness(out))
            except Exception:
                pass

        # Soft clip safety
        peak_out = float(np.max(np.abs(out.mean(axis=1))) + 1e-12)
        peak_out_db = 20 * math.log10(peak_out)
        if peak_out_db > -0.5:
            scale = 10 ** ((-1.0 - peak_out_db) / 20.0)
            out = out * scale
            peak_out = float(np.max(np.abs(out.mean(axis=1))) + 1e-12)
            peak_out_db = 20 * math.log10(peak_out)

        cb("Escribiendo WAV…", 90)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        sf.write(output_path, out, sr, subtype="PCM_16")

        cb("Master listo", 100)

        return MasterResult(
            input_path=input_path,
            output_path=output_path,
            target_lufs=target_lufs,
            lufs_in=lufs_in,
            lufs_out=lufs_out,
            peak_in_dbfs=peak_in_db,
            peak_out_dbfs=peak_out_db,
            gain_applied_db=lufs_out - lufs_in,
            duration_sec=len(out) / sr,
            chain_summary=self.chain_summary(chain),
        )
