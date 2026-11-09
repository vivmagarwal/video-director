#!/usr/bin/env python3
"""Level each speaker on their own words, and write one dialogue track for the film.

usage: <venv>/bin/python tools/voices.py measure <audio.wav> <transcript.json>
       <venv>/bin/python tools/voices.py write <edit.json> <session48k.wav> <gains.json> <voice.wav>
       <venv>/bin/python tools/voices.py left <edit.json> <voice.wav>

Needs numpy and soundfile. The transcript's words carry `who` (tools/assign-speakers.py).

measure  Each speaker's voiced loudness over their own words (spans merged when
         under 1.0 s apart; RMS over 25 ms frames above -45 dBFS) and the gain that
         brings them to the speaker heard most. Prints JSON for gains.json.
write    Splices every clip of edit.json out of the session's sound at its gain,
         into one file the length of the film. A real splice gets a 2 ms fade in and
         out. Clips that follow each other in the source and in the film (a change
         of speaker in flow) get no fade, which would dip mid-word, but a 10 ms ramp
         between the two gains. Writes voice.part.wav, then renames, so a render or
         bundle can never take a half-written track.
left     The same measurement on the finished track: every speaker should be within
         0.5 dB of the reference.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf


def level(a, sr, spans):
    n = int(0.025 * sr)
    x = np.concatenate([a[int(p * sr):int(q * sr)] for p, q in spans])
    r = np.sqrt((x[: len(x) // n * n].reshape(-1, n) ** 2).mean(1))
    v = r[r > 10 ** (-45 / 20)]
    return float(20 * np.log10(np.sqrt((v ** 2).mean()))) if len(v) else -120.0


def gains(a, sr, pairs):
    spans = {}
    for who, p, q in sorted(pairs, key=lambda x: x[1]):
        s = spans.setdefault(who, [])
        if s and p - s[-1][1] < 1.0:
            s[-1][1] = max(s[-1][1], q)
        else:
            s.append([p, q])
    lv = {w: level(a, sr, s) for w, s in spans.items()}
    ref = max(spans, key=lambda w: sum(q - p for p, q in spans[w]))
    return {w: round(lv[ref] - x, 1) for w, x in lv.items()}, ref


def read_mono(path):
    a, sr = sf.read(path, dtype="float32")
    return (a.mean(axis=1) if a.ndim > 1 else a), sr


cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "measure" and len(sys.argv) == 4:
    a, sr = read_mono(sys.argv[2])
    words = [w for s in json.load(open(sys.argv[3]))["segments"] for w in s["words"]]
    g, ref = gains(a, sr, [(w["who"], w["s"], w["e"]) for w in words])
    print(json.dumps(g, indent=1, ensure_ascii=False))
    print(f"reference: {ref}", file=sys.stderr)
elif cmd == "left" and len(sys.argv) == 4:
    a, sr = read_mono(sys.argv[3])
    e = json.load(open(sys.argv[2]))
    said = [(c["who"], c["startMs"] / 1000, c["endMs"] / 1000) for c in e["captions"] if c.get("who")]
    g, ref = gains(a, sr, said)
    print(json.dumps(g, ensure_ascii=False), "reference:", ref)
    sys.exit(1 if any(abs(x) > 0.5 for x in g.values()) else 0)
elif cmd == "write" and len(sys.argv) == 6:
    e = json.load(open(sys.argv[2]))
    a, sr = read_mono(sys.argv[3])
    table = json.load(open(sys.argv[4]))
    f = e["fps"]
    out = np.zeros(round(e["durationInFrames"] / f * sr) + sr, dtype="float32")
    clips = sorted(e["clips"], key=lambda c: c["from"])
    fade, ramp = int(0.002 * sr), int(0.010 * sr)
    for i, c in enumerate(clips):
        x0, n = int(c["src"] / f * sr), int(c["dur"] / f * sr)
        chunk = a[x0:x0 + n].copy()
        g = 10 ** (table.get(c.get("who"), 0.0) / 20)
        env = np.full(len(chunk), g, dtype="float32")
        before = clips[i - 1] if i else None
        after = clips[i + 1] if i + 1 < len(clips) else None
        flows_in = before and before["src"] + before["dur"] == c["src"] and before["from"] + before["dur"] == c["from"]
        flows_out = after and c["src"] + c["dur"] == after["src"] and c["from"] + c["dur"] == after["from"]
        if flows_in:
            g0 = 10 ** (table.get(before.get("who"), 0.0) / 20)
            k = min(ramp, len(env))
            env[:k] = np.linspace(g0, g, k, dtype="float32")
        else:
            env[:fade] *= np.linspace(0, 1, min(fade, len(env)), dtype="float32")
        if not flows_out:
            env[-fade:] *= np.linspace(1, 0, min(fade, len(env)), dtype="float32")
        y0 = int(c["from"] / f * sr)
        out[y0:y0 + len(chunk)] = chunk * env
    out = out[: round(e["durationInFrames"] / f * sr)]
    part = sys.argv[5] + ".part.wav"
    sf.write(part, out, sr, subtype="PCM_16")
    os.replace(part, sys.argv[5])
    print(f"wrote {sys.argv[5]}: {len(out) / sr:.1f} s, peak {20 * np.log10(np.abs(out).max() + 1e-9):.1f} dBFS")
else:
    sys.exit(__doc__)
