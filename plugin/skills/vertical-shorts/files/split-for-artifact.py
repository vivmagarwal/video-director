#!/usr/bin/env python3
"""Split a finished video into pieces an Artifact's asset store accepts.

usage: split-for-artifact.py <video.mp4> <out-dir>

An asset is capped at 20 MiB, and the store refuses a binary piece whose first
non-blank byte is "<". So each piece is 19 MiB, its boundary moved back a byte
at a time until it does not start that way: the same rule the upload page
uses going the other way. Writes out-dir/part-NN.mp4
and out-dir/pieces.json, with each piece's size and SHA-256 for the page that
joins them to check.
"""

import hashlib
import json
import pathlib
import sys

CHUNK = 19 * 1024 * 1024
BLANK = b" \t\n\r\x0c"

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
data = src.read_bytes()
out.mkdir(parents=True, exist_ok=True)


def starts_with_markup(pos: int) -> bool:
    rest = data[pos:].lstrip(BLANK)
    return rest[:1] == b"<"


if starts_with_markup(0):
    sys.exit(f"{src} starts with '<': not a video file")

pieces, start = [], 0
while start < len(data):
    end = min(start + CHUNK, len(data))
    while end < len(data) and starts_with_markup(end):
        end -= 1
    chunk = data[start:end]
    name = f"part-{len(pieces) + 1:02d}.mp4"
    (out / name).write_bytes(chunk)
    pieces.append({"file": name, "start": start, "end": end, "size": len(chunk), "sha256": hashlib.sha256(chunk).hexdigest()})
    start = end

manifest = {"source": src.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "pieces": pieces}
(out / "pieces.json").write_text(json.dumps(manifest, indent=1) + "\n")
print(f"{len(pieces)} pieces of {src.name} ({len(data):,} bytes) in {out}")
