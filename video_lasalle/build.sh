#!/usr/bin/env bash
# Regenera el vídeo completo. Requisitos: pip install kokoro-onnx soundfile numpy; Playwright+Chromium; ffmpeg.
# MODELOS debe contener kokoro.onnx y voices.bin (github.com/thewh1teagle/kokoro-onnx/releases, model-files-v1.0)
set -euo pipefail
cd "$(dirname "$0")"
MODELOS=${MODELOS:?indica la carpeta de modelos}; BUILD=${BUILD:-/tmp/lasalle_build}; mkdir -p "$BUILD"
python3 voces.py "$MODELOS" "$BUILD"          # 1. voces de Lucía y Marta + línea de tiempo
cp "$BUILD/timeline.js" .
node render.js "$BUILD" video                 # 2. animación fotograma a fotograma
python3 audio.py "$BUILD"                     # 3. música, efectos y mezcla
ffmpeg -y -loglevel error -i "$BUILD/video_mudo.mp4" -i "$BUILD/audio_final.wav" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -shortest -movflags +faststart San_Juan_Bautista_de_La_Salle.mp4
