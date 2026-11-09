---
name: sound-and-music
description: Mix and master the sound of a video with ffmpeg: music ducked under speech, sound effects placed on frames, dead air found, and loudness set to a target with only the sound re-encoded. Use it when a video's picture is finished, or nearly, and its sound needs work.
---

# Sound and music

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It takes the sound of a video from "whatever it happened to be" to finished:

1. **Measure** how loud it is.
2. **Mix**: voice, music turned down under speech (this is called ducking), and sound effects placed on the right frames.
3. **Check for dead air**: holes where the sound stops.
4. **Master**: set the loudness of the finished file to a target. The picture is copied exactly. Only the sound is re-encoded.

Mastering is a normal last step for every finished video, not an extra. Skip it only if the user has a reason. Renderers do not set loudness for you. Five real renders of narrated videos measured -23.7 to -27.9 LUFS, which is about 8 to 12 units under a -16 target. Viewers reach for the volume at that level.

**LUFS** is a standard unit of how loud something sounds across its whole length. **dBTP** (true peak) is how close the loudest moment comes to the point of distortion. **LU** is a difference in loudness: 1 LU is 1 dB. **LRA** (loudness range) is how much the loudness moves around.

## When to use it (and when not to)

Use it when:

- a video has a final render and has not been mastered
- narration needs music under it
- a video needs sound effects
- someone says it is too quiet, or the music is too loud

Do not use it when:

- the picture may still change. Master last. A change to the cut means rendering and mastering again
- you need to clean a noisy recording. Denoising is outside this skill. On a clean take, a denoiser only does harm

## What you need before you start

| You need | Check | Install |
|---|---|---|
| ffmpeg with `loudnorm`, `silencedetect`, `ebur128`, `volumedetect` | `ffmpeg -hide_banner -filters \| grep -E 'loudnorm\|silencedetect\|ebur128\|volumedetect'` | `apt-get install -y ffmpeg` if allowed. See below if not |
| Python 3 | `python3 --version` | Usually there already. The scripts use only the standard library |
| Node.js, only for the Remotion parts | `node --version` | |

**Which ffmpeg?** Ask it. The one that ships inside Remotion (`npx remotion ffmpeg`) had `loudnorm` and `silencedetect`, but no `ebur128` or `volumedetect`, when checked on a Mac on 2026-11-09. So use a full build. Some cloud containers have had one at `/usr/bin/ffmpeg`, and `apt` was refused on another, so test with `command -v ffmpeg`. If there is none, this gets one from PyPI (checked on a Mac, not on Linux; it has all the filters above):

```bash
python3 -m venv ~/ffmpeg-venv && ~/ffmpeg-venv/bin/pip install -q imageio-ffmpeg
export FFMPEG=$(~/ffmpeg-venv/bin/python -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())")
```

All the scripts below read `FFMPEG` if it is set. In the plain commands, replace `ffmpeg` with `"$FFMPEG"`.

**Network.** Mastering needs none. You only need it to download music or sound effects. Hosts differ, so test: `curl -sS -o /dev/null -m 15 -w '%{http_code}\n' <url>`. A refusal reads `CONNECT tunnel failed, response 403` or `Host not in allowlist`. Any other status means the host answered. The user can open hosts in the session's cloud environment menu: Edit, then Network access.

**In a cloud session,** when this was written: 4 cores, about 15 GB of memory. The Bash tool times out at 10 minutes. Mastering took seconds on short test files, so it was not a problem there. Long films were not measured with this script. Finished videos are too big for git (GitHub refuses a file over 100 MB), and `SendUserFile` refuses over 30 MiB. Commit scripts and small audio, and push.

**Tested how.** Every script here was run on a Mac (Python 3.10, Homebrew ffmpeg) on 2026-11-09 on a real rendered video with a generated voice, and on real music. They were not run on Linux. The Chrome commands in step 4b were tested with the Mac download, not the Linux one. All the numbers from our runs are marked. Others come from past videos earlier in 2026.

## Steps

### 0. Save the tools

Work in one project folder. Every step below that uses a project file starts with `cd /path/to/project`: put your real folder there, as a full path. A `cd` from an earlier command may not carry over.

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd /path/to/project
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/sound-and-music"
cp -rn "$S/files/." . 2>/dev/null; test -e "duck-mix.py" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It keeps any file that already exists, so your work is safe.

It also saves the Remotion example files for step 4b. Leave them unused if you work with ffmpeg alone.

### 1. Measure first

Two filters give you the numbers:

```bash
cd /path/to/project
ffmpeg -nostdin -hide_banner -i film.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -A12 Summary | grep -E 'I:|LRA:|Peak:'
ffmpeg -nostdin -hide_banner -i film.mp4 -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
```

A real result from a voice-only film after mastering:

```text
    I:         -16.0 LUFS        (integrated: the loudness of the whole file)
    LRA:         1.8 LU          (loudness range)
mean_volume: -19.4 dB
max_volume: -1.5 dB
```

`volumedetect` is quick and gives the sample peak. `ebur128` gives the loudness that platforms talk about.

**This machine cannot listen.** A container can only measure. Numbers can say the music is 20 LU under the voice. They cannot say the music fits, a sound effect is silly, or the voice feels buried. So measure, then ask a person.

### 2. Decide the target

These are **starting points**, and a platform can change its numbers. Ask where the video will go. If the user has a spec, use it.

| Going to | Loudness | True peak ceiling | Ask `master-audio.py` for |
|---|---|---|---|
| YouTube, or a short social clip | -14 LUFS | -1.5 dBTP | `--target=-14` |
| A podcast, or you do not know where it will go | -16 LUFS | -1.5 dBTP | no flags: these are its defaults |

**Why -14.** It is the level widely reported for YouTube, which is said to turn louder videos down and leave quieter ones alone. So a -16 master can play about 2 dB quiet there. YouTube's upload help page named no number when we checked on 2026-11-09, so treat this as common practice, not a YouTube rule. TikTok and Meta were found to publish no target, and -14 is a safe start for them too.

**Why -16.** Apple asks for podcasts at about -16, give or take 1, with true peak no higher than -1 (`https://podcasters.apple.com/support/893-audio-requirements`, checked on 2026-11-09). It is also the safer choice when you do not know the platform, because a quieter file leaves more room above the peaks.

**Why -1.5 for the peak.** The ceiling is a request, not a limiter, so leave some room. In real jobs, asking for -1 gave -0.1 dBTP on one film and -1.0 on another. Asking for -2 gave -1.5. If the `after` row lands over -1.5 and the platform is strict, master again from the original with a lower `--peak`. The script prints a value to try.

### 3. Mix: levels that worked

Set levels relative to the voice. These are starting points. Try them and ask a person.

**Voices.** Keep every voice in a video at one loudness first, so no speaker jumps out. A voice at -20 LUFS leaves room for mastering. Generated voices can differ by up to 10 LU before levelling.

**Music.**

- A video that teaches keeps music at the edges: the cold open, chapter cards, the end. Keep it out from under the reasoning, or at least 20 dB under the voice.
- A flat 0.1 volume under narration turned out only about 15 dB under, which was too loud for teaching speech.
- A trailer, title piece or short can run music throughout, 12 to 18 LU under the voice.
- With no voice at all, run the music near full level and master afterwards.
- Change music at a section break, on a bar line. Music does not stop in a pause.
- Fade music in over about 24 frames, and out over at least 24. Music that starts at full level or stops on the last frame clicks.

**Ducking.**

- Duck 9 to 12 dB, or to at least 20 dB under a teaching voice.
- Start 0.25 to 1 s before the words. 0.4 s worked.
- Release over about 0.6 s.
- Treat speech less than 1.2 s apart as one stretch. Lifting the music between sentences is the most obtrusive mistake in a mix.
- Work in decibels and convert once, with `10 ** (dB / 20)`. A straight ramp of linear gain sounds late going down and early coming back.

**Crossfades** are equal power: `Math.sqrt(t)` in, `Math.sqrt(1 - t)` out. Two straight ramps dip in the middle.

**Silence.** Never more than 20 frames of true digital silence, and that only just before an impact. It reads as a fault. Keep music or room sound under a hold.

### 4a. Mix with ffmpeg

Use this when you already have a rendered video, or no Remotion project. It reads when speech happens from a captions file: a JSON list of words with `startMs` and `endMs`. It measures both files, so the levels do not depend on how loud the music file happens to be.

`duck-mix.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/duck-mix.py (75 lines).
```

```bash
cd /path/to/project
python3 duck-mix.py voice.mp3 music.mp3 voice.captions.json mix.wav --voice-at=4 --tail=5 --merge=0.6
```

```text
voice -20.6 LUFS, music -22.9 LUFS. Music gain -17.7 dB under speech, -7.7 dB between. 2 speech stretches. 37.7 s written to mix.wav
```

We measured what it did in that test, by subtracting the voice from the mix and reading what was left:

| Where | Music level (RMS) |
|---|---|
| Before the voice, 1 to 3 s | -28.6 dB |
| Under speech, 6 to 12 s | -39.1 dB |
| After the voice | -27.5 dB |
| The voice itself, for comparison | -21.1 dB |

So it ducked about 10 dB, as asked, and sat about 18 dB under the voice by that plain measure. A file with 200 separate speech stretches, 10 minutes long, took under 3 s on the Mac.

With no gap of more than `--merge` seconds, the whole voice counts as one stretch and the music stays down until it ends. That is often what you want.

Put the mix on your picture, copying the picture as it is:

```bash
cd /path/to/project
ffmpeg -nostdin -y -v error -i film.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest film.mixed.mp4
```

Your captions need to move if the voice moved. With `--voice-at=4`, every word is 4 s later than its caption time.

### 4b. Mix inside Remotion

Use this if the video is a Remotion project. It is a better fit when the cut may change, because the mix renders with the picture. `<Audio>` volume is a gain on the file's own level. **So measure the music first**, then work out the gains:

```text
gain under speech = voice LUFS - 20 - music LUFS
gain between      = gain under speech + 10
Example: -20.6 - 20 - (-22.9) = -17.7 dB under speech, and -7.7 dB between.
```

`src/Bed.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/Bed.tsx (52 lines).
```

Save this as `src/Sfx.tsx`

```tsx
import React from 'react';
import {Audio, Sequence, staticFile, useVideoConfig} from 'remotion';

// Plays a short sound so that its loudest moment lands one frame before `at`.
// peak comes from peak-time.py. gainDb is relative to the file's own level.
export const Sfx: React.FC<{
	readonly src: string;
	readonly at: number;
	readonly peak: number;
	readonly gainDb: number;
}> = ({src, at, peak, gainDb}) => {
	const {fps} = useVideoConfig();
	return (
		<Sequence from={at - Math.round(peak * fps) - 1} layout="none">
			<Audio src={staticFile(src)} volume={10 ** (gainDb / 20)} />
		</Sequence>
	);
};
```

Here is a working use of both.

Save this as `src/Root.tsx`

```tsx
import React from 'react';
import {AbsoluteFill, Audio, Composition, Sequence, staticFile} from 'remotion';
import {Bed} from './Bed';
import {Sfx} from './Sfx';

// 3 s of music alone, then the voice, then a tail. speech comes from the captions file.
const VOICE_AT = 90;
const Film: React.FC = () => (
	<AbsoluteFill style={{background: '#16213e'}}>
		<Bed src="music.mp3" openDb={-7.7} duckedDb={-17.7} speech={[[VOICE_AT + 4, VOICE_AT + 390], [VOICE_AT + 424, VOICE_AT + 870]]} />
		<Sequence from={VOICE_AT} layout="none">
			<Audio src={staticFile('voice.mp3')} />
		</Sequence>
		<Sfx src="whoosh.wav" at={45} peak={0.078} gainDb={-8} />
	</AbsoluteFill>
);

export const Root: React.FC = () => (
	<Composition id="mix" component={Film} width={1280} height={720} fps={30} durationInFrames={1110} />
);
```

Save this as `src/index.ts`

```ts
import {registerRoot} from 'remotion';
import {Root} from './Root';

registerRoot(Root);
```

If you are starting a new project, install Remotion. All `remotion` and `@remotion/*` packages must be the exact same version:

```bash
cd /path/to/project
mkdir -p src public out
npm init -y >/dev/null
npm i --save-exact remotion @remotion/cli react react-dom
```

A project must have a `tsconfig.json`, or every command stops with `Could not find a tsconfig.json file in your project`.

Save this as `tsconfig.json`

```json
{"compilerOptions":{"target":"ES2022","module":"ES2022","moduleResolution":"bundler","jsx":"react-jsx","strict":true,"skipLibCheck":true,"esModuleInterop":true,"noEmit":true},"include":["src"]}
```

If `remotion.config.ts` already exists, keep it and add only the lines it lacks.

Save this as `remotion.config.ts`

```ts
import {Config} from '@remotion/cli/config';
import {existsSync} from 'node:fs';
import {homedir} from 'node:os';
import {join} from 'node:path';

// How Chrome draws. 'angle' needs no GPU.
Config.setChromiumOpenGlRenderer('angle');

// Caps the video frame cache. Left uncapped, it has run a 16 GB machine out of memory.
Config.setOffthreadVideoCacheSizeInBytes(800000000);

// A Chrome is here only if Remotion's own download was refused and one was added by hand.
const toolsDir = process.env.VIDEO_TOOLS ?? join(homedir(), '.cache/video-tools');
const chrome = join(toolsDir, 'chrome/current/chrome-headless-shell');
if (existsSync(chrome)) {
  Config.setBrowserExecutable(chrome);
}
```

Its comment names another setup script. You do not need that script here: the commands below do the same job.

**If Chrome will not download.** On Linux x64, Remotion downloads its browser from `remotion.media`. If the proxy refuses that, take the same version from Google and put it where `remotion.config.ts` looks:

```bash
cd /path/to/project
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

Then render, and measure what you made:

```bash
cd /path/to/project
npx remotion render src/index.ts mix out/mix.mp4 --offthreadvideo-cache-size-in-bytes=800000000
```

Files go in `public/`. In the example, `speech` is written by hand from the captions at 30 frames a second: `frame = startMs × 30 ÷ 1000`. Work it out in your own code from the captions. We rendered this example, with real music, a generated voice and the whoosh, in 19 s on the Mac, and measured it: -21.3 LUFS before mastering, with the music at -32.4 dB (mean volume) in the open stretch from 1.6 to 2.9 s.

Traps:

- A `volume` callback counts frames from where its own `Sequence` starts, not from the start of the composition.
- A looping music file needs `loopVolumeCurveBehavior="extend"`, or the curve restarts each time the file loops, and the fade-out never plays. `Bed` has it.
- `volume` numbers: 0.5 is -6 dB, 0.3 is -10.5 dB, 0.1 is -20 dB.
- Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees. Others need a company licence. Tell the user once if you start a project: `https://www.remotion.dev/license`.

### 5. Find music and sound effects

These are **examples of public libraries**, as starting points. The user may have their own, or a brand sound. Ask. Hosts differ per environment, so test with curl. `freesound.org` was refused in a real cloud session on 2026-11-09, and Pixabay answered 403 to curl from a Mac that day. When a host is refused, the user can download the file in their own browser and upload it to you.

**Start with a ready-made pack that always works in a cloud session.** remotion-effects-library ships ten short sound effects. Its own script made them, and its `public/ASSETS.md` marks them CC0, so they need no credit. They come from `raw.githubusercontent.com`, which is on the default network list:

```bash
cd /path/to/project
mkdir -p public/sfx
for s in chime click impact key pop riser shutter sub-drop swish whoosh; do
  curl -fsSL -o public/sfx/$s.mp3 https://raw.githubusercontent.com/vivmagarwal/remotion-effects-library/main/public/audio/sfx/$s.mp3
done
```

| Sound | Length | Suits | Where to place it |
|---|---|---|---|
| `impact` | 1.5 s | A word or number slamming in | 1 frame before the hit |
| `sub-drop` | 1.6 s | A big reveal, under an `impact` | On the reveal |
| `riser` | 2.0 s | A build-up to a reveal | Ending on the cut |
| `whoosh` | 0.6 s | A transition | Starting 10 frames before the cut |
| `swish` | 0.3 s | Something quick sliding in | As it starts to move |
| `pop` | 0.2 s | A list item or label appearing | 1 frame before it grows |
| `click` | 0.1 s | A button press on a screen | On the press |
| `key` | 0.2 s | Typing, one per letter or a few | On each keystroke |
| `shutter` | 0.3 s | A photo or a freeze frame | On the frame |
| `chime` | 1.1 s | A tick, a success, a notification | On the moment |

Step 6 places them by their loudest moment. For a quick preview, this is enough, where `from` is the frame the sound starts on:

```tsx
<Sequence from={13} layout="none">
	<Html5Audio src={staticFile('sfx/impact.mp3')} volume={0.5} />
</Sequence>
```

`Html5Audio` and `Audio` from `remotion` are the same component.

| Library | Has | Licence, check each file |
|---|---|---|
| `https://freesound.org/` (refused in a cloud session, so the user downloads) | Sound effects | Each sound differs. Filter for CC0 (no credit needed) |
| `https://kenney.nl/assets` | Game sound packs | Listed on each asset |
| `https://mixkit.co/free-sound-effects/` | Sound effects and music | Its own licence |
| `https://pixabay.com/sound-effects/`, `https://pixabay.com/music/` | Both | Its own licence |
| `https://freemusicarchive.org/` | Music | Each track differs |
| `https://incompetech.com/` | Music | Creative Commons with credit, or paid |
| YouTube Audio Library (in `https://studio.youtube.com/`) | Music and effects | Check its terms, especially off YouTube |
| `@remotion/sfx` on npm (MIT package; sounds hosted on `remotion.media`) | Short effects | See below |

**Read the licence.** Several big free libraries let you use a file in a video but forbid redistributing the file itself, so do not commit it to a public repository. Keep a note of where each sound came from and its licence, beside the sound.

**`@remotion/sfx`** exports URLs. The plain ones are `whip`, `whoosh`, `pageTurn`, `uiSwitch`, `mouseClick`, `shutterModern`, `shutterOld` and `ding`. Many others are meme clips, whose rights we did not check, so avoid them in serious work. You can download one directly where `remotion.media` answers. It is not on a cloud session's default network list:

```bash
cd /path/to/project
curl -sSfLO https://remotion.media/whoosh.wav
```

**Or generate a test tone,** so that you can test your mix with no network. It is not real music:

```bash
cd /path/to/project
ffmpeg -nostdin -y -v error -f lavfi -i "sine=frequency=220:duration=60" -af volume=-20dB test-music.wav
```

### 6. Place sound effects

Save this as `peak-time.py`

```python
#!/usr/bin/env python3
"""Say how far into a sound its loudest moment is, so you can place it on a frame.

  python3 peak-time.py whoosh.wav [--fps=30]
"""
import argparse
import array
import os
import subprocess

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
p = argparse.ArgumentParser()
p.add_argument('file')
p.add_argument('--fps', type=float, default=30)
a = p.parse_args()

SR = 48000
raw = subprocess.run([FFMPEG, '-nostdin', '-v', 'error', '-i', a.file, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                     capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
samples = array.array('h', raw)
loudest = max(range(len(samples)), key=lambda i: abs(samples[i]))
at = loudest / SR
print(f'{os.path.basename(a.file)}: {len(samples) / SR:.3f} s long, peak at {at:.3f} s, which is {at * a.fps:.1f} frames in at {a.fps:g} fps')
```

```bash
cd /path/to/project
python3 peak-time.py whoosh.wav
```

```text
whoosh.wav: 0.154 s long, peak at 0.078 s, which is 2.3 frames in at 30 fps
```

Peaks we measured on the public files on 2026-11-09: `whoosh` 0.078 s, `ding` 0.150 s, `page-turn` 0.168 s, `mouse-click` 0.217 s.

**The rules that worked:**

- The sound's peak lands 1 to 3 frames **before** the visual event, never on it. Early reads as anticipation. Late reads as a mistake. `<Sfx>` puts it 1 frame before.
- No more than 3 effects in any 15-frame window.

**Starting levels relative to the voice.** A sound file has its own level, so render, measure and ask a person.

| Effect | Level against the voice | Where |
|---|---|---|
| Impact | -4 to 0 dB, the loudest thing in the mix | On the event |
| Whoosh | -10 to -6 dB | Across a cut or a move |
| Sub drop | -8 dB | A title's landing frame |
| Chime | -14 dB | The frame something confirms |
| Shutter | -12 dB | The capture frame |
| Swish | -14 dB | 1 frame before a small element moves |
| Pop | -16 dB | When something appears |
| Key or click | -20 dB, varied by 2 dB for keys | When a key or a control changes |

Gains that worked under one narration at 30 frames a second: 0.22 to 0.3 for whoosh, impact, swish and pop. With music only: swish 0.5, riser 0.55, whoosh 0.4 to 0.45, impact 0.6 to 0.85. They apply to those particular files. Yours will differ.

### 7. Check for dead air

Dead air means sound stops when it should not.

`dead-air.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/dead-air.py (49 lines).
```

```bash
cd /path/to/project
python3 dead-air.py film.mp4
```

Our voice-only test film, with 0.7 s pauses between paragraphs and no music:

```text
True silence (under -80 dB) longer than 20 frames (0.67 s): 2
      8.84 s to 9.54 s (0.70 s)
     21.16 s to 21.85 s (0.70 s)
Quiet stretches (under -45 dB) longer than 1.5 s: 0
```

It exits 1 for that. With music mixed under it, the same film gave 0 and 0, and exited 0. Generated voices have true silence between sentences, because a generated voice has no room sound, so music or room sound under it is the floor. A clean take of real speech measured about -87 dB between words.

Then decide. A long pause on a strong picture may be right. Ask. A 3-second hole in the middle of a sentence is not. We tested this by adding 4 s of silence to the end of a voice: it was listed in both groups.

### 8. Master, once, last

`master-audio.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/master-audio.py (114 lines).
```

```bash
cd /path/to/project
python3 master-audio.py film.mp4                                      # -16: a podcast or an unknown platform
python3 master-audio.py film.mp4 --target=-14 --out=film.youtube.mp4  # -14: YouTube or a short social clip
```

```text
film.mp4 -> film.mastered.mp4
  asked      -16.0 LUFS    -1.5 dBTP    11.0 LU
  before     -20.8 LUFS    -5.5 dBTP     2.6 LU
  after      -16.0 LUFS    -1.5 dBTP     2.5 LU
  mode: dynamic (linear keeps the mix as it is; dynamic rides the level)
```

**How it works.** One pass of `loudnorm` undershoots a speech-led mix. So pass 1 measures. Pass 2 applies the filter with those measurements. Pass 3 measures the result.

**Report the `after` row, never the target.** The master lands near the target, not on it. Over six real renders at -16 and -1.5: loudness came out from -16.1 to -16.6 LUFS, and peak from -1.5 to -1.2 dBTP. On our voice test: -16.0 asked for -16, and -14.0 asked for -14, by this reading and by `ebur128`.

**Read the `mode` line.**

- `linear` means one gain over the whole film, so your mix stays exactly as you made it. In our test, asking for -22 LUFS gave `linear`.
- `dynamic` means that the gain needed would have pushed the peaks over the ceiling, so `loudnorm` rode the level instead. All our -16 and -14 tests came back `dynamic`. On voice alone the loudness range moved only from 2.6 to 2.5 LU, and the target was hit, so for plain narration it is usually fine. On voice with music it moved from 10.6 to 6.7 LU, which changes the balance you mixed. Then use the limiter below.

If a few moments are much louder than the rest, the tool cannot raise the whole film evenly. Calm those moments first.

**To keep your mix as it is, tame the peaks first.** A limiter (`alimiter`, in full ffmpeg builds) holds down only the loudest moments, so `loudnorm` can stay linear. Choose the limit from the `before` row: loudness plus about 13.5 dB for a -16 master, or plus about 11.5 dB for a -14 master. For -21.3 LUFS and a -16 master, that is -7.8 dB, which is 0.407 as a number (`10 ** (-7.8 / 20)`):

```bash
cd /path/to/project
ffmpeg -nostdin -y -v error -i mix.mp4 -c:v copy -af "alimiter=limit=0.407:level=false:attack=5:release=50" -c:a pcm_s24le mix.limited.mov
python3 master-audio.py mix.limited.mov --out=mix.final.mp4
```

```text
  asked      -16.0 LUFS    -1.5 dBTP    11.0 LU
  before     -21.3 LUFS    -7.8 dBTP    10.6 LU
  after      -16.0 LUFS    -2.5 dBTP    10.6 LU
  mode: linear (linear keeps the mix as it is; dynamic rides the level)
```

That is a real result on our voice-and-music test: the range held at 10.6 LU, and the picture's `MD5` still matched. A -14 master of another mix took a limit of 0.335 and also came back `linear`, at -14.0 LUFS and -2.1 dBTP. A limiter pressed too hard can be heard, and this machine cannot hear it. Ask a person, and keep the limit as gentle as the numbers allow.

**If you miss the target,** it exits 1 and the file is still written. A real example: a music-only file at -22.9 LUFS and -1.4 dBTP, a gap of 21.5 dB, came out at -17.1 when asked for -16. Gain moves both numbers together, so you cannot get there by volume alone. Fix the mix, render again, or ask the user if a quieter master is fine.

**If the peak is over,** it says by how much. Do not master the master. Go back to the original, with a whole dB of margin. The peak does not follow the ceiling tenth for tenth: on one real film, asking for -1.5 gave -1.2, asking for -1.6 and -1.8 both gave -0.9, and only -2.5 landed under -1.5.

**Rules:**

- Master once, last, on the finished render.
- Add no second normaliser after it.
- Do not master a file that will be re-encoded again.
- It accepts `.mp4`, `.mov`, `.m4a`, `.mkv`, `.mp3` and `.wav`. On video it writes AAC at 320 kb/s and 48 kHz, and sets the file up to start playing before it has fully downloaded (`+faststart`).

**Why `asetpts` is in there.** Without this setting, the sound can drift up to 0.1 second behind the picture near the end.

### 9. Prove the picture did not change

Mastering re-encodes only the sound. Prove it. These two lines must print the same `MD5`:

```bash
cd /path/to/project
ffmpeg -nostdin -v error -i film.mp4 -map 0:v -c copy -f md5 -
ffmpeg -nostdin -v error -i film.mastered.mp4 -map 0:v -c copy -f md5 -
```

In our test both printed the same value. And check that the sound and the picture still have the same length:

```bash
cd /path/to/project
ffprobe -v error -show_entries stream=codec_name,duration -of compact film.mastered.mp4
```

```text
stream|codec_name=h264|duration=29.500000
stream|codec_name=aac|duration=29.482000
```

A subtitle track in the file survives. We tested that too.

### 10. Ask a person

Since this machine cannot listen, send the sound to someone, as a chat file under 30 MiB. Audio alone is small: 30 seconds came to about 420 KB. For a very long film, send a part.

```bash
cd /path/to/project
ffmpeg -nostdin -y -v error -i film.mastered.mp4 -vn -c:a aac -b:a 128k listen.m4a
```

For example:

> Here is the sound. I set it to a good volume for the web, and the music dips while you speak. Could you listen on your usual speakers? Is the voice clear, is the music right for it, and do any of the sound effects feel wrong?

If they ask for a change, change the mix, render again, and master again from the new render.

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs.

Commit the scripts, the captions and your notes on where sounds came from, and push. A commit hook may reformat files you did not touch: run `git status`, and restore only the files that were clean before.

## How to talk to the user

- Plain words: "how loud", "the music dips while someone speaks". If they ask about a number, say: "It is the standard measure of how loud a video feels."
- Ask one question at a time, with a suggestion. "Where will this go? If it is YouTube or a short clip, I will make it a little louder. If you are not sure, I will use a safe middle volume."
- Ask for their taste. "Do you have music you like, or a brand sound? If not, I can find some from a free library for you to choose from."
- Say plainly that you cannot hear. "The measurements say the music sits well under the voice" is honest. "It sounds great" is not.
- Before committing a downloaded sound or paying for one, tell them its licence, and pause.
- Pause for their OK on the choice of music, and on the first full mix, before you master.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `No such filter: 'ebur128'` or `'volumedetect'` | You are using Remotion's ffmpeg | Use a full build. See "What you need" |
| `Could not measure ... Does it have sound?` | No audio stream, often `Output file does not contain any stream` | Check with `ffprobe`. Render with its sound |
| `MISSED the target by 1.1 LU` | A file with a big gap between peak and loudness, or with little in it | Fix the mix, or accept a quieter master. Read the `after` row |
| `note: 0.2 dB over the ceiling` | The ceiling is a request, not a limiter | Report the number. If the platform is strict, master again from the original with `--peak` a whole dB lower |
| `--out would overwrite the input` | The same name in and out | Keep the original |
| `Unknown output type` | An unusual extension | Use one on the list |
| `mode: dynamic` | The gain needed would break the ceiling | Fine for speech. For a mix with music, use the limiter in step 8, and have a person listen |
| Sound ends up to 100 ms late | `asetpts` is missing from a hand-written command | Use `master-audio.py` |
| Music lifts between every sentence | Ranges were not merged | `--merge=1.2`, or more |
| Music does not lift at all between sections | The gaps are under `--merge`, which merges them into one | Use a smaller `--merge` |
| The fade-out does not play on looped music in Remotion | No `loopVolumeCurveBehavior="extend"` | Add it |
| A volume curve lands at the wrong time | It counts from its `Sequence`, not the film | Move it, or subtract the start |
| Video louder or quieter after re-export | It was re-encoded and normalised after mastering | Master last |
| `check` on a mix says pauses are missing | Music fills pauses | Run such checks on the voice alone |
| `CONNECT tunnel failed, response 403` or `Host not in allowlist` for a sound library | The proxy refused | Ask the user to allow the host, or to upload the file |
| Your loop stops early with no error | ffmpeg reads standard input and ate your list | Add `-nostdin`, or `</dev/null`. These scripts already do |

## How to check it worked

1. **The number is near the target.** `ebur128` on the master reads within 1 LU of your target, and the peak is at or under what the platform allows.
2. **The picture is untouched.** The two `MD5` lines in step 9 match.
3. **The lengths match.** `ffprobe` shows the sound and the picture within about 0.1 s.
4. **There is no dead air you did not choose.** `dead-air.py` lists nothing unexplained.
5. **The mix holds up.** Measure the voice and the music where you can. A file check cannot tell you the video is good, and neither can `ebur128`.
6. **Look at a frame,** to be sure you mastered the right video:
   ```bash
   cd /path/to/project
   ffmpeg -nostdin -y -v error -ss 3 -i film.mastered.mp4 -frames:v 1 check.png
   ```
7. **A person has listened** on real speakers and said yes.
