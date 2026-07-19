"""
image_join.py

Module to join a list of images one after another, either horizontally
(side by side) or vertically (stacked), into a single output image.

Usage as a module (from another script):

    from image_join import join_images

    path = join_images(
        images=["img1.jpg", "img2.jpg", "img3.jpg"],
        direction="horizontal",
    )
    print(path)

    # Or if you want the Image object back instead of saving to disk:
    img = join_images(
        images=["img1.jpg", "img2.jpg", "img3.jpg"],
        direction="vertical",
        return_type="image",
    )
    img.show()

Requirements:
    pip install Pillow
"""

from pathlib import Path
from typing import List, Literal, Union
from PIL import Image
from file_util import save_file

# Carpeta donde vive este archivo (image_join.py).
# Se usa como base para resolver rutas relativas, sin importar desde
# dónde se ejecute el script o desde qué módulo se importe.
BASE_DIR = Path(__file__).resolve().parent

ImageInput = Union[str, Path, Image.Image]


def resolve_path(path: Union[str, Path]) -> Path:
    """
    Si `path` es absoluta, la devuelve tal cual.
    Si es relativa, la resuelve tomando como base la carpeta donde
    está image_join.py (BASE_DIR), no el directorio de trabajo actual.
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
    path = resolve_path(image)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path).convert("RGBA")


def join_images(
    images: List[ImageInput],
    direction: Literal["horizontal", "vertical"] = "horizontal",
    spacing: int = 0,
    align: Literal["start", "center", "end"] = "center",
    background_color: tuple = (0, 0, 0, 0),
    output_path: Union[str, Path] = None,
    return_type: Literal["path", "image"] = "path",
) -> Union[str, Image.Image]:
    """
    Joins a list of images one after another into a single image.

    Args:
        images: list of images to join, in order. Each item can be a
                  path (str/Path) or an already-loaded PIL.Image.
                  Needs at least 2 images.
        direction: "horizontal" places them side by side (left to
                  right). "vertical" stacks them top to bottom.
        spacing: gap in pixels between consecutive images.
        align: how to align images that don't share the same size on
                  the cross axis. For "horizontal", this controls
                  vertical alignment ("start"=top, "center", "end"=
                  bottom). For "vertical", this controls horizontal
                  alignment ("start"=left, "center", "end"=right).
        background_color: RGBA color used to fill the canvas behind
                  the images (relevant when images don't fully cover
                  it, e.g. due to alignment or spacing). Default is
                  fully transparent.
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
    if len(images) < 2:
        raise ValueError("You need at least 2 images to join.")

    loaded = [_load_image(img) for img in images]

    if direction == "horizontal":
        total_width = sum(img.width for img in loaded) + spacing * (len(loaded) - 1)
        total_height = max(img.height for img in loaded)
    else:
        total_width = max(img.width for img in loaded)
        total_height = sum(img.height for img in loaded) + spacing * (len(loaded) - 1)

    canvas = Image.new("RGBA", (total_width, total_height), background_color)

    offset = 0
    for img in loaded:
        if direction == "horizontal":
            # Alinea verticalmente dentro de la fila
            if align == "start":
                y = 0
            elif align == "end":
                y = total_height - img.height
            else:  # center
                y = (total_height - img.height) // 2
            canvas.paste(img, (offset, y), img)
            offset += img.width + spacing
        else:
            # Alinea horizontalmente dentro de la columna
            if align == "start":
                x = 0
            elif align == "end":
                x = total_width - img.width
            else:  # center
                x = (total_width - img.width) // 2
            canvas.paste(img, (x, offset), img)
            offset += img.height + spacing

    if return_type == "image":
        if output_path:
            save_file(canvas.convert("RGB"), output_path)
        return canvas

    # return_type == "path"
    if output_path is None:
        output_path = BASE_DIR / "joined.png"

    return save_file(canvas, output_path)


if __name__ == "__main__":
    # Ejemplo de uso por línea de comandos
    import argparse

    parser = argparse.ArgumentParser(description="Joins several images side by side or stacked.")
    parser.add_argument("images", nargs="+", help="Paths of the images to join, in order")
    parser.add_argument("--direction", choices=["horizontal", "vertical"], default="horizontal")
    parser.add_argument("--spacing", type=int, default=0, help="Gap in pixels between images")
    parser.add_argument("--align", choices=["start", "center", "end"], default="center")
    parser.add_argument("--output", default=None, help="Output path (optional)")
    args = parser.parse_args()

    final_path = join_images(
        images=args.images,
        direction=args.direction,
        spacing=args.spacing,
        align=args.align,
        output_path=args.output,
    )
    print(f"Image generated at: {final_path}")