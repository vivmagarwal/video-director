#!/usr/bin/env python3
"""Make one short clip that shows colour grades side by side, for the user to choose.

usage: python3 tools/grade-compare.py <video> <start second> [--seconds=6] [--out=out/grades.mp4]

The clip has four panels: A, the original, top left, then B top right, C bottom
left and D bottom right. It prints each letter's ffmpeg filter, so the one the user
picks can go straight into your working-copy command. The grades are only starting
points that suited one interview by a blown-out bright window. Change them to suit
your footage.
"""
import pathlib
import subprocess
import sys

CURVE = "curves=m='0/0 0.15/0.10 0.5/0.46 0.85/0.80 1/0.92'"
GRADES = [
    ("A", "original", "null"),
    ("B", "rich and warm", f"eq=contrast=1.12:saturation=1.18:gamma=0.88,{CURVE},unsharp=5:5:0.5"),
    ("C", "cinematic", f"eq=contrast=1.18:gamma=0.86,{CURVE},colorbalance=rs=-0.05:bs=0.06:rh=0.04:bh=-0.05"),
    ("D", "moody", "eq=contrast=1.25:saturation=0.72:gamma=0.84"),
]

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 2:
    sys.exit(__doc__)
seconds, out = "6", "out/grades.mp4"
for a in sys.argv[1:]:
    if a.startswith("--seconds="):
        seconds = a.split("=", 1)[1]
    if a.startswith("--out="):
        out = a.split("=", 1)[1]
pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)


def build(labels):
    parts = ["[0:v]split=4" + "".join(f"[in{i}]" for i in range(4))]
    for i, (letter, name, grade) in enumerate(GRADES):
        label = f",drawtext=text='{letter}  {name}':x=20:y=20:fontsize=h/14:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10" if labels else ""
        parts.append(f"[in{i}]scale=trunc(iw/4)*2:trunc(ih/4)*2,{grade}{label}[p{i}]")
    parts.append("[p0][p1][p2][p3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[v]")
    return ["ffmpeg", "-v", "error", "-y", "-nostdin", "-ss", args[1], "-t", seconds, "-i", args[0], "-filter_complex", ";".join(parts),
            "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]


labelled = True
r = subprocess.run(build(True), capture_output=True, text=True)
if r.returncode:
    # Some ffmpeg builds have no drawtext, or no font it can find. The panels still work.
    labelled = False
    r = subprocess.run(build(False), capture_output=True, text=True)
if r.returncode:
    sys.exit("ffmpeg could not make the clip: " + r.stderr[-400:])
print(f"saved {out}" + ("" if labelled else ". This ffmpeg could not draw labels, so tell the user which corner is which letter."))
print("A top left, B top right, C bottom left, D bottom right.")
for letter, name, grade in GRADES:
    print(f"{letter} ({name}): {grade}")
