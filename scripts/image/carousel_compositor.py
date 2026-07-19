from dataset_loader import load_dataset
from image_join import join_images
from PIL import Image
from pathlib import Path
from typing import List, Union
from compositor import compose_image
from resize import resize_image

BASE_DIR = Path(__file__).resolve().parent


def resolve_path(path: Union[str, Path]) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _load_image(image):
    if isinstance(image, Image.Image):
        return image.convert("RGBA")
    path = resolve_path(image)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path).convert("RGBA")


def create_timeline(images: List[Union[str, Path, Image.Image]], 
                    image_frame_path: Union[str, Path, Image.Image]
                    ) -> List[str]:
    
    image_join = join_images(images=images, direction="horizontal")
    image_frame = _load_image(image_frame_path)
    results = []
    x_frame = 0
    
    for i, foto in enumerate(images):
        print(f"foto {foto}")
        
        path_frame = compose_image(
            image1=image_join,
            image2=image_frame_path,
            x=x_frame,
            y=0,
            output_path= f"test/image/out/fr{i}.png"
        )
        x_frame += image_frame.width
        results.append(path_frame)
        
    return results

def create_carousel(images: List[Union[str, Path, Image.Image]], 
                    image_frame_path: Union[str, Path, Image.Image]
                    ) -> List[str]:
    
    timeline_result = create_timeline(images=images, image_frame_path=image_frame_path)
    
    for i , image_back in enumerate(images):
        image_timeline = _load_image(f"{ timeline_result[i]}")
        image_resize = resize_image(image_timeline, width=_load_image(image_back).width, output_path=f"test/image/out/resize/resize.png")
        compose_image(image1=image_back,image2=image_resize,output_path=f"test/image/out/compose/result{i}.png")
    
    
    return

if __name__ == "__main__":
    print("carousel_compositor")
    paths = load_dataset("test/image/dataset")
    print(paths)
    create_carousel(paths,"test/image/dataset/frame/frame.png")