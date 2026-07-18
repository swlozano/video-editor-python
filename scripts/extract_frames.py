#!/usr/bin/env python3
"""
Extrae frames de un video dentro de un rango específico.

Ejemplos de uso:
    # Por número de frame (del frame 100 al 500, cada 5 frames)
    python extraer_frames.py video.mp4 --start 100 --end 500 --step 5

    # Por tiempo en segundos (del segundo 10 al 20)
    python extraer_frames.py video.mp4 --start-time 10 --end-time 20

    # Por tiempo en formato HH:MM:SS
    python extraer_frames.py video.mp4 --start-time 00:00:10 --end-time 00:01:30

    # Extraer todos los frames de todo el video
    python extraer_frames.py video.mp4
"""

import cv2
import os
import argparse


def tiempo_a_segundos(tiempo_str):
    """Convierte 'HH:MM:SS', 'MM:SS' o segundos sueltos a segundos (float)."""
    if tiempo_str is None:
        return None
    partes = str(tiempo_str).split(":")
    partes = [float(p) for p in partes]
    if len(partes) == 1:
        return partes[0]
    elif len(partes) == 2:
        m, s = partes
        return m * 60 + s
    elif len(partes) == 3:
        h, m, s = partes
        return h * 3600 + m * 60 + s
    else:
        raise ValueError(f"Formato de tiempo inválido: {tiempo_str}")


def extraer_frames(video_path, output_dir, start_frame=None, end_frame=None,
                    start_time=None, end_time=None, step=1, step_time=None,
                    frames_por_segundo=None, prefijo="frame"):
    """
    step: intervalo entre frames guardados, en NÚMERO DE FRAMES (step=5 -> 1 de cada 5 frames)
    step_time: intervalo entre frames guardados, en SEGUNDOS (step_time=2 -> 1 frame cada 2 segundos)
    frames_por_segundo: cuántos frames guardar DENTRO de cada segundo (frames_por_segundo=5 -> 5 frames por segundo)
    Prioridad si se combinan: frames_por_segundo > step_time > step
    """

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: no se pudo abrir el video '{video_path}'")
        return {"exito": False, "error": "No se pudo abrir el video", "rutas": []}

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Si se dan tiempos, convertirlos a número de frame
    if start_time is not None:
        start_frame = int(tiempo_a_segundos(start_time) * fps)
    if end_time is not None:
        end_frame = int(tiempo_a_segundos(end_time) * fps)

    # frames_por_segundo tiene la máxima prioridad: cuántos frames extraer por cada segundo real
    if frames_por_segundo is not None:
        step = max(1, round(fps / frames_por_segundo))
    # step_time: 1 frame cada N segundos
    elif step_time is not None:
        step = max(1, round(step_time * fps))

    # Valores por defecto: todo el video
    start_frame = max(0, start_frame if start_frame is not None else 0)
    end_frame = min(total_frames - 1, end_frame if end_frame is not None else total_frames - 1)

    if start_frame > end_frame:
        print("Error: el frame/tiempo de inicio es mayor que el de fin")
        return {"exito": False, "error": "Rango inválido", "rutas": []}

    print(f"Video: {video_path}")
    print(f"FPS: {fps:.2f} | Total frames: {total_frames}")
    print(f"Extrayendo frames {start_frame} a {end_frame} (cada {step} frame/s)...")

    # Saltar directamente al frame de inicio (más rápido que leer uno por uno)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_num = start_frame
    guardados = 0
    rutas_guardadas = []

    while frame_num <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        if (frame_num - start_frame) % step == 0:
            nombre = os.path.join(output_dir, f"{prefijo}_{frame_num:06d}.jpg")
            cv2.imwrite(nombre, frame)
            rutas_guardadas.append(nombre)
            guardados += 1

        frame_num += 1

    cap.release()
    print(f"Listo. Se guardaron {guardados} frames en '{output_dir}'")

    # Esto es lo que se puede usar cuando se importa la función
    return {
        "exito": True,
        "fps": fps,
        "total_frames_video": total_frames,
        "frames_guardados": guardados,
        "rango": (start_frame, end_frame),
        "rutas": rutas_guardadas,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extrae frames de un video dentro de un rango específico.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("video", help="Ruta al archivo de video")
    parser.add_argument("-o", "--output", default="frames_output",
                         help="Carpeta de salida (default: frames_output)")

    # Rango por número de frame
    parser.add_argument("--start", type=int, default=None,
                         help="Número de frame inicial")
    parser.add_argument("--end", type=int, default=None,
                         help="Número de frame final")

    # Rango por tiempo (alternativa a --start/--end)
    parser.add_argument("--start-time", type=str, default=None,
                         help="Tiempo inicial (segundos o HH:MM:SS)")
    parser.add_argument("--end-time", type=str, default=None,
                         help="Tiempo final (segundos o HH:MM:SS)")

    parser.add_argument("--step", type=int, default=1,
                         help="Guardar 1 de cada N frames (default: 1, todos)")
    parser.add_argument("--step-time", type=float, default=None,
                         help="Guardar 1 frame cada N segundos (prioridad sobre --step)")
    parser.add_argument("--frames-por-segundo", type=float, default=None,
                         help="Guardar N frames dentro de cada segundo (máxima prioridad)")
    parser.add_argument("--prefijo", type=str, default="frame",
                         help="Prefijo para el nombre de archivo (default: frame)")

    args = parser.parse_args()

    extraer_frames(
        video_path=args.video,
        output_dir=args.output,
        start_frame=args.start,
        end_frame=args.end,
        start_time=args.start_time,
        end_time=args.end_time,
        step=args.step,
        step_time=args.step_time,
        frames_por_segundo=args.frames_por_segundo,
        prefijo=args.prefijo,
    )


if __name__ == "__main__":
    main()