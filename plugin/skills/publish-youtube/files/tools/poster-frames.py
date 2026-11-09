#!/usr/bin/env python3
"""Shortlist poster frames from a finished film. A person picks; this only narrows it down.

usage: python3 tools/poster-frames.py <working copy or film.mp4> <out dir> [--step=2]

A poster is the one frame someone sees before they press play. A card that is only
type fails, and so does a cut still fading in. So this samples one frame every --step
seconds across the middle 90 % of the file, and throws away frames that are nearly
flat and frames just after a big change in the picture. It ranks what is left by
sharpness and colour, and writes the best three, at least 20 s apart, as poster1.jpg
to poster3.jpg at full size. It cannot see a burned-in caption, or whether a face looks
good: run it on the working copy, which has no captions, and look at all three.

Needs ffmpeg and ffprobe. Standard library only.
"""
import json
import pathlib
import subprocess
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
if len(args) != 2:
    sys.exit(__doc__)
film, out = args[0], pathlib.Path(args[1])
out.mkdir(parents=True, exist_ok=True)
step = float(opts.get("step", 2))
dur = float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", film],
                                      capture_output=True, text=True, check=True).stdout)["format"]["duration"])
W, H = 96, 54
raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", film, "-vf", f"fps=1/{step},scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True, check=True).stdout
n = len(raw) // (W * H * 3)
frames = [raw[i * W * H * 3:(i + 1) * W * H * 3] for i in range(n)]


def luma(f):
    return [(f[i] * 299 + f[i + 1] * 587 + f[i + 2] * 114) // 1000 for i in range(0, len(f), 3)]


rows = []
prev = None
for k, f in enumerate(frames):
    t = k * step + step / 2
    y = luma(f)
    change = sum(abs(a - b) for a, b in zip(y, prev)) / len(y) if prev else 0
    prev = y
    if not 0.05 * dur <= t <= 0.95 * dur:
        continue
    mean = sum(y) / len(y)
    spread = (sum((v - mean) ** 2 for v in y) / len(y)) ** 0.5
    edge = sum(abs(y[i] - y[i + 1]) for i in range(len(y) - 1) if (i + 1) % W) / len(y)
    colour = sum(max(f[i:i + 3]) - min(f[i:i + 3]) for i in range(0, len(f), 3)) / (W * H)
    if spread < 22:
        why = "flat: a card or a fade"
    elif colour < 12 and spread > 90:
        why = "looks like type on a plain ground"
    elif change > 28:
        why = "just after a big change"
    else:
        why = ""
    rows.append({"t": t, "score": edge * 2 + colour * 0.4 + min(spread, 70) * 0.3, "why": why, "edge": edge, "colour": colour})

keep = sorted((r for r in rows if not r["why"]), key=lambda r: -r["score"])
picked = []
for r in keep:
    if all(abs(r["t"] - p["t"]) >= 20 for p in picked):
        picked.append(r)
    if len(picked) == 3:
        break
reasons = {}
for r in rows:
    if r["why"]:
        reasons[r["why"]] = reasons.get(r["why"], 0) + 1
print(f"{len(rows)} frames sampled; thrown away: " + (", ".join(f"{v} {k}" for k, v in reasons.items()) or "none"))
for i, r in enumerate(picked, 1):
    p = out / f"poster{i}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{r['t']:.2f}", "-i", film, "-frames:v", "1", "-q:v", "2", str(p)], check=True)
    print(f"{p}  at {int(r['t'] // 60)}:{r['t'] % 60:05.2f}  sharpness {r['edge']:.1f}, colour {r['colour']:.0f}")
if not picked:
    print("nothing passed; look through the film yourself")
