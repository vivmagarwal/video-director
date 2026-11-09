#!/usr/bin/env python3
"""Give every word a speaker, from a transcript file that names the speakers.

usage: python3 tools/assign-speakers.py <transcript.json> <named.vtt> <out.json> [--fixes=<fixes.json>]

The VTT is a meeting transcript whose cues read `Full Name: text` (Zoom's
.transcript.vtt, for example). Its words are weak but its names are good, so each
recogniser word takes a name like this:

1. The cue holding the word's midpoint, else the nearest cue edge within 1.2 s,
   else the previous word's speaker. Meeting transcripts drop whole turns.
2. Fixes by hand: fixes.json is [["m:ss.s", "m:ss.s", "Name"], ...].
3. Smoothing: a run of 3 words or fewer, under 1.5 s, with one other speaker on
   both sides within 0.7 s, becomes that speaker's. A lone backchannel ("Yeah.",
   "Okay.") keeps its own speaker. Smoothing can undo a short fix: read the result.

Prints each speaker's word count and every stretch over 20 s of words with no cue
near them, which is where the VTT dropped a turn. Check those by ear.
"""
import json
import re
import sys

BACKCHANNEL = {"yeah", "okay", "ok", "right", "mhm", "mm", "mm-hmm", "yes", "no", "sure", "hmm"}


def clock(c):
    sec = 0.0
    for part in str(c).split(":"):
        sec = sec * 60 + float(part)
    return sec


def cues_of(path):
    text = open(path, encoding="utf-8-sig", errors="replace").read()
    cues = []
    for m in re.finditer(r"([\d:.]+) --> ([\d:.]+)[^\n]*\n([^:\n]{1,60}):", text):
        cues.append((clock(m.group(1)), clock(m.group(2)), m.group(3).strip()))
    if not cues:
        sys.exit(f"{path}: no cue reads 'Name: text'; this file does not name its speakers")
    return sorted(cues)


args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 3:
    sys.exit(__doc__)
fixes = []
for a in sys.argv[1:]:
    if a.startswith("--fixes="):
        fixes = [(clock(x), clock(y), n) for x, y, n in json.load(open(a.split("=", 1)[1]))]
data = json.load(open(args[0]))
cues = cues_of(args[1])
words = [w for s in data["segments"] for w in s["words"]]
prev = cues[0][2]
far = []
for w in words:
    mid = (w["s"] + w["e"]) / 2
    hit = next((c for c in cues if c[0] <= mid < c[1]), None)
    if hit is None:
        near = min(cues, key=lambda c: min(abs(c[0] - mid), abs(c[1] - mid)))
        gap = min(abs(near[0] - mid), abs(near[1] - mid))
        hit = near if gap <= 1.2 else None
        if hit is None:
            far.append(mid)
    w["who"] = hit[2] if hit else prev
    prev = w["who"]
    for x, y, n in fixes:
        if x <= mid < y:
            w["who"] = prev = n

i = 0
while i < len(words):
    j = i
    while j + 1 < len(words) and words[j + 1]["who"] == words[i]["who"]:
        j += 1
    n = j - i + 1
    if 0 < i and j + 1 < len(words) and n <= 3 and words[j]["e"] - words[i]["s"] < 1.5:
        before, after = words[i - 1], words[j + 1]
        lone = n == 1 and re.sub(r"[^a-z-]", "", words[i]["w"].lower()) in BACKCHANNEL
        if before["who"] == after["who"] and words[i]["s"] - before["e"] <= 0.7 and after["s"] - words[j]["e"] <= 0.7 and not lone:
            for k in range(i, j + 1):
                words[k]["who"] = before["who"]
    i = j + 1

json.dump(data, open(args[2], "w"), indent=1)
count = {}
for w in words:
    count[w["who"]] = count.get(w["who"], 0) + 1
for who, n in sorted(count.items(), key=lambda kv: -kv[1]):
    print(f"{n:7d} words  {who}")
runs, start = [], None
for a, b in zip(far, far[1:] + [None]):
    start = a if start is None else start
    if b is None or b - a > 3:
        if a - start > 20:
            runs.append((start, a))
        start = None
for a, b in runs:
    print(f"no cue near the words from {int(a // 60)}:{a % 60:04.1f} to {int(b // 60)}:{b % 60:04.1f}: the VTT dropped a turn; check who speaks by ear")
print(f"wrote {args[2]}")
