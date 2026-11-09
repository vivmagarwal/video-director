#!/usr/bin/env python3
"""Check word timings against the sound they caption.

  python check-drift.py voice.captions.json voice.mp3 [--offset-ms=0] [--tolerance=0.25]

Every pause in the captions should match a pause in the sound: the word after the
pause should start where the sound comes back. Run it on the voice alone, or on a
render with no music, because music fills the pauses it needs to see.
--offset-ms says how far into the file the voice starts.
Exit 0 means no drift above the tolerance. Exit 1 means some, or no pauses to compare.
"""
import argparse
import json
import os
import re
import subprocess
import sys

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
p = argparse.ArgumentParser()
p.add_argument('captions')
p.add_argument('audio')
p.add_argument('--offset-ms', type=float, default=0)
p.add_argument('--tolerance', type=float, default=0.25, help='seconds')
p.add_argument('--noise', default='-38dB', help='sound quieter than this counts as a pause')
p.add_argument('--min-pause', type=float, default=0.22, help='seconds')
a = p.parse_args()

with open(a.captions, encoding='utf-8') as f:
    caps = json.load(f)
log = subprocess.run(
    [FFMPEG, '-nostdin', '-hide_banner', '-i', a.audio, '-vn', '-af',
     f'silencedetect=n={a.noise}:d={a.min_pause}', '-f', 'null', '-'],
    capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
sound_back = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]

off = a.offset_ms / 1000
rows, unmatched = [], 0
for before, word in zip(caps, caps[1:]):
    if (word['startMs'] - before['endMs']) / 1000 < a.min_pause:
        continue
    start = word['startMs'] / 1000 + off
    back = min(sound_back, key=lambda t: abs(t - start)) if sound_back else None
    if back is None or abs(start - back) > 1.5:
        unmatched += 1  # no pause in the sound anywhere near this pause in the captions
    else:
        rows.append((start - back, start, word['text'].strip()))
if unmatched:
    print(f'{unmatched} pauses in the captions have no pause in the sound nearby. Music or room noise can hide them: '
          'use the voice alone, or a louder --noise such as -30dB.')
if len(rows) < unmatched or not rows:
    print('Too few pauses matched to judge drift.')
    sys.exit(1)
gaps = sorted(r[0] for r in rows)
middle = gaps[len(gaps) // 2]
print(f'{len(rows)} pauses compared. Word starts {middle:+.3f} s from the sound (middle value); range {gaps[0]:+.3f} to {gaps[-1]:+.3f} s.')
for gap, start, word in sorted(rows, key=lambda r: -abs(r[0]))[:5]:
    print(f'  "{word}" at {start:7.2f} s: {gap:+.3f} s from where the sound returns')
sys.exit(1 if max(abs(g) for g in gaps) > a.tolerance else 0)
