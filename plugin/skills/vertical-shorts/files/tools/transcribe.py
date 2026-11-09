#!/usr/bin/env python3
"""Word-timed transcript of a 16 kHz mono wav: Silero finds speech, Parakeet reads it.

  $ASR_HOME/venv/bin/python transcribe.py in.wav out.json

Writes {"segments": [{"start", "end", "text", "words": [{"w", "s", "e"}]}]} in seconds.
"""
import json
import os
import sys
import time

import numpy as np
import sherpa_onnx
import soundfile as sf

wav, out = sys.argv[1:3]
home = os.environ.get('ASR_HOME')
if not home:
    sys.exit('Set ASR_HOME first. The setup script prints the line to run.')
M = f'{home}/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8'
threads = os.cpu_count() or 4

rec = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=f'{M}/encoder.int8.onnx',
    decoder=f'{M}/decoder.int8.onnx',
    joiner=f'{M}/joiner.int8.onnx',
    tokens=f'{M}/tokens.txt',
    model_type='nemo_transducer',
    num_threads=threads,
)

cfg = sherpa_onnx.VadModelConfig()
cfg.silero_vad.model = f'{home}/models/silero_vad.onnx'
cfg.silero_vad.min_silence_duration = 0.35
cfg.silero_vad.min_speech_duration = 0.2
cfg.silero_vad.max_speech_duration = 25
cfg.silero_vad.threshold = 0.45
cfg.sample_rate = 16000
vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=60)

audio, sr = sf.read(wav, dtype='float32')
if sr != 16000:
    sys.exit(f'{wav} is {sr} Hz. Make it 16 kHz mono first with ffmpeg: -ac 1 -ar 16000 -c:a pcm_s16le')
if audio.ndim > 1:
    audio = audio.mean(axis=1)

segments = []
t0 = time.time()


def decode(samples, start):
    # Pad a little either side so the first and last sounds are heard whole.
    pad = int(0.15 * sr)
    lead = min(pad, int(start * sr))
    s0 = int(start * sr) - lead
    chunk = audio[s0 : s0 + lead + len(samples) + pad]
    st = rec.create_stream()
    st.accept_waveform(sr, chunk)
    rec.decode_stream(st)
    r = st.result
    durations = list(getattr(r, 'durations', []) or [])
    base = s0 / sr
    words = []
    for i, (tok, t) in enumerate(zip(r.tokens, r.timestamps)):
        tend = t + (durations[i] if i < len(durations) and durations[i] > 0 else 0.08)
        # This export marks the start of a word with a space, not with the usual
        # marker. Split on the marker alone and a whole segment becomes one "word".
        if tok.startswith(('▁', ' ')) or not words:
            words.append({'w': tok.lstrip('▁ '), 's': base + t, 'e': base + tend})
        else:
            words[-1]['w'] += tok
            words[-1]['e'] = base + tend
    words = [w for w in words if w['w']]
    for i, w in enumerate(words):
        w['s'] = round(w['s'], 3)
        w['e'] = round(max(w['e'], w['s'] + 0.05), 3)
        if i + 1 < len(words):
            w['e'] = round(min(w['e'], words[i + 1]['s']), 3)
    if words:
        segments.append({'start': words[0]['s'], 'end': words[-1]['e'], 'text': r.text.strip(), 'words': words})


win = cfg.silero_vad.window_size
i = 0
while i < len(audio):
    vad.accept_waveform(audio[i : i + win])
    i += win
    while not vad.empty():
        seg = vad.front
        decode(np.array(seg.samples), seg.start / sr)
        vad.pop()
        if segments and len(segments) % 20 == 0:
            print(f"{segments[-1]['end']:.0f} s of {len(audio) / sr:.0f} s, {time.time() - t0:.0f} s elapsed", flush=True)
vad.flush()
while not vad.empty():
    seg = vad.front
    decode(np.array(seg.samples), seg.start / sr)
    vad.pop()

with open(out, 'w', encoding='utf-8') as f:
    json.dump({'segments': segments}, f, indent=1, ensure_ascii=False)
n = sum(len(s['words']) for s in segments)
print(f'done: {len(segments)} segments, {n} words, {len(audio) / sr:.0f} s of audio in {time.time() - t0:.0f} s')
