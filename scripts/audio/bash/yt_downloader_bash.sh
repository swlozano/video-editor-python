#!/bin/bash
yt-dlp -o "~/Descargas/%(title)s.%(ext)s" --cookies-from-browser brave -f "bestvideo[height<=1080]+bestaudio" --merge-output-format mkv "https://www.youtube.com/watch?v=P4hdwRleEIk&t=13s"