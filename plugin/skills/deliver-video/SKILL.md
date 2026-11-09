---
name: deliver-video
description: Get a finished video, big ones too, out of a Claude Code cloud session and into the user's hands, through a private web page where they can watch it and save it as one file. Use this whenever a video is ready to show, whatever its size.
---

# Deliver Video: a page to watch it and save it

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

## What this skill does

A finished film is usually too big to send in the chat, and git will not hold it either. This skill builds a private web page for it.

You split the video into pieces and store them on the page. When the user opens the page and presses one button, their browser fetches the pieces, checks each one, joins them into a single video, plays it, and lets them save it as one normal MP4 file.

To the user, it feels like a simple download page.

## When to use it (and when not to)

Use the page by default, for small and big videos alike. If you are running on the user's own computer, not in a cloud session, just tell them where the file is. It is the friendliest route, and it holds the notes that go with the video too: chapters, a description, what you changed, and what you would like them to check.

Two other routes exist:

| Route | Use it when | Limit |
|---|---|---|
| A file card in the chat (`SendUserFile`) | A short clip or quick test, when the user just wants to see it fast | Refuses files over 30 MiB: "exceeds the 30 MiB upload limit" |
| A service the user already uses (Google Drive, YouTube) | The user asks for it, and has given you a way in | Depends on the service. Test that you can reach it first |

A delivery to Google Drive worked for a batch of 58 films on one real job. That setup is not covered here. Follow Google's public docs for the Drive API, and test that you can reach it first.

## What you need before you start

- **The `Artifact` tool**, which publishes a private page on claude.ai. Cloud sessions have it.
- **Python 3**. Check with `python3 --version`.
- **ffmpeg and ffprobe**, for the look-before-you-send check. Check with `ffmpeg -version`. If they are missing and `apt` is refused, `pip install imageio-ffmpeg` gives a static ffmpeg:

```bash
pip install imageio-ffmpeg
FF=$(python3 -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')
mkdir -p ~/bin && ln -sf "$FF" ~/bin/ffmpeg && export PATH="$HOME/bin:$PATH"
```

That package has no ffprobe. Use `ffmpeg -i file.mp4` to read a file's length and streams.

## The limits, when this was written

| Limit | Value | Checked |
|---|---|---|
| One stored piece | 20 MiB. The script makes 19 MiB pieces | The tool's own type file, November 2026 |
| One page's total store | 1 GiB (1,073,741,824 bytes) and 5,000 files | A real listing, 9 November 2026 |
| Upload of pieces in one call | Up to 25 files | The tool's description, November 2026 |
| A piece that starts with `<` | Refused, because the store thinks it is markup. The script moves the cut back a byte at a time until it does not | Real use, 2026 |
| Saving on a computer browser | No size limit short of the browser's own memory | Real use, with an earlier version of this page: a 339 MB film |
| Saving in the Android app | 200 MiB | The tool's type file, November 2026 |

**Over 1 GiB?** Make a smaller copy (see "A smaller copy" below), or publish a second page and put part of the film on it.

**Memory.** The film is joined in the viewer's browser memory. A computer handles a few hundred MB well. A phone may not. If a phone stalls, send a smaller copy.

## Steps

### 1. Look before you send

Never send something you have not looked at. Check the shape first:

```bash
ffmpeg -i out/film.mp4 2>&1 | grep -E 'Duration|Stream'
```

Then make a contact sheet (a grid of frames) and open it with the Read tool:

```bash
ffmpeg -v error -y -i out/film.mp4 -vf "fps=1/8,scale=320:-1,tile=8x10" -frames:v 1 sheet.png
```

If you cannot see what you expected, stop and fix it. Tell the user anything you could not check. A cloud container cannot listen to sound, so you can measure sound but not judge it.

### 2. Save and run the split script

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/deliver-video"
cp -rn "$S/files/." . 2>/dev/null; test -e "split-for-artifact.py" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It copies `split-for-artifact.py` and `delivery-page.html`. Run it in your working directory, because the page needs to be there.

`split-for-artifact.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/split-for-artifact.py (48 lines).
```

Put the pieces inside your working directory. A file outside the working directory has to go in an upload call of its own, so a folder that git ignores, such as `out/`, is the right place:

```bash
python3 split-for-artifact.py out/film.mp4 out/film-pieces
```

It writes `part-01.mp4`, `part-02.mp4` and so on, plus `pieces.json` with each piece's size and SHA-256 (a fingerprint of the file).

A file under 20 MiB still works: it becomes one piece.

### 3. The page

This is the page the user sees. The copy step saved it. The `Artifact` tool gives it a private link and somewhere to keep the pieces.

`delivery-page.html`, which the copy step puts in your folder:

```html
# In this skill's files folder: files/delivery-page.html (305 lines).
```

### 4. Publish the empty page

Publish it first, because the pieces need a page to live on. If the tool asks you to load its design or capability skills, do so. Keep this page's script unchanged.

```
Artifact
  action: publish
  file_path: delivery-page.html
  icon: video
  capabilities: {"assets": {}, "downloads": true}
```

Keep the `url` in the result. The page's name comes from its `<title>` tag, so change that tag to the film's name if you like, in two to four words.

### 5. Upload the pieces

```
Artifact
  action: publish
  url: <the page>
  asset: true
  file_paths: [out/film-pieces/part-01.mp4, out/film-pieces/part-02.mp4, ...]
```

Send at most 25 in one call. Make more calls for a longer film. The result gives one `url` per piece, such as `/_blob/7db260ac...`. Use it exactly as given.

### 6. Fill in the data block

Edit the `video-data` block in the page. Here is a full example. Every field except `title` and `videos` can be left empty.

```json
{
	"title": "How the bridge was built",
	"intro": "Your 12-minute film. Press the button, watch it, and save it if you like it.",
	"meta": "12:04 · 1920×1080 · 30 fps",
	"videos": [
		{
			"label": "The full film",
			"filename": "how-the-bridge-was-built.mp4",
			"size": 57940422,
			"pieces": [
				{"url": "/_blob/7db260ac...", "size": 19922944, "sha256": "794caf1d..."},
				{"url": "/_blob/798cc9b4...", "size": 19922944, "sha256": "786de73f..."}
			]
		},
		{
			"label": "The 45-second short",
			"filename": "short.mp4",
			"shape": "tall",
			"size": 13000000,
			"pieces": [{"url": "/_blob/...", "size": 13000000, "sha256": "..."}]
		}
	],
	"chapters": [{"t": "0:00", "title": "The opening"}],
	"description": "Text to copy into a video site.",
	"changes": ["Cut 4 minutes of pauses."],
	"checks": ["Does the name at 3:10 sound right to you? I can't listen."]
}
```

`size` and `sha256` come from `pieces.json`. The top-level `size` in that file is the video's whole size. `shape` is optional: `tall` for 9:16, `square` for 4:5, or leave it out for 16:9.

### 7. Publish again

Publish the same file path once more. Do not pass `capabilities`; they carry forward.

### 8. Check the store

This compares what is stored against what you sent, without downloading anything:

```
Artifact  action: list  scope: assets  url: <the page>
```

Each line shows a SHA-256. Compare each with `pieces.json`. A real test on 9 November 2026 matched for all three pieces of a 58 MB file.

### 9. Send the link

For example:

> Your video is ready: <link>
>
> Open it in your browser and press **Get the video**. When it has loaded it will play right there, and **Save to my device** gives you one normal MP4 file.
>
> Near the bottom I listed two things I would like you to check. I can't listen to sound here, so please play it with the sound on.

The page is private. Only the user and the people they share it with can open it. You cannot change sharing: they use the page's **Share** menu. Tell them that if someone else needs to see it.

### A smaller copy

Sometimes the user wants a file that is easier to pass around. Step the quality down until it fits. A higher CRF number means a smaller file and lower quality.

```bash
ffmpeg -v error -y -i out/film.mp4 -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 160k -movflags +faststart out/film.share.mp4
```

Try 23, then 25, then 27, and stop when the file is small enough. A copy under 30 MiB can also go as a chat file (aim for under 31,000,000 bytes). This route was used for real lesson videos of up to about 10 minutes. Look at the copy before you send it, because a higher number can soften the picture.

## How to talk to the user

- Say "page", "button" and "save". Do not say "artifact", "asset" or "blob".
- Always say what you checked and what you could not check. For example: "I checked every frame's shape and the loudness, but I can't hear it. Please listen once."
- Ask for the one thing you most need from them: "Does the pace feel right?"
- If you plan to replace a film, say that the same link will show the new one.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `exceeds the 30 MiB upload limit` | You used the chat file card on a big file | Use this page, or make a smaller copy |
| The page says "This view can't play it here" | The browser or app cannot play it inside the page | Ask them to save it and play it on their device |
| The page says "Too large to save in this app" | The Android app's 200 MiB limit | Ask them to open the page in a computer browser, or send a smaller copy |
| No **Save** button, and the note says to open in a browser | The `downloads` feature is not available in this view | Ask them to open the link in a browser while signed in |
| `Piece N arrived damaged` or `at the wrong size` | That piece does not match what you recorded | Check the store listing against `pieces.json`, and upload that piece again |
| `Piece N did not load (404)` | A wrong address in the data block | Copy the `url` again, exactly as the upload result gave it |
| Upload of a piece is refused because it looks like markup | The piece starts with `<` | The script prevents this. You probably cut the file with another tool |
| An upload call complains about a file outside the working directory | The pieces are in a scratch folder | Move them into the working directory, or upload them one call at a time |
| A publish is refused as a conflict | Someone or something published a newer version | Read the newer version, merge, and publish again |

## How to check it worked

1. The store's SHA-256 values match `pieces.json`.
2. You opened the page's data block and every piece has a `url`, a `size` and a `sha256`.
3. The user pressed **Get the video** and it played. Ask them. You cannot press it for them.

What was tested: an earlier version of this page delivered a real 19-minute film, which played and saved as one 339 MB MP4. This exact version was tested on 9 November 2026 in headless Chrome against a stand-in for claude.ai, where the saved file matched the original exactly, and its pieces were stored and checked on claude.ai. Nothing here was run from a Linux container.

If a director skill sent you here, go back to it when you finish.
