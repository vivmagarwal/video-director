#!/usr/bin/env python3
"""Read a voice file back in another language with Whisper turbo, and compare it to its script.

  ~/voice-tools/venv/bin/python readback-language.py script.mp3 script.txt --lang=es

readback.py uses an English-only model. This one needs the bigger turbo model.
"""
import argparse
import difflib
import os
import re
import subprocess
import sys

import numpy as np
import sherpa_onnx

p = argparse.ArgumentParser()
p.add_argument('audio')
p.add_argument('script')
p.add_argument('--lang', required=True, help='a two-letter code, such as es or fr')
a = p.parse_args()

MODEL = os.path.join(os.environ.get('VOICE_HOME', os.path.expanduser('~/voice-tools')), 'whisper', 'sherpa-onnx-whisper-turbo')
if not os.path.isdir(MODEL):
    sys.exit(f'No turbo model at {MODEL}. Download it first.')
SR = 16000
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f'{MODEL}/turbo-encoder.int8.onnx',
    decoder=f'{MODEL}/turbo-decoder.int8.onnx',
    tokens=f'{MODEL}/turbo-tokens.txt',
    language=a.lang,
    task='transcribe',
    num_threads=os.cpu_count() or 2,
)
pcm = subprocess.run([os.environ.get('FFMPEG', 'ffmpeg'), '-nostdin', '-v', 'error', '-i', a.audio, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                     capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
heard = []
for i in range(0, len(audio), 28 * SR):  # Whisper takes at most 30 s at a time. A word on a cut may read wrong.
    s = rec.create_stream()
    s.accept_waveform(SR, audio[i : i + 28 * SR])
    rec.decode_stream(s)
    heard.append(s.result.text.strip())
heard = ' '.join(heard)
print(f'HEARD: {heard}')


def words(text):
    return re.findall(r"\w+", re.sub(r'\{[^}\s]+\}', '', text).lower())


with open(a.script, encoding='utf-8') as f:
    want = words(f.read())
got = words(heard)
sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
print(f'MATCH: {sm.ratio() * 100:.1f}% of {len(want)} script words')
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag != 'equal':
        print(f"  script: {' '.join(want[i1:i2]) or '(nothing)':30} heard: {' '.join(got[j1:j2]) or '(nothing)'}")
