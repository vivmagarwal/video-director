#!/usr/bin/env python3
"""How far does a generated clip's picture slide, compared with its first frame?

    python3 clip-drift.py clip.mp4 [--points=6] [--search=12]

It compares only the outer border of the frame, where the subject usually is not, and
prints the best-fitting shift in whole pixels at several moments. A locked camera reads 0.
Anything you lay on top of the clip will appear to slide by this much.
Needs ffmpeg and ffprobe (or `npx remotion ffprobe`), and numpy: pip install numpy
"""
import json
import shutil
import subprocess
import sys

import numpy as np


def option(name, default):
    for arg in sys.argv[2:]:
        if arg.startswith(f'--{name}='):
            return int(arg.split('=', 1)[1])
    return default


path = sys.argv[1]
points = option('points', 6)
search = option('search', 12)
probe = ['ffprobe'] if shutil.which('ffprobe') else ['npx', 'remotion', 'ffprobe']
info = json.loads(subprocess.run(
    [*probe, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,duration', '-of', 'json', path],
    capture_output=True, text=True, check=True,
).stdout)['streams'][0]
W, H, length = int(info['width']), int(info['height']), float(info['duration'])


def frame_at(seconds):
    raw = subprocess.run(
        ['ffmpeg', '-v', 'error', '-ss', str(seconds), '-i', path, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W).astype(np.float32)


first = frame_at(0)
band = max(search + 8, int(0.08 * min(W, H)))
mask = np.zeros((H, W), bool)
mask[search:band + search, search:W - search] = True
mask[H - band - search:H - search, search:W - search] = True
mask[search:H - search, search:band + search] = True
mask[search:H - search, W - band - search:W - search] = True
ys, xs = np.nonzero(mask)
ys, xs = ys[::3], xs[::3]  # every third point is enough, and much faster
base = first[ys, xs]

worst = 0.0
print(f'{W}x{H}, {length:.2f} s. Border shift from the first frame, in pixels:')
for i in range(1, points + 1):
    t = max(0.0, length * i / points - 0.1)
    frame = frame_at(t)
    best = (float('inf'), 0, 0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            error = float(np.abs(frame[ys + dy, xs + dx] - base).mean())
            if error < best[0]:
                best = (error, dx, dy)
    size = (best[1] ** 2 + best[2] ** 2) ** 0.5
    worst = max(worst, size)
    print(f'  {t:6.2f} s  dx {best[1]:+3d}  dy {best[2]:+3d}  ({size:.1f} px), border difference left {best[0]:.1f} of 255')
print(f'largest shift: {worst:.1f} px' + (f' (at the search limit of {search}: pass a larger --search)' if worst >= search else ''))
