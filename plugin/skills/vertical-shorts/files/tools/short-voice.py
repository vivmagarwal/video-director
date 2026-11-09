#!/usr/bin/env python3
"""Write each short's sound as one file, with a 15 ms equal-power crossfade on every splice.

usage: python3 tools/short-voice.py <source video> <short id> <out.wav>

Needs ffmpeg. Standard library only. A tight cut joins two points of the take, and a
hard join can click. Then the composition plays this one file and mutes the footage:
set "voice" on the short in the slate and build again.
"""
import array
import json
import math
import os
import pathlib
import subprocess
import sys
import wave

if len(sys.argv) != 4:
    sys.exit(__doc__)
src, sid, out = sys.argv[1:]
data = next(s for s in json.loads(pathlib.Path("src/shorts.json").read_text()) if s["id"] == sid)
SR = 48000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
take = array.array("h")
take.frombytes(raw[: len(raw) // 2 * 2])
fps = data["fps"]
mix = array.array("h", bytes(2 * round(data["durationInFrames"] / fps * SR)))
half = round(0.0075 * SR)  # half of 15 ms, either side of the splice
for c in data["clips"]:
    a, n = round(c["src"] / fps * SR), round(c["dur"] / fps * SR)
    to = round(c["from"] / fps * SR)
    for k in range(-half, n + half):
        i, j = a + k, to + k
        if not (0 <= i < len(take) and 0 <= j < len(mix)):
            continue
        g = 1.0
        if k < half:
            g = math.sin((k + half) / (2 * half) * math.pi / 2)
        elif k >= n - half:
            g = math.cos((k - n + half) / (2 * half) * math.pi / 2)
        v = mix[j] + take[i] * g
        mix[j] = max(-32768, min(32767, round(v)))
part = out + ".part.wav"
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
with wave.open(part, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(mix.tobytes())
os.replace(part, out)
print(f"wrote {out}: {len(mix) / SR:.2f} s, {len(data['clips'])} pieces")
