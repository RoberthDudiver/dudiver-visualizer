"""Funciones de audio: duracion y analisis de beats."""

import os


def get_audio_duration(audio_path):
    """Retorna la duracion en segundos del audio."""
    from moviepy import AudioFileClip
    ac = AudioFileClip(audio_path)
    dur = ac.duration
    ac.close()
    return dur


def analyze_beats(audio_path):
    """Analiza beats y RMS del audio. Retorna (beat_times, rms, rms_times, y_audio, sr)."""
    import librosa
    import numpy as np
    y_audio, sr = librosa.load(audio_path, sr=22050)
    tempo, beat_frames = librosa.beat.beat_track(y=y_audio, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    rms = librosa.feature.rms(y=y_audio)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr).tolist()
    return beat_times, rms, rms_times
