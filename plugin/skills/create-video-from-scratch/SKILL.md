---
name: create-video-from-scratch
description: Build a narrated or silent video from nothing with Remotion, with a full project, a free computer voice, a voice-timed structure and worked examples. Use it when someone wants a new video written as code and rendered to MP4.
---
# Create a video from scratch

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill (a guide that runs a whole job and hands parts to other guides) sent you here, go back to it when you finish.

**Read up to the heading `## Files`, and stop there.** Everything after that heading is scripts and a page, which Step 2 saves for you.

## What this skill does

It takes you from an empty folder to a finished MP4, using Remotion. It gives you:

- every project file, in full

- a free computer voice that writes its own word timings

- a structure where the voice file sets the timing, so a new voice re-times the whole video

- a worked diagram that animates, and a silent route that can hit a set length

- the rules that stop a render from coming out wrong

- the last steps: setting the sound level, and handing the video over on a private page

- a small worked example you can render in a few minutes, with no paid service

A video here is a list of blocks. A block is either a card or a voice block. A card lasts a set number of frames and can hold any picture: text, a diagram, a clip. A voice block gets its length from its voice file. Inside a voice block, every change of picture is tied to a phrase the narrator says, never to a typed frame number.

## When to use it (and when not to)

Use it for explainers, title pieces, lessons, product walk-throughs and anything built from text, diagrams, images and clips, with or without a voice.

Do not use it to edit a long recording of people talking (cutting pauses and fixing a talk is a different job). A simple trim needs only ffmpeg. For a look-only change to a video that already exists, change that project instead of starting a new one.

## What you need before you start

| Need | How to check | If it is missing |
|---|---|---|
| Node and npm | `node --version` and `npm --version` | Install Node from nodejs.org |
| npm registry | `npm view remotion version` | Ask the user to allow `registry.npmjs.org` |
| Python 3, for the voice and the last steps | `python3 --version` | Install it |
| Full ffmpeg | `ffmpeg -hide_banner -filters \| grep -w tile` | See "Get a full ffmpeg" in Step 2 |
| A voice, if the video is narrated | Ask the user | Step 6. The free computer voice is the default |

Do not check Chrome yet. Chrome comes in Step 2, after the install. Before that install, `npx remotion browser ensure` fails with `npm error could not determine executable to run`. That error does not mean Chrome is missing.

No API key is needed. Rendering needs no network once Chrome is installed and the fonts are local files.

### If you are in a Claude Code cloud session

These were true when this was written. Test instead of trusting them.

- It is a Linux x64 container: 4 cores, about 15 GB of memory, no swap, no GPU, cloned fresh and reclaimed after a while.

- The Bash tool stops at 10 minutes and a background command stops after 30 minutes, or after up to 2 hours if you start it with `timeout: 7200000`. Bare `sleep` is blocked, so wait with a Monitor until-loop or a bounded check loop.

- Outbound traffic goes through a proxy. Test a host with `curl -sS -o /dev/null -m 15 -w '%{http_code}\n' <url>`. A refusal is `CONNECT tunnel failed` or `Host not in allowlist`. Any other status means the host answered. The user can change allowed hosts in the session's cloud environment menu: Edit, then Network access.

- A worker restart kills running processes, `nohup` included, but files usually survive. A container rebuild can roll the disk back to an older snapshot: `node_modules`, anything outside git and unpushed commits can go. Only what is pushed is sure to survive. Commit and push often.

- Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs.

- GitHub refuses a file over 100 MB. `SendUserFile` refuses files over 30 MiB (`exceeds the 30 MiB upload limit`).

- `pgrep -f` and `pkill -f` match their own command line. Use a pattern like `[r]emotion render`, or wait on files.

- A commit hook may reformat files you did not touch. Run `git status` after a commit, and restore only files that were clean before it.

## Steps

**About folders.** A `cd` may not carry over from one command to the next. So every command block below starts with its own `cd`. Use your project's real full path in place of `/path/to/my-video`.

### Step 1. Agree the video with the user

Before you build, settle these. Ask one at a time, each with a recommendation (see "How to talk to the user").

- What is it for, and who watches it?

- Narrated or silent?

- How long? Plan the length from the words: a narrated video at about 144 words a minute (a starting point) runs about 2.4 words a second. Measure your real voice file, because voices differ. If the user needs an exact length, see "Hit a set length" in Step 9.

- What shape? 1920x1080 is the usual landscape. 1080x1920 is the usual phone shape, and needs its own layout.

- Any brand colours, fonts, sample videos or reference videos? Ask. Everything in this file about look is only an example.

Write the script before you build pictures. Plain, short, spoken sentences work best. Start with a person, a moment or a number. Say what the video is about early. Never invent a fact, a number, a name or a quote.

### Step 2. Make the project

Remotion is a tool that makes videos from React code. Each frame is a web page. Chrome takes a picture of it, and a native helper called the compositor joins the pictures into a video. Do this step once per project.

**Make the folder, and save this guide's files.** Copy this skill's files into the new folder. Files already there are kept. Do not retype long files: one slip can break them.

```bash
mkdir -p /path/to/my-video
```

```bash
cd /path/to/my-video
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/create-video-from-scratch"
cp -rn "$S/files/." . 2>/dev/null; test -e "tsconfig.json" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

**Install.** All `remotion` and `@remotion/*` packages must be the exact same version, so use `--save-exact`.

```bash
cd /path/to/my-video
npm init -y
npm pkg set type=module
npm i --save-exact remotion @remotion/cli @remotion/fonts @fontsource/inter react react-dom
npx remotion versions
```

The last line must end with `All packages have the correct version.` When this was written the latest Remotion was 4.0.541. Check yours with `npm view remotion version`. If you add a Remotion package later, pass the same version: `npm i --save-exact @remotion/lottie@$(node -p "require('./node_modules/remotion/package.json').version")`.

On Linux x64, npm also pulls the compositor by itself through the optional dependency `@remotion/compositor-linux-x64-gnu`. You do not need an extra step unless npm itself is refused.

**The two config files.** The script above has saved them. `tsconfig.json` must be there: without it every command stops with `Could not find a tsconfig.json file in your project`.

Save this as `tsconfig.json`:
```json
{"compilerOptions":{"target":"ES2022","module":"ES2022","moduleResolution":"bundler","jsx":"react-jsx","strict":true,"skipLibCheck":true,"esModuleInterop":true,"noEmit":true},"include":["src"]}
```

`remotion.config.ts` chooses how Chrome draws, and finds a Chrome you fetched by hand. If `remotion.config.ts` already exists, keep it and add only the lines it lacks.

Save this as `remotion.config.ts`:
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

GL is the part of Chrome that draws graphics. `angle` is the GL setting used here. It worked in a cloud container with no GPU, and it is fast. Step 8 covers the other setting, `swangle`. The comment in this file names `setup-video.sh`, a script this guide does not use: the Chrome fallback below puts Chrome in the same place.

Only the command line reads this file. The Node API (Remotion's functions, called from your own script) does not.

**Get Chrome.**

```bash
cd /path/to/my-video
npx remotion browser ensure
```

On Linux x64 this downloads Chrome Headless Shell (a Chrome with no window, made for scripts) from `remotion.media` into `node_modules/.remotion/chrome-headless-shell`. If the network refuses that host, you will see `CONNECT tunnel failed, response 403` or `Host not in allowlist`. Take the same Chrome version from Google instead:

```bash
cd /path/to/my-video
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

`remotion.config.ts` then finds this Chrome by itself. The version was 158.0.8127.2 at Remotion 4.0.541. A `require()` of that file fails because the package does not export it, which is why the command uses `grep`. Both download hosts answered 200 from a Mac on 2026-11-09. On an earlier Remotion, cloud sessions saw `storage.googleapis.com` reachable and the render host refused. This block was run on a Mac with the Mac build of the same Chrome (`mac-arm64` in place of `linux64`, in both names), with Remotion's own copy removed: the config found it, and a still rendered. The Linux build was not tested.

**Get a full ffmpeg.** ffmpeg is the standard command-line video tool. `npx remotion ffmpeg` exists, but it is a cut-down build with no `tile` filter, so it cannot make contact sheets (one image holding many small frames). Check first:

```bash
ffmpeg -hide_banner -filters | grep -E ' (tile|ebur128|silencedetect|blackdetect|freezedetect) '
```

You want five rows. If ffmpeg is missing, use `brew install ffmpeg` on a Mac (not tested here, as this Mac already had ffmpeg) or `sudo apt-get install -y ffmpeg` on Linux. If that is refused (an earlier cloud session saw `deb.debian.org` answer 403), install a static build from PyPI:

```bash
cd /path/to/my-video
python3 -m venv .tools
.tools/bin/pip install -q imageio-ffmpeg
mkdir -p .tools/bin
ln -sf "$(.tools/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .tools/bin/ffmpeg
export PATH="$PWD/.tools/bin:$PATH"
```

That build has no `ffprobe` (the tool that reads a video file's details). Use `npx remotion ffprobe` in its place. An earlier cloud session found its Linux build has `tile`, `select` and `volumedetect` but no `drawtext`. Run the `export` line again in each new shell if your shell does not keep it.

**Keep big files out of git.**

```bash
cd /path/to/my-video
printf 'node_modules\nout\nbuild\n.tools\n' > .gitignore
```

**Licence, tell the user once, plainly.** "Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees. Other companies need a company licence. Details are in `node_modules/remotion/LICENSE.md` and at remotion.dev/license."

### Step 3. Understand the structure

Keep one entry file per video. An entry file is the file you hand to Remotion, for example `src/demo-entry.tsx`. It holds `registerRoot`, the call that tells Remotion what the file offers, and one composition. A composition is one video Remotion knows about: an id, a size, a length and a frame rate. With one entry per video, each bundle stays small, and a mistake in one video cannot stop another from rendering. A bundle is your code packed into a folder of web files that Chrome can open.

```
my-video/
  package.json  tsconfig.json  remotion.config.ts  .gitignore
  public/                 files the video loads, read with staticFile()
    fonts/                font files
    demo/n1.txt           what block 1 says
    demo/n1.wav           its voice (or .mp3)
    demo/n1.captions.json its word timings
    demo/clip.mp4         footage
  src/
    kit.tsx               the shared clock and parts
    Demo.tsx              one video
    demo-entry.tsx        registers that one video
```

**The block list.** This one line is the heart of the structure:

```ts
const L = layout([
	{kind: 'card', frames: 60},
	{kind: 'voice', caps: n1},
	{kind: 'voice', caps: n2},
]);
```

`layout` reads each block's length from its word captions, then returns `L.at` (start frames), `L.len` (lengths) and `L.duration`. A voice block is 12 frames of air, then the voice, then 18 frames of tail. The last block gets 75 more frames, because a video that stops half a second after its last word feels cut off. These numbers are starting points.

**Word captions** are a JSON list of words with times. Every word after the first starts with a space, as `@remotion/captions` expects. Without that space, that package shows one giant caption page and no error. `cue` below ignores the spaces.

```json
[{"text": "A", "startMs": 0, "endMs": 160}, {"text": " video", "startMs": 160, "endMs": 400}]
```

**`cue(captions, phrase)`** gives the frame where a phrase starts being said, on that block's own clock:

```ts
const CLIP = cue(n2, 'Here is a moving clip');
```

`cue` works the same on captions from any source. Know these two facts about it, because they cause most of its trouble:

- It returns the **first** match. A phrase also said earlier cuts at the wrong place and can produce `durationInFrames must be positive, but got -12`. So choose a phrase said once in that block ("sales team who would", not "the team").

- It **throws** when the phrase is not said. That is on purpose: a new voice either re-times the video or stops loudly. Read the error: it prints what the block really says.

Match what the captions say, not what the script says. In a test, a script saying "thirty of them" came back from the transcriber as "30 of them", and `cue(n1, 'thirty of them')` stopped the render with: `cue: "thirty of them" is not in this voice block. It says: "A video is a stack of still pictures, each second shows 30 of them."`

### Step 4. Write the shared kit

This file holds the clock, `layout`, `cue`, an entrance, a sentence card, captions and the voice block. Change the colours and fonts to suit the user.

`src/kit.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/kit.tsx (189 lines).
```

The `Narrated` part puts the pictures, the sound and the captions on one clock, so a `cue` frame can be used directly inside it.

### Step 5. Learn the rules that keep a render correct

Each of these has cost someone a re-render.

**Everything moves from the frame number.** Remotion renders frames out of order, in several browser tabs at once, so anything that depends on real time comes out wrong. Often it comes out wrong with no error.

| Do not use | Use |
|---|---|
| `Math.random()` | `random('a-seed')` from `remotion`: same value on every frame and every render |
| CSS `animation`, CSS `transition` | `useCurrentFrame()` with `interpolate()` or `spring()`. Step 9 has a worked example of both |
| `setTimeout`, `setInterval`, `Date.now()` | The frame number |
| A plain `<img>` | `<Img>` from `remotion`, which holds the render until it has loaded |
| `fetch` with nothing holding the render | `delayRender()` and `continueRender()` around it |

**Clamp `interpolate` and give it finite numbers.** Pass `extrapolateLeft: 'clamp'` and `extrapolateRight: 'clamp'` unless you want it to run on. Never pass `Infinity`. It stops the render with `inputRange must contain only finite numbers, but got [0,Infinity]`. For "until the end", use the real length: `durationInFrames` from `useVideoConfig()`.

**Non-breaking spaces need a JS string in an attribute.** A non-breaking space keeps two words on one line, and it fixes a line that breaks badly. Tested on Remotion 4.0.541:

```tsx
<Statement text={'every\u00A0second'} />   // right: shows "every second" and never breaks there
<Statement text="every\u00A0second" />     // wrong: the screen shows the letters \u00A0
<Statement text="every&nbsp;second" />     // also right
```

**Load every font, in every weight you use.** If you name a font that is not loaded, there is no error and you silently get a default serif font. Look at a still. `kit.tsx` loads only weights 500 and 800, so a `fontWeight: 600` needs its own file added to the list. Two ways to load one:

- From files, as `kit.tsx` does: install it from npm (`@fontsource/inter`), copy the `.woff2` web font files you need into `public/fonts/`, and load them with `loadFont` from `@remotion/fonts`. It needs no network at render time. A still rendered this way with all outbound network denied came out in the right font (tested on a Mac).

- From Google, the shorter way: `const {fontFamily} = loadFont('normal', {weights: ['800'], subsets: ['latin']});` with `loadFont` from `@remotion/google-fonts/Inter`. It fetches the font when rendering. With the network denied, the same test stopped with an error holding the words `exceeded rendering` and `Fetching Inter font`. In a real cloud session on 9 November 2026, Chrome refused the font hosts through the proxy (`net::ERR_CERT_AUTHORITY_INVALID`) and every still timed out, so in a cloud session use files.

**Files in `public/` are read with `staticFile()`.** `staticFile('demo/clip.mp4')`, with no `public/` in the path and no leading slash.

**`<OffthreadVideo>` shows footage** frame by frame, exactly, with `style` for its size. It runs in the compositor, so it renders reliably.

- It holds its last frame with no error when the clip runs out. A 4 s clip asked for frame 200 quietly showed the last picture. So give its `<Sequence>` a `durationInFrames` no longer than the clip.

- Start later in a file with `trimBefore={90}` (frames of the clip, not seconds). Use `muted` when the clip's own sound is not wanted.

- Long clips can take a lot of memory. An uncapped cache took 10.2 GB of 16 GB in an earlier cloud job and restarted the container. Pass `--offthreadvideo-cache-size-in-bytes=800000000` on a long render.

**`<Audio>` plays a sound.** Put it inside a `<Sequence from={frame} layout="none">` to start it later. A `volume` function gets the frame counted from where that Sequence starts.

**`<Sequence>` shifts time for what is inside it.** Inside `<Sequence from={100}>`, `useCurrentFrame()` reads 0 on frame 100. `layout="none"` stops it from adding a full-size box.

**A cut onto an empty frame reads as a blink.** If a part starts empty and animates in, begin it a few frames early so the first frame already shows something: `<Sequence from={cut}><Sequence from={-8}>...</Sequence></Sequence>`. Look at the frame you cut to. Inside that, `useCurrentFrame()` reads 8 on the cut, so every delay inside runs 8 frames earlier.

**A highlight must not arrive before the narrator names it.** Land it on the word's `cue`. A line of text may lead its voice by a moment, but a highlight that comes first reads as a spoiler.

### Step 6. Get the voice (for a narrated video)

You need one voice file and one captions file per block. Short blocks make fixes cheap: changing a sentence means re-voicing only that block. Ask the user which of these they want. All are examples, and new ones appear often.

| Source | Cost | Notes |
|---|---|---|
| A free computer voice, Kokoro (the default) | Free | An open voice model that runs on this machine, with no key. It writes its own word timings. English only in this guide |
| The user's own recording | Free | Often sounds most like them. Get a quiet room and one file per block if you can. Needs the timing tool below |
| A paid voice service, such as ElevenLabs | Paid: only if the user asks for it. Say the cost and get an OK first | Some services return word timings too. Convert them to the JSON shape in Step 3, or use the timing tool below |
| The stand-in in Step 7 | Free | Tones, not speech. Good for proving the chain, never for delivery |

**The free voice: set it up once.** It goes in `~/voice-tools`, outside your project. It took about 2 minutes on a Mac on 2026-11-09, and used about 790 MB of disk. A rebuilt container can wipe that folder, and then you run this again.

```bash
cd /path/to/my-video
bash setup-voice.sh
```

**Let the user choose a voice.** Make a short sample of a few voices and send them as chat files. Then ask which they like. `af_heart`, `am_michael`, `bf_emma` and `bm_george` are examples. A wrong name makes the script list every voice it has. The names start with `a` for American or `b` for British, then `f` or `m`.

```bash
cd /path/to/my-video
mkdir -p samples
for v in af_heart am_michael bf_emma bm_george; do
  printf '%s\n' 'A video is a stack of still pictures. Each second shows thirty of them.' > "samples/$v.txt"
  ~/voice-tools/venv/bin/python voice.py "samples/$v.txt" --voice="$v" --target=144
done
```

**Voice each block.** Put the words in a text file, one file per block. `--target` is the pace in words a minute, and the script takes a few tries to reach it.

```bash
cd /path/to/my-video
~/voice-tools/venv/bin/python voice.py public/demo/n1.txt --voice=af_heart --target=144
```

This writes `public/demo/n1.mp3` and `public/demo/n1.captions.json`, beside the text file, in the shape Step 3 shows. Tested on a Mac on 2026-11-09, not on Linux: this text came out at 142 words a minute, in about 7 s. It needs ffmpeg on your PATH. The first run also writes a second copy of the model, about 325 MB, that reports when each word is said.

A word said wrongly can be respelled: write `project{prodject}` in the text. The voice says the respelling, and the caption shows the word. Leave no spaces inside the braces. A blank line in the text starts a new paragraph, with a longer pause.

**Check what was said.** You cannot hear the file, so let a speech model read it back, and compare it with the script:

```bash
cd /path/to/my-video
~/voice-tools/venv/bin/python readback.py public/demo/n1.mp3 public/demo/n1.txt
```

On that file it printed `MATCH: 92.9% of 14 script words` and one difference: script `thirty`, heard `30`. Read each difference: "thirty" and "30" is harmless. A missing line, or a word that really came out as a different word, is not. Respell it, or rephrase the line. Then ask the user to listen.

**Other languages.** `voice.py`, `readback.py` and the timing tool below were written and tested for English only. For another language, tell the user early. Then try the user's own recording, or look for a voice and a speech model for that language, and test them on one sentence before you plan around them.

**To time a recording or any other voice file,** use speech recognition on your own machine. This needs no key. It uses sherpa-onnx from PyPI and models from GitHub. An earlier cloud session found `huggingface.co` refused, while PyPI and GitHub worked, which is why this route is here. The download is 482 MB, and the setup script prints where it put everything.

```bash
cd /path/to/my-video
bash tools/setup-transcription.sh
export ASR_HOME=/the/folder/it/printed
"$ASR_HOME/venv/bin/python" words-to-captions.py public/demo/n1.mp3 public/demo/n1.captions.json
```

Run the `export` line again in each new shell. Tested on a Mac, not on Linux, on speech from the macOS `say` command and on a free-voice file: 9 of 9 and 14 of 14 words came back. Read the words it prints. Compare them to your script: a transcriber writes "30" for "thirty", and adds or drops punctuation. If you need the on-screen captions spelled exactly as written, correct the `text` values and leave the times alone.

### Step 7. Build the worked example

Do this the first time, even if you are in a hurry. It proves the whole chain in a few minutes. Every command and file below was followed from this page in a fresh folder, and rendered and looked at, on an Apple Silicon Mac on 2026-11-09 with Remotion 4.0.541. It was tested on a Mac, not on Linux.

**Fonts and a sample clip:**

```bash
cd /path/to/my-video
mkdir -p public/demo public/fonts src out
cp node_modules/@fontsource/inter/files/inter-latin-500-normal.woff2 public/fonts/
cp node_modules/@fontsource/inter/files/inter-latin-800-normal.woff2 public/fonts/
ffmpeg -v error -y -f lavfi -i "testsrc2=size=1280x720:rate=30:duration=4" -pix_fmt yuv420p public/demo/clip.mp4
```

**The script:**

```bash
cd /path/to/my-video
printf '%s\n' 'A video is a stack of still pictures. Each second shows thirty of them.' > public/demo/n1.txt
printf '%s\n' 'So a video has three parts: the plan, the pictures and the sound. Here is a moving clip, played inside the picture.' > public/demo/n2.txt
```

**A stand-in voice.** This writes a soft tone per word, plus word timings, so the example needs no downloads. Use the free voice from Step 6 for anything real.

`make-demo-voice.mjs`, which the copy step puts in your folder:

```js
# In this skill's files folder: files/make-demo-voice.mjs (49 lines).
```


```bash
cd /path/to/my-video
node make-demo-voice.mjs public/demo/n1.txt public/demo/n2.txt
```

It prints `public/demo/n1.wav  5.8 s, 14 words` and `public/demo/n2.wav  9.3 s, 22 words`.

**The video:**

`src/Demo.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/Demo.tsx (130 lines).
```

**The entry file:**

Save this as `src/demo-entry.tsx`:
```tsx
import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {Demo, DEMO_DURATION} from './Demo';
import {FPS} from './kit';

const Root: React.FC = () => (
	<Composition
		id="demo"
		component={Demo}
		durationInFrames={DEMO_DURATION}
		fps={FPS}
		height={1080}
		width={1920}
	/>
);

registerRoot(Root);
```

Check that Remotion can read it:


```bash
cd /path/to/my-video
npx remotion compositions src/demo-entry.tsx
```

It lists `demo    30      1920x1080      624 (20.80 sec)`. The box "The plan" in this example lands on the frame the word "the" of "the plan" is said. Frame 330 has no box, and the box is there by frame 337.

To hear the example with the free voice, run `voice.py` on both text files, and change `demo/n1.wav` and `demo/n2.wav` to `.mp3` in `src/Demo.tsx`. Tested on a Mac: the video grew to 661 frames, and the boxes still landed on their words, because the cuts are phrases.

### Step 8. Look at stills first, then render the whole video

A whole render costs minutes, or hours on a long video. A still costs a second or two. Most defects show up in stills, so find them there.

Bundle once, then take stills from the bundle. Bundling again for each still wastes most of the time.

```bash
cd /path/to/my-video
npx remotion bundle src/demo-entry.tsx --out-dir=build/demo
rm -rf out/still out/sheets
mkdir -p out/still out/sheets
for f in 30 150 300 450 520 600; do
  npx remotion still build/demo demo "out/still/$(printf %06d $f).png" --frame=$f
done
ffmpeg -v error -y -pattern_type glob -i 'out/still/*.png' -vf "scale=640:-1,tile=3x3" out/sheets/%02d.png
```

The `rm -rf` matters: old stills left in the folder would be mixed into the sheet. Do not add `-frames:v 1` to this `tile` command. With it, ffmpeg writes only the first full grid and drops the rest: in a test, 6 stills on a 2x2 grid kept 4, with exit code 0 and no warning. Without it, ffmpeg writes as many sheets as it needs. Black tiles at the end are spare cells of the grid, not a fault.

Bundle again after each code change. A second bundle may print `○` where the first printed `+`. That mark is harmless: the stills still pick up your change. Open each file in `out/sheets/` and look at it with your own eyes. Choose the frames from the structure: the title, one frame inside each shot, and the last frame of anything that builds up. Then open any surprising frame at full size.

On an idle Apple Silicon Mac on 2026-11-09, a still from a bundle took about 1 s. On a busy machine it took several times longer. Not measured on Linux.

For a real video, take a frame about every 3 seconds. When you have many stills, a small script that opens one browser is much faster than this loop: use `bundle` from `@remotion/bundler`, then `openBrowser`, `selectComposition` and `renderStill` from `@remotion/renderer`, and pass the browser to each call as `puppeteerInstance`. Those two packages must match your Remotion version. The script was not written or tested for this guide. The loop is fine for a few frames.

**The render does not check types.** `tsconfig.json` sets `strict`, but nothing runs that check during a render. A planted error (`const wrong: number = 'text'`) still rendered with no complaint. To check them, install the type packages once and run `tsc`:

```bash
cd /path/to/my-video
npm i --save-dev typescript @types/react @types/react-dom
npx tsc -p .
```

No output means the types are clean. Without those packages, `tsc` prints a wall of `TS7016` and `TS7026` errors that say nothing about your code. An error about `@remotion/lottie` only means you have not installed it: delete `src/lottie-entry.tsx` if the video does not use it.

When the stills are right, render the whole video:

```bash
cd /path/to/my-video
npx remotion render build/demo demo out/demo.mp4 --color-space=bt709 --image-format=png --crf=20 --offthreadvideo-cache-size-in-bytes=800000000
```

A render can start from the bundle you already made, as here, or from an entry file, which bundles again first. Both were tested on a Mac. `--crf` sets quality: lower is better and larger. `--image-format=png` matters wherever footage colour matters. `--color-space=bt709` asks for the colour tags most players expect. On an idle Apple Silicon Mac on 2026-11-09 this took about 12 s for the 20.8 s example. Not measured on Linux.

**Colour tags** are labels in the file that tell a player how to show its colours. On Remotion 4.0.541 on a Mac, all four tags were present. On an older Remotion on Linux, only the matrix tag was. Not yet measured on Linux at 4.0.541. So check your file:

```bash
cd /path/to/my-video
ffprobe -v error -select_streams v -show_entries stream=color_range,color_space,color_transfer,color_primaries -of compact out/demo.mp4
```

You want `tv`, then `bt709` three times. If some are missing, write them without re-encoding:

```bash
cd /path/to/my-video
ffmpeg -v error -y -i out/demo.mp4 -map 0 -c copy -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1 -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -movflags +faststart out/demo.tagged.mp4
```

**In a cloud session, run anything long in the background,** because the Bash tool stops at 10 minutes, and write a marker file when it ends:

```bash
cd /path/to/my-video
npx remotion render build/demo demo out/demo.mp4 --color-space=bt709 --image-format=png --crf=20 --offthreadvideo-cache-size-in-bytes=800000000 > out/render.log 2>&1; echo "EXIT $?" > out/render.done
```

Useful flags: `--concurrency=<n>` for how many tabs render at once, `--frames=0-299` to render part of a video as a test, and `--gl=swangle` for the case below. One whole render at a time is the safe default on 4 cores.

**The GL setting.** Keep `angle`. `swangle` draws everything in software on the CPU. On a 4-core cloud container, on one simple film, `--gl=swangle` measured 4.6 times slower (5 against 24 frames a second, and most films are slower than that one). It also painted a ghost image of a list item (a leftover picture that should not be there) into whole renders, which stills of the same frames did not show. But a scene that really uses WebGL (3D graphics in the browser: three.js, shaders, canvas effects) failed on `angle` in that container with `Error creating WebGL context`, and rendered only with `--gl=swangle`. So use `swangle` only for a WebGL scene that fails or comes out blank. After any swangle render, scan the finished file for ghosts: take a sheet at several frames a second across the moments when things appear.

```bash
cd /path/to/my-video
ffmpeg -v error -y -ss 12 -t 2 -i out/demo.mp4 -vf "fps=6,scale=480:-1,tile=4x3" -frames:v 1 out/ghost.png
```

### Step 9. Make it yours

Now replace the example:

1. Copy `src/Demo.tsx` and `src/demo-entry.tsx` to new names, and change the composition `id`.

2. Put the real voice and captions in a new folder under `public/`. Change the `audio` paths, including the file ending if it is now `.mp3`.

3. Rewrite the `cue` phrases to match the captions.

4. Replace the pictures. A narrated video feels calm when its picture changes about every 6 to 9 seconds. It should never sit on one card for 15 to 20 seconds while the narrator moves on. Add a card or a diagram step on the words of a long stretch, rather than a drift that only moves pixels.

Every command in this file names `demo`. For your own video, change three things: the entry file, the composition id and the bundle folder. The silent route below shows all three.

#### A worked diagram that animates

A diagram here is SVG (shapes drawn by code) whose numbers come from the frame. This one draws a line, moves a dot along its tip, and lands a label when the line ends. The numbers are invented. It shows both `interpolate()` and `spring()`.

`src/LineDiagram.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/LineDiagram.tsx (70 lines).
```

Save this as `src/diagram-entry.tsx`:
```tsx
import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {LineDiagram} from './LineDiagram';
import {FPS} from './kit';

registerRoot(() => (
	<Composition id="diagram" component={LineDiagram} durationInFrames={180} fps={FPS} height={1080} width={1920} />
));
```

```bash
cd /path/to/my-video
npx remotion bundle src/diagram-entry.tsx --out-dir=build/diagram
rm -rf out/still out/sheets
mkdir -p out/still out/sheets
for f in 0 40 70 105 125 170; do
  npx remotion still build/diagram diagram "out/still/$(printf %06d $f).png" --frame=$f
done
ffmpeg -v error -y -pattern_type glob -i 'out/still/*.png' -vf "scale=640:-1,tile=3x2" out/sheets/%02d.png
```

Open the sheet. You should see: the title and a bare axis on frame 0; a line growing with a dot at its tip on frames 40 and 70; the whole line on frame 105; and "Four times over" beside the dot on frames 125 and 170. Rendered and looked at on a Mac, not on Linux.

To put it in a video, place it in a block. Inside a voice block, start it on a phrase, and it re-times with the voice: `<Sequence from={cue(n2, 'sign-ups climbed')}><LineDiagram /></Sequence>`. A `<Sequence>` resets the frame, so `DRAW_FROM` counts from the phrase. To draw your own, change `POINTS`. Add shapes the same way: a bar is a `<rect>` whose `height` comes from `interpolate()`.

#### A silent video

A silent video uses only cards, and its timing comes from reading time. A card can hold a sentence or a diagram. This was rendered and looked at (tested on a Mac, not on Linux):

Save this as `src/silent-entry.tsx`:
```tsx
import React from 'react';
import {AbsoluteFill, Composition, registerRoot, Sequence} from 'remotion';
import {FPS, layout, PAPER, Statement} from './kit';

const LINES = [
	'A video is a stack of still pictures.',
	'Thirty of them play every second.',
	'Change the plan, and every picture follows.',
];

// Reading time: at most 17 characters a second, plus a second to arrive.
const readFrames = (text: string) => Math.ceil((text.length / 17) * FPS) + FPS;

const L = layout(LINES.map((line) => ({kind: 'card' as const, frames: readFrames(line)})));

const Silent: React.FC = () => (
	<AbsoluteFill style={{background: PAPER}}>
		{LINES.map((line, i) => (
			<Sequence key={line} from={L.at[i]} durationInFrames={L.len[i]}>
				{/* centre: no captions sit below, so the text can use the middle of the frame. */}
				<Statement centre text={line} />
			</Sequence>
		))}
	</AbsoluteFill>
);

registerRoot(() => (
	<Composition id="silent" component={Silent} durationInFrames={L.duration} fps={FPS} height={1080} width={1920} />
));
```

The commands are the same as for the example, with three names changed:

```bash
cd /path/to/my-video
npx remotion compositions src/silent-entry.tsx
npx remotion bundle src/silent-entry.tsx --out-dir=build/silent
rm -rf out/still out/sheets
mkdir -p out/still out/sheets
for f in 30 130 240 330; do
  npx remotion still build/silent silent "out/still/$(printf %06d $f).png" --frame=$f
done
ffmpeg -v error -y -pattern_type glob -i 'out/still/*.png' -vf "scale=640:-1,tile=2x2" out/sheets/%02d.png
npx remotion render build/silent silent out/silent.mp4 --color-space=bt709 --image-format=png --crf=20 --offthreadvideo-cache-size-in-bytes=800000000
```

`compositions` prints `silent    30      1920x1080      366 (12.20 sec)`. That 366 includes `OUTRO` (see "Hit a set length" below). Pass `centre` to `Statement` on a silent card. Without it, the text sits above the middle of the frame, because its deep bottom padding leaves room for captions that are not there.

Without a voice, give each line time to be read. The helper above allows 17 characters a second, plus a second to arrive. A silent video can still have music: add `<Audio src={staticFile('music.mp3')} volume={0.3} />`, and check its licence first.

The finished file has no sound track at all, and that is right for a silent video. Some upload sites want a sound track anyway. `--enforce-audio-track` on the render adds a silent one. Tested on a Mac: it added an `aac` stream that measured silent (-91 dB).

#### Hit a set length

`layout` adds `OUTRO` (75 frames, 2.5 s) to the last block, so the end is not abrupt. So the blocks you write must add up to the length you want, minus `OUTRO`.

Example: the user asks for 15 seconds. At 30 frames a second that is 450 frames. Take off `OUTRO`, and your cards must add up to 375. In `src/silent-entry.tsx`, replace the `const L` line with this. Three cards of 140, 155 and 80 frames make 375, and the last one then runs 155 frames on screen.

```tsx
const FRAMES = [140, 155, 15 * FPS - OUTRO - 140 - 155]; // 15 s, with OUTRO taken off the last card
const L = layout(FRAMES.map((frames) => ({kind: 'card' as const, frames})));
```

Add `OUTRO` to the import from `./kit`, then check the length before anything else. `npx remotion compositions src/silent-entry.tsx` must end with `450 (15.00 sec)`. Tested on a Mac: it printed `silent    30      1920x1080      450 (15.00 sec)`, and the rendered file measured 15.000 s. Compare each card with `readFrames`, because a set length can leave a line too little time. If it does, cut words or cards, and do not make the text race.

A narrated video gets its length from the voice. To land near a length, plan the words first (about 2.4 a second at 144 words a minute), voice it, and read the length from `npx remotion compositions`. If it is long, cut words and re-voice. If it is a little short, add frames to the last voice block with `extra`: `{kind: 'voice', caps: n2, extra: 30}`. Do not speed up a voice past what sounds natural to hit a number. Ask the user which matters more.

### Step 10. If the video needs people

Use one of these public options. Ask the user which suits them.

- **Real footage.** Ask the user for a file, or find stock video. Check its licence and that the people in it agreed to be filmed for this use. Show it with `<OffthreadVideo>`.

- **Images or clips from an AI generator.** Decide this with the user first, because it costs money and has rules of its own: say the cost and get an OK, use no real person's likeness without permission, and do not rely on a generated person looking the same in two shots.


- **Lottie animation.** Lottie is a small JSON animation format, and many are available online. Check each file's licence. Install it at your exact Remotion version: `npm i --save-exact @remotion/lottie@$(node -p "require('./node_modules/remotion/package.json').version") lottie-web`. The small test file below is a moving dot, not a person. Swap in a real file. This was rendered with that test file (tested on a Mac, not on Linux):

Save this as `public/figure.json`:
```json
{"v":"5.7.4","fr":30,"ip":0,"op":60,"w":400,"h":400,"nm":"dot","ddd":0,"assets":[],"layers":[{"ddd":0,"ind":1,"ty":4,"nm":"dot","sr":1,"ks":{"o":{"a":0,"k":100},"r":{"a":0,"k":0},"p":{"a":1,"k":[{"t":0,"s":[100,200,0],"i":{"x":[0.5],"y":[1]},"o":{"x":[0.5],"y":[0]}},{"t":59,"s":[300,200,0]}]},"a":{"a":0,"k":[0,0,0]},"s":{"a":0,"k":[100,100,100]}},"ao":0,"shapes":[{"ty":"gr","it":[{"ty":"el","p":{"a":0,"k":[0,0]},"s":{"a":0,"k":[120,120]}},{"ty":"fl","c":{"a":0,"k":[0.76,0.25,0.05,1]},"o":{"a":0,"k":100},"r":1},{"ty":"tr","p":{"a":0,"k":[0,0]},"a":{"a":0,"k":[0,0]},"s":{"a":0,"k":[100,100]},"r":{"a":0,"k":0},"o":{"a":0,"k":100}}]}],"ip":0,"op":60,"st":0,"bm":0}]}
```

Save this as `src/lottie-entry.tsx`:
```tsx
import {Lottie, type LottieAnimationData} from '@remotion/lottie';
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, Composition, continueRender, delayRender, registerRoot, staticFile} from 'remotion';

const Figure: React.FC = () => {
	const [handle] = useState(() => delayRender('Loading the Lottie file'));
	const [data, setData] = useState<LottieAnimationData | null>(null);
	useEffect(() => {
		fetch(staticFile('figure.json'))
			.then((r) => r.json())
			.then((json) => {
				setData(json);
				continueRender(handle);
			})
			.catch((err) => cancelRender(err));
	}, [handle]);
	return (
		<AbsoluteFill style={{alignItems: 'center', background: '#FBF7EF', justifyContent: 'center'}}>
			{data ? <Lottie animationData={data} style={{height: 400, width: 400}} /> : null}
		</AbsoluteFill>
	);
};
registerRoot(() => <Composition id="figure" component={Figure} width={1920} height={1080} fps={30} durationInFrames={60} />);
```

- **Rive animation.** `@remotion/rive` exists for `.riv` files. Not tested here, as no test file was at hand.

Ask whether the video needs a person at all. If you could delete the person and still make the point, a diagram is usually clearer and cheaper.

### Step 11. Master the sound

Mastering means setting the finished video's overall loudness. Do it as a normal last step on the final render, because a render does not level the sound for you. Past renders landed around -24 to -28 LUFS (a measure of how loud sound feels), and viewers reach for the volume at that level. Skip it only for a silent video, or if the user has a reason.

Starting points, and a floor rather than a rule:

| Where it goes | Loudness | Highest peak |
|---|---|---|
| YouTube and short social clips | -14 LUFS | -1.5 dBTP (true peak, the highest the sound really reaches) |
| Podcasts, or when the platform is unknown | -16 LUFS | -1.5 dBTP |

```bash
cd /path/to/my-video
python3 master-audio.py out/demo.mp4 --target=-14 --peak=-1.5 --out=out/demo.mastered.mp4
```

The script measures the sound, applies one change for the whole film when it can, then measures the result. The picture is copied, not re-encoded. Tested on a Mac, not on Linux. On the stand-in tones it went from -17.4 to -14.0 LUFS with `mode: linear`, which means one change for the whole video. With the free voice it went from -20.4 to -14.0 LUFS at -1.5 dBTP with `mode: dynamic`, which means it had to ride the level, because a few moments were too loud for one change. Report the `after` row, not the target you asked for. Keep the render: if you change anything, render again and master again from the render, never from a master. Exit code 1 means it missed the target by more than 1 unit: read the numbers and fix the mix.

### Step 12. Hand it over

Check the file (see "How to check it worked"). Then give it to the user on a private page: a web page only they can open, where the video plays and saves as one file. Files go out this way whatever their size, because `SendUserFile` refuses files over 30 MiB. It uses the Artifact tool, published on claude.ai and private by default. Big files work too, and a very large job may use a second page. A page's store held 1 GiB when this was written, so a bigger film needs a second page holding the rest (not tested here). The Android app saves at most 200 MiB, and a phone may stall on a very large file.

**1. Split the finished file.** Each stored piece has a size cap, so the script makes pieces of 19 MiB.

```bash
cd /path/to/my-video
python3 split-for-artifact.py out/demo.mastered.mp4 out/demo-pieces
```

It writes `part-01.mp4` and so on, plus `pieces.json` with each piece's size and SHA-256 (a fingerprint of a file's bytes).

**2. Publish the empty page,** because the pieces need a page to live on. `delivery-page.html` was saved in Step 2, so it needs no typing. If the tool asks you to load its design or capability skills, do so. Keep this page's script and data blocks unchanged.

```
Artifact
  action: publish
  file_path: delivery-page.html
  icon: video
  capabilities: {"assets": {}, "downloads": true}
```

Keep the `url` in the result. The page's name comes from its `<title>` tag, so change that tag to the video's name if you like, in two to four words.

**3. Upload the pieces,** at most 25 in one call. The result gives one `url` per piece, such as `/_blob/7db260ac...`. Use it exactly as given.

```
Artifact
  action: publish
  url: <the page>
  asset: true
  file_paths: [out/demo-pieces/part-01.mp4, out/demo-pieces/part-02.mp4]
```

**4. Fill in the `video-data` block in the page, and publish the same file path again.** Change only the data, not the script. Do not pass `capabilities`; they carry forward. `size` and `sha256` come from `pieces.json`. The fields other than `title` and `videos` can be empty. The values below are invented.

```json
{
	"title": "How a video is made",
	"intro": "Your video. Press the button, watch it, and save it if you like it.",
	"meta": "0:21 · 1920×1080 · 30 fps",
	"videos": [
		{
			"label": "The full video",
			"filename": "how-a-video-is-made.mp4",
			"size": 800000,
			"pieces": [{"url": "/_blob/7db260ac...", "size": 800000, "sha256": "794caf1d..."}]
		}
	],
	"chapters": [],
	"description": "",
	"changes": [],
	"checks": ["I cannot hear. Does the voice sound right to you?"]
}
```

**5. Check the store.** `Artifact  action: list  scope: assets  url: <the page>` shows a SHA-256 for each piece. Compare each with `pieces.json`.

**6. Send the link.** For example: "Your video is ready: <link>. Open it in your browser and press **Get the video**. When it has loaded it will play right there, and **Save to my device** gives you one normal MP4 file."

The page is private. The user can share it from its **Share** menu. `split-for-artifact.py` was run on a Mac. This page was not published or pressed while this guide was written, so ask the user whether **Get the video** worked, and whether the video plays.

If the user wants a smaller file, make a smaller copy. This lowers quality, so do it only then, and step the `-crf` number up from 23 until it is small enough:

```bash
cd /path/to/my-video
ffmpeg -v error -y -i out/demo.mastered.mp4 -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart out/demo.small.mp4
```

Commit and push the source, not the video. Tell the user that the master file exists only in the session until they save it.

## How to talk to the user

- Use plain words. The user may be new to video. Say "the picture stays still for 6 seconds", not "a long hold".

- Ask one question at a time, with your recommendation. Example: "Should this have a voice? I recommend yes, because this topic has a lot to explain. I recommend a free computer voice, and I'll play you samples. You can also record it yourself or use a paid voice."

- Ask for their taste early: brand colours, fonts, a video they like, a video they dislike. Offer two or three directions as stills, and let them choose.

- Show stills before a long render. Pause for their OK at these points: the script, the first look, the voice, and the first whole video.

- Tell them what you could not check. You cannot hear the audio. Ask them to listen.

- Only a paid service needs a talk about money. Say what it costs before any paid step, and wait for a clear yes.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `Compositor exited with signal SIGKILL` | The machine ran out of memory, and the system killed the render. There is no swap to fall back on | Cap the frame cache with `--offthreadvideo-cache-size-in-bytes=800000000`, use `--concurrency=2`, and run it again. Nothing is lost. It can look odd afterwards, because `free -m` shows plenty of memory once the render is gone |
| `npm error could not determine executable to run` | You ran `npx remotion ...` before the install, or in the wrong folder | Run the install in Step 2, and `cd` to the project first |
| A font silently draws as a serif, though it loaded | A font name with a digit, such as `Baloo 2`, needs inner quotes | `fontFamily: "'Baloo 2'"`. Check with a still |
| `Could not find a tsconfig.json file in your project` | No `tsconfig.json` | Add the file from Step 2 |
| `CONNECT tunnel failed, response 403` or `Host not in allowlist` while getting Chrome | The proxy refuses `remotion.media` | Use the Google route in Step 2, or ask the user to allow the host |
| `Could not find composition with ID demo. Available compositions: ...` | Wrong entry file or id | Run `npx remotion compositions <entry>` |
| `cue: "..." is not in this voice block. It says: "..."` | The voice does not say that, or says it differently (`30` for `thirty`) | Use the words the error prints |
| `durationInFrames must be positive, but got -12` | A phrase matched earlier than you meant, so a block ends before it starts | Choose a phrase said once |
| `inputRange must contain only finite numbers, but got [0,Infinity]` | `Infinity` in `interpolate` | Use the real last frame |
| The screen shows ` ` | Escape in a plain JSX attribute | Write `text={'a b'}` |
| Text is in a serif font | The font was never loaded, with no error | Load it. See Step 5 |
| `Failed to load font "/public/fonts/nope.woff2": 404 Not Found` | Wrong font path | Check the file name in `public/fonts/` |
| An error with the words `exceeded rendering` and `Fetching Inter font` | Google Fonts cannot be reached at render time | Use font files |
| Any other error with the words `exceeded rendering`, on a busy machine | A frame took longer than the time limit | Pass `--timeout=120000` to start, and read the rest of the error |
| `Error loading image with src: http://localhost:3000/public/nope.png` | The file is not in `public/`, or the name is wrong | Fix the `staticFile` path |
| `Received a status code of 404 while downloading file http://localhost:3000/public/nope.mp4.` | The same, for video | Fix the path |
| A clip freezes on one picture, with no error | The clip ended before its `<Sequence>` did | Shorten the Sequence, or use a longer clip |
| A still looks right, but the whole video flickers | `Math.random`, a timer or CSS animation | Drive it from the frame |
| `Error creating WebGL context` or a blank WebGL scene | `angle` cannot run that scene here | Add `--gl=swangle` for that render, then scan for ghosts |
| A ghost image in the whole render only | `--gl=swangle` | Go back to `angle` if you can |
| `Filter not found` (`tile`) | You used Remotion's cut-down ffmpeg | Install the full one. See Step 2 |
| A sheet is missing frames, with no error | `-frames:v 1` with a grid too small | Leave out `-frames:v 1`, and name the output `%02d.png` |
| The video is 2.5 s longer than you planned | `layout` added `OUTRO` to the last block | See "Hit a set length" in Step 9 |
| `No model in ...` from `voice.py` | Setup was not run, or a container rebuild wiped the folder | Run `bash setup-voice.sh` again |
| `OUTSIDE the band` from `voice.py` | The pace missed `--target` by more than 8 words a minute. The files were still written | Decide if the pace is fine, or change `--speed` or the pauses |
| `Set ASR_HOME first` | A new shell lost the setting | Run the `export` line `tools/setup-transcription.sh` printed |
| `TS7016` and `TS7026` from `tsc` | The type packages are not installed | See "The render does not check types" in Step 8 |
| Commands stop working after a pause, or `node_modules` is gone | The container was rebuilt | Run `npm i` again. Get Chrome and ffmpeg again as in Step 2. Render from what you pushed |

## How to check it worked

1. Read the file's details. (Use `npx remotion ffprobe` if there is no `ffprobe`.)

   ```bash
   cd /path/to/my-video
   ffprobe -v error -show_entries stream=codec_name,codec_type,duration,r_frame_rate,pix_fmt -of compact out/demo.mp4
   ```

   For the example you should see `h264` with `yuv420p` and 20.8 s, and `aac`. For a silent video you should see one `stream` line only, for the picture. No sound stream is the right result there.

2. Measure the sound, if it has any. `master-audio.py` prints an `after` row: it should sit within 1 unit of your target.

3. Look at the whole video as a contact sheet:

   ```bash
   cd /path/to/my-video
   rm -rf out/contact
   mkdir -p out/contact
   ffmpeg -v error -y -i out/demo.mp4 -vf "fps=2,scale=460:-1,tile=8x6" out/contact/%02d.png
   ```

   This writes as many sheets as it needs. Black tiles at the end are spare cells of the grid, not a fault in the video.

4. Open each sheet and look with your own eyes. Check the fonts, the words, the line breaks, whether anything is cut off, and whether each picture matches the words under it. For the example, you should see: the title; a sentence; 30 tiles filling in; three boxes arriving one at a time as the narrator names them; the moving colour clip; and a last sentence.

5. A file check cannot tell you the video is good. A file can pass every number and still say the wrong thing. You also cannot hear. Ask the user to watch and listen before you call it done.

## Files

These are saved by the copy step in Step 2. Do not read them unless you need to change one, and do not retype them.

Save this as `setup-voice.sh`:
```bash
#!/usr/bin/env bash
# One-time setup for free local narration. Safe to run again: it skips what exists.
# Everything goes in $VOICE_HOME (default ~/voice-tools), outside your project.
set -euo pipefail

VOICE_HOME="${VOICE_HOME:-$HOME/voice-tools}"
KOKORO=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
SHERPA=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models

# Download to a temporary name first, so a broken download is never mistaken for a finished one.
get() { [ -f "$2" ] || { curl -sSfL --retry 4 --retry-delay 5 -o "$2.part" "$1" && mv "$2.part" "$2"; }; }

mkdir -p "$VOICE_HOME/kokoro" "$VOICE_HOME/whisper"
[ -x "$VOICE_HOME/venv/bin/python" ] || python3 -m venv "$VOICE_HOME/venv"
# voice.py calls two private functions of kokoro-onnx, so the version is pinned.
"$VOICE_HOME/venv/bin/pip" install -q kokoro-onnx==0.6.1 soundfile onnx numpy sherpa-onnx

cd "$VOICE_HOME/kokoro"
get "$KOKORO/kokoro-v1.0.onnx" kokoro-v1.0.onnx
get "$KOKORO/voices-v1.0.bin" voices-v1.0.bin

cd "$VOICE_HOME/whisper"
if [ ! -d sherpa-onnx-whisper-base.en ]; then
	get "$SHERPA/sherpa-onnx-whisper-base.en.tar.bz2" base.tar.bz2
	tar xjf base.tar.bz2
	rm base.tar.bz2
	# Keep the small int8 model. readback.py does not use the two big ones.
	rm -f sherpa-onnx-whisper-base.en/base.en-encoder.onnx sherpa-onnx-whisper-base.en/base.en-decoder.onnx
fi

echo "ready: $VOICE_HOME/venv/bin/python"
```

`voice.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/voice.py (259 lines).
```

`readback.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/readback.py (74 lines).
```

`tools/setup-transcription.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/tools/setup-transcription.sh (41 lines).
```

This one has a different job from a plain transcript. It takes any audio file and writes word captions, in the shape `kit.tsx` and `@remotion/captions` read.

`words-to-captions.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/words-to-captions.py (103 lines).
```

`master-audio.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/master-audio.py (114 lines).
```

`split-for-artifact.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/split-for-artifact.py (48 lines).
```

`delivery-page.html`, which the copy step puts in your folder:

```html
# In this skill's files folder: files/delivery-page.html (305 lines).
```
