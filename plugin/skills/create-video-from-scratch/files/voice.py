#!/usr/bin/env python3
"""Voice a plain text file with Kokoro, free and on this machine.

  ~/voice-tools/venv/bin/python voice.py script.txt --voice=af_heart --target=144
  ~/voice-tools/venv/bin/python voice.py script.txt --voice=af_heart --speed=0.8

Writes script.mp3 and script.captions.json beside the text file.

- A blank line in the text starts a new paragraph. Paragraphs get a longer pause.
- word{respelling} is SAID as the respelling and CAPTIONED as the word. No spaces
  inside the braces: project{prodject}, not project{prod ject}.
- Word timings come from the model's own phoneme durations.
- Every file comes out at the same loudness (-20 LUFS by default).
"""
import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np
import onnx
import soundfile as sf
from kokoro_onnx import Kokoro
from kokoro_onnx.sliding import token_edges
from onnx import helper

MODEL_DIR = os.path.join(os.environ.get('VOICE_HOME', os.path.expanduser('~/voice-tools')), 'kokoro')
FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
SR = 24000
PUNCT = set(';:,.!?¡¿—…"«»“”()')


def model_with_durations():
    """The v1.0 model file does not report durations. Save a copy that does."""
    out = os.path.join(MODEL_DIR, 'kokoro-timed.onnx')
    if os.path.exists(out):
        return out
    if not os.path.exists(os.path.join(MODEL_DIR, 'kokoro-v1.0.onnx')):
        sys.exit(f'No model in {MODEL_DIR}. Run setup-voice.sh. A container rebuild can wipe this folder.')
    print('First run: writing kokoro-timed.onnx (about 325 MB).', flush=True)
    m = onnx.load(os.path.join(MODEL_DIR, 'kokoro-v1.0.onnx'))
    clip = [n for n in m.graph.node if n.op_type == 'Clip'][0]
    m.graph.node.append(helper.make_node('Identity', [clip.output[0]], ['duration']))
    m.graph.output.append(helper.make_tensor_value_info('duration', onnx.TensorProto.FLOAT, None))
    onnx.save(m, out)
    return out


def split_sentences(paragraph):
    """Split after . ? ! (and a closing quote) where a new sentence starts."""
    text, out, start = paragraph.strip(), [], 0
    for m in re.finditer(r'[.?!]["”]?(?=\s+["“A-Z])', text):
        out.append(text[start:m.end()].strip())
        start = m.end()
    out.append(text[start:].strip())
    return [s for s in out if s]


def voiced_span(audio):
    """Where the sound really starts and stops. Kokoro pads every take with silence."""
    level = np.convolve(np.abs(audio), np.ones(240) / 240, mode='same')
    loud = np.where(level > 0.006)[0]
    if len(loud) == 0:
        return 0, len(audio)
    return max(0, loud[0] - int(0.03 * SR)), min(len(audio), loud[-1] + int(0.06 * SR))


class Voice:
    def __init__(self, voice, lang):
        self.k = Kokoro(model_with_durations(), os.path.join(MODEL_DIR, 'voices-v1.0.bin'))
        if not self.k.has_timings:
            sys.exit('This model reports no durations. Delete kokoro-timed.onnx and run again.')
        if voice not in self.k.voices:
            names = ' '.join(sorted(self.k.voices.keys()))
            sys.exit(f'No voice called {voice}. These exist: {names}')
        self.style = self.k.get_voice_style(voice)
        self.lang = lang

    def phonemes(self, text):
        return ' '.join(self.k.tokenizer.phonemize(text, self.lang).split())

    def speak(self, sentence, speed):
        """Audio, plus (start_sample, end_sample, phonemes) for each spoken word group."""
        known = self.k.tokenizer.known(self.phonemes(sentence))
        try:
            tokens = self.k.tokenizer.tokenize(known)
        except ValueError:
            sys.exit(f'This sentence is too long for one model call. Break it up: {sentence[:80]!r}')
        audio, duration = self.k._infer(tokens, self.k._style_for(self.style, len(tokens)), speed)
        edges = token_edges(duration, len(audio))  # edges[i+1] to edges[i+2] is token i
        groups, cur = [], None
        for i, ch in enumerate(known):
            a, b = edges[i + 1], edges[i + 2]
            if ch == ' ':
                if cur:
                    groups.append(cur)
                cur = None
            elif ch not in PUNCT:
                cur = (a, b, ch) if cur is None else (cur[0], b, cur[2] + ch)
        if cur:
            groups.append(cur)
        return audio, groups

    def sound_length(self, word):
        bare = re.sub(r"[^\w'.-]", '', word) or word
        return max(1, len(re.sub(r'[ˈˌ ]', '', self.phonemes(bare))))

    def align(self, words, groups):
        """Match written words to spoken groups.

        espeak (the part that turns spelling into sounds) runs short words together
        ("for the" is one group) and splits others ("back-and-forth" is three), so a
        plain zip slides every caption after the first merge onto the wrong word.
        Each step takes 1:1, several words to one group, or one word to several
        groups, whichever lengths agree best. A merged group's time is shared out
        by the words' own sound lengths.
        """
        n, m = len(words), len(groups)
        word_len = [self.sound_length(w) for w in words]
        group_len = [max(1, len(re.sub(r'[ˈˌ]', '', g[2]))) for g in groups]
        moves = [(1, 1, 0)] + [(d, 1, 1.5 * (d - 1)) for d in (2, 3, 4)] + [(1, d, 1.5 * (d - 1)) for d in range(2, 9)]
        cost = [[float('inf')] * (m + 1) for _ in range(n + 1)]
        back = [[None] * (m + 1) for _ in range(n + 1)]
        cost[0][0] = 0
        for i in range(n + 1):
            for j in range(m + 1):
                if cost[i][j] == float('inf'):
                    continue
                for dw, dg, penalty in moves:
                    if i + dw > n or j + dg > m:
                        continue
                    c = cost[i][j] + abs(sum(word_len[i:i + dw]) - sum(group_len[j:j + dg])) + penalty
                    if c < cost[i + dw][j + dg]:
                        cost[i + dw][j + dg] = c
                        back[i + dw][j + dg] = (i, j, dw, dg)
        if back[n][m] is None:
            # No clean match. Share the whole sentence out by sound length.
            print(f'  WARNING rough timings, check this line: {" ".join(words)[:60]!r}')
            a, b = groups[0][0], groups[-1][1]
            total, acc, out = sum(word_len), a, []
            for ln in word_len:
                nxt = acc + (b - a) * ln / total
                out.append((int(acc), int(nxt)))
                acc = nxt
            return out
        out = [None] * n
        i, j = n, m
        while (i, j) != (0, 0):
            pi, pj, dw, dg = back[i][j]
            a, b = groups[pj][0], groups[pj + dg - 1][1]
            total, acc = sum(word_len[pi:pi + dw]), a
            for k in range(dw):
                nxt = acc + (b - a) * word_len[pi + k] / total
                out[pi + k] = (int(acc), int(nxt))
                acc = nxt
            i, j = pi, pj
        return out


def voice_text(v, paragraphs, speed, sentence_pause, para_pause):
    pieces, caps, t = [], [], 0
    for pi, para in enumerate(paragraphs):
        lines = split_sentences(para)
        for si, sentence in enumerate(lines):
            sentence = re.sub(r'\s+([—–-]+)\s+', r'\1 ', sentence)  # a spaced dash is not a word
            said = re.sub(r"([\w'’-]+)\{([^}\s]+)\}", r'\2', sentence)
            shown = re.sub(r'\{[^}\s]+\}', '', sentence)
            if '{' in said:
                sys.exit(f'A respelling needs a word before it and no spaces inside: {sentence!r}')
            audio, groups = v.speak(said, speed)
            head, tail = voiced_span(audio)
            audio = audio[head:tail]
            for w, (a, b) in zip(shown.split(), v.align(said.split(), groups)):
                a = min(max(a - head, 0), len(audio))
                b = min(max(b - head, 0), len(audio))
                start, end = round((t + a) / SR * 1000), round((t + b) / SR * 1000)
                caps.append({
                    'text': (' ' if caps else '') + w,
                    'startMs': start,
                    'endMs': end,
                    'timestampMs': (start + end) / 2,
                    'confidence': None,
                })
            pieces.append(audio)
            t += len(audio)
            if not (pi == len(paragraphs) - 1 and si == len(lines) - 1):
                gap = int((para_pause if si == len(lines) - 1 else sentence_pause) * SR)
                pieces.append(np.zeros(gap, dtype=np.float32))
                t += gap
    span = (caps[-1]['endMs'] - caps[0]['startMs']) / 1000
    return np.concatenate(pieces), caps, len(caps) / span * 60


def main():
    p = argparse.ArgumentParser(description='Voice a text file with Kokoro.')
    p.add_argument('script', help='a .txt file')
    p.add_argument('--voice', required=True, help='for example af_heart')
    p.add_argument('--speed', type=float, default=0.8, help='the model speed, or where the search starts')
    p.add_argument('--target', type=float, help='aim for this many words a minute; takes a few tries')
    p.add_argument('--band', type=float, default=8, help='how close to --target is close enough')
    p.add_argument('--takes', type=int, default=5, help='most tries for --target')
    p.add_argument('--sentence-pause', type=float, default=0.38, help='seconds between sentences')
    p.add_argument('--para-pause', type=float, default=0.7, help='seconds between paragraphs')
    p.add_argument('--lufs', type=float, default=-20, help='loudness of the finished file')
    p.add_argument('--lang', help='en-us or en-gb; by default it follows the voice name')
    a = p.parse_args()

    base = os.path.splitext(a.script)[0]
    lang = a.lang or ('en-gb' if a.voice.startswith('b') else 'en-us')
    with open(a.script, encoding='utf-8') as f:
        paragraphs = [x for x in re.split(r'\n\s*\n', f.read()) if x.strip()]
    if not paragraphs:
        sys.exit(f'{a.script} is empty.')
    v = Voice(a.voice, lang)

    speed, takes, below, above = a.speed, [], None, None  # below and above bracket the target
    for n in range(a.takes if a.target else 1):
        audio, caps, pace = voice_text(v, paragraphs, speed, a.sentence_pause, a.para_pause)
        takes.append((abs(pace - a.target) if a.target else 0, speed, audio, caps, pace))
        if a.target:
            print(f'  take {n + 1}: speed {speed:.3f} gives {pace:.0f} words a minute', flush=True)
            if abs(pace - a.target) <= a.band:
                break
            if pace < a.target:
                below = (speed, pace)
            else:
                above = (speed, pace)
            if below and above:  # search between the takes either side of the target
                f = (a.target - below[1]) / (above[1] - below[1])
                speed = below[0] + f * (above[0] - below[0])
            else:
                speed = speed * a.target / pace
            speed = min(1.4, max(0.6, speed))
    _, speed, audio, caps, pace = min(takes, key=lambda x: x[0])

    wav = base + '.raw.wav'
    sf.write(wav, audio, SR)
    subprocess.run(
        [FFMPEG, '-nostdin', '-v', 'error', '-y', '-i', wav,
         '-af', f'loudnorm=I={a.lufs}:TP=-2:LRA=11', '-ar', '44100', '-ac', '1',
         '-c:a', 'libmp3lame', '-b:a', '128k',
         '-metadata', f'comment=voice={a.voice} speed={speed:.3f} pace={pace:.0f}',
         base + '.mp3'],
        check=True, stdin=subprocess.DEVNULL)
    os.remove(wav)
    with open(base + '.captions.json', 'w', encoding='utf-8') as f:
        json.dump(caps, f, indent='\t', ensure_ascii=False)
        f.write('\n')
    print(f'{os.path.basename(base)}: {a.voice} speed {speed:.3f} | {len(caps)} words | '
          f'file {len(audio) / SR:.1f} s | {pace:.0f} words a minute over the speech span')
    if a.target and abs(pace - a.target) > a.band:
        print(f'  OUTSIDE the band: asked for {a.target:.0f} +/- {a.band:.0f}. Files were written. Decide, or change the pauses.')
        sys.exit(1)


if __name__ == '__main__':
    main()
