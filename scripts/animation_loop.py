"""
Genera una animación en video a partir de un set de imágenes.

Lógica de los frames (circular, funciona con cualquier cantidad de imágenes):
    frame_1 = [imagen_1 (arriba), imagen_N (abajo)]
    frame_2 = [imagen_2 (arriba), imagen_1 (abajo)]
    frame_3 = [imagen_3 (arriba), imagen_2 (abajo)]
    ...
    frame_k = [imagen_k (arriba), imagen_{k-1} (abajo)]

Posicionamiento dentro de cada frame:
    - La imagen de ARRIBA se escala al ancho del fondo (conservando proporción)
      y su borde INFERIOR queda justo arriba de la mitad del fondo.
    - La imagen de ABAJO se escala al ancho del fondo (conservando proporción)
      y su borde SUPERIOR queda justo debajo de la mitad del fondo.

Luego todos los frames se unen en un video MP4, donde cada frame dura
un tiempo configurable (por defecto 0.5 segundos).
"""

from PIL import Image
import cv2
import numpy as np
import os
import glob


# ---------------------------------------------------------------------------
# Creación de fondo
# ---------------------------------------------------------------------------

def create_black_background(width, height):
    """Crea una imagen de fondo negro con el tamaño indicado."""
    return Image.new('RGB', (width, height), color=(0, 0, 0))


# ---------------------------------------------------------------------------
# Posicionamiento de imágenes
# ---------------------------------------------------------------------------

def _resize_to_width(image, target_width):
    """Redimensiona una imagen al ancho indicado, conservando su proporción."""
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    ratio = image.height / image.width
    new_height = int(target_width * ratio)
    return image.resize((target_width, new_height), Image.LANCZOS)


def paste_image_bottom_at_middle(background, image_path, x=None):
    """
    Pega una imagen (escalada al ancho del fondo) de modo que su borde
    INFERIOR quede justo en la mitad vertical del fondo (la imagen queda
    por encima de la línea media).
    """
    image = Image.open(image_path)
    resized = _resize_to_width(image, background.width)

    bg_height = background.height
    y = (bg_height // 2) - resized.height

    if x is None:
        x = (background.width - resized.width) // 2

    if background.mode != 'RGBA':
        background = background.convert('RGBA')

    background.paste(resized, (x, y), resized)
    return background


def paste_image_top_at_middle(background, image_path, x=None):
    """
    Pega una imagen (escalada al ancho del fondo) de modo que su borde
    SUPERIOR quede justo en la mitad vertical del fondo (la imagen queda
    por debajo de la línea media).
    """
    image = Image.open(image_path)
    resized = _resize_to_width(image, background.width)

    y = background.height // 2

    if x is None:
        x = (background.width - resized.width) // 2

    if background.mode != 'RGBA':
        background = background.convert('RGBA')

    background.paste(resized, (x, y), resized)
    return background


# ---------------------------------------------------------------------------
# Construcción de frames
# ---------------------------------------------------------------------------

def build_frame(width, height, top_image_path, bottom_image_path):
    """Crea un frame individual combinando una imagen arriba y otra abajo."""
    bg = create_black_background(width, height)
    bg = paste_image_bottom_at_middle(bg, top_image_path)
    bg = paste_image_top_at_middle(bg, bottom_image_path)
    return bg


def build_frames(image_paths, width, height):
    """
    Construye todos los frames a partir de una lista de imágenes,
    usando el emparejamiento circular:
        frame_k = (imagen_k, imagen_{k-1})
    Funciona para cualquier cantidad de imágenes (no solo 3).
    """
    n = len(image_paths)
    if n < 2:
        raise ValueError("Se necesitan al menos 2 imágenes para crear frames.")

    frames = []
    for k in range(n):
        top_image = image_paths[k]
        bottom_image = image_paths[k - 1]  # en Python, k-1 con k=0 -> -1 (última imagen, wrap-around)
        frame = build_frame(width, height, top_image, bottom_image)
        frames.append(frame)

    return frames


# ---------------------------------------------------------------------------
# Generación del video
# ---------------------------------------------------------------------------

def frames_to_video(frames, output_path, width, height, duration_per_frame=0.5, fps=30):
    """
    Une una lista de frames (PIL.Image) en un video MP4.

    Parámetros:
        frames (list[Image]): lista de frames en orden
        output_path (str): ruta del archivo de video de salida
        width, height (int): dimensiones del video
        duration_per_frame (float): segundos que dura cada frame en el video
        fps (int): cuadros por segundo del video de salida
    """
    repeats_per_frame = max(1, round(duration_per_frame * fps))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        frame_rgb = frame.convert('RGB')
        frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)
        for _ in range(repeats_per_frame):
            writer.write(frame_bgr)

    writer.release()
    print(f'Video guardado en: {output_path} '
          f'({len(frames)} frames x {duration_per_frame}s = {len(frames) * duration_per_frame}s total)')




def cargar_rutas_desde_carpeta(carpeta, extensiones=(".jpg", ".jpeg", ".png")):
    """
    Escanea una carpeta y devuelve todas las rutas de imágenes
    ordenadas alfabéticamente.
    """
    rutas = []
    for ext in extensiones:
        rutas.extend(glob.glob(os.path.join(carpeta, f"*{ext}")))
    return sorted(rutas)

# ---------------------------------------------------------------------------
# Ejemplo de uso
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # --- Parámetros configurables ---
    WIDTH = 1080
    HEIGHT = 1920
    DURATION_PER_FRAME = 0.1   # segundos que dura cada frame
    FPS = 30
    OUTPUT_VIDEO = 'animacion.mp4'

    # Lista de imágenes en orden (puede ser cualquier cantidad, no solo 3)
    image_paths = cargar_rutas_desde_carpeta("out/frame")
    print(image_paths)

    frames = build_frames(image_paths, WIDTH, HEIGHT)
    frames_to_video(frames, OUTPUT_VIDEO, WIDTH, HEIGHT, DURATION_PER_FRAME, FPS)