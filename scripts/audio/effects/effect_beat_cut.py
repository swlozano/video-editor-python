"""
Editor de video sincronizado con música (beat-synced editing)
----------------------------------------------------------------
Detecta los beats de una canción y aplica automáticamente:
  - Efecto de "líneas" (detección de bordes tipo Canny) en cada beat
  - Un flash de color superpuesto en cada beat
  - Combina el video con el audio de la música al final

Requisitos:
    pip3 install moviepy opencv-python librosa numpy

Uso:
    Ajusta las variables en la sección CONFIG y ejecuta:
    python3 editor_beat_sync.py
"""

import cv2
import numpy as np
import librosa

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
)
from moviepy.video.fx import FadeOut


# ============================================================
# CONFIG — ajusta estas rutas y parámetros a tu proyecto
# ============================================================

VIDEO_PATH = "/Users/main/Descargas/v4.mp4"
AUDIO_PATH = "/Users/main/Downloads/Askate_shorts/audio/beatBox.wav"
OUTPUT_PATH = "/Users/main/Downloads/Askate_shorts/cuts/v2/v4_sync.mp4"

# Duración de cada efecto disparado en el beat (segundos)
DURACION_LINEAS = 0.08   # cuánto dura el efecto de bordes en cada beat
DURACION_FLASH = 0.08    # cuánto dura el flash en cada beat

# Color del flash (RGB)
COLOR_FLASH = (220, 20, 60)  # crimson
OPACIDAD_FLASH = 0.5

# Sensibilidad de detección de beats.
# Más alto = menos beats detectados (solo los golpes fuertes)
# Más bajo = más beats detectados (más sensible/ruidoso)
DELTA_ONSET = 0.3

# Umbral de Canny para el efecto de líneas
CANNY_MIN = 100
CANNY_MAX = 200

# Si quieres limitar el efecto solo a los primeros N segundos del video
# (útil para pruebas rápidas). Pon None para usar todo el video.
LIMITE_DURACION = None  # ej: 10.0


# ============================================================
# 1. DETECCIÓN DE BEATS
# ============================================================

def detectar_beats(audio_path, delta=DELTA_ONSET):
    """Devuelve una lista de tiempos (en segundos) donde caen los beats/onsets."""
    y, sr = librosa.load(audio_path)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, backtrack=True, delta=delta
    )
    onset_times = librosa.frames_to_time(onsets, sr=sr)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_valor = float(np.atleast_1d(tempo)[0])
    print(f"Tempo estimado: {tempo_valor:.1f} BPM")
    print(f"Beats/onsets detectados: {len(onset_times)}")

    return onset_times.tolist()


# ============================================================
# 2. EFECTO DE LÍNEAS (Canny edge detection)
# ============================================================

def efecto_lineas(frame):
    gris = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    bordes = cv2.Canny(gris, CANNY_MIN, CANNY_MAX)
    resultado = cv2.cvtColor(bordes, cv2.COLOR_GRAY2RGB)
    return resultado


def aplicar_efecto_lineas_en_beats(clip, beat_times, duracion=DURACION_LINEAS):
    """
    Corta el clip en mini-segmentos en cada beat y aplica el efecto de líneas
    justo en esa ventana corta, dejando el resto del video normal.
    """
    from moviepy import concatenate_videoclips

    duracion_total = clip.duration
    puntos_crudos = sorted(set(t for t in beat_times if 0 <= t < duracion_total))

    # Filtrar beats demasiado cercanos entre sí (menos de `duracion` de separación),
    # para evitar que dos ventanas de efecto se solapen o se invieran.
    puntos = []
    ultimo = -float("inf")
    for t in puntos_crudos:
        if t - ultimo >= duracion:
            puntos.append(t)
            ultimo = t

    # Construir lista de intervalos (inicio, fin, con_efecto)
    intervalos = []
    cursor = 0.0

    for t in puntos:
        if t < cursor:
            # de todas formas no debería pasar tras el filtro, pero por seguridad
            continue
        fin_efecto = min(t + duracion, duracion_total)
        if fin_efecto <= t:
            continue
        if t > cursor:
            intervalos.append((cursor, t, False))
        intervalos.append((t, fin_efecto, True))
        cursor = fin_efecto

    if cursor < duracion_total:
        intervalos.append((cursor, duracion_total, False))

    segmentos = []
    for inicio, fin, con_efecto in intervalos:
        if fin - inicio <= 0:
            continue
        sub = clip.subclipped(inicio, fin)
        if con_efecto:
            sub = sub.image_transform(efecto_lineas)
        segmentos.append(sub)

    return concatenate_videoclips(segmentos)


# ============================================================
# 3. FLASHES SUPERPUESTOS EN CADA BEAT
# ============================================================

def generar_flashes(clip, beat_times, duracion=DURACION_FLASH):
    duracion_total = clip.duration
    flashes = []
    for t in beat_times:
        if 0 <= t < duracion_total:
            f = (
                ColorClip(size=clip.size, color=COLOR_FLASH, duration=duracion)
                .with_start(t)
                .with_opacity(OPACIDAD_FLASH)
                .with_effects([FadeOut(duracion)])
            )
            flashes.append(f)
    return flashes


# ============================================================
# 4. PIPELINE PRINCIPAL
# ============================================================


def main():
    print("Cargando música...")
    audio_completo = AudioFileClip(AUDIO_PATH)
    print(f"[debug] duración de la música = {audio_completo.duration:.2f}")

    print("Cargando video...")
    clip = VideoFileClip(VIDEO_PATH)
    print(f"[debug] duración del video    = {clip.duration:.2f}")

    # El video puede ser más largo que la canción (ej: un clip de 35 min y
    # una canción de 1:15). Recortamos el video a la duración de la música,
    # que es lo que realmente vamos a exportar sincronizado.
    duracion_objetivo = min(clip.duration, audio_completo.duration)
    if LIMITE_DURACION:
        duracion_objetivo = min(duracion_objetivo, LIMITE_DURACION)

    print(f"[debug] duración objetivo (video recortado a la música) = {duracion_objetivo:.2f}")
    clip = clip.subclipped(0, duracion_objetivo)
    audio = audio_completo.subclipped(0, duracion_objetivo)

    print("Detectando beats en la música...")
    beat_times = detectar_beats(AUDIO_PATH, delta=DELTA_ONSET)
    # Solo usamos beats dentro de la duración del video
    beat_times = [t for t in beat_times if t < clip.duration]
    print(f"Beats dentro del rango del video: {len(beat_times)}")

    print("Aplicando efecto de líneas en cada beat...")
    clip_con_lineas = aplicar_efecto_lineas_en_beats(clip, beat_times)

    # Verificación de seguridad: la duración no debería crecer respecto al original
    if clip_con_lineas.duration > clip.duration + 0.5:
        raise RuntimeError(
            f"Duración inesperada tras aplicar efectos: {clip_con_lineas.duration:.2f}s "
            f"(el video original dura {clip.duration:.2f}s). Revisa DURACION_LINEAS o DELTA_ONSET."
        )

    print("Generando flashes en cada beat...")
    flashes = generar_flashes(clip_con_lineas, beat_times)

    print("Componiendo video final...")
    video_final = CompositeVideoClip([clip_con_lineas] + flashes)
    video_final = video_final.with_duration(duracion_objetivo)

    print("Agregando audio de la música...")
    video_final = video_final.with_audio(audio)

    print(f"Exportando a: {OUTPUT_PATH}")
    video_final.write_videofile(OUTPUT_PATH, fps=clip.fps)

    print("¡Listo!")


if __name__ == "__main__":
    main()