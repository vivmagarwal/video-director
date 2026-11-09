#!/usr/bin/env python3
"""Master the sound of a finished video to a loudness target. The picture is copied.

  python3 master-audio.py film.mp4
  python3 master-audio.py film.mp4 --target=-14 --peak=-2 --out=film.youtube.mp4

Pass 1 measures. Pass 2 applies loudnorm with those measurements, so it can use one
gain for the whole film (linear mode). Pass 3 measures the result, and the "after"
row is the number to report, not the target you asked for.
Exit 0: within 1 LU of the target. Exit 1: missed by more; the file is written, read
the numbers. Exit 2: bad input or a failed pass; use no file it left.
"""
import argparse
import json
import os
import re
import subprocess
import sys

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
CODECS = {
    '.mp4': ['-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart'],
    '.mov': ['-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart'],
    '.m4a': ['-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart'],
    '.mkv': ['-c:a', 'aac', '-b:a', '320k'],
    '.mp3': ['-c:a', 'libmp3lame', '-b:a', '320k'],
    '.wav': ['-c:a', 'pcm_s24le'],
}

p = argparse.ArgumentParser()
p.add_argument('file')
p.add_argument('--target', type=float, default=-16, help='loudness to land on, in LUFS')
p.add_argument('--peak', type=float, default=-1.5, help='true peak ceiling, in dBTP')
p.add_argument('--lra', type=float, default=11, help='loudness range, in LU')
p.add_argument('--out')
a = p.parse_args()

if not os.path.isfile(a.file):
    print(f'No such file: {a.file}')
    sys.exit(2)
stem, ext = os.path.splitext(a.file)
out = a.out or f'{stem}.mastered{ext}'
out_ext = os.path.splitext(out)[1].lower()
if os.path.abspath(out) == os.path.abspath(a.file):
    print('--out would overwrite the input. Keep the input: you master again from it, never from a master.')
    sys.exit(2)
if out_ext not in CODECS:
    print(f'Unknown output type {out_ext}. Use one of: {" ".join(CODECS)}')
    sys.exit(2)


def run(args):
    r = subprocess.run([FFMPEG, '-nostdin', '-hide_banner', *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stderr


def report(err):
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', err)
    if not m:
        return None
    d = json.loads(m.group(0))
    return d if d['input_i'] not in ('-inf', 'inf', 'nan') else None


base = f'loudnorm=I={a.target}:TP={a.peak}:LRA={a.lra}'


def measure(path):
    code, err = run(['-i', path, '-vn', '-af', f'{base}:print_format=json', '-f', 'null', '-'])
    d = report(err)
    if d is None:
        print(f'Could not measure {path} (exit {code}). Does it have sound?')
        print('\n'.join(err.strip().split('\n')[-5:]))
        sys.exit(2)
    return d


before = measure(a.file)
# asetpts restamps every sample from its count. Without it, loudnorm's last buffer
# carries a timestamp about 3 s early, and a player puts the end of the sound up
# to 100 ms late. loudnorm also works at 192 kHz, hence the resample back.
apply = (
    f"{base}:measured_I={before['input_i']}:measured_TP={before['input_tp']}"
    f":measured_LRA={before['input_lra']}:measured_thresh={before['input_thresh']}"
    f":offset={before['target_offset']}:linear=true:print_format=json"
    ',aresample=48000,asetpts=N/SR/TB'
)
code, err = run(['-y', '-i', a.file, '-map', '0:v?', '-map', '0:a', '-map', '0:s?', '-af', apply, '-ar', '48000',
                 '-c:v', 'copy', '-c:s', 'copy', *CODECS[out_ext], out])
if code != 0:
    print(f'Mastering failed (exit {code}):')
    print('\n'.join(err.strip().split('\n')[-8:]))
    sys.exit(2)
applied = report(err) or {}
after = measure(out)


def row(name, d):
    return f"  {name:8}{float(d['input_i']):8.1f} LUFS{float(d['input_tp']):8.1f} dBTP{float(d['input_lra']):8.1f} LU"


print(f'{a.file} -> {out}')
print(f'  {"asked":8}{a.target:8.1f} LUFS{a.peak:8.1f} dBTP{a.lra:8.1f} LU')
print(row('before', before))
print(row('after', after))
print(f"  mode: {applied.get('normalization_type', 'unknown')} (linear keeps the mix as it is; dynamic rides the level)")
over = float(after['input_tp']) - a.peak
if over > 0.05:
    print(f'  note: {over:.1f} dB over the ceiling. Report the measured number. If the platform is strict, '
          f'master again FROM THE ORIGINAL with a whole dB of margin (--peak={a.peak - 1:.1f}) and read this again.')
missed = abs(float(after['input_i']) - a.target)
if missed > 1:
    print(f'  MISSED the target by {missed:.1f} LU. A mix with very little in it, or one already clipping, cannot always reach it. Fix the mix and render again.')
    sys.exit(1)
