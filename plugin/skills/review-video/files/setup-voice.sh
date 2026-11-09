#!/usr/bin/env bash
# One-time setup for free local narration. Safe to run again: it skips what exists.
# Everything goes in $VOICE_HOME (default ~/voice-tools), outside your project.
set -euo pipefail

VOICE_HOME="${VOICE_HOME:-$HOME/voice-tools}"
KOKORO=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
SHERPA=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models

# Download to a temporary name first, so a broken download is never mistaken for a finished one.
get() { [ -f "$2" ] || { curl -sSfL --retry 4 --retry-delay 5 -o "$2.part" "$1" && mv "$2.part" "$2"; }; }

mkdir -p "$VOICE_HOME/kokoro" "$VOICE_HOME/whisper"
[ -x "$VOICE_HOME/venv/bin/python" ] || python3 -m venv "$VOICE_HOME/venv"
# voice.py calls two private functions of kokoro-onnx, so the version is pinned.
"$VOICE_HOME/venv/bin/pip" install -q kokoro-onnx==0.6.1 soundfile onnx numpy sherpa-onnx

cd "$VOICE_HOME/kokoro"
get "$KOKORO/kokoro-v1.0.onnx" kokoro-v1.0.onnx
get "$KOKORO/voices-v1.0.bin" voices-v1.0.bin

cd "$VOICE_HOME/whisper"
if [ ! -d sherpa-onnx-whisper-base.en ]; then
	get "$SHERPA/sherpa-onnx-whisper-base.en.tar.bz2" base.tar.bz2
	tar xjf base.tar.bz2
	rm base.tar.bz2
	# Keep the small int8 model. readback.py does not use the two big ones.
	rm -f sherpa-onnx-whisper-base.en/base.en-encoder.onnx sherpa-onnx-whisper-base.en/base.en-decoder.onnx
fi

echo "ready: $VOICE_HOME/venv/bin/python"
