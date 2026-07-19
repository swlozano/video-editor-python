"""
image_util.py

Shared utility functions for working with images: getting their size,
calculating centering positions, etc. Used by compositor.py, resize.py,
and any other script that needs this kind of helper.

Usage as a module (from another script):

    from image_util import get_size, get_center, resolve_path

    width, height = get_size("test/image/bg.jpg")

    x, y = get_center("test/image/bg.jpg", "test/image/logo.png")

Requirements:
    pip install Pillow
"""

from pathlib import Path
from typing import Tuple, Union
from PIL import Image

# Carpeta donde vive este archivo (image_util.py).
# Se usa como base para resolver rutas relativas, sin importar desde
# dónde se ejecute el script o desde qué módulo se importe.
BASE_DIR = Path(__file__).resolve().parent

ImageInput = Union[str, Path, Image.Image]


def resolve_path(path: Union[str, Path]) -> Path:
    """
    Si `path` es absoluta, la devuelve tal cual.
    Si es relativa, la resuelve tomando como base la carpeta donde
    está image_util.py (BASE_DIR), no el directorio de trabajo actual.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _load_image(image: ImageInput) -> Image.Image:
    """
    Acepta una ruta (str/Path) o un objeto Image ya cargado, y siempre
    devuelve un objeto Image. Así las funciones de este módulo sirven
    tanto si le pasás una ruta como si ya tenés la imagen en memoria.
    """
    if isinstance(image, Image.Image):
        return image
    path = resolve_path(image)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path)


def get_size(image: ImageInput) -> Tuple[int, int]:
    """
    Returns the (width, height) of an image.

    Args:
        image: image path (str/Path) or an already-loaded PIL.Image.

    Returns:
        Tuple (width, height) in pixels.
    """
    img = _load_image(image)
    return img.width, img.height


def get_half(image: ImageInput) -> Tuple[int, int]:
    """
    Returns the (width // 2, height // 2) of an image, i.e. its own
    center point relative to itself.

    Args:
        image: image path (str/Path) or an already-loaded PIL.Image.

    Returns:
        Tuple (half_width, half_height) in pixels.
    """
    width, height = get_size(image)
    return width // 2, height // 2


def get_center(base_image: ImageInput, overlay_image: ImageInput) -> Tuple[int, int]:
    """
    Calculates the (x, y) position where overlay_image's top-left
    corner should be placed on base_image so that overlay_image ends
    up centered on top of base_image.

    Args:
        base_image: base/background image, path or PIL.Image.
        overlay_image: image to be centered on top of base_image,
                  path or PIL.Image.

    Returns:
        Tuple (x, y) in pixels, ready to use with compose_image().
    """
    base_width, base_height = get_size(base_image)
    overlay_width, overlay_height = get_size(overlay_image)

    x = (base_width - overlay_width) // 2
    y = (base_height - overlay_height) // 2
    return x, y


if __name__ == "__main__":
    # Ejemplo de uso por línea de comandos
    import argparse

    parser = argparse.ArgumentParser(description="Prints size and center info for images.")
    parser.add_argument("image", help="Path to the image")
    parser.add_argument("--center-on", default=None, help="If given, calculates the (x, y) to center this image on --image")
    args = parser.parse_args()

    w, h = get_size(args.image)
    print(f"Size of {args.image}: {w}x{h}")

    if args.center_on:
        x, y = get_center(args.image, args.center_on)
        print(f"Center position for {args.center_on} on {args.image}: x={x}, y={y}")