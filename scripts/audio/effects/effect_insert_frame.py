from moviepy import VideoFileClip, ImageClip, concatenate_videoclips

clip = VideoFileClip("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_046.mp4")

momento = 1.6          # segundo donde se inserta la imagen
duracion_imagen = 0.1   # cuánto tiempo se muestra la imagen

antes = clip.subclipped(0, momento)
despues = clip.subclipped(momento, clip.duration)

# Imagen externa, ajustada al mismo tamaño que el video
imagen = (ImageClip("/Users/main/Downloads/Askate_shorts/images/gol.png")
          .with_duration(duracion_imagen)
          .resized(clip.size))  # importante: que coincida con el tamaño del video

final = concatenate_videoclips([antes, imagen, despues])
final.write_videofile("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_insert4_046.mp4")