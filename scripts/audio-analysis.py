import librosa
import matplotlib.pyplot as plt

from moviepy import VideoFileClip, concatenate_videoclips
from moviepy.video.fx import BlackAndWhite


AUDIO_PATH = 'proyects/test/audio/beatBox.wav'
VIDEO_PATH = 'proyects/test/video/short.mp4'
VIDEO_OUTH = 'proyects/test/out/output.mp4'
VIDEO_EDIT_OUTH = 'proyects/test/out/output_edit.mp4'

print("loading audio...")
y, sr = librosa.load(AUDIO_PATH, sr=None)

tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
# Convierte los frames a tiempos en segundos
beat_times = librosa.frames_to_time(beat_frames, sr=sr)

video = VideoFileClip(VIDEO_PATH)
clips = []

for i in range(len(beat_times) - 1):
    start = beat_times[i]
    end = beat_times[i + 1]
    
    # Evita que el corte se pase de la duración del video
    if start >= video.duration:
        break
    end = min(end, video.duration)
    
    subclip = video.subclipped(start, end)
    
    # Alterna: pares en blanco y negro, impares en color
    if i % 2 == 0:
        subclip = subclip.with_effects([BlackAndWhite()])
    
    clips.append(subclip)

final = concatenate_videoclips(clips)
final.write_videofile(VIDEO_OUTH)

from moviepy import VideoFileClip, AudioFileClip

video = VideoFileClip(VIDEO_OUTH)
audio = AudioFileClip(AUDIO_PATH)

video_con_audio = video.with_audio(audio)
video_con_audio.write_videofile(VIDEO_EDIT_OUTH)






