---
name: publish-youtube
description: Get a finished long film ready for YouTube: title, thumbnail and chapters decided together, cold open, payoff ledger, description and call to action, a checked metadata file, poster frames, loudness and file checks, and a clear list of what the user does by hand. Use it before a long film is uploaded, ideally before its final render.
---

# Get a long film ready for YouTube

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

**Read up to the heading `## Files`, and stop there.** Everything after that heading is scripts, which Step 0 saves for you.

## What this skill does

A film can pass every technical check and still go unwatched. The checks measure whether it is correct. Whether anyone presses play, and stays, is decided by other things: the title, the thumbnail, the chapter list, what the first minute does, and whether every promise the film makes is kept.

This skill covers those things, then the file YouTube gets. It produces:

- a title, three thumbnail options and a chapter list, decided together
- a payoff ledger: every promise the film makes, and the moment it pays it
- a description, checked against YouTube's limits
- a mastered MP4 that passes a file check
- a subtitle file, if the user wants one
- a short list of what the user does by hand

**You do not upload anything.** You have no credentials and no upload tool here. The user picks the thumbnail and the visibility, and no film goes out without that.

The examples are from a 24-minute talk cut to a 19-minute film, and two workshops cut to 81 and 26 minutes. Titles and words shown in examples are invented for this page.

## When to use it (and when not to)

Use it for a long film on YouTube: an edited talk, a workshop episode, an explainer. **It works best before the final render,** since the cold open is cut to pay the title and thumbnail. After the render you can still do everything except recut the open. Say so, and ask whether to recut.

Do not use it for:

- a course lesson or a private training video. Its title should be a plain label that says what is inside, and this page pulls the other way
- a Short. YouTube Help says Shorts run up to three minutes, square or vertical (read on 2026-11-09). Their rules differ

**The package is outside the film.** The title, thumbnail words and the description's hook may be sharp and slogan-shaped. Inside the film, keep the user's own writing style. A speaker's own line, quoted, is not a slogan you wrote.

## What you need before you start

**The finished film** (or the near-final cut), and **its chapter times**: from the edit's data file, or from your own list.

**A cloud session, as measured when this was written:** a Linux x64 container with 4 cores, about 15 GB of memory, no swap and no GPU. The Bash tool times out at 10 minutes. Git will not hold big media: GitHub refuses a file over 100 MB. A chat file card refuses over 30 MiB. Only what is pushed to the remote is sure to survive a container rebuild, so commit and push the metadata as you go.

**Everything below was run on an Apple Silicon Mac on 2026-11-09, not on Linux,** with Remotion 4.0.541 and 4.0.542, ffmpeg 7.1.1 and Python 3.10. No keys or paid services are needed.

**Check these:**

```bash
command -v ffmpeg ffprobe && ffmpeg -version | head -1
node --version; python3 --version; df -h .
for u in https://registry.npmjs.org/remotion https://remotion.media https://support.google.com/youtube/answer/9884579; do
  printf '%s  ' "$u"; curl -sS -L -o /dev/null -m 15 -w '%{http_code}\n' -r 0-100 "$u" 2>&1 | tail -1
done
```

A refusal reads `CONNECT tunnel failed, response 403` or `Host not in allowlist`. Any other status means the host answered. The user can allow a host in the session's cloud environment menu (Edit, then Network access). On the cloud container measured in September 2026, YouTube's own pages could not be reached, so a limit may have to be checked by the user.

**If ffmpeg is missing** and apt is refused, PyPI has a static build, and ffprobe comes from Remotion's package, so run the install in Step 8 first. Remotion's own ffmpeg is cut down, so do not use it for this work.

```bash
python3 -m venv ~/ff && ~/ff/bin/pip install -q imageio-ffmpeg
ln -sf "$(~/ff/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" /usr/local/bin/ffmpeg
```

If `/usr/local/bin` is not writable, link it into any folder on your PATH. This link was made this way on a cloud container and not re-run for this page.

## Steps

### Step 0. Copy this skill's files

**Do not retype long files.** Make the project folder, then copy this skill's files into it. Files already there are kept, so running it again after a restart cannot overwrite your work.

**Every command block below starts with its own `cd`,** because a `cd` may not carry over to the next command. Put the full path of your project where it says `/path/to/publish`.

```bash
mkdir -p /path/to/publish
```

```bash
cd /path/to/publish
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/publish-youtube"
cp -rn "$S/files/." . 2>/dev/null; test -e "youtube.json" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It saves every script, page and starter file in this guide, 15 in all.

Then make the folder the commands below write into:

```bash
cd /path/to/publish
mkdir -p out public/thumbs
```

### Step 1. Decide the title, thumbnail and chapters together

Decide all three in one sitting, before the render. They are one promise. The cold open is cut to pay it, and the chapter titles are printed under the title. A title chosen after the render promises something the first minute was not cut for.

**The title names the pain. The thumbnail states the thesis.** They complement each other and never repeat each other. An invented example:

| | |
|---|---|
| title | Why Good Plans Still Miss Their Dates (Full Talk) |
| thumbnail words | Plans lie. |
| chapter | 03 The first slip |

- **The phrase people search for does not have to be in the title.** One published episode put it in the description's first two lines and in the tags, and let the title be the one a person would click.
- **Draft many, and choose the one the film pays at once.** One published title was picked from nine drafts, because the workshop's opening paid it straight away.
- **A chapter title is part of the package.** Use the same words on the chapter card and in the description. Compute them from one source, so the two cannot drift.

### Step 2. Make the cold open pay the thumbnail

The first minute decides whether viewers stay. **Your measure is the film's own retention graph in YouTube Studio.**

- **Open at full energy and let it dip.** Never build up from a low start. No logo bumper and no housekeeping ("before we start…"). The 19-minute film opens on a 40.7 s teaser of six of the speaker's own lines, then a 4.5 s title card, and the talk starts at 0:45.
- **Show what the thumbnail promised within seconds.** Otherwise the viewer feels tricked. An open that promises more than the film holds is clickbait. The aim is the honest edge: **withhold the answer, never the subject.**
- **Put the second-best moment in the first minute after the open.** The best goes last. Never start the first chapter with context-setting.
- **Check it with the thumbnail beside you.** Tile the first 30 s, read the words spoken over them, and ask whether the picture or the voice delivers the claim:

  ```bash
  cd /path/to/publish
  ffmpeg -v error -y -t 30 -i film.mp4 -vf "fps=1/2,scale=384:-1,tile=5x3" -frames:v 1 out/open30.png
  ```

- **Scan the first minute in 10 s windows.** For each one, ask what would make someone leave there, and fix that.

### Step 3. Keep something happening, and watch the clock

Chapter cards alone do not hold a long film. One published workshop episode let no more than 90 s pass without a designed beat: a card, a slide, a cut to another camera, a push-in, or a key point flying in. The 19-minute film carries 9 lists, 6 pull quotes and 9 chapter cards over its 18 minutes of talk, and its longest stretch with no beat is 25.2 s.

- **Calm is fine.** Add structure (a card, a list, a quote), not faster cutting. Advice on cutting rate ranged from every 3 s to every 25 s, so no one rate is right. A talk cuts on its content.
- **Keep chapters short.** About one card every two minutes worked: that film's ran 1:22 to 2:14, after a 3:24 opening. A 2014 study of online course video (Guo, Kim and Rubin, "How Video Production Affects Student Engagement", ACM Learning at Scale) found median watching time was at most 6 minutes, whatever the video's length. So let no chapter run much past 6 minutes. The script below warns when one does.

### Step 4. Keep a payoff ledger

Write down every promise the title, the thumbnail, the teaser and each chapter card opens, and the moment the film pays it. A promise the film never pays is what a viewer remembers. An invented example:

| opened by | the promise | paid at | in chapter |
|---|---|---|---|
| title | why good plans miss their dates | 6:06 | 02 The hidden step |
| teaser | "You can't schedule a surprise." | 7:00 | 03 The first slip |
| thumbnail | "Plans lie." | 13:24 | 06 What to do instead |
| teaser, last line | "What would you cut first?" | 17:40 | 09 The one question |

- **Save the biggest payoff for the end.** Build up to it step by step. Find the single strongest line and land it in the final minutes. Nothing covers it: no card, no quote, no caption effect. If the title question closes the teaser, pay it last, and ask it again on the end card.
- **Name the share beats.** A share beat is a line or a frame someone would screenshot or send. If you cannot name one, there isn't one. Mark two or three. They get the biggest treatment on screen, and they are the first shorts.
- **Nothing says "wrapping up" before the last payoff.** No "to wrap up", "in conclusion" or "before we finish". An ending that announces itself makes people click away before it arrives.
- **After the payoff, end.** Use a hard cut or a short end card, and no spoken outro. Two films used about 9 s. YouTube Help says end-screen elements can go in the last 5 to 20 s of a video, the video must be at least 25 s long, a 16:9 video can have up to four, and they are not available on videos set as made for kids (read on 2026-11-09). So an end card of 5 s or more leaves them room.

### Step 5. Write the metadata file

Every decision goes in one JSON file. A script checks it, and it goes in git. Replace everything here with the real film's values. Every value below is invented.

Save this as `youtube.json`
```json
{
  "title": "Why Good Plans Still Miss Their Dates (Full Talk)",
  "thumbnail_words": "Plans lie.",
  "search_phrase": "project planning mistakes",
  "opening": "Why plans slip",
  "tags": ["project planning", "estimating", "team habits"],
  "links": ["https://example.com/start-here"],
  "cta": {"offer": "A free checklist:", "url": "https://example.com/start-here"},
  "fps": 30,
  "durationInFrames": 34710,
  "chapters": [
    {"at": "3:24", "title": "The hidden step"},
    {"at": "5:00", "title": "The first slip"},
    {"at": "11:43", "title": "What to do instead"},
    {"at": "17:32", "title": "The one question"}
  ],
  "beats": ["0:00", "0:45", "1:40", "3:24", "4:10", "5:00", "6:20", "7:30", "8:50", "10:00", "11:43", "13:00", "14:20", "15:30", "16:40", "17:32", "18:40"],
  "ledger": [
    {"promise": "why good plans miss their dates", "opened_by": "title", "paid_at": "6:06"},
    {"promise": "You can't schedule a surprise.", "opened_by": "teaser", "paid_at": "7:00"},
    {"promise": "Plans lie.", "opened_by": "thumbnail", "paid_at": "13:24"},
    {"promise": "What would you cut first?", "opened_by": "teaser", "paid_at": "17:40", "biggest": true}
  ],
  "share_beats": ["You can't schedule a surprise.", "What would you cut first?"]
}
```

- **Chapters** take `at` as `m:ss`, or `from` in frames.
- **If the film was edited with a data file** holding `fps`, `durationInFrames`, `chapters` (`from`, `title`), and `clips`, replace those four timing fields with `"edit": "path/to/edit.json"`. The script then reads the chapters and works out the beats itself. Every re-cut moves the times, so this is the safest way. If your data file has other fields, write `chapters` and `beats` by hand.
- **`opening`** names the stretch before the first chapter card. YouTube needs a chapter at 0:00, and a film that opens on a teaser has none. Leave it out when the first chapter already starts at 0:00.
- **`links`** is every URL the user approved, and only those. **Never invent a link.** An invented link ships a dead link to real viewers. Copy the call to action from the user, never from an old description, which may carry an old offer.

### Step 6. Check the metadata and write the description

The script is `tools/youtube-meta.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/publish
python3 tools/youtube-meta.py selftest   # proves the script works here
python3 tools/youtube-meta.py youtube.json --write description.md
```

It prints the chapter list, then one line per check. On the file above:

```text
YouTube chapters (youtube.json, 30 fps, 19:17):
0:00 Why plans slip
3:24 The hidden step
5:00 The first slip
11:43 What to do instead
17:32 The one question

PASS  title-length         49 of 100 characters
PASS  description-length   322 of 5000 bytes (322 characters) in the draft
PASS  tags                 3 tags, 43 of 500 characters
PASS  chapters-start       the first chapter is at 0:00
PASS  chapters-count       5 chapters; YouTube needs at least 3
PASS  chapters-min-length  shortest 1:36 ('3:24 The hidden step'); YouTube needs 10 s
WARN  chapter-long         longest 6:43 ('5:00 The first slip')
PASS  chapters-order       ascending; the film ends at 19:17
PASS  links                1 link(s), all approved
PASS  cta-present          carries example.com/start-here
WARN  beat-gap             longest stretch with no designed beat: 104.0 s, from 1:40
PASS  ledger               4 promises paid, the biggest last, at 17:40
PASS  share-beats          2 named
wrote d.md: a draft; replace its first line before it goes anywhere
youtube-meta: fits YouTube's limits
```

The two WARN lines are real: the invented example has a chapter over 6 minutes and a stretch with no beat for 104 s. A WARN never fails, and each is a question to raise with the user.

**Now write the description.** Open `description.md`, replace the `[HOOK…]` line, and add the rest. This order was used on two published episodes:

```text
<hook: one or two lines. The problem the title names, and what the film shows.
 The phrase people search for goes here.>

<optional: WHAT YOU'LL LEARN, five to eight lines>

CHAPTERS
0:00 <opening>
3:24 <first card's title>
…

<optional: WHO THIS IS FOR>

<the offer, in the user's own words>
<the URL>

<other links: only the ones the user approved>
<a role-played session: say the positions voiced belong to the exercise, not to the individuals>
<four to six hashtags>
```

Then check the file exactly as it will be pasted:

```bash
cd /path/to/publish
python3 tools/youtube-meta.py youtube.json --description description.md
```

It fails `placeholder` while the hook line is still there. It fails `description-chapters` when the timestamps are not this cut's list, which is how a description kept from an earlier cut shows up. It fails `links` on any URL not in `links`.

**YouTube's limits, and how sure each one is:**

| what | limit | source |
|---|---|---|
| title | 100 characters, no `<` or `>` | YouTube Data API reference, read 2026-11-09 |
| description | 5000 bytes, no `<` or `>`. An em dash is 3 bytes | the same. YouTube's Help is reported to say 5,000 characters. The script uses bytes, the stricter reading |
| tags | 500 characters in all. Commas between tags count, and so do the quotes around a tag holding a space (`Foo Baz` counts as nine) | the same |
| chapters | the first at 00:00, at least three in ascending order, each at least 10 s | YouTube Help "Video chapters", read 2026-11-09 |

**Break a chapter rule and YouTube shows no chapters at all,** only plain text.

- **Times round down to the whole second,** so a chapter link lands up to a second before its card, never after it.
- **A film with no three parts of 10 s or more** gets no chapters. The script has no mode for that. Delete the `CHAPTERS` line from the description, and expect exactly `FAILED chapters-start, chapters-count, chapters-min-length`. Read the other lines: each must PASS.
- **Chapters are for finding your way.** Add them so a viewer can find the part they came for.
- **Tags:** how much they matter was not checked. Use a few that fit, and do not spend long on them.

### Step 7. Poster frames

A poster is a frame strong enough to carry the film. The thumbnail usually starts from one. This script shortlists three. A person picks. Run it on the working copy if there is one, because a finished film has captions burned in.

The script is `tools/poster-frames.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/publish
python3 tools/poster-frames.py <working copy or film.mp4> out/posters
```

Read all three with your own eyes. It knows sharpness and colour. It does not know whether someone's eyes are shut, or whether a frame gives away the answer the film withholds. On a question-led film, one poster once showed the answer in type across the bottom. **Reject that frame even if it scores best.**

### Step 8. The thumbnail, rendered as a still

Make three options with Remotion.

**Tell the user this once, plainly:** Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees. Others need a company licence (see `node_modules/remotion/LICENSE.md` or remotion.dev/license).

All `@remotion/*` packages and `remotion` must be the exact same version.

```bash
cd /path/to/publish
npm init -y >/dev/null
V=$(npm view remotion version); echo "Remotion $V"
npm i -E remotion@$V @remotion/cli@$V @fontsource/inter react react-dom
npx remotion browser ensure
```

If the proxy refuses `remotion.media`, or you see `getaddrinfo ENOTFOUND remotion.media`, take the same Chrome version from Google. The `remotion.config.ts` below finds it there, so no flag is needed:

```bash
cd /path/to/publish
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
cd /path/to/publish
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

Save this as `src/stills.ts`
```ts
import {registerRoot} from 'remotion';
import {ThumbStills} from './Thumbs';

registerRoot(ThumbStills);
```

The file is `src/Thumbs.tsx`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/publish
cp out/posters/poster1.jpg public/thumbs/face-a.jpg
cp out/posters/poster2.jpg public/thumbs/face-b.jpg
for o in a b c; do
  npx remotion still src/stills.ts thumb-$o out/th/$o.png
  for w in 336 168; do ffmpeg -v error -y -i out/th/$o.png -vf scale=$w:-1 out/th/$o-$w.png; done
done
npx remotion still src/stills.ts thumb-a out/th/a-4k.jpg --scale=3 --image-format=jpeg --jpeg-quality=90
```

To try this with no film yet, make a test frame first: `ffmpeg -v error -y -f lavfi -i testsrc2=s=1280x720 -frames:v 1 public/thumbs/face-a.jpg`, and the same for `face-b.jpg`.

**What worked on two published thumbnails. These are starting points:**

- **Four bold words or fewer.** Both used three. They state the thesis and do not repeat the title.
- **One to three faces, large:** the film's own speakers. Both were trios. No tool here cuts a person out of a frame. Crop in CSS as the example does, ask the user for cut-out PNGs, or try a public background-removal tool (not tested here).
- **High contrast.** Both used a dark ground (the example uses #111827). Measure any accent colour against its ground.
- **Text top left,** clear of the bottom-right corner, where YouTube prints the running time.
- **Every word legible at 168 px wide and at 336 px.** 168 px is about the size of YouTube's side list, as one past review checked, and 336 px is twice that. **Open both files and read each word.** A thumbnail that only works at full size does not work.

**YouTube's thumbnail rules** (YouTube Help, read 2026-11-09): 16:9, with 3840×2160 recommended and a minimum width of 640 px, as JPG or PNG. Desktop uploads are capped at 50 MB and mobile uploads at 2 MB. Custom thumbnails need a verified account. Measured here: `--scale=3` gave a 3840×2160 JPG of about 500 KB, and a 1280×720 PNG of about 700 KB. Use a JPG if the user uploads from a phone.

**Show the user all three at 336 and 168 px, on a near-black page,** labelled A, B and C, at natural size with no scaling. The small sizes are what a viewer sees in search and on a phone. One published thumbnail was picked from exactly such a mock-up. The two they do not pick can go into YouTube Studio's thumbnail test, if their account has it.

Do not name two files alike in everything but case. A Mac treats `thumbs.ts` and `Thumbs.tsx` as one name, which breaks the import with `You must pass a React component to registerRoot()`.

### Step 9. The file you upload

**YouTube's recommended upload settings** (YouTube Help, read 2026-11-09): MP4 with the moov box at the start; AAC-LC at 48 kHz; H.264 High Profile, 4:2:0, progressive; the frame rate it was recorded in; BT.709 for standard video. 8 Mbps for 1080p at 24 to 30 frames a second.

- **Fix the colour in the render, not after.** Mastering copies the picture. A render on Remotion 4.0.541 without flags measured BT.601 colour (an older standard than BT.709) with no matrix tag and an sRGB transfer tag, so players guess, and the check below fails it. Render with `--color-space=bt709 --image-format=png`.

  **Colour tags.** A video file carries labels that tell players how to show its colours. Check that all four are there. On Remotion 4.0.541 on a Mac, a render with `--color-space=bt709 --image-format=png` had all four. On an older Remotion on Linux, only the matrix tag was there. This is not yet measured on Linux at 4.0.541. So check with ffprobe, and if a tag is missing, write it without re-encoding.

  ```bash
  cd /path/to/publish
  ffprobe -v error -select_streams v:0 -show_entries stream=color_range,color_space,color_primaries,color_transfer -of default=nw=1 out/film.mp4
  ```

  You want `color_range=tv` and `bt709` on the other three. If any reads `unknown`, this writes them without touching a pixel:

  ```bash
  cd /path/to/publish
  ffmpeg -v error -y -i out/film.mp4 -c copy \
    -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1 \
    -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -movflags +faststart out/film.tagged.mp4
  mv out/film.tagged.mp4 out/film.mp4
  ```

- **If the film is already rendered without the flags,** render it again if you can. Changing only the label leaves the colours slightly off. If it cannot be rendered again, convert it once. This re-encode passed the file check and came closer to a correct render than a label change did:

  ```bash
  cd /path/to/publish
  ffmpeg -i in.mp4 -vf "scale=in_range=tv:out_range=tv:in_color_matrix=bt601:out_color_matrix=bt709,format=yuv420p,setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709" \
    -c:v libx264 -crf 18 -c:a copy -movflags +faststart out/film.mp4
  ```

- **Bitrate.** A 19-minute film at `--crf=20` came to 352 MB, about 2.4 Mbps, well under the 8 Mbps recommended. Whether a higher rate looks better after YouTube's own encode was not measured. If the user cares, render a minute at `--crf=16` and let them compare.
- **The Help page also says "No Edit Lists".** ffmpeg writes one by default. On a test, `-use_editlist 0` moved the picture 67 ms off the sound, so it is not used here. Whether YouTube minds the default was not measured.

**Master the sound, last.** It is a normal last step. Renderers do not set loudness for you. YouTube is widely reported to turn loud videos down and not to turn quiet ones up, which was not checked against a YouTube page. So a film at -16 LUFS (a unit of how loud a film sounds) can play about 2 dB quieter than one at -14. Starting points, as a floor: -14 LUFS for YouTube and short social clips, -16 LUFS for podcasts or when the platform is unknown, peak -1.5 dBTP. Use what the user or the platform asks for. dBTP is how high the loudest moment reaches.

The script is `tools/master-audio.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/publish
python3 tools/master-audio.py out/film.mp4 --target=-14
```

**The ceiling is a request, not a limiter.** Asked for -1, one teaser landed at -0.1 dBTP. If the script prints a note, or the check below fails on the peak, master again from the render with `--peak=-2.5`. Report the after row, not the target. Master once, from the render. Nothing re-encodes after it.

**Then run the file check.** Upload only what it passes.

The script is `tools/check-delivery.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/publish
python3 tools/check-delivery.py selftest   # once on a new machine: it plants each defect and proves each check
python3 tools/check-delivery.py out/film.mastered.mp4 --fps=30
```

Measured on a 56-second test film:

```text
PASS  codec      h264 yuv420p, range tv, matrix bt709, primaries bt709, transfer bt709
PASS  cfr        1692 frames at 30 fps (r 30/1, avg 30/1); spacing 33.33 ms x1691
PASS  faststart  moov at byte 32, before mdat at 63,525 [ftyp moov free mdat]
PASS  audio      aac LC, 48000 Hz, 2 ch, 248 kb/s
PASS  av-length  video 0.000-56.400 s, audio 0.000-56.405 s: audio starts +0 ms, ends +5 ms (+0.2 frames)
PASS  flashes    1692 frames; the most flashes in any second: 0 over a quarter of the screen, 1 over a quarter of a 10-degree field (from 0:04.20, at x 0-33 %, y 25-58 %)
PASS  loudness   -14.1 LUFS, -1.4 dBTP, range 4.6 LU (want -14 +-1 LUFS, at most -1 dBTP)
film.mastered.mp4: ready to deliver
```

**A `flashes` WARN** names a second to look at: on real films it was hands near the lens. Look at it, and tell the user. A FAIL means change the picture.

### Step 10. A subtitle file

The script is `tools/make-srt.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/publish
python3 tools/make-srt.py <edit.json or a transcript.json of the film> out/film --title="<film title>"
```

It writes `out/film.srt` (at most 2 lines of 42 characters and 6 s a cue) and a readable `out/film.txt`. **If the film has burned-in captions,** a viewer who turns on captions sees two sets of the same words. Tell the user, and let them choose.

**If you have no word-timed transcript,** this uses no paid service: sherpa-onnx from PyPI, and Parakeet TDT 0.6B v2 (a speech model, English only, 633 MB on disk) from sherpa-onnx's GitHub releases. The scripts are `tools/setup-transcription.sh` and `tools/transcribe.py`, saved in Step 0 from [Files](#files).

```bash
cd /path/to/publish
bash tools/setup-transcription.sh
```

It ends with a line such as `ready. Run this in each new shell: export ASR_HOME=/opt/asr`. `$ASR_HOME` is the folder that holds the speech tools and their models. A setting like this may not carry over to the next command, so start every command that uses it with that line. The command below writes `export ASR_HOME=$HOME/asr`. Use the path yours printed. If a download fails, the script stops with curl's error, and running it again skips what is already there.

```bash
cd /path/to/publish
export ASR_HOME=$HOME/asr
ffmpeg -v error -y -i out/film.mastered.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le out/film16k.wav
$ASR_HOME/venv/bin/python tools/transcribe.py out/film16k.wav edit-transcript.json
```

Read it through and correct names and mishearings by hand. Keep the speaker's own wording.

### Step 11. Checks before upload

Go through this list with the user. Every line should hold.

- [ ] Title, thumbnail and chapters decided together, ideally before the render.
- [ ] The first 30 s deliver what the thumbnail promised.
- [ ] Every promise is paid, and the biggest last (`ledger` passes).
- [ ] Nothing before the last payoff says the film is ending.
- [ ] The thumbnail reads at 168 px and at 336 px.
- [ ] `python3 tools/youtube-meta.py youtube.json --description description.md` passes.
- [ ] `python3 tools/check-delivery.py out/film.mastered.mp4 --fps=<rate>` ends `ready to deliver`, and every WARN was looked at.
- [ ] Every link in the description was opened once by a person.
- [ ] The user has picked the thumbnail and the visibility.

### Step 12. Hand it to the user

If the film is on the user's own machine, give the paths. In a cloud session, send it through the private page in the [Appendix](#appendix-the-delivery-page). The page shows the description and chapters too. The thumbnails and `.srt` are small enough for chat file cards (`SendUserFile`, up to 30 MiB).

**Commit and push** `youtube.json`, `description.md`, the source of the thumbnails and the `.srt`, by path, in one command. Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs. Run `git status` after: a commit hook may reformat files you did not touch, and you restore only files that were clean before it.

### Step 13. What the user does by hand

Give them this list. The labels are from memory of YouTube Studio and were not checked against the live page, so they may differ.

1. In YouTube Studio, choose **Create**, then **Upload videos**, and pick the mastered file.
2. Paste the **Title**.
3. Paste the whole **Description**. Chapters come from its timestamps.
4. Upload the **Thumbnail** they picked. If the option is missing, their account needs verifying.
5. Answer the **Audience** question (made for kids or not). End screens are not available on made-for-kids videos.
6. Under **Show more**, paste the **Tags**, and upload the `.srt` under subtitles if they chose to.
7. Add an **End screen** in the last 5 to 20 s, over the end card, pointing at the next video.
8. Choose **Visibility**. Recommend Unlisted first: watch it once on a phone and check that the chapters appear, then publish.
9. **After it is live,** check that the chapters show on the progress bar. Look at the retention graph after a few days, and tell you where it dips. That is the real measure.

## How to talk to the user

Use plain words. Ask one question at a time, with your recommendation.

1. "Who is this film for, and what are they stuck on?" The title names that pain.
2. "What should the viewer do at the end, and what is the exact link?" Never invent a link.
3. "Here are three titles and what each one promises. I recommend B, because the film pays it in the first minute. Which do you want?"
4. "Here are three thumbnails at the size people will see them. Which one reads best to you?"
5. "Do you have colours, a logo, or a channel you like the look of?" The look here is a placeholder, so invite their taste and references.
6. "Public, unlisted or scheduled?" That is their call. Recommend unlisted first.

**Pause for their OK:**

- on the title, thumbnail words and chapter list, before any recut or render
- if the open does not pay the thumbnail: say so plainly, and offer the recut
- on the thumbnail, the description and the visibility, before they upload

**Do not promise results.** No number here predicts views. Say what you checked, and what you could not check, such as how it sounds or whether the live page shows the chapters.

## What goes wrong and how to fix it

| what you see | why | fix |
|---|---|---|
| YouTube shows no chapters | a rule was broken | run `youtube-meta.py`: first at 0:00, at least 3, each 10 s or more, ascending, and on their own lines |
| `chapters-start` fails: `YouTube needs 0:00` | the film opens before the first card | set `opening` in `youtube.json` |
| `opening is set, but the first chapter is already at 0:00` | both were given | remove `opening` |
| `description-chapters` fails | the description is from an earlier cut | copy the list the script prints |
| `placeholder` fails | the `[HOOK` line is still there | write the hook |
| `links` fails: `not approved` | a URL not in `links` | ask the user. Never invent one |
| `ledger` fails: `unpaid` | a promise has no payoff | change the promise, recut, or name where it pays |
| `ledger` fails: `the biggest payoff is not the last` | a later payoff follows it | reorder, or say which truly is biggest |
| `youtube-meta: ... cannot read it` | a missing field | it needs `fps`, `durationInFrames` and `chapters`, or `edit` |
| `check-delivery` FAILS `codec`: `matrix unset` or `pix_fmt yuvj420p` | rendered without the colour flags | render again with `--color-space=bt709 --image-format=png`, or convert once (Step 9) |
| `check-delivery` WARNS `codec`: primaries unset | a tag is missing | tag it, then master again from the tagged render |
| `check-delivery` FAILS `cfr`, `declares 30/1, want 25` | the wrong `--fps` | give the film's own rate |
| `check-delivery` FAILS `av-length` | a timestamp hole | master again from the render, using this skill's script |
| `check-delivery` FAILS `loudness` | quiet or too peaky | read the numbers. Master again from the render, with `--peak=-2.5` if the peak is high. Fix the mix if it cannot reach the target |
| Colours look off after upload | a matrix mismatch | check `codec`. Convert the matrix as well as the range |
| YouTube refuses the thumbnail | too large from a phone, or an unverified account | use the JPG from Step 8; verify the account |
| `You must pass a React component to registerRoot()` | two file names differ only by case | keep the entry named `src/stills.ts` |
| A serif font in the thumbnail | the font did not load | check the `@fontsource/inter` import at the top of `src/Thumbs.tsx` and the `fontFamily` line. `@remotion/google-fonts` is another option, and it needs Google's font host at render time |
| `Your macOS version is older than macOS 15 (Sequoia). Some features such as rendering may not work.` | a warning, not a stop | rendering was fine on macOS 14 |
| `Set ASR_HOME first.` | the shell lost the setting | start the command with the `export ASR_HOME=` line the setup script printed |
| `RuntimeError: Load model from .../encoder.int8.onnx failed` and `File doesn't exist` | the speech model is not on disk | run `bash tools/setup-transcription.sh` again. It stops with curl's error if a download fails, and GitHub has answered 504 for a while on one test, so try again later |
| `CONNECT tunnel failed, response 403` | the proxy refuses the host | test with curl; the user can allow it (Edit, then Network access) |
| `exceeds the 30 MiB upload limit` | the file is too big for a file card | use the private page in the Appendix |

## How to check it worked

- `python3 tools/youtube-meta.py youtube.json --description description.md` ends `fits YouTube's limits`.
- `python3 tools/check-delivery.py out/film.mastered.mp4 --fps=<rate>` ends `ready to deliver`.
- You opened the thumbnail at 168 and 336 px, and read every word with your own eyes.
- You watched the first 30 s sheet with the thumbnail beside you. A file check cannot tell you the video is good.
- The user confirms, after upload, that the chapters appear and the thumbnail is the one they picked. You cannot see the live page.

## Appendix: the delivery page

Files go out through a private page, because git will not take a film and a chat file card (`SendUserFile`) refuses a file over 30 MiB (`exceeds the 30 MiB upload limit`). You split the film into pieces and store them on the page. When the user presses a button, their browser fetches the pieces, checks each one's size and SHA-256 (a fingerprint of the file), joins them, plays the film, and saves it as one normal MP4. A computer browser has no size limit on the save short of its own memory, and the Android app caps it at 200 MiB. The page also shows chapters, a description with a copy button, what you changed, and what you would like checked.

What was tested: an earlier version of this page delivered a real 19-minute film, which played and saved as one 339 MB MP4. This exact page was tested on a Mac on 2026-11-09 in headless Chrome against a stand-in for claude.ai, where the saved file matched the original exactly. It was not pressed by a person inside claude.ai for this guide, and nothing here was run from a Linux container.

1. **Split the file,** into a folder inside your working directory, because a file outside it needs an upload call of its own. A file under 20 MiB still works: it becomes one piece.

   ```bash
   cd /path/to/publish
   python3 split-for-artifact.py out/film.mastered.mp4 out/film-pieces
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
     file_paths: [out/film-pieces/part-01.mp4, out/film-pieces/part-02.mp4, ...]
   ```

4. **Fill in the `video-data` block** in `delivery-page.html`. It is a JSON block inside the page. `videos` holds one entry per file the user can get, and each entry lists its `pieces`, each with its `url`, `size` and `sha256`. `size` and `sha256` come from `pieces.json`. The top-level `size` in that file is the video's whole size. Every field except `title` and `videos` can be left empty. `changes` and `checks` are lists of plain sentences. `shape` is optional: `tall` for 9:16, `square` for 4:5, or leave it out for 16:9.

   ```json
   {
     "title": "Why good plans miss their dates",
     "intro": "Your 19-minute film, ready to upload. Press the button, watch it, and save it if you like it.",
     "meta": "19:17 · 1920×1080 · 30 fps",
     "videos": [
       {"label": "The film", "filename": "film.mp4", "size": 57940422,
        "pieces": [{"url": "/_blob/7db260ac...", "size": 19922944, "sha256": "794caf1d..."},
                   {"url": "/_blob/798cc9b4...", "size": 19922944, "sha256": "786de73f..."}]}
     ],
     "chapters": [{"t": "0:00", "title": "Why plans slip"}],
     "description": "The whole description, ready to paste.",
     "changes": ["Set the volume for the web."],
     "checks": ["Does the first minute deliver what the thumbnail says? I can't listen."]
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
cd /path/to/publish
ffmpeg -v error -y -i <film>.mastered.mp4 -map 0 -c copy -f segment -segment_times <seconds> -reset_timestamps 1 -segment_format_options movflags=+faststart out/part-%d.mp4
```

## Files

Everything from here on is a file to save, not text to read. Step 0 saves them all. Open one only when you need to change it or when a step says to read it.

`tools/youtube-meta.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/youtube-meta.py (324 lines).
```

`tools/poster-frames.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/poster-frames.py (81 lines).
```

Save this as `src/Thumbs.tsx`
```tsx
import '@fontsource/inter/900.css';
import React from 'react';
import {AbsoluteFill, Img, staticFile, Still} from 'remotion';

// Inter is an example, from local files. For another font: npm i @fontsource/<name>, and import its weight above.
const fontFamily = 'Inter';

type Props = {
	readonly words: string; // four bold words or fewer: the thesis, not the title again
	readonly face: string; // a frame under public/
	readonly focus: string; // which part of the frame stays in view, as CSS object-position
	readonly ground: string;
	readonly ink: string;
	readonly accent: string;
};

const Thumb: React.FC<Props> = ({words, face, focus, ground, ink, accent}) => {
	const parts = words.split(' ');
	return (
		<AbsoluteFill style={{backgroundColor: ground, fontFamily}}>
			<Img src={staticFile(face)} style={{position: 'absolute', top: 0, right: 0, width: 640, height: 720, objectFit: 'cover', objectPosition: focus}} />
			{/* Text top left, clear of the bottom-right corner, where YouTube prints the running time. */}
			<div style={{position: 'absolute', left: 48, top: 44, width: 570, color: ink, fontWeight: 900, fontSize: 104, lineHeight: 1.0}}>
				{parts.slice(0, -1).join(' ')} <span style={{color: accent}}>{parts[parts.length - 1]}</span>
			</div>
		</AbsoluteFill>
	);
};

// Colours and words are examples. Make three real options with the user's own.
const dark = {ground: '#111827', ink: '#ffffff', accent: '#fbbf24'};
export const ThumbStills: React.FC = () => (
	<>
		<Still id="thumb-a" component={Thumb} width={1280} height={720} defaultProps={{...dark, words: 'First is heavy', face: 'thumbs/face-a.jpg', focus: '58% 20%'}} />
		<Still id="thumb-b" component={Thumb} width={1280} height={720} defaultProps={{...dark, words: 'Who goes first?', face: 'thumbs/face-b.jpg', focus: '58% 20%'}} />
		<Still id="thumb-c" component={Thumb} width={1280} height={720} defaultProps={{ground: '#f8fafc', ink: '#111827', accent: '#b45309', words: 'The cost of first', face: 'thumbs/face-a.jpg', focus: '58% 20%'}} />
	</>
);
```

`tools/master-audio.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/master-audio.py (114 lines).
```

`tools/check-delivery.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/check-delivery.py (467 lines).
```

`tools/make-srt.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/make-srt.py (93 lines).
```

`tools/setup-transcription.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/tools/setup-transcription.sh (41 lines).
```

`tools/transcribe.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/transcribe.py (104 lines).
```

`split-for-artifact.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/split-for-artifact.py (48 lines).
```

`delivery-page.html`, which the copy step puts in your folder:

```html
# In this skill's files folder: files/delivery-page.html (305 lines).
```
