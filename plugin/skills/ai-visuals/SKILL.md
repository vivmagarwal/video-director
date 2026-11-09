---
name: ai-visuals
description: Make images and short clips with public AI generators for use as video backgrounds, with cost approval, prompts, measuring, provenance notes and licence rules. Use it when a video needs a generated room, place or texture behind elements.
---
# AI visuals for video backgrounds

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It shows you how to get a good background from an AI image or video generator, and put it to use in a video without trouble. It covers:

- choosing between a still, a slow move on a still, and a generated clip

- keys, network checks and cost approval

- prompts for an empty room or background, with no people and no text

- looking at and measuring each result

- slow camera moves on a still, in Remotion

- a provenance note for each file: prompt, model, cost and date

- licence and likeness rules

Calls here cost real money, so you always say the cost and get an OK first. **The script in this file has not been run against a paid API.** It was written from the provider's public documentation on 2026-11-09.

## When to use it (and when not to)

Use it for backgrounds: a room, a place, a texture, an abstract ground, when nothing free is good enough.

Try these first, as they are free, exact and can be changed in a line:

1. A plain colour or simple shapes drawn in code. For a short point, that is often enough.

2. A diagram, if the point is about a quantity, a process or a relationship.

3. Stock images or video from a public library, once you have checked the licence.

4. The user's own photos or footage.

Reach for generation only when the video needs a specific place that those cannot give. One good still can carry a lot.

## What you need before you start

| Need | How to check | If it is missing |
|---|---|---|
| A provider key in the environment | `test -n "$GEMINI_API_KEY" && echo set` (prints `set`, never the key) | Ask the user to add it to the session's environment. Never ask them to paste it in chat, and never write it to a file or print it |
| The provider's host is reachable | See below | Ask the user to allow it in the session's cloud environment menu: Edit, then Network access |
| Python 3 | `python3 --version` | Install it |
| Pillow and numpy, for measuring | `python3 -c "import PIL, numpy"` | `python3 -m venv .ai && .ai/bin/pip install -q pillow numpy` |
| Full ffmpeg, for clips | `ffmpeg -version` | `sudo apt-get install -y ffmpeg`. If refused, `.ai/bin/pip install -q imageio-ffmpeg`, then `ln -sf "$(.ai/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" .ai/bin/ffmpeg` and `export PATH="$PWD/.ai/bin:$PATH"`. That build has no `ffprobe`. In a Remotion project use `npx remotion ffprobe` |
| A Remotion project, for the slow move | `npx remotion versions` | See "A minimal project" in step 6 |

**Test reachability first, before you plan around a provider.** This costs nothing:

```bash
curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://generativelanguage.googleapis.com/v1beta/models
curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://api.openai.com/v1/models
```

A refusal is `CONNECT tunnel failed` or `Host not in allowlist`. Any other status means the host answered. With no key, expect a 401 or 403, which only means it asked for a key. (From a Mac on 2026-11-09, these printed 403 and 401.) In a cloud session the allowed hosts differ per environment and date. An earlier cloud session reached `generativelanguage.googleapis.com` and saw `openrouter.ai` refused. Test yours.

**Some example providers.** This is a floor. New ones appear all the time. Check current names and prices on each provider's own page.

| Provider | For | What its public pages said on 2026-11-09 |
|---|---|---|
| Google Gemini API | Images | `gemini-nano-banana-2.1` about $0.05 for 2K; `gemini-3.1-flash-image` about $0.10 for 2K; `gemini-3-pro-image` about $0.13 for 2K. No free tier for image models |
| Google Gemini API | Video | `gemini-omni-1.2-flash`: 3 to 15 s, about $0.07 a second at 720p, $0.104 at upscaled 1080p, makes its own audio. The older Veo preview models were listed as shut down in this API from 2026-10-22 |
| OpenAI | Images | `POST https://api.openai.com/v1/images/generations`; models named `gpt-image-2.5-sunburst` and `gpt-image-2.5-flare`, and 2.6 models; the image comes back as base64 in `data[0].b64_json`. Not tried here |
| Aggregators such as OpenRouter or fal | Many models, one key | An earlier project compared four video models from one still. Wan 2.7 gave real motion and a locked camera at native 1080p, about $0.10 a second. Kling v3.0 Std was the cheapest of the four at $0.084 a second but capped at 720p, and people drifted. Check today's list |

All Gemini images and videos carry SynthID, an invisible watermark that can be detected later.

## Steps

### Step 1. Save the scripts, then pick the cheapest thing that does the job

A `cd` may not carry over from one command to the next, so each block below starts with its own. Use your project's real full path in place of `/path/to/your-project`.

Copy this skill's files there, and do not retype long files. Files already there are kept.

```bash
mkdir -p /path/to/your-project
cd /path/to/your-project
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/ai-visuals"
cp -rn "$S/files/." . 2>/dev/null; test -e "gen-background.py" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

Now choose:

| Need | Use | Cost |
|---|---|---|
| A place behind your elements | One still | Cents for each take |
| The same, with some life | A slow camera move on the still (step 6) | Nothing more, and it re-times with the voice |
| The place itself must do something: a door opens, hands at work | A generated clip (step 7) | About $6 a finished minute in an earlier project, paid again whenever the script changes |

Why a clip comes last, from real work:

- **It cannot be re-timed.** A cut tied to a spoken phrase moves when you re-voice. A generated clip is a fixed length of fixed pixels. Re-voice, and you pay again.

- **It drifts** (step 7).

- **You cannot fix it.** If a wrong height is a number in your code, you change it. A clip that comes back wrong has only two options: pay again, or live with it.

- **It is a seam.** Clips can look different from everything around them.

A good limit: at most one clip in a video, 5 to 10 s, only where it really adds something.

### Step 2. Say the cost and get an OK

**Never make a paid call without a clear yes for that amount.** Say it like this:

> "I would like to make one background image with Gemini. It should cost about $0.05 a take. Some need two or three tries, so I would plan on about $0.15. May I go ahead?"

Say how many takes you plan. A wide of a whole room landed in one take in earlier work, but four takes of one close-up of two hands gave four different failures. Close-ups need more. Tell the user the running total as you go. An earlier project made six images for about $0.80 in all.

### Step 3. Write the prompt for an empty background

If things will sit on top, generate only the background. Do not ask for people or text. Everything that moves or must be read stays in your own composition, where you can change it.

Write three paragraphs, and keep them in a text file so you can reuse them:

**1. The style.** Be specific. Ask the user for this, and pass a sample if they have one. This one is an example, for one flat look:

> Flat 2D vector illustration in the style of a modern animated explainer video. Soft cel shading: each surface is one flat colour plus one slightly darker tone for shadow, with no gradients and no texture. Warm neutral room: cream walls and a warm wood floor. Accent colours are muted, at medium saturation. Lighting is soft and flat, from one implied source on the left. Clean and uncluttered. 16:9.

**2. The room, describing what you want on the floor.**

> Draw the room only: a back wall, a blank whiteboard, a window with soft daylight and furniture only along the back and side walls. The centre and lower third of the frame are clear empty floor, one even plain wood tone right up to the bottom edge. Camera at standing eye level.

**3. No text.**

> No text, no letters, no words, no numbers, no watermark and no signature anywhere. The whiteboard is completely blank.

The traps in this, each learned from a real image:

- **Keep the floor empty.** The empty floor is where your elements go. Furniture across the middle leaves nowhere to place anything.

- **Describe what you want. Do not name what you do not want.** "There is NO meeting table" drew the table's shadow in the middle of the floor. The model drew the shadow of the object it was told about. Google's own guide gives the same advice: describe the empty scene positively.

- **Name each blank object.** A bottle came back labelled "GLUE" although the prompt asked for no text. The cure was saying "the label is COMPLETELY BLANK" about that one object. Set all words in real type in your composition.

- **"Never black" can backfire.** Asked for no black outlines, a model drew one uniform dark brown line everywhere. What helped was saying how to separate shapes: "shapes are separated by colour, not by ink; any line is hairline-thin, in a slightly darker tone of the colour it borders". It helped but did not finish the job. Measure it.

- **One image is one camera angle forever.** You cannot turn around later. Decide the angle by asking what your widest shot must show.

**A second room in the same style.** Pass the first image as a reference, and keep every word of the prompt but the room paragraph. Add a line such as: "This is a different room in the same building on the same afternoon, drawn by the same hand. Copy from the reference, unchanged: the wall colour, the floor tone, the daylight direction, the line weight, the level of detail and the camera height." This worked twice in earlier work, and the wall and floor lines came back within 1% of the frame. A real reference picture carries a look far better than words can.

**If the user wants a certain look,** ask for a sample image and pass it as a reference. Offer two or three directions as cheap 1K takes before paying for 2K, and get an OK for that spend first.

### Step 4. Make one image

Save your prompt in `prompt.txt`, then save this script. It uses only the Python standard library. Its default mode shows the plan and the cost, and spends nothing.

`gen-background.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/gen-background.py (126 lines).
```

```bash
cd /path/to/your-project
python3 gen-background.py prompt.txt public/bg/room.png
```

That prints the plan and spends nothing. After the user agrees to the cost:

```bash
cd /path/to/your-project
python3 gen-background.py prompt.txt public/bg/room.png --yes
```

To seed from a sample: add `--ref public/bg/first-room.png`. For more detail: `--size 4K`, at a higher price.

**What was tested and what was not.** The real API was not called, so this script is **not run**. On a Mac, not on Linux, these were tested against a small local server standing in for the API: the plan with no spending, the missing-key message, the request's shape, a reply with an image, a reply with no image, an HTTP error and a refused connection. The key did not appear in the note. The request shape and the reply's `steps[].content[]` come from Google's public Interactions API pages. So expect that a field may have changed, and read any error it prints. An earlier cloud project used the older `generateContent` route with `gemini-3.1-flash-image`, and got 2752x1536 images in 15 to 20 s for about $0.13 a take. That route no longer appears on the image page, so it was not used here.

If the API has moved on, read its current page and fix the script. Google's image guide is linked from `https://aistudio.google.com`.

### Step 5. Look at it and measure it

Open the image with your own eyes, **at full size**. A small preview makes a flat picture look heavily inked. One good image was nearly thrown away because of a thumbnail. Check:

- Is any text, signature or watermark in it? Look at boards, books and bottles.

- Are there people you did not ask for, or faces in pictures on the wall?

- Is the floor clear where your elements will go?

- Does it match the user's look?

Show the user. **A person reviews a background before anything is built on it,** because every position later is measured from it. A replacement after that means measuring it all again.

Then measure. Do not eyeball positions.

`measure-image.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/measure-image.py (47 lines).
```

```bash
cd /path/to/your-project
.ai/bin/python measure-image.py public/bg/room.png
```

On a test image of 2752x1536 it printed:

```
size: 2752x1536, aspect 1.7917 (frame 1.7778)
objectFit cover: scale 0.7031, loses 7.5 px each side and 0.0 px top and bottom
note: a slow push-in stays sharp up to a scale of about 1.42.
near-black pixels: 0.01%
```

What to do with the numbers:

- **Size and aspect.** An image may come back double the size you expected, or not exactly 16:9. Use `objectFit: 'cover'`, as `contain` leaves bars. Scale an oversized image down to match any sibling.

- **The flat runs** show where the wall meets the floor. Flat art has hard edges, so each line shows up as a run boundary. Run it at the column where something will go, using `--column=0.3`. Place anything on the floor by these numbers, not by feel. In earlier work, things placed by eye ended up on the wall.

- **Prompts do not set geometry.** The horizon you asked for is not always the one you get, so measure.

- The script was tested on a Mac, not on Linux, on a test pattern, not on a real AI image.

**To make things on top look like they belong:**

- A soft shadow under anything you place on the floor, as wide as its base. Without one it looks like a sticker.

- Keep the scale believable against the drawn furniture.

- A little blur on the background (2 px or so) on close shots, so that the subject stands out.

- The same colour treatment over the whole shot, background and elements together.

- Keep what you place, and its shadow, above the caption band, if there are captions.

### Step 6. Slow camera moves on a still

This is the cheap way to bring a still to life. It costs nothing per second and re-times with the voice.

**A minimal project,** if you do not have one:

```bash
cd /path/to/your-project
npm init -y
npm pkg set type=module
npm i --save-exact remotion @remotion/cli react react-dom
npx remotion browser ensure
mkdir -p src out public/bg
```

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

Without `tsconfig.json`, every command stops with `Could not find a tsconfig.json file in your project`. If `browser ensure` is refused (`CONNECT tunnel failed, response 403` or `Host not in allowlist`), on Linux x64 run these lines. `remotion.config.ts` then finds this Chrome by itself. The comment in that file names `setup-video.sh`, a script this guide does not use: these lines put Chrome in the same place. The same route, with the Mac build, was tested on a Mac. The Linux build was not tested.

```bash
cd /path/to/your-project
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

Tell the user once: Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees. Other companies need a company licence. See `node_modules/remotion/LICENSE.md` or remotion.dev/license.

**The move:**

Save this as `src/SlowMove.tsx`:
```tsx
import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * A slow camera move on one still. Costs nothing per second and re-times with the voice.
 * `from` and `to` are scales. Keep both above 1 when you also pan, or the frame edge shows.
 * Linear on purpose: an eased camera move reads as a stumble.
 */
export const SlowMove: React.FC<{
	readonly src: string;
	readonly from?: number;
	readonly to?: number;
	readonly panX?: number; // pixels the picture travels sideways over the whole shot
	readonly originX?: string; // put this on the subject, not the frame centre
	readonly originY?: string;
	readonly blur?: number; // pixels of soft focus, so things on top stand out
}> = ({src, from = 1.04, to = 1.1, panX = 0, originX = '50%', originY = '50%', blur = 0}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const p = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	return (
		<AbsoluteFill style={{overflow: 'hidden'}}>
			<Img
				src={staticFile(src)}
				style={{
					filter: blur ? `blur(${blur}px)` : undefined,
					height: '100%',
					objectFit: 'cover',
					transform: `translateX(${panX * (p - 0.5)}px) scale(${from + (to - from) * p})`,
					transformOrigin: `${originX} ${originY}`,
					width: '100%',
				}}
			/>
		</AbsoluteFill>
	);
};
```

**A background with something on top,** registered in its own entry file. Replace the orange block with your own element.

Save this as `src/bg-entry.tsx`:
```tsx
import React from 'react';
import {AbsoluteFill, Composition, registerRoot} from 'remotion';
import {SlowMove} from './SlowMove';

/** A background with something composited on top, and a soft contact shadow under it. */
const Shot: React.FC = () => (
	<AbsoluteFill>
		<SlowMove src="bg/room.png" from={1.04} to={1.1} originX="60%" originY="55%" blur={2} />
		<AbsoluteFill style={{alignItems: 'flex-end', justifyContent: 'flex-end', padding: '0 220px 150px'}}>
			<div
				style={{
					background: 'radial-gradient(closest-side, rgba(0,0,0,0.35), transparent)',
					bottom: 130,
					height: 50,
					position: 'absolute',
					right: 190,
					width: 400,
				}}
			/>
			<div style={{background: '#C2410C', borderRadius: 24, height: 420, width: 340}} />
		</AbsoluteFill>
	</AbsoluteFill>
);

registerRoot(() => (
	<Composition id="bg" component={Shot} durationInFrames={150} fps={30} height={1080} width={1920} />
));
```

```bash
cd /path/to/your-project
npx remotion still src/bg-entry.tsx bg out/first.png --frame=0
npx remotion still src/bg-entry.tsx bg out/last.png --frame=149
```

Rendered on a Mac on 2026-11-09, not on Linux, with a test pattern as the background. Compare the first and last frames: nothing should show past the edge of the picture, and the element on top should stay put. Look at the image's edges at the largest scale.

Starting values: about 1.2% scale a second, linear, as an eased camera move reads as a stumble. Alternate direction from shot to shot. Set the origin on the subject. Keep both ends above 1.0 when you pan.

Elements on top do not follow the move unless you put them inside the same transform. Keep moves small when something sits on the picture, or move both together.

### Step 7. A generated clip, only when you need one

**Do not let a clip drift under composited elements.** Even when told not to move the camera, generated clips moved. In earlier work, the border drifted about 2 to 5 px from the first frame. Small, never zero. So anything you lay on top, such as something placed on the floor, will appear to slide. And the clip cannot be re-timed to a new voice.

So use a clip full frame with nothing composited on it, or lay on things that do not need to stick to the picture, such as a title. If something must stay locked to the room, use a still.

Rules from real runs:

- **Seed it from a still you approved.** Pass a frame in, and ask only for movement. Passing a real frame carries the palette and light far better than describing them. Crop any captions off first: a model will warp type.

- **Review the still before you animate it.** In an earlier project a clip cost about three times the still, and every defect in the still is still there afterwards, moving.

- **Keep it short and simple.** A clip of two hands and one object held steady for 5 s. A busy room lost two people and changed two objects in the same 5 s. Three to four seconds is safer.

- **Ask for less motion than you want,** then say what must not change. The second half is longer than you expect:

  > Gentle, small movement, nothing more. Light shifts slowly across the floor. THE CAMERA DOES NOT MOVE AT ALL: no pan, no zoom, no push, no drift. The picture stays exactly as it is: the same style, the same furniture in the same places, the same colours. Do not add or remove anything. Do not add text, letters or numbers.

- **Ask for 1080p, not a lower size.** One pair of runs suggested low resolution was less stable too, though one pair cannot prove it.

- **Do not rely on a model to add something that must be seen.** Asked for someone crossing out a sentence, one take drew the line at 0.5 s and erased it by 2 s. Draw anything the story needs in your own code.

- **A generated person is a different person in each shot.** Do not use one the viewer must recognise again. Keep to rooms, hands, or people far away.

- **Turn the sound down or strip it.** Some models add their own audio. Use `muted` on `<OffthreadVideo>`, or remove it: `ffmpeg -i clip.mp4 -an -c:v copy clip-silent.mp4`.

**Measure every clip:**

`clip-drift.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/clip-drift.py (70 lines).
```

```bash
cd /path/to/your-project
.ai/bin/python clip-drift.py public/bg/clip.mp4
```

Tested on a Mac, not on Linux, on two made-up clips: one with a known 6 px sideways slide, where it read 6.0 px, and one locked, where it read 0.0 px. It was not tried on a real generated clip. It searches for whole pixels, so 1.7 px may read as 2. Then open frames from 0 s, the middle and the end, and compare them: are the people, style and camera where they started? Look at the last frames too: decay usually shows at the tail.

For the clip's API, read the provider's current page. Keep the same habits as the image script: show the cost first, run only after an OK, and write a note. This skill has no clip script, as none could be tested without paying.

### Step 8. Keep a provenance note for each file

Each generated file needs a record of where it came from: prompt, model, cost, date. You will need these to make another in the same style, and to answer "may we use this?". `gen-background.py` writes one beside each image as `<image>.json`. For anything else, write one by hand:

```json
{
  "file": "public/bg/clip.mp4",
  "prompt": "Gentle, small movement, nothing more...",
  "model": "the exact model name",
  "provider": "the service used",
  "date": "2026-11-09",
  "cost_usd_estimate": 0.70,
  "seed_image": "public/bg/room.png",
  "takes": 2,
  "approved_by": "the user, in their words and with the date"
}
```

Commit these notes, and the prompts, to git. Commit the images if they are small: GitHub refuses a file over 100 MB, and a cloud disk can be lost, so ask the user where to keep larger files. Rejected takes count toward the cost, so record them too.

### Step 9. Licence and likeness

Rules to follow, and to tell the user about. This is not legal advice. For a commercial use, or anything risky, ask them to check.

- **Read the provider's terms for this use.** Google's terms for the Gemini API (`https://ai.google.dev/terms`) say it does not claim ownership of what you generate, also that it may generate the same or similar for others, and that you are responsible for how you use it. Terms differ by provider and change over time. Whether generated images can be protected by copyright also varies by country.

- **Real people.** Do not generate a real, recognisable person, living or dead, without their permission, and never to show them doing or saying something they did not. That includes uploading someone's photo as a reference.

- **Brands and characters.** Keep logos, product designs and well-known characters out of the prompt, unless the user owns them.

- **Named artists.** Do not ask for "in the style of" a living artist by name. Describe the qualities instead.

- **Be honest.** Do not present a generated place, person or event as real footage in a way that could mislead. Some platforms ask you to label realistic AI content. Check where the video will be published.

- **Paid and free tiers can treat your data differently.** Ask before you send the user's private images as a reference, and check whether the provider keeps or trains on them.

- **Stock and reference files have their own licences.** Check them before you use them as a reference too.

## How to talk to the user

- Use plain words: "a background picture", "a short moving clip". Say what a term means the first time.

- Ask one question at a time, with a recommendation: "I recommend one still with a slow camera move, because it costs about $0.05 and it stays in sync if you re-record the voice. A moving clip would cost about $0.70 for 10 s and cannot be re-timed. Which would you like?"

- Before any paid call: what it is, how many takes, the cost, then wait for a yes. A yes covers that amount only. Ask again if it runs over.

- Ask for their taste: a sample image, brand colours, a place they have in mind. Offer two or three directions. Everything here about style is only an example.

- Show each result before you build on it. Say what you see, including faults.

- If you need a key, ask them to add it to the environment. Do not take it in chat.

- Tell them what was not tested, including that the script here has not been run against the paid API.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `GEMINI_API_KEY is not set` | No key in the environment | Ask the user to add it to the session environment |
| `CONNECT tunnel failed, response 403` or `Host not in allowlist` | The proxy refused the host | Ask the user to allow it: cloud environment menu, Edit, then Network access |
| `Could not reach the API: ...` | No network to it | Test it with curl, as above |
| `HTTP 400: ...` | A bad field or model name, or a lowercase `2k` | Read the message and the provider's current page. The image size must use an uppercase K |
| `HTTP 401` or `403` from the provider | Bad key, or no billing on it. Image models have no free tier | Ask the user to check the key and billing |
| `HTTP 429: ...` | Over quota or rate | Wait, or ask the user. Do not retry in a tight loop, as each success costs money |
| `No image came back. Status: ...` | A safety block, or the model answered in words | Read the reply, and rephrase. Do not add a person or a brand |
| Text or a label in the image | The model added lettering | Say that specific object is completely blank, and try again. Or crop or cover it |
| A shadow with nothing above it | You named an object as absent | Describe the empty floor instead |
| Heavy dark outlines | Models often ink the edges | Add the line rule from step 3, and judge at full size first |
| The image is not 16:9, or it is twice as large | Models differ | Use `objectFit: 'cover'`, and scale down |
| Something on top seems to slide on a clip | Clip drift | Use a still, or nothing locked on top |
| A frame times out with the words `exceeded rendering` | A frame took longer than the time limit | Pass `--timeout=120000` to start, and read the rest of the error |
| The picture edge shows during a move | A scale below 1, or a pan past the overscan | Keep both scales above 1, and check the last frame |
| The image goes soft during a push | Scaled past its real size | Stay under the scale `measure-image.py` prints |
| A clip has sound you did not ask for | Some models add it | `muted`, or strip it with `-an` |

## How to check it worked

1. Open each file at full size with your own eyes, and show the user.

2. Run `measure-image.py` or `clip-drift.py`, and act on the numbers.

3. Render stills of the shot with your elements on it, and look. Does everything sit where it should? Is any text clear?

4. For a move or a clip, look at the first, middle and last frames. For a whole render, look at a contact sheet: `ffmpeg -v error -y -i out/x.mp4 -vf "fps=2,scale=460:-1,tile=8x7" out/contact-%02d.png`.

5. Check that each generated file has its note, with the prompt, model, cost and date.

6. Add up the real cost, and tell the user. The provider's billing page has the true figure. The script's number is an estimate.

A file check cannot tell you the video is good. Only your eyes and the user can say the picture is right.
