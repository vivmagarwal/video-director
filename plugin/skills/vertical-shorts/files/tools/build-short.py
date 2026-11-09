#!/usr/bin/env python3
"""Turn a slate of shorts into data files the Short composition draws.

usage: python3 tools/build-short.py edit/slate.py [--force]      check the slate, then write src/shorts.json
       python3 tools/build-short.py sync <short id> <final.transcript.json>   caption offset per piece

A segment is anchored on words, never on timestamps: a re-cut moves times, not
phrases. A hint time only chooses between repeats of a phrase (the nearest wins).
A phrase not found, or found twice with no hint, stops the build.

Slate checks, each named when it fires:
  one-speaker   every word in a segment belongs to its named speaker (when words have speakers)
  chapter       a segment starts and ends in the same chapter (when chapters are known)
  clean-start   the word before lacks . ? ! and the gap before it is under 0.4 s
  clean-end     the last word ends no sentence and no "fade": true is set
  hook-length   over 6 words across the hook's two lines
  stumble       a word repeats at once inside the kept text ("the the"): a candidate for a drop
  overlap       over 1 s shared with another short (report only)
Structure checks, before any render:
  hook-window   no full-frame event starts in the first 4.5 s
  end-room      no full-frame event runs past end - 0.8 s
  slides        at least 2 slides (warns; a short of under 25 s may hold 1)
  gap           no stretch over 4 s without a designed change (a cut with a punch-in, pop, slide, plate)
  pops          3 to 6 pops per 45 s (warns)
  length        under 60 s (warns; about 45 s fits every platform)
  upscale       the original pixels are enlarged more than 3.8x (needs RAW_WIDTH and a view width)

Exits 1 on any FAIL unless --force is given. A WARN never fails.
"""
from __future__ import annotations

import difflib
import json
import math
import pathlib
import re
import runpy
import statistics
import subprocess
import sys

OUT = "src/shorts.json"
FILLERS = {"uh", "um", "uhm", "er", "erm", "ah", "hmm"}


def clock(sec: float) -> str:
    return f"{int(sec // 60)}:{sec % 60:05.2f}"


def secs(c) -> float:
    v = 0.0
    for part in str(c).split(":"):
        v = v * 60 + float(part)
    return v


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def load_words(P: dict) -> tuple[list[dict], list[tuple[float, str]]]:
    """Words on the source clock. `at` is the clock hints are written on."""
    if P.get("EDIT"):  # the finished long cut's data: corrected words, film clock for hints
        e = json.loads(pathlib.Path(P["EDIT"]).read_text())
        fps = e["fps"]
        body = [c for c in e["clips"] if c["section"] == "body"]
        words = []
        for c in e["captions"]:
            f = c["startMs"] / 1000 * fps
            clip = next((b for b in body if b["from"] <= f < b["from"] + b["dur"]), None)
            if clip:  # the teaser repeats body lines; shorts take the body's
                base = (clip["src"] - clip["from"]) / fps
                words.append({"w": c["text"].strip(), "s": c["startMs"] / 1000 + base, "e": c["endMs"] / 1000 + base,
                              "at": c["startMs"] / 1000, "who": c.get("who")})
        return words, [(ch["from"] / fps, ch["title"]) for ch in e["chapters"]]
    segs = json.loads(pathlib.Path(P["TRANSCRIPT"]).read_text())["segments"]
    words = [{**w, "at": w["s"], "who": w.get("who")} for s in segs for w in s["words"]]
    return words, [(secs(a), t) for a, t in P.get("CHAPTERS", [])]


def find(words: list[dict], phrase: str, hint, what: str, first: bool = False) -> tuple[int, int]:
    toks = [norm(x) for x in phrase.split()]
    norms = [norm(w["w"]) for w in words]
    hits = [i for i in range(len(words) - len(toks) + 1) if norms[i:i + len(toks)] == toks]
    if not hits:
        raise SystemExit(f"{what}: phrase not found: {phrase!r}")
    if first:
        hint = None
        hits = hits[:1]  # a segment ends at the first time its end phrase comes after its start
    if len(hits) > 1 and hint is None:
        raise SystemExit(f"{what}: {phrase!r} found {len(hits)} times, at " + ", ".join(clock(words[h]['at']) for h in hits) + "; add a hint")
    i = min(hits, key=lambda h: abs(words[h]["at"] - secs(hint))) if hint is not None else hits[0]
    return i, i + len(toks) - 1


def size_of(path: str) -> list[int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", "public/" + path], capture_output=True, text=True).stdout.strip()
    if "," not in out:
        raise SystemExit(f"cannot read public/{path}")
    return [int(x) for x in out.split(",")[:2]]


def to_clips(ranges: list[list], fps: int) -> list[dict]:
    """Integer frames, once. Every caption word maps through this one list, so timing cannot drift."""
    frames = []
    for a, b, seg in ranges:
        fa, fb = math.floor(a * fps), math.ceil(b * fps)
        if frames and frames[-1][2] == seg and fa <= frames[-1][1] + 1:
            frames[-1][1] = max(frames[-1][1], fb)
        else:
            frames.append([fa, fb, seg])
    clips, at = [], 0
    for fa, fb, seg in frames:
        clips.append({"from": at, "dur": fb - fa, "src": fa, "seg": seg})
        at += fb - fa
    return clips


def build(short: dict, words: list[dict], chapters: list, P: dict) -> tuple[dict, list[tuple[str, str, str]]]:
    fps, sid = P["FPS"], short["id"]
    rows: list[tuple[str, str, str]] = []
    drop: set[int] = set()
    for d in short.get("drops", []):
        a, b = find(words, d["phrase"], d.get("hint"), f"{sid} drop")
        drop.update(range(a, b + 1))
    ranges, kept, spans = [], [], []
    for n, seg in enumerate(short["segments"]):
        a, _ = find(words, seg["start"], seg.get("hint"), f"{sid} segment {n + 1} start")
        tail = find(words[a:], seg["end"], None, f"{sid} segment {n + 1} end", first=True)
        b = a + tail[1]
        spans.append((words[a]["s"], words[b]["e"]))
        prev = words[a - 1] if a else None
        if prev and not re.search(r"[.?!]$", prev["w"]) and words[a]["s"] - prev["e"] < 0.4:
            rows.append(("FAIL", "clean-start", f"segment {n + 1} starts mid-sentence, after {prev['w']!r} at {clock(words[a]['at'])}"))
        if not re.search(r"[.?!]$", words[b]["w"]) and not seg.get("fade"):
            rows.append(("FAIL", "clean-end", f"segment {n + 1} ends on {words[b]['w']!r}, which ends no sentence; move it or set fade"))
        if seg.get("who"):
            other = {w["who"] for w in words[a:b + 1] if w.get("who") and w["who"] != seg["who"]}
            if other:
                rows.append(("FAIL", "one-speaker", f"segment {n + 1} holds words by {', '.join(sorted(other))}"))
        marks = [t for t, _ in chapters]
        if sum(1 for m in marks if words[a]["at"] < m <= words[b]["at"]):
            rows.append(("FAIL", "chapter", f"segment {n + 1} crosses a chapter turn"))
        here = [i for i in range(a, b + 1) if i not in drop and norm(words[i]["w"]) not in FILLERS and norm(words[i]["w"])]
        for x, y in zip(here, here[1:]):
            if norm(words[x]["w"]) == norm(words[y]["w"]):
                rows.append(("FAIL", "stumble", f"{words[x]['w']!r} twice at {clock(words[x]['at'])}: add a drop, or check by ear"))
        cur = [max(0.0, words[here[0]]["s"] - 0.05), None, n]
        for x, y in zip(here, here[1:]):
            gap = words[y]["s"] - words[x]["e"]
            if gap > 0.30 or y != x + 1:
                silence = 0.18 if re.search(r"[.?!]$", words[x]["w"]) else 0.14
                post = max(0.12, silence - 0.05)
                cur[1] = min(words[x]["e"] + post, words[y]["s"] - 0.05) if gap > post + 0.05 else (words[x]["e"] + words[y]["s"]) / 2
                ranges.append(cur)
                cur = [max(cur[1], words[y]["s"] - 0.05), None, n]
        cur[1] = words[here[-1]]["e"] + 0.18
        ranges.append(cur)
        kept += [(i, n) for i in here]
    clips = to_clips(ranges, fps)
    for k, c in enumerate(clips):  # a punch-in must be seen: at least 10 to 12 %
        c["scale"] = short.get("punch", [1.0, 1.12])[k % 2]
    total = sum(c["dur"] for c in clips) + round(short.get("tail_s", 0.6) * fps)

    def film_frame(sec: float, n: int | None = None) -> int | None:
        f = sec * fps
        for c in clips:
            if c["src"] <= f < c["src"] + c["dur"] and (n is None or c["seg"] == n):
                return c["from"] + round(f - c["src"])
        return None

    captions = []
    for i, n in kept:
        w = words[i]
        f0 = film_frame((w["s"] + w["e"]) / 2, n)
        if f0 is None:
            continue
        start = film_frame(w["s"], n)
        f0 = start if start is not None else f0
        captions.append({"text": w["w"], "from": f0, "ms": round(f0 / fps * 1000), "hit": norm(w["w"]) in {h.lower() for h in short.get("hits", [])}})
    if len(captions) != len(kept):
        rows.append(("WARN", "captions", f"{len(kept) - len(captions)} kept word(s) fell in no clip"))

    # Caption pages: 2 or 3 words, at most 20 characters, on screen at least 0.5 s.
    pages: list[dict] = []
    for c in captions:
        p = pages[-1] if pages else None
        if p and len(p["words"]) < 3 and sum(len(x["text"]) + 1 for x in p["words"]) + len(c["text"]) <= 20 \
                and not re.search(r"[.?!]$", p["words"][-1]["text"]):
            p["words"].append(c)
        else:
            pages.append({"from": c["from"], "words": [c]})
    for x, y in zip(pages, pages[1:]):
        x["to"] = y["from"]
    if pages:
        pages[-1]["to"] = total

    def anchor(ev: dict, what: str) -> int:
        a, _ = find(words, ev["at"], ev.get("hint"), f"{sid} {what}")
        f = film_frame(words[a]["s"])
        if f is None:
            raise SystemExit(f"{sid} {what}: {ev['at']!r} is not in the kept words")
        return f

    slides = [{**s, "from": anchor(s, "slide"), "dur": round(s.get("dur_s", 3.0) * fps)} for s in short.get("slides", [])]
    pops = [{**p, "from": anchor(p, "pop"), "dur": round(p.get("dur_s", 0.9) * fps)} for p in short.get("pops", [])]
    sfx = [{**x, "from": anchor(x, "sound")} for x in short.get("sfx", [])]
    plate = short.get("plate")
    if plate:
        plate = {**plate, "from": anchor(plate, "plate"), "dur": round(plate.get("dur_s", 3.5) * fps)}

    words_n = len(kept)
    secs_long = total / fps
    hook_words = " ".join(short["hook"]).split()
    if len(hook_words) > 6:
        rows.append(("FAIL", "hook-length", f"{len(hook_words)} words: {' '.join(hook_words)}"))
    for s in slides:  # a slide fills the frame
        if s["from"] < 4.5 * fps:
            rows.append(("FAIL", "hook-window", f"a full-frame slide starts at {s['from'] / fps:.2f} s"))
        if s["from"] + s["dur"] > total - 0.8 * fps:
            rows.append(("FAIL", "end-room", f"a full-frame slide runs to {(s['from'] + s['dur']) / fps:.2f} s of {secs_long:.2f}"))
    if len(slides) < 2:
        rows.append(("WARN", "slides", f"{len(slides)} slide(s); the shape asks for at least 2 that carry content"))
    per45 = len(pops) * 45 / secs_long
    if not 3 <= per45 <= 6:
        rows.append(("WARN", "pops", f"{len(pops)} pops is {per45:.1f} per 45 s; the shape asks for 3 to 6"))
    if secs_long >= 60:
        rows.append(("WARN", "length", f"{secs_long:.1f} s"))
    changes = sorted({c["from"] for c in clips} | {e["from"] for e in slides + pops} | ({plate["from"]} if plate else set()) | {total})
    longest = max((b - a, a) for a, b in zip(changes, changes[1:]))
    if longest[0] > 4 * fps:
        rows.append(("FAIL", "gap", f"{longest[0] / fps:.1f} s with no designed change, from {longest[1] / fps:.1f} s"))
    view = short.get("view") or {}
    source = short.get("source", P["SOURCE"])
    size = size_of(source)
    raw_w, view_w = P.get("RAW_WIDTH"), view.get("w")
    if raw_w and view_w:
        up = (1080 / view_w) * (size[0] / raw_w)
        if up > 3.8:
            rows.append(("FAIL", "upscale", f"{up:.2f}x from the original pixels; the limit used here is about 3.8x"))

    data = {"id": sid, "title": short.get("title", ""), "profile": short.get("profile", "ad"), "fps": fps, "durationInFrames": total,
            "source": source, "sourceSize": size, "view": view, "voice": short.get("voice"),
            "hook": short["hook"], "clips": clips, "captions": captions, "pages": pages, "slides": slides, "pops": pops, "sfx": sfx,
            "plate": plate, "cta": short.get("cta"), "segments": [{"start": clock(a), "end": clock(b)} for a, b in spans]}
    print(f"{sid}: {secs_long:.1f} s, {len(clips)} pieces, {words_n} words, {len(pages)} caption pages, "
          f"{len(slides)} slides, {len(pops)} pops, {len(sfx)} sounds, longest gap {longest[0] / fps:.1f} s, profile {data['profile']}")
    return data, rows


def sync(sid: str, transcript: str) -> int:
    data = next(s for s in json.loads(pathlib.Path(OUT).read_text()) if s["id"] == sid)
    heard = [w for s in json.loads(pathlib.Path(transcript).read_text())["segments"] for w in s["words"]]
    caps = data["captions"]
    sm = difflib.SequenceMatcher(None, [norm(c["text"]) for c in caps], [norm(w["w"]) for w in heard], autojunk=False)
    pairs = []
    for tag, i1, i2, j1, _ in sm.get_opcodes():
        if tag == "equal":
            pairs += [(caps[i1 + k], heard[j1 + k]) for k in range(i2 - i1)]
    print(f"{len(pairs)} of {len(caps)} caption words matched what the short says")
    bad = 0
    for c in data["clips"]:
        off = [w["s"] * 1000 - x["ms"] for x, w in pairs if c["from"] <= x["from"] < c["from"] + c["dur"]]
        if off:
            m = statistics.median(off)
            bad += abs(m) > 120
            print(f"  piece at {c['from'] / data['fps']:6.2f} s: n={len(off):3d}  median {m:+.0f} ms{'  OVER 120 ms' if abs(m) > 120 else ''}")
    return 1 if bad or len(pairs) < len(caps) * 0.6 else 0


def main() -> int:
    if len(sys.argv) >= 4 and sys.argv[1] == "sync":
        return sync(sys.argv[2], sys.argv[3])
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    P = runpy.run_path(sys.argv[1])
    words, chapters = load_words(P)
    out, fails, used = [], 0, []
    for short in P["SHORTS"]:
        data, rows = build(short, words, chapters, P)
        out.append(data)
        for v, cid, text in rows:
            print(f"  {v}  {cid:<12} {text}")
            fails += v == "FAIL"
        for prev_id, prev in used:
            for a, b in [(secs(s["start"]), secs(s["end"])) for s in data["segments"]]:
                for c, d in [(secs(s["start"]), secs(s["end"])) for s in prev]:
                    if min(b, d) - max(a, c) > 1:
                        print(f"  note  overlap      {data['id']} shares {min(b, d) - max(a, c):.1f} s with {prev_id}: fine, but use no line as a hook twice")
        used.append((data["id"], data["segments"]))
    if fails and "--force" not in sys.argv:
        print(f"{fails} check(s) failed; nothing written. Fix the slate, or pass --force for a planned exception.")
        return 1
    pathlib.Path(OUT).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT}: {len(out)} short(s). Print one and read every URL in it before any batch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
