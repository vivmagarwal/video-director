#!/usr/bin/env python3
"""Turn a plan and a word-timed transcript into edit.json, the only file the film reads.

usage: python3 tools/build-edit.py edit/plan.py

Every editorial decision lives in the plan. Change one, run this again, look at a
still. It stops by name rather than ship a quiet fault: a chapter inside a clip,
an overlay anchored on words that were cut, a frame that would play twice, a
correction that matches no segment.

Times in the plan are on the clock of the file the transcript was made from.
Write them as "m:ss.ss" or "h:mm:ss.ss".
"""
from __future__ import annotations

import difflib
import json
import math
import pathlib
import re
import runpy
import subprocess
import sys

P = runpy.run_path(sys.argv[1])
FPS = P["FPS"]
FILLERS = P.get("FILLERS", {"uh", "um", "uhm", "er", "erm", "ah", "hmm"})
KEEP_IF_UNDER = P.get("KEEP_IF_UNDER", 0.42)  # a shorter pause is the speaker's rhythm
PAUSE_IN_SENTENCE = P.get("PAUSE_IN_SENTENCE", 0.30)
PAUSE_AT_STOP = P.get("PAUSE_AT_STOP", 0.50)
PRE = P.get("PRE", 0.08)  # the least kept before a word
POST = P.get("POST", 0.14)  # the least kept after a word
CHAPTER_S, TITLE_S, END_S = P.get("CHAPTER_S", 3.0), P.get("TITLE_S", 4.5), P.get("END_S", 9.0)
CONTENT_CUTS = P.get("CONTENT_CUTS", [])
KEEP = P.get("KEEP")  # long sessions: the passages to keep, in film order; the rest is left out
CORRECTIONS = P.get("CORRECTIONS", {})
MISSED_WORDS = P.get("MISSED_WORDS", [])
HITS = {w.lower() for w in P.get("HITS", [])}
VIEW = P.get("view", lambda who, sec: None)
CUT_ZOOM, TEASER_ZOOM = P.get("CUT_ZOOM", (1.0, 1.07)), P.get("TEASER_ZOOM", (1.10, 1.15))
PAGE_WORDS, PAGE_CHARS = P.get("PAGE_WORDS", 7), P.get("PAGE_CHARS", 42)
LAST_HOLD = P.get("LAST_HOLD", 0.8)  # seconds of breath after the last word, before the end card


def t(clock: str) -> float:
    """'7:44.1' or '1:02:03.5' -> seconds."""
    sec = 0.0
    for part in str(clock).split(":"):
        sec = sec * 60 + float(part)
    return sec


def norm(word: str) -> str:
    return re.sub(r"[^a-z0-9']", "", word.lower())


def seg_key(s: float) -> str:
    m, x = divmod(s, 60)
    return f"{int(m)}:{x:05.2f}"


def size_of(path: str) -> list[int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", "public/" + path], capture_output=True, text=True).stdout.strip()
    if "," not in out:
        raise SystemExit(f"cannot read public/{path}: make the working copy first")
    return [int(x) for x in out.split(",")[:2]]


def seconds_of(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "public/" + path],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def load_words() -> tuple[list[dict], list[dict]]:
    segs = json.loads(pathlib.Path(P["TRANSCRIPT"]).read_text())["segments"]
    # Speech the recogniser never heard: without these the cutter takes it for a pause.
    for a, b, text in MISSED_WORDS:
        toks, s0, e0 = text.split(), t(a), t(b)
        step = (e0 - s0) / len(toks)
        ws = [{"w": w, "s": round(s0 + i * step, 3), "e": round(s0 + (i + 1) * step, 3)} for i, w in enumerate(toks)]
        segs.append({"start": s0, "end": e0, "text": text, "words": ws})
    segs.sort(key=lambda x: x["start"])
    return segs, [dict(w) for s in segs for w in s["words"]]


def corrected_words(segs: list[dict]) -> list[dict]:
    """The caption words: the recogniser's, with each corrected segment re-aligned to its times."""
    out: list[dict] = []
    used = set()
    for seg in segs:
        key, asr = seg_key(seg["start"]), seg["words"]
        text = CORRECTIONS.get(key)
        if text is None:
            out.extend(dict(w) for w in asr)
            continue
        used.add(key)
        toks = text.split()
        times: list = [None] * len(toks)
        sm = difflib.SequenceMatcher(None, [norm(w["w"]) for w in asr], [norm(x) for x in toks], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    times[j1 + k] = (asr[i1 + k]["s"], asr[i1 + k]["e"])
            elif tag == "replace":
                s0, e0 = asr[i1]["s"], asr[i2 - 1]["e"]
                weights = [max(1, len(toks[j])) for j in range(j1, j2)]
                total, acc = sum(weights), s0
                for n, j in enumerate(range(j1, j2)):
                    d = (e0 - s0) * weights[n] / total
                    times[j] = (acc, acc + d)
                    acc += d
        # Inserted words take a share of the time between their neighbours.
        for j, tm in enumerate(times):
            if tm is None:
                prev_e = next((times[k][1] for k in range(j - 1, -1, -1) if times[k]), seg["start"])
                nxt = next((k for k in range(j + 1, len(times)) if times[k]), None)
                next_s = times[nxt][0] if nxt is not None else seg["end"]
                span = max(0.12, next_s - prev_e)
                run = [k for k in range(j, nxt if nxt is not None else len(times)) if times[k] is None]
                for n, k in enumerate(run):
                    times[k] = (prev_e + span * n / len(run), prev_e + span * (n + 1) / len(run))
        who = asr[0].get("who")
        out.extend({"w": tok, "s": round(tm[0], 3), "e": round(tm[1], 3), **({"who": who} if who else {})}
                   for tok, tm in zip(toks, times))
    missing = set(CORRECTIONS) - used
    if missing:
        raise SystemExit(f"corrections name segments that do not exist: {sorted(missing)}; "
                         f"a key is a segment's start as m:ss.ss")
    return out


def keep_ranges(words: list[dict], cuts: list[tuple[float, float]]) -> list[list]:
    """Source ranges in seconds [a, b, who]: fillers and cuts out, pauses compressed."""
    def dropped(w: dict) -> bool:
        mid = (w["s"] + w["e"]) / 2
        return norm(w["w"]) in FILLERS or any(a <= mid < b for a, b in cuts)

    flags = [dropped(w) for w in words]
    ranges: list[list] = []
    prev = None  # index of the last kept word
    for i, w in enumerate(words):
        if flags[i]:
            continue
        if prev is None:
            ranges.append([max(0.0, w["s"] - PRE), w["e"] + POST, w.get("who")])
            prev = i
            continue
        p = words[prev]
        gap = w["s"] - p["e"]
        between = [words[k] for k in range(prev + 1, i) if flags[k]]
        if not between and gap <= KEEP_IF_UNDER:
            if w.get("who") != p.get("who"):  # a change of voice in flow: split, with no sound lost
                m = (p["e"] + w["s"]) / 2
                ranges[-1][1] = m
                ranges.append([m, w["e"] + POST, w.get("who")])
            else:
                ranges[-1][1] = w["e"] + POST
        else:
            target = PAUSE_AT_STOP if p["w"].rstrip().endswith((".", "?", "!")) else PAUSE_IN_SENTENCE
            post, pre = max(POST, 0.62 * target), max(PRE, 0.38 * target)
            if between:
                post = min(post, max(0.04, between[0]["s"] - p["e"]))
                pre = min(pre, max(0.04, w["s"] - between[-1]["e"]))
            if gap <= post + pre and not between and w.get("who") == p.get("who"):
                ranges[-1][1] = w["e"] + POST
            else:
                ranges[-1][1] = min(p["e"] + post, w["s"] - pre) if gap > post + pre else (p["e"] + w["s"]) / 2
                ranges.append([max(ranges[-1][1], w["s"] - pre), w["e"] + POST, w.get("who")])
        prev = i
    return ranges


def to_frames(ranges: list[list]) -> list[list]:
    fr: list[list] = []
    for a, b, who in ranges:
        fa, fb = math.floor(a * FPS), math.ceil(b * FPS)
        if fr and fa <= fr[-1][1] + 1 and fr[-1][2] == who and fa >= fr[-1][0]:  # two frames apart or less: one clip
            fr[-1][1] = max(fr[-1][1], fb)
        else:
            if fr and fr[-1][0] <= fa < fr[-1][1]:  # another voice in flow: start where the last clip ends
                fa = fr[-1][1]
            if fb > fa:
                fr.append([fa, fb, who])
    return fr


def complement(passages: list[tuple[float, float]], end: float) -> list[tuple[float, float]]:
    out, at = [], 0.0
    for a, b in sorted(passages):
        if a > at:
            out.append((at, a))
        at = max(at, b)
    return out + ([(at, end)] if end > at else [])


def main() -> None:
    segs, words = load_words()
    cap_words = corrected_words(segs)
    src_len = segs[-1]["end"]
    cuts = [(t(a), t(b)) for a, b, _ in CONTENT_CUTS]

    # --- the body, in film order ------------------------------------------------
    if KEEP:
        passages = [(t(a), t(b)) for a, b in KEEP]
        body = []
        for a, b in passages:
            inside = [w for w in words if a <= (w["s"] + w["e"]) / 2 < b]
            body += to_frames([[max(x, a), min(y, b), who] for x, y, who in keep_ranges(inside, cuts)])
        left_out = complement(passages, src_len + 1)
    else:
        body = to_frames(keep_ranges(words, cuts))
        left_out = []
    # A breath after the last word, stopping short of the next word, cut or passage end.
    last_end = body[-1][1] / FPS
    limits = [w["s"] - PRE for w in words if w["s"] >= last_end]
    limits += [max(a, last_end) for a, b in cuts if b > last_end] + ([max(b for _, b in passages)] if KEEP else [])
    stop = min(limits, default=seconds_of(next(iter(P["SOURCES"].values()))))
    body[-1][1] = max(body[-1][1], math.floor(min(last_end + LAST_HOLD, stop) * FPS))
    seen = sorted((a, b) for a, b, _ in body)
    for (a0, b0), (a1, _) in zip(seen, seen[1:]):
        if a1 < b0:
            raise SystemExit(f"frames at {a1 / FPS:.2f} s would play twice; check KEEP and the pauses")

    # --- chapters open on the nearest clip -------------------------------------
    opens: dict[int, tuple] = {}
    cursor_i = 0
    for ch in P.get("CHAPTERS", []):
        f = round(t(ch[0]) * FPS)
        # A chapter time inside a clip splits it, as long as it lands between two words.
        for i, (a, b, who) in enumerate(body):
            if a + 2 < f < b - 2 and not KEEP:
                if any(w["s"] < t(ch[0]) - 0.02 and t(ch[0]) + 0.02 < w["e"] for w in words):
                    raise SystemExit(f"chapter {ch[1]} at {ch[0]} falls inside a word; move it to a pause")
                body[i:i + 1] = [[a, f, who], [f, b, who]]
                break
        idx = min(range(cursor_i, len(body)), key=lambda i: abs(body[i][0] - f), default=None)
        if idx is None or abs(body[idx][0] - f) > 2 * FPS:
            raise SystemExit(f"chapter {ch[1]} at {ch[0]} falls outside what is kept; move it to a pause")
        opens[idx] = ch
        cursor_i = idx + 1

    # --- the timeline -----------------------------------------------------------
    clips: list[dict] = []
    cursor, teaser_items = 0, []
    for n, item in enumerate(P.get("TEASER", [])):
        start = cursor
        for a, b in item["ranges"]:
            fa, fb = round(t(a) * FPS), round(t(b) * FPS)
            who = next((w.get("who") for w in words if t(a) <= w["s"] < t(b)), None)
            clips.append({"section": "teaser", "from": cursor, "dur": fb - fa, "src": fa, "scale": TEASER_ZOOM[n % 2],
                          **({"who": who} if who else {}), **({"view": VIEW(who, t(a))} if VIEW(who, t(a)) else {})})
            cursor += fb - fa
        teaser_items.append({"from": start, "dur": cursor - start, "keyword": item["keyword"], "side": item.get("side", "right")})
    title = {"from": cursor, "dur": round(TITLE_S * FPS), **P["TITLE"]}
    cursor += title["dur"]
    chapters, body_from = [], cursor
    z, last_end = 0, None
    for i, (a, b, who) in enumerate(body):
        if i in opens:
            at, num, name, sub = opens[i]
            chapters.append({"from": cursor, "dur": round(CHAPTER_S * FPS), "number": num, "title": name, "subtitle": sub})
            cursor += round(CHAPTER_S * FPS)
            last_end = None
        if last_end is not None and a - last_end >= 6:  # a jump cut reads as a new angle
            z = 1 - z
        view = VIEW(who, a / FPS)
        clips.append({"section": "body", "from": cursor, "dur": b - a, "src": a, "scale": CUT_ZOOM[z],
                      **({"who": who} if who else {}), **({"view": view} if view else {})})
        cursor += b - a
        last_end = b
    body_to = cursor
    end = {"from": cursor, "dur": round(END_S * FPS), **P["END"]}
    total = cursor + end["dur"]
    body_clips = [c for c in clips if c["section"] == "body"]

    def out_frame(clock: str) -> int:
        """Where a moment of the raw take lands in the film. An anchor that was cut stops the build."""
        sec = t(clock)
        f = sec * FPS
        for c in body_clips:
            if c["src"] <= f < c["src"] + c["dur"]:
                return c["from"] + round(f - c["src"])
        near = [c for c in body_clips if 0 < c["src"] - f <= FPS]
        if not near:
            raise SystemExit(f"an overlay is anchored at {clock}, which no kept passage holds")
        return min(near, key=lambda c: c["src"])["from"]

    lists = []
    for s in P.get("LISTS", []):
        f0, f1 = out_frame(s["start"]), out_frame(s["end"])
        lists.append({"from": f0, "dur": f1 - f0, "kicker": s["kicker"], "title": s["title"],
                      "items": [{"at": out_frame(at) - f0 - 4, "text": text} for at, text in s["items"]]})
    quotes = [{"from": out_frame(q["start"]), "dur": out_frame(q["end"]) - out_frame(q["start"]), "lines": q["lines"]}
              for q in P.get("QUOTES", [])]
    plates = [{"from": out_frame(at), "dur": round(5 * FPS), "name": name, "role": role}
              for at, name, role in P.get("NAME_PLATES", [])]
    chats = [{"from": out_frame(at), "dur": round(P.get("CHAT_S", 6) * FPS), "name": name, "text": text}
             for at, name, text in P.get("CHAT", [])]

    # --- captions: every kept word, wherever its clip plays --------------------
    captions = []
    for c in clips:
        a, b = c["src"] / FPS, (c["src"] + c["dur"]) / FPS
        base = c["from"] / FPS - a
        for w in cap_words:
            mid = (w["s"] + w["e"]) / 2
            if a <= mid < b and norm(w["w"]) not in FILLERS:
                captions.append({"text": w["w"], "startMs": round((max(w["s"], a) + base) * 1000),
                                 "endMs": round((min(w["e"], b) + base) * 1000), **({"who": w["who"]} if w.get("who") else {})})
    captions.sort(key=lambda x: x["startMs"])

    # --- caption pages: a few words at a time, none under a full-frame quote ---
    pages: list[dict] = []
    # A page never runs across a teaser line, so no word shows before its own shot.
    breaks = {i["from"] for i in teaser_items} | {title["from"], body_from}
    for cap in captions:
        f0 = cap["startMs"] * FPS // 1000
        if any(q["from"] <= f0 < q["from"] + q["dur"] for q in quotes):
            continue
        word = {"t": cap["text"], "from": f0, "hit": norm(cap["text"]) in HITS}
        p = pages[-1] if pages else None
        if p:
            chars = sum(len(x["t"]) + 1 for x in p["words"]) + len(cap["text"])
            stop = p["words"][-1]["t"].rstrip().endswith((".", "?", "!"))
            gap = f0 - p["to"]
            crossed = any(p["from"] < x <= f0 for x in breaks)
        if not p or crossed or stop or gap > 0.6 * FPS or len(p["words"]) >= PAGE_WORDS or chars > PAGE_CHARS or p.get("who") != cap.get("who"):
            pages.append({"from": f0, "to": 0, "words": [word], **({"who": cap["who"]} if cap.get("who") else {})})
        else:
            p["words"].append(word)
        pages[-1]["to"] = max(f0 + 1, cap["endMs"] * FPS // 1000)
    for x, y in zip(pages, pages[1:]):  # a page holds until the next one, across a short gap
        if y["from"] - x["to"] < 0.4 * FPS:
            x["to"] = y["from"]
    for x in pages:
        x["to"] = max(x["to"], x["from"] + round(0.5 * FPS))

    sources = P["SOURCES"]
    data = {
        "fps": FPS, "durationInFrames": total, "width": P.get("WIDTH", 1920), "height": P.get("HEIGHT", 1080),
        "sources": sources, "sizes": {k: size_of(v) for k, v in sources.items()},
        "voice": P.get("VOICE"), "bed": P.get("BED"),
        "colors": P.get("COLORS", {}),
        "clips": clips, "teaser": teaser_items, "title": title, "chapters": chapters,
        "body": {"from": body_from, "to": body_to}, "end": end,
        "lists": lists, "quotes": quotes, "plates": plates, "chats": chats, "captions": captions, "pages": pages,
        # What was taken out on purpose, in seconds of the raw take, so that
        # tools/check-edit.py can tell a deliberate cut from lost speech.
        "removed": {
            "cuts": [{"from": t(a), "to": t(b), "why": why} for a, b, why in CONTENT_CUTS]
            + [{"from": a, "to": b, "why": "left out on purpose"} for a, b in left_out],
            "fillers": [[w["s"], w["e"]] for w in words if norm(w["w"]) in FILLERS],
        },
    }
    pathlib.Path(P["OUT"]).write_text(json.dumps(data, indent=1) + "\n")
    kept = sum(b - a for a, b, _ in body) / FPS
    cut_count = sum(y["src"] != x["src"] + x["dur"] for x, y in zip(body_clips, body_clips[1:]))
    print(f"raw {src_len / 60:.1f} min -> body {kept / 60:.1f} min ({src_len - kept:.0f} s out, {cut_count} cuts)")
    print(f"teaser {title['from'] / FPS:.1f} s, total {total / FPS / 60:.2f} min ({total} frames), {len(captions)} caption words, {len(pages)} pages")
    print("chapters at " + (", ".join(f"{int(c['from'] / FPS // 60)}:{int(c['from'] / FPS % 60):02d}" for c in chapters) or "none"))
    print(f"wrote {P['OUT']}")


if __name__ == "__main__":
    main()
