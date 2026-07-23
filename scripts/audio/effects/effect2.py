"""
Aquí el flash se sobrepone sobre el video, no lo interrumpe — como cuando algo "brilla" en pantalla:
"""

from moviepy import VideoFileClip, ColorClip, CompositeVideoClip
from moviepy.video.fx import FadeOut

clip = VideoFileClip("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_011.mp4")

# Flash blanco que aparece en el segundo 3, dura 0.3s
flash = (ColorClip(size=clip.size, color=(255, 255, 255), duration=0.3)
          .with_start(3)
          .with_effects([FadeOut(0.3)])
          .with_opacity(1))

final = CompositeVideoClip([clip, flash])
final.write_videofile("/Users/main/Downloads/Askate_shorts/cuts/v2/clip_00011.mp4")