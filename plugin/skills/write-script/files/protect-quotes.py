#!/usr/bin/env python3
"""Compare a revised script against its source, to protect quotes and facts.

  python3 protect-quotes.py source.md revised.txt

FAIL: a quote in the revised script that is not, word for word, in the source.
LOOK: digits and capitalised names in the revised script that the source does not
have, and quotes from the source that the script left out.
Then it prints every changed passage, so a person or an agent can read each change.
Exit 1 if there is any FAIL. Standard library only.
"""
import difflib
import re
import sys


def clean(text):
    text = re.sub(r'\{[^}\s]+\}', '', text)  # word{respelling} counts as the word
    text = text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', text)


def quotes(text):
    found = [q.strip(' ,.?!;:') for q in re.findall(r'"([^"]{3,}?)"', text)]
    return [q for q in found if len(q.split()) >= 2]


source_path, revised_path = sys.argv[1:3]
with open(source_path, encoding='utf-8') as f:
    source = clean(f.read())
with open(revised_path, encoding='utf-8') as f:
    revised = clean(f.read())

fails = 0
for q in quotes(revised):
    if q.lower() not in source.lower():
        fails += 1
        near = difflib.get_close_matches(q, quotes(source), n=1, cutoff=0.5)
        print(f'FAIL quote not in the source: "{q}"' + (f'\n     nearest in the source:  "{near[0]}"' if near else ''))
for q in quotes(source):
    if q.lower() not in revised.lower():
        print(f'LOOK quote from the source not in the script: "{q}"')

for num in sorted(set(re.findall(r'\d[\d,.]*\d|\d', revised)) - set(re.findall(r'\d[\d,.]*\d|\d', source))):
    print(f'LOOK number not in the source: {num}')
source_lower = source.lower()
names = set(re.findall(r'(?<=[a-z,] )[A-Z][a-zA-Z]+', revised))
for name in sorted(n for n in names if n.lower() not in source_lower):
    print(f'LOOK name or capitalised word not in the source: {name}')

print('\nEvery changed passage (source, then script):')
a, b = source.split(), revised.split()
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
    if tag == 'equal':
        continue
    before = ' '.join(a[max(0, i1 - 3):i1])
    print(f"  ...{before} [{' '.join(a[i1:i2]) or '(nothing)'}] -> [{' '.join(b[j1:j2]) or '(nothing)'}]")
print(f'\n{fails} changed quote(s).')
sys.exit(1 if fails else 0)
