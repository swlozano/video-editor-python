#!/usr/bin/env python3
"""
video_cutter_v4.py
===================

Analiza un archivo de audio con detect_bands.py e imprime el CSV completo.
Selecciona segmentos acumulativos según duración mínima configurable.

USO
---
    python3 video_cutter_v4.py --audio song.mp3 --band bass --min-duration 1.8
"""

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent


def run_detect_bands(audio_path, csv_path):
    cmd = [sys.executable, str(SCRIPT_DIR / "detect_bands.py"), str(audio_path), "--out", str(csv_path)]
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        sys.exit("[ERROR] detect_bands falló")


def read_csv(csv_path):
    segments = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            segments.append({
                "start": float(row["start_s"]),
                "end": float(row["end_s"]),
                "band": row["band"],
            })
    return segments


def get_audio_duration(audio_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def select_segments(segments, target_band, min_duration, audio_duration):
    """Selecciona segmentos acumulativos de la banda objetivo."""
    selected = []
    target = min_duration

    for seg in segments:
        if target >= audio_duration:
            break

        duration = seg["end"] - seg["start"]
        if seg["band"] == target_band and duration >= min_duration:
            if seg["end"] >= target:
                selected.append(seg)
                target += min_duration

    return selected


def main():
    parser = argparse.ArgumentParser(description="Analiza audio y selecciona segmentos acumulativos.")
    parser.add_argument("--audio", type=Path, required=True, help="Audio a analizar")
    parser.add_argument("--band", default="bass", help="Banda de frecuencia objetivo (default: bass)")
    parser.add_argument("--min-duration", type=float, default=1.8,
                        help="Duración mínima acumulativa en segundos (default: 1.8)")
    args = parser.parse_args()

    if not args.audio.exists():
        sys.exit(f"[ERROR] No existe el audio: {args.audio}")

    audio_duration = get_audio_duration(args.audio)
    print(f"[INFO] Duración del audio: {audio_duration:.2f}s")
    print(f"[INFO] Buscando segmentos de '{args.band}' >= {args.min_duration}s\n")

    with tempfile.TemporaryDirectory(prefix="cutter_v4_") as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "segments.csv"

        run_detect_bands(args.audio, csv_path)
        segments = read_csv(csv_path)

        print(f"{'='*60}")
        print(f"CSV COMPLETO ({len(segments)} segmentos)")
        print(f"{'='*60}\n")

        for seg in segments:
            dur = seg["end"] - seg["start"]
            print(f"  {seg['start']:.3f},{seg['end']:.3f},{seg['band']},{dur:.3f}s")

        print(f"\n{'='*60}")
        print(f"SEGMENTOS SELECCIONADOS (banda: {args.band}, min: {args.min_duration}s)")
        print(f"{'='*60}\n")

        selected = select_segments(segments, args.band, args.min_duration, audio_duration)

        if not selected:
            print("  (ningún segmento cumple el criterio)")
        else:
            for i, seg in enumerate(selected):
                dur = seg["end"] - seg["start"]
                print(f"  [{i+1}] {seg['start']:.3f}s - {seg['end']:.3f}s  ({dur:.3f}s)")

            total = sum(seg["end"] - seg["start"] for seg in selected)
            print(f"\n  Total: {len(selected)} segmentos, {total:.3f}s")


if __name__ == "__main__":
    main()
