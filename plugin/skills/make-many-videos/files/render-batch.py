#!/usr/bin/env python3
"""Render every film in a batch that is not already current. Safe to run again.

usage: python3 render-batch.py films.json [film id ...]

Run it from the project folder. LOCK=/tmp/render-1.lock (the default) names the
render lock. One render at a time is the default. To test two at once, set
--concurrency=2 in "flags" and start a second copy with LOCK=/tmp/render-2.lock.

films.json:
  {
    "entry": "src/index.ts",
    "shared": ["src/kit", "public/shared", "remotion.config.ts", "package-lock.json"],
    "flags": ["--concurrency=4", "--color-space=bt709", "--offthreadvideo-cache-size-in-bytes=800000000"],
    "chunk": 3000,
    "films": {
      "film-01": ["src/films/film-01.tsx", "public/films/film-01"],
      "film-02": ["src/films/film-02.tsx", "public/films/film-02"]
    }
  }

"shared" lists what every film reads. Each film lists what only it reads. A folder
counts as every file inside it. A path that does not exist stops the run, because a
fingerprint with a hole in it says "current" when it is not.

A film is current when out/batch/final/<id>.mp4 exists and its fingerprint (one
line per input file) still matches out/batch/<id>.built-from. So a run after an edit
re-renders exactly the films the edit reached, and a run after a restart picks up
where the last one stopped. A half-rendered film resumes from its chunks only if they
came from the same fingerprint. Otherwise they are thrown away, because a chunk with
the right frame count can still hold the old words.

The run takes one bundle, straight after the fingerprints, so an edit made while it
runs lands in neither and the next run catches it. Two copies of this script share
the work: a film being rendered by one copy is skipped by the other.

The last line of a run is ALL-CURRENT, or RUN-DONE failed=<n>.
"""

import contextlib
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import time

if len(sys.argv) < 2:
    sys.exit(__doc__)
config = json.loads(pathlib.Path(sys.argv[1]).read_text())
wanted = sys.argv[2:] or list(config["films"])
unknown_films = [f for f in wanted if f not in config["films"]]
if unknown_films:
    sys.exit(f"not in {sys.argv[1]}: {unknown_films}")
for tool in ("ffmpeg", "ffprobe", "npx"):
    if not shutil.which(tool):
        sys.exit(f"{tool} is not on the PATH")

OUT = pathlib.Path("out/batch")
FINAL = OUT / "final"
FINAL.mkdir(parents=True, exist_ok=True)
LOCK = os.environ.get("LOCK", "/tmp/render-1.lock")
BUNDLE = OUT / f"bundle-{pathlib.Path(LOCK).stem}"
FLAGS = config.get("flags", [])
CHUNK = int(config.get("chunk", 3000))
signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def run(*cmd: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL, **kw)


@contextlib.contextmanager
def flocked(path, wait: bool = True):
    """The same kind of lock as the `flock` command, so both queue together.
    Yields True if we hold the lock. With wait=False it yields False if someone else does."""
    fd = os.open(path, os.O_CREAT | os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        yield True
    finally:
        os.close(fd)


def fingerprint(film: str) -> str:
    lines = []
    for name in [*config.get("shared", []), *config["films"][film]]:
        p = pathlib.Path(name)
        if not p.exists():
            sys.exit(f"{film}: {name} does not exist. Fix films.json; a hole here would hide stale films.")
        for f in sorted([p] if p.is_file() else [x for x in p.rglob("*") if x.is_file()]):
            lines.append(f"{hashlib.sha1(f.read_bytes()).hexdigest()}  {f}")
    return "\n".join(lines) + "\n"


def changed(old: str, new: str) -> str:
    a, b = set(old.splitlines()), set(new.splitlines())
    names = sorted({x.split("  ", 1)[1] for x in a ^ b})
    return ", ".join(names[:5]) + (f" and {len(names) - 5} more" if len(names) > 5 else "")


def is_current(film: str, fp: str) -> bool:
    stamp = OUT / f"{film}.built-from"
    return (FINAL / f"{film}.mp4").exists() and stamp.exists() and stamp.read_text() == fp


def cli(*a: str) -> list:
    return ["npx", "--no-install", "remotion", *a]


def composition(comp: str) -> tuple:
    shared = [f for f in FLAGS if f.startswith(("--browser-executable", "--binaries-directory", "--gl"))]
    r = run(*cli("compositions", str(BUNDLE), *shared), text=True)
    m = re.search(rf"^{re.escape(comp)}\s+([\d.]+)\s+(\d+)x(\d+)\s+(\d+) \(", r.stdout, re.M)
    if not m:
        raise RuntimeError(f"composition {comp!r} not in the bundle. Is it registered in the entry?\n{r.stdout}{r.stderr}")
    return float(m.group(1)), int(m.group(4))


def frames_in(path: pathlib.Path) -> int:
    r = run("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
            "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path), text=True)
    try:
        return int(r.stdout.strip().split("\n")[0].rstrip(","))
    except ValueError:
        return -1


def sound_in(path: pathlib.Path) -> float:
    """Seconds of sound, counted by decoding, because Matroska's packet times fall short."""
    r = run("ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "48000",
            "-f", "s16le", "-")
    return len(r.stdout) / 2 / 48000 if r.returncode == 0 else -1


def good(path: pathlib.Path, want: int, fps: float) -> bool:
    return path.exists() and frames_in(path) == want and abs(sound_in(path) - want / fps) < 0.5 / fps


def kill_render(group: int, tmp: pathlib.Path) -> None:
    """Kill the render's process group and Chrome's, which Remotion starts apart."""
    groups = {group}
    rows = subprocess.run(["ps", "-A", "-o", "pgid=,args="], capture_output=True, text=True).stdout
    for row in rows.splitlines():
        pgid, _, cmd = row.strip().partition(" ")
        if f"--user-data-dir={tmp}" in cmd:
            groups.add(int(pgid))
    for g in groups:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(g, signal.SIGKILL)


def render_chunk(comp: str, dest: pathlib.Path, a: int, b: int, work: pathlib.Path) -> int:
    part = dest.with_name(dest.stem + ".part" + dest.suffix)
    tmp = work / "tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    cmd = cli("render", str(BUNDLE), comp, str(part), "--overwrite", "--codec=h264-mkv",
              "--audio-codec=pcm-16", "--enforce-audio-track", f"--frames={a}-{b}", *FLAGS)
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


def render_film(film: str, fp: str) -> None:
    work = OUT / "chunks" / film
    stamp = work / ".built-from"
    if not stamp.exists() or stamp.read_text() != fp:
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        stamp.write_text(fp)
    fps, length = composition(film)
    files = []
    for a in range(0, length, CHUNK):
        b = min(a + CHUNK - 1, length - 1)
        dest = work / f"frames-{a:06d}-{b:06d}.mkv"
        files.append(dest)
        if good(dest, b - a + 1, fps):
            continue
        dest.unlink(missing_ok=True)
        for attempt in (1, 2):
            render_chunk(film, dest, a, b, work)
            if good(dest, b - a + 1, fps):
                break
            dest.unlink(missing_ok=True)
            log(f"  chunk {a}-{b} failed (try {attempt}); see {work / 'render.log'}")
        else:
            raise RuntimeError(f"chunk {a}-{b} failed twice")
    listing = work / "chunks.txt"
    listing.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
    tags = []
    if "--color-space=bt709" in FLAGS:
        tags = ["-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    joined = OUT / f"{film}.part.mp4"
    r = run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-map", "0:v", "-map", "0:a", "-c:v", "copy", *tags, "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(joined), text=True)
    if r.returncode != 0:
        raise RuntimeError(f"the join failed: {r.stderr[-400:]}")
    n = frames_in(joined)
    if n != length:
        raise RuntimeError(f"the joined film has {n} frames, not {length}")
    # A contact sheet, one frame a second, to look at with your own eyes.
    secs = length / fps
    side = int((secs + 1) ** 0.5) + 1
    run("ffmpeg", "-v", "error", "-y", "-i", str(joined), "-vf", f"fps=1,scale=240:-1,tile={side}x{side}",
        "-frames:v", "1", str(OUT / f"{film}-sheet.png"))
    joined.rename(FINAL / f"{film}.mp4")
    (OUT / f"{film}.built-from").write_text(fp)
    shutil.rmtree(work, ignore_errors=True)


prints = {f: fingerprint(f) for f in wanted}
todo = []
for film in wanted:
    if is_current(film, prints[film]):
        log(f"{film} current")
        continue
    stamp = OUT / f"{film}.built-from"
    if stamp.exists():
        log(f"{film} stale: {changed(stamp.read_text(), prints[film])}")
    todo.append(film)
if not todo:
    print("ALL-CURRENT")
    sys.exit(0)

log(f"{len(todo)} to render; bundling {config['entry']} (lock {LOCK})")
with flocked(LOCK):
    shutil.rmtree(BUNDLE, ignore_errors=True)
    r = run(*cli("bundle", config["entry"], f"--out-dir={BUNDLE}"), text=True)
    if r.returncode != 0:
        sys.exit(f"the bundle failed:\n{r.stdout[-800:]}{r.stderr[-800:]}")

failed = 0
for film in todo:
    claim = OUT / f"{film}.claim"
    with flocked(claim, wait=False) as mine:
        if not mine:
            log(f"{film} is being rendered by another run; skipping")
            continue
        if is_current(film, prints[film]):
            log(f"{film} finished by another run")
            continue
        start = time.time()
        log(f"{film} waiting for the render lock")
        with flocked(LOCK):
            log(f"{film} rendering")
            try:
                render_film(film, prints[film])
                log(f"{film} done in {time.time() - start:.0f} s")
            except RuntimeError as e:
                failed += 1
                log(f"{film} FAILED: {e}")
print(f"RUN-DONE failed={failed}")
sys.exit(1 if failed else 0)
