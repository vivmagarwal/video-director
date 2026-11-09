#!/usr/bin/env python3
"""Turn word timings from most tools into the caption JSON Remotion reads.

  python3 to-captions.py transcript.json voice.captions.json [--shift-ms=0]

Reads any of these shapes (times in seconds unless the keys say Ms):
  {"segments": [{"words": [{"w": "Hello,", "s": 0.1, "e": 0.4}]}]}    sherpa-onnx script
  {"words": [{"word": " Hello,", "start": 0.1, "end": 0.4}]}          Whisper-style
  [{"punctuated_word": "Hello,", "word": "hello", "start": 0.1, "end": 0.4}]    Deepgram-style
  [{"text": "Hello,", "startMs": 100, "endMs": 400}]                  already in milliseconds
Writes a list of captions. Every word after the first has a leading space, which
is what lets Remotion's page maker break between words.
"""
import argparse
import json
import sys

p = argparse.ArgumentParser()
p.add_argument('input')
p.add_argument('output')
p.add_argument('--shift-ms', type=float, default=0, help='add this to every time; negative moves words earlier')
a = p.parse_args()

with open(a.input, encoding='utf-8') as f:
    data = json.load(f)
if isinstance(data, dict) and 'segments' in data:
    words = [w for s in data['segments'] for w in s.get('words', [])]
elif isinstance(data, dict) and 'words' in data:
    words = data['words']
elif isinstance(data, list):
    words = data
else:
    sys.exit('I do not know this shape. It needs a list of words, or "words", or "segments" holding "words".')
if not words:
    sys.exit('There are no words in that file.')


def pick(w, *keys):
    for k in keys:
        if w.get(k) is not None:
            return w[k]
    sys.exit(f'This word has none of {keys}: {w}')


caps = []
for w in words:
    text = str(pick(w, 'punctuated_word', 'text', 'word', 'w')).strip()
    if not text:
        continue
    if 'startMs' in w:
        s, e = w['startMs'], w['endMs']
    else:
        s, e = pick(w, 's', 'start') * 1000, pick(w, 'e', 'end') * 1000
    s, e = round(s + a.shift_ms), round(e + a.shift_ms)
    caps.append({'text': (' ' if caps else '') + text, 'startMs': s, 'endMs': e, 'timestampMs': (s + e) / 2, 'confidence': None})
with open(a.output, 'w', encoding='utf-8') as f:
    json.dump(caps, f, indent='\t', ensure_ascii=False)
    f.write('\n')
print(f'{len(caps)} words, {caps[0]["startMs"] / 1000:.2f} s to {caps[-1]["endMs"] / 1000:.2f} s, written to {a.output}')
