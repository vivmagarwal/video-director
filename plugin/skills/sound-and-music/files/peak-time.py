#!/usr/bin/env python3
"""Say how far into a sound its loudest moment is, so you can place it on a frame.

  python3 peak-time.py whoosh.wav [--fps=30]
"""
import argparse
import array
import os
import subprocess

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
p = argparse.ArgumentParser()
p.add_argument('file')
p.add_argument('--fps', type=float, default=30)
a = p.parse_args()

SR = 48000
raw = subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', a.file, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                     capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
samples = array.array('h', raw)
loudest = max(range(len(samples)), key=lambda i: abs(samples[i]))
at = loudest / SR
print(f'{os.path.basename(a.file)}: {len(samples) / SR:.3f} s long, peak at {at:.3f} s, which is {at * a.fps:.1f} frames in at {a.fps:g} fps')
