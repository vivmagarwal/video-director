#!/usr/bin/env python3
"""Prove a cut lost no speech. Run it with the Python that transcribe.py uses.

  $ASR_HOME/venv/bin/python check-cut.py raw16k.wav transcript.json keep.json

keep.json is a list of [start, end] in seconds: the parts of raw16k.wav the cut keeps.
Two checks, because each catches what the other misses:
  1. Sound the cut throws away: compare non-silent stretches against keep.json.
     This finds speech the recogniser never wrote down.
  2. Words: splice the kept audio, transcribe it again, and diff it against what
     the transcript says should be there. This finds clipped words.
Exit 0 means both are clean; exit 1 means read the lines it printed.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

raw, transcript, keep_file = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
NOISE, MIN_SILENCE, MIN_LOST = '-35dB', 0.20, 0.15
with open(keep_file) as f:
    keep = sorted(json.load(f))
with open(transcript, encoding='utf-8') as f:
    segments = json.load(f)['segments']
audio, sr = sf.read(raw, dtype='float32')
length = len(audio) / sr
bad = 0

# Check 1: sound outside the kept ranges.
log = subprocess.run(
    [FFMPEG, '-nostdin', '-hide_banner', '-i', raw, '-af', f'silencedetect=n={NOISE}:d={MIN_SILENCE}', '-f', 'null', '-'],
    capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
starts = [float(x) for x in re.findall(r'silence_start: (-?[\d.]+)', log)]
ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
sounds, t = [], 0.0
for a, b in zip(starts, ends + [length]):
    if a > t:
        sounds.append((t, max(a, 0)))
    t = b
if t < length:
    sounds.append((t, length))
all_words = [w for s in segments for w in s['words']]
for a, b in sounds:
    lost, t = [], a
    for k0, k1 in keep:
        if k1 <= t or k0 >= b:
            continue
        if k0 > t:
            lost.append((t, k0))
        t = max(t, k1)
    if t < b:
        lost.append((t, b))
    for x, y in lost:
        if y - x < MIN_LOST:
            continue
        named = ' '.join(w['w'] for w in all_words if w['s'] < y and w['e'] > x)
        bad += 1
        print(f'SOUND DROPPED {x:8.2f} to {y:8.2f} s ({y - x:.2f} s). Transcript there: {named or "(nothing: the recogniser missed it, listen here)"}')
print(f'check 1: {len(sounds)} stretches of sound compared with {len(keep)} kept ranges')

# Check 2: re-transcribe the spliced audio and diff the words.
expected = [w['w'] for w in all_words if any(k0 <= (w['s'] + w['e']) / 2 < k1 for k0, k1 in keep)]
with tempfile.TemporaryDirectory() as tmp:
    cut_wav, cut_json = os.path.join(tmp, 'cut.wav'), os.path.join(tmp, 'cut.json')
    sf.write(cut_wav, np.concatenate([audio[int(a * sr) : int(b * sr)] for a, b in keep]), sr, subtype='PCM_16')
    subprocess.run([sys.executable, os.path.join(HERE, 'transcribe.py'), cut_wav, cut_json],
                   check=True, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    with open(cut_json, encoding='utf-8') as f:
        heard = [w['w'] for s in json.load(f)['segments'] for w in s['words']]


def plain(ws):
    return [re.sub(r"[^a-z0-9']", '', w.lower().replace('’', "'")) for w in ws]


want, got = plain(expected), plain(heard)
sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag != 'equal':
        bad += 1
        print(f"WORDS DIFFER expected: {' '.join(want[i1:i2]) or '(nothing)'}  |  heard in the cut: {' '.join(got[j1:j2]) or '(nothing)'}")
print(f'check 2: {len(want)} expected words, {len(got)} heard in the cut')
sys.exit(1 if bad else 0)
