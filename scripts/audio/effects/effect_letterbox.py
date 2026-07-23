from moviepy import VideoFileClip, ColorClip, CompositeVideoClip

clip = VideoFileClip("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_046.mp4")

# Altura de las barras negras (ajusta según el look que quieras)
alto_barra = int(clip.h * 0.4 )  # 12% de la altura del video, por ejemplo

barra_superior = (ColorClip(size=(clip.w, alto_barra), color=(0, 0, 0))
                   .with_duration(clip.duration)
                   .with_position(("center", "top")))

barra_inferior = (ColorClip(size=(clip.w, alto_barra), color=(0, 0, 0))
                   .with_duration(clip.duration)
                   .with_position(("center", "bottom")))

final = CompositeVideoClip([clip, barra_superior, barra_inferior])
final.write_videofile("/Users/main/Downloads/Askate_shorts/cuts/v2/effects/clip_letterbox_046.mp4")