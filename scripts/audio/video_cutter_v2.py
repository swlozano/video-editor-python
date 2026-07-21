#!/usr/bin/env python3
"""
video_cutter_v2.py
===================

Genera clips aleatorios a partir de uno o más archivos de video (.mkv),
especificando la duración de cada clip y la duración total deseada.
Cada clip se guarda por separado en una carpeta de salida.

USO
---
    python3 video_cutter_v2.py entrada.mkv

    python3 video_cutter_v2.py video1.mkv video2.mkv --clip-duration 5 --total-duration 30

Requiere ffmpeg y ffprobe instalados y accesibles en el PATH.
"""

import argparse
import random
import subprocess
import sys
from pathlib import Path


def get_video_duration(path: Path) -> float:
    """Devuelve la duración total del video en segundos usando ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"[ERROR] No se pudo leer la duración del video: {result.stderr}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        sys.exit(f"[ERROR] ffprobe devolvió una duración inválida: {result.stdout!r}")


def extract_clip(input_path: Path, start: float, duration: float, output_path: Path) -> None:
    """Extrae un fragmento del video original."""
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
    if result.returncode != 0:
        sys.exit(f"[ERROR] ffmpeg falló extrayendo el clip {start:.3f}s: {result.stderr}")


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def find_random_fragment(video_duration, clip_duration, avoid_intervals, max_tries=500):
    """Busca un fragmento aleatorio que no se solape con los intervalos ya usados."""
    if clip_duration >= video_duration:
        sys.exit("[ERROR] La duración del clip es mayor o igual a la del video original.")

    max_start = video_duration - clip_duration
    for _ in range(max_tries):
        start = random.uniform(0, max_start)
        end = start + clip_duration
        if not any(overlaps(start, end, a, b) for a, b in avoid_intervals):
            return round(start, 2), round(end, 2)

    sys.exit("[ERROR] No se encontró un fragmento libre sin solaparse con los ya usados.")


def main():
    parser = argparse.ArgumentParser(
        description="Genera clips aleatorios a partir de un video .mkv."
    )
    parser.add_argument("inputs", type=Path, nargs="+", help="Video(s) de entrada (.mkv)")
    parser.add_argument("--clip-duration", type=float, default=5,
                        help="Duración de cada clip en segundos (default: 5)")
    parser.add_argument("--total-duration", type=float, default=30,
                        help="Duración total deseada de todos los clips en segundos (default: 30)")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Carpeta de salida (default: clips/)")
    args = parser.parse_args()

    input_paths = []
    for p in args.inputs:
        if not p.exists():
            sys.exit(f"[ERROR] No existe el archivo de entrada: {p}")
        input_paths.append(p)

    if args.clip_duration <= 0 or args.total_duration <= 0:
        sys.exit("[ERROR] --clip-duration y --total-duration deben ser mayores a 0.")

    n_clips = int(args.total_duration // args.clip_duration)
    if n_clips < 1:
        sys.exit("[ERROR] --clip-duration es mayor que --total-duration.")
    real_total = n_clips * args.clip_duration
    if real_total != args.total_duration:
        print(f"[AVISO] {args.total_duration}s no es múltiplo exacto de {args.clip_duration}s. "
              f"Se generarán {n_clips} clips = {real_total}s de duración total.")

    # Obtener duración de cada video
    videos = []
    for p in input_paths:
        dur = get_video_duration(p)
        print(f"[INFO] {p.name}: {dur:.2f}s")
        videos.append((p, dur))

    if args.clip_duration > min(dur for _, dur in videos):
        sys.exit("[ERROR] --clip-duration es mayor que la duración del video más corto.")

    output_dir = args.output_dir or Path("clips")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generar fragmentos aleatorios sin repetición (pueden venir de distintos videos)
    used = []  # [(video_index, start, end), ...]
    fragments = []  # [(video_path, start, end), ...]
    for i in range(n_clips):
        found = False
        indices = list(range(len(videos)))
        random.shuffle(indices)
        for vi in indices:
            vpath, vdur = videos[vi]
            try:
                frag = find_random_fragment(vdur, args.clip_duration,
                                            [(a, b) for ai, a, b in used if ai == vi])
                fragments.append((vpath, frag[0], frag[1]))
                used.append((vi, frag[0], frag[1]))
                found = True
                break
            except SystemExit:
                continue
        if not found:
            sys.exit("[ERROR] No se encontraron fragmentos libres en ningún video.")

    # Extraer cada clip
    print(f"[INFO] Extrayendo {n_clips} clips de {args.clip_duration}s cada uno...")
    for i, (vpath, s, e) in enumerate(fragments):
        clip_path = output_dir / f"clip_{i+1:03d}.mp4"
        extract_clip(vpath, s, e - s, clip_path)
        print(f"    - Clip {i+1}/{n_clips}: {vpath.name} {s:.2f}s -> {e:.2f}s  ->  {clip_path}")

    print(f"\n[LISTO] {n_clips} clips guardados en: {output_dir}")
    print(f"        Duración total: {real_total}s")


if __name__ == "__main__":
    main()
