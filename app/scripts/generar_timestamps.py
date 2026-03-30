#!/usr/bin/env python3
"""
Genera timestamps palabra por palabra usando Whisper
Para sincronizar lyric videos
"""
import argparse
import json
import os
import sys

def generar_timestamps(ruta_audio, modelo="base", idioma="es"):
    import whisper

    print(f"Cargando modelo Whisper ({modelo})...")
    model = whisper.load_model(modelo)

    print(f"Transcribiendo: {ruta_audio}")
    result = model.transcribe(
        ruta_audio,
        language=idioma,
        word_timestamps=True
    )

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
