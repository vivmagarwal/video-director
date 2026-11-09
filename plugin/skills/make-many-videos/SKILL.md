---
name: make-many-videos
description: Make a batch of many videos in one Claude Code cloud container, with one agent per video, render locks, resumable renders and a review round. Use when a user wants ten or more similar videos, such as a series of course intros or product clips.
---

# Make many videos with many agents

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It shows how to make dozens of videos in one cloud container, using many agents at once, without the agents wrecking each other's work or the machine. It comes from a real batch: **58 films of 2 to 3 minutes each, about 2.5 hours in all, made in one 4-core cloud container in October 2026** on an older Remotion (4.0.523). Numbers below come from that batch, unless they say otherwise.

Remotion writes videos as React code. A composition is one video in that code. A bundle is the packed copy of a project that a render reads.

The method:

1. Make two pilot films first. Put every fault you find into the shared code.

2. Give each other film to its own agent, with its own files.

3. Queue every render through a lock, so agents take turns.

4. Commit by path, and let one session write the shared files.

5. Review with fresh agents, who did not make the film.

6. Render in resumable batches. Only stale films render again.

7. Master the sound of each finished film, then deliver the films through private pages.

## When to use it (and when not to)

Use it for a batch that shares a look and a structure, where each video has its own script.

Do not use it for one video, or for 2 or 3: make those directly. The machinery costs more than it saves.

Do not use it if the videos have no shared look yet. Settle that with the user first, on a pilot.

## What you need before you start

When this was written, a cloud session was a Linux x64 container: 4 cores, about 15 GB of memory, no swap, no GPU. The Bash tool stops a command at 10 minutes, and a background command stops at 2 hours. Bare `sleep` is blocked.

| Need | How to check | How to get it |
|---|---|---|
| A Remotion project | `ls package.json src` | Step 1. |
| Packages, Chrome, full ffmpeg, ffprobe | `prep-render.sh` tests them | Step 1. |
| `flock`, the command that queues work behind a lock file | `command -v flock` | Part of util-linux on Linux. |
| Python 3 | `python3 --version` | For the batch script. |
| A way to run agents | Your Agent tool | See "How many agents". |
| Usage allowance | Ask the user what plan they are on | Weekly limits are real. See Step 12. |
| Free disk | `df -h .` | Keep three times the working copies free (the media in `public/`), plus about four times the finished films. 58 finished films came to about 2.1 GB. |
| The `Artifact` tool, for the delivery pages | Cloud sessions have it | Step 11 uses it. |
| Network | `curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://registry.npmjs.org/remotion` | The user can change allowed hosts in the session's cloud environment menu: **Edit**, then **Network access**. A refusal is `CONNECT tunnel failed` or `Host not in allowlist`. Any other status means the host answered. |

Voices are free by default with Kokoro (see "Voices" below). Ask about money only for paid services, such as a paid voice, stock footage, or images from a paid generator. Keys go in the cloud environment's variables (menu, **Edit**), never in the chat. For people on screen, the public options include real footage, stock video, Lottie or Rive animation, and clips from an AI generator. Those are examples: use what suits the user.

Licence, once: Remotion is free for individuals, non-profits and for-profit companies with up to 3 employees; others need a company licence (remotion.dev/license). A batch for a company makes this worth saying clearly.

## What it costs in time

Give the user these numbers before they commit. Do not estimate from a short clip.

| Stage | Measured |
|---|---|
| Composing 56 films, up to 20 agents at once, each checking its own frames | About 3 hours, one restart included |
| Rendering one film of 2 to 3 minutes at `--concurrency=4` | About 6 to 9 minutes, including its checks |
| The same kind of film, alone on the machine | About 4.5 to 6 minutes (12 to 13 frames a second) |
| The same kind of film, beside other work | About 16 minutes (4 frames a second) |
| Rendering all 58 | **About 7 hours, in four batches** |
| The estimate made beforehand | **About 3 hours, from short-clip speed (5 to 8 frames a second). It was less than half of the real time.** |

So plan from a full pilot film, then add a margin. A starting formula: films × seconds per pilot × 1.5. On the real batch, the average film took about 1.4 times the pilots' time. That batch ran two renders at once, each at `--concurrency=4`. Whether two renders finish a batch sooner on 4 cores was not measured: they share the same cores, and a film can take three times as long beside other work.

Each `--concurrency=4` render held about 4 GB of memory in total. A still with its bundle took about 9 s when the machine was quiet. A `compositions` call took about 16 s.

## Steps

`my-video` below stands for your project folder. A `cd` may not carry over from one Bash call to the next, so each step's commands start with their own.

### First, save the files in this guide

```bash
mkdir -p my-video
```

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd my-video
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/make-many-videos"
cp -rn "$S/files/." . 2>/dev/null; test -e "remotion.config.ts" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It saves the tools, the example project and the voice scripts. It keeps any file you already have.

### Step 1. Prepare the machine

The script below is safe to run again, and you will after a restart. If you have no project yet, start one first:

```bash
cd my-video
npm init -y && npm i --save-exact remotion@$(npm view remotion version) @remotion/cli@$(npm view remotion version) react react-dom
```

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
cd my-video
bash prep-render.sh
```

Tested on a Mac at Remotion 4.0.541, on its normal route and with all its fallbacks forced. **Not run on Linux.** No `--binaries-directory` and no separate compositor download is needed, because npm brings the right one on Linux.

### Step 2. Lay out the project so that agents cannot collide

Each film gets files nobody else writes. Everything shared goes in a kit that agents only read.

```text
src/kit/                 shared look: titles, captions, colours. Agents never edit this.
src/films/film-01.tsx    one film. One agent writes it.
src/films/film-01.entry.tsx   registers that film alone. The same agent writes it.
src/Root.tsx, src/index.ts    registers every film. One session writes these, after films land.
public/films/film-01/    that film's voice, images and clips.
public/shared/           music and images every film uses.
films.json               the list the render script reads.
```

The film names and folders are examples.

Here is an example kit piece and film, tested as they stand. The film plays `public/films/film-01/voice.mp3`. The look is a placeholder: use the user's.

Save this as `src/kit/Title.tsx`
```tsx
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
export const Title: React.FC<{text: string; color: string}> = ({text, color}) => {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [0, 149], [0, 300]);
  return (
    <AbsoluteFill style={{backgroundColor: color, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{transform: `translateY(${y}px)`, color: 'white', fontFamily: 'sans-serif', fontSize: 120}}>{text}</div>
      <div style={{position: 'absolute', bottom: 40, right: 60, color: 'white', fontFamily: 'sans-serif', fontSize: 40}}>frame {frame}</div>
    </AbsoluteFill>
  );
};
```

Save this as `src/films/film-01.tsx`
```tsx
import {Audio, staticFile} from 'remotion';
import {Title} from '../kit/Title';
export const meta = {id: 'film-01', durationInFrames: 150, fps: 30, width: 1280, height: 720};
export const Film = () => (
  <>
    <Title text="Film 01" color="#264653" />
    <Audio src={staticFile('films/film-01/voice.mp3')} />
  </>
);
```

**Give each film its own entry file.** Then its stills and test bundles hold that one film, a half-written film elsewhere cannot break them, and a render stays reproducible while others edit the checkout.

Save this as `src/films/film-01.entry.tsx`
```tsx
import {Composition, registerRoot} from 'remotion';
import {Film, meta} from './film-01';
registerRoot(() => <Composition {...meta} component={Film} />);
```

A test tone stands in until the film has a real voice:

```bash
cd my-video
mkdir -p public/films/film-01
ffmpeg -v error -y -f lavfi -i sine=frequency=330:duration=5 public/films/film-01/voice.mp3 </dev/null
npx remotion compositions src/films/film-01.entry.tsx
```

The main entry registers all films, for the final renders. **Agents do not touch it.** Twenty agents appending to one file will collide. One session adds films after they land.

Save this as `src/index.ts`
```ts
import {registerRoot} from 'remotion';
import {Root} from './Root';

registerRoot(Root);
```

This example registers one film. Add an import and a list entry for each film that lands.

Save this as `src/Root.tsx`
```tsx
import {Composition} from 'remotion';
import * as F01 from './films/film-01';
export const Root = () => (
  <>
    {[F01].map((f) => (
      <Composition key={f.meta.id} {...f.meta} component={f.Film} />
    ))}
  </>
);
```

### Voices, if the films need them

Voices are free by default with Kokoro, an open voice model that runs on this machine. It needs no key and no account. A paid voice is the user's choice. Ask about money only for paid services. Kokoro is not a person, so tell the user that plainly, and play them samples on the pilots.

The setup downloads the model, the speech model that checks it and their Python packages into `~/voice-tools`. It needs `pypi.org`, `files.pythonhosted.org` and `github.com`. It is safe to run again, and a restart can wipe that folder, so you may need to.

Save this as `setup-voice.sh`
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

`readback.py` reads the finished sound back to you, because a container has no ears. It prints every place that differs from the script.

`readback.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/readback.py (74 lines).
```

Voice one film, under the render lock, because voicing and rendering share the same cores. The film's script is a plain text file:

```bash
cd my-video
bash setup-voice.sh
mkdir -p public/films/film-01
cp scripts/film-01.txt public/films/film-01/voice.txt
flock /tmp/render-1.lock ~/voice-tools/venv/bin/python voice.py public/films/film-01/voice.txt --voice=af_heart --target=144
flock /tmp/render-1.lock ~/voice-tools/venv/bin/python readback.py public/films/film-01/voice.mp3 public/films/film-01/voice.txt
```

It writes `voice.mp3` and `voice.captions.json` beside the text. `af_heart` and 144 words a minute are only examples: choose with the user, and ask for their references. If a name comes out wrong, respell it in the text, like `project{prodject}`. The word timing and the read-back were only tested on English, so test first for another language. Tested on a Mac: a 36-word script was voiced in 9 s and read back in 3 s, with every word matched. Its speed inside a batch on a 4-core container was not measured, and it was **not run on Linux**.

### Step 3. Make two pilot films, and fix the kit

Make two films by yourself, as different from each other as the batch will be. Compose, render, and look at every frame of each sheet. The first faults are much cheaper on 2 films than on 58. Show them to the user, and wait for their OK on the look, the pace and the voice. Time them too: this is your real render speed.

Every fault goes into the kit, before the batch. Once agents are composing, a kit change reaches films they have already checked.

### Step 4. Learn the render lock

Every still, render, bundle and `compositions` call goes through `flock`:

```bash
cd my-video
flock /tmp/render-1.lock npx remotion still src/films/film-01.entry.tsx film-01 out/test.png --frame=60 --timeout=120000
```

`flock` waits until nobody else holds that file, and then runs the command. Why this matters: twenty agents each starting a bundle and a Chrome would exhaust a 4-core, 15 GB container.

**Use one lock file by default,** so one render runs at a time and the rest queue. Two lock files, `/tmp/render-1.lock` and `/tmp/render-2.lock`, each with `--concurrency=2`, is something to test on your own pilots, not a rule.

- **A still on a busy machine can pass the default 30 s timeout.** That is why the command above has `--timeout=120000`, as a start.

- **A long queue can outlast the Bash tool's 10 minutes.** Run the call in the background, or use `flock -w 500 /tmp/render-1.lock ...` and retry (`-w` gives up after that many seconds). Not measured.

- **A stuck lock.** A process left running after a crash can keep holding a lock, and everyone then waits forever. Check `ps`, and kill the leftover. `flock -o` closes the lock for the command's children. Not tested: the Mac used for testing has no `flock` command.

### Step 5. Brief one agent per video

Give each agent one film. An agent should never edit the kit: a kit fault comes back as a report, and the coordinating session makes the change once, for every film.

**How many agents.** The real batch ran up to 20 agents at once through the Agent tool, with render locks keeping the machine alive. A workflow tool on the same 4-core machine ran only 2 agents at a time. So try one, and see what your tool allows. Thinking is not what is slow: the renders are.

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs. The brief below pushes, so do this before the first agent starts.

Use this brief, changed to fit. Fill the words in capitals. LOCK-FILE is `/tmp/render-1.lock` unless you are testing two locks.

```markdown
You make ONE video, FILM-ID, of a batch of many, in the repository at PATH, on the branch
BRANCH, which is already checked out. Never switch branches. Other agents are working in
this same folder right now.

Read first: the pilots src/films/PILOT-1.tsx and PILOT-2.tsx, then src/kit/. Your script
is at SCRIPT-PATH. Your film must be as good as the pilots.

Write ONLY: src/films/FILM-ID.tsx, src/films/FILM-ID.entry.tsx, public/films/FILM-ID/.
Never edit src/kit/, src/Root.tsx, or any other film. If the kit needs a change, say so in
your report. Names on screen come only from the script. A person the script does not name
stays unnamed: use initials or a role.

Every still, render, bundle or compositions call goes through the lock:
  flock LOCK-FILE npx remotion ... --timeout=120000
Do not render the whole film. The final renders run later as one queue.

Check your work:
1. Make a sheet: LOCK=LOCK-FILE bash shot-sheet.sh src/films/FILM-ID.entry.tsx FILM-ID out/sheets/FILM-ID.png 16
2. Open it with the Read tool, and look at every tile as a viewer would. Is each moment of
   the script there? Is any text cut off or overlapping? Does anything look wrong against
   what is being said? Fix it and look again, until it is right.

Save your work, by path, and only your own files:
  flock /tmp/git.lock sh -c 'git add src/films/FILM-ID.tsx src/films/FILM-ID.entry.tsx public/films/FILM-ID &&
    git commit --no-verify -m "FILM-ID composed" -- src/films/FILM-ID.tsx src/films/FILM-ID.entry.tsx public/films/FILM-ID &&
    git push -u origin BRANCH'
If the push is rejected because others pushed:
  flock /tmp/git.lock git pull --rebase --autostash origin BRANCH
and push again. On a network error, retry after 2, 4, 8 and 16 seconds.

Kill any process you started before you finish. Reply in at most 6 lines: what you made,
what you fixed after looking, what you could not do, and any kit change you need.
```

Here is the sheet script. It takes stills spread across the film and tiles them.

Save this as `shot-sheet.sh`
```bash
#!/usr/bin/env bash
# One still from the middle of each stretch of a film, tiled into one picture.
#
#   LOCK=/tmp/render-1.lock bash shot-sheet.sh <entry or bundle> <composition id> <sheet.png> [count]
#
# It prints which frame each tile is, so you can find a fault in the code.
set -euo pipefail
src=$1; comp=$2; sheet=$3; count=${4:-16}
LOCK=${LOCK:-/tmp/render-1.lock}
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT

# Bundle once, under the lock, so the stills do not each bundle again.
if [ -d "$src" ]; then
  bundle=$src
else
  bundle=$dir/bundle
  flock "$LOCK" npx --no-install remotion bundle "$src" --out-dir="$bundle" </dev/null >/dev/null 2>&1
fi
frames=$(flock "$LOCK" npx --no-install remotion compositions "$bundle" </dev/null 2>/dev/null |
  awk -v c="$comp" '$1 == c { print $4 }')
[ -n "$frames" ] || { echo "composition $comp is not in $src" >&2; exit 1; }

side=1
while [ $((side * side)) -lt "$count" ]; do side=$((side + 1)); done
for i in $(seq 0 $((count - 1))); do
  f=$(( (2 * i + 1) * frames / (2 * count) ))
  echo "tile $((i + 1)): frame $f"
  # A still on a busy machine can pass the default 30 s timeout, so give it room.
  flock "$LOCK" npx --no-install remotion still "$bundle" "$comp" "$dir/$(printf %03d "$i").png" \
    --frame="$f" --scale=0.5 --timeout=120000 </dev/null >/dev/null 2>&1
done
mkdir -p "$(dirname "$sheet")"
ffmpeg -v error -y -framerate 1 -i "$dir/%03d.png" -vf "scale=480:-1,tile=${side}x${side}" -frames:v 1 "$sheet" </dev/null
echo "wrote $sheet"
```

Tested on a Mac with a small stand-in for `flock`, because the Mac has no `flock` command: 9 stills, and the sheet was looked at. **Not run on Linux.**

### Step 6. Commit by path, with shared files handled apart

All agents share one checkout and one branch, so each sees the others' half-written files. That caused every problem in this list:

- **Commit by path, with `-- paths`.** Without it, a commit takes whatever another agent has just staged. Tested on a Mac: the staged stranger's file stayed out of the commit.

- **Use `git commit --no-verify` during the batch, and run the checks by hand.** A commit hook that formats a whole folder would reformat other agents' half-written files. Afterwards, run `git status`.

- **One git lock.** Two git commands at once can fail on `.git/index.lock`. The brief puts commits and pushes behind `/tmp/git.lock`. This lock is not measured on a real batch. It is a simple guard against that failure.

- **Watch `--autostash`.** It takes everyone's uncommitted changes off the disk for a moment, then puts them back. Under the git lock that moment is short, but an agent writing right then can hit a conflict. Check `git stash list` is empty now and then. If it is not, look before you touch anything.

- **Agents report, and one session writes any shared file.** Agents that stage a shared file whole commit each other's unfinished lines, and a commit built on a stale copy can undo someone else's change.

- **Agents should finish by killing what they started.**

A git worktree per agent (a separate folder on its own branch) would avoid much of this. It was not tried here. If your Agent tool offers it and your disk can hold it, consider it. You then need a merge step, and `node_modules` for each.

**Generators and shared files.** A shared file with many writers is a race. A script that writes many files, and adds a line for each to a shared list, must wait until no one else has that list dirty. Rules that worked:

- Each agent writes only its own files.

- One session runs generators, when nobody else is writing what they write.

- Registration (`src/Root.tsx`) happens after films land, in one or two commits by one session.

- Never rewrite a shared file with `open(p,'w').write(f(open(p).read()))`. The write's `open` runs first, and empties the file before the read, along with any other agent's uncommitted work. Read to a variable on one line, and write on the next.

- A fingerprint or other tool should be tested with a real edit: change one input, and see that it notices.

### Step 7. Register, then run a review round

When films have landed, one session registers them in `src/Root.tsx`, runs `npx remotion compositions src/index.ts`, and commits.

**Then a fresh agent reviews each film.** An agent looking at its own work misses what a fresh reader sees: **after every agent had looked at its own film, 43 of 58 films still changed in review.** Eight review agents did this. Each made a new sheet of a few films, looked at each frame against the script as a viewer would, fixed what a viewer would notice in that film's file only, and committed each film alone.

What they found, most common first:

1. **A picture whose mood contradicts the words.**

2. **A label under the wrong thing.**

3. **Names the script does not give:** agents had invented names.

4. **Cut-off text and split items:** a chart losing its last month, a list number split from its step, a hyphenated word broken across lines.

Use the same list as a checklist. The real batch used no paid frame reviewer: every review was a session or a person looking.

**After any kit change, look at every sheet again before the render.** A kit change after a film was looked at changes that film unseen. A longer title, for example, can wrap and push something else off the screen. Probe a kit change first: a fix can look right in code and change nothing on screen, so render the exact case before and after, and look at both.

### Step 8. Render in resumable batches

Rendering runs in the background, and only for what is stale. The script below gives each film a **fingerprint**: one line per input file, with its SHA-1. A film is current when its final file exists and its fingerprint still matches. So a run after an edit re-renders exactly the films the edit reached.

Save this as `films.json`
```json
{
  "entry": "src/index.ts",
  "shared": ["src/kit", "remotion.config.ts", "package-lock.json"],
  "flags": ["--concurrency=4", "--color-space=bt709", "--offthreadvideo-cache-size-in-bytes=800000000"],
  "chunk": 60,
  "films": {
    "film-01": ["src/films/film-01.tsx", "public/films/film-01"]
  }
}
```

`"chunk": 60` is for a small test. For real films, use `3000` or leave it out. The other values are examples too. Add `"--image-format=png"` to `flags` if the films hold real footage, so its colours stay right.

**List everything a film reads in `shared`.** If the fingerprint leaves out a shared package, a change there does not mark films stale. So include `package-lock.json` and `remotion.config.ts`, and any folder your kit imports.

`render-batch.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/render-batch.py (281 lines).
```

Run it with `run_in_background: true` and `timeout: 7200000`:

```bash
cd my-video
mkdir -p out; python3 render-batch.py films.json > out/batch-1.log 2>&1
```

Name some films after `films.json` to render only those. To test two at once, set `--concurrency=2` in `flags`, then start two copies, each in its own background call. They share the list with no overlap:

```bash
cd my-video
LOCK=/tmp/render-1.lock python3 render-batch.py films.json > out/batch-1.log 2>&1
```

```bash
cd my-video
LOCK=/tmp/render-2.lock python3 render-batch.py films.json > out/batch-2.log 2>&1
```

To wait, use a Monitor until-loop on the log:

```bash
cd my-video
until grep -qE '^(RUN-DONE|ALL-CURRENT)' out/batch-1.log; do sleep 60; done
```

**Size a batch to the 2-hour limit.** At about 6 to 9 minutes a film, 13 to 21 films fit in 2 hours. So plan 15. A batch that overruns is simply run again. Before you run it again, make sure nothing is left from the last one: `pgrep -af '[r]emotion render'` must print nothing.

**Only one bundle a run,** taken straight after the fingerprints. An edit made during the run lands in neither, and the next run catches it. **Do not write into `public/` while a bundle runs.** A half-written file goes in, and the frames that play it fail with `moov atom not found`.

**Render one series on one machine.** Mac and Linux frames differ, in text anti-aliasing and shading tones. Each repeats exactly, run to run.

What was tested, on a Mac at 4.0.541, with three 5-second films made from the example:

| Test | Result |
|---|---|
| First run | All three rendered, `RUN-DONE failed=0` |
| Second run | `ALL-CURRENT` |
| Edit one film's file | Only that film rendered. The log named the file. |
| Edit a kit file | The film asked for was stale, and the log named the file. |
| Two copies with two locks, each at `--concurrency=2` | They shared the list, and no film rendered twice. |
| `kill -TERM` mid-film, then run again | The finished chunks were kept, and only the rest rendered. |
| Half-rendered, an edit, then run again | The old chunks were thrown away. |
| A path in `films.json` that does not exist | The run stopped and named it. |
| A film not registered in the entry | That film was reported failed. |
| Colour tags | All four BT.709 tags present. |

A stand-in for `flock` was used for the test of queuing. The script itself uses Python's `fcntl.flock`, the same kind of lock as the `flock` command. **Not run on Linux.**

Two traps that shaped this script:

- A chunk with the right frame count is kept, even if it holds old words. So chunks carry the fingerprint, and a mismatch throws them away.

- A fingerprint with a wrong path can silently leave out a film's own files, and the verdict still looks clean. So here a missing path stops the run.

**Colour tags.** A video file carries labels that tell players how to show its colours. On Remotion 4.0.541 on a Mac all four tags were present; on an older Remotion on Linux only the matrix tag was. So check with ffprobe, and if the tags are missing, write them without re-encoding. Pass `--image-format=png` wherever footage colour matters. Not yet measured on Linux at 4.0.541. `render-batch.py` writes all four at the join when `--color-space=bt709` is in `flags`. To check a film:

```bash
cd my-video
ffprobe -v error -select_streams v -show_entries stream=color_range,color_space,color_transfer,color_primaries -of compact out/batch/final/film-01.mp4
```

You want `color_range=tv|color_space=bt709|color_transfer=bt709|color_primaries=bt709`.

### Step 9. Look at what came out

The script writes `out/batch/<id>-sheet.png` for each film: one frame a second. Open them with the Read tool. A real check of a batch is a sheet per film and a closer look at a sample. Give the user the list, and a few films to watch. A cloud session cannot hear, so ask them to listen to a sample, especially names.

### Step 10. Master the sound of each finished film

Mastering sets how loud a finished film sounds. It is a normal last step. Renderers do not set loudness for you: five narrated renders measured about -24 to -28 LUFS (LUFS is the unit for how loud a film sounds), and viewers reach for the volume at that level. Skip this only if the user has a reason.

Starting points, as a floor: -14 LUFS for YouTube and short social clips, -16 LUFS for podcasts or when the platform is unknown, peak -1.5 dBTP. Use what the user or the platform asks for. dBTP is the unit for how high the loudest moment reaches.

`master-audio.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/master-audio.py (114 lines).
```

This loop masters every film that is new or re-rendered, and it is safe to run again. Run it with `run_in_background: true` and `timeout: 7200000`:

```bash
cd my-video
mkdir -p out/batch/mastered
for f in out/batch/final/*.mp4; do
  m=out/batch/mastered/$(basename "$f" .mp4)
  [ "$m.mp4" -nt "$f" ] && continue
  python3 master-audio.py "$f" --target=-14 --out="$m.part.mp4" && mv "$m.part.mp4" "$m.mp4" || echo "LOOK AT $f"
done
```

It copies each picture and does not touch it. Read each `after` row, and look into any `LOOK AT` line. Tested on a Mac on one film, and the loop skipped that film on a second pass. The time for a whole batch was not measured. **Not run on Linux.**

### Step 11. Deliver the films through private pages

Finished films are not in git, and exist only in this container until delivered, so send them as you go.

The route is a private web page. You split each film into pieces and store them on the page. The user presses a button beside a film. Their browser fetches its pieces, checks each one, joins them, plays the film, and saves it as one normal MP4.

**58 films came to about 2.1 GB, so plan one page for each 1 GiB.** One page can list many films. That batch needs at least two pages.

The limits, when this was written:

| Limit | Value | Checked |
|---|---|---|
| One stored piece | 20 MiB. The script makes 19 MiB pieces | The tool's own type file, November 2026 |
| One page's total store | 1 GiB (1,073,741,824 bytes) and 5,000 files | A real listing, November 2026 |
| Upload of pieces in one call | Up to 25 files | The tool's description, November 2026 |
| Saving in the Android app | 200 MiB | The tool's type file, November 2026 |

**Split every film.** Keep the pieces inside your working folder, because a file outside it has to go in an upload call of its own. A film under 20 MiB still works: it becomes one piece.

`split-for-artifact.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/split-for-artifact.py (48 lines).
```

```bash
cd my-video
for f in out/batch/mastered/*.mp4; do
  python3 split-for-artifact.py "$f" "out/batch/pieces/$(basename "$f" .mp4)"
done
du -sh out/batch/pieces
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
  file_paths: [out/batch/pieces/film-01/part-01.mp4, out/batch/pieces/film-01/part-02.mp4, ...]
```

**Fill in the data block.** Edit the `video-data` block in the page, with one entry in `videos` for each film. `size` and `sha256` come from that film's `pieces.json`, and the top-level `size` in that file is the whole film's size. This example is invented:

```json
{
	"title": "Your course intros, part 1",
	"intro": "Press the button beside a film to watch it and save it.",
	"videos": [
		{
			"label": "Film 01",
			"filename": "film-01.mp4",
			"size": 25922944,
			"pieces": [
				{"url": "/_blob/7db260ac...", "size": 19922944, "sha256": "794caf1d..."},
				{"url": "/_blob/798cc9b4...", "size": 6000000, "sha256": "786de73f..."}
			]
		}
	],
	"checks": ["Please listen to a few films. I can't hear them."]
}
```

**Publish again,** with the same file path. Do not pass `capabilities`; they carry forward.

**Check the store before you count a film as delivered.** Each line of this listing shows a SHA-256. Compare each with `pieces.json`.

```text
Artifact  action: list  scope: assets  url: <the page>
```

**When a page nears 1 GiB, start the next page,** and tell the user which films are on which. Send each link, and say: "Open it in your browser and press **Get the video** beside a film. **Save to my device** then gives you one normal MP4 file." The page is private. They use its **Share** menu to show someone else.

What was tested: an earlier version of this page delivered one real 19-minute film. This exact version was tested on 9 November 2026 in headless Chrome against a stand-in for claude.ai. A page with two films, one of 1 piece and one of 8 pieces (156 MB), played both, and the saved files matched the originals exactly. Its pieces have been stored and checked on claude.ai, but its buttons have not been pressed there. A page holding many films, and a whole batch through pages, were not tested. If the user asks for Google Drive or another service they use, test that you can reach it first. That setup is not covered here.

### Step 12. Plan for agents stopping

**Subagents can hit a weekly usage limit mid-run.** When that happens they stop, and the batch is half done. So:

- Before you start, ask the user how much allowance they have, and tell them this batch is heavy. No figure for it was measured.

- Each film's work is committed on its own, so a stopped agent loses only its current film.

- **Plan to be able to finish inline**, in the main session, without agents. Keep the brief and the script list in git, and keep a list of what has landed:

```bash
cd my-video
for f in src/films/film-*.entry.tsx; do git log -1 --format="%h %s" -- "$f"; done
git status --short src/films public/films
```

- Do the expensive thinking once: a good kit and two good pilots make every agent cheaper.

- Review agents can be fewer than composing agents. Eight reviewed 58.

### Step 13. A restart in mid-batch

It will probably happen. A restart stops the agents. Their drafts may survive, and then new agents can build on them. Or it may roll back the disk, so commit and push often: about every 30 minutes on a long run.

After a restart:

1. Run `git status --short` and `git log --oneline -10`. See what landed, and what was only drafted.

2. Run `pgrep -af '[r]emotion render'`. Kill any leftovers.

3. Run `bash prep-render.sh` again from the project folder. Tools and `node_modules` may be gone.

4. Start new agents for the films that did not land. Tell each to build on any draft it finds.

5. Run `render-batch.py` again. Its log says what it is skipping, and why.

6. Keep a short `PROJECT.md` in git saying where the batch stands, so a new session can continue.

## How to talk to the user

- Ask one question at a time, with a recommendation. "I recommend two pilot films before the other 56. It costs about an hour, and every fault it finds is fixed once instead of 56 times. OK?"

- Give the real time, up front: "58 films of 2 to 3 minutes took about 7 hours to render on this kind of computer in a past batch, plus about 3 hours to compose. An early estimate of 3 hours was wrong, so I will not promise less."

- Show the pilots and pause for their OK. That is the one moment their taste changes everything cheaply. Ask for their samples and references: looks, voices and fonts here are all only examples.

- Then report per batch, not per film: "20 of 58 done. No failures. Next batch running."

- Tell them what review changed, in a line or two.

- At the end, say where the films are, which branch holds the source, and that it is not on `main` unless you merged it.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `Compositor exited with signal SIGKILL` | The machine ran out of memory, and the system killed the render. There is no swap to fall back on | Cap the frame cache with `--offthreadvideo-cache-size-in-bytes=800000000`, use `--concurrency=2`, and run it again. Nothing is lost. It can look odd afterwards, because `free -m` shows plenty of memory once the render is gone |
| The machine crawls, or the container restarts | Too many renders at once | Every render goes through one lock. |
| An error with the words `exceeded rendering`, on a still while others render | The page took longer than the limit | Add `--timeout=120000` to start. If it still fails, read which `delayRender()` handle the error names. |
| Everyone waits on a lock, and nothing runs | A leftover process holds it | `ps`, then kill the leftover. See Step 4. |
| `fatal: Unable to create '.git/index.lock': File exists` | Two git commands at once | Use the git lock. Remove the lock file only when no git is running. |
| A commit holds another agent's unfinished lines | A shared file was staged whole | Agents report, and one session writes. |
| Files you did not touch are reformatted | A hook ran | `--no-verify` during the batch. Restore only what was clean before you committed. |
| `updates were rejected` on a push | Others pushed first | `git pull --rebase --autostash origin <branch>`, then push. |
| A shared file is suddenly empty | The one-line rewrite | `git checkout -- <file>`, then ask who had uncommitted lines there. |
| The batch stops at about 2 hours, or at 30 minutes | The background limit. 30 minutes means it was started with no `timeout` | Start it with `run_in_background: true` and `timeout: 7200000`, and run it again. It resumes. |
| A loop of jobs ends early with no error | ffmpeg ate stdin | `</dev/null` on every command. |
| A wait never ends | `pgrep -f` matched its own command line | Wait on a file, or use `[r]emotion render`. |
| `moov atom not found`, on some frames | A file was still being written when you bundled | Finish writes first, then bundle again. |
| A film rendered with old words | Stale chunks, or a fingerprint with a hole | Add what is missing to `shared`. Delete that film's folder under `out/batch/chunks/`. |
| `composition ... not in the bundle` | The film is not registered in the main entry | Have the one session add it to `src/Root.tsx`. |
| `film-03: ... does not exist. Fix films.json` | A wrong path in the list | Fix it. This check is on purpose. |
| Agents stop, with a limit message | Weekly usage limit | Step 12: finish inline, or wait for it to reset, and ask the user. |
| Agents wrote to different places | The brief named a path that the tool does not use | Check where a tool really writes before you put the path in a brief. |
| Sheets look right, but one film has a name wrong | An agent invented a name, or a voice misread it | The script's names only. Respell it for the voice. Ask the user to listen to a sample. |
| `exceeds the 30 MiB upload limit` | The file is too big for a chat file | Use the private pages (Step 11). |
| `Piece N arrived damaged` or `did not load (404)`, on a page | A wrong piece or a wrong address in the data block | Check the store against `pieces.json`. Upload the piece again, or copy its `url` again. |
| `No model in ...` from `voice.py` | A restart wiped `~/voice-tools` | Run `bash setup-voice.sh` again. |

## How to check it worked

1. **Everything is current:**

   ```bash
   cd my-video
   python3 render-batch.py films.json
   ```

   It must end with `ALL-CURRENT`. That proves that every final file matches its inputs as they stand now.

2. **A fingerprint really notices.** On one film, add a space to its file, run the script for that film alone, and see it reported as stale. Then undo the edit, and run it again.

3. **The shape of every film:**

   ```bash
   cd my-video
   for f in out/batch/mastered/*.mp4; do echo "$f $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")"; done
   ```

   Look for a film whose length is out of line. A file check cannot tell you the video is good.

4. **The sense.** You looked at a sheet of every film with your own eyes, after the last kit change. A fresh reader looked at each film too.

5. **Sound.** Check a sample:

   ```bash
   cd my-video
   ffmpeg -hide_banner -i out/batch/mastered/film-01.mp4 -af volumedetect -f null - 2>&1 </dev/null | grep -E 'mean_volume|max_volume'
   ```

   `max_volume` must not read `-91.0 dB`. `master-audio.py` printed each film's loudness in its `after` row. Ask the user to listen.

6. **The pages.** Every film's store listing matches its `pieces.json`, and the user pressed **Get the video** on a sample.

7. **The user** watched the pilots and a sample, and said they are right. That is the last check, and only they can do it.
