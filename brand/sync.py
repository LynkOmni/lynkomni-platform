#!/usr/bin/env python3
"""Vendors one @lynkomni/icons release into brand/vendor and writes brand.lock.json.

    python -m brand.sync --from <folder>        <folder> is the unpacked package (it holds package.json and dist/)

Only svg/, web/, email/ and brand.json are vendored (the Android, iOS and React outputs are consumed straight from the
package by those builds). Every file is verified against the checksums the package lists for itself first, and the
sync refuses anything unexpected. The brand-sync workflow runs this on a schedule and opens a pull request."""
import argparse, json, os, shutil, sys
from brand import ROOT, HERE, VENDOR, LOCK, STATE, sha256_file, THEMES

PACKAGE = "@lynkomni/icons"
VENDORED_DIRS = ("svg", "web", "email", "icons")
SAFE = set("abcdefghijklmnopqrstuvwxyz0123456789-_.@/")


def _json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def plan(pkg_dir):
    """Reads and checks the package. Returns (version, {rel: absolute source path}). Raises ValueError when unsafe."""
    meta = _json(os.path.join(pkg_dir, "package.json"))
    if meta.get("name") != PACKAGE:
        raise ValueError(f"package is {meta.get('name')!r}, expected {PACKAGE}")
    dist = os.path.join(pkg_dir, "dist")
    bj = _json(os.path.join(dist, "brand.json"))
    if bj.get("schema") != 1 or bj.get("package") != PACKAGE:
        raise ValueError("brand.json has an unknown schema or package")
    listed = dict(bj.get("files", {}))
    listed.update(bj.get("rasters", {}))
    chosen = {"brand.json": os.path.join(dist, "brand.json")}
    for rel, info in sorted(listed.items()):
        if rel.split("/")[0] not in VENDORED_DIRS:
            continue
        if rel.startswith("icons/react/"):
            continue                      # React components are for web apps that install the package; the platform vendors the SVGs
        if any(c not in SAFE for c in rel) or ".." in rel or rel.startswith("/"):
            raise ValueError(f"unsafe file name {rel!r}")
        src = os.path.join(dist, *rel.split("/"))
        if not os.path.isfile(src):
            raise ValueError(f"package lists {rel} but it is missing")
        if sha256_file(src) != info["sha256"]:
            raise ValueError(f"checksum mismatch inside the package for {rel}")
        chosen[rel] = src
    for must in ("svg", "web", "email", "icons"):
        if not any(r.startswith(must + "/") for r in chosen):
            raise ValueError(f"package has no {must}/ files (was the raster step skipped?)")
    for t in THEMES:
        if t not in bj["themes"]:
            raise ValueError(f"brand.json is missing theme {t}")
    return meta["version"], chosen


def sync(pkg_dir, vendor=None, lock_path=None, state_path=None):
    version, chosen = plan(pkg_dir)
    vdir = vendor or VENDOR
    for name in os.listdir(vdir):
        p = os.path.join(vdir, name)
        if name == ".gitkeep":
            continue
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    files = {}
    for rel, src in chosen.items():
        dest = os.path.join(vdir, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
        files[rel] = sha256_file(dest)
    lock = {"schema": 1, "package": PACKAGE, "version": version, "files": dict(sorted(files.items()))}
    with open(lock_path or LOCK, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2); f.write("\n")
    with open(state_path or STATE, "w", encoding="utf-8") as f:
        json.dump({"synced": True}, f); f.write("\n")
    return lock


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="src", required=True, help="unpacked @lynkomni/icons package folder")
    args = ap.parse_args(argv)
    try:
        lock = sync(args.src)
    except (ValueError, OSError, KeyError) as e:
        print(f"brand sync refused: {e}", file=sys.stderr)
        return 1
    print(f"Vendored {PACKAGE}@{lock['version']}: {len(lock['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
