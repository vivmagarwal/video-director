#!/usr/bin/env python3
"""Search a clone of remocn, for when its online index is out of reach.

usage: python3 list-remocn.py <folder of the clone> [word] [--vibe=paper]

Prints, one line each: section, component, feel, length in frames, what it is for,
and what to avoid it for. A search word looks in the name, the description and the
"use for" notes, never in the "avoid" notes, which name the things it is wrong for.
"""
import pathlib
import re
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    sys.exit(__doc__)
root = pathlib.Path(args[0]) / "content" / "docs"
if not root.is_dir():
    sys.exit(f"{root} is not there. Clone remocn first.")
word = args[1].lower() if len(args) > 1 else None
vibe = next((a.split("=", 1)[1].lower() for a in sys.argv[1:] if a.startswith("--vibe=")), None)


def scalar(head, key):
    m = re.search(rf"^{key}:\s*(.+)$", head, re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def items(head, key):
    m = re.search(rf"^{key}:\n((?:\s+- .*\n?)+)", head, re.M)
    return [x.strip()[2:].strip().strip("\"'") for x in m.group(1).splitlines()] if m else []


count = 0
for page in sorted(root.rglob("*.mdx")):
    m = re.match(r"---\n(.*?)\n---", page.read_text(encoding="utf-8"), re.S)
    if not m or not scalar(m.group(1), "component"):
        continue
    head = m.group(1)
    use, avoid = items(head, "useWhen"), items(head, "avoidWhen")
    name, desc, feel = scalar(head, "component"), scalar(head, "description"), scalar(head, "vibe")
    if word and word not in " ".join([name, desc, feel, *use]).lower():
        continue
    if vibe and feel.lower() != vibe:
        continue
    print(" | ".join([page.parent.relative_to(root).as_posix(), name, feel or "-", scalar(head, "length") or "-", (use[0] if use else desc), (avoid[0] if avoid else "-")]))
    count += 1
print(f"{count} components", file=sys.stderr)
