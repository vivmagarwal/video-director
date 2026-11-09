#!/usr/bin/env python3
"""The checks that catch what a long edit of a raw recording hides.

An edit built from word timings removes hundreds of
pauses. No still or contact sheet shows a clipped word, or a phrase cut because
the recogniser never heard it, and nothing but the finished file shows captions
drifting away from the voice. These three do. Each reads the `edit.json` a
build script writes: `clips` (from, dur, src, section; frames at `fps`),
`body` (from, to), `captions` (text, startMs, endMs, in the finished film) and
`removed` (the cuts and fillers taken out on purpose, in raw seconds).

  splice  <edit.json> <raw16k.wav> <out.wav>
      The body's audio exactly as the cut plays it. Transcribe it
      (tools/transcribe.py), then run `clipped` on the result.
  clipped <edit.json> <raw.transcript.json> <spliced.transcript.json>
      Every word a clip edge cuts through (from the raw word timings), then the
      words the recogniser heard in the raw take, inside a kept clip, that it no
      longer hears in the splice. One within 0.15 s of a cut may be clipped.
      Clips that follow each other in the source and in the film count as one:
      an edit split at every change of speaker splits inside overlapping words
      without cutting anything.
  dropped <edit.json> <raw16k.wav> [--noise=-38] [--min=0.25] [--edge=0.5]
      Stretches of sound in the raw take that no clip keeps and no deliberate
      cut or filler accounts for: speech the recogniser missed, which a cut on
      word timings takes for a pause. Then the sound lost from the edge of a kept
      stretch, longest first: one of --edge seconds or more counts as a finding,
      since speech can run on into a kept word with no silence between. A shorter
      one is likely a breath, not a pass. Needs ffmpeg with silencedetect on PATH.
  sync    <edit.json> <final.transcript.json>
      Transcribe the FINISHED film's audio, then compare each caption's start
      with when the word is heard: median lead, spread, drift per 2 minutes.
  retakes <raw.transcript.json> [--window 120] [--ratio 0.62]
      Before the cut: where the take went wrong and went again. Prints
      candidates in raw time, each with the sentence either side, and cuts
      nothing. Four kinds, fillers ignored throughout:
        retake   a sentence that nearly repeats one begun up to --window s
                 before (difflib ratio of the lowercased words > --ratio). The
                 EARLIER take is usually the one to cut: it is the broken one.
        repeat   a word said twice ("I I", "the the"), or a fragment of the next
                 word ("a s student"), less than 1 s apart.
        restart  a 2-4-word phrase said again straight away ("we have to we
                 have to").
        number   a number corrected at once ("80 percent, 18 percent"): keep the
                 second.
      The guard against rhetoric: "It's not the grades. It's not the scores."
      repeats its frame, not its content. A sentence pair counts only if its
      content words (what is left when function words are dropped) recur too:
      more than half of the shorter side's. A broken take passes, its few
      content words all said again; a new point in an old frame does not.
      Said again more than 10 s later, it must share two content words: a
      broken take is re-said at once, a short line said later is a refrain
      ("What will they keep?"). A phrase that ends a sentence is not a
      restart ("Where am I? Where am I going?").
      Doubles said on purpose ("very very", "no no") and adjacent counts
      ("three, four times") are not flagged either.
      A careful scan with these rules once found 24 real cuts in a recording
      where a first reading found 5.
  selftest
      Plants one retake of each kind, and the rhetoric and doubles that must
      not count, in a synthetic transcript; `retakes` must find exactly those.

Exits 1 when `clipped`, `dropped`, `sync` or `retakes` finds something to look
at, 2 on a usage error. A finding is a lead: open the moment it names and
listen before changing the cut.
"""

from __future__ import annotations

import difflib
import json
import re
import statistics
import subprocess
import sys
import wave

norm = lambda x: re.sub(r"[^a-z0-9']", "", x.lower())  # noqa: E731


def clock(sec: float) -> str:
    m, s = divmod(max(0.0, sec), 60)
    return f"{int(m)}:{s:05.2f}"


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def body_clips(edit: dict) -> list[dict]:
    return [c for c in edit["clips"] if c["section"] == "body"]


def heard_words(transcript: str) -> list[dict]:
    return [w for s in load(transcript)["segments"] for w in s["words"]]


def splice(edit_path: str, raw: str, out: str) -> int:
    edit = load(edit_path)
    fps = edit["fps"]
    with wave.open(raw) as src, wave.open(out, "wb") as dst:
        dst.setparams(src.getparams())
        rate, width = src.getframerate(), src.getsampwidth() * src.getnchannels()
        for c in body_clips(edit):
            src.setpos(int(c["src"] / fps * rate))
            n = int((c["src"] + c["dur"]) / fps * rate) - int(c["src"] / fps * rate)
            dst.writeframes(src.readframes(n))
        total = dst.getnframes() / rate
    print(f"wrote {out}: {len(body_clips(edit))} clips, {total / 60:.2f} min")
    return 0


def clipped(edit_path: str, raw_transcript: str, transcript: str) -> int:
    # Compare like with like: the same recogniser's reading of the raw take,
    # limited to what the clips keep, against its reading of the splice. The
    # captions are the wrong yardstick: they hold corrections, and words the
    # recogniser never hears would read as "missing" on both sides.
    edit = load(edit_path)
    fps = edit["fps"]
    # Clips that follow each other in the source AND in the film play as one:
    # an edit that splits at every change of speaker (to level each voice)
    # splits inside words that overlap, and no sound is lost there.
    runs: list[list[int]] = []
    for c in sorted(body_clips(edit), key=lambda c: c["from"]):
        if runs and runs[-1][1] == c["src"] and runs[-1][2] == c["from"]:
            runs[-1][1] += c["dur"]
            runs[-1][2] += c["dur"]
        else:
            runs.append([c["src"], c["src"] + c["dur"], c["from"] + c["dur"]])
    clips = [(a / fps, b / fps) for a, b, _ in runs]
    raw = heard_words(raw_transcript)
    kept = []  # (word, distance to the nearer edge of its clip)
    for a, b in clips:
        for w in raw:
            if a <= (w["s"] + w["e"]) / 2 < b:
                kept.append((w, min(w["s"] - a, b - w["e"])))
    # First, structurally: no clip edge may fall inside a word the take keeps
    # any of. A word cut through still half-sounds, and the recogniser often
    # hears it anyway, so this is the check that does not depend on hearing.
    removed = edit.get("removed", {})
    meant = [(c["from"], c["to"]) for c in removed.get("cuts", [])] + [tuple(f) for f in removed.get("fillers", [])]
    through = 0
    for w in raw:
        if any(x <= (w["s"] + w["e"]) / 2 < y for x, y in meant):
            continue
        for a, b in clips:
            inside = max(0.0, min(b, w["e"]) - max(a, w["s"]))
            if 0 < inside < (w["e"] - w["s"]) - 0.02:
                through += 1
                print(f"  raw {clock(w['s'])}  {w['w']!r}  CUT THROUGH: a clip keeps {inside:.2f} s of its {w['e'] - w['s']:.2f} s")
    print(f"{through} word(s) cut through by a clip edge")

    # Then by ear: what the recogniser no longer hears in the splice.
    got = heard_words(transcript)
    x, y = [norm(w["w"]) for w, _ in kept], [norm(w["w"]) for w in got]
    sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
    print(f"{len(kept)} words kept by the clips, {len(got)} heard in the splice, agreement {sm.ratio():.1%}")
    at_cut = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag not in ("delete", "replace"):
            continue
        heard = f" (heard as {' '.join(y[j1:j2])!r})" if tag == "replace" else ""
        for w, edge in kept[i1:i2]:
            where = "AT A CUT, listen" if edge < 0.15 else "inside its clip: read differently, not cut"
            at_cut += edge < 0.15
            print(f"  raw {clock(w['s'])}  {w['w']!r}{heard}  {edge:.2f} s from the clip edge — {where}")
    print(f"{at_cut} missing word(s) at a cut")
    return 1 if at_cut or through else 0


def dropped(edit_path: str, raw: str, noise: float, minimum: float, edge: float) -> int:
    edit = load(edit_path)
    fps = edit["fps"]
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", raw, "-af", f"silencedetect=n={noise}dB:d=0.12", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    events = re.findall(r"silence_(start|end): ([0-9.]+)", log)
    sound, prev = [], 0.0
    for kind, value in events:
        if kind == "start" and float(value) > prev:
            sound.append((prev, float(value)))
        elif kind == "end":
            prev = float(value)
    kept = [(c["src"] / fps, (c["src"] + c["dur"]) / fps) for c in body_clips(edit)]
    removed = edit.get("removed", {})
    # A removal takes its neighbouring pause with it, and a recogniser times a
    # filler shorter than it sounds: 0.35 s either side of one is its own.
    meant = [(c["from"] - 0.35, c["to"] + 0.35) for c in removed.get("cuts", [])]
    meant += [(s - 0.35, e + 0.35) for s, e in removed.get("fillers", [])]

    def overlap(a: float, b: float, ranges: list[tuple[float, float]]) -> float:
        return sum(max(0.0, min(b, y) - max(a, x)) for x, y in ranges)

    def outside(a: float, b: float, ranges: list[tuple[float, float]]) -> list[tuple[float, float]]:
        parts, at = [], a
        for x, y in sorted(ranges):
            if y <= at or x >= b:
                continue
            if x > at:
                parts.append((at, x))
            at = max(at, y)
        return parts + ([(at, b)] if at < b else [])

    # Two faults look alike here. A whole stretch of sound that no clip touches
    # is lost speech or a noise. Sound lost from the edge of a kept stretch is
    # usually a breath trimmed by the pause compression, but speech the recogniser
    # missed can run on into a kept word, and `clipped` cannot see that either.
    found, edges = 0, []
    for a, b in sound:
        if b - a < minimum:
            continue
        if overlap(a, b, kept) >= 0.1:
            edges += [(q - p, p, q) for p, q in outside(a, b, kept)
                      if (q - p) - overlap(p, q, meant) >= minimum]
            continue
        unexplained = (b - a) - overlap(a, b, meant)
        if unexplained < minimum:
            continue
        found += 1
        print(f"  raw {clock(a)}-{clock(b)}  {b - a:.2f} s of sound that no clip keeps")
    print(f"{found} stretch(es) of sound dropped whole that no cut or filler explains"
          + (" — listen to each: speech the recogniser never heard, or a noise" if found else ""))
    long_edges = 0
    for n, p, q in sorted(edges, reverse=True):
        long_edges += n >= edge
        print(f"  raw {clock(p)}-{clock(q)}  {n:.2f} s lost from the edge of a kept stretch"
              + (" — LONG, listen: it can be speech running on into a kept word" if n >= edge else " — likely a breath"))
    print(f"{long_edges} lost edge(s) of {edge} s or more, and {len(edges) - long_edges} shorter; "
          "neither check can hear speech the recogniser missed, so the shorter ones are not a pass")
    return 1 if found or long_edges else 0


def sync(edit_path: str, transcript: str) -> int:
    edit = load(edit_path)
    caps = edit["captions"]
    got = heard_words(transcript)
    a, b = [norm(c["text"]) for c in caps], [norm(w["w"]) for w in got]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    offs = []
    for tag, i1, i2, j1, _ in sm.get_opcodes():
        if tag == "equal":
            offs += [(caps[i1 + k]["startMs"] / 1000, got[j1 + k]["s"] - caps[i1 + k]["startMs"] / 1000) for k in range(i2 - i1)]
    if len(offs) < 20:
        print(f"only {len(offs)} words matched: wrong transcript for this edit?")
        return 1
    o = sorted(x for _, x in offs)
    print(f"{len(offs)} of {len(caps)} caption words matched what the film says")
    print(f"heard minus caption: median {statistics.median(o) * 1000:+.0f} ms, 5% {o[len(o) // 20] * 1000:+.0f} ms, 95% {o[len(o) * 19 // 20] * 1000:+.0f} ms")
    medians = []
    end = max(t for t, _ in offs)
    for w0 in range(0, int(end) + 1, 120):
        window = [x for t, x in offs if w0 <= t < w0 + 120]
        if window:
            medians.append(statistics.median(window))
            print(f"  {clock(w0)}  n={len(window):3d}  median {medians[-1] * 1000:+.0f} ms")
    drift = max(medians) - min(medians)
    far = [(t, x) for t, x in offs if abs(x) > 0.4]
    print(f"drift across windows {drift * 1000:.0f} ms; {len(far)} word(s) more than 0.4 s off"
          + ("".join(f"\n  film {clock(t)}: {x:+.2f} s" for t, x in far[:10])))
    return 1 if drift > 0.08 or abs(statistics.median(o)) > 0.12 else 0


# --------------------------------------------------------------------------- retakes
FILLERS = {"uh", "um", "uhm", "er", "erm", "ah", "hmm", "mm"}
# Function words: what a sentence is built from rather than what it is about.
STOP = set("""a an the and or but so if then than that this these those it its it's is are was were be been being am
i i'm i've i'll i'd you you're you've you'll we we're we've we'll they they're they've he he's she she's him her
them us me my our your their his of to in on at for with from by as about into over under not no nor do does did
don't doesn't didn't can can't cannot will won't would should could may might must shall have has had just also very really what what's
which who when where why how there there's here here's that's let's all some any more most much many such other
same too each both up out down off again now even only because while like well okay ok yeah yes oh get got going
gonna go know think say said make one thing things way""".split())
DOUBLES = {"very", "really", "so", "no", "yes", "yeah", "ha", "bye", "okay", "ok", "had", "much", "many", "more"}
UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES = {"hundred": 100, "thousand": 1000, "million": 10**6, "billion": 10**9}


def tok(word: str) -> str:
    return re.sub(r"[^a-z0-9'%.]", "", word.lower().replace("’", "'")).strip(".")


def spoken(words: list[dict]) -> list[tuple[int, str]]:
    """(index, token) of every word that is not a filler."""
    return [(i, t) for i, t in ((i, tok(w["w"])) for i, w in enumerate(words)) if t and t not in FILLERS]


def sentence_spans(words: list[dict], pause: float = 0.6) -> list[tuple[int, int]]:
    """[first, last] word index of each sentence: it ends at . ? ! or a pause of `pause` s."""
    spans, first = [], 0
    for i, w in enumerate(words):
        if i + 1 == len(words) or re.search(r"[.?!]$", w["w"]) or words[i + 1]["s"] - w["e"] >= pause:
            spans.append((first, i))
            first = i + 1
    return spans


def number(t: str) -> float | None:
    if re.fullmatch(r"\d+(\.\d+)?%?", t.replace(",", "")):
        return float(t.replace(",", "").rstrip("%"))
    return None


def find_retakes(words, spans, window, ratio):
    toks = [[t for _, t in spoken(words[a:b + 1])] for a, b in spans]
    found, rhetoric = [], 0
    for i, (a, _) in enumerate(spans):
        best = None
        for j in range(i - 1, -1, -1):
            if words[a]["s"] - words[spans[j][0]]["s"] > window:
                break
            x, y = toks[j], toks[i]
            if max(len(x), len(y)) < 4 or min(len(x), len(y)) < 2:
                continue
            r = difflib.SequenceMatcher(None, x, y, autojunk=False).ratio()
            if r <= ratio or (best and r <= best[1]):
                continue
            cx, cy = {t for t in x if t not in STOP}, {t for t in y if t not in STOP}
            if not cx or not cy or len(cx & cy) / min(len(cx), len(cy)) <= 0.5:
                rhetoric += 1  # the same frame round different content: rhetoric, not a retake
                continue
            if words[a]["s"] - words[spans[j][1]]["e"] > 10 and len(cx & cy) < 2:
                rhetoric += 1  # a short line said again later is a refrain; a broken take is re-said at once
                continue
            best = (j, r)
        if best:
            j, r = best
            gap = words[a]["s"] - words[spans[j][0]]["s"]
            found.append({"kind": "retake", "i": spans[j][0], "later": spans[i],
                          "note": f"said again {gap:.1f} s later (ratio {r:.2f}); the earlier take is usually the one to cut"})
    return found, rhetoric


def find_repeats(words, spans, window, ratio):
    toks, found = spoken(words), []
    for (i, a), (j, b) in zip(toks, toks[1:]):
        if words[j]["s"] - words[i]["e"] > 1.0 or re.search(r"[.?!]$", words[i]["w"]):
            continue
        if a == b and a not in DOUBLES and number(a) is None:
            found.append({"kind": "repeat", "i": i, "note": f"{words[i]['w']!r} twice"})
        elif a != b and b.startswith(a) and a not in STOP and number(a) is None:
            found.append({"kind": "repeat", "i": i, "note": f"{words[i]['w']!r} broken off, then {words[j]['w']!r}"})
    return found, 0


def find_restarts(words, spans, window, ratio):
    toks, found, k = spoken(words), [], 0
    while k < len(toks):
        for n in (4, 3, 2):
            first, second = toks[k:k + n], toks[k + n:k + 2 * n]
            if len(second) == n and [t for _, t in first] == [t for _, t in second] and len({t for _, t in first}) > 1 \
                    and words[second[0][0]]["s"] - words[first[-1][0]]["e"] <= 1.5 \
                    and not re.search(r"[.?!]$", words[first[-1][0]]["w"]):  # a restart breaks off; it does not end a sentence
                found.append({"kind": "restart", "i": first[0][0],
                              "note": f"{' '.join(words[i]['w'] for i, _ in first)!r} twice: keep the second"})
                k += n
                break
        else:
            k += 1
    return found, 0


def find_numbers(words, spans, window, ratio):
    # Group the words into numbers: digits, or runs of number words ("twenty five").
    toks, groups, k = spoken(words), [], 0
    while k < len(toks):
        i, t = toks[k]
        if number(t) is not None:
            groups.append((k, k, number(t), "%" if t.endswith("%") else None))
            k += 1
            continue
        total = cur = 0
        j = k
        while j < len(toks) and (toks[j][1] in UNITS or toks[j][1] in TENS or toks[j][1] in SCALES):
            w = toks[j][1]
            if w in SCALES:
                cur = (cur or 1) * SCALES[w]
                if SCALES[w] > 100:
                    total, cur = total + cur, 0
            else:
                cur += UNITS.get(w, 0) + TENS.get(w, 0)
            j += 1
            if re.search(r"[,.?!;]$", words[toks[j - 1][0]]["w"]):
                break  # "eighty, eighteen" is two numbers
        if j > k:
            groups.append((k, j - 1, total + cur, None))
            k = j
        else:
            k += 1
    found = []
    for (a0, a1, va, ua), (b0, b1, vb, ub) in zip(groups, groups[1:]):
        between = b0 - a1 - 1
        if va == vb or between > 2 or words[toks[b0][0]]["s"] - words[toks[a1][0]]["e"] > 2.0:
            continue
        unit = lambda e, u: u or (toks[e + 1][1] if e + 1 < len(toks) else None)  # noqa: E731
        same_unit = between > 0 and unit(a1, ua) == unit(b1, ub)
        adjacent = between == 0 and abs(va - vb) != 1  # "three, four times" is an estimate, not a correction
        if same_unit or adjacent:
            said = lambda x, y: " ".join(words[toks[m][0]]["w"] for m in range(x, y + 1))  # noqa: E731
            found.append({"kind": "number", "i": toks[a0][0], "note": f"{said(a0, a1)!r} then {said(b0, b1)!r}: keep the second"})
    return found, 0


RULES = {"retake": find_retakes, "repeat": find_repeats, "restart": find_restarts, "number": find_numbers}


def find(words: list[dict], window: float, ratio: float) -> tuple[list[dict], list[tuple[int, int]], int]:
    spans = sentence_spans(words)
    found, rhetoric = [], 0
    for rule in RULES.values():
        got, skipped = rule(words, spans, window, ratio)
        found += got
        rhetoric += skipped
    # A cut of an earlier take removes whatever stumbles it held: name those once.
    taken = [(c["i"], next(b for a, b in spans if a == c["i"])) for c in found if c["kind"] == "retake"]
    found = [c for c in found if c["kind"] == "retake" or not any(a <= c["i"] <= b for a, b in taken)]
    once = {(c["kind"], c["i"]): c for c in reversed(found)}  # three takes name the first one once
    return sorted(once.values(), key=lambda c: c["i"]), spans, rhetoric


def retakes(transcript: str, window: float, ratio: float) -> int:
    words = heard_words(transcript)
    found, spans, rhetoric = find(words, window, ratio)
    at = {i: k for k, (a, b) in enumerate(spans) for i in range(a, b + 1)}
    line = lambda k: f"{clock(words[spans[k][0]]['s'])}  " + " ".join(w["w"] for w in words[spans[k][0]:spans[k][1] + 1])  # noqa: E731
    for c in found:
        k = at[c["i"]]
        print(f"{clock(words[c['i']]['s'])}  {c['kind']:<7}  {c['note']}")
        for m in (k - 1, k, k + 1):
            if 0 <= m < len(spans):
                print(f"   {'>>' if m == k else '  '} {line(m)}")
        if "later" in c and at[c["later"][0]] != k + 1:
            print(f"   == {line(at[c['later'][0]])}")
    kinds = {kind: sum(c["kind"] == kind for c in found) for kind in RULES}
    print(f"{len(found)} candidate(s) in {len(spans)} sentences: " + ", ".join(f"{n} {kind}" for kind, n in kinds.items())
          + f"; {rhetoric} similar pair(s) passed over as rhetoric (same frame, different content)"
          + ("\nleads, not cuts: listen to each before cutting" if found else ""))
    return 1 if found else 0


def synthetic() -> tuple[list[dict], dict[str, float]]:
    """A transcript with one planted retake of each kind, and the rhetoric and doubles that must not count."""
    text = [
        "What will they keep?",                             # a refrain, said again below: must not count
        "Today I want to talk about the soil in which a garden grows.",
        "The gardener cannot make the",                    # retake: the broken first take
        "The gardener cannot make the plant grow any faster.",
        "It is not about the grades.",                     # rhetoric: must not count
        "It is not about the scores.",
        "And I I think this is where it starts.",           # repeat
        "Every person in the s studio wants to be seen.",  # repeat: a fragment
        "It was very very hard for them at first.",        # a double on purpose: must not count
        "So we have to we have to let them struggle.",     # restart
        "About eighty percent, eighteen percent of them came back.",  # number
        "They tried it three, four times before it held.",  # an estimate: must not count
        "Where am I? Where am I going?",                    # questions in a row, not a restart
        "That is what they keep when the course is over.",
        "So what will they keep?",
    ]
    words, t, planted = [], 1.0, {}
    marks = {2: ("retake", 0), 6: ("repeat", 1), 7: ("repeat", 4), 9: ("restart", 1), 10: ("number", 1)}
    for k, sentence in enumerate(text):
        for n, w in enumerate(sentence.split()):
            if marks.get(k, (None, -1))[1] == n:
                planted[f"{marks[k][0]}@{k}"] = round(t, 3)
            words.append({"w": w, "s": round(t, 3), "e": round(t + 0.3, 3)})
            t += 0.35
        t += 0.9
    return words, planted


def selftest() -> int:
    words, planted = synthetic()
    found, _, rhetoric = find(words, 120, 0.62)
    got = {(c["kind"], round(words[c["i"]]["s"], 3)) for c in found}
    want = {(key.split("@")[0], at) for key, at in planted.items()}
    for kind, at in sorted(want, key=lambda x: x[1]):
        print(f"{'ok  ' if (kind, at) in got else 'MISS'} {kind:<7} planted at {clock(at)}")
    extra = sorted(got - want, key=lambda x: x[1])
    for kind, at in extra:
        text = next(c["note"] for c in found if c["kind"] == kind and round(words[c["i"]]["s"], 3) == at)
        print(f"NOISE {kind:<7} at {clock(at)}: {text}")
    missed = want - got
    print(f"selftest: {len(want) - len(missed)} of {len(want)} planted found, {len(extra)} false candidate(s), "
          f"{rhetoric} rhetorical pair(s) passed over")
    return 1 if missed or extra or rhetoric < 2 else 0


def usage() -> None:
    print(__doc__, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    args, opts, pos, k = sys.argv[1:], {}, [], 0
    while k < len(args):
        a = args[k]
        if a.startswith("--"):
            key, eq, value = a[2:].partition("=")
            if not eq:
                k += 1
                value = args[k] if k < len(args) else ""
            try:
                opts[key] = float(value)
            except ValueError:
                usage()
        else:
            pos.append(a)
        k += 1
    need = {"splice": 3, "clipped": 2, "dropped": 2, "sync": 2, "retakes": 1, "selftest": 0}
    if not pos or pos[0] not in need or len(pos) - 1 < need[pos[0]]:
        usage()
    cmd = pos[0]
    if cmd == "splice":
        sys.exit(splice(*pos[1:4]))
    if cmd == "clipped":
        sys.exit(clipped(*pos[1:4]))
    if cmd == "dropped":
        sys.exit(dropped(pos[1], pos[2], opts.get("noise", -38), opts.get("min", 0.25), opts.get("edge", 0.5)))
    if cmd == "retakes":
        sys.exit(retakes(pos[1], opts.get("window", 120), opts.get("ratio", 0.62)))
    if cmd == "selftest":
        sys.exit(selftest())
    sys.exit(sync(*pos[1:3]))
