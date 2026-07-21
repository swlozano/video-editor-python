#!/usr/bin/env python3
"""
video_glue.py
==============

Toma uno o más directorios que contienen videos, los une en orden aleatorio
y genera un solo video de salida.

USO
---
    python3 video_glue.py carpeta1/ carpeta2/

    python3 video_glue.py carpeta1/ carpeta2/ --duration 60

Requiere ffmpeg y ffprobe instalados y accesibles en el PATH.
"""

import argparse
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}


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
        print(f"[AVISO] No se pudo leer la duración de {path.name}, se omite.")
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        print(f"[AVISO] Duración inválida para {path.name}, se omite.")
        return 0.0


def normalize_clip(input_path: Path, output_path: Path) -> bool:
    """Re-codifica un clip a un códec común para poder concatenarlo."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[AVISO] No se pudo re-codificar {input_path.name}, se omite.")
        return False
    return True


def concat_videos(clip_paths, output_path: Path) -> None:
    """Concatena una lista de clips en un solo video."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        list_file = Path(f.name)
        for clip in clip_paths:
            safe_path = str(clip.resolve()).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        sys.exit(f"[ERROR] ffmpeg falló concatenando los videos: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(
        description="Une videos de varios directorios en orden aleatorio."
    )
    parser.add_argument("directories", type=Path, nargs="+",
                        help="Directorios que contienen videos")
    parser.add_argument("--extensions", nargs="+", default=None,
                        help="Extensiones de video a buscar (default: todas las comunes)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Duración máxima del video final en segundos (default: sin límite)")
    args = parser.parse_args()

    # Validar directorios
    for d in args.directories:
        if not d.is_dir():
            sys.exit(f"[ERROR] No existe el directorio: {d}")

    extensions = set(args.extensions) if args.extensions else VIDEO_EXTENSIONS

    # Buscar todos los videos en los directorios
    videos = []
    for d in args.directories:
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in extensions:
                videos.append(f)

    if not videos:
        sys.exit("[ERROR] No se encontraron videos en los directorios especificados.")

    print(f"[INFO] {len(videos)} videos encontrados:")
    for v in videos:
        print(f"    - {v.parent.name}/{v.name}")

    # Mezclar aleatoriamente
    random.shuffle(videos)

    # Si se especifica duración, limitar la cantidad de videos
    selected = []
    total_dur = 0.0
    for v in videos:
        if args.duration and total_dur >= args.duration:
            break
        dur = get_video_duration(v)
        if dur > 0:
            selected.append(v)
            total_dur += dur

    if not selected:
        sys.exit("[ERROR] No se pudieron seleccionar videos.")

    if args.duration:
        print(f"[INFO] Seleccionados {len(selected)} videos (~{total_dur:.2f}s) "
              f"para una duración objetivo de {args.duration}s")
    else:
        print(f"[INFO] Seleccionados {len(selected)} videos (~{total_dur:.2f}s)")

    output_path = Path("video_final.mp4")

    # Re-codificar cada video a un formato común en un directorio temporal
    tmp_dir = Path(tempfile.mkdtemp(prefix="video_glue_"))
    normalized = []
    try:
        print("[INFO] Re-codificando videos...")
        for i, v in enumerate(selected):
            out = tmp_dir / f"part_{i:03d}.mp4"
            print(f"    - {i+1}/{len(selected)}: {v.name}")
            if normalize_clip(v, out):
                normalized.append(out)

        if not normalized:
            sys.exit("[ERROR] Ningún video pudo ser procesado.")

        # Crear carpeta out/glue/{timestamp}/
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_dir = Path("out") / "glue" / timestamp
        out_dir.mkdir(parents=True, exist_ok=True)

        # Video temporero para recortar si es necesario
        temp_output = tmp_dir / "concat_raw.mp4"
        print(f"[INFO] Concatenando {len(normalized)} videos...")
        concat_videos(normalized, temp_output)

        # Si se pidió duración máxima, recortar
        if args.duration:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_output),
                "-t", f"{args.duration:.3f}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "128k",
                str(out_dir / output_path.name),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                sys.exit(f"[ERROR] ffmpeg falló al recortar: {result.stderr}")
        else:
            shutil.move(str(temp_output), str(out_dir / output_path.name))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Duración total
    total_dur = get_video_duration(output_path)
    print(f"\n[LISTO] Video generado: {output_path}")
    print(f"        Videos unidos: {len(normalized)}")
    print(f"        Duración total: {total_dur:.2f}s")


if __name__ == "__main__":
    main()
