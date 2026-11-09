#!/usr/bin/env python3
"""Copy a remocn component out of a clone, with its helpers. It does what `shadcn add` does, with no need for remocn.dev.

usage: python3 copy-remocn.py <folder of the clone> <component> [more components]

Run it from your preview project. It writes each file under src/, and follows the
component's helpers. It keeps any file already there, so your edits are safe. It
then installs the npm packages they need, at your Remotion version for @remotion/*.
"""
import json
import pathlib
import subprocess
import sys

if len(sys.argv) < 3:
    sys.exit(__doc__)
if not pathlib.Path("package.json").exists():
    sys.exit("run this from your preview project: there is no package.json here")
art = pathlib.Path(sys.argv[1]) / "registry-artifacts"
if not art.is_dir():
    sys.exit(f"{art} is not there. Clone remocn first.")

queue, seen, deps, written, kept, missing = list(sys.argv[2:]), set(), set(), [], [], []
while queue:
    name = queue.pop().removeprefix("@remocn/")
    if name in seen:
        continue
    seen.add(name)
    f = art / f"{name}.json"
    if not f.exists():
        missing.append(name)
        continue
    item = json.loads(f.read_text(encoding="utf-8"))
    deps |= set(item.get("dependencies") or [])
    queue += item.get("registryDependencies") or []
    for part in item.get("files") or []:
        target = pathlib.Path("src") / (part.get("target") or part["path"])
        if target.exists():
            kept.append(str(target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(part["content"], encoding="utf-8")
        written.append(str(target))

installed = json.loads(pathlib.Path("package.json").read_text(encoding="utf-8")).get("dependencies", {})
version = installed.get("remotion", "")
need = sorted(d for d in deps if d != "remotion" and d not in installed)
args = [f"{d}@{version}" if d.startswith("@remotion/") and version else d for d in need]
if args:
    r = subprocess.run(["npm", "i", "--save-exact", "--no-audit", "--no-fund", *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit("npm could not install " + " ".join(args) + ":\n" + r.stderr[-400:])
for w in written:
    print("saved:", w)
print(f"{len(written)} file(s) saved, {len(kept)} kept. Installed: {', '.join(args) or 'nothing new'}.")
if missing:
    print("NOT FOUND:", ", ".join(missing), "- check the name with list-remocn.py")
    sys.exit(1)
