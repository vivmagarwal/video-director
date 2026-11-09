#!/usr/bin/env python3
"""Copy remotion-effects-library file by file, for when `git clone` is refused.

usage: python3 fetch-effects-raw.py <out folder>

Reads the library's list of effects, then downloads each effect's folder from
raw.githubusercontent.com: its main .tsx file, meta.ts and prompt.md. The result
has the same layout as a clone, so list-effects.py works on it.
"""
import concurrent.futures
import pathlib
import re
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/vivmagarwal/remotion-effects-library/main/"
if len(sys.argv) != 2:
    sys.exit(__doc__)
out = pathlib.Path(sys.argv[1])


def get(path: str) -> bytes:
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.read()


registry = get("src/registry.generated.ts").decode()
wanted = []
for m in re.finditer(r"from '\./(effects/[^']+)'", registry):
    path = m.group(1)
    if path.endswith("/meta"):
        wanted += [f"src/{path}.ts", f"src/{path[:-4]}prompt.md"]
    else:
        wanted.append(f"src/{path}.tsx")


def save(path: str) -> str:
    try:
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(get(path))
        return ""
    except Exception as e:
        return f"{path}: {e}"


with concurrent.futures.ThreadPoolExecutor(8) as pool:
    failed = [x for x in pool.map(save, wanted) if x]
print(f"{len(wanted) - len(failed)} of {len(wanted)} files saved in {out}")
for line in failed:
    print("failed", line)
sys.exit(1 if failed else 0)
