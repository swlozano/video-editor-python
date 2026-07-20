#!/usr/bin/env python3
"""
detect_bands.py

Analiza un archivo de audio y determina en qué momentos (segmentos de tiempo)
predomina cada banda de frecuencia (graves, medios, agudos, etc).

Requisitos:
    pip install librosa soundfile numpy

Uso básico:
    python detect_bands.py song.mp3

Uso avanzado:
    python detect_bands.py song.mp3 --band bass
    python detect_bands.py song.mp3 --out result.csv
    python detect_bands.py song.mp3 --min-duration 0.3
"""

import argparse
import sys
import csv

import numpy as np
import librosa


# Definición de bandas de frecuencia estándar (en Hz)
BANDS = {
    "sub_bass": (20, 60),
    "bass": (60, 250),
    "low_mid": (250, 500),
    "mid": (500, 2000),
    "upper_mid": (2000, 4000),
    "treble": (4000, 8000),
    "high_treble": (8000, 20000),
}


def load_audio(path, sr=22050):
    """Carga el audio en mono a la frecuencia de muestreo indicada."""
    y, sr = librosa.load(path, sr=sr, mono=True)
    return y, sr


def compute_band_energy(y, sr, n_fft=2048, hop_length=512):
    """
    Calcula un espectrograma y agrupa la energía en las bandas definidas.
    Devuelve:
        times: array con el tiempo (segundos) de cada frame
        energies: dict {band_name: array de energía por frame}
    """
    # Espectrograma de magnitud
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop_length)

    energies = {}
    for name, (f_min, f_max) in BANDS.items():
        idx = np.where((freqs >= f_min) & (freqs < f_max))[0]
        if len(idx) == 0:
            energies[name] = np.zeros(S.shape[1])
        else:
            energies[name] = S[idx, :].sum(axis=0)

    return times, energies


def dominant_band_per_frame(energies):
    """Devuelve un array con el nombre de la banda dominante en cada frame."""
    names = list(energies.keys())
    matrix = np.stack([energies[n] for n in names], axis=0)  # (n_bands, n_frames)
    dominant_idx = np.argmax(matrix, axis=0)
    return [names[i] for i in dominant_idx]


def group_into_segments(times, labels, min_duration=0.0):
    """
    Convierte una secuencia de etiquetas por frame en segmentos (start, end, label).
    Fusiona frames consecutivos con la misma etiqueta.
    Descarta segmentos más cortos que min_duration (opcional).
    """
    segments = []
    start = times[0]
    current_label = labels[0]

    for i in range(1, len(labels)):
        if labels[i] != current_label:
            end = times[i]
            segments.append((start, end, current_label))
            start = times[i]
            current_label = labels[i]

    segments.append((start, times[-1], current_label))

    if min_duration > 0:
        segments = [s for s in segments if (s[1] - s[0]) >= min_duration]

    return segments


def format_time(seconds):
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:05.2f}"


def main():
    parser = argparse.ArgumentParser(description="Detects when each frequency band dominates in an audio file.")
    parser.add_argument("audio", help="Path to the audio file (mp3, wav, etc.)")
    parser.add_argument("--band", choices=list(BANDS.keys()), default=None,
                         help="If set, only shows segments where this band dominates.")
    parser.add_argument("--min-duration", type=float, default=0.15,
                         help="Minimum segment duration in seconds to report (default 0.15s).")
    parser.add_argument("--out", default=None, help="Output .csv path with detected segments.")
    args = parser.parse_args()

    print(f"Loading audio: {args.audio}")
    try:
        y, sr = load_audio(args.audio)
    except Exception as e:
        print(f"Error loading audio: {e}", file=sys.stderr)
        sys.exit(1)

    total_duration = len(y) / sr
    print(f"Total duration: {format_time(total_duration)} ({total_duration:.2f}s)")
    print("Analyzing spectrum by frequency band...\n")

    times, energies = compute_band_energy(y, sr)
    labels = dominant_band_per_frame(energies)
    segments = group_into_segments(times, labels, min_duration=args.min_duration)

    if args.band:
        segments = [s for s in segments if s[2] == args.band]
        print(f"Segments where band '{args.band}' dominates "
              f"({BANDS[args.band][0]}-{BANDS[args.band][1]} Hz):\n")
    else:
        print("Dominant band per time segment:\n")

    for start, end, label in segments:
        hz_range = BANDS[label]
        print(f"  {format_time(start)} - {format_time(end)}  ->  "
              f"{label} ({hz_range[0]}-{hz_range[1]} Hz)")

    if not segments:
        print("  (no segments found matching those criteria)")

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["start_s", "end_s", "band", "freq_min_hz", "freq_max_hz"])
            for start, end, label in segments:
                hz_range = BANDS[label]
                writer.writerow([f"{start:.3f}", f"{end:.3f}", label, hz_range[0], hz_range[1]])
        print(f"\nResults saved to: {args.out}")


if __name__ == "__main__":
    main()