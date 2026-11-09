#!/usr/bin/env python3
"""Check a spoken script before anyone voices it. Standard library only.

  python3 check-script.py narration/            every .txt in a folder, in name order
  python3 check-script.py n1.txt n2.txt --wpm=180 --gap=1.0

Prints the words and estimated seconds of each block, then the total at your pace.
Lines starting with FIX break the voice or the captions. Lines starting with LOOK
are for you to judge. Exit 1 if there is any FIX.
"""
import argparse
import glob
import os
import re
import sys

FILLER = [
    "it's worth noting", "it's important to", 'at its core', "in today's world", "let's dive in",
    'in order to', 'in this video', 'in this lesson', 'we will explore', "here's the thing",
    'what nobody tells you', 'the best part', 'studies show', 'experts say', 'to wrap up',
    "that's it", 'delve', 'leverage', 'robust', 'seamless', 'empower', 'elevate', 'transformative',
    'pivotal', 'realm', 'tapestry', 'testament to', 'utilize', 'facilitate',
]

p = argparse.ArgumentParser()
p.add_argument('paths', nargs='+')
p.add_argument('--wpm', type=float, default=144, help='words a minute')
p.add_argument('--gap', type=float, default=1.0, help='seconds of held picture you plan after each block')
p.add_argument('--max-block', type=int, default=70, help='words')
p.add_argument('--max-sentence', type=int, default=25, help='words')
a = p.parse_args()

files = []
for path in a.paths:
    files += sorted(glob.glob(os.path.join(path, '*.txt'))) if os.path.isdir(path) else [path]
if not files:
    sys.exit('No .txt files found.')

total_words, fixes, looks = 0, 0, 0


def fix(name, text):
    global fixes
    fixes += 1
    print(f'  FIX  {name}: {text}')


def look(name, text):
    global looks
    looks += 1
    print(f'  LOOK {name}: {text}')


for path in files:
    name = os.path.basename(path)
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    spoken = re.sub(r'\{[^}\s]+\}', '', raw)  # word{respelling} counts as one word
    words = spoken.split()
    total_words += len(words)
    print(f'{name}: {len(words)} words, about {len(words) / a.wpm * 60:.0f} s')
    if len(words) > a.max_block:
        look(name, f'{len(words)} words in one block. Over {a.max_block}, split it, so one change does not mean voicing it all again.')
    if not raw.strip():
        fix(name, 'empty file')
        continue
    if not re.search(r'[.?!]["”’]?\s*$', raw):
        fix(name, 'does not end on . ? or !')
    for mark, why in [('`', 'a backtick'), ('**', 'markdown bold'), ('#', 'a hash sign'), ('<', 'a tag'), ('[', 'a square bracket'), ('_', 'an underscore')]:
        if mark in spoken:
            fix(name, f'{why} would be read aloud or dropped')
    if '  ' in spoken.strip():
        fix(name, 'a doubled space')
    if re.search(r'\s[,.?!;:]', spoken):
        fix(name, 'a space before punctuation')
    for m in re.finditer(r'\b(\w+) \1\b', spoken, flags=re.I):
        look(name, f'a doubled word: "{m.group(0)}"')
    for m in re.finditer(r'\S*\d\S*', spoken):
        look(name, f'"{m.group(0)}" has digits. Write it as it is said: "four hundred kilometres".')
    for sentence in re.split(r'(?<=[.?!])["”’]?\s+', spoken):
        n = len(sentence.split())
        if n > a.max_sentence:
            look(name, f'a {n}-word sentence: "{sentence[:60]}..."')
    if '—' in spoken or '…' in spoken:
        look(name, 'a dash or an ellipsis changes the timing. Keep it only if you mean it.')
    lower = spoken.lower().replace('’', "'")
    for phrase in FILLER:
        if re.search(rf'\b{re.escape(phrase)}\b', lower):
            look(name, f'filler or inflated wording: "{phrase}"')

seconds = total_words / a.wpm * 60 + a.gap * len(files)
print(f'TOTAL: {total_words} words in {len(files)} blocks. At {a.wpm:.0f} words a minute, plus {a.gap} s per block: '
      f'about {int(seconds // 60)} min {int(seconds % 60)} s. {fixes} to fix, {looks} to look at.')
sys.exit(1 if fixes else 0)
