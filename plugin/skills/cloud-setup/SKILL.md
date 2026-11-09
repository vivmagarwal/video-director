---
name: cloud-setup
description: Get a fresh Claude Code cloud container ready to make video with Remotion, from nothing to a checked test render. Use at the start of any cloud session that will make or edit video, and again after a container restart.
---

# Set up a cloud container for video

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It takes an empty cloud container and leaves it able to make video:

- It checks node and python.

- It finds or installs a full ffmpeg.

- It tests which network hosts you can reach.

- It creates a Remotion project from nothing. Remotion is a tool that writes videos as React code.

- It makes sure a Chrome is there, with a fallback when Remotion's own download is refused.

- It runs a smoke test: one still picture and a 2-second video, and you look at the frame.

- It tells you what a restart loses, how to recover, and how the user adds secret keys.

## When to use it (and when not to)

Use it:

- At the start of a cloud session that will make or edit video.

- After a restart, when `node_modules` or the tools have gone. The setup script is safe to run again.

Do not use it:

- When a test render already works in this session. Nothing here would improve it.

- For the render of a long film itself. This skill stops at a working 2-second test.

## What you need before you start

A cloud session (Claude Code on the web). When this was written a session was a Linux x64 container: 4 cores, about 15 GB of memory, no swap (no spill-over to disk when memory runs out), no GPU, cloned fresh and reclaimed after a while.

| Need | How to check | If it is missing |
|---|---|---|
| Node | `node --version` | Ask the user. A cloud container had 22.22.0 in October 2026, and the scripts here were tested on 24.2.0. |
| npm | `npm --version` | Comes with node. |
| Python 3 with pip | `python3 -m pip --version` | Only needed if ffmpeg must come from pip. |
| ffmpeg, full build | The setup script tests it | The setup script installs it. |
| Network to npm | Step 2 below | The user changes it (Step 2 says how). |
| About 2 GB of free disk | `df -h .` | Free some, or ask for a new session. Long videos need much more. |

No key and no account is needed for this skill. No step here costs money.

## Steps

### First, save the files in this guide

Make the project folder and work there. `my-video` is an example name. If the session's repository is the project, use its folder instead.

```bash
mkdir -p my-video
```

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd my-video
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/cloud-setup"
cp -rn "$S/files/." . 2>/dev/null; test -e "net-check.sh" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It saves `net-check.sh`, `setup-video.sh` and the project files shown in Step 5.

### Step 1. Look at the machine

```bash
uname -sm; nproc; free -g | head -2; df -h . | tail -1; node --version; python3 --version; ffmpeg -version 2>/dev/null | head -1
```

Write down the core count, memory and free disk. Later decisions depend on them.

### Step 2. Test the network

Outbound traffic goes through a proxy. The hosts it allows differ per environment and per date, so test instead of assuming. The script below tries each host and prints one line for each.

Save this as `net-check.sh`
```bash
#!/usr/bin/env bash
# Which hosts can this container reach? Prints one line per host. Add your own
# URLs after the command:  bash net-check.sh https://example.com/
URLS=(
  https://registry.npmjs.org/remotion
  https://pypi.org/simple/imageio-ffmpeg/
  https://files.pythonhosted.org/
  https://github.com/
  https://remotion.media/
  https://storage.googleapis.com/chrome-for-testing-public/
  https://fonts.googleapis.com/css2?family=Inter
  https://fonts.gstatic.com/
  https://deb.debian.org/debian/
  https://huggingface.co/
  https://api.elevenlabs.io/v1/models
  "$@"
)
body=$(mktemp); err=$(mktemp)
for url in "${URLS[@]}"; do
  code=$(curl -sS -o "$body" -m 15 -w '%{http_code}' "$url" 2>"$err" </dev/null)
  if grep -qs 'allowlist' "$body" || grep -qs 'CONNECT tunnel failed' "$err"; then
    verdict="REFUSED by the proxy"
  elif [ "$code" = 000 ]; then
    verdict="NOT REACHED: $(head -c 80 "$err")"
  else
    verdict="open"
  fi
  printf '%-4s %-22s %s\n' "$code" "$verdict" "$url"
done
rm -f "$body" "$err"
```

```bash
cd my-video
bash net-check.sh
```

Add your own hosts after the command if the job needs them, for example `bash net-check.sh https://api.example.com/`.

**How to read a line.** The first column is the HTTP status. A refusal is `CONNECT tunnel failed` or `Host not in allowlist`. Any other status means the host answered.

| You see | What it means |
|---|---|
| Any status, verdict `open` | The host answered. This counts even for `403` or `404`: Google's Chrome download host answers `403` to its bare folder address, and a key-protected API answers `401`. |
| `000  REFUSED by the proxy` | The proxy said no. By hand, curl prints `curl: (56) CONNECT tunnel failed, response 403`. |
| `403  REFUSED by the proxy` | The reply body says `Host not in allowlist`. Same meaning. |
| `000  NOT REACHED: ...` | No answer: a timeout or a name that did not resolve. Run it once more before you believe it. |

**What each host is for, and what past sessions saw.** These readings are old. Yours may differ.

Anthropic's docs list the hosts a session may reach at the default **Trusted** network level (checked November 2026, at `https://code.claude.com/docs/en/cloud-environments`). The third column says what its list and real sessions showed. Real sessions in 2026 did not always match the list, so test.

| Host | Needed for | Default list, and seen from a cloud container | If it is refused |
|---|---|---|---|
| `registry.npmjs.org` | Remotion and every npm package | On the list. Reachable, Sep and Oct 2026 | Nothing works. Ask the user to allow it. |
| `pypi.org`, `files.pythonhosted.org` | ffmpeg from pip, Python tools | On the list. Reachable, Sep 2026 | Only matters if the image has no full ffmpeg. |
| `github.com` and its release files | Models and tools from GitHub releases | On the list. Reachable, Sep 2026 | Ask, if the job needs them. |
| `raw.githubusercontent.com` | Single files from any public repository | On the list | Ask, if the job needs them. |
| A clone or archive of a public repository that is not attached to this session | Using someone else's code | The GitHub proxy refuses archive downloads with a 403 that says `is not enabled for this session`. A plain `git clone` was not measured | Fetch single files from `raw.githubusercontent.com`, or ask the user to add that repository to the session. |
| `remotion.media` | Remotion's own Chrome download | Not on the list | The setup script falls back to Google. |
| `storage.googleapis.com` | Google's Chrome for Testing | On the list. Reachable, Sep and Oct 2026 | With `remotion.media` also refused, there is no Chrome. Ask the user to allow one. |
| `fonts.googleapis.com`, `fonts.gstatic.com` | `@remotion/google-fonts` | `curl` reaches them, but Chrome refused them in a real session on 9 November 2026 (`net::ERR_CERT_AUTHORITY_INVALID`), so a `curl` pass here proves nothing about a render | Use the npm way in Step 7. |
| `archive.ubuntu.com` | `apt` | On the list, and the docs describe the image as Ubuntu 24.04. `deb.debian.org` was refused in Sep 2026 | The setup script falls back to pip. |
| `huggingface.co` | Many AI models | Not on the list. Refused, Sep 2026. A session in Oct 2026 seemed to reach it, in an environment that may have allowed it | Look for the model on GitHub releases or PyPI, or ask. |
| `api.elevenlabs.io` | One paid voice service | Not on the list. One session reported it unreachable. Test it | Only matters if the user wants that service. |

On an earlier Remotion, cloud sessions saw `storage.googleapis.com` reachable while the host that served its Chrome was refused. That is why the Google fallback exists.

**What is already on the machine.** Anthropic's docs list Python with pip and uv, Node 20 to 22 with npm, git, gh, and Chrome for Testing at `/usr/bin/google-chrome` (`CHROME_PATH`), on about 4 vCPUs, 16 GB of memory and 30 GB of disk. Check with `check-tools`. Using that Chrome for rendering was not tried, so this guide fetches the exact version Remotion expects. Bun has known trouble with the session's proxy, so this guide uses npm.

**To open a host, the user does this.** In the session's cloud environment menu, choose **Edit**, then **Network access**. Add the host under **Allowed domains**. Leave **Allow package managers** ticked. These labels were right when this was written. You cannot do this yourself. A new session may be needed before it takes effect (not measured).

### Step 3. Tell the user about the licence, once

Say this plainly when you start a Remotion project:

> Remotion is free for individuals, non-profits, and for-profit companies with up to 3 employees. Other companies need a company licence. The terms are at remotion.dev/license and in `node_modules/remotion/LICENSE.md` after install.

Do not ask them to prove anything. It is their decision.

### Step 4. Run the setup script

It does everything below in order, and skips what is already there. It never overwrites a file you have.

1. Checks node, npm and python.

2. Looks for a full ffmpeg. It asks the ffmpeg to do three jobs: `tile` (contact sheets), `volumedetect` (is there sound) and `loudnorm` (set the loudness). It tries the one on the PATH, then `apt` if you are root (the proxy may refuse it), then `pip install imageio-ffmpeg`.

3. Writes the project files, if missing.

4. Installs Remotion. Every `remotion` and `@remotion/*` package must be the exact same version, so it pins them.

5. Finds an ffprobe (the tool that reads a video's facts). pip's ffmpeg comes without one, so it falls back to the one inside Remotion's own package.

6. Gets Chrome: Remotion's download first, then Google's copy of the same version.

`setup-video.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/setup-video.sh (253 lines).
```

```bash
cd my-video
bash setup-video.sh .
```

**Bash calls run in a fresh shell.** A `cd` or `export` may not carry over to the next call, so start each call with `cd my-video`. If the script tells you to export a PATH, add that too.

**A real cloud run on 9 November 2026** (Remotion 4.0.542, 4 cores, 16 GB, no swap) confirmed that the Chrome fallback works. An earlier copy of this script printed `getaddrinfo ENOTFOUND remotion.media` along the way, which is harmless.

Tested on a Mac (Apple Silicon, Remotion 4.0.541): from an empty folder in about 25 s, about 1 s on a second run, and about 18 s with every fallback forced and `node_modules` already there. No setup time was measured in a cloud container. **Not run on Linux.** The Linux branches (the `linux64` download and `ldd`) have not been run. The Linux pip ffmpeg was read, not run: imageio-ffmpeg 0.7.0 holds ffmpeg 7.0.2, and its text contains the tile, volumedetect and loudnorm filters. An earlier cloud session used that same package.

**You do not need a separate compositor download.** The compositor is Remotion's native render helper. `npm i remotion @remotion/cli` pulls the right one by itself on Linux, through `@remotion/compositor-linux-x64-gnu`. You would need `--binaries-directory` only if npm were refused, and then little else would work either.

**Do not use the compositor's own ffmpeg for your work.** In the Linux package at 4.0.541 its filter library holds `loudnorm` but not `tile` or `volumedetect` (read from the file, not run). An earlier cloud session got `Filter not found` from it.

### Step 5. The project files, if you prefer to write them yourself

The setup script writes these files, and the copy step has already saved all of them except `package.json`. They are here so you can see exactly what a working project is, or repair one.

A finished `package.json` looks like this. The setup script writes it, with the current versions:

```json
{
  "name": "video",
  "private": true,
  "type": "module",
  "dependencies": {
    "@remotion/cli": "4.0.541",
    "react": "19.3.1",
    "react-dom": "19.3.1",
    "remotion": "4.0.541"
  }
}
```

These versions are examples from November 2026. Get the current one with `npm view remotion version`, and use it for every Remotion package.

A project **must** have this file, or every command stops with `Could not find a tsconfig.json file in your project`.

Save this as `tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "noEmit": true
  },
  "include": ["src"]
}
```

This file holds the settings every command reads. Run commands from the folder that holds it, or they will not see it. If `remotion.config.ts` already exists, keep it and add only the lines it lacks.

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

// setup-video.sh puts a Chrome here only when Remotion's own download was refused.
const toolsDir = process.env.VIDEO_TOOLS ?? join(homedir(), '.cache/video-tools');
const chrome = join(toolsDir, 'chrome/current/chrome-headless-shell');
if (existsSync(chrome)) {
  Config.setBrowserExecutable(chrome);
}
```

The smoke test has a file of its own, so it can never get in the way of a real project's `src/index.ts` or `src/Root.tsx`. Delete it when you like.

`src/smoke.tsx`, which the copy step puts in your folder:

```tsx
# In this skill's files folder: files/src/smoke.tsx (45 lines).
```

Save this as `.gitignore`
```text
node_modules/
out/
build/
.cache/
```

If you wrote these files by hand, write `package.json` too, then run `npm install`.

### Step 6. Smoke test: look at a real frame

```bash
cd my-video
npx remotion compositions src/smoke.tsx
npx remotion still src/smoke.tsx smoke out/smoke.png --frame=30
npx remotion render src/smoke.tsx smoke out/smoke.mp4 --offthreadvideo-cache-size-in-bytes=800000000
ffprobe -v error -show_entries stream=codec_name,width,height,nb_frames,duration -of compact out/smoke.mp4
```

The last line should read something like `stream|codec_name=h264|width=1920|height=1080|duration=2.000000|nb_frames=60`.

**Then open `out/smoke.png` with the Read tool and look at it.** You should see the words "Smoke test" in white on dark blue, and an orange square. A file check cannot tell you the video is good. Your eyes can.

A plain `sans-serif` word in a clean container depends on what fonts the image holds. If the words are missing or show as boxes, the image has no usable fonts, and the next section is the fix.

### Step 7. Fonts

Fonts must be loaded in code. Without that you silently get a fallback serif, and nothing warns you.

**In a cloud session, use a font package from npm.** It puts the font in the project, so a render needs no font host:

```bash
cd my-video
npm i @fontsource/lobster
```

```tsx
import '@fontsource/lobster/400.css';
// then style={{fontFamily: 'Lobster'}}
```

This was rendered on a Mac with the network denied, and the frame was looked at: the font was right.

The other way is Google Fonts through Remotion. It downloads the font at render time. **In a real cloud session on 9 November 2026 this failed:** Chrome Headless Shell refused `fonts.gstatic.com` with `net::ERR_CERT_AUTHORITY_INVALID`, because it does not trust the session proxy's certificate, although `curl` to the same host worked. Use it only outside a cloud session:

```bash
cd my-video
npm i --save-exact @remotion/google-fonts@$(node -p "require('remotion/package.json').version")
```

```tsx
import {loadFont} from '@remotion/google-fonts/Pacifico';
const {fontFamily} = loadFont();
// then style={{fontFamily}}
```

A blocked download does not fall back quietly. The render stops after 30 seconds with:

```text
Error: Timeout (30000ms) exceeded rendering the component initially. Open delayRender() handles: "1. Fetching Pacifico font ...
```

If code you copied imports `@remotion/google-fonts/<Name>`, replace that import with the font package's CSS, and set `fontFamily` to the font's name. **Never use `--ignore-certificate-errors`:** the session's proxy rules forbid turning off certificate checks. One idea nobody has tried: add the proxy's certificate to Chrome's own store, with `certutil`.

The same cause probably affects anything else a page loads from the internet while rendering, such as `<Img src="https://...">`, though only fonts were seen to fail. So download such files with `curl` into `public/`, and use `staticFile`.

Lobster and Pacifico are only examples. Use the user's brand fonts or taste. If they have font files of their own, ask for them.

### Step 8. Choosing how Chrome draws (GL)

The config above sets `angle`. It worked with no GPU in the cloud container, and it was fast. Keep it.

| Setting | When | What was measured on a 4-core cloud container, 2026 |
|---|---|---|
| `angle` (the default here) | Almost everything: text, SVG, CSS, video | 24 frames a second on one simple film. Expect 5 to 13 on most films, measured on an older Remotion |
| `--gl=swangle` | Only a scene that really uses WebGL (three.js, shaders, canvas effects) and that fails on `angle` with `Error creating WebGL context`, or comes out blank | 5 frames a second on that simple film. It also painted a ghost image of a list item into whole renders that stills did not show. |

After any `swangle` render, scan the finished file for ghosts at several frames a second. A still will not catch them.

### Step 9. Keys

Some jobs need a secret key for a paid service. **Never ask for a key in the chat, never print one, never write one into a file in git.**

**How the user adds one.** In the session's cloud environment menu, choose **Edit**, and add a line to the environment variables, for example `SOME_API_KEY=...`. Save. A new session picks it up. Whether a running session does was not measured, so expect to start a new one. A `.env` file in the repo is the wrong place: it can end up in git.

Give them the exact name you need and these steps. Then check it this way, which shows names and never values:

```bash
env | cut -d= -f1 | grep -E 'KEY|TOKEN|SECRET'
[ -n "${SOME_API_KEY:-}" ] && echo "SOME_API_KEY is set" || echo "SOME_API_KEY is missing"
```

Do not run a bare `env`, `printenv` or `echo $SOME_API_KEY`: the value lands in the transcript.

Two traps:

- **A key that is present may still not work.** One key in the environment answered `401` on every request. Test it with a free call, such as listing models, before you plan around it.

- **A key can have a name no tool reads.** A speech service's key had an extra word on the end of its name, so the tool looking for the usual name did not find it. Ask the user before you map one name to another.

### Step 10. Know what a restart loses

Two different things happen, and you cannot choose which:

| Event | Running processes | Files | What to do |
|---|---|---|---|
| Worker restart | All killed, `nohup` included | Usually survive | Check what is still running, then relaunch your jobs. |
| Container rebuild or restart | All killed | The disk can roll back to an older snapshot. `node_modules`, anything outside git, and commits you did not push can go. | Run the setup script again and rebuild the rest. |

**Only what is pushed to the remote is sure to survive.** A restart can take a render, the working video files, the transcripts and a finished commit that was not pushed. Doing that work again took an hour and a half in one case. Other times, uncommitted drafts survive. Plan for the worse case.

To recover:

```bash
cd my-video
git status --short; git log --oneline -3; git log origin/$(git branch --show-current)..HEAD --oneline
ls node_modules/.bin/remotion
bash setup-video.sh .
```

Keep `setup-video.sh` in the repo and commit it, so it comes back after a rollback. Commit by path and push in the same command, as often as you can bear.

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs.

```bash
cd my-video
git add path/to/file && git commit -m "what changed" -- path/to/file && git push -u origin HEAD
```

Another way, not tried: Claude Code can run a command when a session starts (a SessionStart hook), which could run this script for you. Check its current documentation if the user wants that.

## How to talk to the user

- Use plain words. Say "the tool that draws frames", not "the compositor", unless they ask.

- Ask one question at a time, and give your recommendation with it. For example, when a download host is refused and the fallback works: "All good. Nothing needed from you."

- Ask them to act only when you cannot go on, and give the exact clicks: "Open the environment menu at the top of this session, choose Edit, then Network access, add `pypi.org` under Allowed domains, and save."

- Tell them the licence note once.

- Show them the smoke frame when you finish, with one line: "The setup works. Here is a test frame." If a director skill sent you, skip the test frame.

- Do not read them the host table unless something is refused.

## For someone who makes videos often

The environment menu has a **Setup script** box. It runs once as root and is saved with the environment if it finishes in about five minutes, so later sessions start with everything on disk. This was not tried. Its contents could be the install lines from `setup-video.sh`. Check the docs first: `https://code.claude.com/docs/en/cloud-environments`.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `Could not find a tsconfig.json file in your project` | No `tsconfig.json` | Add the file from Step 5. |
| `curl: (56) CONNECT tunnel failed, response 403` | The proxy refused the host | Step 2: ask the user to allow it, or use the fallback. |
| `Host not in allowlist`, or `Received a status code of 403` during a Chrome download | The proxy refused Chrome's host | The setup script falls back to Google by itself. By hand, see below. |
| `npm warn tar TAR_ENTRY_ERROR ENOSPC: no space left on device`, then `npm error could not determine executable to run` | The disk filled during install, so the package never landed (seen on a Mac while writing this) | `df -h .`, free space, delete `node_modules`, and run the setup again. |
| `Filter not found` for `tile` or `volumedetect` | You used a cut-down ffmpeg, such as Remotion's own | Use the one the setup script put on the PATH. |
| `ffprobe: command not found` | The pip ffmpeg has no ffprobe, or the PATH did not carry over | Run the setup script again. Start the call with the `export PATH` line it printed. |
| `SETUP FAILED: Chrome is missing N system libraries` | The image lacks libraries Chrome needs | `apt install -y libnss3 libdbus-1-3 libatk1.0-0 libasound2t64 libxrandr2 libxkbcommon-dev libxfixes3 libxcomposite1 libxdamage1 libgbm-dev libcups2 libcairo2 libpango-1.0-0 libatk-bridge2.0-0` (Remotion's list for Ubuntu 24.04, on its Linux Dependencies page). If apt is refused, ask the user to allow `deb.debian.org` or the mirror the image uses. An earlier cloud container had 0 missing. |
| A version mismatch warning from `npx remotion versions` | Remotion packages differ in version | Set them all to one exact version. Delete `node_modules`, then run `npm install`. |
| `Error creating WebGL context` | A WebGL scene on `angle` | `--gl=swangle` for that render only (Step 8). |
| A serif font you did not ask for | The font was not loaded | Step 7. |
| An error with the words `exceeded rendering` that names a font, such as `Fetching Pacifico font`, or `net::ERR_CERT_AUTHORITY_INVALID` | Chrome refused the font host through the session proxy | Use `@fontsource/<name>` (Step 7). Never `--ignore-certificate-errors`. |
| An error with the words `exceeded rendering` and no font in it | The page took longer than the limit, often on a busy machine | Add `--timeout=120000` to start. If it still fails, read which `delayRender()` handle it names. |
| `Detected differing memory amounts` | The container reports memory two ways | Harmless. Remotion uses the lower figure. |
| A command dies at 10 minutes | The Bash tool's limit | Run long work with `run_in_background: true` and `timeout: 7200000`. Without that timeout it stops at 30 minutes, and with it at 2 hours. |
| A wait loop never ends, or `pkill` kills your own shell | `pgrep -f` and `pkill -f` match their own command line | Write the pattern as `[r]emotion render`, or wait on files. |
| `sleep` is refused | Bare `sleep` is blocked | Wait with a Monitor until-loop or a bounded check loop. |

**The Chrome fallback by hand.** Read the version Remotion wants, and download that same version:

```bash
V=$(grep -oE "TESTED_VERSION = '[^']+'" node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2); echo "$V"
curl -sSfL -o /tmp/chs.zip "https://storage.googleapis.com/chrome-for-testing-public/$V/linux64/chrome-headless-shell-linux64.zip"
mkdir -p ~/.cache/video-tools/chrome && python3 -m zipfile -e /tmp/chs.zip /tmp/chs
mv /tmp/chs/chrome-headless-shell-linux64 ~/.cache/video-tools/chrome/current
chmod -R u+x ~/.cache/video-tools/chrome/current
printf %s "$V" > ~/.cache/video-tools/chrome/VERSION
```

The version was 158.0.8127.2 at Remotion 4.0.541. A `require()` of that file fails, because the package does not export it, so use the `grep`. The `remotion.config.ts` above picks this Chrome up by itself. With a config of your own, pass `--browser-executable=$HOME/.cache/video-tools/chrome/current/chrome-headless-shell` on every call. Remotion normally keeps its own copy in `node_modules/.remotion/chrome-headless-shell`.

On a Mac, the config route used the Google copy with no new download, and its still was byte-identical to one from Remotion's own Chrome. `npx remotion browser ensure` with the network denied exits with code 1, which is how the script knows to fall back.

## How to check it worked

All of these must hold. Run them from the project folder (start each call with `cd my-video`):

1. `npx remotion versions` ends with `All packages have the correct version.`

2. `ffmpeg -hide_banner -filters | grep -wE 'tile|volumedetect|loudnorm'` prints three lines.

3. `ffprobe -version` prints a version.

4. `out/smoke.mp4` has 60 frames and lasts 2.0 seconds.

5. You opened `out/smoke.png` with the Read tool and saw the words and the orange square. In the video, the square moves: take a frame from the start and the end to prove it:

```bash
cd my-video
ffmpeg -v error -y -i out/smoke.mp4 -vf "select='eq(n,0)+eq(n,59)',scale=480:-1,tile=2x1" -frames:v 1 out/ends.png
```

Open `out/ends.png`. The square must be on the left in the first half, and on the right in the second.
