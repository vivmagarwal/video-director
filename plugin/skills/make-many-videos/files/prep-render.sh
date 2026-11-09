#!/usr/bin/env bash
# Make an existing Remotion project able to render on this machine.
#
#   bash prep-render.sh     (run it in the project folder; safe to run again)
#
# It installs the packages, finds a full ffmpeg and an ffprobe, and makes sure there
# is a Chrome. It adds a tsconfig.json only if there is none.
set -euo pipefail

TOOLS=${VIDEO_TOOLS:-$HOME/.cache/video-tools}
if [ -z "${VIDEO_BIN:-}" ]; then
  if [ -w /usr/local/bin ]; then VIDEO_BIN=/usr/local/bin; else VIDEO_BIN=$HOME/.local/bin; fi
fi
FORCE=${FORCE_FALLBACKS:-0}
mkdir -p "$TOOLS" "$VIDEO_BIN"
export PATH="$VIDEO_BIN:$PATH"
die() { printf 'PREP FAILED: %s\n' "$*" >&2; exit 1; }
[ -f package.json ] || die "no package.json here. Run this in the project folder."
command -v node >/dev/null || die "node is not installed"

# The project files a render cannot start without.
if [ ! -f tsconfig.json ]; then
  echo '{"compilerOptions":{"target":"ES2022","module":"ES2022","moduleResolution":"bundler","jsx":"react-jsx","strict":true,"skipLibCheck":true,"esModuleInterop":true,"noEmit":true},"include":["src"]}' > tsconfig.json
  echo "wrote tsconfig.json"
fi
[ -f remotion.config.ts ] || die "no remotion.config.ts here. Copy this skill's files again."

# Packages. Every remotion package must be the exact same version.
[ -x node_modules/.bin/remotion ] || npm install --no-audit --no-fund </dev/null
npx --no-install remotion versions </dev/null | tail -1

# ffmpeg. We ask it to do the jobs, because a path says nothing about its filters.
is_full_ffmpeg() {
  "$1" -v error -f lavfi -i testsrc2=d=1:s=64x64 -f lavfi -i sine=d=1 \
    -filter_complex '[0:v]tile=2x2[v];[1:a]volumedetect,loudnorm[a]' \
    -map '[v]' -map '[a]' -f null - </dev/null >/dev/null 2>&1
}
if [ "$FORCE" = 1 ] || ! command -v ffmpeg >/dev/null || ! is_full_ffmpeg "$(command -v ffmpeg)"; then
  echo "installing a static ffmpeg from PyPI"
  python3 -m pip install -q --target "$TOOLS/ffmpeg-py" imageio-ffmpeg </dev/null ||
    die "pip could not install imageio-ffmpeg. Check that pypi.org and files.pythonhosted.org are allowed."
  FF=$(ls "$TOOLS"/ffmpeg-py/imageio_ffmpeg/binaries/ffmpeg-* | head -1)
  chmod +x "$FF"
  ln -sf "$FF" "$VIDEO_BIN/ffmpeg"
fi
is_full_ffmpeg ffmpeg || die "this ffmpeg cannot do tile, volumedetect and loudnorm"

# ffprobe. Remotion's own works, through a wrapper, because it loads libraries from its folder.
if [ "$FORCE" = 1 ] || ! command -v ffprobe >/dev/null; then
  PROBE=$(ls node_modules/@remotion/compositor-*/ffprobe 2>/dev/null | head -1 || true)
  [ -n "$PROBE" ] || die "no ffprobe on PATH and none in Remotion's compositor package"
  PROBE_DIR=$(pwd)/$(dirname "$PROBE")
  rm -f "$VIDEO_BIN/ffprobe"
  printf '#!/bin/sh\nLD_LIBRARY_PATH="%s" DYLD_LIBRARY_PATH="%s" exec "%s/ffprobe" "$@"\n' \
    "$PROBE_DIR" "$PROBE_DIR" "$PROBE_DIR" > "$VIDEO_BIN/ffprobe"
  chmod +x "$VIDEO_BIN/ffprobe"
fi
ffprobe -version | head -1

# Chrome. Remotion's own download first; Google's copy of the same version if refused.
VERSION=$(grep -oE "TESTED_VERSION = '[^']+'" \
  node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js | cut -d"'" -f2)
OWN=$TOOLS/chrome/current/chrome-headless-shell
if [ -x "$OWN" ] && [ "$(cat "$TOOLS/chrome/VERSION" 2>/dev/null)" = "$VERSION" ]; then
  CHROME=$OWN
elif [ "$FORCE" != 1 ] && npx --no-install remotion browser ensure </dev/null >/dev/null 2>&1; then
  CHROME=$(find node_modules/.remotion/chrome-headless-shell -type f -name chrome-headless-shell | head -1)
else
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) PLATFORM=linux64 ;;
    Darwin-arm64) PLATFORM=mac-arm64 ;;
    *) die "no Chrome route written for $(uname -s)-$(uname -m)" ;;
  esac
  URL=https://storage.googleapis.com/chrome-for-testing-public/$VERSION/$PLATFORM/chrome-headless-shell-$PLATFORM.zip
  echo "downloading Chrome $VERSION from Google"
  rm -rf "$TOOLS/chrome"
  mkdir -p "$TOOLS/chrome"
  curl -sSfL -o "$TOOLS/chrome/chs.zip" "$URL" || die "could not download $URL"
  python3 -m zipfile -e "$TOOLS/chrome/chs.zip" "$TOOLS/chrome/unzip"
  mv "$TOOLS/chrome/unzip/chrome-headless-shell-$PLATFORM" "$TOOLS/chrome/current"
  rm -rf "$TOOLS/chrome/unzip" "$TOOLS/chrome/chs.zip"
  chmod -R u+x "$TOOLS/chrome/current"
  printf %s "$VERSION" > "$TOOLS/chrome/VERSION"
  CHROME=$OWN
  grep -q setBrowserExecutable remotion.config.ts ||
    echo "Your remotion.config.ts does not know this Chrome. Add its Chrome lines from the guide."
fi
"$CHROME" --version
if command -v ldd >/dev/null && ldd "$CHROME" | grep "not found"; then
  die "Chrome is missing the system libraries listed above"
fi
echo "ready. ffmpeg: $(command -v ffmpeg). If this is not /usr/local/bin, run: export PATH=\"$VIDEO_BIN:\$PATH\""
