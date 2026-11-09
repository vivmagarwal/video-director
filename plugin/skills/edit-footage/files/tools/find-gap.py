#!/usr/bin/env python3
"""Find the real quiet gap near a proposed cut, 10 ms at a time.

usage: python3 tools/find-gap.py <audio or video> <seconds> [--around=0.6]

Prints the loudness of each 10 ms slice around that time, then the longest quiet
stretch, which is where a cut belongs. Use it when two words touch, or when a
speech recogniser's timings and the build's margins disagree. It needs ffmpeg.
"""
import array
import math
import subprocess
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 2:
    sys.exit(__doc__)
around = 0.6
for a in sys.argv[1:]:
    if a.startswith("--around="):
        around = float(a.split("=", 1)[1])
path, at = args[0], float(args[1])
start = max(0.0, at - around)
RATE, STEP = 16000, 160  # 160 samples at 16 kHz is 10 ms
raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{start:.3f}", "-t", f"{2 * around:.3f}", "-i", path,
     "-map", "0:a:0", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
    capture_output=True,
)
if raw.returncode or not raw.stdout:
    sys.exit("ffmpeg could not read sound from that file: " + raw.stderr.decode()[:300])
pcm = array.array("h")
pcm.frombytes(raw.stdout[: len(raw.stdout) // 2 * 2])
if sys.byteorder == "big":
    pcm.byteswap()

levels = []
for i in range(0, len(pcm) - STEP + 1, STEP):
    rms = math.sqrt(sum(s * s for s in pcm[i : i + STEP]) / STEP)
    levels.append(20 * math.log10(max(rms, 1) / 32768))
if not levels:
    sys.exit("too little sound there")

floor = min(levels)
quiet = floor + 10
best, run = (0, 0), None
for i, db in enumerate(levels + [0.0]):
    if db <= quiet:
        run = i if run is None else run
    elif run is not None:
        if i - run > best[1] - best[0]:
            best = (run, i)
        run = None
for i, db in enumerate(levels):
    t = start + i * 0.01
    mark = " <-- quiet" if best[0] <= i < best[1] else ""
    print(f"{t:8.2f} s {db:6.1f} dB {'#' * max(0, int((db + 70) / 2))}{mark}")
a, b = start + best[0] * 0.01, start + best[1] * 0.01
print(f"quietest stretch: {a:.2f} to {b:.2f} s ({(b - a) * 1000:.0f} ms), floor {floor:.1f} dB. Cut near {(a + b) / 2:.2f} s.")
