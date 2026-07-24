#!/bin/bash

# ===========================================
# detect_bands.py
#
# Uso:
# python3 detect_bands.py <audio> [opciones]
#
# Argumentos:
#   <audio>               Ruta al archivo de audio (.mp3, .wav, etc.)
#
# Opciones:
#   --band <nombre>       Mostrar únicamente los segmentos donde
#                         domina esa banda de frecuencia.
#
#   --min-duration <seg>  Duración mínima del segmento en segundos.
#                         Valor por defecto: 0.15
#
#   --out <archivo.csv>   Ruta del archivo CSV de salida.
# ===========================================

"""
python3 /Users/main/Dev/Python/video-editor/scripts/audio/detect_bands.py \
    /Users/main/Downloads/Askate_shorts/audio/beatBox.wav \
    --band mid \
    --min-duration 0 \
    --out /Users/main/Downloads/Askate_shorts/out/resultado.csv
"""

python3 /Users/main/Dev/Python/video-editor/scripts/audio/detect_bands.py \
    /Users/main/Downloads/Askate_shorts/audio/beat.mp3 \
    --min-duration 0 \
    --out /Users/main/Downloads/Askate_shorts/out/resultado.csv