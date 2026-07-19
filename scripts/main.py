import os
from extract_frames import extraer_frames

# Carpeta donde está main.py (scripts/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Subir un nivel para llegar a la raíz del proyecto (video-editor/)
PROJECT_ROOT = os.path.dirname(BASE_DIR)

video_path = os.path.join(PROJECT_ROOT, "proyects/test/video/v1.mp4")
output_dir = os.path.join(PROJECT_ROOT, "out/frame")

resultado = extraer_frames(
    video_path=video_path,
    output_dir=output_dir,
    start_time="00:08:45",
    end_time="00:08:54",
    frames_por_segundo=3
)

print(resultado)

if resultado["exito"]:
    print(resultado["frames_guardados"])
    print(resultado["rutas"])
    print(resultado["fps"])
else:
    print("Error:", resultado["error"])