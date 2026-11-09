#!/usr/bin/env python3
"""Mix a voice over music, with the music ducked (turned down) under the speech.

  python duck-mix.py voice.mp3 music.mp3 voice.captions.json mix.wav
  python duck-mix.py voice.mp3 music.mp3 voice.captions.json mix.wav --under=20 --depth=10 --tail=3

The levels are set from measured loudness, so they do not depend on how loud the
music file happens to be. --under: LU the ducked music sits under the voice.
--depth: dB the music rises when nobody is speaking. Speech closer together than
--merge seconds counts as one stretch, so the music never lifts into a comma.
"""
import argparse
import json
import os
import re
import subprocess
import sys

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
p = argparse.ArgumentParser()
p.add_argument('voice')
p.add_argument('music')
p.add_argument('captions', help='JSON list of words with startMs and endMs')
p.add_argument('out')
p.add_argument('--under', type=float, default=20)
p.add_argument('--depth', type=float, default=10)
p.add_argument('--merge', type=float, default=1.2, help='seconds')
p.add_argument('--lead', type=float, default=0.4, help='seconds the duck starts before the first word')
p.add_argument('--release', type=float, default=0.6, help='seconds the music takes to come back')
p.add_argument('--voice-at', type=float, default=0, help='seconds of music before the voice starts')
p.add_argument('--tail', type=float, default=2.5, help='seconds of music after the voice ends')
p.add_argument('--fade', type=float, default=0.8, help='seconds of fade at the start and the end')
a = p.parse_args()


def loudness(path):
    err = subprocess.run([FFMPEG, '-nostdin', '-hide_banner', '-i', path, '-vn', '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', err)
    if not m:
        sys.exit(f'Could not measure {path}.')
    return float(json.loads(m.group(0))['input_i'])


with open(a.captions, encoding='utf-8') as f:
    words = json.load(f)
stretches = []
for w in words:
    s, e = w['startMs'] / 1000 + a.voice_at, w['endMs'] / 1000 + a.voice_at
    if stretches and s - stretches[-1][1] < a.merge:
        stretches[-1][1] = e
    else:
        stretches.append([s, e])

voice_lufs, music_lufs = loudness(a.voice), loudness(a.music)
duck = voice_lufs - a.under - music_lufs  # gain in dB under speech
open_gain = duck + a.depth                # gain in dB between speech
length = words[-1]['endMs'] / 1000 + a.voice_at + a.tail

# How far down the music is at time t: 0 is open, 1 is fully ducked. The stretches
# never overlap (they are --merge apart), so the terms can simply be added.
terms = [f'clip((t-{s - a.lead:.3f})/{a.lead},0,1)*clip(({e + a.release:.3f}-t)/{a.release},0,1)' for s, e in stretches]
down = '+'.join(terms)
# Work in decibels and convert once. A straight ramp of linear gain sounds late going down.
volume = f"volume='pow(10,({open_gain:.2f}+({duck - open_gain:.2f})*({down}))/20)':eval=frame"
graph = (
    f'[1:a]aresample=48000,{volume},afade=t=in:d={a.fade},afade=t=out:st={length - a.fade:.3f}:d={a.fade}[bed];'
    f'[0:a]aresample=48000,adelay={int(a.voice_at * 1000)}:all=1[v];'
    f'[v][bed]amix=inputs=2:duration=longest:normalize=0,atrim=0:{length:.3f}[out]'
)
subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-y', '-i', a.voice, '-stream_loop', '-1', '-i', a.music,
                '-filter_complex', graph, '-map', '[out]', '-ac', '2', '-c:a', 'pcm_s24le', a.out],
               check=True, stdin=subprocess.DEVNULL)
print(f'voice {voice_lufs:.1f} LUFS, music {music_lufs:.1f} LUFS. Music gain {duck:.1f} dB under speech, {open_gain:.1f} dB between. '
      f'{len(stretches)} speech stretches. {length:.1f} s written to {a.out}')
