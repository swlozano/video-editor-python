from compositor import compose_image
from resize import resize_image
from image_util import get_center
from dataset_loader import load_dataset
from image_join import join_images
from carousel_compositor import create_timeline
from PIL import Image


dataset_path = "test/image/dataset"

dataset = load_dataset(dataset_path)
resizes = []
composes = []
image_resize = ""
width = 1080
background = resize_image("test/image/bg.jpg", 
                          width=1080, height=1920,
                          output_path=f"out/bg/bg_resize.png")


for i, image in enumerate(dataset):
    image_resize = resize_image(image, width, output_path=f"out/resize/resize_{i}.png")
    resizes.append(image_resize)
    x, y = get_center(background, image_resize)
    compose = compose_image(
        image1=background,
        image2=image_resize,
        x=x,
        y=y,
        output_path=f"out/compose/compose_{i}.png"
    )
    composes.append(compose)
    
image_timeline = create_timeline(resizes, "test/image/dataset/frame/frame.png")
resize_heigth = y+Image.open(resizes[0]).convert("RGBA").height


for i, image in enumerate(dataset):
    image_resize = resize_image(image_timeline[i], width, return_type="image")
    compose = compose_image(
        image1=composes[i],
        image2=image_resize,
        x=x,
        y=resize_heigth,
        output_path=f"out/compose_timeline/compose_{i}.png"
    )
    

# Estira la imagen exactamente a 1080x1080 (puede deformarla si la proporción no coincide)
"""
img1_path = resize_image("test/image/bg3.jpg", width=1080, height=1920)
print(f"ruta{img1_path}")

img2_path  = "test/image/frame_004747.jpg"
img2_path = resize_image(img2_path, 1080)


x, y = get_center(img1_path, img2_path)


ruta = compose_image(
    image1=img1_path,
    image2=img2_path,
    x=x,
    y=y,
)

print(ruta)

paths = load_dataset("test/image/dataset")


# Horizontal: una al lado de la otra
pathj = join_images(paths, direction="horizontal")
print(f"pathj------------> {pathj}")


pathf = compose_image(
    image1=pathj,
    image2="test/image/dataset/frame/frame.png",
    x=0,
    y=0,
)
print(f"path frame----------------->{pathf}")


# Vertical: una debajo de la otra
#path = join_images(["img1.jpg", "img2.jpg", "img3.jpg"], direction="vertical")

# Con espacio entre ellas y alineadas al inicio
#path = join_images(["img1.jpg", "img2.jpg"], direction="horizontal", spacing=20, align="start")
"""