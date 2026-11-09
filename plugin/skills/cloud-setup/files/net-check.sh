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
