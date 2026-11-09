#!/usr/bin/env python3
"""Render a long Remotion composition in pieces that survive a crash, then join them.

usage: python3 render-chunks.py <bundle dir> <composition id> <out.mp4> <work dir>
                                [--chunk=<frames>] [--range=<first>-<last>]
                                [-- <more render flags>]

Run it from the project folder, so that `npx remotion` finds the project and its
remotion.config.ts. Write every flag with `=`: `--chunk=1500`, not `--chunk 1500`.

What it does:

1. It renders `--chunk` frames at a time (default 3000), one render process each,
   into <work dir>, as H.264 with uncompressed sound. A chunk is kept only when it
   holds exactly the frames it was asked for and its sound lasts as long as its
   picture. A run that finds a good chunk skips it, so running the same command
   again resumes.
2. It joins the chunks without re-encoding the picture, and encodes the sound to
   AAC once, over the whole film. Uncompressed sound joins exactly. AAC per chunk
   would add encoder delay at every join and drift the sound out of sync.
3. It checks the whole film's frame count and length.

Everything after `--` goes to every chunk's render, for example:
  -- --concurrency=2 --color-space=bt709 --offthreadvideo-cache-size-in-bytes=800000000

`--color-space=bt709` sets the colour tags. An older Remotion on Linux wrote only the
matrix tag, so when that exact flag is passed, the join writes all four without
touching a pixel.

Each render runs in its own process group and its own temp folder. When it ends, or
when this script is stopped, that group, Chrome's group and the folder all go.

A chunk is reused if its frame count is right, even if the source has changed since.
After changing the video, delete <work dir> or use a new one.
"""

import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import time

args = sys.argv[1:]
extra = []
if "--" in args:
    extra = args[args.index("--") + 1 :]
    args = args[: args.index("--")]
opts = {a.split("=")[0]: (a.split("=", 1)[1] if "=" in a else "") for a in args if a.startswith("--")}
pos = [a for a in args if not a.startswith("--")]
unknown = set(opts) - {"--chunk", "--range"}
if len(pos) != 4 or unknown or "" in opts.values():
    sys.exit(__doc__)
if not any(f.startswith("--offthreadvideo-cache-size-in-bytes") for f in extra):
    extra.append("--offthreadvideo-cache-size-in-bytes=800000000")
if "--color-space" in extra:
    sys.exit("write --color-space=bt709 with an equals sign, so the join can see it")
for tool in ("ffmpeg", "ffprobe", "npx"):
    if not shutil.which(tool):
        sys.exit(f"{tool} is not on the PATH")

bundle, comp, out, work = pos[0], pos[1], pathlib.Path(pos[2]), pathlib.Path(pos[3])
chunk = int(opts.get("--chunk", 3000))
work.mkdir(parents=True, exist_ok=True)
# These flags also apply to `compositions`.
shared = [f for f in extra if f.startswith(("--browser-executable", "--binaries-directory", "--gl"))]
signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))


def cli(*a: str) -> list:
    return ["npx", "--no-install", "remotion", *a]


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def composition() -> tuple:
    r = subprocess.run(cli("compositions", bundle, *shared), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)
    m = re.search(rf"^{re.escape(comp)}\s+([\d.]+)\s+(\d+)x(\d+)\s+(\d+) \(", r.stdout, re.M)
    if not m:
        sys.exit(f"composition {comp!r} not found in the bundle:\n{r.stdout}{r.stderr}")
    return float(m.group(1)), int(m.group(4))


def probe(path: pathlib.Path, stream: str, entry: str, count: bool = False) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", stream, *(["-count_packets"] if count else []),
         "-show_entries", f"stream={entry}", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    try:
        return float(r.stdout.strip().split("\n")[0].rstrip(","))
    except ValueError:
        return -1


def frames_in(path: pathlib.Path) -> int:
    return int(probe(path, "v:0", "nb_read_packets", count=True))


def sound_in(path: pathlib.Path) -> float:
    """Seconds of sound, counted by decoding it. Matroska keeps packet times to the
    millisecond, so adding them up falls short of the true length."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "48000",
         "-f", "s16le", "-"],
        capture_output=True, stdin=subprocess.DEVNULL,
    )
    return len(r.stdout) / 2 / 48000 if r.returncode == 0 else -1


def good(path: pathlib.Path, want: int, fps: float) -> bool:
    return path.exists() and frames_in(path) == want and abs(sound_in(path) - want / fps) < 0.5 / fps


def kill_render(group: int, tmp: pathlib.Path) -> None:
    """Kill the render's process group and Chrome's. Remotion starts Chrome in a group
    of its own, so killing the render's group alone leaves Chrome running. Chrome's
    profile folder sits in this render's temp folder, which is how we find it."""
    groups = {group}
    rows = subprocess.run(["ps", "-A", "-o", "pgid=,args="], capture_output=True, text=True).stdout
    for row in rows.splitlines():
        pgid, _, cmd = row.strip().partition(" ")
        if f"--user-data-dir={tmp}" in cmd:
            groups.add(int(pgid))
    for g in groups:
        try:
            os.killpg(g, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def render(dest: pathlib.Path, flags: list) -> int:
    """One render, in its own process group, with its own temp folder (a glob over
    the shared one could delete another render's files). Leaves nothing behind."""
    part = dest.with_name(dest.stem + ".part" + dest.suffix)
    tmp = work / "tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    cmd = cli("render", bundle, comp, str(part), "--overwrite", *flags)
    with open(work / "render.log", "a") as lf:
        lf.write(f"\n$ {' '.join(cmd)}\n")
        lf.flush()
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True, env={**os.environ, "TMPDIR": str(tmp.resolve())})
        try:
            code = p.wait()
        finally:
            kill_render(p.pid, tmp.resolve())
            shutil.rmtree(tmp, ignore_errors=True)
    if code == 0:
        part.rename(dest)
    else:
        part.unlink(missing_ok=True)
    return code


fps, length = composition()
first, last = 0, length - 1
if "--range" in opts:
    first, last = (int(x) for x in opts["--range"].split("-"))
    if not 0 <= first <= last < length:
        sys.exit(f"--range {first}-{last} is outside the composition's frames 0-{length - 1}")
total = last - first + 1
ranges = [(a, min(a + chunk - 1, last)) for a in range(first, last + 1, chunk)]
log(f"{comp}: frames {first}-{last} of {length} at {fps:g} fps, {len(ranges)} chunks of up to {chunk}")

files = []
for i, (a, b) in enumerate(ranges):
    dest = work / f"frames-{a:06d}-{b:06d}.mkv"
    files.append(dest)
    want = b - a + 1
    if good(dest, want, fps):
        continue
    dest.unlink(missing_ok=True)
    for attempt in (1, 2):
        t = time.time()
        log(f"chunk {i + 1}/{len(ranges)}: frames {a}-{b}" + (" (again)" if attempt == 2 else ""))
        code = render(dest, ["--codec=h264-mkv", "--audio-codec=pcm-16", "--enforce-audio-track",
                             f"--frames={a}-{b}", *extra])
        if code == 0 and good(dest, want, fps):
            log(f"chunk {i + 1} ok in {time.time() - t:.0f} s ({want / (time.time() - t):.1f} fps)")
            break
        log(f"chunk {i + 1} failed (exit {code}, {frames_in(dest) if dest.exists() else 0} frames, "
            f"{sound_in(dest) if dest.exists() else 0:.3f} s of sound); see {work / 'render.log'}")
        dest.unlink(missing_ok=True)
    else:
        sys.exit(f"chunk {i + 1} failed twice; run the same command again to resume from it")

listing = work / "chunks.txt"
listing.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
out.parent.mkdir(parents=True, exist_ok=True)
# A chunk's times are rounded to the millisecond, so joined frames come out at uneven
# spacing. For a whole-number frame rate, put every frame back on an exact time.
bsf, tags = [], []
if fps == round(fps):
    r = round(fps)
    bsf.append(f"setts=time_base=1/{r * 512}:pts=round(PTS*TB*{r})*512:dts=round(DTS*TB*{r})*512:duration=512")
    tags += ["-video_track_timescale", str(r * 512)]
if "--color-space=bt709" in extra:
    bsf.append("h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1")
    tags += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
if bsf:
    tags = ["-bsf:v", ",".join(bsf), *tags]
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
     "-map", "0:v", "-map", "0:a", "-c:v", "copy", *tags, "-c:a", "aac", "-b:a", "192k",
     "-movflags", "+faststart", str(out)],
    check=True, stdin=subprocess.DEVNULL,
)
n = frames_in(out)
v, s = probe(out, "v:0", "duration"), probe(out, "a:0", "duration")
report = {"frames": n, "expected": total, "video_s": round(v, 3), "audio_s": round(s, 3)}
print(json.dumps(report))
if n != total or abs(v - s) > 0.1:
    sys.exit(f"the joined film is wrong: {report}")
log(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB)")
