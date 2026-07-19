"""
file_util.py

Module to save a file (e.g. a PIL.Image, bytes, or text) to a given
path, automatically creating any missing folders along the way.

Usage as a module (from another script):

    from file_util import save_file
    from PIL import Image

    img = Image.open("some_photo.jpg")

    # Saves a PIL.Image, creating "test/image/output/" if it doesn't exist
    path = save_file(img, "test/image/output/result.png")
    print(path)

    # Saves raw bytes
    path = save_file(b"raw data", "test/data/output/file.bin")

    # Saves text
    path = save_file("hello world", "test/data/output/notes.txt")

Requirements:
    pip install Pillow
"""

from pathlib import Path
from typing import Union
from PIL import Image

# Carpeta donde vive este archivo (file_util.py).
# Se usa como base para resolver rutas relativas, sin importar desde
# dónde se ejecute el script o desde qué módulo se importe.
BASE_DIR = Path(__file__).resolve().parent


def resolve_path(path: Union[str, Path]) -> Path:
    """
    Si `path` es absoluta, la devuelve tal cual.
    Si es relativa, la resuelve tomando como base la carpeta donde
    está file_util.py (BASE_DIR), no el directorio de trabajo actual.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def ensure_folder(path: Union[str, Path]) -> Path:
    """
    Makes sure the parent folder of `path` exists, creating it (and any
    missing parent folders) if needed.

    Args:
        path: file path whose parent folder should exist. Can be
                  absolute or relative to file_util.py's folder.

    Returns:
        The resolved Path (not the folder, the full file path).
    """
    resolved = resolve_path(path)
    # mkdir crea todas las carpetas intermedias que falten (parents=True)
    # y no falla si ya existen (exist_ok=True).
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def save_file(content: Union[Image.Image, bytes, str], output_path: Union[str, Path]) -> str:
    """
    Saves `content` to `output_path`, creating any missing folders
    along the way.

    Args:
        content: what to save. Can be:
                  - a PIL.Image (saved using Pillow, format inferred
                    from the file extension in output_path).
                  - bytes (written as a binary file).
                  - str (written as a text file, UTF-8).
        output_path: where to save the file (absolute or relative to
                  file_util.py's folder). Missing parent folders are
                  created automatically.

    Returns:
        str with the final path where the file was saved.
    """
    path = ensure_folder(output_path)

    if isinstance(content, Image.Image):
        # Si la imagen tiene transparencia pero el formato de salida no
        # la soporta (ej. .jpg), se convierte a RGB antes de guardar.
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg") and content.mode != "RGB":
            content = content.convert("RGB")
        content.save(path)
    elif isinstance(content, bytes):
        path.write_bytes(content)
    elif isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        raise TypeError(f"Unsupported content type: {type(content).__name__}")

    return str(path)


def copy_file(source_path: Union[str, Path], output_path: Union[str, Path]) -> str:
    """
    Copies an existing file from source_path to output_path, creating
    any missing folders along the way.

    Args:
        source_path: path to the existing file to copy.
        output_path: destination path (folders are created if needed).

    Returns:
        str with the final path where the file was copied to.
    """
    import shutil

    source = resolve_path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    destination = ensure_folder(output_path)
    shutil.copy2(source, destination)
    return str(destination)


if __name__ == "__main__":
    # Ejemplo de uso por línea de comandos
    import argparse

    parser = argparse.ArgumentParser(description="Copies a file to a destination path, creating folders as needed.")
    parser.add_argument("source", help="Path to the source file")
    parser.add_argument("destination", help="Destination path")
    args = parser.parse_args()

    final_path = copy_file(args.source, args.destination)
    print(f"File saved at: {final_path}")