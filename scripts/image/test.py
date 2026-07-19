from datetime import datetime
from image_interlace import interlace_images, interlace_columns, interlace_rows

# Alternar columnas (lo que ya tenías)
path = interlace_images(
                        image1="/Users/main/Dev/Python/video-editor/scripts/image/in/i17.png", 
                        image2="/Users/main/Dev/Python/video-editor/scripts/image/in/i12.2.png", 
                        output_path="/Users/main/Dev/Python/video-editor/scripts/image/in/r1_1_2.png",
                        axis="columns",
                        )

path = interlace_images(
                        image1="/Users/main/Dev/Python/video-editor/scripts/image/in/i17.png", 
                        image2="/Users/main/Dev/Python/video-editor/scripts/image/in/i12.2.png", 
                        output_path="/Users/main/Dev/Python/video-editor/scripts/image/in/r2_1_2.png",
                        axis="rows"
                        )

# Alternar filas (lo nuevo)
#path = interlace_images(image1="i1.png", image2="i2.png", axis="rows")

# Funciones de conveniencia, mismos resultados que las de arriba
#path = interlace_columns(image1="i1.png", image2="i2.png")
#path = interlace_rows(image1="i1.png", image2="i2.png")

from pixel_scatter import scatter_pixels

path = scatter_pixels(
    image1="/Users/main/Dev/Python/video-editor/scripts/image/in/i12.png",       # imagen base, donde se reemplazan píxeles
    image2="/Users/main/Dev/Python/video-editor/scripts/image/in/i12.png",  # de acá se sacan los colores al azar
    density=0.1,# de acá se sacan los colores al aza# ~10% de los píxeles de image1
    output_path=f"/Users/main/Dev/Python/video-editor/scripts/image/in/{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.png"  
)