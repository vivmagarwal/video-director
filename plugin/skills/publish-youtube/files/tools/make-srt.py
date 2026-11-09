#!/usr/bin/env python3
"""A subtitle file and a readable transcript, from the film's own captions.

usage: python3 tools/make-srt.py <edit.json or transcript.json> <out stem> [--title="Film title"]

Writes <stem>.srt (at most 2 lines of 42 characters and 6 s a cue, a new cue at an
800 ms pause, a chapter card or a change of speaker, named [First] when speakers
are known) and <stem>.txt (chapter headings and speaker turns with their times).
Both hold the words as corrected and cut, at film time.
"""
import json
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 2:
    sys.exit(__doc__)
title = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--title=")), "")
e = json.load(open(args[0]))
if "segments" in e:  # a word-timed transcript of the finished film
    e = {"fps": 1, "chapters": [], "captions": [
        {"text": w["w"], "startMs": round(w["s"] * 1000), "endMs": round(w["e"] * 1000), **({"who": w["who"]} if w.get("who") else {})}
        for s in e["segments"] for w in s["words"]]}
fps = e["fps"]
chapter_ms = sorted(round(c["from"] / fps * 1000) for c in e["chapters"])


def stamp(ms):
    h, ms = divmod(int(ms), 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def clock(ms):
    s = int(ms // 1000)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def wrap(words, width=42):
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


cues, cur = [], None
for c in e["captions"]:
    t = c["text"].strip()
    if cur:
        crossed = any(cur["end"] <= m < c["startMs"] for m in chapter_ms)
        new = crossed or c["startMs"] - cur["end"] > 800 or c.get("who") != cur["who"] or c["endMs"] - cur["start"] > 6000 \
            or len(wrap(([f"[{cur['who'].split()[0]}]"] if cur["who"] else []) + cur["words"] + [t])) > 2
    if not cur or new:
        cur = {"start": c["startMs"], "end": c["endMs"], "words": [t], "who": c.get("who")}
        cues.append(cur)
    else:
        cur["words"].append(t)
        cur["end"] = c["endMs"]
with open(args[1] + ".srt", "w") as f:
    last = None
    for i, q in enumerate(cues, 1):
        name = f"[{q['who'].split()[0]}] " if q["who"] and q["who"] != last else ""
        last = q["who"]
        f.write(f"{i}\n{stamp(q['start'])} --> {stamp(q['end'])}\n" + "\n".join(wrap((name + " ".join(q["words"])).split())) + "\n\n")

marks = sorted([(round(c["from"] / fps * 1000), f"{c['number']}  {c['title']}") for c in e["chapters"]])
with open(args[1] + ".txt", "w") as f:
    if title:
        f.write(title + "\n\n")
    para, who, at = [], None, 0

    def flush():
        if para:
            f.write(f"[{clock(at)}]{' ' + who + ':' if who else ''} " + " ".join(para) + "\n\n")
            para.clear()

    for c in e["captions"]:
        while marks and marks[0][0] <= c["startMs"]:
            flush()
            f.write(f"## {clock(marks[0][0])}  {marks[0][1]}\n\n")
            marks.pop(0)
        if c.get("who") != who or len(para) > 140 or (len(para) > 90 and para[-1].endswith((".", "?", "!"))):
            flush()
            who = c.get("who")
        if not para:
            at = c["startMs"]
        para.append(c["text"].strip())
    flush()
print(f"wrote {args[1]}.srt ({len(cues)} cues) and {args[1]}.txt")
