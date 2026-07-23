#!/usr/bin/env python3
"""
video_cutter_v3.py
===================

Corta videos de acuerdo a los segmentos de banda de frecuencia detectados
por detect_bands.py. Solo realiza un corte si los segmentos consecutivos
de la banda objetivo suman la duración mínima configurada.
La suma total de los cortes debe ser igual a la duración del audio.

USO
---
    python3 video_cutter_v3.py video1.mkv video2.mkv \
        --audio song.mp3 --band bass --min-duration 1.8

    python3 video_cutter_v3.py video1.mkv \
        --audio song.mp3 --band bass --min-duration 2.0 --output cuts/

Requiere ffmpeg, ffprobe y las dependencias de detect_bands.py.
"""

import argparse
import csv
import random
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent


def run_cmd(cmd, desc=""):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {desc}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result


def run_detect_bands(audio_path, csv_path, band=None):
    cmd = [sys.executable, str(SCRIPT_DIR / "detect_bands.py"), str(audio_path), "--out", str(csv_path)]
    if band:
        cmd += ["--band", band]
    print(f"[INFO] Analizando audio con detect_bands...")
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"[ERROR] detect_bands falló", file=sys.stderr)
        sys.exit(1)
    print(f"[INFO] CSV generado: {csv_path}")


def read_csv_segments(csv_path):
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


def group_consecutive_segments(segments, target_band, min_duration):
    """Marca segmentos que pertenecen a un grupo válido (consecutivos de la misma banda >= min_duration)."""
    groups = []
    current_group = []

    for seg in segments:
        if seg["band"] == target_band:
            if not current_group:
                current_group.append(seg)
            else:
                if seg["start"] <= current_group[-1]["end"] + 0.1:
                    current_group.append(seg)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [seg]
        else:
            if current_group:
                groups.append(current_group)
                current_group = []

    if current_group:
        groups.append(current_group)

    valid_groups = []
    for group in groups:
        duration = group[-1]["end"] - group[0]["start"]
        if duration >= min_duration:
            valid_groups.append({
                "start": group[0]["start"],
                "end": group[-1]["end"],
                "duration": duration,
                "segments": len(group),
            })

    return valid_groups


def select_cuts_until_duration(segments, valid_groups, target_duration):
    """Selecciona cortes continuos sin gaps: desde cursor hasta final de grupo válido."""
    if not valid_groups:
        return [], 0.0

    selected = []
    cursor = 0.0

    for g in valid_groups:
        if cursor >= target_duration:
            break

        cut_end = min(g["end"], target_duration)
        if cut_end > cursor:
            selected.append({
                "start": cursor,
                "end": cut_end,
                "duration": cut_end - cursor,
            })
            cursor = cut_end

    # Corte final si aún no se alcanza la duración del audio
    if cursor < target_duration:
        selected.append({
            "start": cursor,
            "end": target_duration,
            "duration": target_duration - cursor,
        })

    total = sum(c["duration"] for c in selected)
    return selected, total


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
    parser = argparse.ArgumentParser(
        description="Corta videos según bandas de frecuencia detectadas."
    )
    parser.add_argument("videos", type=Path, nargs="+", help="Videos de entrada")
    parser.add_argument("--audio", type=Path, required=True, help="Audio a analizar")
    parser.add_argument("--band", default="bass", help="Banda de frecuencia objetivo (default: bass)")
    parser.add_argument("--min-duration", type=float, default=1.8,
                        help="Duración mínima del grupo de segmentos en segundos (default: 1.8)")
    parser.add_argument("--output", type=Path, default=None, help="Carpeta de salida")
    args = parser.parse_args()

    for v in args.videos:
        if not v.exists():
            sys.exit(f"[ERROR] No existe: {v}")

    if not args.audio.exists():
        sys.exit(f"[ERROR] No existe el audio: {args.audio}")

    output_dir = args.output or Path("cuts")
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_duration = get_audio_duration(args.audio)
    print(f"[INFO] Duración del audio: {audio_duration:.2f}s")

    with tempfile.TemporaryDirectory(prefix="cutter_v3_") as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "segments.csv"

        run_detect_bands(args.audio, csv_path, band=args.band)

        segments = read_csv_segments(csv_path)
        print(f"[INFO] {len(segments)} segmentos totales en CSV")

        groups = group_consecutive_segments(segments, args.band, args.min_duration)
        print(f"[INFO] {len(groups)} grupos de '{args.band}' con duración >= {args.min_duration}s")

        if not groups:
            sys.exit("[ERROR] No se encontraron grupos válidos.")

        selected, total_duration = select_cuts_until_duration(segments, groups, audio_duration)
        print(f"[INFO] {len(selected)} cortes seleccionados para igualar duración del audio")
        print(f"[INFO] Duración total de cortes: {total_duration:.2f}s")
        for s in selected:
            print(f"    {s['start']:.2f}s - {s['end']:.2f}s  ({s['duration']:.2f}s)")

        clips = []
        for v in args.videos:
            vdur = get_video_duration(v)
            for s in selected:
                if s["end"] <= vdur:
                    clips.append({"video": v, "start": s["start"], "end": s["end"]})
                elif s["start"] < vdur:
                    clips.append({"video": v, "start": s["start"], "end": vdur})

        print(f"[INFO] Extrayendo {len(clips)} clips...")
        for i, clip in enumerate(clips):
            out_path = output_dir / f"cut_{i+1:03d}.mp4"
            duration = clip["end"] - clip["start"]
            extract_clip(clip["video"], clip["start"], duration, out_path)
            print(f"    - Cut {i+1}/{len(clips)}: {clip['video'].name} {clip['start']:.2f}s -> {clip['end']:.2f}s  ->  {out_path}")

    print(f"\n[LISTO] {len(clips)} clips guardados en: {output_dir}")
    print(f"        Duración total: {total_duration:.2f}s (audio: {audio_duration:.2f}s)")


if __name__ == "__main__":
    main()
