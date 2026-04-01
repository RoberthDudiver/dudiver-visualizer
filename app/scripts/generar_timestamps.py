#!/usr/bin/env python3
"""
Genera timestamps palabra por palabra usando Whisper.
Opcionalmente separa voces con Demucs para mejor detección en música.
"""
import argparse
import json
import os
import sys
import tempfile
import shutil


# ── Separación de voces con Demucs ──────────────────────────────────────────

def _separar_voces(ruta_audio, on_log=None):
    """Separa las voces del instrumental usando Demucs.

    Retorna ruta al archivo de voces aisladas, o None si falla.
    """
    log = on_log or print
    try:
        import torch
        import torchaudio
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
    except ImportError:
        log("  Demucs no disponible — usando audio original")
        return None

    try:
        import numpy as np
        import soundfile as sf
        log("  Separando voces con Demucs...")

        # htdemucs: mejor calidad pero más lento en CPU
        # htdemucs_ft: fine-tuned, ligeramente mejor
        model = get_model("htdemucs")
        model.eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)

        # Cargar audio con soundfile (soporta MP3, WAV, FLAC, etc.)
        audio_np, sr = sf.read(ruta_audio, dtype="float32")
        # soundfile retorna (samples, channels) — convertir a (channels, samples)
        if audio_np.ndim == 1:
            audio_np = np.stack([audio_np, audio_np])  # mono → stereo
        else:
            audio_np = audio_np.T  # (samples, ch) → (ch, samples)
        wav = torch.from_numpy(audio_np).float()

        # Resamplear si es necesario
        if sr != model.samplerate:
            wav = torchaudio.functional.resample(wav, sr, model.samplerate)
            sr = model.samplerate

        # Asegurar stereo
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)

        # Normalizar para Demucs
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()
        wav_input = wav.unsqueeze(0).to(device)

        with torch.no_grad():
            sources = apply_model(model, wav_input, device=device)

        # sources shape: [1, n_sources, channels, samples]
        source_names = model.sources  # ['drums', 'bass', 'other', 'vocals']
        vocals_idx = source_names.index("vocals")
        vocals = sources[0, vocals_idx]  # [channels, samples]

        # Desnormalizar
        vocals = vocals * ref.std() + ref.mean()

        # Guardar a WAV temporal
        vocals_path = os.path.join(
            tempfile.gettempdir(),
            "dvs_vocals_" + os.path.splitext(os.path.basename(ruta_audio))[0] + ".wav"
        )
        # soundfile espera (samples, channels)
        sf.write(vocals_path, vocals.cpu().numpy().T, sr)
        size_mb = os.path.getsize(vocals_path) / (1024 * 1024)
        log(f"  Voces separadas OK ({size_mb:.1f} MB)")
        return vocals_path
    except Exception as e:
        log(f"  Demucs error: {e} — usando audio original")
        return None


# ── Generación de timestamps ────────────────────────────────────────────────

def generar_timestamps(ruta_audio, modelo="base", idioma="es", on_log=None,
                       usar_demucs=True):
    """Genera timestamps con Whisper. Si usar_demucs=True, separa voces primero."""
    import whisper
    log = on_log or print

    # Intentar separar voces con Demucs para mejor detección
    audio_para_whisper = ruta_audio
    vocals_tmp = None
    if usar_demucs:
        vocals_tmp = _separar_voces(ruta_audio, on_log=log)
        if vocals_tmp and os.path.isfile(vocals_tmp):
            audio_para_whisper = vocals_tmp
            log("  Whisper analizará las voces aisladas")

    log(f"  Cargando modelo Whisper ({modelo})...")
    model = whisper.load_model(modelo)

    log(f"  Transcribiendo...")
    result = model.transcribe(
        audio_para_whisper,
        language=idioma,
        word_timestamps=True
    )

    # Limpiar archivo temporal de voces
    if vocals_tmp and os.path.isfile(vocals_tmp):
        try:
            os.remove(vocals_tmp)
        except Exception:
            pass

    palabras = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            palabras.append({
                "palabra": w["word"].strip(),
                "inicio": round(w["start"], 3),
                "fin": round(w["end"], 3)
            })

    segmentos = []
    for seg in result["segments"]:
        segmentos.append({
            "inicio": round(seg["start"], 3),
            "fin": round(seg["end"], 3),
            "texto": seg["text"].strip()
        })

    return {
        "palabras": palabras,
        "segmentos": segmentos,
        "texto_completo": result["text"].strip()
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", help="Ruta al archivo de audio")
    parser.add_argument("-o", "--output", help="Archivo JSON de salida", required=True)
    parser.add_argument("--modelo", default="base", help="Modelo Whisper")
    parser.add_argument("--idioma", default="es", help="Idioma")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"Error: {args.audio} no existe")
        sys.exit(1)

    resultado = generar_timestamps(args.audio, args.modelo, args.idioma)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n{len(resultado['palabras'])} palabras detectadas")
    print(f"Guardado en: {args.output}")

    # Preview
    for p in resultado['palabras'][:20]:
        print(f"  [{p['inicio']:.2f} - {p['fin']:.2f}] {p['palabra']}")
    if len(resultado['palabras']) > 20:
        print(f"  ... y {len(resultado['palabras'])-20} más")

if __name__ == "__main__":
    main()
