#!/usr/bin/env bash
# Word-timed transcription with no paid API and no Hugging Face.
# The Python package comes from PyPI. The models come from GitHub releases.
#
#   bash setup-transcription.sh             Parakeet: word timings (482 MB download)
#   bash setup-transcription.sh --whisper   adds Whisper turbo: a second reading (564 MB download)
#
# It installs to $ASR_HOME if you set it, else /opt/asr if you may write there,
# else ~/asr. It is safe to run again: it skips what is already there.
set -euo pipefail

if [ -z "${ASR_HOME:-}" ]; then
	if mkdir -p /opt/asr 2>/dev/null && [ -w /opt/asr ]; then
		ASR_HOME=/opt/asr
	else
		ASR_HOME="$HOME/asr"
	fi
fi
RELEASE=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models

# Download to a temporary name first, so a broken download is never mistaken for a finished one.
get() { [ -f "$2" ] || { curl -sSfL --retry 4 --retry-delay 5 -o "$2.part" "$1" && mv "$2.part" "$2"; }; }
model() {
	[ -d "$1" ] && return 0
	get "$RELEASE/$1.tar.bz2" "$1.tar.bz2"
	tar xjf "$1.tar.bz2"
	rm "$1.tar.bz2"
}

mkdir -p "$ASR_HOME/models"
[ -x "$ASR_HOME/venv/bin/python" ] || python3 -m venv "$ASR_HOME/venv"
"$ASR_HOME/venv/bin/pip" install -q sherpa-onnx numpy soundfile

cd "$ASR_HOME/models"
get "$RELEASE/silero_vad.onnx" silero_vad.onnx
model sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8
if [ "${1:-}" = "--whisper" ]; then
	model sherpa-onnx-whisper-turbo
fi

echo "ready. Run this in each new shell: export ASR_HOME=$ASR_HOME"
