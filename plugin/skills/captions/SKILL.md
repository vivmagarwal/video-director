---
name: captions
description: Put readable, word-highlighted captions in a Remotion video from a word-timed JSON file, check they stay in time with the sound, and make an .srt file. Use it for any video with speech that needs captions, burned in or as a separate file.
---

# Captions

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

You have a video with speech and a file with the time of each word. This skill gives you:

- a working `<Captions>` component for Remotion that shows a few words at a time and lights up the word being said
- an `.srt` subtitle file, from the same words
- a check that the words have not drifted away from the sound

The look here (white text, a black edge, a yellow highlight, the Inter font) is **one example**. Every colour, font and size is a setting. If the user has a brand, a style they like, or a reference video, use that.

## When to use it (and when not to)

Use it when:

- a Remotion video has narration or real speech, and you have word timings, or can get them
- the user wants an `.srt` to upload to YouTube or similar

Do not use it when:

- you have no word timings yet. Get them first. A voice tool may write them, and a speech recogniser can read them from any recording. This skill's input is that JSON file
- the video is not made with Remotion, and the user only wants captions burned on. You can still use `make-srt.mjs` and burn the `.srt` on with ffmpeg's `subtitles` filter, but that was not tested here

## What you need before you start

| You need | Check | Install |
|---|---|---|
| Node.js and npm | `node --version` | Tested on Node 24 |
| A Remotion project | `npx remotion versions` | Step 1 |
| `@remotion/captions` at the same version as `remotion` | `npx remotion versions` | Step 1 |
| A word-timed JSON file | Open it | Step 2 |
| The voice file | | `public/voice.mp3` here |
| ffmpeg and Python 3, for the checks | `ffmpeg -version`, `python3 --version` | `apt-get install -y ffmpeg`, if allowed |
| Network to npm | `curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://registry.npmjs.org/remotion` | A refusal reads `CONNECT tunnel failed` or `Host not in allowlist`. Any other status means the host answered. The user can open hosts in the cloud environment menu: Edit, then Network access |

**Licence, tell the user once.** Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees. Others need a company licence. See `node_modules/remotion/LICENSE.md` or `https://www.remotion.dev/license`.

**Tested how.** Everything here was tested on an Apple Silicon Mac on 2026-11-09 with Remotion 4.0.541: rendered, and the frames looked at. A still also rendered with all outbound network denied, so the font needs no host. It was not run on Linux, and the Chrome step below was run with the Mac download in place of the Linux one. Facts about the cloud, below, are from earlier cloud sessions in 2026.

## Steps

### 0. Save the tools

Make one project folder first: `mkdir -p /path/to/project`, with your real folder as a full path. Every step below starts with `cd /path/to/project`, because a `cd` from an earlier command may not carry over.

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd /path/to/project
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/captions"
cp -rn "$S/files/." . 2>/dev/null; test -e "tsconfig.json" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It keeps any file that already exists, so your work is safe.

### 1. Set up the project

Skip what you already have. All `remotion` and `@remotion/*` packages must be the exact same version, so check the latest with `npm view remotion version`.

```bash
cd /path/to/project
mkdir -p src public out
npm init -y >/dev/null
npm i --save-exact remotion @remotion/cli @remotion/captions @fontsource/inter react react-dom
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

**Chrome in a cloud session.** On Linux x64, Remotion downloads its browser from `remotion.media`. If the proxy refuses that, take the same version from Google and put it where `remotion.config.ts` looks:

```bash
cd /path/to/project
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

`angle` in `remotion.config.ts` worked with no GPU in the cloud container. Captions are plain page text, so they do not need anything more.

### 2. Get the words into the right shape

Remotion's caption type looks like this. Every word after the first has a **leading space**:

```json
[
  {"text": "Last", "startMs": 122, "endMs": 472, "timestampMs": 297, "confidence": null},
  {"text": " March,", "startMs": 522, "endMs": 1022, "timestampMs": 772, "confidence": null}
]
```

**The leading space is not a detail.** `createTikTokStyleCaptions` only breaks a page at a word starting with a space. In a test, five words with no spaces gave one page; the same words with spaces gave three. On a real transcript you get one giant page and no error.

If your timings are in another shape, convert them.

`to-captions.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/to-captions.py (59 lines).
```

```bash
cd /path/to/project
python3 to-captions.py transcript.json public/voice.captions.json
```

Put your voice at `public/voice.mp3`.

**Three units are in play.** Recognisers often give seconds, captions hold milliseconds, and a composition counts frames. Convert once, at the edge, and stay converted. If you pass seconds as milliseconds, every word lands in the first frames, and the captions flash and vanish.

**Word times are relative to the voice file.** If the voice starts at frame 90 of the video, tell the component with `voiceStartsAt={90}`. If you play a clip with `trimBefore`, subtract the trim. For a re-cut clip, map every word through the same list of cuts, once.

### 3. Add the component

`src/caption-pages.mjs`, which the copy step puts in your folder:

```js
# In this skill's files folder: files/src/caption-pages.mjs (44 lines).
```

`src/Captions.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/Captions.tsx (100 lines).
```

This Root has one landscape and one vertical composition as examples. Replace the gradient with your picture. If your project already has a `src/Root.tsx`, the extractor keeps yours, so add `<Captions>` to it yourself.

`src/Root.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/Root.tsx (55 lines).
```

Save this as `src/index.ts`

```ts
import {registerRoot} from 'remotion';
import {Root} from './Root';

registerRoot(Root);
```

Check that it loads:

```bash
cd /path/to/project
npx remotion compositions src/index.ts
```

```text
landscape    30      1920x1080      885 (29.50 sec)
vertical     30      1080x1920      885 (29.50 sec)
```

**Other fonts.** Inter is only an example. For another font, install its package (`npm i --save-exact @fontsource/lobster`, for example) and change the `import` and the `fontFamily` line. Without a font that really loads, you silently get a fallback serif.

Google Fonts is the other option: `npm i --save-exact @remotion/google-fonts`, then in `Captions.tsx` use `import {loadFont} from '@remotion/google-fonts/Inter'` and `const {fontFamily} = loadFont('normal', {weights: ['700'], subsets: ['latin']})` in place of the font lines. It fetches the font at render time, which failed in a real cloud session on 9 November 2026 (`net::ERR_CERT_AUTHORITY_INVALID`, then a 30-second timeout). So in a cloud session, stay with `@fontsource`.

### 4. Look at stills before any long render

Pick a frame in the middle of a word: `frame = startMs × fps ÷ 1000`. Then look at it with your own eyes:

```bash
cd /path/to/project
npx remotion still src/index.ts landscape out/a.png --frame=100
npx remotion still src/index.ts vertical out/b.png --frame=100
```

Check these:

- The right word is lit for that moment.
- The text sits inside the safe area (see below) and clear of anything important in the picture.
- Lines break well.
- A frame in a long pause shows no caption. In our test, with a 0.85 s pause at about 21.6 s, frame 647 was empty.

### 5. Choose how the pages read

A **page** is the group of words on screen at one time. These settings are in `pagesFrom` in `src/caption-pages.mjs`:

| Setting | Here | What it does |
|---|---|---|
| `pageMs` | 1800 | A page tries to last this long. About 1200 is good for short-form, with fewer words |
| `pauseMs` | 500 | A pause this long always starts a new page, so no half-full page hangs over silence. About 400 for short-form, 700 for a calm documentary read |
| `pageBreakAfter` | on full stops, `?`, `!` | Pages break on meaning, not just on time. The last word of a sentence also stays with the word before it, so it is never alone |

**Reading limits that worked, as starting points:**

- At most 17 characters a second on a page. Split a page that is faster.
- A page lasts from 833 ms to 7 s.
- A subtitle-style line has at most 42 characters, and two lines at most.
- Break after punctuation, and before a conjunction ("and", "but") or a preposition.
- Never leave one or two words alone on the top line.
- Never split an article from its noun, or a first name from a last name.

**Word highlight rules:**

- A page appears on the frame its first word starts.
- Each word lights on its own start, never earlier. A highlight ahead of the sound reads as a spoiler.
- A page stays 12 frames after its last word, then clears. A caption sitting through a two-second silence is dead air.
- A subtitle line, or designed text on screen, may lead its sound by 0.2 to 0.5 s, and never arrive late.
- Mark emphasis on purpose, for chosen words. A rule such as "the longest word" lands on the wrong word.

**Reading size,** as example starting points at 1920x1080 or 1080x1920. Scale by `Math.min(width, height) / 1080`:

| Frame | Captions | Do not go under |
|---|---|---|
| Landscape | 44 to 56 px | 34 px for anything that carries the message |
| Vertical | 52 to 92 px | 40 px. In one test on a phone-sized view, 26 was a smudge, 30 whispered, 34 read as secondary, and 40 read as a line meant to be read |

### 6. Keep the safe area

Screens and players cover parts of the frame. Treat these figures as floors, and look at the real thing.

**Landscape, 1920x1080.** These are working figures from past videos, not measured against the platforms. Keep everything to read 84 px from the edges. For YouTube, keep captions at least 108 px above the bottom, clear of the player's control bar. `bottomInset={108}` does that.

**Vertical, 1080x1920.** Platforms draw their own buttons and text over the video. These are the areas text may occupy. The three platform rows were measured pixel by pixel from each platform's official ad template in September 2026. They change, so check the current ones before a big batch:

| profile | text stays inside | where it comes from |
|---|---|---|
| YouTube Shorts | x 48 to 888, y 288 to 1248 | Google's overlay template |
| TikTok In-Feed | x 120 to 960, y 240 to 1260, but not x 780 to 960 where y is 840 to 1260 (the button stack) | TikTok Ads Manager's file, April 2025 |
| Instagram and Facebook Reels | x 65 to 1015, y 269 to 1248 | Meta's Ads Guide |
| **ad** | x 120 to 888, y 288 to 1248, and x at most 780 where y is over 840 | all three at once. Use it for anything that may be boosted as a paid ad |
| **organic** | x 60 to 888, y 240 to 1490 | a working choice from past videos, for posts that are not boosted. Not from a platform's file. y of 240 or more also keeps text inside Instagram's 3:4 grid crop |

Here is what each profile means for the component, for captions that sit in the band below y 840:

| profile | `bottomInset` | `left` | `right` |
|---|---|---|---|
| **ad** (the vertical example in `src/Root.tsx`) | 672 | 120 | 300 |
| **organic** | 430 | 60 | 192 |

Those numbers leave the text a little left of centre, because the buttons are on the right. Ask the user if these videos may be boosted. If yes or unsure, use `ad`.

**A 4:5 feed crop** of a vertical master drops 285 px at the top and the bottom. Anything that must survive both stays between y 285 and y 1635. The feeds' own buttons at 4:5 were not measured, so look at a 4:5 frame too.

**Leave room for captions in your picture.** The lowest thing in the picture should sit above the captions. Their height is about `bottomInset + fontSize × (1.6 + (lines - 1) × 1.1)`. At `bottomInset` 108, size 56, one line, that is 198 px from the bottom. In general, a drawing that will carry captions keeps its lowest label out of the bottom fifth of the frame.

**Text over footage.** Aim for at least 4.5:1 contrast against the worst pixel the text covers, across the whole shot. In order of preference:

1. A gradient scrim over the lower 40% of the frame: `linear-gradient(to top, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.45) 28%, transparent 60%)`.
2. A blurred pill behind the text: `backdropFilter: 'blur(18px) saturate(1.4)'`, `background: 'rgba(0,0,0,0.35)'`, `borderRadius: 999`.
3. A hard stroke of 14 to 16% of the font size, with `paintOrder: 'stroke fill'`. This is what the component uses.
4. A drop shadow alone is not enough. It fails exactly where the footage is busy.

`backgroundClip: 'text'` with a transparent fill cancels `WebkitTextStroke`. For a gradient fill with a stroke, stack two copies of the text.

### 7. Keep phrases together with non-breaking spaces

A **non-breaking space** (the character U+00A0) looks like a space, but no line can break there. Use it where a break would read badly, such as "six weeks", "24 minutes", or a first and last name.

The component does this for you. List the phrases as they appear in the captions, without the end punctuation:

```tsx
<Captions captions={captions} keepTogether={['six weeks', 'spreadsheet and found']} />
```

We tested this at 1080x1920 with the `ad` margins from step 6. Without it, the page broke as "opened a / spreadsheet / and found". With `keepTogether={['spreadsheet and found']}` it became "opened a / spreadsheet and found". That phrase is wider than those margins, and it stuck out to x 40 and x 860, because a kept phrase cannot wrap. So keep phrases short, and look at the frame. A non-breaking space also stops a page break there, because a page only breaks at a word starting with a normal space.

**A trap in your own JSX.** A non-breaking space in a JSX attribute must be a JavaScript string:

```tsx
<Title text={'six\u00A0weeks'} />   // right
<Title text="six\u00A0weeks" />     // wrong: the backslash text stays, literally
```

### 8. Captions and a respelled word

Sometimes the voice needs a word spelled for its sound, and the screen needs the real spelling. There are three cases:

1. **Your voice tool separates them.** Some voice scripts take `project{prodject}`, say the second and caption the first. Then there is nothing to do.
2. **The voice file was made from the spoken spelling,** so the captions file says `Tan-dor`. Put the real spelling back on what is displayed, and nowhere else. That is the `show` function in `src/caption-pages.mjs`, so the video and the `.srt` both get it:
   ```js
   export const show = (captions) =>
   	captions.map((c) => ({...c, text: c.text.replace(/Tan-dor/g, 'Thandor')}));
   ```
   Do not change the captions file itself. Anything that finds a moment by its spoken words still needs the spoken spelling.
3. **A speech recogniser wrote the captions,** and heard a name wrong. Keep a table of corrections for each segment, keep the recogniser's timings, and apply the table each time.

Read every name on a real frame before you call it done.

### 9. Render, then look again

```bash
cd /path/to/project
npx remotion render src/index.ts landscape out/film.mp4 --offthreadvideo-cache-size-in-bytes=800000000
```

Our 29.50 s test took 12 s on the Mac (11 cores). Not measured on a 4-core container, so run long renders in the background. The Bash tool times out at 10 minutes, and `pgrep -f` and `pkill -f` match their own command line, so use patterns such as `[r]emotion render`, or wait on the finished file.

Look at a contact sheet (a grid of frames), one frame every 3 seconds:

```bash
cd /path/to/project
ffmpeg -nostdin -y -v error -i out/film.mp4 -vf "fps=1/3,scale=480:-1,tile=4x3" -frames:v 1 out/sheet.png
```

Open `out/sheet.png`, and read every caption. Then pull out single frames from the video itself:

```bash
cd /path/to/project
ffmpeg -nostdin -y -v error -ss 3.33 -i out/film.mp4 -frames:v 1 out/check.png
```

### 10. Check caption drift

Drift means the words and the sound have slid apart.

`check-drift.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/check-drift.py (59 lines).
```

```bash
cd /path/to/project
python3 check-drift.py public/voice.captions.json public/voice.mp3
python3 check-drift.py public/voice.captions.json out/film.mp4
```

A real clean result from generated speech:

```text
7 pauses compared. Word starts +0.113 s from the sound (middle value); range +0.056 to +0.138 s.
```

To be sure it can fail, we told it the voice started 0.5 s later than it did. It printed `+0.613` and exited 1.

How to read it:

- **Every pause off by about the same amount** is a shift. Look for a wrong `voiceStartsAt` or a forgotten trim.
- **The gap grows through the file** means the audio was cut or stretched after the timings were made.
- **Music fills the pauses.** It prints `no pause in the sound nearby`. Check on the voice alone, or a render with no music.
- **A real recording with room noise is rougher.** Pass `--noise=-30dB`. On a noisy 53-second interview it gave a middle value of +0.023 s and a range of -0.377 to +0.520 s, and exited 1 for that range. So read the middle value. For noisy speech, if it is near zero and only a few pauses are off, you do not have drift.

**Look at the end too.** If the sound was cut, or the film runs a little long, the last line shows it. Mastering the sound afterwards can also change the timing of the last few seconds if done carelessly, so run this check on the finished file.

### 11. Choose burn-in, an .srt, or both

| | Burned in | `.srt` file |
|---|---|---|
| What it is | Part of the picture | A separate text file with times |
| Word highlight | Yes | No |
| Viewer can turn it off | No | Yes |
| Works on a silent autoplay feed | Yes | Often not |
| Search and translation can read it | No | Yes |
| Fix a typo | Render again | Edit the text |

Our suggestion: burn in for short social videos, and upload an `.srt` for a long video. For YouTube, do both only if the user wants: the two will overlap if a viewer turns on the subtitles.

Save this as `make-srt.mjs`, in the project folder:

```js
// Write an .srt file and report any page that is hard to read.
//   node make-srt.mjs public/voice.captions.json out/voice.srt
import {readFileSync, writeFileSync} from 'node:fs';
import {serializeSrt} from '@remotion/captions';
import {pagesFrom} from './src/caption-pages.mjs';

const [input, output] = process.argv.slice(2);
const captions = JSON.parse(readFileSync(input, 'utf8'));
// A subtitle holds more words than a highlighted page: about 4 s, 2 lines.
const pages = pagesFrom(captions, {pageMs: 4000, pauseMs: 800});

const wrap = (text, max = 42) => {
	if (text.length <= max) {
		return text;
	}
	// Break at the space nearest the middle, so the two lines come out even.
	const spaces = [...text.matchAll(/ /g)].map((m) => m.index);
	const middle = spaces.reduce((a, b) => (Math.abs(b - text.length / 2) < Math.abs(a - text.length / 2) ? b : a));
	return `${text.slice(0, middle)}\n${text.slice(middle + 1)}`;
};

let problems = 0;
const lines = pages.map((p) => {
	const start = p.tokens[0].fromMs;
	const end = p.tokens[p.tokens.length - 1].toMs;
	const text = p.tokens.map((t) => t.text).join('').replace(/\u00A0/g, ' ').trim();
	const seconds = (end - start) / 1000;
	const report = (why) => {
		problems++;
		console.log(`${why}: ${seconds.toFixed(1)} s, ${text.length} characters: "${text}"`);
	};
	if (text.length > 84) report('too long (more than 2 lines of 42)');
	if (text.length / seconds > 17) report('too fast (more than 17 characters a second)');
	if (seconds < 0.833) report('too short (under 0.83 s)');
	if (seconds > 7) report('too long on screen (over 7 s)');
	return [{text: wrap(text), startMs: start, endMs: end, timestampMs: null, confidence: null}];
});
writeFileSync(output, serializeSrt({lines}) + '\n');
console.log(`${lines.length} subtitles written to ${output}. ${problems} to read again.`);
```

```bash
cd /path/to/project
node make-srt.mjs public/voice.captions.json out/voice.srt
```

```text
too fast (more than 17 characters a second): 2.2 s, 38 characters: "Nobody had touched them for six weeks."
too fast (more than 17 characters a second): 2.3 s, 42 characters: "Ask the people on it what they still need."
9 subtitles written to out/voice.srt. 2 to read again.
```

```text
1
00:00:00,122 --> 00:00:04,147
Last March, a new manager
opened a spreadsheet and found
```

Those "too fast" lines came from a generated voice at about 147 words a minute. Slightly over 17 is usually fine. Treat the line as something to read, and ask the user if many pages show it.

To carry the subtitles inside the video as a track a viewer can turn on, copying the picture and sound as they are:

```bash
cd /path/to/project
ffmpeg -nostdin -y -v error -i out/film.mp4 -i out/voice.srt -map 0 -map 1 -c copy -c:s mov_text -metadata:s:s:0 language=eng out/film.subs.mp4
```

### 12. Save your work

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs.

```bash
cd /path/to/project
git add src public/voice.captions.json remotion.config.ts tsconfig.json package.json package-lock.json make-srt.mjs
git commit -m "Captions" && git push
```

In a cloud session only what is pushed is sure to survive a restart. Git refuses files over 100 MB, so keep finished videos out of it. A commit hook may reformat files you did not touch: run `git status`, and restore only the files that were clean before.

## How to talk to the user

- Plain words: "captions", "the word that lights up". Not "tokens" or "pages", unless they ask.
- One question at a time, with a suggestion. For example: "Do you want captions in the picture, or a file viewers can turn on? I suggest in the picture, since this is a short for phones."
- Show a still before the long render, and ask if the look is right. Ask for their brand, font and colours, or a video they like.
- Then show a contact sheet, or a 10-second clip, before the whole thing.
- List names and terms for them to check. Show them as they will appear.
- Tell them about the Remotion licence once.
- Send a short clip and the stills as chat files, each under 30 MiB.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `Compositor exited with signal SIGKILL` | The machine ran out of memory, and the system killed the render. There is no swap to fall back on | Cap the frame cache with `--offthreadvideo-cache-size-in-bytes=800000000`, use `--concurrency=2`, and run it again. Nothing is lost. It can look odd afterwards, because `free -m` shows plenty of memory once the render is gone |
| The whole transcript sits on one page, with no error | Words have no leading space | Run `to-captions.py` |
| Captions flash at the very start, then nothing | Seconds passed as milliseconds | Convert to milliseconds once |
| Every word lights up early or late by the same amount | The voice starts elsewhere, or a trim was not subtracted | Set `voiceStartsAt`. Subtract the trim |
| Words light a couple of frames late | Normal with generated-voice timings. We measured 0.06 to 0.14 s after a pause | Leave it. A late highlight is better than an early one |
| Two words lit on one frame | A closed range | Use `frame >= start && frame < end`, as the component does |
| A serif font appears | The font did not load | Check the `@fontsource/inter` import and the `fontFamily` line in `Captions.tsx` |
| `Could not find a tsconfig.json file in your project` | No `tsconfig.json` | Save the one in step 1 |
| A package error about versions | `remotion` and `@remotion/*` differ | `npx remotion versions`, then install all at one exact version |
| `CONNECT tunnel failed, response 403` or `Host not in allowlist` | The proxy refused a host | Ask the user to allow it in the cloud environment menu: Edit, then Network access. For Chrome, see step 1 |
| `Failed to fetch` for the captions file | It is not in `public/`, or has another name | `ls public`. `staticFile('voice.captions.json')` means `public/voice.captions.json` |
| The text shows `\u00A0` literally | A JSX attribute in plain quotes | Use `{'six\u00A0weeks'}` |
| A caption hangs during a long pause | A custom component ignored the end of the last word | Clear it 12 frames after the last word, as the component does |
| Text covered by a player or an app's buttons | Outside the safe area | Use the numbers in step 6, and check the real platform |
| Text hard to read on bright footage | Low contrast | Add a scrim, a pill or a thicker stroke |
| `no pause in the sound nearby` | Music or noise hides the pauses | Use the voice alone, or `--noise=-30dB` |
| A name is spelled wrong | The recogniser or the voice file spelled it by sound | Case 2 or 3 of step 8 |

## How to check it worked

1. `npx remotion versions` says all packages match.
2. Stills show the right word lit. Work out the frame from `startMs` for three words, and look.
3. A frame in the middle of a long pause shows no caption.
4. The contact sheet, read by your own eyes, has no caption over a face or off the edge, and no bad line break.
5. `check-drift.py` passes on the voice and on the finished file.
6. `ffprobe -v error -show_entries stream=codec_type -of csv=p=0 out/film.subs.mp4` lists `video`, `audio`, `subtitle`, if you made a subtitle track. A file check cannot tell you the video is good.
7. `make-srt.mjs` lists nothing you have not read.
8. A person has watched it with the sound on and said yes. A machine here cannot listen, and only a person can tell if it feels in time.
