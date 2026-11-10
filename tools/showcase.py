#!/usr/bin/env python3
"""Build the owner's showcase: one offline page with everything completed so far.

    python3 tools/showcase.py            -> web/showcase/dist/lynkomni-showcase.html

Sources (never typed by hand here): web/showcase/showcase.v1.json (build sections, emulator pages),
tools/blueprint_numbers.py (counts and version), catalog/products.v1.json + services/billing.py (families),
visuals/generated/index.json + visuals.svg_text (every picture), design/tokens.v1.json (colours, fonts),
brand.for_surface (logo). The page is a draft until a human designer has signed off, like everything it shows.
"""
import html
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import brand  # noqa: E402
import visuals  # noqa: E402
from services import billing  # noqa: E402

OUT_DIR = os.path.join(ROOT, "web", "showcase", "dist")
OUT = os.path.join(OUT_DIR, "lynkomni-showcase.html")
COPYRIGHT = "© {year} CruxOmni Group. All rights reserved. LynkOmni is a product of CruxOmni Group."


def _load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def _numbers():
    out = subprocess.run([sys.executable, os.path.join(HERE, "blueprint_numbers.py")], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def _css(tokens):
    def block(theme):
        t = tokens["themes"][theme]
        return "".join(f"--{k}:{v[0]};" for k, v in t.items() if isinstance(v, list) and isinstance(v[0], str) and v[0].startswith("#"))
    fonts = tokens["fonts"]
    return f"""
:root{{{block('light')}--font-heading:{fonts['heading']};--font-body:{fonts['body']};}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{{block('dark')}}}}}
:root[data-theme="dark"]{{{block('dark')}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg-base);color:var(--text-primary);font-family:var(--font-body);font-size:16px;line-height:1.5}}
header,main,footer{{max-width:1100px;margin:0 auto;padding:16px}}
h1,h2,h3{{font-family:var(--font-heading);margin:0 0 8px;line-height:1.2}}
h1{{font-size:28px}} h2{{font-size:22px;margin-top:40px}} h3{{font-size:16px}}
p{{margin:0 0 8px}} .muted{{color:var(--text-secondary)}}
.logo{{height:40px;width:auto}} .logo-dark{{display:none}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]) .logo-light{{display:none}} :root:not([data-theme="light"]) .logo-dark{{display:inline}}}}
:root[data-theme="dark"] .logo-light{{display:none}} :root[data-theme="dark"] .logo-dark{{display:inline}}
.draft{{display:inline-block;border:1px solid var(--border-strong);border-radius:999px;padding:2px 10px;font-size:12px;color:var(--text-secondary)}}
.grid{{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}}
.card{{background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:12px;padding:16px}}
.card .pic{{display:flex;justify-content:center;align-items:center;min-height:120px;margin-block-end:8px}}
.card .pic svg{{max-width:100%;height:auto;max-height:140px}}
.card.wide{{grid-column:1/-1}} .card.wide .pic svg{{max-height:420px}}
.btn{{display:inline-block;background:var(--brand-primary);color:var(--text-on-brand,#fff);text-decoration:none;border-radius:8px;padding:10px 16px;font-weight:600;min-height:44px;line-height:24px}}
.btn:hover{{background:var(--brand-hover)}}
.nums{{display:grid;gap:8px;grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}}
.num{{background:var(--bg-subtle);border-radius:10px;padding:10px}} .num b{{display:block;font-size:24px;font-family:var(--font-heading)}}
table{{width:100%;border-collapse:collapse}} td,th{{text-align:start;padding:8px 6px;border-block-end:1px solid var(--border-subtle);vertical-align:top}}
.tag{{display:inline-block;border-radius:6px;padding:1px 8px;font-size:13px;background:var(--bg-subtle)}}
.tag.locked{{background:var(--brand-subtle);color:var(--brand-ink,var(--text-primary))}}
.tag.next{{border:1px solid var(--brand-primary)}}
footer{{color:var(--text-secondary);font-size:14px;margin-top:48px;border-block-start:1px solid var(--border-subtle)}}
nav a{{margin-inline-end:16px}}
a{{color:var(--brand-ink,var(--brand-primary))}}
"""


def _svg(vid, theme="light"):
    try:
        return visuals.svg_text(vid, theme)
    except Exception:
        return ""


def _pic_card(vid, info, wide=False):
    svg = _svg(vid)
    alt = html.escape(info.get("alt", vid))
    return (f'<div class="card{" wide" if wide else ""}"><div class="pic" role="img" aria-label="{alt}">{svg}</div>'
            f'<h3>{html.escape(vid)}</h3><p class="muted">{alt}</p>'
            f'<p class="muted">{html.escape(info.get("purpose", ""))}</p></div>')


def _device_pick(devreg, names):
    """The showcase picks the viewer's device (DEVICE 48.17) with the one decision function itself (ts/src/interfaces.ts,
    compiled by `node web/build.mjs`): capabilities only, never the browser's name. Emulators made for this kind of device
    move to the front with a "Made for this device" tag; everything else stays open to try."""
    js_path = os.path.join(ROOT, "web", ".build", "ts", "src", "interfaces.js")
    if not os.path.isfile(js_path):
        raise SystemExit("run `node web/build.mjs` first: the showcase uses the compiled decision function")
    js = open(js_path, encoding="utf-8").read().replace("export ", "")
    reg = {"safe_default": devreg["safe_default"], "interfaces": {k: {"class": v["class"]} for k, v in devreg["interfaces"].items()},
           "devices": [{"id": d["id"], "touch": d["touch"], "non_touch": d["non_touch"]} for d in devreg["devices"]]}
    return ("<script>(() => {" + js + f"const REG = {json.dumps(reg)}, NAMES = {json.dumps(names)};"
            "const c = chooseInterface(REG, browserFacts(window)), out = document.getElementById('thisDevice');"
            "out.textContent = 'This device: ' + (NAMES[c.interface] || c.interface) + '. Emulators made for it come first.'; out.hidden = false;"
            "const grid = out.nextElementSibling; const mine = [...grid.querySelectorAll('[data-views]')].filter((e) => e.dataset.views.split(' ').includes(c.interface));"
            "for (const e of mine.reverse()) { const tag = document.createElement('span'); tag.className = 'tag next'; tag.textContent = 'Made for this device'; e.querySelector('h3').after(tag); grid.prepend(e); }"
            "})();</script>")


def build():
    cfg = _load("web/showcase/showcase.v1.json")
    tokens = _load("design/tokens.v1.json")
    nums = _numbers()
    products = _load("catalog/products.v1.json")["products"]
    index = visuals.index()["needs"] if isinstance(visuals.index(), dict) and "needs" in visuals.index() else visuals.index()
    year = cfg.get("year") or 2026
    logo_l = brand.svg_text("logo", "light")
    logo_d = brand.svg_text("logo", "dark")

    parts = []
    parts.append(f'<header><span class="logo logo-light" role="img" aria-label="LynkOmni">{logo_l}</span>'
                 f'<span class="logo logo-dark" role="img" aria-label="LynkOmni">{logo_d}</span>'
                 f'<h1>Everything built so far</h1><p class="muted">LynkOmni {html.escape(nums["version"])}. Open each piece and try it; it all runs in your browser on sandbox rules, nothing is real or stored. <span class="draft">Draft design: not yet reviewed by a human designer</span></p>'
                 '<nav aria-label="Sections of this page"><a href="#try">Try it</a><a href="#progress">Progress</a><a href="#numbers">Numbers</a><a href="#products">Products</a><a href="#cards">Card faces</a><a href="#figures">Charts and diagrams</a><a href="#pictures">Other pictures</a><a href="#store">Store and web</a></nav></header><main>')

    # Emulators
    parts.append('<h2 id="try">Try it: the working emulators</h2><p id="thisDevice" class="muted" hidden></p><div class="grid">')
    devreg = _load("catalog/devices.v1.json")
    fits = {}                                   # emulator -> the interfaces it shows (catalog/devices.v1.json)
    for d in devreg["devices"]:
        for ver in ("touch", "non_touch"):
            if d["emulator"][ver] and d[ver]:
                fits.setdefault(d["emulator"][ver], set()).add(d[ver])
    shell_en = _load("web/shell/strings.en.json")
    names = {i: shell_en.get("iface_" + i.replace(".", "_"), i) for i in devreg["interfaces"]}
    for e in cfg["emulators"]:
        views = " ".join(sorted(fits.get(e["id"], ())))
        parts.append(f'<div class="card" data-emulator="{html.escape(e["id"])}" data-views="{views}"><h3>{html.escape(e["title"])}</h3><p class="muted">Build section {e["section"]}</p>'
                     f'<p>{html.escape(e["what"])}</p><p class="muted">Try: {html.escape(e["try"])}</p>'
                     f'<p><a class="btn" href="{html.escape(e["url"])}">Open {html.escape(e["title"])}</a></p></div>')
    parts.append('</div>')
    parts.append(_device_pick(devreg, names))

    # Progress
    parts.append(f'<h2 id="progress">Progress: the {len(cfg["sections"])} build steps</h2><table><thead><tr><th>#</th><th>Build section</th><th>Status</th><th>Version</th></tr></thead><tbody>')
    for s in cfg["sections"]:
        st = s.get("status", "")
        word = {"locked": "Done and locked", "next": "Next"}.get(st, "Waiting")
        parts.append(f'<tr><td>{s["n"]}</td><td>{html.escape(s["title"])}</td><td><span class="tag {st}">{word}</span></td><td>{html.escape(s.get("version", ""))}</td></tr>')
    parts.append('</tbody></table>')

    # Numbers
    labels = [("billing_families", "product families"), ("languages", "languages"), ("country_packs", "country packs"),
              ("currencies", "currencies"), ("event_types", "event types in the contract"), ("identifier_types", "identifier types"),
              ("automations", "registered automations"), ("pictures", "pictures"), ("provider_items", "provider items in the ledger")]
    parts.append('<h2 id="numbers">Numbers, read from the code</h2><div class="nums">')
    for k, lab in labels:
        if k in nums:
            parts.append(f'<div class="num"><b>{nums[k]}</b>{lab}</div>')
    parts.append('</div>')

    # Products with illustrations and prices
    parts.append('<h2 id="products">Products and their pictures</h2><p class="muted">Standard prices in US dollars per month (Free, Plus, Pro, Max), read from services/billing.py. Prices are locked (version 3).</p><div class="grid">')
    for p in products:
        fam = billing.FAMILIES.get(p["family"])
        name = fam[1] if fam else p["family"]
        long = fam[0] if fam else ""
        prices = nums.get("prices_usd", {}).get(p["family"])
        price_line = " / ".join(f"${x}" for x in prices) if prices else ""
        svg = _svg(p["illustration"])
        alt = html.escape(index.get(p["illustration"], {}).get("alt", name))
        parts.append(f'<div class="card"><div class="pic" role="img" aria-label="{alt}">{svg}</div><h3>{html.escape(name)}</h3>'
                     f'<p class="muted">{html.escape(long)}</p><p>{price_line}</p><p class="muted">lynkomni.com{html.escape(p["page"])}</p></div>')
    parts.append('</div>')

    # Card faces
    cards = sorted(v for v, i in index.items() if i["kind"] == "card")
    parts.append('<h2 id="cards">LynkVCard faces</h2><p class="muted">Free = EDGE, Plus = HUB, Pro = CORE, Max = OMNI. A face never shows a card number, name, bank or network mark; the licensed issuer adds those.</p><div class="grid">')
    for vid in cards:
        parts.append(_pic_card(vid, index[vid]))
    parts.append('</div>')

    # Charts and diagrams
    figs = sorted(v for v, i in index.items() if i["kind"] in ("chart", "diagram"))
    parts.append('<h2 id="figures">Charts and diagrams</h2><p class="muted">Figures use real numbers from the code; where a figure rests on an assumption it says so.</p><div class="grid">')
    for vid in figs:
        parts.append(_pic_card(vid, index[vid], wide=True))
    parts.append('</div>')

    # Other illustrations
    used = {p["illustration"] for p in products}
    others = sorted(v for v, i in index.items() if i["kind"] == "illustration" and v not in used)
    parts.append('<h2 id="pictures">Other pictures (empty states, onboarding, states)</h2><div class="grid">')
    for vid in others:
        parts.append(_pic_card(vid, index[vid]))
    parts.append('</div>')

    # Store and web
    rest = sorted(v for v, i in index.items() if i["kind"] in ("share", "store", "icon-set"))
    parts.append('<h2 id="store">Store, share and web images</h2><div class="grid">')
    for vid in rest:
        parts.append(_pic_card(vid, index[vid], wide=(index[vid]["kind"] == "share")))
    parts.append('</div></main>')

    parts.append(f'<footer><p>{html.escape(COPYRIGHT.format(year=year))}</p><p>Generated by tools/showcase.py from the code; everything shown is a draft until a human designer signs off.</p></footer>')

    # the tab icon (brand surface "favicon"): the light-theme emblem for light browsers, the dark-theme emblem for dark ones
    import re as _re, urllib.parse as _up
    def _fav(th):
        svg = _re.sub(r'\s+(role|aria-label|focusable)="[^"]*"', "", open(brand.for_surface("favicon", th).path, encoding="utf-8").read())
        return f'<link rel="icon" type="image/svg+xml" media="(prefers-color-scheme: {th})" href="data:image/svg+xml,{_up.quote(svg)}">'
    doc = ('<!doctype html><html lang="en" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>LynkOmni Showcase</title><meta name="description" content="Everything built so far in LynkOmni: working emulators, progress, numbers and every picture.">'
           f'{_fav("light")}{_fav("dark")}<style>{_css(tokens)}</style></head><body>{"".join(parts)}</body></html>')
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    return OUT


if __name__ == "__main__":
    path = build()
    print(path, os.path.getsize(path) // 1024, "KB")
