#!/usr/bin/env python3
"""
detect_bands_to_cmd.py
=======================

Recibe un archivo CSV de detect_bands y convierte start_s,end_s
a rangos tipo "0-10 1-20" para usar con super_cutter.py.

USO
---
    python3 detect_bands_to_cmd.py result.csv
    python3 detect_bands_to_cmd.py result.csv --band bass
"""

import argparse
import csv
import sys


def main():
    parser = argparse.ArgumentParser(description="Convierte CSV de detect_bands a rangos.")
    parser.add_argument("csv", type=str, help="Archivo CSV de detect_bands")
    parser.add_argument("--band", default=None, help="Filtrar por banda específica")
    args = parser.parse_args()

    try:
        with open(args.csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
    except FileNotFoundError:
        sys.exit(f"[ERROR] No existe el archivo: {args.csv}")

    if args.band:
        rows = [r for r in rows if r["band"] == args.band]

    if not rows:
        sys.exit("[ERROR] No se encontraron segmentos.")

    ranges = []
    for row in rows:
        start = float(row["start_s"])
        end = float(row["end_s"])
        ranges.append(f"{start:.3f}-{end:.3f}")

    print(" ".join(ranges))


if __name__ == "__main__":
    main()
