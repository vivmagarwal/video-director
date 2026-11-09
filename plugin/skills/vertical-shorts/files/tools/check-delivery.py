#!/usr/bin/env python3
"""The delivery check: what a finished video must pass before it is uploaded or handed over.

  check-delivery.py <film.mp4> [--fps N] [--target LUFS] [--peak dBTP] [--no-loudness]
      Seven checks, one line each: PASS, WARN or FAIL, the check's id, and what
      was measured. --fps is the rate the film must run at (default: whatever
      the stream declares). Needs ffmpeg and ffprobe on PATH.
  check-delivery.py selftest
      Makes tiny films in a temp folder: one that must pass everything, one per
      defect that must fail on its own id and nothing else, and two that must
      only WARN. Run it once in a new machine to prove this ffmpeg can do the job.

Exits 1 when a check FAILs, 2 on a usage error or a file it cannot read. A WARN
never fails: it names a risk this script cannot measure.

  codec      H.264, yuv420p (not yuvj420p), limited ("tv") range, matrix,
             primaries and transfer BT.709. Matrix unset FAILS: players differ,
             and ffmpeg falls back to BT.601, so colours shift. Range unset
             passes: H.264 then means limited. Primaries or transfer unset WARN:
             only colour-managed players (QuickTime, Safari) read them.
  cfr        Every frame on the grid of the declared rate, within one tick.
  faststart  The top-level `moov` box comes before the first `mdat`.
  audio      Present, AAC, 48 kHz.
  av-length  Both streams start and end together and the audio has no holes,
             measured from packet timestamps, which is what a player schedules.
             A decoded sample count hides holes. The audio may end up to one
             frame plus one AAC frame after the picture. `loudnorm` can leave a
             hole near the end of a file unless its output is restamped
             (asetpts=N/SR/TB).
  flashes    WCAG 2.3.1's general flash: opposing changes in relative luminance
             of 0.10 or more, the darker state under 0.80, more than 3 in any one
             second. FAIL over a quarter of the screen together (the area
             broadcast rules use). WARN over a quarter of a 10-degree field
             (WCAG's own area), which natural motion such as hands near a lens
             can reach: look at the second it names. The red-flash rule is not
             checked.
  loudness   Integrated within 1 LU of --target (default -14) and true peak at or
             under --peak (default -1), read from loudnorm's own measurement.
             --no-loudness skips it.
"""

from __future__ import annotations

import collections
import json
import re
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from fractions import Fraction

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def clock(sec: float) -> str:
    m, s = divmod(max(0.0, sec), 60)
    return f"{int(m)}:{s:05.2f}"


def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise OSError(r.stderr.strip() or f"ffprobe could not read {path}")
    return json.loads(r.stdout)


def packets(path: str, stream: str) -> list[tuple[int, int]]:
    """(pts, duration) of every packet of one stream, in its timebase, sorted by pts."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries",
                          "packet=pts,duration", "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout
    got = []
    for line in out.split():
        f = line.strip(",").split(",")
        if f[0].lstrip("-").isdigit():
            got.append((int(f[0]), int(f[1]) if len(f) > 1 and f[1].isdigit() else 0))
    return sorted(got)


def rate(s: str | None) -> Fraction | None:
    try:
        f = Fraction(s)
        return f if f > 0 else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


# --------------------------------------------------------------------------- codec
def check_codec(v: dict) -> tuple[str, str]:
    got = {k: v.get(k) or "unset" for k in ("codec_name", "pix_fmt", "color_range", "color_space", "color_primaries", "color_transfer")}
    got = {k: ("unset" if x == "unknown" else x) for k, x in got.items()}
    fails, warns = [], []
    if got["codec_name"] != "h264":
        fails.append(f"codec {got['codec_name']}, want h264")
    if got["pix_fmt"] != "yuv420p":
        fails.append(f"pix_fmt {got['pix_fmt']}, want yuv420p" + (" (full range)" if got["pix_fmt"].startswith("yuvj") else ""))
    if got["color_range"] not in ("tv", "unset"):
        fails.append(f"range {got['color_range']}, want tv (limited)")
    if got["color_space"] != "bt709":
        fails.append(f"matrix {got['color_space']}, want bt709" + (" (players guess; ffmpeg picks BT.601)" if got["color_space"] == "unset" else ""))
    for k, name in (("color_primaries", "primaries"), ("color_transfer", "transfer")):
        if got[k] == "unset":
            warns.append(f"{name} unset")
        elif got[k] != "bt709":
            fails.append(f"{name} {got[k]}, want bt709")
    seen = f"{got['codec_name']} {got['pix_fmt']}, range {got['color_range']}" + (" (limited by default)" if got["color_range"] == "unset" else "") \
        + f", matrix {got['color_space']}, primaries {got['color_primaries']}, transfer {got['color_transfer']}"
    if fails:
        return FAIL, f"{seen}: " + "; ".join(fails + warns)
    if warns:
        return WARN, f"{seen}: " + "; ".join(warns) + " (colour-managed players guess; ffmpeg ignores them)"
    return PASS, seen


# --------------------------------------------------------------------------- cfr
def check_cfr(path: str, v: dict, want: Fraction | None) -> tuple[str, str]:
    r, avg = rate(v.get("r_frame_rate")), rate(v.get("avg_frame_rate"))
    fps = want or r
    tb = Fraction(v.get("time_base", "1/90000"))
    pk = packets(path, "v:0")
    if not fps or len(pk) < 2:
        return FAIL, f"no frame rate or too few frames to measure (r {v.get('r_frame_rate')}, {len(pk)} packets)"
    step = 1 / (fps * tb)  # ticks per frame, exact
    first = pk[0][0]
    dev = [p - first - i * step for i, (p, _) in enumerate(pk)]
    worst = max(dev, key=abs)
    steps = collections.Counter(b[0] - a[0] for a, b in zip(pk, pk[1:]))
    off = next((i for i, d in enumerate(dev) if abs(d) > 1), None)
    declared = f"r {v.get('r_frame_rate')}, avg {v.get('avg_frame_rate')}"
    problems = []
    if want and (r is None or abs(float(r - want)) > 0.01):
        problems.append(f"declares {v.get('r_frame_rate')}, want {float(want):g}")
    if r and avg and abs(float(r - avg)) > 0.01:
        problems.append("r_frame_rate and avg_frame_rate differ")
    if off is not None:
        problems.append(f"frame {off} at {float(pk[off][0] * tb):.3f} s is {float(dev[off] * tb) * 1000:+.1f} ms off the grid "
                        f"(worst {float(worst * tb) * 1000:+.1f} ms)")
    common = ", ".join(f"{float(s * tb) * 1000:.2f} ms x{n}" for s, n in steps.most_common(3))
    seen = f"{len(pk)} frames at {float(fps):g} fps ({declared}); spacing {common}"
    return (FAIL, f"{seen}: " + "; ".join(problems)) if problems else (PASS, seen)


# --------------------------------------------------------------------------- faststart
def top_boxes(path: str) -> list[tuple[str, int]]:
    boxes = []
    with open(path, "rb") as f:
        end = os.fstat(f.fileno()).st_size
        pos = 0
        while pos + 8 <= end:
            f.seek(pos)
            size, kind = struct.unpack(">I4s", f.read(8))
            if size == 1:
                size = struct.unpack(">Q", f.read(8))[0]
            elif size == 0:
                size = end - pos
            if size < 8:
                break
            boxes.append((kind.decode("latin1"), pos))
            pos += size
    return boxes


def check_faststart(path: str) -> tuple[str, str]:
    boxes = top_boxes(path)
    names = [b for b, _ in boxes]
    order = " ".join(names[:8])
    if "moov" not in names or "mdat" not in names:
        return FAIL, f"top-level boxes [{order}]: no moov and mdat, not an MP4 this can read"
    at = dict(reversed(boxes))
    if names.index("moov") < names.index("mdat"):
        return PASS, f"moov at byte {at['moov']:,}, before mdat at {at['mdat']:,} [{order}]"
    return FAIL, f"moov at byte {at['moov']:,}, after mdat at {at['mdat']:,} [{order}]: a player must fetch the end first (remux with -movflags +faststart)"


# --------------------------------------------------------------------------- audio
def check_audio(streams: list[dict]) -> tuple[str, str]:
    au = [s for s in streams if s.get("codec_type") == "audio"]
    if not au:
        return FAIL, "no audio stream"
    a = au[0]
    prof = {"1": "LC", "4": "HE", "28": "HEv2"}.get(str(a.get("profile")), a.get("profile"))  # this ffprobe prints numbers
    seen = f"{a.get('codec_name')}{' ' + prof if prof else ''}, {a.get('sample_rate')} Hz, {a.get('channels')} ch" \
        + (f", {int(a['bit_rate']) // 1000} kb/s" if str(a.get("bit_rate", "")).isdigit() else "") \
        + (f" ({len(au)} audio streams; the first is checked)" if len(au) > 1 else "")
    problems = []
    if a.get("codec_name") != "aac":
        problems.append("want aac")
    if a.get("sample_rate") != "48000":
        problems.append("want 48000 Hz")
    return (FAIL, f"{seen}: " + ", ".join(problems)) if problems else (PASS, seen)


# --------------------------------------------------------------------------- av-length
def check_av_length(path: str, v: dict, streams: list[dict], fps: Fraction | None) -> tuple[str, str]:
    au = [s for s in streams if s.get("codec_type") == "audio"]
    if not au:
        return FAIL, "no audio stream to compare"
    a = au[0]
    frame = float(1 / fps) if fps else 0.04
    vtb, atb = Fraction(v["time_base"]), Fraction(a["time_base"])
    vp, ap = packets(path, "v:0"), packets(path, "a:0")
    # Packets that end at or before 0 are priming the edit list discards.
    ap = [(p, d) for p, d in ap if p + d > 0]
    if not vp or not ap:
        return FAIL, f"{len(vp)} video and {len(ap)} audio packets: nothing to compare"
    v0, v1 = float(vp[0][0] * vtb), float(max(p + d for p, d in vp) * vtb)
    a0, a1 = float(max(0, ap[0][0]) * atb), float(max(p + d for p, d in ap) * atb)
    # A hole: the next packet starts later than this one's samples end. In MP4 it
    # shows as one packet stamped longer than the codec's fixed frame; elsewhere
    # as a jump in pts. Either way everything after it plays that much late.
    fixed = a.get("codec_name") in ("aac", "mp3", "ac3", "eac3", "opus", "mp2")
    size = collections.Counter(d for _, d in ap).most_common(1)[0][0] if fixed else None
    shift, worst, holes = 0, (0, 0), []  # ticks: running shift, and (pts, shift) where it was largest
    for (p, d), (q, _) in zip(ap, ap[1:]):
        gap = q - p - (min(d, size) if size else d)
        if gap:
            shift += gap
            if abs(gap * atb) > 0.001:
                holes.append((float(p * atb), float(gap * atb)))
            if abs(shift) > abs(worst[1]):
                worst = (p, shift)
    worst = (float(worst[0] * atb), float(worst[1] * atb))
    aac_frame = 1024 / int(a.get("sample_rate") or 48000)
    d0, d1 = a0 - v0, a1 - v1
    seen = f"video {v0:.3f}-{v1:.3f} s, audio {a0:.3f}-{a1:.3f} s: audio starts {d0 * 1000:+.0f} ms, ends {d1 * 1000:+.0f} ms ({d1 / frame:+.1f} frames)"
    problems = []
    if abs(d0) > frame + 1e-6:
        problems.append(f"the audio starts {d0 * 1000:+.0f} ms from the picture (one frame is {frame * 1000:.0f} ms)")
    if d1 < -frame - 1e-6:
        problems.append(f"the audio stops {-d1 * 1000:.0f} ms before the picture")
    elif d1 > frame + aac_frame + 1e-6:
        problems.append(f"the audio runs {d1 * 1000:.0f} ms past the picture (allowed {(frame + aac_frame) * 1000:.0f}: one frame + one AAC frame)")
    if abs(worst[1]) > frame + 1e-6:
        big = max(holes, key=lambda h: abs(h[1]))
        problems.append(f"{len(holes)} hole(s) in the audio timeline, the largest {big[1] * 1000:+.0f} ms at {clock(big[0])}: "
                        f"from {clock(worst[0])} the audio plays {worst[1] * 1000:+.0f} ms off the picture (a filter restamped it; loudnorm's flush does)")
    elif holes:
        seen += f"; {len(holes)} small hole(s), at most {max(abs(h[1]) for h in holes) * 1000:.0f} ms"
    return (FAIL, f"{seen}; " + "; ".join(problems)) if problems else (PASS, seen)


# --------------------------------------------------------------------------- flashes
GRID = 12  # tiles per side: 144 tiles, and a 10-degree field is 4x4 of them
LIN = "255*if(lte(val/255\\,0.04045)\\,val/255/12.92\\,pow((val/255+0.055)/1.055\\,2.4))"
MIX = ":".join(f"{o}{i}={w}" for o in "rgb" for i, w in zip("rgb", ("0.2126", "0.7152", "0.0722")))
FLASH_VF = (f"scale=96:96:flags=area,format=gbrp,lutrgb=r='{LIN}':g='{LIN}':b='{LIN}',"
            f"colorchannelmixer={MIX},scale={GRID}:{GRID}:flags=area")


def check_flashes(path: str, fps: Fraction | None) -> tuple[str, str]:
    n = round(float(fps)) if fps else 25
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-map", "0:v:0", "-vf", FLASH_VF,
                             "-f", "rawvideo", "-pix_fmt", "gbrp", "-"], stdout=subprocess.PIPE)
    T = GRID * GRID
    # Each tile: the direction of its last transition (0 = none yet), the
    # extreme since then, and the low and high seen before its first.
    tdir, ext, lo, hi = [0] * T, [0.0] * T, [9.0] * T, [-9.0] * T
    fields = [(r, c) for r in range(GRID - 3) for c in range(GRID - 3)]
    windows: dict = {}  # the screen, or a field: [direction of its last transition, recent transition frames]
    worst = {"screen": (0, 0, None), "field": (0, 0, None)}
    prev_up, prev_dn, f = set(), set(), 0

    def register(tier: str, key, d: int) -> None:
        w = windows.setdefault(key, [0, collections.deque()])
        if w[0] == d:  # a flash is a pair of OPPOSING changes; the same way again is the same change
            return
        w[0] = d
        q = w[1]
        q.append(f)
        while q[0] <= f - n:
            q.popleft()
        if len(q) // 2 > worst[tier][0]:
            worst[tier] = (len(q) // 2, q[0], key)

    while True:
        buf = proc.stdout.read(T * 3)
        if len(buf) < T * 3:
            break
        up, dn = set(), set()
        for i in range(T):
            y = buf[i] / 255  # every plane holds the luminance; read the first
            d, darker = tdir[i], None
            if d == 0:
                lo[i], hi[i] = min(lo[i], y), max(hi[i], y)
                if hi[i] - y >= 0.10:
                    darker, tdir[i], ext[i] = y, -1, y
                elif y - lo[i] >= 0.10:
                    darker, tdir[i], ext[i] = lo[i], 1, y
            elif d > 0:
                if ext[i] - y >= 0.10:
                    darker, tdir[i], ext[i] = y, -1, y
                elif y > ext[i]:
                    ext[i] = y
            elif y - ext[i] >= 0.10:
                darker, tdir[i], ext[i] = ext[i], 1, y
            elif y < ext[i]:
                ext[i] = y
            if darker is not None and darker < 0.80:  # WCAG: the darker state below 0.80
                (up if tdir[i] > 0 else dn).add(i)
        # Concurrent means the same way in this frame or the last: an edge can lag a frame.
        both_up, both_dn = up | prev_up, dn | prev_dn
        prev_up, prev_dn = up, dn
        for d, tiles in ((1, both_up), (-1, both_dn)):
            if len(tiles) >= T // 4:
                register("screen", "screen", d)
            if len(tiles) >= 4:
                for r, c in fields:
                    if sum((r + a) * GRID + c + b in tiles for a in range(4) for b in range(4)) >= 4:
                        register("field", (r, c), d)
        f += 1
    proc.wait()
    if proc.returncode != 0 or f == 0:
        return FAIL, f"could not decode the picture (ffmpeg exit {proc.returncode}, {f} frames)"
    (s, s_at, _), (w, w_at, box) = worst["screen"], worst["field"]
    seen = f"{f} frames; the most flashes in any second: {s} over a quarter of the screen" \
        + (f" (from {clock(s_at / n)})" if s else "") + f", {w} over a quarter of a 10-degree field" \
        + (f" (from {clock(w_at / n)}, at x {box[1] * 100 // GRID}-{(box[1] + 4) * 100 // GRID} %, "
           f"y {box[0] * 100 // GRID}-{(box[0] + 4) * 100 // GRID} %)" if w else "")
    if s > 3:
        return FAIL, f"{seen}: more than 3 (WCAG 2.3.1, over the area broadcast rules use)"
    if w > 3:
        return WARN, f"{seen}: more than 3 over WCAG's arm's-length area, which natural motion also reaches; look at it"
    return PASS, seen


# --------------------------------------------------------------------------- loudness
TARGET, PEAK = -14.0, -1.0


def check_loudness(path: str) -> tuple[str, str]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", path, "-map", "0:a:0", "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr)
    if r.returncode or not m:
        return FAIL, f"could not measure the sound (ffmpeg exit {r.returncode})"
    j = json.loads(m.group(0))
    i, tp, lra = float(j["input_i"]), float(j["input_tp"]), float(j["input_lra"])
    seen = f"{i:.1f} LUFS, {tp:.1f} dBTP, range {lra:.1f} LU (want {TARGET:g} +-1 LUFS, at most {PEAK:g} dBTP)"
    return (PASS, seen) if abs(i - TARGET) <= 1 and tp <= PEAK else (FAIL, seen)


# --------------------------------------------------------------------------- the gate
def measure(path: str, want: Fraction | None, loudness: bool = False) -> list[tuple[str, str, str]]:
    j = probe(path)
    streams = j.get("streams", [])
    vs = [s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    if not vs:
        raise OSError(f"{path}: no video stream")
    v = vs[0]
    fps = want or rate(v.get("r_frame_rate"))
    out = []
    for cid, fn in (("codec", lambda: check_codec(v)), ("cfr", lambda: check_cfr(path, v, want)),
                    ("faststart", lambda: check_faststart(path)), ("audio", lambda: check_audio(streams)),
                    ("av-length", lambda: check_av_length(path, v, streams, fps)), ("flashes", lambda: check_flashes(path, fps))):
        verdict, text = fn()
        out.append((verdict, cid, text))
    if loudness:
        verdict, text = check_loudness(path)
        out.append((verdict, "loudness", text))
    return out


def gate(path: str, want: Fraction | None, loudness: bool = True) -> int:
    rows = measure(path, want, loudness)
    for verdict, cid, text in rows:
        print(f"{verdict}  {cid:<10} {text}")
    fails = [cid for verdict, cid, _ in rows if verdict == FAIL]
    print(f"{os.path.basename(path)}: " + (f"FAILED {', '.join(fails)}" if fails else "ready to deliver"))
    return 1 if fails else 0


# --------------------------------------------------------------------------- selftest
PLAIN_V = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
# ffmpeg 7.1 writes primaries and transfer from the frame, not from -color_primaries alone.
GOOD_V = PLAIN_V + ",setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def make(dst: str, vf: str = GOOD_V, af: str | None = None, video: list[str] | None = None,
         audio: list[str] | None = None, mux: list[str] | None = None, adur: float = 4.0) -> None:
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i", "testsrc=s=320x180:r=25:d=4",
           "-f", "lavfi", "-i", f"sine=f=440:r=48000:d={adur}", "-vf", vf]
    cmd += ["-af", af] if af else []
    cmd += video if video is not None else ["-c:v", "libx264", "-preset", "ultrafast", *TAGS]
    cmd += audio if audio is not None else ["-c:a", "aac", "-ac", "2", "-ar", "48000"]
    cmd += mux if mux is not None else ["-movflags", "+faststart"]
    subprocess.run(cmd + [dst], check=True)


def selftest() -> int:
    def strobe(box: str) -> str:
        on = "between(t,1,3)*lt(mod(t*12,2),1)"
        return f"{GOOD_V},drawbox={box}:c=white:t=fill:enable='{on}',drawbox={box}:c=black:t=fill:enable='not({on})*between(t,1,3)'"
    cases = [  # name, the id it must FAIL, the id it must WARN, how to make it
        ("good", None, None, {}),
        ("full range, bt470bg (the default render)", "codec", None,
         {"vf": "scale=out_color_matrix=bt601:out_range=pc,format=yuvj420p",
          "video": ["-c:v", "libx264", "-preset", "ultrafast", "-colorspace", "bt470bg", "-color_range", "pc"]}),
        ("primaries and transfer unset", None, "codec",
         {"vf": PLAIN_V, "video": ["-c:v", "libx264", "-preset", "ultrafast", "-colorspace", "bt709", "-color_range", "tv"]}),
        ("every fifth frame dropped (VFR)", "cfr", None,
         {"vf": GOOD_V + ",select='not(eq(mod(n\\,5)\\,2))'", "mux": ["-fps_mode", "passthrough", "-movflags", "+faststart"]}),
        ("moov at the end", "faststart", None, {"mux": []}),
        ("44.1 kHz AAC", "audio", None, {"audio": ["-c:a", "aac", "-ac", "2", "-ar", "44100"]}),
        ("MP3 audio", "audio", None, {"audio": ["-c:a", "libmp3lame", "-ac", "2", "-ar", "48000"]}),
        ("audio 0.5 s short", "av-length", None, {"adur": 3.5}),
        ("a 100 ms hole at 2 s", "av-length", None, {"af": "asetpts='PTS+gte(PTS*TB\\,2)*0.1/TB'", "adur": 3.9}),
        ("a 6 Hz black/white strobe, full screen", "flashes", None, {"vf": strobe("x=0:y=0:w=iw:h=ih")}),
        ("the same strobe on 1/36 of the screen", None, "flashes", {"vf": strobe("x=iw/4:y=ih/5:w=iw/6:h=ih/6")}),
    ]
    tmp = tempfile.mkdtemp(prefix="check-delivery-")
    bad = 0
    try:
        for k, (name, want, want_warn, kw) in enumerate(cases):
            dst = os.path.join(tmp, f"case{k}.mp4")
            make(dst, **kw)
            rows = measure(dst, None)
            failed = {cid for verdict, cid, _ in rows if verdict == FAIL}
            warned = {cid for verdict, cid, _ in rows if verdict == WARN}
            expect, expect_warn = {want} - {None}, {want_warn} - {None}
            ok = failed == expect and warned == expect_warn
            bad += not ok
            extra = (failed - expect) | (warned - expect_warn)
            print(f"{'ok  ' if ok else 'BAD '} {name:<42} failed [{', '.join(sorted(failed)) or 'nothing'}]"
                  + (f", warned [{', '.join(sorted(warned))}]" if warned or want_warn else "")
                  + (f"; want failed [{want or 'nothing'}]" + (f", warned [{want_warn}]" if want_warn else "") if not ok else "")
                  + (f"; collateral: {', '.join(sorted(extra))}" if extra else ""))
            if not ok:
                for verdict, cid, text in rows:
                    print(f"       {verdict} {cid:<10} {text}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"selftest: {len(cases) - bad} of {len(cases)} films judged as planted" + ("" if not bad else f", {bad} NOT"))
    return 1 if bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {}
    for name in ("--fps", "--target", "--peak"):
        for i, x in enumerate(args):
            if x == name and i + 1 < len(args):
                opts[name] = args[i + 1]
                args = args[:i] + args[i + 2:]
                break
            if x.startswith(name + "="):
                opts[name] = x.split("=", 1)[1]
                args = args[:i] + args[i + 1:]
                break
    loud = "--no-loudness" not in args
    args = [x for x in args if x != "--no-loudness"]
    fps = rate(opts["--fps"]) if "--fps" in opts else None
    if ("--fps" in opts and fps is None) or len(args) != 1 or args[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    TARGET = float(opts.get("--target", TARGET))
    PEAK = float(opts.get("--peak", PEAK))
    if args[0] == "selftest":
        sys.exit(selftest())
    try:
        sys.exit(gate(args[0], fps, loud))
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"check-delivery: {e}", file=sys.stderr)
        sys.exit(2)
