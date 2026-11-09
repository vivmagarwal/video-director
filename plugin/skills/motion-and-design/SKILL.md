---
name: motion-and-design
description: Make a video look good, with starting values for type, safe areas, colour, motion, pacing and diagrams, and a way to agree a look with the user. Use it when designing or improving how a video looks, in Remotion or any other tool.
---
# Motion and design for video

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It gives you a good starting point for how a video looks and moves, and a way to find what the user actually wants. Every number here is a starting point, not a law. These values came from real videos that were rendered and looked at. Your user's taste, brand and samples beat all of them.

Taste is the user's. Your job is to bring options, look at the frames and say what you see.

## When to use it (and when not to)

Use it when you choose a look, set type, plan motion or pacing, or when a video "feels off" and you need to find out why.

It does not cover how to build a project or render one, beyond one small example. The code here is for Remotion, a tool that makes video from React code, but the design values work in any tool.

## What you need before you start

Nothing for the advice. To try the example you need:

| Need | How to check | If it is missing |
|---|---|---|
| Node and npm | `node --version` | Install Node from nodejs.org |
| A Remotion project | `npx remotion versions` | The setup below |
| Chrome | Comes in the setup below. Before the install, `npx remotion browser ensure` fails with `npm error could not determine executable to run`, which does not mean Chrome is missing | The setup below |

**A minimal project.** A `cd` may not carry over from one command to the next, so each block starts with its own. Use the real full path in place of `/path/to/look-test`. First make the folder, and copy this skill's files into it. Files already there are kept. Do not retype long files.

```bash
mkdir -p /path/to/look-test
```

```bash
cd /path/to/look-test
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/motion-and-design"
cp -rn "$S/files/." . 2>/dev/null; test -e "tsconfig.json" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
npm init -y
npm pkg set type=module
npm i --save-exact remotion @remotion/cli @remotion/fonts @fontsource/inter @fontsource/fraunces @fontsource/space-grotesk react react-dom
npx remotion browser ensure
mkdir -p src out public/fonts
cp node_modules/@fontsource/fraunces/files/fraunces-latin-700-normal.woff2 public/fonts/
cp node_modules/@fontsource/inter/files/inter-latin-500-normal.woff2 node_modules/@fontsource/inter/files/inter-latin-800-normal.woff2 public/fonts/
cp node_modules/@fontsource/space-grotesk/files/space-grotesk-latin-500-normal.woff2 node_modules/@fontsource/space-grotesk/files/space-grotesk-latin-700-normal.woff2 public/fonts/
```

The fonts are local files, so a render needs no font server.

Save this as `tsconfig.json`:
```json
{"compilerOptions":{"target":"ES2022","module":"ES2022","moduleResolution":"bundler","jsx":"react-jsx","strict":true,"skipLibCheck":true,"esModuleInterop":true,"noEmit":true},"include":["src"]}
```

If `remotion.config.ts` already exists, keep it and add only the lines it lacks.

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

Without `tsconfig.json` every command stops with `Could not find a tsconfig.json file in your project`. `angle` is how Chrome draws. It worked in a cloud container with no GPU. The comment in the config names `setup-video.sh`, a script this guide does not use: the Chrome fallback below puts Chrome in the same place.

All `remotion` and `@remotion/*` packages must be the same exact version. `npx remotion versions` checks that.

**If Chrome will not download** (`CONNECT tunnel failed, response 403` or `Host not in allowlist`), take the same version from Google on Linux x64:

```bash
cd /path/to/look-test
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

`remotion.config.ts` then finds this Chrome by itself. A refusal is `CONNECT tunnel failed` or `Host not in allowlist`. Any other status from a host means it answered. The same route, with the Mac build, was tested on a Mac. The Linux build was not tested.

**Licence.** Tell the user once when you start a Remotion project: it is free for individuals, non-profits and for-profit companies with up to 3 employees; other companies need a company licence. See `node_modules/remotion/LICENSE.md` or remotion.dev/license.

## Steps

### Step 1. Ask for taste first

Before you pick anything, ask, one question at a time:

1. "Do you have a brand: colours, fonts, a logo?" Get the exact values if you can.

2. "Is there a video you would like this to feel like? A link or a file is perfect. Is there one you dislike?"

3. "Do you have any samples of your own, such as slides, a website or an old video?"

4. "Who watches it, and on what? A phone on a bus, or a laptop in a lesson?"

If they have a reference video, take frames from it and study them: what the ground colour is, how big the type is, how fast things move. Measure a frame instead of guessing:

```bash
ffmpeg -v error -y -ss 10 -i reference.mp4 -frames:v 1 ref-10s.png
```

Copy the qualities, not the work. Do not reuse someone's logo, characters, footage or exact design without permission.

### Step 2. Offer several directions as real stills

Do not describe looks in words. Render one frame of the real video in two or three different looks, and let the user point. Stills cost seconds, and changing a look later costs far more.

This file renders one frame in three looks. The look values are examples only. Replace them with what you learned in step 1. Keep the real words from their script.

`src/directions-entry.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/directions-entry.tsx (136 lines).
```

```bash
cd /path/to/look-test
npx remotion still src/directions-entry.tsx dir-paper out/dir-paper.png --frame=60
npx remotion still src/directions-entry.tsx dir-night out/dir-night.png --frame=60
npx remotion still src/directions-entry.tsx dir-poster out/dir-poster.png --frame=60
npx remotion still src/directions-entry.tsx dir-paper out/dir-guide.png --frame=60 --props='{"guide":true}'
```

The last line draws the safe area in pink, so you can check that everything sits inside it. Rendered and looked at on a Mac on 2026-11-09, not on Linux. To add a font, install `@fontsource/<name>`, copy the `.woff2` web font files you need into `public/fonts/`, and add a line to the list. Google Fonts is the other option: `@remotion/google-fonts` loads a font in one line, but it fetches it at render time, and whether the cloud proxy allows that was not measured. If such a render stops with an error holding the words `exceeded rendering` and `Fetching Inter font`, use font files.

Show the stills and give one recommendation, with your reason. Once they choose, write the choice down and keep it for the whole video. Viewers notice when a video changes its look halfway.

### Step 3. Set the type

Starting sizes, in pixels, for text you add to a 1920x1080 or 1080x1920 frame:

| Tier | Landscape | Portrait | Weight | Letter spacing | For |
|---|---|---|---|---|---|
| Hero | 220 | 170 | 800 | -0.045em | One word, or one number |
| Display | 140 | 120 | 800 | -0.035em | A title |
| Headline | 92 | 92 | 800 | -0.03em | A headline, moving words |
| Subhead | 62 | 62 | 700 | -0.02em | A second line, a chart title |
| Body | 44 | 52 | 500 | -0.01em | Captions, labels |
| Small | 34 | 40 | 500 | 0 | The smallest size for text that carries the message |
| Eyebrow | 28 | 40 | 700 | +0.24em, uppercase | A small label above a title |

- For another resolution, multiply by the short side of the frame over 1080. A 4K frame doubles everything.

- A square frame is narrow, so use the portrait column.

- Portrait is a different design, not a resize. Its big sizes come down so they fit the width. Its small sizes go up because a phone is held far away. In one test at 1080x1920, 26 px was a smudge, 30 whispered, 34 read as secondary and 40 read as a line meant to be read.

- Exempt from the floor: axis numbers, code and table cells, where shape and position help the reader.

**Every line needs a width limit too.** A 45-character subtitle at 40 px measured 1,055 px wide in a 1,080 px frame, 12 px from the edge. Use `maxWidth`, and measure the longest line on a still. A camera push moves things outward too, so leave room for it.

**Line breaks.** Read each one. Never leave one or two words alone on a line, or split a first name from a last name, "the" from its noun, or "1." from its step. Fix these with a non-breaking space (`{'a\u00A0b'}` in JSX). In a plain attribute like `text="a\u00A0b"` the screen shows the letters.

**Numbers.** A number that counts up or sits in a centred ring needs `fontVariantNumeric: 'tabular-nums lining-nums'`, or it jitters and sits off centre.

**Text on footage or images.** Aim for at least 4.5:1 contrast against the worst pixel the text covers across the whole shot, not the average and not the first frame. In order of preference: a soft dark gradient over the lower part, such as `linear-gradient(to top, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.45) 28%, transparent 60%)`; a blurred pill behind the text; a hard outline about 15% of the font size. A drop shadow alone fails when the picture is busy.

### Step 4. Keep things in the safe area

The safe area is the part of the frame that is sure to be seen, clear of player controls and edges. Starting values:

- **Landscape:** keep anything that must be read 84 px inside a 1920x1080 frame. Only full-screen grounds and wipes cross it. A slow camera push crops too: a scale of 1.03 moves 29 px off each side of 1920.

- **YouTube captions:** at least 108 px above the bottom, clear of the player's control bar.

- **Portrait, 1080x1920:** platforms draw their own buttons and text over the video. These are the areas text may occupy. They are starting points and they change. The first three rows were measured pixel by pixel from each platform's official ad template in September 2026, so check the current ones before a big batch. The last row is one person's judgement, not a measurement.

| profile | text stays inside | where it comes from |
|---|---|---|
| YouTube Shorts | x 48 to 888, y 288 to 1248 | Google's overlay template |
| TikTok In-Feed | x 120 to 960, y 240 to 1260, but not x 780 to 960 where y is 840 to 1260 (the button stack) | TikTok Ads Manager's file, April 2025 |
| Instagram and Facebook Reels | x 65 to 1015, y 269 to 1248 | Meta's Ads Guide |
| **ad** | x 120 to 888, y 288 to 1248, and x at most 780 where y is over 840 | all three at once. Use it for anything that may be boosted |
| **organic** | x 60 to 888, y 240 to 1490 | set from a director's notes, for posts that are not boosted. y of 240 or more also keeps text inside Instagram's 3:4 grid crop |

The two differ most at the bottom: captions end by y 1248 in `ad` and by y 1490 in `organic`.

- **A 4:5 feed crop** of a 1080x1920 master keeps y from 285 to 1635. Keep what must survive both inside that band and inside the row you chose above.

- **Anything with captions:** keep the lowest label of a drawing out of the bottom fifth of the frame.

### Step 5. Choose colour

- **One accent per shot.** One strong colour tells the eye where to go. A second colour only works as a pair with a meaning: before and after, gain and loss.

- **Colour means something.** If red means "wrong" in one shot, do not use it as decoration in the next.

- **Check contrast with numbers, not by eye.**

Save this as `contrast.mjs`:
```js
// WCAG contrast ratio between pairs of colours.
//   node contrast.mjs '#1F2430' '#FBF7EF' ['#C2410C' '#FBF7EF' ...]
// 4.5 or more is the usual target for normal text, 3 or more for large text.
const channel = (v) => {
	const c = v / 255;
	return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};
const luminance = (hex) => {
	const n = Number.parseInt(hex.replace('#', ''), 16);
	const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
	return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
};
const args = process.argv.slice(2);
if (args.length < 2 || args.length % 2 === 1) {
	console.error("Usage: node contrast.mjs '#text' '#ground' ['#text2' '#ground2' ...]");
	process.exit(1);
}
for (let i = 0; i < args.length; i += 2) {
	const [a, b] = [luminance(args[i]), luminance(args[i + 1])];
	const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
	const verdict = ratio >= 4.5 ? 'fine for any text' : ratio >= 3 ? 'large text only' : 'too low';
	console.log(`${args[i]} on ${args[i + 1]}: ${ratio.toFixed(2)}:1  ${verdict}`);
}
```

```bash
node contrast.mjs '#1F2430' '#FBF7EF' '#C2410C' '#FBF7EF'
```

It prints (tested on a Mac, not on Linux):

```
#1F2430 on #FBF7EF: 14.52:1  fine for any text
#C2410C on #FBF7EF: 4.85:1  fine for any text
```

The looks in the example above all measured 4.8:1 or better. White on a pale orange, by contrast, measured 1.69:1: too low. Aim for 4.5:1 for normal text and 3:1 for large text.

- **Look on a real screen.** A colour that reads fine on a white sheet can read dark in a graded picture. Judge colours on a still of the actual shot.

### Step 6. One idea per screen

Decide the one thing the viewer should notice, and build the frame around it.

- **Hierarchy.** Biggest and strongest is the message. Everything else is clearly smaller or quieter. If two things compete, one is in the wrong shot.

- **Every line on screen is a whole sentence, or a clear label.** A viewer reads it once, at a glance, while listening.

- **Show it, then name it.** A title should say what is inside, rather than tease.

- **The silent test.** Turn off the sound and cover the captions. Write one line about what the picture alone says. If the answer is "some text", the shot is not designed yet.

- **Fewer items.** More than about four items on one screen: split the beat.

### Step 7. Decide when a diagram beats a sentence

A sentence on screen repeats the voice. A diagram adds something. Find the verb in the narration line, then draw that.

| The line says | Show |
|---|---|
| "These two are the same except for one thing" | The same shape twice, identical but for the one difference. Different colours would read as two different things |
| "It moved from here to there" | One object in two states: a faded ghost where it left, an arrow, the same object solid where it arrived |
| "Not this, but that" | Two identical cards on one line. The strike lands on the first, and the second holds the replacement. Make the strike heavy or diagonal: one thin line reads as a divider |
| "Only four" | The number as a quantity you can count: four blocks filling a box, a fifth bounced off it. A number written as a word never shows four of anything |
| "Three moves" | Three items fixed to one object, such as a staircase, one per step, and every one stays on screen |
| A real amount to compare | A chart drawn to scale. Never draw figures by feel |
| Steps, a cycle, a hierarchy | Arrows claim a direction, a ring claims a cycle, a pie claims the parts make a whole. Pick the shape that says the same as the line |

Rules these came from, each from judging real frames:

- The frame shows an **event**, something landing or arriving, not a state. A still arrangement scored lower.

- The verb must match the picture. "You build the scaffold" over a finished scaffold asks for the act of building.

- **Never open on an empty canvas.** Put the first ink on screen within about 4 frames of the cut.

- Icons under about 100 px turn to mush at 1080p.

- Reveal one item at a time, at least 0.8 s apart, each on its phrase.

Add a person only when the point is human. If you could delete the person and still make the point, use a diagram.

### Step 8. Time the motion

At 30 frames a second, starting values:

| Kind | Frames | For |
|---|---|---|
| Small | 6 to 10 | A tick, a digit flip, a chip |
| Standard | 15 to 20 | A card entering, a bar growing |
| Big | 30 to 45 | A title, a camera push only |
| Background | 90 or more, looping | A slow grid or drift |

A routine element taking over 20 frames, or a fade near a second, looks slow.

**Easing,** the shape of a move over time:

```ts
const SETTLE = Easing.bezier(0.16, 1, 0.3, 1); // the default entrance: fast start, soft stop
const GLIDE = Easing.bezier(0.22, 1, 0.36, 1); // softer, for long travel
const SWEEP = Easing.bezier(0.65, 0, 0.35, 1); // an on-screen move from A to B
const LEAVE = Easing.bezier(0.5, 0, 0.75, 0); // exits only
```

- An entrance that starts slow or moves at constant speed feels weightless, so use `SETTLE` or `GLIDE`.

- An exit is about 20% shorter than its entrance.

- `SETTLE` is at 83% a quarter of the way through (re-measured on Remotion 4.0.541). A frame from the middle of the move already looks finished, so check frames from its first quarter.

- Nothing scales from 0. Start at 0.92 to 0.97 rising, or 1.04 to 1.08 settling.

- Clamp both ends of every `interpolate()`.

**Springs.** Always pass `spring()` a config. Its default bounce is a sure sign of an unstyled video. Measured at 30 frames a second on Remotion 4.0.541:

| Config | Overshoot | Frames to settle |
|---|---|---|
| Default | 16.3% | 28 |
| `{damping: 14, stiffness: 180, mass: 0.6}` | 5.6% | 12 |
| `{damping: 20, stiffness: 165, mass: 1}` | 2.0% | 17 |
| `{damping: 24, stiffness: 155, mass: 1}` | 0% | 17 |
| `{damping: 200}` | 0% | 23 |

Use no overshoot, or at most about 7%, and on at most one thing in a frame.

**Stagger,** the gap between things arriving:

- Letters and particles: 2 to 3 frames apart, the whole run within 12 frames.

- Cards and list items: 4 to 8 frames apart. Past about 8 items, group them.

- Two ideas in one shot: at least 24 frames apart. A payoff line gets about 36 frames alone.

**One thing moves at a time.** In any short window, one property carries the motion. Everything else moves at most a tenth as much.

**Camera moves,** starting values:

| Move | Scale | Length | Curve |
|---|---|---|---|
| Slow creep | About 1.2% a second | The whole shot | Linear: an eased camera move reads as a stumble |
| Slow pull back | 1.10 to 1.00 | 3 to 4 s | Linear |
| Emphasis punch | 1.00 to 1.12 | 6 to 8 frames | `SETTLE`, ending on the stressed syllable |

Set `transformOrigin` on the subject, not the frame centre. Stay at or below about 1.35 times on 1080p footage in a 1080p frame, or it goes soft. Do not fade between a light ground and a dark one: cut, or wipe.

### Step 9. Pace it, and hold for the right length

**Length from words.** Narration runs at about 135 to 160 words a minute in measured scripts. A starting point of about 144 suits most videos, and about 180 can suit a short intro of 2 to 3 minutes. Ask.

**How long may a picture stand still?** These are judgements:

- Short social video: no picture still for over about 4 s.

- A narrated lesson: a picture changing every 6 to 9 s reads calm. One card for 15 to 20 s while the narrator moves on does not.

- Fix a long hold with something new on the words: a card, a diagram step, an earlier cut. A drift or a zoom only moves pixels, and the viewer still waits.

- A card held under speech can be right. Three authors' videos that looked fine to them spent a third to two thirds of their time on a stopped picture, so measure as well as look.

**Holds at a boundary.** Start from a pause of about 10 frames: 24 when the topic changes, 42 at a new section. Add about 24 after a reveal, and take off about 6 between list items. Stay within 8 to 150 frames. Up to 18 frames, use a hard cut. For 19 to 40, a short fade or push.

**Captions.** Page by meaning. At most about 17 characters a second, at most 42 characters a line, two lines at most. A page stays about 12 frames after its last word, then clears.

**Do not end on the last syllable.** A video that stops half a second after the final word feels cut off. Hold the last shot about 2.5 s, with any music fading under it. Choose a last shot worth reading.

**Keep something happening in long videos.** Aim for a designed beat (a card, a quote, a change of camera) at least every 90 s in a long video, and about one chapter card every 2 minutes.

### Step 10. The highlight rule

**A highlight must not arrive before the narrator names it.** If a box lights up, then the voice says what it is, the picture has given away the line, and viewers read it as a spoiler. A real review caught this.

| Thing | When it arrives |
|---|---|
| A word lit in a caption | On that word's start frame, never earlier |
| A highlight, an underline, a strike | On the frame the word is said |
| A line of designed text | It may lead its voice by 0.2 to 0.5 s, and must never arrive late |
| A sound effect | 1 to 3 frames before the event it marks |

Tie these to the voice's word timings rather than typed frames. Then a new voice moves them with it.

### Step 11. Avoid what looks machine-made

These are judgement calls from looking at many videos. Some are fine on purpose. Ask the user. Be suspicious when you reach for these out of habit:

- A purple-to-blue gradient on everything, glowing edges or neon on dark

- Frosted glass cards, floating shapes and particles with no meaning

- Everything centred, everything fading up in the same way, at the same speed

- The default spring bounce on every element

- Emoji as bullet points, or an icon beside every line

- A title that teases, a slogan, or a dramatic fragment instead of a sentence

- Text inside AI-generated images: it warps. Set all words in real type

- A drifting background that makes a finished frame look alive

- Three cards in a row for everything, whatever the idea

A plain, confident frame with one idea, real type and one colour often looks more designed than any of these.

## How to talk to the user

- Use plain words. "The text is too close to the edge" beats "the safe area is violated".

- Ask one question at a time, with a recommendation. For example: "I made three looks from your script. I recommend the first, because your audience reads these on laptops in daylight and it stays clear. Which do you like? You can also send me a video you like and I will match it."

- Show stills, not words. Pause for their choice before you build all the scenes.

- When they say "make it pop" or "it feels cheap", ask for an example, or offer two versions of one frame and let them point.

- Tell them plainly when a choice has a cost, such as low contrast or very small text, then let them decide. It is their video.

- Say every number is a starting point. If they want something else, do it.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| Text is in a serif font you did not choose | The font was not loaded, with no error | Load it, and look at a still |
| An error with the words `exceeded rendering` and `Fetching Inter font`, or `net::ERR_CERT_AUTHORITY_INVALID` | Chrome cannot load Google Fonts at render time. In a cloud session it refuses the hosts through the proxy, even though `curl` works | Use font files from `@fontsource` with `@remotion/fonts` |
| Any other error with the words `exceeded rendering`, on a busy machine | A frame took longer than the time limit | Pass `--timeout=120000` to start, and read the rest of the error |
| `Could not find a tsconfig.json file in your project` | No `tsconfig.json` | Add it |
| `inputRange must contain only finite numbers, but got [0,Infinity]` | `Infinity` in `interpolate` | Use the real last frame |
| The screen shows `\u00A0` | An escape in a plain attribute | Use `text={'a\u00A0b'}` |
| A move looks finished in every still | A strong ease-out is nearly done early | Check frames from its first quarter |
| The frame flashes on a cut | The next shot opens empty | Start it a few frames early, with `<Sequence from={-8}>` inside the cut |
| A slow push cuts off a word by its end | The push crops the frame | Add room for the largest scale it reaches |
| Everything looks slow | Routine moves are over 20 frames | Shorten them |
| It looks like a slide deck | The picture stops changing | Add a beat on the words, or cut sooner |
| A number jitters while counting | Digits have different widths | `fontVariantNumeric: 'tabular-nums lining-nums'` |
| A fading text flickers between frames, or the look differs between renders | `Math.random`, a timer or CSS animation | Drive everything from `useCurrentFrame()`. Use `random('seed')` |

## How to check it worked

Numbers help, but this is a matter of looking:

1. Look at a still of every shot, at full size and at thumbnail size. Can you read it at a glance? Does it say one thing?

2. Draw the safe area on your stills and check that everything that must be read sits inside it, including the largest scale of any camera push.

3. Run `contrast.mjs` on each text colour and its ground.

4. Look at a whole render as a contact sheet at 2 frames a second: `ffmpeg -v error -y -i out/x.mp4 -vf "fps=2,scale=460:-1,tile=8x7" out/contact-%02d.png`. A run of near-identical tiles is a shot with nothing to do. This needs a full ffmpeg, as `npx remotion ffmpeg` has no `tile` filter.

5. Check each highlight against the frame its word is said.

6. Run the silent test on each shot.

7. Show the user. A file check cannot tell you the video is good, and only they can say whether it is the look they wanted.
