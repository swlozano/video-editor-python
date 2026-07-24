#!/usr/bin/env python3
"""
video_cutter_v4.py
===================

Analiza un archivo de audio con detect_bands.py y genera clips de video
basados en los segmentos de banda de frecuencia detectados.

USO
---
    python3 video_cutter_v4.py --audio song.mp3 --video video.mkv --band bass
    python3 video_cutter_v4.py --audio song.mp3 --video video.mkv --band bass --output clips/
"""

import argparse
import csv
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


def select_segments(segments, target_band, min_duration, audio_duration):
    """Selecciona segmentos acumulativos de la banda objetivo."""
    selected = []
    used_indices = set()
    segment = min_duration

    while segment < audio_duration:
        found = False
        for i, seg in enumerate(segments):
            if i not in used_indices and seg["band"] == target_band and seg["end"] >= segment:
                selected.append(seg)
                used_indices.add(i)
                segment += min_duration
                found = True
                break
        if not found:
            break

    return selected


def generate_cuts(segments):
    """Genera cortes continuos desde 0 hasta el final de cada segmento."""
    cuts = []
    cursor = 0.0

    for seg in segments:
        if seg["end"] > cursor:
            cuts.append({
                "start": cursor,
                "end": seg["end"],
                "duration": seg["end"] - cursor,
            })
            cursor = seg["end"]

    return cuts


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
    parser = argparse.ArgumentParser(description="Genera clips de video según bandas de frecuencia.")
    parser.add_argument("--audio", type=Path, required=True, help="Audio a analizar")
    parser.add_argument("--video", type=Path, required=True, help="Video de entrada")
    parser.add_argument("--band", default="bass", help="Banda de frecuencia objetivo (default: bass)")
    parser.add_argument("--min-duration", type=float, default=1.8,
                        help="Duración mínima acumulativa en segundos (default: 1.8)")
    parser.add_argument("--output", type=Path, default=None, help="Carpeta de salida")
    args = parser.parse_args()

    if not args.audio.exists():
        sys.exit(f"[ERROR] No existe el audio: {args.audio}")
    if not args.video.exists():
        sys.exit(f"[ERROR] No existe el video: {args.video}")

    output_dir = args.output or Path("cuts_v4")
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_duration = get_audio_duration(args.audio)
    video_duration = get_video_duration(args.video)
    print(f"[INFO] Duración del audio: {audio_duration:.2f}s")
    print(f"[INFO] Duración del video: {video_duration:.2f}s")
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
            return

        for i, seg in enumerate(selected):
            dur = seg["end"] - seg["start"]
            print(f"  [{i+1}] {seg['start']:.3f}s - {seg['end']:.3f}s  ({dur:.3f}s)")

        total = sum(seg["end"] - seg["start"] for seg in selected)
        print(f"\n  Total: {len(selected)} segmentos, {total:.3f}s")

        print(f"\n{'='*60}")
        print(f"CORTES GENERADOS")
        print(f"{'='*60}\n")

        cuts = generate_cuts(selected)
        for i, cut in enumerate(cuts):
            print(f"  Corte {i+1}: {cut['start']:.3f}s - {cut['end']:.3f}s  ({cut['duration']:.3f}s)")

        total_cuts = sum(c["duration"] for c in cuts)
        print(f"\n  Total cortes: {len(cuts)}, {total_cuts:.3f}s")

        print(f"\n{'='*60}")
        print(f"EXTRAYENDO CLIPS DEL VIDEO")
        print(f"{'='*60}\n")

        for i, cut in enumerate(cuts):
            if cut["end"] > video_duration:
                print(f"  [AVISO] Corte {i+1} excede duración del video, se trunca")
                cut["end"] = video_duration
                cut["duration"] = cut["end"] - cut["start"]

            out_path = output_dir / f"clip_{i+1:03d}.mp4"
            extract_clip(args.video, cut["start"], cut["duration"], out_path)
            print(f"  Clip {i+1}/{len(cuts)}: {cut['start']:.3f}s -> {cut['end']:.3f}s  ->  {out_path}")

    print(f"\n[LISTO] {len(cuts)} clips guardados en: {output_dir}")


if __name__ == "__main__":
    main()
