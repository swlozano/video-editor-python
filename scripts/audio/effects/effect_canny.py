from moviepy import VideoFileClip
import cv2
import numpy as np

"""
Sí, eso es un efecto de detección de bordes (edge detection) — el fondo se vuelve negro y solo se ven las líneas/contornos de la imagen en blanco. Se logra con OpenCV usando el algoritmo de Canny, y se integra en MoviePy procesando frame por frame.
"""

def efecto_lineas(frame):
    # Convertir a escala de grises
    gris = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    
    # Detección de bordes (Canny)
    bordes = cv2.Canny(gris, threshold1=100, threshold2=200)
    
    # Convertir de vuelta a RGB (para que MoviePy lo acepte)
    resultado = cv2.cvtColor(bordes, cv2.COLOR_GRAY2RGB)
    
    return resultado

"""
clip = VideoFileClip("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_011.mp4")
clip_lineas = clip.image_transform(efecto_lineas)
clip_lineas.write_videofile("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_e_011.mp4")
"""

inicio, fin = 1.6, 1.7  # segundos

clip = VideoFileClip("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_046.mp4")

parte_normal_1 = clip.subclipped(0, inicio)
parte_efecto = clip.subclipped(inicio, fin).image_transform(efecto_lineas)
parte_normal_2 = clip.subclipped(fin, clip.duration)

from moviepy import concatenate_videoclips
final = concatenate_videoclips([parte_normal_1, parte_efecto, parte_normal_2])
final.write_videofile("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_e_046.mp4")