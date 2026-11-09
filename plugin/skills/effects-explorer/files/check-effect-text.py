#!/usr/bin/env python3
"""List the words a copied effect will show unless you change them.

usage: python3 check-effect-text.py <effect file> [more files]

Prints each prop default that holds words, and any words written straight into
the JSX. Many library effects carry sample text, and some of it reads like a real
claim or names a real person. It only finds likely text, so still look at the frame.
"""
import re
import sys

if len(sys.argv) < 2:
    sys.exit(__doc__)
SKIP = re.compile(r"(?i)font|color|colour|background|easing|align|direction|mode|variant|style|ground|side|anchor|fit|blend|layout")
found = 0
for path in sys.argv[1:]:
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    # A list of words as a default, such as words = ['Design', 'in', 'motion.'].
    for m in re.finditer(r"^\s*([a-zA-Z_]\w*)\s*=\s*\[(.*?)\]\s*,?\s*$", text, re.M | re.S):
        words = [w for w in re.findall(r"'((?:[^'\\]|\\.)*)'|\"([^\"]*)\"", m.group(2)) for w in w if w]
        words = [w for w in words if re.search(r"[A-Za-z]", w) and not w.startswith("#")]
        if words and not SKIP.search(m.group(1)) and "text:" not in m.group(2):
            n = text.count("\n", 0, m.start(1)) + 1
            print(f"{path}:{n}  list {m.group(1)}: {', '.join(words)[:120]}")
            found += 1
    for n, line in enumerate(lines, 1):
        d = re.match(r"\s*([a-zA-Z_]\w*)\s*=\s*(['\"])((?:(?!\2).|\\.)*)\2\s*,?\s*$", line)
        j = re.search(r">\s*([A-Z][^<>{}]{3,}?)\s*</", line) if "=>" not in line else None
        alone = re.fullmatch(r"\s*([A-Z][^<>{}=;()]{3,})\s*", line) if n > 1 and lines[n - 2].rstrip().endswith(">") else None
        if d and not SKIP.search(d.group(1)) and d.group(1) not in {"name", "id", "key"} and not d.group(3).startswith("#") and re.search(r"[A-Za-z0-9]", d.group(3)) and (" " in d.group(3) or d.group(3)[0].isupper() or "%" in d.group(3)):
            print(f"{path}:{n}  prop {d.group(1)}: {d.group(3)}")
            found += 1
        elif re.search(r"\btext:\s*['\"]", line):
            print(f"{path}:{n}  sample text: {line.strip()}")
            found += 1
        elif j or alone:
            print(f"{path}:{n}  written in the JSX: {(j or alone).group(1)}")
            found += 1
print(f"{found} piece(s) of text found. Replace each with the user's words, or remove it. Never leave a name, a number or a source they did not give you.")
