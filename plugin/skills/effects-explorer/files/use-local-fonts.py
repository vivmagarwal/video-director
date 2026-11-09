#!/usr/bin/env python3
"""Make every Google Font in a Remotion project load from npm, not from the internet.

usage: python3 use-local-fonts.py [folder to scan, default src]

Run it from the project folder, after you copy in an effect and before your first
still. It finds each import from @remotion/google-fonts/<Name>, installs the same
font as @fontsource/<name>, writes src/fontshim/<Name>.ts, and points the import
there. The effect's own code does not change. It is safe to run again.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

scan = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "src")
if not pathlib.Path("package.json").exists() or not scan.is_dir():
    sys.exit(f"run this from the project folder: no package.json here, or no {scan} folder")
shims = pathlib.Path("src/fontshim")
GOOGLE = re.compile(r"""(['"])@remotion/google-fonts/([A-Za-z0-9]+)\1""")
LOCAL = re.compile(r"""(['"])[./@a-z]*fontshim/([A-Za-z0-9]+)\1""")


def sources():
    for p in scan.rglob("*"):
        if p.suffix in {".ts", ".tsx", ".js", ".jsx", ".mts"} and shims not in p.parents and "node_modules" not in p.parts:
            yield p


def package_for(name):
    """The npm name comes from Google's own family name when that package is here."""
    remote = pathlib.Path(f"node_modules/@remotion/google-fonts/dist/cjs/{name}.js")
    if remote.exists():
        m = re.search(r"fontFamily:\s*['\"]([^'\"]+)['\"]", remote.read_text(encoding="utf-8"))
        if m:
            return "@fontsource/" + m.group(1).lower().replace(" ", "-")
    # PlayfairDisplay becomes playfair-display. A name this gets wrong fails at install.
    return "@fontsource/" + re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name).lower()


wanted, italic, files = set(), set(), {}
for p in sources():
    t = p.read_text(encoding="utf-8")
    here = {m.group(2) for m in GOOGLE.finditer(t)} | {m.group(2) for m in LOCAL.finditer(t)}
    wanted |= here
    if "italic" in t:
        italic |= here
    if GOOGLE.search(t):
        files[p] = t
if not wanted:
    print("no Google Fonts in this project, so nothing to do")
    sys.exit(0)

deps = json.loads(pathlib.Path("package.json").read_text(encoding="utf-8")).get("dependencies", {})
failed = {}
for name in sorted(wanted):
    pkg = package_for(name)
    if pkg in deps and pathlib.Path("node_modules", pkg).is_dir():
        continue
    r = subprocess.run(["npm", "i", "--save-exact", "--no-audit", "--no-fund", pkg], capture_output=True, text=True)
    if r.returncode:
        failed[name] = pkg

shims.mkdir(parents=True, exist_ok=True)
done = sorted(wanted - set(failed))
for name in done:
    pkg = package_for(name)
    folder = pathlib.Path("node_modules", pkg)
    css = sorted(c.name for c in folder.glob("*.css") if re.fullmatch(r"\d+(-italic)?\.css", c.name))
    if name not in italic:
        css = [c for c in css if "italic" not in c]
    if not css:
        failed[name] = pkg
        continue
    family = re.search(r"font-family:\s*['\"]([^'\"]+)['\"]", (folder / css[0]).read_text(encoding="utf-8")).group(1)
    lines = [f"// Written by use-local-fonts.py. {family} loads from npm, so a render needs no font host."]
    lines += [f"import '{pkg}/{c}';" for c in css]
    lines += [
        f"export const fontFamily = {json.dumps(family)};",
        "export const loadFont = (..._args: unknown[]) => ({",
        "\tfontFamily,",
        "\tfonts: {},",
        "\tunicodeRanges: {},",
        "\twaitUntilDone: () => Promise.resolve(undefined),",
        "});",
        "",
    ]
    (shims / f"{name}.ts").write_text("\n".join(lines), encoding="utf-8")

changed = 0
for p, t in files.items():
    def point(m):
        global changed
        if m.group(2) in failed:
            return m.group(0)
        changed += 1
        rel = os.path.relpath(shims / m.group(2), p.parent).replace(os.sep, "/")
        return m.group(1) + (rel if rel.startswith(".") else "./" + rel) + m.group(1)
    p.write_text(GOOGLE.sub(point, t), encoding="utf-8")

print(f"local fonts: {', '.join(n for n in done if n not in failed)}. {changed} import(s) changed.")
for name, pkg in failed.items():
    print(f"NOT DONE: {name}. Could not get {pkg} from npm. Find the font's real package name, or use another font.")
sys.exit(1 if failed else 0)
