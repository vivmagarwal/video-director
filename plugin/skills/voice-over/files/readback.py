#!/usr/bin/env python3
"""Read an audio file back with offline Whisper and compare it to its script.

  ~/voice-tools/venv/bin/python readback.py script.mp3 script.txt     (the .txt is optional)

This is how a machine with no ears "listens". It prints what it heard and every
place that differs from the script. No prompt is given to Whisper on purpose:
with a name in the prompt, Whisper writes the name whatever was said.
"""
import difflib
import os
import re
import subprocess
import sys

import numpy as np
import sherpa_onnx

MODEL = os.path.join(os.environ.get('VOICE_HOME', os.path.expanduser('~/voice-tools')), 'whisper', 'sherpa-onnx-whisper-base.en')
FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
SR = 16000
MAX_WINDOW = 28 * SR  # Whisper takes at most 30 s at a time


def windows(a):
    """Yield pieces under 28 s, cut at the quietest moment in the last 6 s of each."""
    i = 0
    while len(a) - i > MAX_WINDOW:
        tail = a[i + MAX_WINDOW - 6 * SR : i + MAX_WINDOW]
        hop = SR // 10
        levels = [np.abs(tail[j : j + hop]).mean() for j in range(0, len(tail) - hop, hop)]
        cut = i + MAX_WINDOW - 6 * SR + hop * int(np.argmin(levels))
        yield a[i:cut]
        i = cut
    yield a[i:]


def words(text):
    text = re.sub(r'\{[^}\s]+\}', '', text).lower().replace('’', "'")
    return re.findall(r"[a-z0-9']+", text)


path = sys.argv[1]
if not os.path.isdir(MODEL):
    sys.exit(f'No Whisper model at {MODEL}. Run setup-voice.sh. A container rebuild can wipe this folder.')
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f'{MODEL}/base.en-encoder.int8.onnx',
    decoder=f'{MODEL}/base.en-decoder.int8.onnx',
    tokens=f'{MODEL}/base.en-tokens.txt',
    num_threads=os.cpu_count() or 2,
)
pcm = subprocess.run(
    [FFMPEG, '-nostdin', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
    capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
heard = []
for piece in windows(audio):
    s = rec.create_stream()
    s.accept_waveform(SR, piece)
    rec.decode_stream(s)
    heard.append(s.result.text.strip())
heard = ' '.join(heard)
print(f'HEARD: {heard}')
if len(sys.argv) > 2:
    with open(sys.argv[2], encoding='utf-8') as f:
        want = words(f.read())
    got = words(heard)
    sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
    diffs = [(' '.join(want[i1:i2]), ' '.join(got[j1:j2])) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']
    print(f'MATCH: {sm.ratio() * 100:.1f}% of {len(want)} script words')
    for w, g in diffs:
        print(f'  script: {w or "(nothing)":30} heard: {g or "(nothing)"}')
    if not diffs:
        print('  no differences')
