#!/usr/bin/env python3
"""
crazy_frame.py
===============

Toma un directorio con clips de video y extrae frames intercalándolos:
frame 1 de c1, frame 1 de c2, frame 1 de c3,
frame 2 de c1, frame 2 de c2, frame 2 de c3, etc.

Luego combina todos los frames en un solo video.

USO
---
    python3 crazy_frame.py clips/
    python3 crazy_frame.py clips/ --output crazy.mp4 --fps 24
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}


def run_cmd(cmd, desc=""):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {desc}: {result.stderr}", file=sys.stderr)
        return False
    return True


def get_frame_count(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-count_frames",
        "-show_entries", "stream=nb_read_frames",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0


def get_frame_rate(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        num, den = result.stdout.strip().split("/")
        return float(num) / float(den)
    except (ValueError, AttributeError):
        return 24.0


def extract_frame(video_path, frame_num, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"select=eq(n\\,{frame_num})",
        "-vframes", "1",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def create_video_from_frames(frames_dir, output_path, fps):
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%06d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    return run_cmd(cmd, "Error creando video desde frames")


def main():
    parser = argparse.ArgumentParser(
        description="Extrae frames intercalados de clips y crea un video crazy."
    )
    parser.add_argument("clips_dir", type=Path, help="Directorio con clips de video")
    parser.add_argument("--output", type=Path, default=None, help="Video de salida")
    parser.add_argument("--fps", type=int, default=24, help="FPS del video final (default: 24)")
    args = parser.parse_args()

    if not args.clips_dir.is_dir():
        sys.exit(f"[ERROR] No existe el directorio: {args.clips_dir}")

    clips = sorted([
        f for f in args.clips_dir.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ])

    if not clips:
        sys.exit("[ERROR] No se encontraron clips de video.")

    print(f"[INFO] {len(clips)} clips encontrados:")

    clip_data = []
    for clip in clips:
        fc = get_frame_count(clip)
        fr = get_frame_rate(clip)
        clip_data.append({"path": clip, "frames": fc, "fps": fr})
        print(f"    - {clip.name}: {fc} frames, {fr:.2f} fps")

    max_frames = max(c["frames"] for c in clip_data)
    print(f"\n[INFO] Máximo de frames por clip: {max_frames}")
    print(f"[INFO] Total de frames a extraer: {max_frames * len(clip_data)}")

    output_path = args.output or Path("crazy_frame_output.mp4")

    with tempfile.TemporaryDirectory(prefix="crazy_frame_") as tmpdir:
        tmpdir = Path(tmpdir)
        frame_idx = 0

        print(f"\n[INFO] Extrayendo frames intercalados...")
        for frame_num in range(max_frames):
            for i, clip in enumerate(clip_data):
                if frame_num < clip["frames"]:
                    frame_path = tmpdir / f"frame_{frame_idx:06d}.png"
                    extract_frame(clip["path"], frame_num, frame_path)
                    frame_idx += 1

            if (frame_num + 1) % 10 == 0:
                print(f"    - Procesados {(frame_num + 1) * len(clip_data)} frames...")

        print(f"[INFO] Total de frames extraídos: {frame_idx}")

        print(f"[INFO] Creando video final...")
        create_video_from_frames(tmpdir, output_path, args.fps)

    print(f"\n[LISTO] Video generado: {output_path}")
    print(f"        Frames: {frame_idx}, FPS: {args.fps}")


if __name__ == "__main__":
    main()
