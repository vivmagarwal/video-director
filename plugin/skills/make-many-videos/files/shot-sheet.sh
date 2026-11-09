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
