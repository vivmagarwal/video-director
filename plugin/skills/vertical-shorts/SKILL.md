---
name: vertical-shorts
description: Cut 9:16 and 4:5 shorts from a finished long film with Remotion and ffmpeg, chosen by phrase, laid out for phone screens, captioned, mastered and checked. Use it when a long talk, interview or workshop is finished and the user wants clips that send people back to it.
---

# Make vertical shorts from a long film

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

**Read up to the heading `## Files`, and stop there.** Everything after that heading is scripts, which Step 0 saves for you.

## What this skill does

A short is a vertical clip, usually under a minute, cut from a long recording. It makes one point. It opens on a line that makes sense to someone who has never seen the talk. It sends that person back to the long film.

This skill delivers each short twice: **9:16 at 1080×1920** (YouTube Shorts, Reels, TikTok) and **4:5 at 1080×1350** (feeds such as LinkedIn and X). The picture is a full-width panel at the top, and all the words sit on a band below it.

The numbers here come from past projects, and each number says which:

| past work | what it made |
|---|---|
| an 80-minute workshop | a batch of 14 shorts, all in one shape |
| two more workshops | 7 shorts each: crops per segment, text limits, colour range |
| one test | one 45 s short built seven ways and scored by one blind reviewer: timing, type, sound and safe-zone numbers |

**Layout beat everything else in that test.** Of the seven builds, the best scored 50 of 80 against 42 to 45 for the others. That is one reviewer on one short, so treat it as a lead. It won because every big word sat on a band below a full-width panel, and none touched the face. The example here is built that way.

## When to use it (and when not to)

Use it when a long cut already exists, or at least a clean recording and its transcript. Build shorts after the long cut is approved, so they carry its corrected words.

Do not use it for:

- a vertical video written from scratch with no long film behind it. The slate and phrase matching have nothing to work on
- a clip that needs the talk around it to make sense. That is not a short. Tell the user
- a horizontal teaser. Cut that from the long film

**A short needs one idea, a hook that stands alone, and one speaker at a time.** It may cut between two people (11 of the batch of 14 did), but every segment belongs to one speaker, and the picture and the name on screen follow them.

## What you need before you start

**A cloud session, as measured when this was written:** a Linux x64 container with 4 cores, about 15 GB of memory, no swap and no GPU. The Bash tool times out at 10 minutes, and a background command stops after 30 minutes, or after up to 2 hours if you start it with `timeout: 7200000`. Bare `sleep` is blocked. Files outside git can vanish in a container rebuild, so commit and push often.

**Everything below was run on an Apple Silicon Mac on 2026-11-09, not on Linux,** with Remotion 4.0.541 and 4.0.542, ffmpeg 7.1.1 and Python 3.10. No keys or paid services are needed.

**What you need from the long film:**

| you have | use it like this |
|---|---|
| its edit data, with corrected captions and the clip list | set `EDIT` in the slate. Hint times then read on the film's clock, and the short plays the clean working copy |
| a clean working copy and its word-timed transcript | set `TRANSCRIPT` in the slate. This is the example below |
| only the finished MP4 | transcribe it (below) and use it as the source. If it has captions burned in, keep them out of the panel by framing above them, or ask the user for the file from before captions |

The edit data is a JSON file with `fps`, `clips` (`section`, `from`, `dur`, `src`, in frames), `captions` (`text`, `startMs`, `endMs`, `who`, in film milliseconds) and `chapters` (`from`, `title`). Words in the teaser section are skipped, since the teaser repeats lines from the body.

**Check these:**

```bash
command -v ffmpeg ffprobe && ffmpeg -version | head -1
node --version; python3 --version; df -h .
for u in https://registry.npmjs.org/remotion https://remotion.media; do
  printf '%s  ' "$u"; curl -sS -L -o /dev/null -m 15 -w '%{http_code}\n' -r 0-100 "$u" 2>&1 | tail -1
done
```

A refusal reads `CONNECT tunnel failed, response 403` or `Host not in allowlist`. Any other status means the host answered. The user can allow a host in the session's cloud environment menu (Edit, then Network access).

**If ffmpeg is missing** and apt is refused, PyPI has a static build, and ffprobe comes from Remotion's package after Step 1. Remotion's own ffmpeg is cut down, so do not use it for this work.

```bash
python3 -m venv ~/ff && ~/ff/bin/pip install -q imageio-ffmpeg
ln -sf "$(~/ff/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" /usr/local/bin/ffmpeg
```

If `/usr/local/bin` is not writable, link it into any folder on your PATH. This link was made this way on a cloud container and not re-run for this page.

**If you need a transcript,** do this after Step 1. It uses no paid service: sherpa-onnx from PyPI, and Parakeet TDT 0.6B v2 (a speech model, English only, 633 MB on disk) from sherpa-onnx's GitHub releases. Hugging Face was refused on the cloud container measured.

```bash
cd /path/to/shorts
bash tools/setup-transcription.sh
```

It ends with a line such as `ready. Run this in each new shell: export ASR_HOME=/opt/asr`. `$ASR_HOME` is the folder that holds the speech tools and their models. A setting like this may not carry over to the next command, so start every command that uses it with that line. The commands here write `export ASR_HOME=$HOME/asr`. Use the path yours printed. If a download fails, the script stops with curl's error, and running it again skips what is already there.

```bash
cd /path/to/shorts
export ASR_HOME=$HOME/asr
ffmpeg -v error -y -i public/footage/main.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le out/raw16k.wav
$ASR_HOME/venv/bin/python tools/transcribe.py out/raw16k.wav edit/transcript.json
```

The scripts are `tools/setup-transcription.sh` and `tools/transcribe.py`, saved in Step 0 from [Files](#files).

Measured: 24 minutes in 121 s on the cloud container, and 53 seconds in 2 s on the Mac. Commit the transcript at once, because it took real work. Accents and names trip it, and it often skips ums and stutters, so ask the user for proper nouns, correct them in the JSON, and listen.

## Steps

### Step 0. Copy this skill's files

**Do not retype long files.** Make the project folder, then copy this skill's files into it. Files already there are kept, so running it again after a restart cannot overwrite your work.

**Every command block below starts with its own `cd`,** because a `cd` may not carry over to the next command. Put the full path of your project where it says `/path/to/shorts`.

```bash
mkdir -p /path/to/shorts
```

```bash
cd /path/to/shorts
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/vertical-shorts"
cp -rn "$S/files/." . 2>/dev/null; test -e "tsconfig.json" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

**If this project already had files in it,** this step keeps them. A leftover `src/Root.tsx`, for example from a test, means the project never loads your shorts, with no error. Check it:

```bash
cd /path/to/film
grep -c 'Short' src/Root.tsx
```

If that prints `0`, run `mv src/Root.tsx src/Root.old.tsx`, and then run this step again.

It saves every script, page and starter file in this guide, 17 in all.

### Step 1. Set up the Remotion project

**Tell the user this once, plainly:** Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees. Others need a company licence (see `node_modules/remotion/LICENSE.md` or remotion.dev/license).

All `@remotion/*` packages and `remotion` must be the exact same version.

```bash
cd /path/to/shorts
npm init -y >/dev/null
V=$(npm view remotion version); echo "Remotion $V"
npm i -E remotion@$V @remotion/cli@$V @fontsource/inter react react-dom
npx remotion browser ensure
mkdir -p raw public/footage public/sfx edit out/shorts
```

If the proxy refuses `remotion.media`, or you see `getaddrinfo ENOTFOUND remotion.media`, take the same Chrome version from Google. The `remotion.config.ts` below finds it there, so no flag is needed:

```bash
cd /path/to/shorts
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

That URL is the Linux form. On a Mac, Remotion's own download worked, and npm picks the Mac render helper by itself. This fallback was not run on Linux for this page.

If you installed ffmpeg from PyPI, ffprobe comes from Remotion's package, now that it is installed:

```bash
cd /path/to/shorts
ln -sf "$PWD/node_modules/@remotion/compositor-linux-x64-gnu/ffprobe" /usr/local/bin/ffprobe
```

Save this as `tsconfig.json`
```json
{"compilerOptions":{"target":"ES2022","module":"ES2022","moduleResolution":"bundler","jsx":"react-jsx","strict":true,"skipLibCheck":true,"esModuleInterop":true,"resolveJsonModule":true,"noEmit":true},"include":["src"]}
```

This config sets how Chrome draws (`angle` needs no GPU) and finds the Chrome the fallback above downloads. If `remotion.config.ts` already exists, keep it and add only the lines it lacks.

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

Save this as `src/index.ts`
```ts
import {registerRoot} from 'remotion';
import {Root} from './Root';

registerRoot(Root);
```

The composition draws one short from its data, at either size. Its colours and type are examples: use the user's own, and ask for samples.

The file is `src/Root.tsx`, saved in Step 0 from [Files](#files). The file is `src/Short.tsx`, saved in Step 0 from [Files](#files).

Keep media out of git. GitHub refuses a file over 100 MB.

Save this as `.gitignore`
```text
node_modules/
out/
raw/
public/footage/
*.wav
```

### Step 2. Try it on a practice take

This takes a few minutes and proves the machine works, with no footage and no speech model. The "voice" is tone bursts, and the picture shows its own running clock. Use a real clip as soon as you have one.

Save this as `edit/slate.py`
```python
# The slate: one entry per short. Anchor on words, never on timestamps.
# This slate fits the practice take from tools/make-sample.py. Replace it for a real film.
# Run: python3 tools/build-short.py edit/slate.py
FPS = 30  # the source's own rate
SOURCE = "footage/main.mp4"  # under public/
RAW_WIDTH = 1280  # the original recording's width, for the upscale check
EDIT = None  # the long cut's edit.json if you have one (its corrected words). Otherwise:
TRANSCRIPT = "edit/transcript.json"  # words on the source's clock
CHAPTERS = []  # (time, title) if there is no edit.json: a segment may not cross one

SHORTS = [
    {
        "id": "s01", "title": "Never lose a word", "kind": "practical move",
        "profile": "organic",  # "ad" if it may be boosted, "organic" if not
        "hook": ["A CUT MUST", "KEEP THIS"],  # at most 6 words across two lines
        "hits": ["cut", "word", "trust", "remember"],  # marked in the captions
        "view": {"cx": 640, "cy": 360, "w": 620},  # the picture window, in source pixels
        "segments": [  # a start phrase, an end phrase, and a hint time for repeats
            {"hint": "0:24", "start": "A cut must never", "end": "lose a word."},
            {"hint": "0:15", "start": "Three things matter", "end": "sound you can trust."},
            {"hint": "0:32", "start": "That idea is", "end": "to remember."},
        ],
        "drops": [],  # {"hint": "0:36", "phrase": "a than"} removes a stumble inside a segment
        "plate": {"at": "A cut must never", "name": "The speaker", "role": "Exact wording from the user", "dur_s": 2.5},
        "slides": [
            {"at": "a steady picture", "kicker": "Three things", "title": "What matters", "lines": ["Clear words", "A steady picture"], "dur_s": 2.2},
        ],
        "pops": [
            {"at": "lose a word.", "text": "A WORD"},
            {"at": "Three things", "text": "THREE"},
            {"at": "to remember.", "text": "REMEMBER"},
        ],
        "sfx": [{"at": "Three things", "src": "sfx/pop.wav", "volume": 0.25}],
        "cta": {"line": "Watch the whole talk", "sub": "Link under this video"},  # never invent a link
    },
]
```

The script is `tools/make-sample.py`, saved in Step 0 from [Files](#files). The script is `tools/build-short.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/shorts
python3 tools/make-sample.py
ffmpeg -v error -y -i raw/take.mp4 -c:v libx264 -preset veryfast -crf 17 -g 30 -keyint_min 30 -sc_threshold 0 \
  -pix_fmt yuv420p -c:a copy -movflags +faststart public/footage/main.mp4
ffmpeg -v error -y -f lavfi -i "sine=f=880:d=0.12:r=48000" -af "afade=t=out:st=0.02:d=0.1" public/sfx/pop.wav
python3 tools/build-short.py edit/slate.py
npx remotion still src/index.ts s01-9x16 out/test.png --frame=100
```

The build should print this, then two WARN lines, because the practice short is so short:

```text
s01: 10.7 s, 6 pieces, 28 words, 12 caption pages, 1 slides, 3 pops, 1 sounds, longest gap 1.8 s, profile organic
```

Open `out/test.png` and look at it.

A working copy has a keyframe (a complete picture the video can jump to) every second. Raw webcam files often have one every 30 s, and the renderer then seeks for every frame it draws. Keep `-g` and `-keyint_min` equal to the frame rate. Do not put raw files in `public/`: a bundle copies all of it.

### Step 3. Choose moments by phrase

Plan the shorts in the same reading pass as the long cut, if you can: while you read the whole transcript for the teaser and chapters, mark the candidates. Good candidates are the lines someone would screenshot or send.

**What makes a good one:**

- **One idea.** A chapter turn is where the talk changes subject, so a short never crosses one.
- **A hook that stands alone, spoken in the first three seconds.** Pick a line that is contrarian **and answered in the short**. A hook the short does not pay off feels like a trick.
- **A balanced slate.** The batch of 14 was five myth-busters, five practical moves, two mindset pieces, one story and one closing anthem. Their segments ran 24 to 56 s before tightening.

**The plan is a slate:** data, one entry per short. Each holds an id, a title, a kind, the two-line hook, the words to mark, and its segments. **A segment is a start phrase, an end phrase and a hint time.** Here is one in plain form, invented for this example:

```text
S01  myth-buster   hook "PLANS LIE. / HERE IS WHY."
     sam  ~6:21  "Every plan I have seen" … "and nobody says so"
     sam  ~6:34  "The date comes first" … "the work comes last"
     drop ~6:36  "and and"
```

- **Anchor on words, never on timestamps.** A timestamp moves every time the long cut is re-cut. A phrase does not. The hint only chooses between repeats (the nearest wins). Hints read on the long film's clock with `EDIT`, and on the source's clock with `TRANSCRIPT`.
- **A phrase that is not found, or found twice with no hint, stops the build.** A silent miss is a caption out of sync.
- **Drops** remove a stumble or an aside inside a segment, anchored the same way.
- **Shorts may overlap.** The build lists overlaps, so no line is a hook twice by accident.

**Fill in the slate, then run the slate checks before you cut anything.** They cost only the reading of a list. On the batch of 14 they caught a broken cut-in, a segment ending on a dangling "she", two mid-sentence endings and four garbled spans to drop.

```bash
cd /path/to/shorts
python3 tools/build-short.py edit/slate.py
```

| check | fails when |
|---|---|
| `one-speaker` | a word in a segment is not its named speaker's (when words have speakers, and the segment sets `who`) |
| `chapter` | a segment crosses a chapter turn |
| `clean-start` | the word before lacks `.` `?` `!` and the gap before it is under 0.4 s |
| `clean-end` | the last word ends no sentence and the segment does not set `"fade": true` |
| `hook-length` | over 6 words across the hook's two lines |
| `stumble` | a word repeats at once in kept text ("the the"): add a drop, or check by ear |

**A planned exception is fine.** `--force` writes the data anyway, and you tell the user what you passed over.

**Then listen to every first word.** The first word is the hook. A keep that started 0.16 s late opened one film on half a word, and one short may have lost a spoken "How" because the recogniser never transcribed it. Compare the sound around each start:

```bash
cd /path/to/shorts
ffmpeg -hide_banner -ss <start - 1> -t 2 -i public/footage/main.mp4 -af silencedetect=n=-38dB:d=0.1 -f null - 2>&1 | grep silence_
```

Sound that begins before the first word's time is either a word the recogniser missed or a breath. Have both you and the user check it.

**Show the user the slate before you cut.**

### Step 4. The shape of a short

This shape comes from the batch of 14, with timing from the test. **It is a starting point.** Ask the user, and use their own references.

| when | what | rule |
|---|---|---|
| frame 0 | **the poster**: a face and the hook, composed like a thumbnail | the feed shows frame 0 before play, so no fade from black. Key words at least 80 to 100 px |
| 0 s | speech starts under the poster | the first sentence by 3 s. The test's short finished its first sentence by 1.66 s |
| by frame 12 | motion starts | the poster held about 0.4 s |
| 0 to 4.5 s | the hook window | no full-frame device |
| early | a name plate | at least 80 % of the words in its window are that person's. Ask for the exact name and title |
| between | at least 2 slides | each carries content. One that only decorates does not count |
| throughout | something designed changes every 2 to 4 s | the test allowed a longest gap of 4 s. A talking head always moves, so a motion detector cannot prove this: count the events in the data |
| throughout | 3 to 6 pops and 4 to 8 sound effects per 45 s | a pop is one to three big words that jump in quickly and leave within a second. The numbers are in `Pop` in `src/Short.tsx` |
| after end - 0.8 s | nothing full-frame | the closing needs the room |
| the end | the call to action, then the hook again | frame 0's hook fades in over the last 3 frames, so the last frame hands straight back to the first when it loops |

**Length.** Aim at about 45 s as a starting point, and cut a 30 s version when a short can stand it. YouTube Help says a Short can run up to three minutes with a square or vertical shape (read on 2026-11-09), so under a minute is a craft choice, not a limit there.

**Captions never carry a link.** Links live in the closing and in the description. Keep the logo off frame 0 unless the user asks.

### Step 5. Reframe the footage

Most recordings are wide, and the frame is tall. The source limits the design more than any platform tip does.

**The view in the slate says what the panel shows:** `{"cx": 640, "cy": 360, "w": 620}` means a window 620 source pixels wide, centred on that point. The panel's height then decides the window's height, for both exports. Find the face with your eyes: take a frame and read the coordinates.

```bash
cd /path/to/shorts
ffmpeg -v error -y -ss <a moment> -i public/footage/main.mp4 -frames:v 1 out/frame.png
```

- **Do not go full-bleed on a low-resolution source.** A full-bleed 9:16 crop of 640×360 was 202×360, a 5.35× enlargement. It could not hold the face in 34 of 158 clips, and its captions landed on the mouth. The test settled on a panel 1080×1200 at the top (3.33× at zoom 1.00), under a limit of about 3.8×. The `upscale` check uses `RAW_WIDTH` and your view for this. Upload at 1080 anyway, and hide a weak source with layout, not more zoom.
- **Nothing covers the face.** No caption plate over the face box extended 15 % below the chin, in any frame. Anything else covers it for at most 0.3 s. A word stamped on the eyes, a pop grazing the chin, and a re-crop that cut the face at the eyes were all caught on sheets.
- **Punch-ins must be seen.** A step of at least 10 to 12 % reads as a choice. 1.10 back to 1.00 was too small and became 1.12. The build alternates 1.00 and 1.12 at each cut (`"punch"` in the slate). On a 360p source keep every punch at or under 1.15.
- **A speaker moves between segments:** give a short its own `"view"`, or make a short per speaker. The build uses one view per short. For several views in one short, extend `build()` to read a view from the segment and `Picture` to read it from the clip.
- **A meeting's gallery re-grids** when a camera turns on or off. One speaker's tile moved 320 px between two layouts of one session. Measure the layout over the whole file, and give every segment its own crop. Crop the burned-in name label out: a tile crop 328 px tall cleared it, and 336 px left 6 px of the label.
- **The active-speaker feed** has a sharper face than a gallery tile, and may carry a one-speaker segment, but only after every second is matched against that second's gallery tiles. In one workshop it showed the right person 94 % of the time. A crosstalk segment stays on the tiles.
- **Grade per speaker when the light changes.** A speaker whose light faded over a long session became a silhouette in the late chapters. Grade with ffmpeg when you make the working copy: a WebGL effect needs the slow `--gl=swangle` backend in a cloud container (measured 4.6 times slower).

### Step 6. Safe zones

Platforms draw their own buttons and text over the video. These are the areas text may occupy on a 1080×1920 frame. **They are starting points and they change.** The three platform rows were measured pixel by pixel from each platform's official ad template in September 2026. Check the current ones before a big batch.

| profile | text stays inside | where it comes from |
|---|---|---|
| YouTube Shorts | x 48 to 888, y 288 to 1248 | Google's overlay template |
| TikTok In-Feed | x 120 to 960, y 240 to 1260, but not x 780 to 960 where y is 840 to 1260 (the button stack) | TikTok Ads Manager's file, April 2025 |
| Instagram and Facebook Reels | x 65 to 1015, y 269 to 1248 | Meta's Ads Guide |
| **ad** | x 120 to 888, y 288 to 1248, and x at most 780 where y is over 840 | all three at once. Use it for anything that may be boosted as a paid ad |
| **organic** | x 60 to 888, y 240 to 1490 | a working choice from past videos, for posts that are not boosted. Not from a platform's file. y of 240 or more also keeps text inside Instagram's 3:4 grid crop |

**Set `"profile"` on every short, and record it in your delivery notes.** They differ most at the bottom: captions end by y 1248 in `ad` and by y 1490 in `organic`. The composition's `PROFILES` uses x 120 to 780 for `ad`, because its whole text band sits below y 840.

**4:5.** The example registers the same data at 1080×1350, and keeps the band a centre crop of the 9:16 would (y 285 to 1635). The feeds' own overlays at 4:5 were not measured. A 78 px full-frame line once overflowed only in the 4:5 and was caught only on its sheet, so **sheet both exports**.

### Step 7. Sound

**Tighten again.** The long cut kept the talk's rhythm, and a short does not. The build compresses every pause over 0.30 s to about 0.14 s of silence (0.18 s after `.` `?` `!`), starting about 0.05 s before the next word and never ending sooner than 0.12 s after a word. A 46 s test short took 20 cuts. Tell the user this is much tighter than a long film.

**A crossfade on every splice.** A hard join can click. This writes the short's sound as one file, with a 15 ms equal-power crossfade centred on each splice:

The script is `tools/short-voice.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/shorts
python3 tools/short-voice.py public/footage/main.mp4 s01 public/footage/s01-voice.wav
```

Then set `"voice": "footage/s01-voice.wav"` on the short, and run the build again. The composition plays that file and mutes the footage. Run the voice script again after any change to the cut.

- **Natural speed,** unless the user asks. Reach the pace by trimming pauses. At 1.2×, a 46 s short runs about 38 s.
- **Sound effects** sit 6 to 12 dB under the voice, lead the picture they belong to by a frame, and never land on the hook's first words. The sample uses a generated tone. Use the user's own files or a library they can use. Set each in `"sfx"`.
- **A music bed is optional.** About 15 LU (a difference in loudness; 1 LU is 1 dB) under the voice, in a range of 12 to 18, ducked under speech, and nearly silent from 0.3 s before the key question. Try it with and without. The example has none: add one `<Audio>` with a low `volume` to `Short`, and measure it.
- **Some viewers watch muted, and some listen.** A short must work both ways. Caption everything, and design the sound.

### Step 8. Captions in shorts

The build makes pages of 2 or 3 words, at most 20 characters, each on screen at least 0.5 s, with the spoken word lit. The example uses 80 px.

- **Every clip has an integer frame length, and every word maps through that one list.** So timing cannot build up an error from piece to piece.
- **Fix mishearings in the words before the build.** With `EDIT` you inherit the long cut's corrections. Keep the speaker's own wording.
- **Over a bright wall, use an opaque plate.** Text straight on a graded white wall failed badly (white at 1.21:1). The test used an opaque dark plate, #111827, with white text at 17.7:1. Keep any accent colour on the plate at 4.5:1 or more. Check contrast for the user's own colours.
- **A word on a line:** 40 px is the floor for anything that carries the message in a portrait frame. A big-type line holds about 18 characters at 80 px or more, so write a long one as 2 to 4 lines.
- **A name plate:** one past design clipped at about 16 characters of name and 24 of title, so use first names, and measure on a still with the real names.

### Step 9. Test on a phone view

A phone shows a 1080-wide frame about 360 to 400 points wide. Text that reads on your monitor may not read there. Do three things.

**1. Draw the safe zone on real frames.** The red area is outside the profile. Nothing that matters may sit in it, except the picture. Bundle first, then render a few frames with `guides` on:

```bash
cd /path/to/shorts
npx remotion bundle src/index.ts --out-dir=out/bundle --log=error
for f in 0 70 200 400; do
  npx remotion still out/bundle s01-9x16 out/g-$f.png --frame=$f --props='{"guides":true}' --log=error
done
```

In the `ad` profile the panel is shorter, so the face can sit above the top line, in the zone the platform's own controls may use. The rule is about text, but look at it. If the source has headroom, a lower `cy` moves the face down.

**2. View them at phone size.** Scale each frame down to 360 px wide and read every word with your own eyes. If a word is hard to read here, it is too small:

```bash
cd /path/to/shorts
ffmpeg -v error -y -i out/g-0.png -i out/g-70.png -i out/g-200.png -i out/g-400.png -filter_complex \
  "[0]scale=360:-1[a];[1]scale=360:-1[b];[2]scale=360:-1[c];[3]scale=360:-1[d];[a][b][c][d]hstack=4" out/phone.png
```

**3. Ask the user to watch it on a real phone,** with sound on and then muted. In a cloud session, a quick test file up to 30 MiB can go as a chat file card with `SendUserFile`. A 19 s short came to about 5 MB at the settings below, so a 45 s one should fit. You cannot judge feel, so ask: "Does the first line make you want the second?"

### Step 10. Render, master and check both exports

Fix the colour in the render. Without the flags below, a render on Remotion 4.0.541 measured BT.601 colour (an older standard) with no matrix tag, so players guess, and in one test a matrix mismatch dropped a colour's contrast from 4.74:1 to 3.94:1. Mastering copies the picture, so it cannot fix colour later.

**Colour tags.** A video file carries labels that tell players how to show its colours. Check that all four are there. On Remotion 4.0.541 on a Mac, a render with `--color-space=bt709 --image-format=png` had all four. On an older Remotion on Linux, only the matrix tag was there. This is not yet measured on Linux at 4.0.541. So check with ffprobe, and if a tag is missing, write it without re-encoding. The tagging line below does that, and does no harm to a file that already has them.

Mastering is a normal last step. Renderers do not set loudness for you, and a quiet short stays quiet. Starting points, as a floor: -14 LUFS for YouTube and short social clips, -16 LUFS for podcasts or when the platform is unknown, peak -1.5 dBTP. Use what the user or the platform asks for.

The script is `tools/master-audio.py`, saved in Step 0 from [Files](#files). The script is `tools/check-delivery.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/shorts
python3 tools/check-delivery.py selftest   # once on a new machine: it plants each defect and proves each check
for x in 9x16 4x5; do
  npx remotion render out/bundle s01-$x out/shorts/s01-$x.untagged.mp4 --color-space=bt709 --image-format=png --crf=20 --concurrency=2 --offthreadvideo-cache-size-in-bytes=800000000
  ffmpeg -v error -y -i out/shorts/s01-$x.untagged.mp4 -c copy \
    -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1 \
    -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -movflags +faststart out/shorts/s01-$x.mp4
  python3 tools/master-audio.py out/shorts/s01-$x.mp4 --target=-14
  python3 tools/check-delivery.py out/shorts/s01-$x.mastered.mp4 --fps=30
done
```

**Delivery numbers:**

| | value | why |
|---|---|---|
| frame rate | the source's own (25 for the workshop footage) | so no frame repeats |
| loudness | -14 LUFS (a unit of how loud a film sounds), peak -1.5 dBTP (how high the loudest moment reaches) | a starting point for short social clips. TikTok's and Meta's own targets were not checked |
| peak | -1.5 is a request, not a limiter | asked for -1, one file landed at -0.1 dBTP. If the script prints a note, or the check fails on the peak, master again from the render with `--peak=-2.5` |
| picture | H.264, `yuv420p`, limited range, BT.709 | the check fails anything else |
| sound | AAC, 48 kHz | the same |

Measured on a 19-second short from a real clip, on the Mac: each export rendered in about 27 s at concurrency 3. The master on a 16-second short read -14.3 LUFS and -1.5 dBTP, and its files were 2.1 to 2.7 MB. A quiet speaker is the trap: one short came out as low as -18.4 LUFS from a one-pass loudness tool, so level the voices before you cut when speakers differ.

**Are the captions still on the voice?** Transcribe the finished short and read each piece's median offset:

```bash
cd /path/to/shorts
export ASR_HOME=$HOME/asr
ffmpeg -v error -y -i out/shorts/s01-9x16.mastered.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le out/final.wav
$ASR_HOME/venv/bin/python tools/transcribe.py out/final.wav out/final.json
python3 tools/build-short.py sync s01 out/final.json
```

Each piece must be within 120 ms. A limit of 250 ms let audio moved 300 ms late pass. **Read a piece's median, not the slope.** One check flagged two 50 s shorts as drifting at -140 and -185 ms a minute, when each piece carried a constant offset of 100 ms or less. On one test short, pieces of several words read within 100 ms, and a one-word piece read +133 ms. Check a one-word piece by ear before you move anything.

### Step 11. Look before it ships

Stills show layout, never sound. On every short:

```bash
cd /path/to/shorts
for x in 9x16 4x5; do ffmpeg -v error -y -i out/shorts/s01-$x.mastered.mp4 -vf "fps=1/2,scale=216:-1,tile=10x3" -frames:v 1 out/sheet-$x.png; done
```

- a contact sheet of **both** exports
- frame 0 at thumbnail size, since it is the poster
- one frame inside every slide. In one batch a fade computed on the wrong timeline hid every slide after about 4 s
- each cut at -2, 0 and +2 frames
- the name plate, with the named person on screen

**Read the links in the data.** A slate's defaults once went unread, and every short fell back to a placeholder link. It was caught only because one data file was printed and read. Print one short and read every URL and name in it:

```bash
cd /path/to/shorts
python3 -c "import json; d=json.load(open('src/shorts.json'))[0]; print(d['cta'], d['plate'], d['hook'])"
```

### Step 12. Post copy, and what the user does by hand

Write the post text per short, and check it against each cap. These caps were noted in 2026 and not re-checked, so check them:

| platform | cap (characters) |
|---|---|
| YouTube Shorts title | 100, with `#shorts` inside it |
| X | 200 (one publishing tool's own cap, not X's) |
| Pinterest | title 100, description 500; a video pin needs a cover image |
| Instagram | 2,200 |
| LinkedIn | 3,000 |

One style that worked: the hook as the first line, contractions, no em dashes, and a close on a question. **Never invent a link.** Ask the user whether links go in post text or only on the closing frame.

**The user does these by hand. You have no credentials, and no upload tool:**

1. Upload the 9:16 to YouTube Shorts, Reels and TikTok, and the 4:5 to LinkedIn and X. The 4:5 can also go to Instagram and Pinterest.
2. On YouTube, set the long film as the short's Related video.
3. Choose visibility, and when each one goes out.

### Step 13. Hand the files to the user

**On the user's own machine,** give the paths. **In a cloud session,** send them through the private page in [Appendix: the delivery page](#appendix-the-delivery-page).

**Commit and push** the slate, `src/shorts.json`, the transcript and the tools, by path, in one command. Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs. Run `git status` after: a commit hook may reformat files you did not touch, and you restore only files that were clean before it.

## How to talk to the user

Use plain words. Ask one question at a time, with your recommendation.

**Before the first batch, ask, one at a time:**

1. "Might any of these be boosted as paid ads?" If yes or unsure, recommend `ad`, the stricter safe zone.
2. "Natural speed, or a little faster?" Recommend natural speed.
3. "How exactly should each person's name and title read?" Never guess.
4. "Where should the short send people, and what is the exact link?"
5. "Logo on the first frame?" Recommend none.
6. "Music, or voice only?" Recommend voice only for the first one, then compare.
7. "Do you have colours, fonts, or a short you love?" Invite their taste and references. The look here is a placeholder.

**Pause for their OK at these points:**

- the slate, before any cut
- the first finished short, before a batch. Get approval on one, then render the rest
- the finished files, before anything is posted

Show them the phone-size sheet and the file. Say what you checked by eye and by script, and that you cannot hear it.

## What goes wrong and how to fix it

| what you see | why | fix |
|---|---|---|
| `Compositor exited with signal SIGKILL` | The machine ran out of memory, and the system killed the render. There is no swap to fall back on | Cap the frame cache with `--offthreadvideo-cache-size-in-bytes=800000000`, use `--concurrency=2`, and run it again. Nothing is lost. It can look odd afterwards, because `free -m` shows plenty of memory once the render is gone |
| `Could not find a tsconfig.json file in your project` | the project has none | add the `tsconfig.json` from Step 1 |
| `Module not found: Error: Can't resolve './shorts.json'` | the slate has not built, or it failed its checks | run the build and fix what it names. The first bundle needs `src/shorts.json` |
| `phrase not found` | words differ, or a typo | read the transcript around the hint. Punctuation and case are ignored |
| `found 2 times ... add a hint` | the line repeats | add `"hint": "m:ss"` |
| `clean-start` or `clean-end` fails | a cut mid-sentence | move the phrase, or set `"fade": true` for a planned ending, or use `--force` and tell the user |
| `gap` fails | over 4 s with nothing new | add a pop or slide, or cut the segment |
| `hook-window` fails | a slide starts in the first 4.5 s | anchor it on a later phrase |
| Words over the face | the view leaves the face too low, or a device was moved | change `cy` and `w`. Keep text on the band |
| A big word overflows the 4:5 | long text at a fixed size | shorten it. The example scales pops and hooks to fit, and slides need short lines. Check the 4:5 sheet |
| `CONNECT tunnel failed, response 403` | the proxy refuses the host | test with curl; the user can allow it (Edit, then Network access) |
| A serif font | the font did not load | check the `@fontsource/inter` imports at the top of `src/Short.tsx` and the `fontFamily` line. `@remotion/google-fonts` is another option, and it needs Google's font host at render time |
| `Your macOS version is older than macOS 15 (Sequoia). Some features such as rendering may not work.` | a warning, not a stop | rendering was fine on macOS 14 |
| `Set ASR_HOME first.` | the shell lost the setting | start the command with the `export ASR_HOME=` line the setup script printed |
| `RuntimeError: Load model from .../encoder.int8.onnx failed` and `File doesn't exist` | the speech model is not on disk | run `bash tools/setup-transcription.sh` again. It stops with curl's error if a download fails, and GitHub has answered 504 for a while on one test, so try again later |
| `check-delivery` FAILS `codec` | rendered without the colour flags | render again with `--color-space=bt709 --image-format=png` |
| `check-delivery` WARNS `codec`, primaries unset | a tag is missing | run the tagging line in Step 10, then master again from that file |
| `check-delivery` FAILS `cfr`, `declares 30/1, want 25` | the wrong `--fps` | use the composition's rate from `npx remotion compositions src/index.ts` |
| `check-delivery` FAILS `loudness` | a quiet mix, or a peak too high | read the numbers, master again from the render, with `--peak=-2.5` if the peak is high |
| A file card is refused: `exceeds the 30 MiB upload limit` | too big for chat | use the private page in the Appendix. Lower the quality only if the user wants a smaller file |
| `moov atom not found` on a still | a bundle copied a file ffmpeg was still writing | wait until `pgrep -x ffmpeg` prints nothing, then bundle again |

## How to check it worked

- `python3 tools/build-short.py edit/slate.py` exits 0, and you read every WARN.
- `python3 tools/build-short.py sync <id> out/final.json` exits 0.
- `python3 tools/check-delivery.py <file> --fps=<rate>` ends with `ready to deliver` for **both** exports.
- You looked with your own eyes: the phone view with guides on, frame 0, one frame in every slide, and the sheets of both exports. A file check cannot tell you the video is good.
- The user watched one on a real phone, with sound on and muted.
- `git status` is clean, and the slate, `src/shorts.json`, the transcript and the tools are pushed. Only what is pushed is sure to survive a container rebuild.

## Appendix: the delivery page

Files go out through a private page, because git will not take a film and a chat file card (`SendUserFile`) refuses a file over 30 MiB (`exceeds the 30 MiB upload limit`). You split the film into pieces and store them on the page. When the user presses a button, their browser fetches the pieces, checks each one's size and SHA-256 (a fingerprint of the file), joins them, plays the film, and saves it as one normal MP4. A computer browser has no size limit on the save short of its own memory, and the Android app caps it at 200 MiB. The page also shows chapters, a description with a copy button, what you changed, and what you would like checked.

What was tested: an earlier version of this page delivered a real 19-minute film, which played and saved as one 339 MB MP4. This exact page was tested on a Mac on 2026-11-09 in headless Chrome against a stand-in for claude.ai, where the saved file matched the original exactly. It was not pressed by a person inside claude.ai for this guide, and nothing here was run from a Linux container.

1. **Split the file,** into a folder inside your working directory, because a file outside it needs an upload call of its own. A file under 20 MiB still works: it becomes one piece.

   ```bash
   cd /path/to/shorts
   python3 split-for-artifact.py out/shorts/s01-9x16.mastered.mp4 out/s01-9x16-pieces
   python3 split-for-artifact.py out/shorts/s01-4x5.mastered.mp4 out/s01-4x5-pieces
   ```

2. **Publish the empty page first,** because the pieces need a page to live on. Read the file whole first: the Artifact tool publishes only files you have read. If the tool asks you to load its design or capability skills, do so. Keep this page's script and data blocks unchanged. You fill in only the values in the `video-data` block. Keep the `url` in the result. The page's name comes from its `<title>` tag, so change that tag to a name of two to four words if you like.

   ```text
   Artifact
     action: publish
     file_path: delivery-page.html
     icon: video
     capabilities: {"assets": {}, "downloads": true}
   ```

3. **Upload the pieces.** Send at most 25 in one call, and make more calls if you need them. The result gives one `url` per piece, such as `/_blob/7db260ac...`. Use it exactly as given.

   ```text
   Artifact
     action: publish
     url: <the page>
     asset: true
     file_paths: [out/s01-9x16-pieces/part-01.mp4, out/s01-4x5-pieces/part-01.mp4, ...]
   ```

4. **Fill in the `video-data` block** in `delivery-page.html`. It is a JSON block inside the page. `videos` holds one entry per file the user can get, and each entry lists its `pieces`, each with its `url`, `size` and `sha256`. `size` and `sha256` come from `pieces.json`. The top-level `size` in that file is the video's whole size. Every field except `title` and `videos` can be left empty. `changes` and `checks` are lists of plain sentences. `shape` is optional: `tall` for 9:16, `square` for 4:5, or leave it out for 16:9.

   ```json
   {
     "title": "Your shorts",
     "intro": "Two shapes of each short. Press the button, watch it, and save it if you like it.",
     "meta": "45 s · 30 fps",
     "videos": [
       {"label": "Short 1, for phones (9:16)", "filename": "s01-9x16.mp4", "shape": "tall", "size": 5300000,
        "pieces": [{"url": "/_blob/7db260ac...", "size": 5300000, "sha256": "794caf1d..."}]},
       {"label": "Short 1, for feeds (4:5)", "filename": "s01-4x5.mp4", "shape": "square", "size": 3300000,
        "pieces": [{"url": "/_blob/798cc9b4...", "size": 3300000, "sha256": "786de73f..."}]}
     ],
     "description": "Post text to copy.",
     "changes": ["Tightened the pauses, so it runs faster than the long film."],
     "checks": ["Does the first line make you want the second? I can't listen."]
   }
   ```

5. **Publish the same file path again.** Leave out `capabilities` and `icon`, because they carry forward.

6. **Check the store.** Each line shows a SHA-256. Compare each with `pieces.json`.

   ```text
   Artifact  action: list  scope: assets  url: <the page>
   ```

7. **Send the link,** for example: "Your video is ready: <link>. Open it in your browser and press **Get the video**. When it has loaded it plays right there, and **Save to my device** gives you one normal MP4 file. Near the bottom I listed what I would like you to check. I can't listen to sound here, so please play it with the sound on." The page is private. If someone else needs to see it, the user shares it from the page's **Share** menu. You cannot do that for them.

**Over 1 GiB.** One page holds 1 GiB and 5,000 files, counting everything on it. Each page fetches pieces from its own store, so a video's pieces must all sit on one page. Cut a film over that into two parts at a keyframe, with no re-encoding, near the middle (`<seconds>`), then give each part a page of its own: copy `delivery-page.html` to a new file name, such as `delivery-page-2.html`, and repeat the steps above. The cut was run on a Mac. Two pages were not tried on a real job.

```bash
cd /path/to/shorts
ffmpeg -v error -y -i <film>.mastered.mp4 -map 0 -c copy -f segment -segment_times <seconds> -reset_timestamps 1 -segment_format_options movflags=+faststart out/part-%d.mp4
```

## Files

Everything from here on is a file to save, not text to read. Step 0 saves them all. Open one only when you need to change it or when a step says to read it.

`tools/setup-transcription.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/tools/setup-transcription.sh (41 lines).
```

`tools/transcribe.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/transcribe.py (104 lines).
```

Save this as `src/Root.tsx`
```tsx
import React from 'react';
import {Composition} from 'remotion';
import {Short, type ShortData} from './Short';
import shorts from './shorts.json';

export const Root: React.FC = () => (
	<>
		{(shorts as unknown as ShortData[]).map((d) => (
			<React.Fragment key={d.id}>
				<Composition id={`${d.id}-9x16`} component={Short} width={1080} height={1920} fps={d.fps} durationInFrames={d.durationInFrames} defaultProps={{data: d, guides: false}} />
				<Composition id={`${d.id}-4x5`} component={Short} width={1080} height={1350} fps={d.fps} durationInFrames={d.durationInFrames} defaultProps={{data: d, guides: false}} />
			</React.Fragment>
		))}
	</>
);
```

`src/Short.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/Short.tsx (263 lines).
```

`tools/make-sample.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/make-sample.py (78 lines).
```

`tools/build-short.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/build-short.py (302 lines).
```

`tools/short-voice.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/short-voice.py (53 lines).
```

`tools/master-audio.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/master-audio.py (114 lines).
```

`tools/check-delivery.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/check-delivery.py (467 lines).
```

`split-for-artifact.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/split-for-artifact.py (48 lines).
```

`delivery-page.html`, which the copy step puts in your folder:

```html
# In this skill's files folder: files/delivery-page.html (305 lines).
```
