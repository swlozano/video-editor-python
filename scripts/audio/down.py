#!/usr/bin/env python3
"""
Script para descargar un video de YouTube usando yt-dlp
con las cookies del navegador Brave, calidad hasta 1080p
y fusión en formato MKV.
"""

import subprocess
import sys
import shutil

# --- Configuración ---
URL = "https://www.youtube.com/watch?v=cMgcaUtXMkw"
OUTPUT_TEMPLATE = "~/Descargas/%(title)s.%(ext)s"
BROWSER = "brave"
FORMATO = "bestvideo[height<=1080]+bestaudio"
MERGE_FORMAT = "mkv"


def main():
    # Verificar que yt-dlp está instalado
    if shutil.which("yt-dlp") is None:
        print("Error: yt-dlp no está instalado o no está en el PATH.")
        print("Instálalo con: pip install -U yt-dlp")
        sys.exit(1)

    comando = [
        "yt-dlp",
        "-o", OUTPUT_TEMPLATE,
        "--cookies-from-browser", BROWSER,
        "-f", FORMATO,
        "--merge-output-format", MERGE_FORMAT,
        URL,
    ]

    print("Ejecutando:", " ".join(comando))

    try:
        subprocess.run(comando, check=True)
        print("\n✅ Descarga completada correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ yt-dlp terminó con un error (código {e.returncode}).")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("\n❌ No se encontró el comando yt-dlp.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹ Descarga cancelada por el usuario.")
        sys.exit(130)


if __name__ == "__main__":
    main()