#!/usr/bin/env python3
"""Brand gates for the platform repo. Exit code 1 on any problem.

    python3 brand/check.py

1. The vendored copy matches brand.lock.json exactly (no edits, no extra or missing files).
2. Brand colours and backgrounds in the release equal the design tokens (logo-ink, brand-primary, bg-*).
3. Every surface in brand/surfaces.v1.json is well formed and, when live, resolves to real assets and files.
4. No code outside the token and brand folders writes the brand violet, a logo file name, or an image web address.

Until the first sync, state.json says synced=false and gates 1 to 3 are skipped with a notice (gate 4 always runs)."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brand import ROOT, HERE, THEMES, VARIANTS, is_synced, verify, sha256_file
from brand import LOCK, STATE, VENDOR

SURFACE_STATUS = ("live", "planned")
ID_OK = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ASSET_IDS = ("emblem", "logo", "wordmark")
SCAN_EXT = (".py", ".ts", ".mjs", ".js", ".html", ".css", ".kt", ".swift", ".rs", ".sql", ".yml", ".yaml")
SKIP_DIRS = {".git", "node_modules", "dist", "target", "build", "__pycache__", ".build", "vendor"}
# Places where the brand colours and logo names legitimately appear: tokens, the brand module, its tests, docs.
ALLOW_PREFIX = ("design/", "brand/", "tests/", "ts/src/brand.ts", "ts/test/brand.test.ts", "ts/src/tokens.ts", "android/core/src/main/kotlin/com/lynkomni/core/Tokens.kt", "ios/Sources/LynkCore/Tokens.swift", ".github/workflows/brand-sync.yml")
RULES = (
    (re.compile(r"(?=.*emblem)(?=.*wordmark)", re.I), "puts the emblem and wordmark together; use the logo asset (brand.for_surface)"),
    (re.compile(r"#7C4DFF", re.I), "writes the brand violet; use the design tokens"),
    (re.compile(r"lynkomni-(logo|emblem|wordmark)-"), "names a logo file; use brand.asset(id, variant)"),
    (re.compile(r"https?://[^\s\"')]*\.(svg|png|ico|jpe?g|webp)\b", re.I), "loads an image from a web address; bundle it instead"),
)


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def vendored_checks(root=ROOT, vendor=None, lock_path=None, state_path=None, tokens=None):
    problems = list(verify(vendor, lock_path, state_path))
    if not is_synced(state_path):
        return problems
    lock_path = lock_path or LOCK
    if not os.path.isfile(lock_path):
        return problems
    vdir = vendor or VENDOR
    bj = _load(os.path.join(vdir, "brand.json"))
    if tokens is None:
        sys.path.insert(0, root)
        from design import generate
        tokens = generate.resolved
    for theme in THEMES:
        t, m = bj["themes"][theme], tokens(theme)
        if t["ink"].upper() != m["logo-ink"].upper():
            problems.append(f"{theme}: logo ink {t['ink']} differs from token logo-ink {m['logo-ink']}")
        if t["accent"].upper() != m["brand-primary"].upper():
            problems.append(f"{theme}: logo accent {t['accent']} differs from token brand-primary {m['brand-primary']}")
        for name, hexv in t["backgrounds"].items():
            if name not in m:
                problems.append(f"{theme}: brand background {name} is not a design token")
            elif hexv.upper() != m[name].upper():
                problems.append(f"{theme}: brand background {name} {hexv} differs from the token {m[name]}")
    return problems


def _placement_problems(sid, s, bj):
    """Rules for `choose`: ordered by preference, minimum widths descending, last entry always fits, every chosen
    asset is declared in `uses`, and a one-colour place only allows the mono variant."""
    out = []
    rules = s.get("choose")
    if not rules:
        return [f"surface {sid}: must say which asset to choose (choose)"]
    used = {u.get("asset"): set(u.get("variants", [])) for u in s.get("uses", [])}
    prev = None
    for i, r in enumerate(rules):
        last = i == len(rules) - 1
        if r.get("asset") not in ASSET_IDS:
            out.append(f"surface {sid}: choose has unknown asset {r.get('asset')!r}")
            continue
        if r["asset"] not in used:
            out.append(f"surface {sid}: chooses {r['asset']} but does not list it under uses")
        mw = r.get("minWidthPx")
        if last and mw is not None:
            out.append(f"surface {sid}: the last choice must have no minWidthPx so something always fits")
        if not last:
            if not isinstance(mw, int) or mw <= 0:
                out.append(f"surface {sid}: every choice except the last needs a minWidthPx")
            elif prev is not None and mw >= prev:
                out.append(f"surface {sid}: minWidthPx must get smaller down the list")
            else:
                prev = mw
                if bj is not None and r["asset"] in bj["assets"] and mw < bj["assets"][r["asset"]]["minWidthPx"]:
                    out.append(f"surface {sid}: {r['asset']} chosen below its own minimum of {bj['assets'][r['asset']]['minWidthPx']} px")
    if s.get("colour") not in ("theme", "mono"):
        out.append(f"surface {sid}: colour must be theme or mono")
    if s.get("colour") == "mono":
        for a, vs in used.items():
            if vs != {"mono"}:
                out.append(f"surface {sid}: a one-colour place may only use the mono variant")
    if "print" in s:
        if s["print"] != "mono":
            out.append(f"surface {sid}: print must be mono")
        if not any("mono" in vs for vs in used.values()):
            out.append(f"surface {sid}: print is mono, so mono must be listed under uses")
    return out


def surface_checks(root=ROOT, vendor=None, lock_path=None, state_path=None, surfaces_path=None):
    problems = []
    doc = _load(surfaces_path or os.path.join(HERE, "surfaces.v1.json"))
    synced = is_synced(state_path)
    bj = _load(os.path.join(vendor or VENDOR, "brand.json")) if synced else None
    lock = _load(lock_path or LOCK) if synced and os.path.isfile(lock_path or LOCK) else {"files": {}}
    seen = set()
    for s in doc["surfaces"]:
        sid = s.get("id", "")
        if not ID_OK.match(sid):
            problems.append(f"surface id {sid!r} must be lowercase with hyphens")
        if sid in seen:
            problems.append(f"surface {sid}: duplicate id")
        seen.add(sid)
        if s.get("status") not in SURFACE_STATUS:
            problems.append(f"surface {sid}: status must be live or planned")
        if "offline" not in s or not isinstance(s["offline"], bool):
            problems.append(f"surface {sid}: must say whether it works offline (true or false)")
        if not s.get("uses"):
            problems.append(f"surface {sid}: must list the assets it uses")
        problems.extend(_placement_problems(sid, s, bj))
        for u in s.get("uses", []):
            for v in u.get("variants", []):
                if v not in VARIANTS:
                    problems.append(f"surface {sid}: unknown variant {v}")
            if synced:
                a = bj["assets"].get(u.get("asset"))
                if a is None:
                    problems.append(f"surface {sid}: unknown asset {u.get('asset')}")
                else:
                    for v in u.get("variants", []):
                        if v in a["variants"] and a["variants"][v]["svg"] not in lock["files"]:
                            problems.append(f"surface {sid}: {a['variants'][v]['svg']} is not vendored")
        if synced:
            for rel in s.get("files", []):
                if rel not in lock["files"]:
                    problems.append(f"surface {sid}: file {rel} is not in the brand lock")
    return problems


def scan_code(root=ROOT):
    problems = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            if not n.endswith(SCAN_EXT):
                continue
            full = os.path.join(base, n)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel.startswith(ALLOW_PREFIX):
                continue
            try:
                with open(full, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for rx, why in RULES:
                    if rx.search(line):
                        problems.append(f"{rel}:{i}: {why}")
    return problems


def icon_checks(vendor=None, lock_path=None, state_path=None):
    """Once synced: every icon in brand.json is vendored and locked, and the five user-facing states all exist."""
    if not is_synced(state_path):
        return []
    out = []
    bj = _load(os.path.join(vendor or VENDOR, "brand.json"))
    lock = _load(lock_path or LOCK)
    icons = bj.get("icons", {})
    from brand import STATUS_ICONS
    for state, iid in STATUS_ICONS.items():
        if iid not in icons:
            out.append(f"status icon {iid} for state {state} is missing from the release")
    for iid, e in icons.items():
        if not ID_OK.match(iid):
            out.append(f"icon id {iid!r} must be lowercase with hyphens")
        if e["svg"] not in lock["files"]:
            out.append(f"icon {iid}: {e['svg']} is not in the brand lock")
        if not e.get("accessibleName"):
            out.append(f"icon {iid}: needs an accessible name")
    return out


def all_problems(root=ROOT):
    return vendored_checks(root) + surface_checks(root) + icon_checks() + scan_code(root)


if __name__ == "__main__":
    out = all_problems()
    if not is_synced():
        print("notice: brand not synced from @lynkomni/icons yet; lock, token and file checks are skipped")
    print("\n".join(out) if out else "brand gates: ok")
    sys.exit(1 if out else 0)
