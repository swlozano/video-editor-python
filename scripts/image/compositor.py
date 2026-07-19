"""
compositor.py

Module to overlay an image (image2) on top of another one (image1) at a
given (x, y) position. It does not resize either image: it uses each
image's original size as-is.

Usage as a module (from another script):

    from compositor import compose_image

    path = compose_image(
        image1="test/image/bg.jpg",
        image2="test/image/logo.png",
        x=100,
        y=50,
    )
    print(path)

    # Or if you want the Image object back instead of saving to disk:
    img = compose_image(
        image1="test/image/bg.jpg",
        image2="test/image/logo.png",
        x=100,
        y=50,
        return_type="image",
    )
    img.show()

Requirements:
    pip install Pillow
"""

from pathlib import Path
from typing import Literal, Union
from PIL import Image
from file_util import save_file

# Carpeta donde vive este archivo (compositor.py).
# Se usa como base para resolver rutas relativas, sin importar desde
# dónde se ejecute el script o desde qué módulo se importe.
BASE_DIR = Path(__file__).resolve().parent

ImageInput = Union[str, Path, Image.Image]


def _resolve_path(path: Union[str, Path]) -> Path:
    """
    Si `path` es absoluta, la devuelve tal cual.
    Si es relativa, la resuelve tomando como base la carpeta donde
    está compositor.py (BASE_DIR), no el directorio de trabajo actual.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _load_image(image: ImageInput) -> Image.Image:
    """
    Acepta una ruta (str/Path) o un objeto Image ya cargado, y siempre
    devuelve un objeto Image en modo RGBA.
    """
    if isinstance(image, Image.Image):
        return image.convert("RGBA")
    path = _resolve_path(image)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path).convert("RGBA")


def compose_image(
    image1: ImageInput,
    image2: ImageInput,
    x: int = 0,
    y: int = 0,
    output_path: Union[str, Path] = None,
    return_type: Literal["path", "image"] = "path",
) -> Union[str, Image.Image]:
    """
    Places image2 on top of image1 at position (x, y).

    Args:
        image1: base image (background). Path (str/Path) or an
                  already-loaded PIL.Image.
        image2: image to overlay. Path (str/Path) or an already-loaded
                  PIL.Image.
        x: horizontal position (px) where image2's top-left corner
           is pasted onto image1.
        y: vertical position (px) where image2's top-left corner
           is pasted onto image1.
        output_path: where to save the result. If not provided and
                  return_type="path", an automatic name is generated.
        return_type: "path" -> saves the file and returns the path (str).
                  "image" -> returns the PIL.Image object without saving it
                  (unless output_path was also provided, in which case it
                  saves it anyway and also returns the image).

    Returns:
        str with the path to the generated file, or a PIL.Image object,
        depending on the `return_type` parameter.
    """
    # Cargar imágenes en modo RGBA para soportar transparencia
    base = _load_image(image1)
    overlay = _load_image(image2)

    # Pegar respetando el canal alpha de image2
    result = base.copy()
    result.paste(overlay, (x, y), overlay)

    if return_type == "image":
        if output_path:
            save_file(result.convert("RGB"),output_path)
        return result

    # return_type == "path"
    if output_path is None:
        # Si image1 era una ruta, se usa su carpeta/nombre como base.
        # Si era un objeto Image en memoria, se guarda en BASE_DIR.
        if isinstance(image1, Image.Image):
            output_path = BASE_DIR / "composed.png"
        else:
            image1_path = _resolve_path(image1)
            output_path = image1_path.parent / f"{image1_path.stem}_composed.png"

    return save_file(result, output_path)


if __name__ == "__main__":
    # Ejemplo de uso por línea de comandos
    import argparse

    parser = argparse.ArgumentParser(description="Places image2 on top of image1 at position (x, y).")
    parser.add_argument("image1", help="Path to the base image")
    parser.add_argument("image2", help="Path to the image to overlay")
    parser.add_argument("--x", type=int, default=0, help="Horizontal position (px)")
    parser.add_argument("--y", type=int, default=0, help="Vertical position (px)")
    parser.add_argument("--output", default=None, help="Output path (optional)")
    args = parser.parse_args()

    final_path = compose_image(
        image1=args.image1,
        image2=args.image2,
        x=args.x,
        y=args.y,
        output_path=args.output,
    )
    print(f"Image generated at: {final_path}")