#!/usr/bin/env python3
"""A long film's YouTube metadata: its chapter list, and the limits it must fit.

  youtube-meta.py <youtube.json> [--description desc.md] [--write desc.md]
      Prints the chapter list (`0:00 Title` lines; m:ss, or h:mm:ss from an hour),
      then one line per check: PASS, WARN or FAIL, its id, and what was measured.
      --description   the description exactly as it will be pasted. Without it, the
                      checks run on the draft --write would write.
      --write         writes a draft: a hook placeholder, the chapter list, and the
                      call to action from youtube.json. Never overwrites a file.
  youtube-meta.py selftest
      Builds good and bad inputs in a temp folder. Each bad one must fail on its own
      id and no other.

Exits 1 when a check FAILs, 2 on a usage error or a file it cannot read. A WARN never fails.

youtube.json (see the skill for a full example):
  title, tags [..], opening (names the stretch before the first chapter, if it does
  not start at 0:00), links [..] (every URL the user approved), cta {offer, url}.
  Timing, either: "edit": "src/edit.json" (reads fps, durationInFrames, chapters and
  the designed beats), or: fps, durationInFrames, chapters [{from (frames) or at
  ("m:ss"), title}], and optional beats [frames or "m:ss"].
  Optional: ledger [{promise, opened_by, paid_at, biggest}], share_beats [..].

  title-length          1 to 100 characters, no < or >.
  description-length    at most 5000 UTF-8 bytes, no < or >.
  description-chapters  (--description) the timestamp lines are exactly this cut's list.
                        A description kept from an earlier cut fails here.
  placeholder           (--description) the draft's hook line is gone.
  tags                  at most 500 characters, counting commas and the quotes around a
                        tag that holds a space.
  chapters-start, chapters-count, chapters-min-length, chapters-order
                        YouTube's rules: the first at 0:00, at least 3, each at least
                        10 s, ascending. Break one and it shows no chapters at all.
  chapter-long          WARN when a chapter runs over 6 minutes.
  links                 every URL in the description is one the user approved.
  cta-present           WARN when the description lacks the call to action's URL.
  beat-gap              WARN when over 90 s pass with no designed beat.
  ledger                every promise is paid inside the film, and the biggest is paid last.
  share-beats           WARN with fewer than 2 named.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from fractions import Fraction

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
TITLE_MAX, DESCRIPTION_MAX, TAGS_MAX, CHAPTERS_MIN, CHAPTER_MIN_S = 100, 5000, 500, 3, 10
PLACEHOLDER = "[HOOK"
HOOK = (f"{PLACEHOLDER}: one or two lines. The problem the title names, and what the film shows about it. "
        "Put the phrase people search for here. Replace this whole line.]")
URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
STAMP = re.compile(r"^\s*((?:\d+:)?\d{1,2}:\d{2})\s+\S")


class Unreadable(Exception):
    pass


def clock(sec: int) -> str:
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def secs(c) -> float:
    v = 0.0
    for part in str(c).split(":"):
        v = v * 60 + float(part)
    return v


def norm(u: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", u.rstrip(".,;:!?").rstrip("/"), flags=re.I)


def load(path: str) -> dict:
    try:
        m = json.loads(pathlib.Path(path).read_text())
        base = pathlib.Path(path).parent
        beats = m.get("beats", [])
        if m.get("edit"):
            e = json.loads((pathlib.Path(m["edit"]) if pathlib.Path(m["edit"]).exists() else base / m["edit"]).read_text())
            m = {**m, "fps": e["fps"], "durationInFrames": e["durationInFrames"], "chapters": e["chapters"]}
            found = [e[k]["from"] for k in ("title", "end") if k in e]
            found += [x["from"] for k in ("teaser", "chapters", "lists", "quotes", "plates", "chats") for x in e.get(k, [])]
            look = lambda c: (c.get("scale"), json.dumps(c.get("view")), c.get("who"))  # noqa: E731
            found += [y["from"] for x, y in zip(e["clips"], e["clips"][1:]) if look(x) != look(y)]
            beats = found
        fps = Fraction(str(m["fps"]))
        m["_fps"] = fps
        m["_len"] = int(Fraction(m["durationInFrames"]) / fps)
        m["_chapters"] = [(int(Fraction(c["from"]) / fps) if "from" in c else int(secs(c["at"])), str(c["title"]).strip()) for c in m["chapters"]]
        m["_beats"] = sorted(float(Fraction(b) / fps) if not isinstance(b, str) else secs(b) for b in beats)
        return m
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        raise Unreadable(f"{path}: cannot read it ({type(e).__name__}: {e}); it needs fps, durationInFrames and chapters, or edit")


def listed(m: dict) -> list[tuple[int, str]]:
    ch = m["_chapters"]
    if m.get("opening"):
        if ch and ch[0][0] == 0:
            raise Unreadable("opening is set, but the first chapter is already at 0:00; remove opening")
        return [(0, m["opening"].strip())] + ch
    return list(ch)


def lines_of(items: list[tuple[int, str]]) -> list[str]:
    return [f"{clock(t)} {title}" for t, title in items]


def draft(m: dict) -> str:
    out = [HOOK, "", "CHAPTERS", *lines_of(listed(m)), ""]
    cta = m.get("cta") or {}
    if cta.get("url"):
        out += [cta.get("offer", ""), cta["url"], ""]
    return "\n".join(out)


def tag_chars(tags: list[str]) -> int:
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)


def measure(path: str, description: str | None) -> tuple[list[str], list[tuple[str, str, str]]]:
    m = load(path)
    items = listed(m)
    lines = lines_of(items)
    rows = []
    title = m.get("title", "")
    bad = "<" in title or ">" in title
    rows.append((FAIL if not 0 < len(title) <= TITLE_MAX or bad else PASS, "title-length",
                 f"{len(title)} of {TITLE_MAX} characters" + (": holds < or >" if bad else "")))
    if description is None:
        text, what = draft(m), "the draft"
    else:
        try:
            text, what = pathlib.Path(description).read_text(), description
        except OSError as e:
            raise Unreadable(f"cannot read {description}: {e}")
    size = len(text.encode())
    bad = description is not None and ("<" in text or ">" in text)
    rows.append((FAIL if size > DESCRIPTION_MAX or bad else PASS, "description-length",
                 f"{size} of {DESCRIPTION_MAX} bytes ({len(text)} characters) in {what}" + (": holds < or >" if bad else "")))
    if description is not None:
        found = [ln.strip() for ln in text.splitlines() if STAMP.match(ln)]
        if found == lines:
            rows.append((PASS, "description-chapters", f"its {len(found)} timestamp lines are the list above"))
        else:
            k = next((i for i, (a, b) in enumerate(zip(found, lines)) if a != b), min(len(found), len(lines)))
            rows.append((FAIL, "description-chapters", f"{len(found)} timestamp lines, this cut gives {len(lines)}; line {k + 1} reads "
                         f"{found[k] if k < len(found) else 'nothing'!r}, should read {lines[k] if k < len(lines) else 'nothing'!r}"))
        left = PLACEHOLDER in text
        rows.append((FAIL if left else PASS, "placeholder", "the draft's hook line is still in it" if left else "no draft placeholder left"))
    tags = m.get("tags", [])
    c = tag_chars(tags)
    rows.append((PASS if c <= TAGS_MAX else FAIL, "tags", f"{len(tags)} tags, {c} of {TAGS_MAX} characters"))
    first = items[0][0] if items else None
    rows.append((PASS if first == 0 else FAIL, "chapters-start", "no chapters" if first is None else f"the first chapter is at {clock(first)}"
                 + ("" if first == 0 else ": YouTube needs 0:00. Name the stretch before it with \"opening\"")))
    rows.append((PASS if len(items) >= CHAPTERS_MIN else FAIL, "chapters-count", f"{len(items)} chapters; YouTube needs at least {CHAPTERS_MIN}"))
    laid = sorted(zip((t for t, _ in items), lines))
    ends = [t for t, _ in laid[1:]] + [m["_len"]]
    spans = [(end - t, line) for (t, line), end in zip(laid, ends)]
    if spans:
        short = [(s, ln) for s, ln in spans if s < CHAPTER_MIN_S]
        s, ln = min(spans)
        rows.append((FAIL if short else PASS, "chapters-min-length",
                     "; ".join(f"{x!r} lasts {n} s" for n, x in short) if short else f"shortest {clock(s)} ({ln!r}); YouTube needs {CHAPTER_MIN_S} s"))
        s, ln = max(spans)
        rows.append((WARN if s > 360 else PASS, "chapter-long", f"longest {clock(s)} ({ln!r})"))
    else:
        rows.append((FAIL, "chapters-min-length", "no chapters to measure"))
    pairs = list(zip((t for t, _ in items), lines))
    back = [(a, b) for (ta, a), (tb, b) in zip(pairs, pairs[1:]) if ta >= tb]
    rows.append((FAIL if back else PASS, "chapters-order",
                 "not ascending: " + "; ".join(f"{a!r} then {b!r}" for a, b in back) if back else f"ascending; the film ends at {clock(m['_len'])}"))
    allowed = {norm(u) for u in m.get("links", [])}
    got = [norm(u) for u in URL.findall(text)]
    foreign = sorted({g for g in got if g not in allowed})
    rows.append((FAIL if foreign else PASS, "links", f"not approved: {', '.join(foreign)}. Never invent a link; ask the user" if foreign else f"{len(got)} link(s), all approved"))
    url = (m.get("cta") or {}).get("url")
    if url:
        rows.append((PASS if norm(url) in got else WARN, "cta-present", f"carries {norm(url)}" if norm(url) in got else f"no {norm(url)}"))
    if m["_beats"]:
        b = m["_beats"] + [float(m["_len"])]
        g, a = max((y - x, x) for x, y in zip(b, b[1:]))
        rows.append((WARN if g > 90 else PASS, "beat-gap", f"longest stretch with no designed beat: {g:.1f} s, from {clock(int(a))}"))
    led = m.get("ledger")
    if led is not None:
        unpaid = [x["promise"] for x in led if not x.get("paid_at") or secs(x["paid_at"]) > m["_len"]]
        big = [x for x in led if x.get("biggest")]
        late = big and any(x.get("paid_at") and secs(x["paid_at"]) > secs(big[0].get("paid_at") or 0) for x in led)
        rows.append((FAIL if unpaid or late or not big else PASS, "ledger",
                     f"unpaid: {unpaid}" if unpaid else "no entry is marked biggest" if not big else "the biggest payoff is not the last" if late
                     else f"{len(led)} promises paid, the biggest last, at {big[0]['paid_at']}"))
        n = len(m.get("share_beats", []))
        rows.append((WARN if n < 2 else PASS, "share-beats", f"{n} named"))
    return lines, rows


def run(path: str, description: str | None, write: str | None) -> int:
    if write and os.path.exists(write):
        raise Unreadable(f"{write} exists; this never overwrites a description. Pick another name")
    lines, rows = measure(path, description)
    m = load(path)
    print(f"YouTube chapters ({path}, {m['_fps']} fps, {clock(m['_len'])}):")
    print("\n".join(lines) or "(none)")
    print()
    for verdict, cid, text in rows:
        print(f"{verdict}  {cid:<20} {text}")
    if write:
        pathlib.Path(write).write_text(draft(m))
        print(f"wrote {write}: a draft; replace its first line before it goes anywhere")
    fails = [cid for verdict, cid, _ in rows if verdict == FAIL]
    print("youtube-meta: " + (f"FAILED {', '.join(fails)}" if fails else "fits YouTube's limits"))
    return 1 if fails else 0


def selftest() -> int:
    tmp = tempfile.mkdtemp(prefix="youtube-meta-")
    url = "https://example.com/start"

    def meta(name: str, starts: list[float], total: float, **kw) -> str:
        p = os.path.join(tmp, name + ".json")
        base = {"fps": 25, "durationInFrames": round(total * 25), "title": "A good title", "tags": ["a", "b c"], "links": [url],
                "cta": {"offer": "Start here:", "url": url}, "chapters": [{"from": round(s * 25), "title": f"Part {i + 1}"} for i, s in enumerate(starts)]}
        base.update(kw)
        pathlib.Path(p).write_text(json.dumps(base))
        return p

    def desc(name: str, text: str) -> str:
        p = os.path.join(tmp, name + ".md")
        pathlib.Path(p).write_text(text)
        return p

    good = meta("good", [45, 204.48, 300.44], 600, opening="Opening")
    body = draft(load(good)).replace(HOOK, "Why a person who passed the test can still not know what to do.")
    written = desc("good", body)
    edge = meta("edge", [0, 10, 20], 30, title="x" * TITLE_MAX, tags=["ab"] * 167)
    edge_body = draft(load(edge)).replace(HOOK, "Hook.")
    at_limit = desc("edge", edge_body + "e" * (DESCRIPTION_MAX - len(edge_body.encode())))
    led_ok = [{"promise": "a", "paid_at": "1:00"}, {"promise": "b", "paid_at": "6:00", "biggest": True}]
    cases = [
        ("good: description as written", None, None, (good, written)),
        ("good: every limit met exactly", None, None, (edge, at_limit)),
        ("good: the draft, no description", None, None, (good, None)),
        ("good: a ledger paid in order", None, None, (meta("led", [0, 60, 120], 400, ledger=led_ok, share_beats=["x", "y"]), None)),
        ("first chapter not at 0:00", "chapters-start", None, (meta("late", [45, 100, 200], 300), None)),
        ("a 5 s chapter", "chapters-min-length", None, (meta("short", [0, 30, 35], 120), None)),
        ("2 chapters", "chapters-count", None, (meta("two", [0, 60], 120), None)),
        ("chapters out of order", "chapters-order", None, (meta("order", [0, 80, 40], 120), None)),
        ("a 101-character title", "title-length", None, (meta("t", [0, 30, 60], 120, title="x" * 101), None)),
        ("an unapproved link", "links", None, (good, desc("inv", body + "\nMore: https://example.org/free\n"))),
        ("over 5000 bytes, under 5000 characters", "description-length", None,
         (good, desc("long", body + "é" * ((DESCRIPTION_MAX + 2 - len(body.encode())) // 2)))),
        ("chapters kept from an earlier cut", "description-chapters", None, (good, desc("stale", body.replace(lines_of(listed(load(good)))[1], "0:47 Part 1")))),
        ("the draft pasted with its placeholder", "placeholder", None, (good, desc("draft", draft(load(good))))),
        ("501 characters of tags", "tags", None, (meta("tg", [0, 30, 60], 120, tags=["tag"] * 125 + ["x"]), None)),
        ("an unpaid promise", "ledger", None, (meta("led2", [0, 60, 120], 400, ledger=[{"promise": "a"}, {"promise": "b", "paid_at": "6:00", "biggest": True}], share_beats=["x", "y"]), None)),
        ("the biggest payoff before the last", "ledger", None, (meta("led3", [0, 60, 120], 400, ledger=[{"promise": "a", "paid_at": "6:00"}, {"promise": "b", "paid_at": "1:00", "biggest": True}], share_beats=["x", "y"]), None)),
        ("no call to action", None, "cta-present", (good, desc("nocta", "\n".join(ln for ln in body.splitlines() if "example.com" not in ln)))),
        ("a 200 s stretch with no beat", None, "beat-gap", (meta("b", [0, 30, 60], 400, beats=[0, 750, 1500]), None)),
    ]
    bad = 0
    try:
        for name, want, want_warn, args in cases:
            _, rows = measure(*args)
            failed = {c for v, c, _ in rows if v == FAIL}
            warned = {c for v, c, _ in rows if v == WARN}
            ok = failed == ({want} - {None}) and warned == ({want_warn} - {None})
            bad += not ok
            print(f"{'ok  ' if ok else 'BAD '} {name:<44} failed [{', '.join(sorted(failed)) or 'nothing'}]" + (f", warned [{', '.join(sorted(warned))}]" if warned else ""))
            if not ok:
                for v, c, text in rows:
                    print(f"       {v} {c:<20} {text}")
        out = os.path.join(tmp, "out.md")
        saved, sys.stdout = sys.stdout, open(os.devnull, "w")
        try:
            run(good, None, out)
        finally:
            sys.stdout.close()
            sys.stdout = saved
        ok = url in pathlib.Path(out).read_text()
        try:
            run(good, None, out)
            ok = False
        except Unreadable:
            pass
        bad += not ok
        print(f"{'ok  ' if ok else 'BAD '} --write: the call to action in it, no overwrite")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"selftest: {len(cases) + 1 - bad} of {len(cases) + 1} inputs judged as planted" + (f", {bad} NOT" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    opts = {}
    for k in ("--description", "--write"):
        if k in a:
            i = a.index(k)
            if i + 1 >= len(a):
                print(__doc__, file=sys.stderr)
                sys.exit(2)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    try:
        if a == ["selftest"] and not opts:
            sys.exit(selftest())
        if len(a) != 1 or a[0].startswith("-"):
            print(__doc__, file=sys.stderr)
            sys.exit(2)
        sys.exit(run(a[0], opts.get("--description"), opts.get("--write")))
    except Unreadable as e:
        print(f"youtube-meta: {e}", file=sys.stderr)
        sys.exit(2)
