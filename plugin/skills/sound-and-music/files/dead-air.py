#!/usr/bin/env python3
"""Find dead air in a finished file.

  python dead-air.py film.mp4 [--fps=30] [--longest-pause=1.5]

Reports stretches of true silence longer than 20 frames (they read as a fault), and
quiet stretches longer than --longest-pause seconds (ask if the picture earns them).
Exit 1 if it found true silence longer than 20 frames, else 0.
"""
import argparse
import os
import re
import subprocess
import sys

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
p = argparse.ArgumentParser()
p.add_argument('file')
p.add_argument('--fps', type=float, default=30)
p.add_argument('--longest-pause', type=float, default=1.5)
a = p.parse_args()


def silences(noise, minimum):
    err = subprocess.run([FFMPEG, '-nostdin', '-hide_banner', '-i', a.file, '-vn', '-af',
                          f'silencedetect=n={noise}:d={minimum}', '-f', 'null', '-'],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
    h, m, sec = re.search(r'Duration: (\d+):(\d+):([\d.]+)', err).groups()
    length = int(h) * 3600 + int(m) * 60 + float(sec)
    starts = [max(float(x), 0) for x in re.findall(r'silence_start: (-?[\d.]+)', err)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)] + [length]
    rows = list(zip(starts, ends))
    # A short silence at the very end is a tail, not a hole in the film.
    return [(s, e) for s, e in rows if not (e > length - 0.2 and e - s <= 2)]


def show(rows):
    for s, e in rows:
        print(f'  {s:8.2f} s to {e:.2f} s ({e - s:.2f} s)')


frames20 = 20 / a.fps
true_silence = silences('-80dB', frames20)
quiet = silences('-45dB', a.longest_pause)
print(f'True silence (under -80 dB) longer than 20 frames ({frames20:.2f} s): {len(true_silence)}')
show(true_silence)
print(f'Quiet stretches (under -45 dB) longer than {a.longest_pause} s: {len(quiet)}')
show(quiet)
sys.exit(1 if true_silence else 0)
