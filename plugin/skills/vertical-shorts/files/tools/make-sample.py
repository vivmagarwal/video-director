#!/usr/bin/env python3
"""Make a small practice recording and its transcript, so the whole method can be
tried in a few minutes, with no real footage and no speech model.

usage: python3 tools/make-sample.py     (from the project folder)

Writes raw/take.mp4 (40 s, 1280x720, 30 fps, a keyframe only every 30 s, like a
webcam file; the picture shows its own running clock, so you can see which moment
of the take each frame came from), raw/raw16k.wav and edit/transcript.json.
The "voice" is tone bursts, one per word. One burst, at 0:26, is not in the
transcript: it stands for speech the recogniser never heard.
"""
import json
import math
import os
import random
import struct
import subprocess
import wave

TEXT = [
    ("This is the first sentence of the practice talk.", 0.9),
    ("Um now we say what the talk is about.", 2.2),
    ("We say it badly and we stop", 0.7),
    ("We say it well and we go on.", 1.1),
    ("Three things matter here.", 0.5),
    ("Clear words,", 0.4),
    ("a steady picture,", 0.4),
    ("and sound you can trust.", 2.6),
    ("A cut must never lose a word.", 1.2),
    ("LOST", 1.0),
    ("Now the talk turns to its last idea.", 0.9),
    ("That idea is the one to remember.", 1.8),
]
SR = 48000
random.seed(4)
os.makedirs("raw", exist_ok=True)
os.makedirs("edit", exist_ok=True)
pcm, segs, t = [], [], 0.6


def silence(sec):
    pcm.extend([0] * int(sec * SR))


silence(t)
for line, pause in TEXT:
    words = []
    start = t
    for w in (["(unheard"] + ["burst)"] if line == "LOST" else line.split()):
        d = 0.14 + 0.03 * len(w)
        f = random.choice([180, 210, 240, 270, 300])
        for i in range(int(d * SR)):
            env = min(1, i / 240, (int(d * SR) - i) / 240)
            pcm.append(int(9000 * env * math.sin(2 * math.pi * f * i / SR)))
        words.append({"w": w, "s": round(t, 3), "e": round(t + d, 3)})
        t += d
        silence(0.06)
        t += 0.06
    if line != "LOST":
        segs.append({"start": start, "end": words[-1]["e"], "text": line, "words": words})
    silence(pause)
    t += pause
silence(max(0.0, 40 - t))
with wave.open("raw/voice.wav", "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=40", "-i", "raw/voice.wav",
                "-c:v", "libx264", "-preset", "veryfast", "-g", "900", "-keyint_min", "900", "-sc_threshold", "0", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-shortest", "raw/take.mp4"], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "raw/take.mp4", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "raw/raw16k.wav"], check=True)
json.dump({"segments": segs}, open("edit/transcript.json", "w"), indent=1)
os.remove("raw/voice.wav")
for s in segs:
    print(f"{int(s['start'] // 60)}:{s['start'] % 60:05.2f}  {s['text']}")
print("wrote raw/take.mp4, raw/raw16k.wav, edit/transcript.json")
