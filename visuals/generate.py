#!/usr/bin/env python3
"""Builds every visual declared in visuals/needs.v1.json into visuals/generated/, plus the index and the TypeScript table.

Run: python3 visuals/generate.py          (writes the files)
     python3 visuals/generate.py --check  (writes nothing; fails if generated files are out of date)

SVG output is deterministic, so --check can compare it byte for byte. PNG files are drawn from those SVGs with the
Chromium that Playwright installs (offline); they are checked for size and dimensions, not byte for byte."""
import hashlib, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from visuals import kit, scenes, figures, cards  # noqa: E402

NEEDS = os.path.join(HERE, "needs.v1.json")
OUT = os.path.join(HERE, "generated")
TS_OUT = os.path.join(ROOT, "ts", "src", "visuals.generated.ts")
FOLDER = {"illustration": "illustrations", "chart": "charts", "diagram": "diagrams", "card": "cards"}
FIGURES = {"pricing_ladder": figures.pricing_ladder, "revenue_path": figures.revenue_path, "sync_states": figures.sync_states, "vcard_tiers": cards.tier_ladder}


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def load():
    with open(NEEDS, encoding="utf-8") as f:
        return json.load(f)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def web_icon_svgs():
    """The browser and phone icon family: (file -> svg text). Emblem only, through the brand module."""
    return {
        "web/pwa-192.png": figures.app_icon("light", 62, view=192),
        "web/pwa-512.png": figures.app_icon("light", 62, view=512),
        "web/pwa-maskable-512.png": figures.app_icon("light", 44, view=512),       # artwork inside the 80% safe zone
        "web/apple-touch-icon-180.png": figures.app_icon("light", 62, view=180),
        "web/favicon.svg": figures.app_icon("light", 66, rounded=True, bg=kit.Palette("light").surface, view=64),
        "web/favicon-32.png": figures.app_icon("light", 66, rounded=True, bg=kit.Palette("light").surface, view=32),
    }


def svg_jobs(doc):
    """Every deterministic file: path (inside generated/) -> text. Also the PNG jobs: path -> (svg text, w, h)."""
    text_files, png_jobs, meta = {}, {}, {}
    for need in doc["needs"]:
        nid, kind = need["id"], need["kind"]
        files = []
        if kind == "illustration":
            for th in need["themes"]:
                p = kit.Palette(th, need["accent"])
                svg = kit.frame(nid, need["alt"], scenes.SCENES[need["scene"]](p))
                rel = f"{FOLDER[kind]}/{nid}.{th}.svg"
                text_files[rel] = svg
                files.append({"theme": th, "file": rel})
        elif kind in ("chart", "diagram"):
            for th in need["themes"]:
                rel = f"{FOLDER[kind]}/{nid}.{th}.svg"
                text_files[rel] = FIGURES[need["figure"]](th)
                files.append({"theme": th, "file": rel})
        elif kind == "card":
            rel = f"{FOLDER[kind]}/{nid}.svg"
            text_files[rel] = {"face": lambda: cards.card_face(need["tier"]), "back": lambda: cards.card_back(need["tier"]),
                               "near-limit": cards.near_limit, "physical": cards.physical}[need.get("variant", "face")]()
            files.append({"theme": "light", "file": rel})
        elif nid == "share-card":
            svg = figures.share_card("light")
            text_files["share/share-card.light.svg"] = svg
            png_jobs["web/og-1200x630.png"] = (svg, 1200, 630)
            files = [{"theme": "light", "file": "share/share-card.light.svg"}, {"theme": "light", "file": "web/og-1200x630.png", "w": 1200, "h": 630}]
        elif nid == "store-feature-graphic":
            svg = figures.store_feature("light")
            text_files["store/play-feature-1024x500.svg"] = svg
            png_jobs["store/play-feature-1024x500.png"] = (svg, 1024, 500)
            files = [{"theme": "light", "file": "store/play-feature-1024x500.svg"}, {"theme": "light", "file": "store/play-feature-1024x500.png", "w": 1024, "h": 500}]
        elif nid == "app-icon":
            for th in need["themes"]:
                rel = f"store/app-icon-1024-{th}.png"
                png_jobs[rel] = (figures.app_icon(th, 58, view=1024), 1024, 1024)
                files.append({"theme": th, "file": rel, "w": 1024, "h": 1024})
        elif nid == "web-icons":
            for rel, svg in web_icon_svgs().items():
                w = int(re.search(r'viewBox="0 0 (\d+) ', svg).group(1))
                if rel.endswith(".svg"):
                    text_files[rel] = svg
                    files.append({"theme": "light", "file": rel})
                else:
                    png_jobs[rel] = (svg, w, w)
                    files.append({"theme": "light", "file": rel, "w": w, "h": w})
            text_files["web/icons-snippet.json"] = json.dumps({
                "icons": [{"src": "web/pwa-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                          {"src": "web/pwa-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                          {"src": "web/pwa-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
                "head": ['<link rel="icon" href="/web/favicon.svg" type="image/svg+xml">', '<link rel="icon" href="/web/favicon.ico" sizes="any">',
                         '<link rel="apple-touch-icon" href="/web/apple-touch-icon-180.png">']}, indent=1) + "\n"
            tk = kit._design.resolved("light")
            text_files["web/manifest.webmanifest"] = json.dumps({
                "name": "LynkOmni", "short_name": "LynkOmni", "start_url": "/", "scope": "/", "display": "standalone", "orientation": "portrait",
                "background_color": tk["bg-base"], "theme_color": tk["brand-primary"], "lang": "en",
                "icons": [{"src": "pwa-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"}, {"src": "pwa-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                          {"src": "pwa-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}, indent=1) + "\n"
            files += [{"theme": "light", "file": "web/icons-snippet.json"}, {"theme": "light", "file": "web/favicon.ico"}, {"theme": "light", "file": "web/manifest.webmanifest"}]
            png_jobs["__ico__"] = ("", 0, 0)
        else:
            raise SystemExit(f"need {nid}: unknown kind or figure")
        meta[nid] = files
    return text_files, png_jobs, meta


def ico_from_pngs(pngs):
    """An .ico that holds PNG images (supported by every current browser)."""
    head = struct.pack("<HHH", 0, 1, len(pngs))
    entries, data, off = b"", b"", 6 + 16 * len(pngs)
    for size, b in pngs:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(b), off)
        data += b
        off += len(b)
    return head + entries + data


def png_dims(b):
    return struct.unpack(">II", b[16:24])


def render_pngs(png_jobs):
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for rel, (svg, w, h) in png_jobs.items():
            if rel == "__ico__":
                continue
            pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg.set_content(f'<body style="margin:0;background:transparent">{svg.replace("<svg ", f"<svg style=\"display:block;width:{w}px;height:{h}px\" ", 1)}</body>')
            out[rel] = pg.screenshot(clip={"x": 0, "y": 0, "width": w, "height": h}, type="png")
            pg.close()
        small = {}
        for s in (16, 32, 48):
            pg = br.new_page(viewport={"width": s, "height": s}, device_scale_factor=1)
            svg = figures.app_icon("light", 66, rounded=True, bg=kit.Palette("light").surface, view=s)
            pg.set_content(f'<body style="margin:0;background:transparent">{svg.replace("<svg ", f"<svg style=\"display:block;width:{s}px;height:{s}px\" ", 1)}</body>')
            small[s] = pg.screenshot(clip={"x": 0, "y": 0, "width": s, "height": s}, type="png", omit_background=True)
            pg.close()
        br.close()
    out["web/favicon.ico"] = ico_from_pngs(sorted(small.items()))
    return out


def build_index(doc, meta, written):
    idx = {"version": 1, "status": doc["status"], "needs": {}}
    for need in doc["needs"]:
        files = []
        for f in meta[need["id"]]:
            b = written[f["file"]]
            files.append({**f, "sha256": sha(b), "bytes": len(b)})
        idx["needs"][need["id"]] = {"kind": need["kind"], "alt": need["alt"], "purpose": need["purpose"], "used_in": need["used_in"], "status": "draft", "files": files}
    return idx


def ts_table(idx):
    """theme -> file, SVG preferred; `png` lists the PNG for each theme where one exists. Icon-set helper files (.ico, .json) are left out."""
    rows = []
    for nid, v in idx["needs"].items():
        svg, png = {}, {}
        for f in v["files"]:
            if f["file"].endswith(".svg"):
                svg.setdefault(f["theme"], f["file"])
            elif f["file"].endswith(".png"):
                png.setdefault(f["theme"], f["file"])
        main = {**png, **svg}
        enc = lambda d: ", ".join(f"{json.dumps(k)}: {json.dumps(x)}" for k, x in d.items())
        rows.append(f'  {json.dumps(nid)}: {{ kind: {json.dumps(v["kind"])}, alt: {json.dumps(v["alt"])}, files: {{ {enc(main)} }}, png: {{ {enc(png)} }} }},')
    return ("// Generated by visuals/generate.py from visuals/needs.v1.json. Do not edit by hand.\n"
            "export const VISUALS: Record<string, { kind: string; alt: string; files: Record<string, string>; png: Record<string, string> }> = {\n" + "\n".join(rows) + "\n};\n")


def build(write=True, png=True):
    doc = load()
    text_files, png_jobs, meta = svg_jobs(doc)
    written = {rel: t.encode("utf-8") for rel, t in text_files.items()}
    if png:
        written.update(render_pngs(png_jobs))
    else:   # deterministic part only (used by --check and quick tests)
        for rel in png_jobs:
            if rel != "__ico__":
                written[rel] = b""
        written["web/favicon.ico"] = b""
    idx = build_index(doc, meta, written) if png else None
    return doc, text_files, written, idx


def main(argv):
    check_only = "--check" in argv
    doc, text_files, written, idx = build(png=not check_only)
    if check_only:
        bad = []
        for rel, t in text_files.items():
            p = os.path.join(OUT, rel)
            if not os.path.isfile(p) or read_bytes(p) != t.encode("utf-8"):
                bad.append(rel)
        print("generated files are up to date" if not bad else "out of date (run python3 visuals/generate.py): " + ", ".join(bad[:8]))
        return 1 if bad else 0
    keep = set(written) | {"index.json"}
    for rel, b in written.items():
        p = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=1, ensure_ascii=False)
        f.write("\n")
    for base, _, names in os.walk(OUT):       # remove orphans so nothing stale ever ships
        for nme in names:
            rel = os.path.relpath(os.path.join(base, nme), OUT).replace(os.sep, "/")
            if rel not in keep:
                os.remove(os.path.join(base, nme))
    with open(TS_OUT, "w", encoding="utf-8") as f:
        f.write(ts_table(idx))
    print(f"wrote {len(written)} files for {len(doc['needs'])} needs")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
