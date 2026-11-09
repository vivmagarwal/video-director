#!/usr/bin/env python3
"""Word captions for any voice file, on your own machine, with no paid API.

    "$ASR_HOME/venv/bin/python" words-to-captions.py public/demo/n1.mp3 public/demo/n1.captions.json

Writes [{"text": "Word", "startMs": 120, "endMs": 410, ...}, {"text": " next", ...}]. Every word
after the first starts with a space, as @remotion/captions expects.
Needs ffmpeg on PATH, and ASR_HOME pointing at what setup-transcription.sh installed.
"""
import json
import os
import subprocess
import sys

import numpy as np
import sherpa_onnx

source, out = sys.argv[1:3]
ASR = os.environ.get('ASR_HOME')
if not ASR:
    sys.exit('Set ASR_HOME first. The setup script prints the line to run.')
MODEL = f'{ASR}/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8'
RATE = 16000

pcm = subprocess.run(
    ['ffmpeg', '-v', 'error', '-i', source, '-f', 's16le', '-ac', '1', '-ar', str(RATE), '-'],
    capture_output=True, check=True,
).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768

recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=f'{MODEL}/encoder.int8.onnx',
    decoder=f'{MODEL}/decoder.int8.onnx',
    joiner=f'{MODEL}/joiner.int8.onnx',
    tokens=f'{MODEL}/tokens.txt',
    model_type='nemo_transducer',
    num_threads=os.cpu_count() or 2,
)

# Split on silences first: the model works on short pieces of speech.
config = sherpa_onnx.VadModelConfig()
config.silero_vad.model = f'{ASR}/models/silero_vad.onnx'
config.silero_vad.min_silence_duration = 0.35
config.silero_vad.min_speech_duration = 0.2
config.silero_vad.max_speech_duration = 25
config.silero_vad.threshold = 0.45
config.sample_rate = RATE
vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)

words = []


def decode(samples, start):
    # Keep a little either side, so the first and last sounds are heard whole.
    pad = int(0.15 * RATE)
    lead = min(pad, start)
    begin = start - lead
    stream = recognizer.create_stream()
    stream.accept_waveform(RATE, audio[begin:begin + lead + len(samples) + pad])
    recognizer.decode_stream(stream)
    result = stream.result
    durations = list(getattr(result, 'durations', []) or [])
    first = len(words)
    for i, (token, t) in enumerate(zip(result.tokens, result.timestamps)):
        end = t + (durations[i] if i < len(durations) and durations[i] > 0 else 0.08)
        at, until = begin / RATE + t, begin / RATE + end
        if token.startswith(('▁', ' ')) or len(words) == first:
            words.append({'text': token.lstrip('▁ '), 'start': at, 'end': until})
        else:
            words[-1]['text'] += token
            words[-1]['end'] = until


window = config.silero_vad.window_size
for i in range(0, len(audio), window):
    vad.accept_waveform(audio[i:i + window])
    while not vad.empty():
        decode(np.array(vad.front.samples), vad.front.start)
        vad.pop()
vad.flush()
while not vad.empty():
    decode(np.array(vad.front.samples), vad.front.start)
    vad.pop()

words = [w for w in words if w['text']]
captions = []
for i, w in enumerate(words):
    end = max(w['end'], w['start'] + 0.05)
    if i + 1 < len(words):
        end = min(end, words[i + 1]['start'])
    start_ms, end_ms = round(w['start'] * 1000), round(end * 1000)
    captions.append({
        'text': (' ' if i else '') + w['text'],
        'startMs': start_ms,
        'endMs': end_ms,
        'timestampMs': (start_ms + end_ms) / 2,
        'confidence': None,
    })
with open(out, 'w', encoding='utf-8') as f:
    json.dump(captions, f, indent='\t', ensure_ascii=False)
    f.write('\n')
print(f'{out}: {len(captions)} words, last ends at {captions[-1]["endMs"] / 1000:.1f} s')
print(''.join(c['text'] for c in captions))
