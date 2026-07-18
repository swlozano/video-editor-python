from moviepy import VideoFileClip, concatenate_videoclips

# ==========================
# CONFIGURACIÓN
# ==========================

VIDEO_PATH = "proyects/test/video/short.mp4"
OUTPUT_PATH = "proyects/test/out/video_cortado.mp4"

# ==========================
# FUNCIÓN AUXILIAR
# ==========================

def t(minuto, segundo):
    """Convierte (minuto, segundo) a segundos."""
    return minuto * 60 + segundo


# ==========================
# SEGMENTOS A EXTRAER
# Formato:
# (inicio, fin)
# donde inicio y fin son t(minuto, segundo)
# ==========================

segmentos = [
    (t(4, 6),  t(4, 16)),   # 00:05 -> 00:10

]

# ==========================
# CARGAR VIDEO
# ==========================

video = VideoFileClip(VIDEO_PATH)

clips = []

for inicio, fin in segmentos:

    # Evita tiempos fuera del video
    inicio = max(0, inicio)
    fin = min(fin, video.duration)

    if fin <= inicio:
        print(f"Segmento inválido: {inicio} - {fin}")
        continue

    print(f"Extrayendo: {inicio:.2f}s -> {fin:.2f}s")

    clip = video.subclipped(inicio, fin)
    clips.append(clip)

# ==========================
# UNIR Y EXPORTAR
# ==========================

if len(clips) == 0:
    raise Exception("No se generó ningún clip.")

resultado = concatenate_videoclips(clips, method="compose")

resultado.write_videofile(
    OUTPUT_PATH,
    codec="libx264",
    audio_codec="aac",
    fps=video.fps
)

video.close()
resultado.close()

print("✅ Video generado correctamente.")