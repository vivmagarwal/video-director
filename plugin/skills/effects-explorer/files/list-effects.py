#!/usr/bin/env python3
"""List every effect in a copy of remotion-effects-library, one line each.

usage: python3 list-effects.py <folder of the clone> [word to search for]

Prints: category, id, frames, packages, tagline, and the effect's main file.
The second argument keeps only the effects whose line or meta.ts holds that word.
"""
import pathlib
import re
import sys

if len(sys.argv) < 2:
    sys.exit("usage: list-effects.py <folder of the clone> [word]")
root = pathlib.Path(sys.argv[1]) / "src" / "effects"
if not root.is_dir():
    sys.exit(f"{root} is not there. Clone the library first.")
word = sys.argv[2].lower() if len(sys.argv) > 2 else None


def field(text: str, name: str) -> str:
    m = re.search(name + r":\s*(?:\n\s*)?'((?:[^'\\]|\\.)*)'", text)
    return m.group(1).replace("\\'", "'") if m else ""


count = 0
for meta in sorted(root.glob("*/*/meta.ts")):
    text = meta.read_text()
    frames = re.search(r"durationInFrames:\s*(\d+)", text)
    packages = re.search(r"packages:\s*\[([^\]]*)\]", text)
    names = [p.strip(" '\"\n") for p in packages.group(1).split(",")] if packages else []
    names = [p for p in names if p and p != "remotion"]
    line = " | ".join([
        meta.parent.parent.name,
        field(text, "id") or meta.parent.name,
        (frames.group(1) + "f") if frames else "?",
        ",".join(names) or "-",
        field(text, "tagline"),
        str(next(iter(sorted(meta.parent.glob("*.tsx"))), meta.parent).relative_to(root.parent.parent)),
    ])
    if word and word not in line.lower() and word not in text.lower():
        continue
    print(line)
    count += 1
print(f"{count} effects", file=sys.stderr)
