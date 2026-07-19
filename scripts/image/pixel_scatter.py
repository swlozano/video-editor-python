"""
pixel_scatter.py

Module to scatter random pixels from image2 onto image1: it picks a
set of positions on image1 and replaces each one with a randomly
sampled pixel color from image2. The only rule: none of the chosen
positions can be adjacent (touching) to each other on image1 — they
must always be separated by at least one untouched pixel.

Usage as a module (from another script):

    from pixel_scatter import scatter_pixels

    path = scatter_pixels(
        image1="test/image/bg.jpg",
        image2="test/image/texture.jpg",
        density=0.1,
    )
    print(path)

    # Or get the Image object back instead of saving to disk:
    img = scatter_pixels(
        image1="test/image/bg.jpg",
        image2="test/image/texture.jpg",
        density=0.1,
        return_type="image",
    )
    img.show()

Requirements:
    pip install Pillow numpy
"""

import random
from pathlib import Path
from typing import Literal, Union
from PIL import Image
import numpy as np

from file_util import save_file

# Carpeta donde vive este archivo (pixel_scatter.py).
# Se usa como base para resolver rutas relativas, sin importar desde
# dónde se ejecute el script o desde qué módulo se importe.
BASE_DIR = Path(__file__).resolve().parent

ImageInput = Union[str, Path, Image.Image]

# Densidad máxima teórica de un conjunto de posiciones no-adyacentes
# en una grilla, usada solo para avisar si se pide una densidad
# imposible de alcanzar.
MAX_DENSITY_8_CONNECTED = 0.25  # aprox., patrón tipo tablero de ajedrez espaciado
MAX_DENSITY_4_CONNECTED = 0.5   # aprox., patrón tipo tablero de ajedrez


def _resolve_path(path: Union[str, Path]) -> Path:
    """
    Si `path` es absoluta, la devuelve tal cual.
    Si es relativa, la resuelve tomando como base la carpeta donde
    está pixel_scatter.py (BASE_DIR), no el directorio de trabajo actual.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _load_image(image: ImageInput) -> Image.Image:
    """
    Acepta una ruta (str/Path) o un objeto Image ya cargado, y siempre
    devuelve un objeto Image en modo RGB.
    """
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    path = _resolve_path(image)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path).convert("RGB")


def scatter_pixels(
    image1: ImageInput,
    image2: ImageInput,
    density: float = 0.1,
    neighbor_mode: Literal["4", "8"] = "8",
    seed: int = None,
    output_path: Union[str, Path] = None,
    return_type: Literal["path", "image"] = "path",
) -> Union[str, Image.Image]:
    """
    Replaces a scattered set of pixels on image1 with random pixel
    colors sampled from image2. The chosen positions on image1 are
    never adjacent to each other.

    Args:
        image1: base image where pixels get replaced. Path (str/Path)
                  or an already-loaded PIL.Image.
        image2: image to sample random pixel colors from. Path
                  (str/Path) or an already-loaded PIL.Image. Does not
                  need to match image1's size — colors are sampled
                  from random coordinates within image2's own size.
        density: target fraction (0.0 - 1.0) of image1's pixels to
                  replace. Because replaced pixels can't be adjacent,
                  very high densities are not achievable — the
                  function replaces as many as it can and reports the
                  actual count reached.
        neighbor_mode: "8" (default) treats all 8 surrounding pixels
                  (including diagonals) as neighbors, giving a more
                  spaced-out scatter. "4" only treats up/down/left/
                  right as neighbors, allowing a denser (but still
                  non-touching) result.
        seed: optional random seed, for reproducible results.
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
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be between 0.0 and 1.0")

    rng = random.Random(seed)

    img1 = _load_image(image1)
    img2 = _load_image(image2)

    array1 = np.array(img1)
    array2 = np.array(img2)

    height, width = array1.shape[:2]
    target_count = int(height * width * density)

    # Vecindad a chequear: 4-conectada (cruz) u 8-conectada (todas las
    # direcciones, incluidas diagonales).
    if neighbor_mode == "8":
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    else:
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    # occupied marca qué posiciones de image1 ya fueron elegidas, para
    # poder chequear rápido si un candidato tiene un vecino ocupado.
    occupied = np.zeros((height, width), dtype=bool)

    # Se recorren todas las posiciones en orden aleatorio y se van
    # aceptando de a una si ninguno de sus vecinos ya fue elegido
    # (selección voraz de un conjunto "independiente" en la grilla).
    all_positions = [(y, x) for y in range(height) for x in range(width)]
    rng.shuffle(all_positions)

    chosen = []
    for y, x in all_positions:
        if len(chosen) >= target_count:
            break

        has_occupied_neighbor = False
        for dy, dx in offsets:
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and occupied[ny, nx]:
                has_occupied_neighbor = True
                break

        if not has_occupied_neighbor:
            occupied[y, x] = True
            chosen.append((y, x))

    # Para cada posición elegida, se toma un pixel de color aleatorio
    # desde image2 (coordenadas propias, independientes del tamaño de
    # image1) y se pega en esa posición.
    src_height, src_width = array2.shape[:2]
    result_array = array1.copy()
    for y, x in chosen:
        sy = rng.randrange(src_height)
        sx = rng.randrange(src_width)
        result_array[y, x] = array2[sy, sx]

    actual_density = len(chosen) / (height * width)
    print(f"Replaced {len(chosen)} pixels (requested density: {density:.2%}, actual: {actual_density:.2%})")

    result = Image.fromarray(result_array)

    if return_type == "image":
        if output_path:
            save_file(result, output_path)
        return result

    # return_type == "path"
    if output_path is None:
        if isinstance(image1, Image.Image):
            output_path = "scattered.png"
        else:
            image1_path = _resolve_path(image1)
            output_path = image1_path.parent / f"{image1_path.stem}_scattered.png"

    return save_file(result, output_path)


if __name__ == "__main__":
    # Ejemplo de uso por línea de comandos
    import argparse

    parser = argparse.ArgumentParser(description="Scatters random pixels from image2 onto image1, never adjacent.")
    parser.add_argument("image1", help="Path to the base image")
    parser.add_argument("image2", help="Path to the image to sample pixel colors from")
    parser.add_argument("--density", type=float, default=0.1, help="Target fraction of pixels to replace (0.0 - 1.0)")
    parser.add_argument("--neighbor-mode", choices=["4", "8"], default="8", help="Adjacency rule: 4 or 8 connected")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", default=None, help="Output path (optional)")
    args = parser.parse_args()

    final_path = scatter_pixels(
        image1=args.image1,
        image2=args.image2,
        density=args.density,
        neighbor_mode=args.neighbor_mode,
        seed=args.seed,
        output_path=args.output,
    )
    print(f"Image generated at: {final_path}")