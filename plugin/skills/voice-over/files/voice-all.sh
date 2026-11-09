#!/usr/bin/env bash
# Voice every .txt in a folder, skipping any whose .mp3 is already newer.
#   bash voice-all.sh narration af_heart 144 2>&1 | tee voice.log
set -u
FOLDER="$1"; VOICE="$2"; PACE="$3"
PY="${VOICE_HOME:-$HOME/voice-tools}/venv/bin/python"
find "$FOLDER" -name '*.txt' | sort | while read -r f; do
	m="${f%.txt}.mp3"
	if [ -f "$m" ] && [ ! "$f" -nt "$m" ]; then echo "skip $f"; continue; fi
	# </dev/null matters: without it, ffmpeg eats the rest of this list and the loop stops early with no error.
	"$PY" voice.py "$f" --voice="$VOICE" --target="$PACE" </dev/null || echo "CHECK $f"
done
echo "finished $FOLDER"
