---
name: render-video
description: Turn a Remotion project into a finished MP4 in a Claude Code cloud container, without losing the render to a timeout, a full disk, a memory crash or a restart. Use when a project already works and you need the final file, especially for anything longer than a couple of minutes or anything with real footage.
---

# Render a video in the cloud

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It takes a Remotion project (Remotion writes videos as React code) and gives you a finished, checked MP4 in the user's hands. It holds its own setup, so nothing else is needed. It covers:

- Running a render so it outlives the tool's time limits.

- Bundling once. A bundle is the packed copy of your project that a render reads.

- Chunked rendering: a crash costs one chunk, not the whole film.

- Disk and memory limits, with the numbers that caused real failures.

- Setting the loudness, which is a normal last step.

- Delivering the film through a private page.

- Traps with colour tags, sound sync and machine differences.

## When to use it (and when not to)

Use it when the composition is ready and you want the final file.

Do not use it to design a video or to preview one idea. A single still is much faster for that:

```bash
npx remotion still src/index.ts my-film out/test.png --frame=120
```

For a batch of many videos at once you also need render locks and fingerprints, which this skill does not cover.

## What you need before you start

A Remotion project with a `package.json`. When this was written, a cloud session was a Linux x64 container: 4 cores, about 15 GB of memory, no swap, no GPU. The Bash tool stops a command at 10 minutes, and a background command stops at 2 hours. Bare `sleep` is blocked.

| Need | How to check | How to get it |
|---|---|---|
| node, npm | `node --version` | Ask the user if missing. |
| Remotion installed, all one version | `npx remotion versions` | The script below. |
| Chrome | `npx remotion browser ensure` | The script below, with a fallback. |
| ffmpeg with `tile`, `volumedetect`, `loudnorm` | The script below tests it | The script below. Falls back to `pip install imageio-ffmpeg`. |
| ffprobe | `ffprobe -version` | The script below. |
| Python 3 | `python3 --version` | Needed for the chunk script. |
| Free disk | `df -h .` | See "Disk" below. |
| The `Artifact` tool, for the delivery page | Cloud sessions have it | Step 11 uses it. |

Licence, if nobody has told the user yet: Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees; others need a company licence (remotion.dev/license).

No key is needed. No step here costs money. Networks differ per environment. A refusal is `CONNECT tunnel failed` or `Host not in allowlist`. Any other status means the host answered. To test one host:

```bash
curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://registry.npmjs.org/remotion
```

The user can allow hosts in the session's cloud environment menu: **Edit**, then **Network access**.

## Steps

`my-video` below stands for your project folder. A `cd` may not carry over from one Bash call to the next, so each step's commands start with their own.

### First, save the files in this guide

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd my-video
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/render-video"
cp -rn "$S/files/." . 2>/dev/null; test -e "remotion.config.ts" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It saves `prep-render.sh`, `remotion.config.ts`, `render-chunks.py`, `master-audio.py`, `split-for-artifact.py` and `delivery-page.html`.

### Step 1. Prepare the machine

A fresh container has no `node_modules` and may lack tools. A restart can take them away again. The script below is safe to run again.

This config sets how Chrome draws and finds the Chrome the fallback downloads. If `remotion.config.ts` already exists, keep it and add only the lines it lacks.

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

`prep-render.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/prep-render.sh (92 lines).
```

```bash
cd my-video && bash prep-render.sh
```

Tested on a Mac at Remotion 4.0.541, on the normal route and with `FORCE_FALLBACKS=1`. **Not run on Linux.** It needs no `--binaries-directory` and no separate compositor download, because npm brings the right compositor (Remotion's native render helper) by itself on Linux.

### Step 2. Check disk and memory before you start

```bash
cd my-video
df -h . ; free -g | head -2 ; du -sh public
```

Disk rule: **keep three times the working copies free (the media in `public/`), plus about four times the finished film.** The "Disk" section says why. Footage above 1080p needs the memory cap in Step 6.

### Step 3. Look at your footage, if you have any

A webcam file is not a camera file. One had a keyframe (a complete picture the video can jump to) only every 30 seconds, so a render would seek up to 750 frames for every frame it drew. Check:

```bash
cd my-video
ffprobe -v error -select_streams v -skip_frame nokey -show_entries frame=pts_time -of csv=p=0 public/clip.mp4 | head -5
```

If the numbers are more than a second or two apart, make a working copy with a keyframe every second. `-g` is your frame rate:

```bash
cd my-video
ffmpeg -i raw.mp4 -vf "scale=1280:720:flags=lanczos" -c:v libx264 -preset veryfast -crf 17 -g 25 -keyint_min 25 -sc_threshold 0 -pix_fmt yuv420p -c:a copy -movflags +faststart public/working.mp4
```

The size and frame rate here are examples. Keep what the job needs.

### Step 4. Bundle once, after every write to `public/` has finished

Each render given `src/index.ts` bundles again. Bundling once saves that time, and stills can use the same bundle.

```bash
cd my-video
pgrep -x ffmpeg || npx remotion bundle src/index.ts --out-dir=out/bundle
```

**Bundle only when nothing is writing into `public/`.** A bundle copies `public/` as it stands, so a file still being written goes in half-written. Every frame that touches it then fails with this, while the other frames render fine, which makes it look like a fault in the file:

```text
[mov,mp4,m4a,3gp,3g2,mj2 @ 0x12bf041d0] moov atom not found
```

(A moov atom is the index of an MP4. ffmpeg writes it last.) That exact message came back on 4.0.541 on a Mac from a cut-off file. If ffmpeg is still running, the command above prints its process id and does not bundle. Use `pgrep -x`, not `pgrep -f`, whose match on the full command line can find your own shell.

**Keep caches out of `public/`.** The bundle copies all of it: a 418 MB audio cache in there went into every bundle.

After you change code or `public/`, bundle again. An old bundle renders the old video without a word of warning.

### Step 5. Render a short test from the bundle

Render 2 seconds from the hardest part of the film, and look at it.

```bash
cd my-video
npx remotion render out/bundle my-film out/test.mp4 --frames=300-359 --concurrency=2 --offthreadvideo-cache-size-in-bytes=800000000 --overwrite
ffmpeg -v error -y -i out/test.mp4 -vf "fps=2,scale=480:-1,tile=2x2" -frames:v 1 out/test-sheet.png
```

Open `out/test-sheet.png` with the Read tool. Run the command from the project folder, so it reads `remotion.config.ts`. List your composition ids with `npx remotion compositions out/bundle`.

### Step 6. Render the whole film, detached

**Under about 10 minutes of expected work, a single render is fine.** Still run it in the background, because the Bash tool stops a command at 10 minutes. In the Bash tool, set `run_in_background: true` and `timeout: 7200000`:

```bash
cd my-video
npx remotion render out/bundle my-film out/my-film.mp4 --concurrency=2 --offthreadvideo-cache-size-in-bytes=800000000 --color-space=bt709 > out/render.log 2>&1; echo "EXIT $?" >> out/render.log
```

If the film holds real footage, add `--image-format=png`, so its colours stay right. "Colour tags" below says more.

**For anything longer, or with heavy footage, use chunks.** The script renders a set number of frames at a time, one process each. It keeps a chunk only if the frames and sound are all there. It resumes from the first missing chunk when you run it again, and joins the chunks at the end.

`render-chunks.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/render-chunks.py (222 lines).
```

Run it with `run_in_background: true` and `timeout: 7200000`:

```bash
cd my-video
python3 render-chunks.py out/bundle my-film out/my-film.mp4 out/chunks/my-film -- \
  --concurrency=2 --offthreadvideo-cache-size-in-bytes=800000000 --color-space=bt709 > out/render.log 2>&1; echo "EXIT $?" >> out/render.log
```

For footage, add the memory cap. For example, a footage edit used these flags:

```bash
cd my-video
python3 render-chunks.py out/bundle my-film out/my-film.mp4 out/chunks/my-film -- \
  --concurrency=2 --crf=20 --color-space=bt709 --image-format=png \
  --offthreadvideo-cache-size-in-bytes=800000000 > out/render.log 2>&1; echo "EXIT $?" >> out/render.log
```

The options, all written with `=`:

- `--chunk=<frames>` sets the chunk size. The default of 3000 is two minutes at 25 frames a second.

- `--range=<first>-<last>` renders only those frames, for a teaser or a test.

- Everything after `--` goes to every chunk's render.

What was tested, on a Mac at 4.0.541, on a real small project (a 20-second 1080p composition with `<OffthreadVideo>`, a separate `<Audio>` track and text on top). **Not tested on Linux at this version.** An earlier version of this script rendered whole films in the cloud.

| Test | Result |
|---|---|
| Whole film in chunks | 600 of 600 frames, 20.000 s of picture and of sound |
| Same command again | Re-rendered nothing, finished in 4 s |
| A chunk cut short by hand | Only that chunk was rendered again |
| Script stopped with `kill -TERM` mid-chunk | Exit 143, no Chrome left, temp folder gone |
| Sound of joined chunks against one unbroken render | Byte-identical |
| A composition with no sound | Joined with a silent track, as it should |
| `--range=100-159` | 60 frames, 2.000 s |

### Step 7. Wait without blocking

Do not sit in a foreground call. The Bash tool tells you when a background command exits. To watch for it, run a Monitor until-loop, or a bounded check loop, on the file:

```bash
cd my-video
until grep -q '^EXIT ' out/render.log; do sleep 30; done
```

Read progress from the log's last lines. If you made the chunk log, `out/chunks/my-film/render.log` holds each render's own output.

### Step 8. If it stopped, resume

A background command stops after 30 minutes, or after up to 2 hours if you start it with `timeout: 7200000`. A restart kills everything, `nohup` included. How the tool ends a command at the limit was not measured, so first make sure nothing is left over:

```bash
pgrep -af '[r]emotion render' ; pgrep -af '[c]hrome-headless-shell'
```

If a render is left, stop it, the CLI first. Killing only its Chrome makes it start another.

```bash
pkill -f '[r]emotion render' ; pkill -f '[c]hrome-headless-shell'
```

The brackets matter: a plain `pkill -f "remotion render"` can match your own shell and kill it (exit 144 on Linux). Then run the exact same chunk command. If `out/bundle` or `node_modules` is gone, repeat Steps 1 and 4 first. If the source changed since the chunks were made, delete the work folder. The script keeps any chunk with the right frame count, old words and all.

### Step 9. Master the sound, after the final render

Mastering sets how loud the finished film sounds. It is a normal last step. Renderers do not set loudness for you: five narrated renders measured about -24 to -28 LUFS (LUFS is the unit for how loud a film sounds), and viewers reach for the volume at that level. Skip this only if the user has a reason, or the video has no sound at all.

Master once, on the final render. If you render again, master again, always from the render and never from a master.

Starting points, as a floor: -14 LUFS for YouTube and short social clips, -16 LUFS for podcasts or when the platform is unknown, peak -1.5 dBTP. Use what the user or the platform asks for. dBTP is the unit for how high the loudest moment reaches.

The script takes three passes. It measures, then applies one even gain when it can, then measures the result. It copies the picture and does not touch it.

`master-audio.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/master-audio.py (114 lines).
```

```bash
cd my-video
python3 master-audio.py out/my-film.mp4 --target=-14
```

The default target is -16, so leave out `--target` when the platform is unknown. It writes `out/my-film.mastered.mp4`. The `after` row is the number to report. Exit 1 means it missed the target by more than 1 LUFS. The file is still written, so read the numbers, then fix the mix or ask the user.

Tested on a Mac, on a 10-second render with a test tone and on a spoken track: both landed within 1 LUFS of the target, the decoded picture had the same MD5 before and after, and all four colour tags stayed. Both came back in `dynamic` mode, which rides the level, and the script prints which mode it used. **Not run on Linux.** Listen if you can, and tell the user you could not if you cannot: a container has no ears.

### Step 10. Check it

See "How to check it worked", on the mastered file.

### Step 11. Deliver it through a private page

Finished videos are not in git (`out/` is ignored, and GitHub refuses a file over 100 MB), so **until you deliver a film it exists only in this container, and a restart can take it.** Deliver soon.

The route is a private web page. You split the film into pieces and store them on the page. The user presses one button. Their browser fetches the pieces, checks each one, joins them, plays the film, and saves it as one normal MP4.

The limits, when this was written:

| Limit | Value | Checked |
|---|---|---|
| One stored piece | 20 MiB. The script makes 19 MiB pieces | The tool's own type file, November 2026 |
| One page's total store | 1 GiB (1,073,741,824 bytes) and 5,000 files | A real listing, November 2026 |
| Upload of pieces in one call | Up to 25 files | The tool's description, November 2026 |
| Saving in the Android app | 200 MiB | The tool's type file, November 2026 |

**Over 1 GiB?** Publish a second page and put part of the film on it.

**Split the film.** Keep the pieces inside your working folder, because a file outside it has to go in an upload call of its own. `out/` is the right place. A file under 20 MiB still works: it becomes one piece.

`split-for-artifact.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/split-for-artifact.py (48 lines).
```

```bash
cd my-video
python3 split-for-artifact.py out/my-film.mastered.mp4 out/my-film-pieces
```

**Publish the empty page first,** because the pieces need a page to live on. If the tool asks you to load its design or capability skills, do so. Keep this page's script and data blocks unchanged. You fill in only the `video-data` block, below.

`delivery-page.html`, which the copy step puts in your folder:

```html
# In this skill's files folder: files/delivery-page.html (305 lines).
```

```text
Artifact
  action: publish
  file_path: delivery-page.html
  icon: video
  capabilities: {"assets": {}, "downloads": true}
```

Keep the `url` in the result. The page's name comes from its `<title>` tag, so change that tag to a name of two to four words if you like.

**Upload the pieces.** Send at most 25 in one call, and make more calls if you need them. The result gives one `url` per piece, such as `/_blob/7db260ac...`. Use it exactly as given.

```text
Artifact
  action: publish
  url: <the page>
  asset: true
  file_paths: [out/my-film-pieces/part-01.mp4, out/my-film-pieces/part-02.mp4, ...]
```

**Fill in the data block.** Edit the `video-data` block in the page. `size` and `sha256` come from `pieces.json`, and the top-level `size` in that file is the whole film's size. Every field except `title` and `videos` can be left empty. `shape` is optional: `tall` for 9:16, `square` for 4:5, or leave it out for 16:9. This example is invented:

```json
{
	"title": "How the bridge was built",
	"intro": "Your 12-minute film. Press the button, watch it, and save it if you like it.",
	"meta": "12:04 · 1920×1080 · 30 fps",
	"videos": [
		{
			"label": "The full film",
			"filename": "how-the-bridge-was-built.mp4",
			"size": 39845888,
			"pieces": [
				{"url": "/_blob/7db260ac...", "size": 19922944, "sha256": "794caf1d..."},
				{"url": "/_blob/798cc9b4...", "size": 19922944, "sha256": "786de73f..."}
			]
		}
	],
	"chapters": [{"t": "0:00", "title": "The opening"}],
	"description": "Text to copy into a video site.",
	"changes": ["Cut 4 minutes of pauses."],
	"checks": ["Does the name at 3:10 sound right to you? I can't listen."]
}
```

**Publish again,** with the same file path. Do not pass `capabilities`; they carry forward.

**Check the store.** Each line of this listing shows a SHA-256. Compare each with `pieces.json`.

```text
Artifact  action: list  scope: assets  url: <the page>
```

**Send the link.** For example:

> Your video is ready: <link>
>
> Open it in your browser and press **Get the video**. When it has loaded it will play right there, and **Save to my device** gives you one normal MP4 file. I can't listen to sound here, so please play it with the sound on.

The page is private. Only the user and the people they share it with can open it. They use the page's **Share** menu for that.

What was tested: an earlier version of this page delivered a real 19-minute film, which played and saved as one 339 MB MP4. This exact version was tested on 9 November 2026 in headless Chrome against a stand-in for claude.ai. A page with two films, one of 1 piece and one of 8 pieces (156 MB), played both, and the saved files matched the originals exactly. Its pieces have been stored and checked on claude.ai, but its buttons have not been pressed there. Nothing here was run from a Linux container.

**A smaller copy,** only if the user wants one. A higher CRF number means a smaller file and lower quality, so step it from 23 to 25 to 27, and stop when the file is small enough. Look at the copy before you send it.

```bash
cd my-video
ffmpeg -v error -y -i out/my-film.mastered.mp4 -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart out/my-film.share.mp4 </dev/null
```

A file under 30 MiB can also go as a chat file with `SendUserFile`. If the user asks for Google Drive or another service they use, test that you can reach it first. That setup is not covered here.

## How many frames a second to expect

Measured on a 4-core cloud container, September and October 2026, on an older Remotion (4.0.523). **Not measured at the current version.** Your video's speed depends on what it draws, so time your own test from Step 5.

| What | Result |
|---|---|
| 1080p drawn scenes, 300 frames, default concurrency (2 of 4 cores) | 60 s, 5.0 frames a second |
| The same, `--concurrency=4` | 39 s, 7.8 frames a second |
| A 121-second film alone, 3,636 frames, chunked | 4.5 minutes, about 13 frames a second |
| A 141-second film alone, 4,243 frames, chunked | 5.9 minutes, about 12 frames a second |
| A 125-second film with other renders running, plus its checks | 952 s, about 4 frames a second |
| A 1080p footage edit with captions, 28,930 frames (19:17) | 42 minutes, 8 to 13 frames a second, 352 MB at `--crf=20` |
| Lesson videos with diagrams | 1.2 to 2.1 s of waiting per second of video |
| A still, with its bundle | 9 s |
| A still from a bundle | 3 to 5 s |
| `compositions` | 16 s |

So a render shares the 4 cores with whatever else runs. A film that takes 5 minutes alone can take three times that beside other work. Use `--concurrency=4` (the core count), and run one render at a time. Fewer is safer with heavy footage: the edit above used 3.

## Choosing how Chrome draws (GL)

| Setting | Use it for | Measured on the cloud container |
|---|---|---|
| `Config.setChromiumOpenGlRenderer('angle')` in `remotion.config.ts`, or `--gl=angle` | Everything by default: text, SVG, CSS, video | Works with no GPU. 24 frames a second on one simple film. Expect 5 to 13 on most films, as in the table above. |
| `--gl=swangle` | Only a scene that really uses WebGL (three.js, shaders, canvas effects) that fails on `angle` with `Error creating WebGL context`, or comes out blank | 5 frames a second on that simple film, 4.6 times slower. It painted a ghost image of a list item into whole renders, and stills did not show it. |

After any `swangle` render, scan the finished file for ghosts. A still cannot catch this one, so look at several frames a second across the moments when something new appears:

```bash
cd my-video
ffmpeg -v error -y -ss 10 -t 4 -i out/my-film.mp4 -vf "fps=6,scale=480:-1,tile=6x4" -frames:v 1 out/ghost-scan.png </dev/null
```

Grading a picture with ffmpeg in a working copy, instead of with a WebGL effect at render time, avoids `swangle` altogether.

## Disk

- **A render holds three copies of every media file it plays:** the one in `public/`, the bundle's, and its own asset cache in the temp folder.

- **`npx remotion bundle` copies all of `public/`.** A 71-minute film from two sources bundled at 2.4 GB, and its asset cache took 2.8 GB within the first 85 s.

- **A full disk does not look like a full disk.** With 7.3 GB free, that render failed twice at the same frame, the first to touch the biggest file, with `Failed to fetch … the disk space is low` and a closed browser tab. A 141-frame test of that stretch passed, which made it look like a fault in that frame. After space was freed, the same frames rendered.

- **To win one copy back,** hard-link the `public/` file to the bundle's, once you know they match. A hard link makes two names for one file on disk:

  ```bash
  cmp out/bundle/public/clip.mp4 public/clip.mp4 && ln -f out/bundle/public/clip.mp4 public/clip.mp4
  ```

  After this, never rewrite such a file in place, because a running render reads the same bytes. Write beside it, then rename it over.

- **A chunk folder grows too:** PCM sound and H.264 together took about 4.3 MB for 5 seconds at 1080p in a test, so the folder is larger than the final film until the join. That is why the rule in Step 2 counts about four times the finished film. The script removes its temp folder but keeps the chunks. Delete them when the film is safe.

- **Disk seen in containers:** 17 GB free in one, 29 GB in another. Check yours.

## Memory

- **For footage, cap the frame cache:** `--offthreadvideo-cache-size-in-bytes=800000000`. `<OffthreadVideo>` keeps decoded frames, and uncapped the cache can grow toward half the machine's memory. On a 2560x1440 footage edit the render reached 10.2 GB of 16, and the container restarted mid-render.

- **Normal use**, on 1080p drawn scenes: 1.7 GB at rest, 3.4 GB at concurrency 2, 4.1 GB at concurrency 4.

- There is no swap. When memory runs out the container restarts, and you lose whatever was not pushed.

## Traps worth understanding

**Colour tags.** A video file carries labels that tell players how to show its colours. Check that all four are there:

```bash
cd my-video
ffprobe -v error -select_streams v -show_entries stream=color_range,color_space,color_transfer,color_primaries -of compact out/my-film.mp4
```

You want `color_range=tv|color_space=bt709|color_transfer=bt709|color_primaries=bt709`.

On Remotion 4.0.541 on a Mac all four tags were present; on an older Remotion on Linux only the matrix tag was. So check with ffprobe, and if the tags are missing, write them without re-encoding. Pass `--image-format=png` wherever footage colour matters. Not yet measured on Linux at 4.0.541.

Without the `--color-space=bt709` flag at all, a Mac render read `color_space=unknown|color_transfer=iec61966-2-1`. When you pass the flag, `render-chunks.py` writes all four at the join without touching a pixel: the decoded frames had the same MD5 before and after. A file rendered in one piece can be retagged the same way, again with no re-encode:

```bash
cd my-video
ffmpeg -v error -y -i in.mp4 -c copy -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1 -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -movflags +faststart out.mp4 </dev/null
```

Write the flag as `--color-space=bt709` with an `=`. The script looks for that exact string, and stops with a message if you write it with a space.

**AAC per chunk drifts the sound.** AAC (the usual compressed sound format) adds a short delay every time it starts. So chunks each with their own AAC, joined, come out longer than the picture. Over two chunks this measured 75 ms in the cloud, and 112 ms on a Mac at 4.0.541 (5,376 extra samples over 10 s). A film of many chunks would drift visibly. So each chunk here carries uncompressed sound, which joins exactly, and AAC is encoded once over the whole film. `--enforce-audio-track` gives a silent chunk a silent track, or the join would break.

**A sound-only render is not a shortcut.** `--codec=wav` still visits every frame and waits for the footage: 4.5 frames a second against 5 for the picture.

**A short test file can report a slightly wrong length.** A 5.000-second chunk read 4.98 s on a Mac. So the script counts a chunk's sound directly. If you write your own checks, use this command:

```bash
cd my-video
ffmpeg -v error -i chunk.mkv -map 0:a:0 -ac 1 -ar 48000 -f s16le - </dev/null | wc -c
```

Divide the result by 96,000 to get seconds.

**Killing a render takes more than killing the render.** Remotion starts Chrome in a process group of its own. A script that killed only the render's group left Chrome running in a test on a Mac. `render-chunks.py` also finds Chrome by the profile folder inside its temp folder, and kills that group too.

**Two renders and one temp folder.** A script that cleans up `remotion-v*-assets*` folders in a shared temp folder would delete another render's files. So each render here gets a temp folder of its own, through `TMPDIR`.

**`ffmpeg` eats a `while read` loop.** It reads stdin. Inside `while read job; do ffmpeg ...; done < jobs.txt` it swallows job lines. In a test on a Mac the names came out as `first`, `econd`, `hird`, and with longer encodes the loop ends early with no error. Give every ffmpeg in such a loop `</dev/null`. From Python, use `stdin=subprocess.DEVNULL`.

**Mac and Linux frames differ.** Text anti-aliasing differs, and so do shading tones: one shaded area measured 118,102,87 on a Mac and 153,115,83 in the cloud, with identical shapes. Each machine repeats exactly, run to run, but the two do not match. So:

- Render one series on one machine, or a viewer can see the seam between episodes.

- Keep reference frames per machine. A Mac's reference stills will not match a cloud render.

**The two-hour limit.** A background command stops after 30 minutes unless you start it with `timeout: 7200000`, which gives it up to 2 hours, the most allowed (from Anthropic's docs, checked November 2026). A 2.5-hour render needs a second run, and the chunk script makes that second run cheap. It costs one unfinished chunk, at most. A chunk of 3000 frames takes about 6 minutes at 8 frames a second.

## How to talk to the user

- Give the wait before it starts, from your own test: "This film is 12 minutes. From my test, expect about 35 minutes. I will check on it and tell you when it is done."

- Do not narrate every chunk. Report at the start, on a problem, and at the end.

- Ask one question at a time, with a recommendation. For example: "This film is for YouTube, so I recommend setting its volume for YouTube. Is that OK?"

- Before a long render, pause for their OK on one test frame or a short test clip. A wrong render costs an hour; a look costs a minute.

- Say plainly what you could not check. "I checked the picture frame by frame and measured the sound, but I cannot hear it. Please listen to the first minute."

- Send the link to the private page. Say "page", "button" and "save".

## Memory: start small

**Start at `--concurrency=2`, with the frame cache capped.** Raise it only after watching `free -m` during a test. Every render command in this guide does this, and the config sets the cap as well, so a render that forgets the flag is still protected.

Real footage is the danger, because each Chrome tab holds video frames on top of the cache. In a real cloud job on 9 November 2026 (Remotion 4.0.542, 4 cores, 16 GB, no swap), a half-size edit of a 720p interview at `--concurrency=3`, with no cap, died with `Compositor exited with signal SIGKILL`. The same render at `--concurrency=2` with an 800 MB cap finished: 4,468 frames in about 5.5 minutes, about 13 frames a second, and a 16.5 MB file.

With no real video, `--concurrency=4` ran well across a batch of 58 animated films. A cap of up to 2 GB has also worked on a 16 GB machine. These are starting points.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `Compositor exited with signal SIGKILL` | The machine ran out of memory, and the system killed the render. There is no swap to fall back on | Cap the frame cache with `--offthreadvideo-cache-size-in-bytes=800000000`, use `--concurrency=2`, and run it again. Nothing is lost. It can look odd afterwards, because `free -m` shows plenty of memory once the render is gone |
| `moov atom not found`, on only some frames | A file was still being written when you bundled | Wait for writes to finish (`pgrep -x ffmpeg` prints nothing). Bundle again. |
| `Failed to fetch … the disk space is low`, and a closed browser tab, at the same frame each time | The disk filled up | Free space. Hard-link as in "Disk". Keep three times the working copies free, plus about four times the finished film. |
| The container restarts during footage | Memory ran out | `--offthreadvideo-cache-size-in-bytes=800000000`, lower `--concurrency`, chunks. |
| `Error creating WebGL context` | A WebGL scene on `angle` | `--gl=swangle` for that render. Scan for ghosts. |
| A faint copy of something, only in the video | `swangle` ghost | Remove `--gl=swangle` if the scene is not WebGL. |
| Blank where an effect should be | No working GL for a shader | Look at a still. Try `--gl=swangle`. |
| `Could not find composition with ID` | Wrong entry or bundle | `npx remotion compositions out/bundle`. |
| `Could not find a tsconfig.json file in your project` | No `tsconfig.json` | `prep-render.sh` adds one. |
| `npm error could not determine executable to run` | You are not in the project folder, or `node_modules` is gone | `cd` into the project folder. Run `prep-render.sh`. |
| `Filter not found` for `tile` or `volumedetect` | You used Remotion's cut-down ffmpeg (`npx remotion ffmpeg`) | Use the `ffmpeg` that `prep-render.sh` put on the PATH. |
| `ffprobe: command not found` | The PATH did not carry to this call | Start with the `export PATH=...` line the script printed. |
| The render looks fine, but with old content | An old bundle, or old chunks | Bundle again. Delete the work folder. |
| `chunk N failed twice; run the same command again to resume from it` | A real render error | Read the end of `<work dir>/render.log`, and fix that. |
| The usage text prints | A flag written with a space | Write `--chunk=1500`. |
| An error with the words `exceeded rendering`, such as a still failing while other renders run | The page took longer than the limit | Add `--timeout=120000` to start. If it still fails, read which `delayRender()` handle the error names. |
| `exceeds the 30 MiB upload limit` | The file is too big for a chat file | Use the private page (Step 11). |
| `Piece N arrived damaged` or `at the wrong size`, on the page | That piece does not match what you recorded | Check the store listing against `pieces.json`, and upload that piece again. |
| `Piece N did not load (404)`, on the page | A wrong address in the data block | Copy the `url` again, exactly as the upload result gave it. |
| No **Save** button, and the note says to open it in a browser | Saving is not available in that view | Ask them to open the link in a browser while signed in. |
| `Too large to save in this app`, on the page | The Android app's 200 MiB limit | Ask them to open the page in a computer browser, or make a smaller copy if they want one. |
| A render stops at about 30 minutes, or 40 | It ran with no `timeout`. A command started in the background gets 30 minutes by default, and one that began in the foreground gets 30 minutes after it moves to the background | Start it with `run_in_background: true` and `timeout: 7200000`. The stop notice reads `was stopped after reaching its background time limit` |
| Jobs have vanished after "worker was restarted" | A restart kills processes | Check `ps` and the log's last line, then relaunch. |
| `Detected differing memory amounts` | The container reports memory two ways | Harmless. |

## How to check it worked

1. **The shape.** The script prints `{"frames": 600, "expected": 600, "video_s": 20.0, "audio_s": 20.0}`. For any file:

   ```bash
   cd my-video
   ffprobe -v error -show_entries stream=codec_name,nb_frames,duration -of compact out/my-film.mastered.mp4
   ```

2. **Sound is really there.** `max_volume` must not read `-91.0 dB` (that is silence):

   ```bash
   cd my-video
   ffmpeg -hide_banner -i out/my-film.mastered.mp4 -af volumedetect -f null - 2>&1 </dev/null | grep -E 'mean_volume|max_volume'
   ```

   `master-audio.py` printed the loudness in its `after` row. Check it is where you aimed.

3. **Look at it with your own eyes.** A file check cannot tell you the video is good. Make a contact sheet of one frame every few seconds, and open it with the Read tool:

   ```bash
   cd my-video
   ffmpeg -v error -y -i out/my-film.mastered.mp4 -vf "fps=1/8,scale=320:-1,tile=8x10" -frames:v 1 out/sheet.png </dev/null
   ```

   Check the first and last frames, every title, and the joins between chunks. Open a few frames at full size to read small text.

4. **Colour tags**, using the command above.

5. **The store** matches `pieces.json`, and every piece in the data block has a `url`, a `size` and a `sha256`.

6. **The user** pressed **Get the video** and it played. Ask them. You cannot press it for them.

7. **Keep the evidence short:** the frame count, the length, the size, the loudness, and what you saw. Tell the user.
