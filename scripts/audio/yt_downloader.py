#!/usr/bin/env python3
"""
yt_downloader.py
=================

Descarga videos de YouTube usando yt-dlp con cookies del navegador Brave.

USO
---
    python3 yt_downloader.py "https://www.youtube.com/watch?v=..."

    python3 yt_downloader.py "https://www.youtube.com/watch?v=..." -o mi_video.mkv
"""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Descarga videos con yt-dlp usando cookies de Brave.")
    parser.add_argument("url", help="URL del video a descargar")
    parser.add_argument("-o", "--output", default=None, help="Nombre del archivo de salida")
    args = parser.parse_args()

    cmd = ["yt-dlp", "--cookies-from-browser", "brave", "--merge-output-format", "mkv"]
    if args.output:
        cmd += ["-o", args.output]
    cmd.append(args.url)

    print(f"[INFO] Descargando: {args.url}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        sys.exit(f"[ERROR] yt-dlp falló con código {result.returncode}")
    print("[LISTO] Descarga completada.")


if __name__ == "__main__":
    main()
