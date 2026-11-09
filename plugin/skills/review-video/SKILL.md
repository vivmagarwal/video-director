---
name: review-video
description: Look at your own video like an editor, using contact sheets of stills, checks on the finished file, a ghost scan and a read-back of the words. Use it before you call any video done, and whenever a user asks you to check or review one.
---
# Review a video like an editor

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

**Read up to the heading `## Files`, and stop there.** Everything after that heading is scripts, which Step 1 saves for you.

## What this skill does

It helps you find what a viewer would notice before the viewer does. It gives you:

- a script that turns a Remotion composition into labelled contact sheets, one still every 3 seconds

- checks on the finished file: length, streams, loudness, dead air, black frames

- a way to scan for ghost images that stills cannot show

- a read-back: a machine transcribes the finished sound, and you compare it with the script

- a way to ask the user what you cannot judge, and to record what they said

The main idea is simple. Almost every defect worth fixing is found by looking at a frame beside the script. A script that passes all the numbers can still say the wrong thing. In one large batch of short films, an agent had looked at each of its own films, and a fresh reader with a fresh sheet and the script beside it still changed most of them.

## When to use it (and when not to)

Use it for every video before you hand it over, and again after any change to shared code, because a change in one shared part can break a video nobody looked at again.

It is not for checking a script before it is voiced, and it does not replace a person watching and listening. The scripts work on any MP4. The shot sheet needs the video's Remotion source.

## What you need before you start

| Need | How to check | If it is missing |
|---|---|---|
| The finished MP4 | `ls -la out/` | Render it, or review stills only |
| The script or the words that should be said | Ask the user or read the project | Review only the picture, and say so |
| Full ffmpeg | `ffmpeg -hide_banner -filters \| grep -E ' (tile\|ebur128\|silencedetect\|blackdetect\|freezedetect) '` shows five rows | Install below |
| ffprobe (reads a file's details) | `ffprobe -version`, or `npx remotion ffprobe -version` in a Remotion project | The check script falls back to `npx remotion ffprobe` |
| For the shot sheet: `remotion`, `@remotion/bundler` and `@remotion/renderer`, all the same version | `npx remotion versions` | Install below |
| For the read-back: Python 3 and about 800 MB of disk | `python3 --version` | Step 5 |

**Get a full ffmpeg.** `npx remotion ffmpeg` is a cut-down build with no `tile` filter. Try `sudo apt-get install -y ffmpeg`. If that is refused (an earlier cloud session saw `deb.debian.org` answer 403), use PyPI:

```bash
cd /path/to/your-project
python3 -m venv .tools
.tools/bin/pip install -q imageio-ffmpeg
mkdir -p .tools/bin
ln -sf "$(.tools/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .tools/bin/ffmpeg
export PATH="$PWD/.tools/bin:$PATH"
```

An earlier cloud session found that this Linux build has `fps`, `tile`, `select` and `volumedetect`, but no `drawtext`. The shot sheet then prints the frame order instead of labelling the tiles. Check `ebur128`, `silencedetect`, `blackdetect` and `freezedetect` with the command in the table. If one is missing, the check script's reading for it comes back empty, so say that part was not checked. There is no `ffprobe` in this build; use `npx remotion ffprobe`.

**Add the Node API to a Remotion project,** at the exact version of `remotion`. npm often brings these along with `@remotion/cli`, but do not count on it:

```bash
cd /path/to/your-project
V=$(node -p "require('./node_modules/remotion/package.json').version")
npm i --save-exact @remotion/bundler@$V @remotion/renderer@$V
```

**A project with no setup yet.** Run `npm i --save-exact remotion @remotion/cli @remotion/bundler @remotion/renderer react react-dom`, then make sure there is a `tsconfig.json`, or every command stops with `Could not find a tsconfig.json file in your project`. Then run `npx remotion browser ensure` for Chrome. If that download is refused with `CONNECT tunnel failed, response 403` or `Host not in allowlist`, get the same version from Google (a refusal reads like that, and any other status means the host answered). Use your project's full path in the `cd`:

```bash
cd /path/to/your-project
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

Pass that Chrome to the shot sheet: `--browser=$HOME/.cache/video-tools/chrome/current/chrome-headless-shell`. `npx remotion` commands find it through this config. If `remotion.config.ts` already exists, keep it and add only the lines it lacks. The comment in it names `setup-video.sh`, a script this guide does not use: the block above puts Chrome in the same place.

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

The same route, with the Mac build, was tested on a Mac. The Linux build was not tested.

**Licence, if you start a Remotion project.** Tell the user once: Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees. Other companies need a company licence. See `node_modules/remotion/LICENSE.md` or remotion.dev/license.

**In a cloud session** (a Linux x64 container, 4 cores, no GPU, when this was written), the Bash tool stops at 10 minutes. Run a long job in the background and wait on a file. `pgrep -f` matches its own command line, so use a pattern like `[r]emotion render`.

## Steps

### Step 1. Save the tools, then make shot sheets before the render

A `cd` may not carry over from one command to the next, so each block below starts with its own. Use your project's real full path in place of `/path/to/your-project`.

Copy this skill's files into the project. Files already there are kept, so your `remotion.config.ts` stays as it is. Do not retype long files.

```bash
cd /path/to/your-project
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/review-video"
cp -rn "$S/files/." . 2>/dev/null; test -e "remotion.config.ts" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

A contact sheet is one image holding many small frames. A shot sheet takes those frames from the source, so you see the video before you pay for a whole render.

`shot-sheet.mjs`, which the copy step puts in your folder:

```js
# In this skill's files folder: files/shot-sheet.mjs (149 lines).
```

```bash
cd /path/to/your-project
node shot-sheet.mjs src/demo-entry.tsx demo --every=3
```

It writes `out/sheets/demo-01.png` and so on, and prints the frames in reading order. By default each sheet holds 5 x 4 tiles, which is a minute of video at one still every 3 seconds.

Why this script and not `npx remotion still` in a loop: it opens one browser and reuses it. In an earlier project, at scale 0.5, this took about 1.5 s a still, against about 4 s from the command line. On an Apple Silicon Mac on 2026-11-09 it took 0.2 to 0.5 s a still. Tested on a Mac, not on Linux. That includes the frame list, the crop, a bad frame number, a missing `drawtext` and `drawtext` failing for lack of a font.

**The Node API does not read `remotion.config.ts`.** That is why the script passes `chromiumOptions: {gl: 'angle'}` itself. If your project needs something else for WebGL, pass `--gl=swangle`.

Open each sheet with your own eyes. Then:

- **Sample by structure too.** Evenly spaced frames can miss a whole shot. Add one frame inside every shot, and the last frame of anything that builds up: `--frames=40,150,310,520`.

- **Open anything surprising at full size.** A tile is about a third of the frame wide. Shrinking hides small text and can invent shapes that are not there. `npx remotion still <entry> <id> out/x.png --frame=310` gives you the full frame.

- **Run the silent test.** Crop away the captions (`--crop=960:440:0:0` at scale 0.5 keeps the part above a caption band in a 1920x1080 frame). For each tile, write one line saying what the picture alone says. If the answer is "some text", the shot is not designed yet.

- **Put the script beside the sheet.** For each tile, ask: does this picture match the words being said right now?

### Step 2. Know what to look for

These are what real reviews caught. Each passed every automatic check first.

| What was caught | How to catch it |
|---|---|
| A label under the wrong thing | Check every label against the thing it names |
| A missing line under a diagram | Compare the diagram with the script, line by line |
| Words that broke badly across lines | Read every line break, and keep the words together with a non-breaking space |
| A highlight that came before the narrator named it | Find the frame the word is said, and check the frame just before it |
| A message that appeared late | The same check, the other way round |
| A ghost image of a list item, only in the whole render | The ghost scan in step 4 |
| Names the script never gave (invented for a chat line or a contact) | Check every name against the script. Anyone else stays a role or initials |
| Cut-off text: a chart cutting off the months at its edge, a calendar losing two months | Read the edges of every frame, especially during a camera move |
| A picture whose mood contradicts the words | Read each picture next to the line it goes with |
| An empty frame right after a cut, which reads as a blink | Look at the first frame after every cut |
| A shared change that broke a video already reviewed | After any change to shared code, make all the sheets again |

Also check: the font is the one you asked for (a font that failed to load falls back to a serif with no error), text stays inside the safe area, and the first and last frames are worth seeing.

A fresh pair of eyes finds more. If you can start another agent, give it the sheet and the script but not your opinion, and ask what it thinks each frame shows. Treat what it says as a lead, and check it yourself.

### Step 3. Check the finished file

Save the check script, then run it on the render. Pass the expected length if you know it.

`check-video.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/check-video.sh (63 lines).
```

```bash
cd /path/to/your-project
bash check-video.sh out/demo.mp4 20.8
```

Tested on a Mac, not on Linux, on a good file and on files with planted defects. A planted 1 s black gap, a 4 s silent stretch, a missing sound track, a 6 s frozen ending and a length mismatch all showed up.

How to read it:

| Reading | What it means | What to do |
|---|---|---|
| Streams and length | Is there picture and sound, and does the length match | Render again if the length is wrong |
| Loudness, in LUFS (a measure of how loud it feels) | A render is not levelled for you. Past renders landed around -24 to -28 | Master it, as below. Starting points: -14 LUFS for YouTube and short social clips, -16 LUFS for podcasts or when the platform is unknown, peak -1.5 dBTP (true peak, the highest the sound really reaches). Ask where the video will go |
| True peak over about -1 | The sound may distort after a platform re-encodes it | Lower it |
| Silence over 1.5 s | A pause is fine. Long dead air at a surprising time is not | Compare the times with the script. The stretch before the first word and the outro are expected in a video with no music |
| `PROBLEM: black frames` | A flash, or a late scene | Open those frames. A fade at the very start or end can be fine |
| Picture stopped for over 4 s | The frame did not change | Look at it. `freeze_start` with no `freeze_duration` after it means it lasts to the end. A card held under speech can be right |

**Master the sound as a normal last step,** on the final render, unless the video is silent or the user has a reason to skip it. Mastering sets the overall loudness. It should happen once and last, then you read the numbers again. The picture is copied, not re-encoded.

```bash
cd /path/to/your-project
python3 master-audio.py out/demo.mp4 --target=-14 --peak=-1.5 --out=out/demo.mastered.mp4
bash check-video.sh out/demo.mastered.mp4
```

Tested on a Mac, not on Linux. On a free-voice video it went from -20.4 to -14.0 LUFS at -1.5 dBTP, with `mode: dynamic`. That mode means it had to ride the level, because a few moments were too loud for one change. `mode: linear` means one change for the whole video. Report the `after` row, not the target. If you change the video, render again and master from the render. Never master a master. Exit code 1 means it missed the target by more than 1 unit: read the numbers and fix the mix.

**Measure dead air on the picture, not on the captions.** Captions lighting up word by word can hide a picture that stopped long ago. Crop them off, and read the list. (Change the crop to your frame size.)

```bash
cd /path/to/your-project
ffmpeg -hide_banner -nostats -i out/demo.mp4 -vf "crop=1920:880:0:0,freezedetect=n=0.001:d=2" -an -f null - 2>&1 | grep -E 'freeze_(start|duration)' | sed 's/.*lavfi.freezedetect.//' | paste -sd' ' -
```

What numbers should you aim for? These are judgements, and they measure different things:

- Whole frame, short social video: no single stretch over about 4 s.

- Captions cropped off: a list of what finished early, about 1.5 s and up. Read it. It is not a pass or fail.

- A narrated teaching video: changing the picture every 6 to 9 s feels calm. Sitting on one card for 15 to 20 s while the narrator moves on does not.

**Do not let a number stand in for looking.** `freezedetect` cannot tell motion that means something from motion that does not. In an earlier test, a drifting background kept a finished title card "moving" for 4.5 s, and a similar frozen-picture check passed it. The contact sheet showed it at a glance.

### Step 4. Look at the finished file

A sheet from stills is not the finished file. Look at the real thing too:

```bash
cd /path/to/your-project
mkdir -p out/review
ffmpeg -v error -y -i out/demo.mp4 -vf "fps=2,scale=460:-1,tile=8x7" out/review/contact-%02d.png
```

This writes as many sheets as it needs: 8 x 7 tiles at 2 frames a second is 28 s a sheet. If you use `-frames:v 1` instead, keep columns x rows at least seconds x 2, or the ending is left out with no warning. Black tiles after the end are spare cells of the grid, not a fault. A run of nearly identical tiles is a shot with nothing to do.

**Scan for ghosts at several frames a second.** A ghost is a leftover image of something that should not be there. On a cloud container, `--gl=swangle` painted a ghost of a list's first item into the second item's slot for about 20 frames. Stills of those frames were clean, even at `--concurrency=1`. A still cannot catch this. Only the whole render shows it. So after any swangle render, take the moments when things arrive, and scan them:

```bash
cd /path/to/your-project
ffmpeg -v error -y -ss 12 -t 2 -i out/demo.mp4 -vf "fps=6,scale=480:-1,tile=4x3" -frames:v 1 out/review/ghost-12s.png
```

Do this across the first beats of each diagram or list. The command was tested, but a real ghost was not reproduced for this skill. If you find one, render with `angle` if the scene allows it.

### Step 5. Check the words: the read-back

Skip this step for a video with no speech.

**You cannot hear.** The container has no ears, and neither do you. A read-back is a stand-in: a speech model writes down what it hears, and you compare that with the script. This catches a missing line, a skipped word and many mispronunciations. For example (an invented one), a model may write "mortar" where the script says "motor", because that is how the voice said it. It does not tell you whether the voice sounds good.

Set it up once. The route is PyPI and GitHub, because an earlier cloud session found `huggingface.co` refused while those two worked. This setup also installs a free voice model, because the two share one folder, `~/voice-tools`. It took about 2 minutes on a Mac on 2026-11-09 and used about 790 MB of disk. A rebuilt container can wipe that folder, and then you run it again.

```bash
cd /path/to/your-project
bash setup-voice.sh
```

```bash
cd /path/to/your-project
cat public/demo/n1.txt public/demo/n2.txt > out/script.txt
~/voice-tools/venv/bin/python readback.py out/demo.mastered.mp4 out/script.txt
```

Join the script files in the order they are said. A real test on a free-voice video printed:

```
HEARD: A video is a stack of still pictures. Each second shows 30 of them. So a video has three parts. The plan, the pictures, and the sound. Here is a moving clip, played inside the picture.
MATCH: 97.2% of 36 script words
  script: thirty                         heard: 30
```

And for a script with a wrong number and a line that was never voiced:

```
MATCH: 88.6% of 43 script words
  script: forty                          heard: 30
  script: this line was never voiced at all heard: (nothing)
```

Tested on a Mac, not on Linux. This model handles English. Read each difference: "thirty" and "30" is harmless, a homophone is harmless, a missing line is not. If a real mishearing comes back, rephrase, or if the words must stay, fix how the voice says them. Run it on each voice file before building, and on the finished file too, as a mix can bury a word. Music over the voice may make it read worse (not measured), so a wrong word may be the music's fault. Listen, or ask.

Compare any quote with its source word for word. An agent revising a script once changed a quote and swapped words. A diff catches that. Reading does not.

### Step 6. Ask a person

What you cannot judge, ask. A person's ear is needed for: names and unusual words, how fast lines feel, whether a voice suits the video, how the music sits under the voice, and whether the sound and picture feel in sync.

Then record the answers. Keep a file next to the video, committed to git, so the next session knows what was decided.

```markdown
# Review notes: demo

## Round 1, 2026-11-09, rendered from commit abc1234
- Checked: 7 stills, the contact sheet, check-video.sh, the read-back.
- Not checked: how it sounds. I cannot hear.

### Found and fixed
- f405, 0:13: "The sound" box came 4 frames before the word. Moved it to the cue.

### Asked the user
- "Does the name at 0:42 sound right?" The user, 2026-11-09: "Say it with a long a." Re-voiced block 3.

### Left alone, and why
- f610, 0:20: the last card holds for 3 s. The user liked it as an ending.
```

Write down the user's own words and the date. Do not write "approved" unless they said so.

## How to talk to the user

- Use plain words. Say "the picture stays still for 6 seconds", not "a 6 s hold".

- Lead with what matters: what you found, what you fixed, and what you need from them.

- Ask one question at a time, with your recommendation and an exact place to look. For example: "At 0:42, the machine heard the name as a different name. Please listen from 0:40 to 0:45. Is that how it should sound? I recommend re-voicing that block if not, which takes a few minutes and costs nothing."

- Show the sheet, not a description of it. In a cloud session, send it with `SendUserFile` if it is under 30 MiB. Say which tile to look at, by frame and time.

- Say plainly what you did not check. "I looked at frames and measured the sound, but I cannot hear it" is the right sentence. Never say it sounds good.

- Pause for their OK before anything costly: a long re-render, a paid re-voice. Say what it costs.

- Ask for their taste when it is a matter of taste. A reviewer's rule is only a suggestion. What they want wins, and small defects may be fine with them. Ask rather than guess.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `Cannot find package '@remotion/bundler'` | The Node API (Remotion's functions, called from a script) is not installed | Install it at the same version |
| `Could not find composition with ID ...` | Wrong entry or id | Run `npx remotion compositions <entry>` |
| `These frames are not in "demo" (0 to 458): 500, 600` | The video is shorter than you thought, often after a re-voice | Pick frames inside that range |
| `Filter not found` | Remotion's cut-down ffmpeg | Install a full one |
| `This ffmpeg could not draw labels, so the tiles carry none` | No `drawtext`, or no font for it | Use the frame order the script prints |
| Stills are blank where WebGL should draw | The Node API uses what you pass, not your config | Pass `--gl=swangle` for that sheet |
| An error with the words `exceeded rendering` | A frame took longer than the time limit, often because other renders are running | Pass `--timeout=120000` to start, or wait for them, and read the rest of the error |
| The contact sheet stops before the end | The grid is too small with `-frames:v 1` | Use `contact-%02d.png` |
| `ffprobe: command not found` | The PyPI ffmpeg has no ffprobe | `check-video.sh` falls back on its own. Use `npx remotion ffprobe` elsewhere |
| Loudness prints nothing | This ffmpeg has no `ebur128` | Use `loudnorm=print_format=json` and read `input_i` |
| `No Whisper model at ...` from the read-back | Setup was not run, or a container rebuild wiped the folder | Run `bash setup-voice.sh` again |
| The read-back shows many differences near music | Music covers the voice | Run it on the voice files before the mix |
| `CONNECT tunnel failed, response 403` | The proxy refused a host | Ask the user to allow it in the session's cloud environment menu: Edit, then Network access |

## How to check it worked

The review is done when all of this is true:

1. You have opened each sheet of the finished video, with your own eyes, next to the script.

2. `check-video.sh` printed no unexplained `PROBLEM` line. Each one is fixed or written down with a reason.

3. The read-back has no unexplained difference.

4. You made the sheets after the last code change.

5. A person has listened, or you have told them they have not, and what you could not check.

6. The review notes hold what was found, what the user said and the date.

A file check cannot tell you the video is good. A passing file can still be a bad video. Your eyes and the user's ears decide.

## Files

These are saved by the copy step in Step 1. Do not read them unless you need to change one, and do not retype them.

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

`readback.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/readback.py (74 lines).
```

`master-audio.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/master-audio.py (114 lines).
```
