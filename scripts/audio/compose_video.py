#!/usr/bin/env python3
"""
compose_video.py
=================

Pipeline completo:
1. Analiza audio con detect_bands → CSV con segmentos
2. Selecciona N items aleatorios no próximos del CSV
3. Une clips con video_glue → video_base.mp4
4. Aplica boomerang con los rangos seleccionados → video_boomerang.mp4
5. Reemplaza audio con canción parametrizada → video_final.mp4

USO
---
    python3 compose_video.py \
        --audio song.mp3 \
        --clips clips/ \
        --song cancion.mp3 \
        --num-items 5 \
        --min-distance 2 \
        --keep-boomerang

Requiere ffmpeg, ffprobe y las dependencias de detect_bands.py.
"""

import argparse
import csv
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent


def run_cmd(cmd, desc=""):
    """Ejecuta un comando y maneja errores."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {desc}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result


def run_detect_bands(audio_path, csv_path, band=None):
    """Llama a detect_bands.py y genera el CSV de segmentos."""
    cmd = [sys.executable, str(SCRIPT_DIR / "detect_bands.py"), str(audio_path), "--out", str(csv_path)]
    if band:
        cmd += ["--band", band]
    print(f"[INFO] Analizando audio con detect_bands...")
    run_cmd(cmd, "detect_bands falló")
    print(f"[INFO] CSV generado: {csv_path}")


def read_csv_segments(csv_path):
    """Lee el CSV de detect_bands y devuelve lista de dicts."""
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


def select_random_items(segments, num_items, min_distance):
    """Selecciona N items aleatorios con distancia mínima entre ellos."""
    if num_items >= len(segments):
        print(f"[AVISO] Se pidieron {num_items} items pero solo hay {len(segments)} disponibles.")
        return segments

    shuffled = list(segments)
    random.shuffle(shuffled)

    selected = []
    for item in shuffled:
        if len(selected) >= num_items:
            break
        too_close = False
        for s in selected:
            if abs(item["start"] - s["start"]) < min_distance:
                too_close = True
                break
        if not too_close:
            selected.append(item)

    selected.sort(key=lambda x: x["start"])
    return selected


def get_video_duration(path):
    """Obtiene la duración del video en segundos."""
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


def run_video_glue(clips_dirs, output_path):
    """Llama a video_glue.py para unir clips."""
    cmd = [sys.executable, str(SCRIPT_DIR / "video_glue.py")]
    for d in clips_dirs:
        cmd.append(str(d))
    cmd += ["--output", str(output_path)]
    print(f"[INFO] Uniendo clips con video_glue...")
    run_cmd(cmd, "video_glue falló")
    print(f"[INFO] Video base generado: {output_path}")


def run_boomerang(video_path, ranges, output_path, loops=1, speed=1.0):
    """Llama a boomerang_video.py con los rangos seleccionados."""
    cmd = [sys.executable, str(SCRIPT_DIR / "boomerang_video.py"), str(video_path)]
    for r in ranges:
        cmd += ["--range", f"{r['start']:.3f}-{r['end']:.3f}"]
    cmd += ["--loops", str(loops), "--speed", str(speed), "-o", str(output_path)]
    print(f"[INFO] Aplicando boomerang con {len(ranges)} rangos, loops={loops}, speed={speed}x...")
    run_cmd(cmd, "boomerang_video falló")
    print(f"[INFO] Video boomerang generado: {output_path}")


def replace_audio(video_path, song_path, output_path):
    """Reemplaza el audio del video con la canción usando ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(song_path),
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ]
    print(f"[INFO] Reemplazando audio con {song_path.name}...")
    run_cmd(cmd, "ffmpeg falló reemplazando audio")
    print(f"[INFO] Audio reemplazado: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline: detect_bands → video_glue → boomerang → reemplazar audio."
    )
    parser.add_argument("--audio", type=Path, required=True,
                        help="Archivo de audio a analizar con detect_bands")
    parser.add_argument("--clips", type=Path, nargs="+", required=True,
                        help="Carpeta(s) con clips de video para video_glue")
    parser.add_argument("--song", type=Path, required=True,
                        help="Canción para reemplazar el audio final")
    parser.add_argument("--num-items", type=int, default=5,
                        help="Número de items aleatorios a seleccionar (default: 5)")
    parser.add_argument("--min-distance", type=float, default=2.0,
                        help="Distancia mínima en segundos entre items (default: 2)")
    parser.add_argument("--band", default=None,
                        help="Filtrar por banda específica (bass, mid, treble, etc)")
    parser.add_argument("--loops", type=int, default=1,
                        help="Loops para boomerang (default: 1)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Velocidad del boomerang (default: 1.0)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Video de salida (default: composed_final.mp4)")
    parser.add_argument("--keep-boomerang", action="store_true",
                        help="Guardar el video boomerang generado (default: no guardar)")
    args = parser.parse_args()
    print(args)

    # Validaciones
    if not args.audio.exists():
        sys.exit(f"[ERROR] No existe el archivo de audio: {args.audio}")
    for d in args.clips:
        if not d.is_dir():
            sys.exit(f"[ERROR] No existe la carpeta de clips: {d}")
    if not args.song.exists():
        sys.exit(f"[ERROR] No existe la canción: {args.song}")

    output_path = args.output or Path("composed_final.mp4")

    # Ruta para guardar el boomerang si se pide
    boomerang_out = None
    if args.keep_boomerang:
        boomerang_out = output_path.parent / f"{output_path.stem}_boomerang.mp4"

    with tempfile.TemporaryDirectory(prefix="compose_") as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "segments.csv"
        video_base = tmpdir / "video_base.mp4"
        video_boomerang = tmpdir / "video_boomerang.mp4"

        # Paso 1: detect_bands
        run_detect_bands(args.audio, csv_path, band=args.band)

        # Paso 2: Leer CSV y seleccionar items
        segments = read_csv_segments(csv_path)
        print(f"[INFO] {len(segments)} segmentos en el CSV")
        selected = select_random_items(segments, args.num_items, args.min_distance)
        print(f"[INFO] {len(selected)} items seleccionados:")
        for s in selected:
            print(f"    {s['start']:.2f}s - {s['end']:.2f}s  ({s['band']})")

        # Paso 3: video_glue
        run_video_glue(args.clips, video_base)

        # Paso 4: Filtrar rangos que excedan la duración del video
        video_duration = get_video_duration(video_base)
        print(f"[INFO] Duración del video base: {video_duration:.2f}s")
        filtered = [s for s in selected if s["start"] < video_duration]
        if len(filtered) < len(selected):
            print(f"[AVISO] {len(selected) - len(filtered)} rangos descartados (exceden duración del video)")
        if not filtered:
            sys.exit("[ERROR] Ningún rango es válido para la duración del video.")
        selected = filtered

        # Paso 5: boomerang
        run_boomerang(video_base, selected, video_boomerang, loops=args.loops, speed=args.speed)

        # Guardar boomerang si se pide
        if boomerang_out:
            import shutil
            shutil.copy2(str(video_boomerang), str(boomerang_out))
            print(f"[INFO] Boomerang guardado: {boomerang_out}")

        # Paso 6: reemplazar audio
        replace_audio(video_boomerang, args.song, output_path)

    print(f"\n[LISTO] Video final: {output_path}")


if __name__ == "__main__":
    main()
