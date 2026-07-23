from moviepy import VideoFileClip, ColorClip, CompositeVideoClip
from moviepy.video.fx import FadeOut

clip = VideoFileClip("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_011.mp4")
flashes = []

tiempos = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8]  # momentos donde aparece el flash
for t in tiempos:
    f = (ColorClip(size=clip.size, color=(220, 20, 60), duration=0.1)
          .with_start(t)
          .with_opacity(0.6)     
          .with_effects([FadeOut(0.1)]))
    flashes.append(f)

final = CompositeVideoClip([clip] + flashes)
final.write_videofile("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_0011.mp4")