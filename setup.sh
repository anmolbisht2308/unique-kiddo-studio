#!/usr/bin/env bash
# One-time setup in a fresh session: downloads the voice model, espeak and emoji artwork into assets/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p assets out
pip install --break-system-packages -q onnxruntime numpy pillow >/dev/null 2>&1 || true
if [ ! -f assets/kokoro-v1.0.onnx ]; then
  for f in kokoro-v1.0.onnx voices-v1.0.bin; do
    curl -sSL -o "assets/$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
  done
fi
if [ ! -d assets/piper ]; then
  curl -sSL -o /tmp/piper.tgz "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
  tar xzf /tmp/piper.tgz -C assets && rm /tmp/piper.tgz
fi
if [ ! -d assets/noto/2D/png/512 ]; then
  rm -rf assets/noto
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/googlefonts/noto-emoji assets/noto
  git -C assets/noto sparse-checkout set 2D/png/512
fi
which ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
python3 -c "import sys; sys.path.insert(0,'engine'); import tts; print('setup ok')"
