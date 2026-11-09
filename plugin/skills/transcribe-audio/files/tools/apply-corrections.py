#!/usr/bin/env python3
"""Fix words a recogniser got wrong, keeping its timings.

  python apply-corrections.py transcript.json corrections.json fixed.json

corrections.json holds one row per fix, keyed to the segment it belongs to:
  [{"segment": 12, "heard": "cheetah", "said": "teacher", "why": "both models, checked by ear"}]
A fix that changes the word count shares the old time out across the new words.
A row that matches nothing stops the script, so a stale table cannot pass unseen.
"""
import json
import re
import sys

src, table, out = sys.argv[1:4]
with open(src, encoding='utf-8') as f:
    data = json.load(f)
with open(table, encoding='utf-8') as f:
    rows = json.load(f)


def bare(w):
    return re.sub(r"[^\w']", '', w).lower()


for row in rows:
    seg = data['segments'][row['segment']]
    heard, said = row['heard'].split(), row['said'].split()
    words = seg['words']
    for i in range(len(words) - len(heard) + 1):
        if [bare(w['w']) for w in words[i : i + len(heard)]] == [bare(h) for h in heard]:
            s, e = words[i]['s'], words[i + len(heard) - 1]['e']
            tail = re.sub(r"^[\w']+", '', words[i + len(heard) - 1]['w'])  # keep a full stop or comma
            step = (e - s) / len(said)
            new = [{'w': w, 's': round(s + k * step, 3), 'e': round(s + (k + 1) * step, 3)} for k, w in enumerate(said)]
            new[-1]['w'] += tail
            words[i : i + len(heard)] = new
            seg['text'] = ' '.join(w['w'] for w in words)
            break
    else:
        sys.exit(f"No match for {row['heard']!r} in segment {row['segment']}: {seg['text']!r}")
with open(out, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=1, ensure_ascii=False)
print(f'{len(rows)} corrections applied')
