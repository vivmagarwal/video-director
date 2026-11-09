#!/usr/bin/env python3
"""Before a multicam edit: what each file is, what it shows, and how the clocks line up.

usage: which-is-which.py <out-dir> <file> [<file> ...] [--shots 6] [--align-minutes 10]

A session often arrives as several recordings of one event (Zoom's gallery,
active-speaker and shared-screen exports; a phone and a camera) plus text that
came with them (a transcript with speaker names, captions, the chat). Nothing
about the edit can be planned until each file's role is known, and a file name
is a hint, not an answer. This prints, for every file:

- what it is: duration, picture size and rate, whether it has sound, and what
  its name says (Zoom's export suffixes are decoded; see ZOOM below);
- for a transcript or chat: how many cues or lines, and the names in it;
- where its sound sits against the first file with sound: "starts 12.34 s
  later", found by correlating loudness envelopes (a coarse 10 Hz search over
  +-120 s, then 100 Hz around the best lag, over `--align-minutes` from where
  the first file's sound starts, so a silent waiting room does not count).
  `match` is the peak over the runner-up; under 1.3 the files probably do not
  share sound, and the offset means nothing.

It writes `sheet-<n>.png` (one strip per video: the same moments of the event
in every strip, shifted by the offset wherever the sound matched, so each
column is one instant seen by every camera), `all.png` (every strip stacked in the
printed order) and `sources.json` (the facts, with an empty `role` for each
file, to fill in once you have looked). LOOK at `all.png` before deciding
anything: which file is the gallery, who sits in which tile, when the grid
changes, which one carries the slides, whose camera is off.

Needs ffmpeg and ffprobe on PATH. Standard library only.
"""

from __future__ import annotations

import array
import json
import math
import pathlib
import re
import subprocess
import sys

# Zoom cloud-recording export suffixes, as they appear in the file names.
ZOOM = [
    (r"_gvo_", "Zoom gallery view: every camera in a grid. The face source; it re-grids when a camera turns on or off"),
    (r"_avo_", "Zoom active-speaker view: whoever Zoom thinks is talking. It lags and mis-picks; never the picture base"),
    (r"_as_", "Zoom shared screen only: the slides or screen, black when nothing is shared"),
    (r"_gallery_", "Zoom shared screen with a gallery thumbnail"),
    (r"audio_only|\.m4a$", "audio only"),
    (r"\.transcript\.vtt$", "Zoom transcript: cues with speaker names"),
    (r"\.cc\.vtt$", "Zoom closed captions: cues without speaker names"),
    (r"chat.*\.txt$|\.chat\.txt$", "Zoom chat"),
    (r"gallery", "a gallery (grid) view, by its name"),
    (r"speaker", "an active-speaker view, by its name"),
    (r"shared_screen|screen", "a screen recording, by its name"),
    (r"_\d{3,4}x\d{3,4}\.mp4$", "Zoom shared screen with the active speaker's thumbnail (by the size-only suffix)"),
]

TEXT = {".vtt", ".srt", ".txt", ".json", ".csv", ".md", ".sbv"}


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, **kw)


def probe(path: pathlib.Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], text=True)
    if r.returncode:
        return {}
    j = json.loads(r.stdout)
    out: dict = {"duration": float(j.get("format", {}).get("duration") or 0)}
    for s in j.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in out and s.get("disposition", {}).get("attached_pic") != 1:
            num, _, den = (s.get("avg_frame_rate") or "0/1").partition("/")
            out.update(width=s["width"], height=s["height"], fps=round(float(num) / float(den or 1), 3) if float(den or 1) else 0, vcodec=s.get("codec_name"))
        if s.get("codec_type") == "audio" and "audio" not in out:
            out["audio"] = f"{s.get('codec_name')} {s.get('sample_rate')} Hz {s.get('channels')} ch"
    return out


def guess(name: str) -> str:
    for pat, what in ZOOM:
        if re.search(pat, name, re.I):
            return what
    return ""


def read_text(path: pathlib.Path) -> dict:
    """Cue or line counts and the speaker names a transcript or chat carries."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return {}
    names: dict[str, int] = {}
    if path.suffix.lower() == ".vtt" or text.startswith("WEBVTT"):
        cues = len(re.findall(r"-->", text))
        for m in re.finditer(r"^(?:\d+\n)?[\d:.]+ --> [\d:.]+[^\n]*\n([^:\n]{1,40}):", text, re.M):
            names[m.group(1).strip()] = names.get(m.group(1).strip(), 0) + 1
        return {"cues": cues, "names": names}
    lines = [ln for ln in text.splitlines() if ln.strip()]
    # Zoom chat, old and new layouts: "10:02:03 From Name to Everyone:" / "10:02:03\tName:\tmessage"
    for ln in lines:
        m = re.match(r"^\d{1,2}:\d{2}:\d{2}\s+From\s+(.+?)\s+to\s+", ln) or re.match(r"^\d{1,2}:\d{2}:\d{2}\t([^\t:]{1,40}):", ln)
        if m:
            names[m.group(1).strip()] = names.get(m.group(1).strip(), 0) + 1
    return {"lines": len(lines), "names": names}


def sound_starts(path: pathlib.Path, within_s: float = 3600) -> float:
    """Where the sound starts: the end of a silence that opens the file, else 0.

    A Zoom cloud recording often opens on minutes of digital silence (the
    waiting room). Silence looks the same at every offset, so an alignment
    window that is mostly silence finds no clear peak even between two files
    carrying identical sound.
    """
    r = run(["ffmpeg", "-v", "info", "-t", str(within_s), "-i", str(path), "-vn", "-af", "silencedetect=n=-50dB:d=2", "-f", "null", "-"], text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    if starts and starts[0] <= 0.5 and ends:
        return ends[0]
    return 0.0


def envelope(path: pathlib.Path, minutes: float, rate: int, start_s: float = 0.0) -> list[float]:
    """Log loudness at `rate` values a second over `minutes` from `start_s`."""
    sr = 8000
    r = run(["ffmpeg", "-v", "error", "-ss", f"{start_s:.3f}", "-t", str(minutes * 60), "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"])
    if r.returncode or not r.stdout:
        return []
    pcm = array.array("h")
    pcm.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    step = sr // rate
    env = []
    for i in range(0, len(pcm) - step + 1, step):
        chunk = pcm[i : i + step]
        env.append(math.log10(1 + sum(x * x for x in chunk) / step))
    return env


def normalise(v: list[float]) -> list[float]:
    if not v:
        return v
    mean = sum(v) / len(v)
    sd = math.sqrt(sum((x - mean) ** 2 for x in v) / len(v)) or 1.0
    return [(x - mean) / sd for x in v]


def corr_at(a: list[float], b: list[float], lag: int) -> float:
    """Correlation of a[t] with b[t - lag] over their overlap."""
    lo, hi = max(0, lag), min(len(a), len(b) + lag)
    if hi - lo < 50:
        return -1.0
    return sum(a[t] * b[t - lag] for t in range(lo, hi)) / (hi - lo)


def align(ref: list[float], other: list[float], rate: int, max_s: float) -> tuple[float, float]:
    """Seconds to add to `other`'s clock to land on `ref`'s, and how clearly."""
    a, b = normalise(ref), normalise(other)
    lags = range(-int(max_s * rate), int(max_s * rate) + 1)
    scores = sorted(((corr_at(a, b, lag), lag) for lag in lags), reverse=True)
    best, lag = scores[0]
    # The runner-up must be a different peak, not the shoulder of this one.
    runner = next((s for s, l in scores[1:] if abs(l - lag) > rate), 0.0)
    return lag / rate, (best / runner if runner > 0 else float("inf"))


def shot(path: pathlib.Path, t: float, out: pathlib.Path) -> bool:
    vf = "scale=384:216:force_original_aspect_ratio=decrease,pad=384:216:(ow-iw)/2:(oh-ih)/2:color=0x202020"
    return run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1", "-vf", vf, str(out)]).returncode == 0 and out.exists()


def stack(images: list[pathlib.Path], out: pathlib.Path, how: str) -> bool:
    if len(images) == 1:
        out.write_bytes(images[0].read_bytes())
        return True
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for im in images:
        cmd += ["-i", str(im)]
    cmd += ["-filter_complex", f"{how}=inputs={len(images)}", "-frames:v", "1", str(out)]
    return run(cmd).returncode == 0


def fmt(s: float) -> str:
    s = max(0.0, s)
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}" if s >= 3600 else f"{int(s // 60)}:{s % 60:05.2f}"


def main() -> int:
    args = sys.argv[1:]
    shots_n, minutes = 6, 10.0
    if "--shots" in args:
        i = args.index("--shots")
        shots_n = int(args[i + 1])
        del args[i : i + 2]
    if "--align-minutes" in args:
        i = args.index("--align-minutes")
        minutes = float(args[i + 1])
        del args[i : i + 2]
    if len(args) < 2:
        print(__doc__)
        return 2
    out = pathlib.Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    files = [pathlib.Path(a) for a in args[1:]]
    missing = [f for f in files if not f.exists()]
    if missing:
        print("not found: " + ", ".join(map(str, missing)), file=sys.stderr)
        return 2

    facts = []
    for n, f in enumerate(files, 1):
        d: dict = {"n": n, "file": f.name, "path": str(f), "bytes": f.stat().st_size, "name_says": guess(f.name), "role": ""}
        if f.suffix.lower() in TEXT:
            d["kind"] = "text"
            d.update(read_text(f))
        else:
            d.update(probe(f))
            d["kind"] = "video" if "width" in d else ("audio" if "audio" in d else "unknown")
        facts.append(d)

    # Sound: every file with audio against the first one that has it.
    sounding = [d for d in facts if d.get("audio")]
    if len(sounding) > 1:
        # Every file is read from the same clock time, where the reference's
        # sound starts, so a shared silent opening cannot swamp the match.
        # Reading all of them from one time leaves the offsets unchanged.
        t0 = max(0.0, sound_starts(pathlib.Path(sounding[0]["path"])) - 5)
        ref = envelope(pathlib.Path(sounding[0]["path"]), minutes, 10, t0)
        ref_fine = envelope(pathlib.Path(sounding[0]["path"]), minutes, 100, t0)
        sounding[0]["offset_s"], sounding[0]["match"] = 0.0, None
        sounding[0]["sound_from_s"] = round(t0, 2)
        for d in sounding[1:]:
            coarse, match = align(ref, envelope(pathlib.Path(d["path"]), minutes, 10, t0), 10, 120)
            fine_other = envelope(pathlib.Path(d["path"]), minutes, 100, t0)
            a, b = normalise(ref_fine), normalise(fine_other)
            base = int(round(coarse * 100))
            _, lag = max((corr_at(a, b, base + k), base + k) for k in range(-20, 21))
            d["offset_s"], d["match"] = round(lag / 100, 2), round(match, 2)

    # Pictures: the same moments in every video, inside the shortest one.
    videos = [d for d in facts if d["kind"] == "video"]
    strips = []
    if videos:
        span = min(d["duration"] for d in videos if d.get("duration")) or 1
        times = [span * (0.03 + 0.94 * i / max(1, shots_n - 1)) for i in range(shots_n)]
        for d in videos:
            # Where the sound lines up, show the same moment of the event in
            # every row: the reference's time t is this file's t - offset.
            shift = d.get("offset_s", 0.0) if (d.get("match") or 0) >= 1.3 else 0.0
            d["shots_shifted_by_s"] = -shift
            frames = []
            for k, t in enumerate(times):
                p = out / f"shot-{d['n']}-{k}.png"
                ft = min(max(0.0, t - shift), max(0.0, d.get("duration", 0) - 0.1))
                if shot(pathlib.Path(d["path"]), ft, p):
                    frames.append(p)
            strip = out / f"sheet-{d['n']}.png"
            if frames and stack(frames, strip, "hstack"):
                strips.append(strip)
                d["sheet"] = str(strip)
            for p in frames:
                p.unlink()
        if strips:
            stack(strips, out / "all.png", "vstack")

    print("| # | file | kind | length | picture | sound | offset vs first with sound | the name says |")
    print("|---|---|---|---|---|---|---|---|")
    for d in facts:
        if d["kind"] == "text":
            size = f"{d.get('cues', d.get('lines', 0))} {'cues' if 'cues' in d else 'lines'}"
            who = ", ".join(f"{k} ({v})" for k, v in sorted(d.get("names", {}).items(), key=lambda kv: -kv[1])[:8])
            print(f"| {d['n']} | {d['file']} | text | {size} | | | | {d['name_says'] or ''}{' · names: ' + who if who else ''} |")
            continue
        pic = f"{d['width']}x{d['height']} {d.get('fps', '')} fps" if "width" in d else ""
        off = ""
        if "offset_s" in d:
            o = d["offset_s"]
            weak = d.get("match") is not None and d["match"] < 1.3
            off = "reference" if d["match"] is None else f"{'+' if o >= 0 else ''}{o:.2f} s (match {d['match']}){' - WEAK, check by ear' if weak else ''}"
        print(f"| {d['n']} | {d['file']} | {d['kind']} | {fmt(d.get('duration', 0))} | {pic} | {d.get('audio', 'none')} | {off} | {d['name_says']} |")
    if videos:
        print(f"\nshots at {', '.join(fmt(t) for t in times)} in every strip; rows of {out / 'all.png'} are files {', '.join(str(d['n']) for d in videos if 'sheet' in d)}, top to bottom")
        shifted = [str(d["n"]) for d in videos if d.get("shots_shifted_by_s")]
        if shifted:
            print(f"files {', '.join(shifted)} are shifted by their offset, so each column is one moment of the event")
    print("offset: add it to that file's time to get the reference's time. A positive offset means the file started later.")
    (out / "sources.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out / 'sources.json'}: fill in each file's `role` once you have looked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
