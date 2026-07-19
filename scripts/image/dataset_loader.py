"""
dataset_loader.py

Module to load a dataset of images from a folder: list matching files,
optionally filter by extension, search recursively, and load them as
paths or as PIL.Image objects.

Usage as a module (from another script):

    from dataset_loader import load_dataset

    # Get a list of paths (str)
    paths = load_dataset("test/image/dataset")

    # Get a list of PIL.Image objects already loaded
    images = load_dataset("test/image/dataset", return_type="image")

    # Only .jpg and .png, searching subfolders too
    paths = load_dataset(
        "test/image/dataset",
        extensions=[".jpg", ".png"],
        recursive=True,
    )

Requirements:
    pip install Pillow
"""

from pathlib import Path
from typing import List, Literal, Union
from PIL import Image

# Carpeta donde vive este archivo (dataset_loader.py).
# Se usa como base para resolver rutas relativas, sin importar desde
# dónde se ejecute el script o desde qué módulo se importe.
BASE_DIR = Path(__file__).resolve().parent

# Extensiones de imagen soportadas por default.
DEFAULT_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"]


def resolve_path(path: Union[str, Path]) -> Path:
    """
    Si `path` es absoluta, la devuelve tal cual.
    Si es relativa, la resuelve tomando como base la carpeta donde
    está dataset_loader.py (BASE_DIR), no el directorio de trabajo actual.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def load_dataset(
    folder_path: Union[str, Path],
    extensions: List[str] = None,
    recursive: bool = False,
    return_type: Literal["path", "image"] = "path",
    sort: bool = True,
) -> Union[List[str], List[Image.Image]]:
    """
    Loads a dataset of images from a folder.

    Args:
        folder_path: path to the folder containing the images
                  (absolute or relative to dataset_loader.py's folder).
        extensions: list of file extensions to include (e.g.
                  [".jpg", ".png"]). Case-insensitive. If not provided,
                  uses DEFAULT_EXTENSIONS (jpg, jpeg, png, webp, bmp,
                  gif, tiff).
        recursive: if True, also searches inside subfolders. If False
                  (default), only looks at files directly inside
                  folder_path.
        return_type: "path" -> returns a list of file paths (str).
                  "image" -> returns a list of PIL.Image objects,
                  already opened and ready to use.
        sort: if True (default), sorts the results alphabetically by
                  filename, so the order is stable and predictable.

    Returns:
        A list of strings (paths) or a list of PIL.Image objects,
        depending on `return_type`.
    """
    folder = resolve_path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")

    exts = {e.lower() for e in (extensions or DEFAULT_EXTENSIONS)}

    # "**/*" busca en subcarpetas, "*" solo en el nivel actual.
    pattern = "**/*" if recursive else "*"
    files = [
        f for f in folder.glob(pattern)
        if f.is_file() and f.suffix.lower() in exts
    ]

    if sort:
        files.sort(key=lambda f: f.name)

    if return_type == "image":
        return [Image.open(f) for f in files]

    return [str(f) for f in files]


if __name__ == "__main__":
    # Ejemplo de uso por línea de comandos
    import argparse

    parser = argparse.ArgumentParser(description="Lists the images found in a folder (dataset).")
    parser.add_argument("folder", help="Path to the folder containing the images")
    parser.add_argument("--extensions", nargs="+", default=None, help="Extensions to include, e.g. --extensions .jpg .png")
    parser.add_argument("--recursive", action="store_true", help="Also search inside subfolders")
    args = parser.parse_args()

    result = load_dataset(
        folder_path=args.folder,
        extensions=args.extensions,
        recursive=args.recursive,
    )

    print(f"Found {len(result)} images:")
    for path in result:
        print(f"  - {path}")