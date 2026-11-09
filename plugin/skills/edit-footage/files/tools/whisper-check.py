#!/usr/bin/env python3
"""Second opinion: Whisper turbo reads the same speech as the Parakeet transcript.

  $ASR_HOME/venv/bin/python whisper-check.py in.wav transcript.json out.json

Writes a list of {"start", "end", "whisper", "parakeet"} in chunks of about 25 s,
and prints the chunks where the two disagree on the words.
"""
import json
import os
import re
import sys
import time

import sherpa_onnx
import soundfile as sf

wav, transcript, out = sys.argv[1:4]
home = os.environ.get('ASR_HOME')
if not home:
    sys.exit('Set ASR_HOME first. The setup script prints the line to run.')
M = f'{home}/models/sherpa-onnx-whisper-turbo'
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f'{M}/turbo-encoder.int8.onnx',
    decoder=f'{M}/turbo-decoder.int8.onnx',
    tokens=f'{M}/turbo-tokens.txt',
    language='en',
    task='transcribe',
    num_threads=os.cpu_count() or 4,
)
audio, sr = sf.read(wav, dtype='float32')
with open(transcript, encoding='utf-8') as f:
    segments = json.load(f)['segments']

chunks, cur = [], []
for s in segments:
    if cur and s['end'] - cur[0]['start'] > 24:
        chunks.append(cur)
        cur = []
    cur.append(s)
if cur:
    chunks.append(cur)


def plain(text):
    return re.findall(r"[a-z0-9']+", text.lower().replace('’', "'"))


res = []
t0 = time.time()
for i, c in enumerate(chunks):
    a, b = max(0, c[0]['start'] - 0.2), c[-1]['end'] + 0.3
    st = rec.create_stream()
    st.accept_waveform(sr, audio[int(a * sr) : int(b * sr)])
    rec.decode_stream(st)
    row = {'start': a, 'end': b, 'whisper': st.result.text.strip(), 'parakeet': ' '.join(s['text'] for s in c)}
    res.append(row)
    print(f'{i + 1}/{len(chunks)}, {time.time() - t0:.0f} s elapsed', flush=True)
    if plain(row['whisper']) != plain(row['parakeet']):
        print(f"  {a:.1f} s  Parakeet: {row['parakeet']}\n  {' ' * len(f'{a:.1f}')}    Whisper:  {row['whisper']}", flush=True)
with open(out, 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print('done')
