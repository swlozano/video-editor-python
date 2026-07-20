#!/usr/bin/env python3
"""
boomerang_video.py

Toma un video y una o más secciones de tiempo, y reemplaza cada una por un
efecto "boomerang" (la sección se reproduce hacia adelante y luego hacia
atrás, pudiendo repetirse el ciclo N veces y a una velocidad configurable).
El resto del video queda igual.

Requiere: ffmpeg y ffprobe instalados y accesibles en el PATH.

Formato de cada --range:
    start-end                  -> usa --loops y --speed por defecto
    start-end@loops            -> loops propio, speed por defecto
    start-end@loops@speed      -> loops y speed propios
    start-end@@speed           -> speed propio, loops por defecto (nota el @@)

start y end aceptan segundos ('5.5') o hh:mm:ss / mm:ss ('00:05', '1:02:03').
speed es un multiplicador: 2 = el doble de rápido, 0.5 = mitad de velocidad.

Ejemplos:
    python boomerang_video.py input.mp4 --range 5-8 -o output.mp4

    python boomerang_video.py input.mp4 --range 00:05-00:08 -o output.mp4

    python boomerang_video.py input.mp4 --range 5-8 --range 20-22 -o output.mp4

    python boomerang_video.py input.mp4 --range 5-8@1 --range 20-22@3 -o output.mp4

    # Todo el boomerang al doble de velocidad
    python boomerang_video.py input.mp4 --range 5-8 --range 20-22 --speed 2 -o output.mp4

    # Loops y velocidad distintos por sección
    python boomerang_video.py input.mp4 --range 5-8@2@2.5 --range 20-22@1@1.5 -o output.mp4
"""

import argparse
import os
import subprocess
import sys
import tempfile


def run(cmd):
    """Ejecuta un comando y lanza error legible si falla."""
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("Error ejecutando:", " ".join(cmd), file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result


def parse_time(value):
    """Acepta segundos ('5.5') o formato hh:mm:ss / mm:ss y devuelve segundos (float)."""
    if ":" not in value:
        return float(value)
    parts = [float(p) for p in value.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def parse_range(raw, default_loops, default_speed):
    """
    Parsea un string de rango: 'start-end', 'start-end@loops',
    'start-end@loops@speed' o 'start-end@@speed'.
    Se usa '@' (en vez de ':') para loops/speed para no chocar con los ':'
    de los formatos de tiempo hh:mm:ss.
    """
    loops = default_loops
    speed = default_speed

    text = raw
    if "@" in text:
        segments = text.split("@")
        text = segments[0]
        meta = segments[1:]
        if len(meta) >= 1 and meta[0] != "":
            try:
                loops = int(meta[0])
            except ValueError:
                raise ValueError(f"loops inválido en '{raw}': '{meta[0]}'")
        if len(meta) >= 2 and meta[1] != "":
            try:
                speed = float(meta[1])
            except ValueError:
                raise ValueError(f"speed inválido en '{raw}': '{meta[1]}'")

    if "-" not in text:
        raise ValueError(f"Rango inválido: '{raw}'. Formato esperado: start-end[@loops[@speed]]")

    start_str, end_str = text.rsplit("-", 1)
    start = parse_time(start_str)
    end = parse_time(end_str)

    if loops < 1:
        raise ValueError(f"loops debe ser >= 1 en el rango '{raw}'")
    if speed <= 0:
        raise ValueError(f"speed debe ser > 0 en el rango '{raw}'")
    if end <= start:
        raise ValueError(f"El fin debe ser mayor al inicio en el rango '{raw}'")

    return start, end, loops, speed


def get_duration(path):
    """Obtiene la duración total del video en segundos usando ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    result = run(cmd)
    return float(result.stdout.strip())


def get_frame_rate(path):
    """Obtiene el frame rate del video (ej. 25.0, 29.97) usando ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    result = run(cmd)
    num, den = result.stdout.strip().split("/")
    return float(num) / float(den)


def count_frames(path):
    """Cuenta los frames de video de un archivo."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v", "-count_frames",
        "-show_entries", "stream=nb_read_frames", "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    result = run(cmd)
    return int(result.stdout.strip())


def trim_last_frame(input_path, output_path, has_audio, frame_rate):
    """
    Recorta el último frame de un clip. Se usa para el tramo 'reversa' cuando
    hay más de un loop: el último frame de la reversa es idéntico al primer
    frame del siguiente ciclo, y sin recortarlo se ve otro frame duplicado /
    congelamiento en cada empalme entre loops.
    """
    n = count_frames(input_path)
    if n <= 1:
        run(["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path])
        return
    duration = get_duration(input_path)
    end_time = max(duration - (1.0 / frame_rate), 0.0)
    cmd = ["ffmpeg", "-y", "-i", input_path,
           "-vf", f"trim=start_frame=0:end_frame={n - 1},setpts=PTS-STARTPTS"]
    if has_audio:
        cmd += ["-af", f"atrim=end={end_time},asetpts=PTS-STARTPTS"]
    else:
        cmd += ["-an"]
    cmd += ["-c:v", "libx264"]
    if has_audio:
        cmd += ["-c:a", "aac"]
    cmd += [output_path]
    run(cmd)


def has_audio_stream(path):
    """Detecta si el video tiene pista de audio."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index", "-of", "csv=p=0", path,
    ]
    result = run(cmd)
    return bool(result.stdout.strip())


def extract_clip(input_path, start, end, out_path, has_audio):
    """Extrae un tramo [start, end) re-codificando para asegurar cortes exactos."""
    duration = end - start
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", input_path, "-t", str(duration)]
    if has_audio:
        cmd += ["-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero"]
    else:
        cmd += ["-an", "-c:v", "libx264", "-avoid_negative_ts", "make_zero"]
    cmd += [out_path]
    run(cmd)


def build_reversed_clip(segment_path, reversed_path, has_audio, frame_rate):
    """
    Genera la versión invertida (reversa) del segmento, recortando el primer
    frame de la reversa. Ese frame es idéntico al último frame del segmento
    original (que ya se mostró), así que sin este recorte se ve un frame
    duplicado / una pausa en cada punto de giro del boomerang. Con clips
    cortos ese "congelamiento" se nota mucho.
    """
    frame_duration = 1.0 / frame_rate
    video_filter = f"reverse,trim=start_frame=1,setpts=PTS-STARTPTS"
    cmd = ["ffmpeg", "-y", "-i", segment_path, "-vf", video_filter]
    if has_audio:
        audio_filter = f"areverse,atrim=start={frame_duration},asetpts=PTS-STARTPTS"
        cmd += ["-af", audio_filter]
    else:
        cmd += ["-an"]
    cmd += ["-c:v", "libx264"]
    if has_audio:
        cmd += ["-c:a", "aac"]
    cmd += [reversed_path]
    run(cmd)


def atempo_chain(speed):
    """
    El filtro atempo de ffmpeg solo acepta valores entre 0.5 y 2.0 por instancia.
    Para velocidades fuera de ese rango, hay que encadenar varios atempo.
    """
    factors = []
    remaining = speed
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    factors.append(remaining)
    return ",".join(f"atempo={f:.6f}" for f in factors)


def apply_speed(input_path, output_path, speed, has_audio):
    """Acelera o ralentiza un clip de video (y audio si tiene) manteniendo sincronía."""
    if speed == 1.0:
        # Nada que hacer, solo copiar
        run(["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path])
        return
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", f"setpts=PTS/{speed}"]
    if has_audio:
        cmd += ["-af", atempo_chain(speed)]
    else:
        cmd += ["-an"]
    cmd += ["-c:v", "libx264"]
    if has_audio:
        cmd += ["-c:a", "aac"]
    cmd += [output_path]
    run(cmd)


def concat_files(file_list, output_path, tmpdir, has_audio=True, reencode=True):
    """
    Concatena archivos de video usando el demuxer concat de ffmpeg.

    Por defecto re-codifica (reencode=True) en vez de copiar el stream (-c copy).
    Esto es importante para clips muy cortos (fracciones de segundo): copiar el
    stream en los empalmes puede romper la estructura de keyframes/GOP y causar
    que la imagen se congele en algún punto de la reproducción. Re-codificar es
    un poco más lento pero mucho más confiable, y para clips cortos el costo es
    insignificante.
    """
    list_path = os.path.join(tmpdir, f"list_{os.path.basename(output_path)}.txt")
    with open(list_path, "w") as f:
        for path in file_list:
            f.write(f"file '{os.path.abspath(path)}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path]
    if reencode:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        if has_audio:
            cmd += ["-c:a", "aac"]
        else:
            cmd += ["-an"]
    else:
        cmd += ["-c", "copy"]
    cmd += [output_path]
    run(cmd)


def build_boomerang_piece(input_path, start, end, loops, speed, has_audio, tmpdir, tag, frame_rate):
    """Crea el archivo boomerang (segmento + reversa, repetido 'loops' veces, a 'speed' veces la velocidad)."""
    segment_path = os.path.join(tmpdir, f"segment_{tag}.mp4")
    reversed_path = os.path.join(tmpdir, f"reversed_{tag}.mp4")
    cycle_path = os.path.join(tmpdir, f"cycle_{tag}.mp4")

    extract_clip(input_path, start, end, segment_path, has_audio)
    build_reversed_clip(segment_path, reversed_path, has_audio, frame_rate)

    if loops > 1:
        # Para los empalmes intermedios (entre una vuelta y la siguiente) se usa
        # una reversa sin su último frame, porque ese frame es idéntico al primer
        # frame del próximo ciclo (evita el freeze en cada empalme). La ÚLTIMA
        # vuelta sí usa la reversa completa, para terminar prolijo en el frame inicial.
        reversed_mid_path = os.path.join(tmpdir, f"reversed_mid_{tag}.mp4")
        trim_last_frame(reversed_path, reversed_mid_path, has_audio, frame_rate)

        file_list = []
        for _ in range(loops - 1):
            file_list += [segment_path, reversed_mid_path]
        file_list += [segment_path, reversed_path]

        looped_path = os.path.join(tmpdir, f"looped_{tag}.mp4")
        concat_files(file_list, looped_path, tmpdir, has_audio)
    else:
        concat_files([segment_path, reversed_path], cycle_path, tmpdir, has_audio)
        looped_path = cycle_path

    if speed != 1.0:
        final_path = os.path.join(tmpdir, f"boomerang_{tag}.mp4")
        apply_speed(looped_path, final_path, speed, has_audio)
        return final_path

    return looped_path


def main():
    parser = argparse.ArgumentParser(description="Reemplaza una o más secciones de un video por un efecto boomerang.")
    parser.add_argument("input", help="Ruta al video de entrada")
    parser.add_argument("--range", action="append", required=True, dest="ranges",
                         help="Rango 'start-end[@loops[@speed]]'. Se puede repetir varias veces.")
    parser.add_argument("--loops", type=int, default=1,
                         help="Loops por defecto para rangos que no especifiquen el suyo (default 1)")
    parser.add_argument("--speed", type=float, default=1.0,
                         help="Velocidad por defecto del boomerang, ej 2 = el doble de rápido (default 1.0)")
    parser.add_argument("-o", "--output", default=None, help="Ruta del video de salida")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No se encontró el archivo: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        ranges = [parse_range(r, args.loops, args.speed) for r in args.ranges]
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    ranges.sort(key=lambda r: r[0])  # ordenar por tiempo de inicio

    total_duration = get_duration(args.input)

    # Validar límites y que no se superpongan entre sí
    prev_end = 0.0
    for i, (start, end, loops, speed) in enumerate(ranges):
        if start < 0 or end > total_duration:
            print(f"El rango #{i+1} [{start}, {end}] está fuera de la duración del video "
                  f"({total_duration:.2f}s).", file=sys.stderr)
            sys.exit(1)
        if start < prev_end:
            print(f"El rango #{i+1} [{start}, {end}] se superpone con el anterior. "
                  f"Los rangos deben ser secuenciales y no superponerse.", file=sys.stderr)
            sys.exit(1)
        prev_end = end

    output_path = args.output or (os.path.splitext(args.input)[0] + "_boomerang.mp4")
    audio = has_audio_stream(args.input)
    frame_rate = get_frame_rate(args.input)

    print(f"Duración total del video: {total_duration:.2f}s")
    print(f"Frame rate: {frame_rate:.2f} fps")
    print(f"Audio detectado: {'sí' if audio else 'no'}")
    print(f"Secciones a convertir en boomerang ({len(ranges)}):")
    for start, end, loops, speed in ranges:
        print(f"  {start:.3f}s - {end:.3f}s  (loops={loops}, speed={speed}x)")

    with tempfile.TemporaryDirectory() as tmpdir:
        pieces = []
        cursor = 0.0

        for i, (start, end, loops, speed) in enumerate(ranges):
            if start > cursor:
                gap_path = os.path.join(tmpdir, f"gap_{i}.mp4")
                print(f"Extrayendo tramo normal {cursor:.3f}s - {start:.3f}s...")
                extract_clip(args.input, cursor, start, gap_path, audio)
                pieces.append(gap_path)

            print(f"Construyendo boomerang para {start:.3f}s - {end:.3f}s "
                  f"(loops={loops}, speed={speed}x)...")
            boomerang_path = build_boomerang_piece(args.input, start, end, loops, speed, audio, tmpdir, tag=i,
                                                    frame_rate=frame_rate)
            pieces.append(boomerang_path)

            cursor = end

        if cursor < total_duration:
            after_path = os.path.join(tmpdir, "after.mp4")
            print(f"Extrayendo tramo final {cursor:.3f}s - {total_duration:.3f}s...")
            extract_clip(args.input, cursor, total_duration, after_path, audio)
            pieces.append(after_path)

        print("Uniendo todo en el video final...")
        concat_files(pieces, output_path, tmpdir, audio)

    print(f"\nListo! Video generado en: {output_path}")


if __name__ == "__main__":
    main()