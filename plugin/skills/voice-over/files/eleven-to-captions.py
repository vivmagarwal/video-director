#!/usr/bin/env python3
"""Turn an ElevenLabs with-timestamps response into .mp3 and .captions.json.

  python3 eleven-to-captions.py n1.response.json n1

A word starts at its first letter and ends at its last character, so a pause
belongs to no word.
"""
import base64
import json
import sys

src, base = sys.argv[1:3]
with open(src, encoding='utf-8') as f:
    r = json.load(f)
if 'audio_base64' not in r:
    sys.exit(f'No audio in that response. It said: {json.dumps(r)[:300]}')
with open(base + '.mp3', 'wb') as f:
    f.write(base64.b64decode(r['audio_base64']))
al = r['alignment']
chars = al['characters']
starts = al['character_start_times_seconds']
ends = al['character_end_times_seconds']
caps, word, a, b = [], '', 0.0, 0.0


def flush():
    global word
    if word:
        s, e = round(a * 1000), round(b * 1000)
        caps.append({'text': (' ' if caps else '') + word, 'startMs': s, 'endMs': e, 'timestampMs': (s + e) / 2, 'confidence': None})
    word = ''


for ch, s, e in zip(chars, starts, ends):
    if ch.isspace():
        flush()
        continue
    if not word:
        a = s
    word += ch
    b = e
flush()
with open(base + '.captions.json', 'w', encoding='utf-8') as f:
    json.dump(caps, f, indent='\t', ensure_ascii=False)
    f.write('\n')
print(f'{base}: {len(caps)} words, last word ends at {caps[-1]["endMs"] / 1000:.1f} s')
