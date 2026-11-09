#!/usr/bin/env python3
"""Measure a generated background before you put anything on it.

    python3 measure-image.py public/bg/room.png [--frame=1920x1080] [--column=0.5]

Prints its size, what 'cover' does to it in your frame, how much of it is near black,
and the runs of flat colour down one column (fractions of the height), which is where
the wall, the floor and the furniture lines are. Needs Pillow: pip install pillow
"""
import sys

from PIL import Image


def option(name, default):
    for arg in sys.argv[2:]:
        if arg.startswith(f'--{name}='):
            return arg.split('=', 1)[1]
    return default


image = Image.open(sys.argv[1]).convert('RGB')
W, H = image.size
fw, fh = map(int, option('frame', '1920x1080').split('x'))
scale = max(fw / W, fh / H)
print(f'size: {W}x{H}, aspect {W / H:.4f} (frame {fw / fh:.4f})')
print(f'objectFit cover: scale {scale:.4f}, loses {(W * scale - fw) / 2:.1f} px each side and {(H * scale - fh) / 2:.1f} px top and bottom')
if scale >= 1:
    print('note: this image is smaller than the frame, so it will look soft at any size.')
else:
    print(f'note: a slow push-in stays sharp up to a scale of about {1 / scale:.2f}.')

pixels = image.load()
sample = [pixels[x, y] for y in range(0, H, 4) for x in range(0, W, 4)]
dark = sum(1 for p in sample if max(p) < 30)
print(f'near-black pixels: {100 * dark / len(sample):.2f}%')

x = min(W - 1, int(float(option('column', '0.5')) * W))
print(f'flat runs down column x={x} ({x / W:.2f} of the width):')
previous, start = pixels[x, 0], 0
for y in range(1, H):
    colour = pixels[x, y]
    if max(abs(a - b) for a, b in zip(colour, previous)) > 16:
        if y - start > 8:  # ignore soft edges and thin lines
            print(f'  {start / H:.3f} to {(y - 1) / H:.3f}  rgb{previous}')
        previous, start = colour, y
print(f'  {start / H:.3f} to {(H - 1) / H:.3f}  rgb{previous}')
