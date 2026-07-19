"""
image_interlace.py

Module to combine two images by interlacing them: either by columns
(even columns from image1, odd columns from image2) or by rows (even
rows from image1, odd rows from image2), producing a new "striped"
image made of alternating slices.

Both images must end up with the same size to be combined slice by
slice. If they don't match, image2 is resized to image1's size
(configurable).

Usage as a module (from another script):

    from image_interlace import interlace_images

    # Alternating columns (default)
    path = interlace_images(
        image1="test/image/img1.jpg",
        image2="test/image/img2.jpg",
        axis="columns",
    )

    # Alternating rows
    path = interlace_images(
        image1="test/image/img1.jpg",
        image2="test/image/img2.jpg",
        axis="rows",
    )
    print(path)

    # Or get the Image object back instead of saving to disk:
    img = interlace_images(
        image1="test/image/img1.jpg",
        image2="test/image/img2.jpg",
        axis="rows",
        return_type="image",
    )
    img.show()

Requirements:
    pip install Pillow numpy
"""

from pathlib import Path
from typing import Literal, Union
from PIL import Image
import numpy as np

from file_util import save_file

# Carpeta donde vive este archivo (image_interlace.py).
# Se usa como base para resolver rutas relativas, sin importar desde
# dónde se ejecute el script o desde qué módulo se importe.
BASE_DIR = Path(__file__).resolve().parent

ImageInput = Union[str, Path, Image.Image]


def _resolve_path(path: Union[str, Path]) -> Path:
    """
    Si `path` es absoluta, la devuelve tal cual.
    Si es relativa, la resuelve tomando como base la carpeta donde
    está image_interlace.py (BASE_DIR), no el directorio de trabajo actual.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _load_image(image: ImageInput) -> Image.Image:
    """
    Acepta una ruta (str/Path) o un objeto Image ya cargado, y siempre
    devuelve un objeto Image en modo RGB (sin canal alpha, para que
    el array de numpy tenga siempre 3 canales consistentes).
    """
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    path = _resolve_path(image)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path).convert("RGB")


def interlace_images(
    image1: ImageInput,
    image2: ImageInput,
    axis: Literal["columns", "rows"] = "columns",
    resize_to_match: bool = True,
    output_path: Union[str, Path] = None,
    return_type: Literal["path", "image"] = "path",
) -> Union[str, Image.Image]:
    """
    Combines image1 and image2 by alternating either their columns or
    their rows. Even slices (0, 2, 4, ...) come from image1, odd
    slices (1, 3, 5, ...) come from image2.

    Args:
        image1: image to take the even slices from. Path (str/Path)
                  or an already-loaded PIL.Image.
        image2: image to take the odd slices from. Path (str/Path)
                  or an already-loaded PIL.Image.
        axis: "columns" alternates vertical stripes (column by
                  column). "rows" alternates horizontal stripes (row
                  by row).
        resize_to_match: if True (default) and both images have
                  different sizes, image2 is resized to match image1's
                  size before combining. If False and sizes don't
                  match, raises a ValueError instead.
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
    img1 = _load_image(image1)
    img2 = _load_image(image2)

    if img1.size != img2.size:
        if resize_to_match:
            img2 = img2.resize(img1.size, Image.LANCZOS)
        else:
            raise ValueError(
                f"image1 and image2 must have the same size to interlace "
                f"(got {img1.size} and {img2.size}). "
                f"Set resize_to_match=True to auto-resize image2."
            )

    # Convertir a arrays de numpy para poder seleccionar filas/columnas
    # pares/impares de forma vectorizada (mucho más rápido que un
    # loop píxel por píxel en Python puro).
    array1 = np.array(img1)
    array2 = np.array(img2)

    result_array = array1.copy()

    if axis == "columns":
        # Un array de imagen tiene forma (alto, ancho, canales), así
        # que las columnas son el eje 1. Se reemplazan las impares.
        result_array[:, 1::2] = array2[:, 1::2]
    else:  # axis == "rows"
        # Las filas son el eje 0. Se reemplazan las impares.
        result_array[1::2, :] = array2[1::2, :]

    result = Image.fromarray(result_array)

    if return_type == "image":
        if output_path:
            save_file(result, output_path)
        return result

    # return_type == "path"
    if output_path is None:
        if isinstance(image1, Image.Image):
            output_path = "interlaced.png"
        else:
            image1_path = _resolve_path(image1)
            output_path = image1_path.parent / f"{image1_path.stem}_interlaced.png"

    return save_file(result, output_path)


# Alias por compatibilidad con el nombre anterior (equivalente a
# interlace_images(..., axis="columns")).
def interlace_columns(image1, image2, **kwargs):
    return interlace_images(image1, image2, axis="columns", **kwargs)


def interlace_rows(image1, image2, **kwargs):
    return interlace_images(image1, image2, axis="rows", **kwargs)


if __name__ == "__main__":
    # Ejemplo de uso por línea de comandos
    import argparse

    parser = argparse.ArgumentParser(description="Combines two images by interlacing their columns or rows.")
    parser.add_argument("image1", help="Path to the image to take even slices from")
    parser.add_argument("image2", help="Path to the image to take odd slices from")
    parser.add_argument("--axis", choices=["columns", "rows"], default="columns", help="Alternate by columns or rows")
    parser.add_argument("--output", default=None, help="Output path (optional)")
    args = parser.parse_args()

    final_path = interlace_images(
        image1=args.image1,
        image2=args.image2,
        axis=args.axis,
        output_path=args.output,
    )
    print(f"Image generated at: {final_path}")