#!/usr/bin/env python3
"""
video_cutter.py
================

Genera un video "resumen" a partir de un archivo .mkv, tomando cortes
(fragmentos) aleatorios del video original.

FLUJO GENERAL
-------------
1. Si el archivo CSV (--csv) no existe o está vacío -> se generan TODOS
   los fragmentos desde cero, de forma aleatoria.
2. Si el CSV ya existe y tiene datos -> se usa como fuente de verdad:
      - Filas con source_start / source_end = "X"  -> ese fragmento se
        REEMPLAZA por uno nuevo elegido al azar (que no se haya usado antes).
      - Filas con source_start / source_end = números -> se respetan tal
        cual (ya sea porque vienen de una corrida anterior, o porque el
        usuario los escribió a mano para indicar qué parte del video
        original quiere usar en ese hueco).
3. Se lleva un historial persistente (--history) con todos los fragmentos
   (inicio, fin) que alguna vez se usaron, para que al generar fragmentos
   nuevos (aleatorios) nunca se repita un pedazo del video ya utilizado.
4. Se recalculan las columnas output_start / output_end según el orden de
   las filas en el CSV (esa es la posición del fragmento dentro del video
   final generado).
5. Se cortan los fragmentos con ffmpeg y se concatenan en el video final.
6. Se reescribe el CSV con el resultado final (para que quede sincronizado
   y el usuario pueda volver a editarlo para la siguiente corrida).

FORMATO DEL CSV
----------------
index,source_start,source_end,output_start,output_end

- index          : número de orden del fragmento (1, 2, 3, ...)
- source_start   : segundo del VIDEO ORIGINAL donde empieza el corte
- source_end     : segundo del VIDEO ORIGINAL donde termina el corte
- output_start   : segundo del VIDEO FINAL donde queda ese fragmento
- output_end     : segundo del VIDEO FINAL donde termina ese fragmento

Para pedir que un fragmento se reemplace por uno nuevo (aleatorio),
el usuario simplemente pone una "X" (mayúscula o minúscula) en
source_start y/o source_end de esa fila y vuelve a correr el script.

Para pedir que un fragmento se reemplace por una parte ESPECÍFICA del
video original, el usuario escribe los segundos exactos que quiere en
source_start / source_end de esa fila (en vez de "X").

USO
---
    python video_cutter.py entrada.mkv

    python video_cutter.py entrada.mkv \
        --output salida.mp4 \
        --csv cortes.csv \
        --history historial.json \
        --total-duration 120 \
        --clip-duration 30

Requiere ffmpeg y ffprobe instalados y accesibles en el PATH.
"""

import argparse
import csv
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# --------------------------------------------------------------------------
# Utilidades de video (ffmpeg / ffprobe)
# --------------------------------------------------------------------------

def get_video_duration(path: Path) -> float:
    """Devuelve la duración total del video en segundos usando ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"[ERROR] No se pudo leer la duración del video: {result.stderr}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        sys.exit(f"[ERROR] ffprobe devolvió una duración inválida: {result.stdout!r}")


def extract_clip(input_path: Path, start: float, duration: float, output_path: Path) -> None:
    """Extrae un fragmento del video original re-codificando para precisión."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", str(input_path),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"[ERROR] ffmpeg falló extrayendo el clip {start}-{start+duration}: {result.stderr}")


def concat_clips(clip_paths, output_path: Path) -> None:
    """Concatena una lista de clips (ya en el mismo códec) en un solo video."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        list_file = Path(f.name)
        for clip in clip_paths:
            # Escapar comillas simples para el formato del concat demuxer
            safe_path = str(clip.resolve()).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        sys.exit(f"[ERROR] ffmpeg falló concatenando los clips: {result.stderr}")


# --------------------------------------------------------------------------
# Utilidades de intervalos (para no solapar / no repetir fragmentos)
# --------------------------------------------------------------------------

def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def find_random_fragment(video_duration, clip_duration, avoid_intervals, max_tries=500):
    """Busca un fragmento aleatorio de `clip_duration` segundos que no se
    solape con ninguno de los intervalos en `avoid_intervals`."""
    if clip_duration >= video_duration:
        sys.exit("[ERROR] La duración del corte es mayor o igual a la del video original.")

    max_start = video_duration - clip_duration
    for _ in range(max_tries):
        start = random.uniform(0, max_start)
        end = start + clip_duration
        if not any(overlaps(start, end, a, b) for a, b in avoid_intervals):
            return round(start, 2), round(end, 2)

    sys.exit(
        "[ERROR] No se encontró un fragmento libre sin solaparse con fragmentos "
        "ya usados. El video puede ser demasiado corto para la cantidad de "
        "cortes / duración pedida, o ya se usó casi todo el metraje."
    )


# --------------------------------------------------------------------------
# Historial persistente de fragmentos usados (para no repetir entre corridas)
# --------------------------------------------------------------------------

def load_history(history_path: Path):
    if not history_path.exists():
        return []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [(float(a), float(b)) for a, b in data]
    except (json.JSONDecodeError, ValueError):
        print(f"[AVISO] El historial en {history_path} está corrupto, se ignora.")
        return []


def save_history(history_path: Path, intervals):
    # Deduplicar conservando orden
    seen = set()
    unique = []
    for a, b in intervals:
        key = (round(a, 2), round(b, 2))
        if key not in seen:
            seen.add(key)
            unique.append(key)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2)


# --------------------------------------------------------------------------
# Lectura / escritura del CSV de cortes
# --------------------------------------------------------------------------

CSV_FIELDS = ["index", "source_start", "source_end", "output_start", "output_end"]


def load_csv_rows(csv_path: Path):
    """Devuelve la lista de filas del CSV, o None si no existe o está vacío."""
    if not csv_path.exists():
        return None
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]
    return rows if rows else None


def save_csv_rows(csv_path: Path, rows):
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def is_placeholder(value: str) -> bool:
    """True si la celda está vacía o marcada con X (pide reemplazo aleatorio)."""
    if value is None:
        return True
    v = value.strip().lower()
    return v == "" or v == "x"


# --------------------------------------------------------------------------
# Lógica principal de construcción de fragmentos
# --------------------------------------------------------------------------

def build_fragments(csv_rows, n_clips, video_duration, clip_duration, history):
    """
    Devuelve la lista final de fragmentos [(source_start, source_end), ...]
    en el orden en que deben ir en el video final, respetando:
      - fragmentos fijos (números en el CSV) -> se mantienen
      - fragmentos marcados con "X"          -> se reemplazan por nuevos
      - fragmentos faltantes (CSV con menos filas que n_clips) -> se agregan
      - fragmentos sobrantes (CSV con más filas que n_clips)   -> se recortan
    """
    fragments = [None] * n_clips
    fixed_intervals = []  # fragmentos que NO se van a tocar en esta corrida

    if csv_rows:
        if len(csv_rows) > n_clips:
            print(f"[AVISO] El CSV tiene {len(csv_rows)} filas pero solo se "
                  f"necesitan {n_clips} según --total-duration/--clip-duration. "
                  f"Se descartan las últimas {len(csv_rows) - n_clips}.")
        csv_rows = csv_rows[:n_clips]

        for i, row in enumerate(csv_rows):
            s_raw = row.get("source_start", "")
            e_raw = row.get("source_end", "")
            if is_placeholder(s_raw) or is_placeholder(e_raw):
                fragments[i] = "X"  # marcador temporal, se resuelve después
            else:
                try:
                    s, e = float(s_raw), float(e_raw)
                except ValueError:
                    sys.exit(f"[ERROR] Fila {i+1} del CSV tiene valores no numéricos: "
                              f"source_start={s_raw!r}, source_end={e_raw!r}")
                if s < 0 or e > video_duration or s >= e:
                    sys.exit(f"[ERROR] Fila {i+1} del CSV tiene un rango inválido "
                              f"({s}-{e}) para un video de {video_duration:.2f}s.")
                fragments[i] = (s, e)
                fixed_intervals.append((s, e))

    if len(fragments) > len(csv_rows or []):
        print(f"[AVISO] El CSV tenía {len(csv_rows or [])} filas, se agregan "
              f"{len(fragments) - len(csv_rows or [])} fragmentos aleatorios nuevos.")

    # Resolver los que faltan (None = CSV no traía esa fila) o están en "X"
    avoid = list(history) + fixed_intervals
    for i in range(n_clips):
        if fragments[i] is None or fragments[i] == "X":
            new_frag = find_random_fragment(video_duration, clip_duration, avoid)
            fragments[i] = new_frag
            avoid.append(new_frag)

    return fragments


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Genera un video de cortes aleatorios a partir de un .mkv, "
                    "controlado por un CSV editable.",
    )
    parser.add_argument("input", type=Path, help="Video de entrada (.mkv)")
    parser.add_argument("--output", type=Path, default=None,
                         help="Video de salida (default: <input>_cortes.mp4)")
    parser.add_argument("--csv", type=Path, default=None,
                         help="Archivo CSV de cortes (default: <input>_cortes.csv)")
    parser.add_argument("--history", type=Path, default=None,
                         help="Archivo de historial de fragmentos usados "
                              "(default: <input>_historial.json)")
    parser.add_argument("--total-duration", type=float, default=120,
                         help="Duración total del video final en segundos (default: 120)")
    parser.add_argument("--clip-duration", type=float, default=30,
                         help="Duración de cada corte en segundos (default: 30)")
    parser.add_argument("--keep-temp", action="store_true",
                         help="No borrar los clips temporales al terminar")
    args = parser.parse_args()

    input_path = args.input
    if not input_path.exists():
        sys.exit(f"[ERROR] No existe el archivo de entrada: {input_path}")

    stem = input_path.with_suffix("")
    output_path = args.output or Path(f"{stem}_cortes.mp4")
    csv_path = args.csv or Path(f"{stem}_cortes.csv")
    history_path = args.history or Path(f"{stem}_historial.json")

    if args.clip_duration <= 0 or args.total_duration <= 0:
        sys.exit("[ERROR] --total-duration y --clip-duration deben ser mayores a 0.")

    n_clips = int(args.total_duration // args.clip_duration)
    if n_clips < 1:
        sys.exit("[ERROR] --clip-duration es mayor que --total-duration, no hay cortes que hacer.")
    real_total = n_clips * args.clip_duration
    if real_total != args.total_duration:
        print(f"[AVISO] {args.total_duration}s no es múltiplo exacto de {args.clip_duration}s. "
              f"Se generarán {n_clips} cortes = {real_total}s de video final.")

    print(f"[INFO] Analizando video de entrada: {input_path}")
    video_duration = get_video_duration(input_path)
    print(f"[INFO] Duración del video original: {video_duration:.2f}s")

    if args.clip_duration > video_duration:
        sys.exit("[ERROR] --clip-duration es mayor que la duración del video original.")

    history = load_history(history_path)
    csv_rows = load_csv_rows(csv_path)

    if csv_rows is None:
        print(f"[INFO] {csv_path} no existe o está vacío -> generando todo desde cero.")
    else:
        print(f"[INFO] Leyendo cortes existentes desde {csv_path} "
              f"({len(csv_rows)} filas encontradas).")

    fragments = build_fragments(csv_rows, n_clips, video_duration, args.clip_duration, history)

    # Extraer y concatenar los clips
    tmp_dir = Path(tempfile.mkdtemp(prefix="video_cutter_"))
    clip_paths = []
    try:
        print("[INFO] Extrayendo fragmentos...")
        for i, (s, e) in enumerate(fragments):
            clip_path = tmp_dir / f"clip_{i:03d}.mp4"
            extract_clip(input_path, s, e - s, clip_path)
            clip_paths.append(clip_path)
            print(f"    - Corte {i+1}/{n_clips}: original {s:.2f}s -> {e:.2f}s")

        print(f"[INFO] Concatenando {len(clip_paths)} clips en {output_path} ...")
        concat_clips(clip_paths, output_path)
    finally:
        if not args.keep_temp:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            print(f"[INFO] Clips temporales conservados en: {tmp_dir}")

    # Recalcular output_start/output_end según el orden final y reescribir el CSV
    rows_out = []
    for i, (s, e) in enumerate(fragments):
        out_start = i * args.clip_duration
        out_end = out_start + args.clip_duration
        rows_out.append({
            "index": i + 1,
            "source_start": f"{s:.2f}",
            "source_end": f"{e:.2f}",
            "output_start": f"{out_start:.2f}",
            "output_end": f"{out_end:.2f}",
        })
    save_csv_rows(csv_path, rows_out)
    print(f"[INFO] CSV actualizado: {csv_path}")

    # Actualizar historial con todos los fragmentos usados en esta corrida
    save_history(history_path, history + fragments)
    print(f"[INFO] Historial actualizado: {history_path}")

    print(f"\n[LISTO] Video final generado: {output_path}")
    print("Para regenerar cortes específicos, edita el CSV: pon una 'X' en "
          "source_start/source_end de la fila que quieras reemplazar por un "
          "corte aleatorio nuevo, o escribe los segundos exactos del video "
          "original que quieres usar en su lugar. Luego vuelve a correr el script.")


if __name__ == "__main__":
    main()