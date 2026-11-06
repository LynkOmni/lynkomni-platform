#!/usr/bin/env python3
"""Visuals gate. Fails the build when a picture is missing, orphaned, off-brand, inaccessible, too big, out of date,
or when code leaves a placeholder or a "TODO image". Run: python3 visuals/check.py"""
import hashlib, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

KINDS = ("illustration", "chart", "diagram", "card", "share", "store", "icon-set")
TEXT_OK = ("chart", "diagram")                       # only these may contain words; the words are real data
ID_OK = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BAD_ALT = re.compile(r"placeholder|todo|lorem|tbd|image of|picture of|untitled", re.I)
SKIP_DIRS = {".git", "node_modules", "dist", "target", "build", "__pycache__", ".build", "vendor", "generated"}
SCAN_EXT = (".py", ".ts", ".mjs", ".js", ".html", ".css", ".kt", ".swift", ".rs", ".md", ".json", ".yml", ".yaml")
# Where the banned words may appear because they are the rules themselves.
SCAN_ALLOW = ("visuals/check.py", "tests/", "ts/test/visuals.test.ts", "CLAUDE.md", "README.md", "STACK.md", "brand/check.py")
BANNED = (
    (re.compile(r"TODO[:\s-]*\(?(image|icon|illustration|logo|art|picture|graphic)", re.I), 'a "TODO image" marker'),
    (re.compile(r"(placeholder|placehold|dummy|temp)[-_.]?(image|img|logo|icon|photo)?\.(png|jpe?g|svg|webp|gif)", re.I), "a placeholder image file"),
    (re.compile(r"via\.placeholder|placehold\.co|placeimg|picsum\.photos|unsplash\.com|pexels\.com|lorempixel|dummyimage", re.I), "a stock or placeholder image service"),
    (re.compile(r"<img[^>]+src=[\"']https?://", re.I), "an image loaded from the web (bundle it instead)"),
    (re.compile(r"lorem ipsum", re.I), "lorem ipsum text"),
)
REFERENCE = re.compile(r"""visuals?\.(?:get|decorative|alt|svg_text|data_uri)\(\s*["']([a-z0-9-]+)["']""")
TS_REFERENCE = re.compile(r"""\bvisual(?:File|Alt|Decorative)?\(\s*["']([a-z0-9-]+)["']""")


def _read(p, mode="rb"):
    with open(p, mode) as f:
        return f.read()


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _png(b):
    return b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) > 24, struct.unpack(">II", b[16:24]) if len(b) > 24 else (0, 0)


def need_checks(doc):
    out, seen_ids, seen_alt = [], set(), {}
    if doc.get("status") != "draft":
        out.append("needs status must stay 'draft' until a human designer signs off")
    for n in doc["needs"]:
        nid = n.get("id", "?")
        if not ID_OK.match(nid): out.append(f"{nid}: id must be lowercase words joined by hyphens")
        if nid in seen_ids: out.append(f"{nid}: duplicate id")
        seen_ids.add(nid)
        if n.get("kind") not in KINDS: out.append(f"{nid}: unknown kind")
        a = n.get("alt", "")
        if len(a) < 20 or BAD_ALT.search(a): out.append(f"{nid}: write a real text alternative (20+ characters, no placeholder words)")
        if a in seen_alt: out.append(f"{nid}: same text alternative as {seen_alt[a]}")
        seen_alt[a] = nid
        if not n.get("purpose") or not n.get("used_in"): out.append(f"{nid}: say what it is for (purpose and used_in)")
        if not n.get("budget_kb"): out.append(f"{nid}: needs a size budget")
        if n.get("kind") == "illustration":
            from visuals import scenes
            if n.get("scene") not in scenes.SCENES: out.append(f"{nid}: scene {n.get('scene')!r} does not exist")
    return out


def palette_checks():
    """The colour pairs every picture relies on, per theme and accent: shapes 3:1, text 4.5:1."""
    from visuals import kit
    out = []
    for th in kit.THEMES:
        for acc in ("brand", "booking", "essential", "exchange", "vcard"):
            p = kit.Palette(th, acc)
            pairs = [("ink on base", p.ink, p.base, 3.0), ("ink on ground", p.ink, p.ground, 3.0), ("marks on accent", p.on_accent, p.accent, 3.0),
                     ("accent ink on soft accent", p.accent_ink, p.accent_soft, 3.0), ("secondary ink on base", p.ink2, p.base, 4.5)]
            if acc == "brand":
                pairs += [("success text", p.ok, p.ok_bg, 4.5), ("danger text", p.bad, p.bad_bg, 4.5), ("warning text", p.warn, p.warn_bg, 4.5), ("ink on soft brand", p.ink, p.brand_soft, 4.5)]
            for name, a, b, need in pairs:
                if kit.contrast(a, b) < need:
                    out.append(f"{th}/{acc}: {name} is {kit.contrast(a, b):.2f}:1, needs {need}:1")
    return out


def card_checks():
    """Text and marks on every card face must read on its colour."""
    from visuals import kit, cards
    from design import generate as design
    t = design.resolved("dark")
    return [f"card {c}: text is {kit.contrast(t['on-vcard-' + c], t['vcard-' + c + '-bg']):.2f}:1, needs 4.5:1" for c in cards.TIERS
            if kit.contrast(t["on-vcard-" + c], t["vcard-" + c + "-bg"]) < 4.5]


def svg_problems(rel, text, kind, theme, budget_kb):
    from design import generate as design
    out = []
    if len(text.encode("utf-8")) > budget_kb * 1024: out.append(f"{rel}: over its {budget_kb} KB budget")
    for rx, why in ((r"<script", "has a script"), (r"<image\b", "embeds a raster image"), (r"<foreignObject", "has foreignObject"), (r"(xlink:)?href\s*=", "has a link or external reference"),
                    (r"url\(\s*[\"']?https?:", "loads from the web"), (r"@import", "imports a stylesheet"), (r"\son[a-z]+\s*=", "has an event handler")):
        if re.search(rx, text, re.I): out.append(f"{rel}: {why}")
    if "<title" not in text or 'role="img"' not in text or "viewBox" not in text: out.append(f"{rel}: needs role=img, a <title> (the text alternative) and a viewBox")
    card_rx = re.compile(r"<!--card:start-->(.*?)<!--card:end-->", re.S)
    segs = card_rx.findall(text)
    outside = card_rx.sub("", text)
    if kind == "card" and not segs: out.append(f"{rel}: a card face must be wrapped in card markers")
    if kind not in TEXT_OK and "<text" in outside: out.append(f"{rel}: {kind} images contain no words (put the words in the page, beside the picture)")
    from visuals import cards
    for seg in segs:                       # card faces: only the fixed tier lines, and the dark-theme glow tokens are allowed
        for words in re.findall(r"<text[^>]*>(.*?)</text>", seg, re.S):
            if words.replace("&amp;", "&") not in cards.TIER_TEXT.values(): out.append(f"{rel}: card text {words[:30]!r} is not one of the approved tier lines")
        both = {v.upper() for th in ("light", "dark") for v in design.resolved(th).values() if re.fullmatch(r"#[0-9A-Fa-f]{6}", v)}
        for c in set(re.findall(r"#[0-9A-Fa-f]{3,8}\b", re.sub(r'<g data-brand="[a-z]+">.*?</svg></g>', "", seg, flags=re.S))):
            if c.upper() not in both: out.append(f"{rel}: card colour {c} is not a design token")
        if re.search(r"\d{4}", re.sub(r"<[^>]+>", "", seg)): out.append(f"{rel}: a card face must not show a number")
    body = re.sub(r'<g data-brand="[a-z]+">.*?</svg></g>', "", outside, flags=re.S)   # brand artwork keeps its own colours
    allowed = {v.upper() for v in design.resolved(theme).values() if re.fullmatch(r"#[0-9A-Fa-f]{6}", v)}
    for c in set(re.findall(r"#[0-9A-Fa-f]{3,8}\b", body)):
        if c.upper() not in allowed: out.append(f"{rel}: colour {c} is not a {theme} design token")
    if re.search(r"(rgb|hsl)a?\(", body): out.append(f"{rel}: use token hex colours, not rgb() or hsl()")
    for fam in set(re.findall(r"font-family=\"([^\"]+)\"", body)):
        if "Montserrat" not in fam and "Inter" not in fam: out.append(f"{rel}: font {fam[:30]} is not a token font")
    return out


def file_checks(doc, gen=None):
    gen = gen or os.path.join(HERE, "generated")
    out = []
    ip = os.path.join(gen, "index.json")
    if not os.path.isfile(ip):
        return ["visuals/generated/index.json is missing; run python3 visuals/generate.py"]
    idx = _load(ip)
    declared, by_id = set(), {n["id"]: n for n in doc["needs"]}
    if set(idx["needs"]) != set(by_id): out.append("index.json and needs.v1.json list different needs; run python3 visuals/generate.py")
    for nid, n in by_id.items():
        entry = idx["needs"].get(nid)
        if not entry: continue
        themes_done = {f["theme"] for f in entry["files"]}
        for th in n["themes"]:
            if th not in themes_done: out.append(f"{nid}: no file for theme {th}")
        for f in entry["files"]:
            rel = f["file"]; declared.add(rel); full = os.path.join(gen, rel)
            if not os.path.isfile(full): out.append(f"{nid}: {rel} is missing"); continue
            b = _read(full)
            if hashlib.sha256(b).hexdigest() != f["sha256"]: out.append(f"{rel}: does not match index.json")
            if len(b) == 0: out.append(f"{rel}: is empty")
            if len(b) > n["budget_kb"] * 1024: out.append(f"{rel}: {len(b) // 1024} KB is over the {n['budget_kb']} KB budget")
            if rel.endswith(".svg"):
                out += svg_problems(rel, b.decode("utf-8"), n["kind"], f["theme"], n["budget_kb"])
            elif rel.endswith(".png"):
                ok, (w, h) = _png(b)
                if not ok: out.append(f"{rel}: not a PNG")
                elif (w, h) != (f.get("w"), f.get("h")): out.append(f"{rel}: is {w}x{h}, expected {f.get('w')}x{f.get('h')}")
            elif rel.endswith(".ico"):
                if b[:4] != b"\x00\x00\x01\x00": out.append(f"{rel}: not an .ico")
    for base, _, names in os.walk(gen):
        for nme in names:
            rel = os.path.relpath(os.path.join(base, nme), gen).replace(os.sep, "/")
            if rel != "index.json" and rel not in declared: out.append(f"{rel}: has no declared need (orphan)")
    return out


def freshness_checks():
    """The SVG files must equal what the generator makes today (so nobody hand-edited or forgot to regenerate)."""
    from visuals import generate
    doc, text_files, _, _ = generate.build(png=False)
    out = []
    for rel, t in text_files.items():
        p = os.path.join(generate.OUT, rel)
        if not os.path.isfile(p) or _read(p) != t.encode("utf-8"): out.append(f"{rel}: out of date; run python3 visuals/generate.py")
    return out


def scan_code(root=ROOT, valid_ids=None):
    out = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for nme in names:
            if not nme.endswith(SCAN_EXT): continue
            full = os.path.join(base, nme); rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel.startswith(SCAN_ALLOW) or rel.endswith("needs.v1.json") or rel.endswith("package-lock.json"): continue
            try: text = _read(full, "r")
            except (UnicodeDecodeError, OSError): continue
            for i, ln in enumerate(text.splitlines(), 1):
                for rx, why in BANNED:
                    if rx.search(ln): out.append(f"{rel}:{i}: {why}")
                if valid_ids is not None and nme.endswith((".py", ".ts")) and not rel.startswith("visuals/"):
                    for m in (REFERENCE.findall(ln) + (TS_REFERENCE.findall(ln) if nme.endswith(".ts") else [])):
                        if m not in valid_ids: out.append(f"{rel}:{i}: asks for visual {m!r}, which is not in visuals/needs.v1.json")
    return out


def problems(root=ROOT):
    doc = _load(os.path.join(HERE, "needs.v1.json"))
    return need_checks(doc) + palette_checks() + card_checks() + file_checks(doc) + freshness_checks() + scan_code(root, {n["id"] for n in doc["needs"]})


if __name__ == "__main__":
    p = problems()
    print("\n".join(p) if p else "visuals gate: ok (every need has its files; nothing orphaned, off-brand, placeholder or out of date)")
    sys.exit(1 if p else 0)
