#!/usr/bin/env bash
# Get a cloud container ready to make video with Remotion.
#
#   bash setup-video.sh [project-folder]     (default: the current folder)
#
# Safe to run again. Each step checks for its result first and skips itself when
# it is already there. It never overwrites a file you already have.
#
# Settings, all optional:
#   VIDEO_TOOLS       where downloads go (default ~/.cache/video-tools)
#   VIDEO_BIN         where ffmpeg and ffprobe links go (default /usr/local/bin
#                     when writable, else ~/.local/bin)
#   FORCE_FALLBACKS=1 use pip's ffmpeg, Remotion's ffprobe and Google's Chrome
#                     even when the normal route works
set -euo pipefail

PROJECT=${1:-.}
TOOLS=${VIDEO_TOOLS:-$HOME/.cache/video-tools}
FORCE=${FORCE_FALLBACKS:-0}
if [ -z "${VIDEO_BIN:-}" ]; then
  if [ -w /usr/local/bin ]; then VIDEO_BIN=/usr/local/bin; else VIDEO_BIN=$HOME/.local/bin; fi
fi
mkdir -p "$PROJECT" "$TOOLS" "$VIDEO_BIN"
cd "$PROJECT"
PROJECT=$(pwd)
export PATH="$VIDEO_BIN:$PATH"

say() { printf '\n== %s\n' "$*"; }
die() { printf 'SETUP FAILED: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 1. node, python
say "node and python"
command -v node >/dev/null || die "node is not installed."
command -v npm >/dev/null || die "npm is not installed."
command -v python3 >/dev/null || die "python3 is not installed."
node --version
python3 --version

# ---------------------------------------------------------------- 2. a full ffmpeg
# A full ffmpeg can do all three jobs below. We ask it to do them, because a path
# or a version number says nothing about which filters a build has.
is_full_ffmpeg() {
  "$1" -v error -f lavfi -i testsrc2=d=1:s=64x64 -f lavfi -i sine=d=1 \
    -filter_complex '[0:v]tile=2x2[v];[1:a]volumedetect,loudnorm[a]' \
    -map '[v]' -map '[a]' -f null - </dev/null >/dev/null 2>&1
}
say "ffmpeg (needs tile, volumedetect, loudnorm)"
FF=
if [ "$FORCE" != 1 ] && command -v ffmpeg >/dev/null && is_full_ffmpeg "$(command -v ffmpeg)"; then
  FF=$(command -v ffmpeg)
fi
if [ -z "$FF" ] && [ "$FORCE" != 1 ] && [ "$(id -u)" = 0 ] && command -v apt-get >/dev/null; then
  echo "trying apt (the proxy may refuse it)"
  if apt-get update -qq </dev/null >/dev/null 2>&1 && apt-get install -y -qq ffmpeg </dev/null >/dev/null 2>&1; then
    if command -v ffmpeg >/dev/null && is_full_ffmpeg "$(command -v ffmpeg)"; then FF=$(command -v ffmpeg); fi
  else
    echo "apt did not work, moving on to pip"
  fi
fi
if [ -z "$FF" ]; then
  echo "installing a static ffmpeg from PyPI (imageio-ffmpeg)"
  if ! ls "$TOOLS"/ffmpeg-py/imageio_ffmpeg/binaries/ffmpeg-* >/dev/null 2>&1; then
    python3 -m pip install -q --target "$TOOLS/ffmpeg-py" imageio-ffmpeg </dev/null ||
      die "pip could not install imageio-ffmpeg. Check that pypi.org and files.pythonhosted.org are allowed."
  fi
  FF=$(ls "$TOOLS"/ffmpeg-py/imageio_ffmpeg/binaries/ffmpeg-* | head -1)
  chmod +x "$FF"
  is_full_ffmpeg "$FF" || die "the pip ffmpeg cannot do tile, volumedetect and loudnorm: $FF"
  ln -sf "$FF" "$VIDEO_BIN/ffmpeg"
fi
"$FF" -version | head -1

# ---------------------------------------------------------------- 3. project files
say "project files in $PROJECT (only the missing ones)"
if [ ! -f package.json ]; then
  cat > package.json <<'JSON'
{
  "name": "video",
  "private": true,
  "type": "module"
}
JSON
fi
if [ ! -f tsconfig.json ]; then
  cat > tsconfig.json <<'JSON'
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
JSON
fi
if [ ! -f remotion.config.ts ]; then
  cat > remotion.config.ts <<'TS'
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
TS
fi
mkdir -p src
if [ ! -f src/smoke.tsx ]; then
  cat > src/smoke.tsx <<'TSX'
import {AbsoluteFill, Composition, interpolate, registerRoot, useCurrentFrame} from 'remotion';

const Smoke = () => {
  const frame = useCurrentFrame();
  const x = interpolate(frame, [0, 59], [0, 1400]);
  return (
    <AbsoluteFill style={{backgroundColor: '#14213d'}}>
      <div
        style={{
          position: 'absolute',
          top: 200,
          left: 100,
          color: 'white',
          fontFamily: 'sans-serif',
          fontSize: 120,
        }}
      >
        Smoke test
      </div>
      <div
        style={{
          position: 'absolute',
          top: 600,
          left: 100 + x,
          width: 200,
          height: 200,
          backgroundColor: '#fca311',
        }}
      />
    </AbsoluteFill>
  );
};

export const Root = () => (
  <Composition
    id="smoke"
    component={Smoke}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={60}
  />
);

registerRoot(Root);
TSX
fi
if [ ! -f .gitignore ]; then
  printf 'node_modules/\nout/\nbuild/\n.cache/\n' > .gitignore
fi

# ---------------------------------------------------------------- 4. npm packages
say "npm packages"
if [ ! -x node_modules/.bin/remotion ]; then
  if grep -q '"remotion"' package.json; then
    npm install --no-audit --no-fund </dev/null
  else
    V=$(npm view remotion version </dev/null) ||
      die "npm cannot reach its registry. Check that registry.npmjs.org is allowed."
    npm install --no-audit --no-fund --save-exact \
      "remotion@$V" "@remotion/cli@$V" react react-dom </dev/null
  fi
fi
npx --no-install remotion versions </dev/null | tail -1

# ---------------------------------------------------------------- 5. ffprobe
say "ffprobe"
if [ "$FORCE" = 1 ] || ! command -v ffprobe >/dev/null; then
  PROBE=$(ls node_modules/@remotion/compositor-*/ffprobe 2>/dev/null | head -1 || true)
  [ -n "$PROBE" ] || die "no ffprobe on PATH and none in Remotion's compositor package"
  # A small wrapper, because this ffprobe loads its libraries from its own folder.
  PROBE_DIR=$PROJECT/$(dirname "$PROBE")
  rm -f "$VIDEO_BIN/ffprobe"
  cat > "$VIDEO_BIN/ffprobe" <<WRAP
#!/bin/sh
LD_LIBRARY_PATH="$PROBE_DIR" DYLD_LIBRARY_PATH="$PROBE_DIR" exec "$PROBE_DIR/ffprobe" "\$@"
WRAP
  chmod +x "$VIDEO_BIN/ffprobe"
fi
ffprobe -version | head -1

# ---------------------------------------------------------------- 6. Chrome
say "Chrome Headless Shell"
CHROME_VERSION=$(grep -oE "TESTED_VERSION = '[^']+'" \
  node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2)
[ -n "$CHROME_VERSION" ] || die "could not read TESTED_VERSION from @remotion/renderer"
OWN=$TOOLS/chrome/current/chrome-headless-shell
CHROME_PATH=
if [ -x "$OWN" ] && [ "$(cat "$TOOLS/chrome/VERSION" 2>/dev/null)" = "$CHROME_VERSION" ]; then
  CHROME_PATH=$OWN
elif [ "$FORCE" != 1 ] && npx --no-install remotion browser ensure </dev/null >"$TOOLS/browser-ensure.log" 2>&1; then
  CHROME_PATH=$(find node_modules/.remotion/chrome-headless-shell -type f -name chrome-headless-shell | head -1)
fi
if [ -z "$CHROME_PATH" ]; then
  echo "Remotion's own Chrome download is not reachable, which is normal on a cloud session's default network. Using Google's copy of Chrome $CHROME_VERSION."
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) PLATFORM=linux64 ;;
    Darwin-arm64) PLATFORM=mac-arm64 ;;
    *) die "no Chrome for Testing route written for $(uname -s)-$(uname -m)" ;;
  esac
  URL=https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/$PLATFORM/chrome-headless-shell-$PLATFORM.zip
  rm -rf "$TOOLS/chrome"
  mkdir -p "$TOOLS/chrome"
  curl -sSfL -o "$TOOLS/chrome/chs.zip" "$URL" ||
    die "could not download $URL. Check that storage.googleapis.com is allowed."
  python3 -m zipfile -e "$TOOLS/chrome/chs.zip" "$TOOLS/chrome/unzip"
  mv "$TOOLS/chrome/unzip/chrome-headless-shell-$PLATFORM" "$TOOLS/chrome/current"
  rm -rf "$TOOLS/chrome/unzip" "$TOOLS/chrome/chs.zip"
  chmod -R u+x "$TOOLS/chrome/current"
  printf %s "$CHROME_VERSION" > "$TOOLS/chrome/VERSION"
  CHROME_PATH=$OWN
fi
"$CHROME_PATH" --version
if command -v ldd >/dev/null; then
  MISSING=$(ldd "$CHROME_PATH" | grep -c "not found" || true)
  if [ "$MISSING" != 0 ]; then
    ldd "$CHROME_PATH" | grep "not found"
    die "Chrome is missing $MISSING system libraries, listed above."
  fi
fi

say "ready"
echo "project:  $PROJECT"
echo "ffmpeg:   $(command -v ffmpeg)"
echo "ffprobe:  $(command -v ffprobe)"
echo "chrome:   $CHROME_PATH"
if [ "$VIDEO_BIN" != /usr/local/bin ]; then
  echo "add this to every shell command: export PATH=\"$VIDEO_BIN:\$PATH\""
fi
