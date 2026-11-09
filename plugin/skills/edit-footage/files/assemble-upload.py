#!/usr/bin/env python3
"""Join the pieces the upload page stored back into the original files, and prove it.

usage: assemble-upload.py <upload-doc.json> <dir holding <asset-id>.* files> <out-file>
       assemble-upload.py --all <dir of upload docs> <pieces dir> <out dir>
       assemble-upload.py --need <dir of upload docs> <pieces dir>

A doc is an `uploads/<id>` document as ArtifactData saved it (out_dir). Every
piece is checked for its size and SHA-256 against what the browser measured
before sending it, and the joined file against the size the browser read.

`--all` joins every complete upload into <out dir> under its original name and
prints one line per file: its kind, size, SHA-256 and the note the user gave
it on the page. An upload that stopped part-way is listed, not joined.
`--need` prints the asset ids of the complete uploads' pieces that are not in
<pieces dir> yet: the list to fetch, one `Artifact read path=<id>` each.
"""
import hashlib
import json
import pathlib
import re
import sys


def load(doc_path: pathlib.Path) -> dict:
    raw = json.loads(doc_path.read_text())
    return raw.get("data", raw)


def piece_file(pieces_dir: pathlib.Path, asset_id: str) -> list:
    return list(pieces_dir.glob(asset_id + ".*")) or list(pieces_dir.glob(asset_id))


def assemble(doc: dict, pieces_dir: pathlib.Path, out_path: pathlib.Path) -> str:
    """Join one upload; returns its SHA-256, or exits naming what is wrong."""
    if doc.get("status") != "complete":
        sys.exit(f"upload is {doc.get('status')!r}, not complete ({len(doc.get('chunks', []))} of {len(doc.get('ends', []))} pieces)")
    chunks = sorted(doc["chunks"], key=lambda c: c["i"])
    if [c["i"] for c in chunks] != list(range(len(doc["ends"]))):
        sys.exit(f"pieces are not contiguous: {[c['i'] for c in chunks]}")
    total = hashlib.sha256()
    with out_path.open("wb") as out:
        for c in chunks:
            matches = piece_file(pieces_dir, c["id"])
            if len(matches) != 1:
                sys.exit(f"{doc.get('name')}: piece {c['i']}: expected one file for asset {c['id']}, found {matches}")
            data = matches[0].read_bytes()
            if len(data) != c["end"] - c["start"]:
                sys.exit(f"{doc.get('name')}: piece {c['i']}: {len(data)} bytes, expected {c['end'] - c['start']}")
            if c.get("sha256") and hashlib.sha256(data).hexdigest() != c["sha256"]:
                sys.exit(f"{doc.get('name')}: piece {c['i']}: SHA-256 differs from what the browser sent")
            out.write(data)
            total.update(data)
    size = out_path.stat().st_size
    if size != doc["size"]:
        sys.exit(f"{doc.get('name')}: joined file is {size} bytes, the original was {doc['size']}")
    return total.hexdigest()


def safe_name(name: str) -> str:
    name = pathlib.PurePath(str(name)).name
    return re.sub(r"[^\w.\- ()+@]", "_", name).strip() or "upload"


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] in ("--all", "--need"):
        mode, docs_dir, pieces_dir = args[0], pathlib.Path(args[1]), pathlib.Path(args[2])
        docs = sorted(((p, load(p)) for p in docs_dir.glob("*.json")), key=lambda pd: str(pd[1].get("startedAt", "")))
        if mode == "--need":
            for _, d in docs:
                if d.get("status") == "complete":
                    for c in sorted(d["chunks"], key=lambda c: c["i"]):
                        if not piece_file(pieces_dir, c["id"]):
                            print(c["id"])
            return
        out_dir = pathlib.Path(args[3])
        out_dir.mkdir(parents=True, exist_ok=True)
        used = set()
        for path, d in docs:
            name = safe_name(d.get("name", path.stem))
            if d.get("status") != "complete":
                print(f"STOPPED  {name}: {len(d.get('chunks', []))} of {len(d.get('ends', []))} pieces; ask the user to choose it again on the page")
                continue
            # Two files may share a name (two cameras both writing "video.mp4").
            target, n = name, 2
            while target in used:
                stem, dot, ext = name.rpartition(".")
                target = f"{stem} ({n}).{ext}" if dot else f"{name} ({n})"
                n += 1
            used.add(target)
            sha = assemble(d, pieces_dir, out_dir / target)
            note = f' · "{d["note"]}"' if d.get("note") else ""
            print(f"ok  {target} · {d.get('kind') or 'file'} · {d['size']} bytes · sha256 {sha}{note}")
        return
    if len(args) != 3:
        sys.exit(__doc__)
    doc_path, pieces_dir, out_path = map(pathlib.Path, args)
    doc = load(doc_path)
    sha = assemble(doc, pieces_dir, out_path)
    print(f"ok: {out_path} · {out_path.stat().st_size} bytes · {len(doc['chunks'])} pieces · sha256 {sha}")


if __name__ == "__main__":
    main()
