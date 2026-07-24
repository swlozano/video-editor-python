#!/usr/bin/env python3
"""
super_cutter.py
================

Corta un video en segmentos de tiempo especificados.

USO
---
    python3 super_cutter.py video.mkv --ranges 0-5 10-15 20-25
    python3 super_cutter.py video.mkv --ranges 0-5 10-15 --output cuts/
    python3 super_cutter.py video.mkv --ranges 00:00-00:05 00:10-00:15
"""

import argparse
import subprocess
import sys
from pathlib import Path


def parse_time(time_str):
    """Parsea tiempo en segundos (5.5) o formato mm:ss / hh:mm:ss."""
    if ":" in time_str:
        parts = [float(p) for p in time_str.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        h, m, s = parts
        return h * 3600 + m * 60 + s
    return float(time_str)


def parse_range(range_str):
    """Parsea un rango 'start-end' y devuelve (start, end)."""
    if "-" not in range_str:
        print(f"[ERROR] Rango inválido: {range_str}. Formato: start-end", file=sys.stderr)
        sys.exit(1)
    start_str, end_str = range_str.rsplit("-", 1)
    return parse_time(start_str), parse_time(end_str)


def get_video_duration(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def extract_clip(input_path, start, duration, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", str(input_path),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Corta un video en segmentos de tiempo.")
    parser.add_argument("video", type=Path, help="Video de entrada")
    parser.add_argument("--ranges", nargs="+", required=True,
                        help="Rangos de tiempo: start-end (ej: 0-5, 10-15)")
    parser.add_argument("--output", type=Path, default=None, help="Carpeta de salida")
    args = parser.parse_args()

    if not args.video.exists():
        sys.exit(f"[ERROR] No existe el video: {args.video}")

    output_dir = args.output or Path("super_cuts")
    output_dir.mkdir(parents=True, exist_ok=True)

    video_duration = get_video_duration(args.video)
    print(f"[INFO] Video: {args.video}")
    print(f"[INFO] Duración: {video_duration:.2f}s")
    print(f"[INFO] {len(args.ranges)} rangos a cortar\n")

    ranges = [parse_range(r) for r in args.ranges]

    for i, (start, end) in enumerate(ranges):
        if start >= end:
            print(f"[AVISO] Rango {i+1} inválido ({start:.2f}s >= {end:.2f}s), se omite")
            continue
        if start >= video_duration:
            print(f"[AVISO] Rango {i+1} excede duración del video, se omite")
            continue
        if end > video_duration:
            print(f"[AVISO] Rango {i+1} truncado a {video_duration:.2f}s")
            end = video_duration

        duration = end - start
        out_path = output_dir / f"segment_{i+1:03d}.mp4"
        extract_clip(args.video, start, duration, out_path)
        print(f"  Segmento {i+1}: {start:.2f}s - {end:.2f}s ({duration:.2f}s) -> {out_path}")

    print(f"\n[LISTO] Segmentos guardados en: {output_dir}")


if __name__ == "__main__":
    main()
