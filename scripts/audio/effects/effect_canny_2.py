from moviepy import VideoFileClip, concatenate_videoclips
import cv2

def efecto_lineas(frame):
    gris = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    bordes = cv2.Canny(gris, 100, 200)
    resultado = cv2.cvtColor(bordes, cv2.COLOR_GRAY2RGB)
    return resultado

inicio, fin = 0, 1  # segundos
titileo = 0.05  # duración de cada parpadeo

clip = VideoFileClip("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_046.mp4")

parte_normal_2 = clip.subclipped(fin, clip.duration)

# Generar los mini-cortes alternados entre normal y efecto
segmentos = []
t = inicio
i = 0
while t < fin:
    t_fin = min(t + titileo, fin)
    sub = clip.subclipped(t, t_fin)
    if i % 2 == 0:
        sub = sub.image_transform(efecto_lineas)  # con efecto
    # si i es impar, se queda normal (sin transform)
    segmentos.append(sub)
    t = t_fin
    i += 1

final = concatenate_videoclips(segmentos + [parte_normal_2])
final.write_videofile("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_e_046.mp4")