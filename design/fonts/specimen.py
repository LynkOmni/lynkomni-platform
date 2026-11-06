#!/usr/bin/env python3
"""Writes a self-contained font specimen page: every LynkOmni language in its heading and body font, in its own writing
direction, with a price in that language's number style. All fonts are inside the file (works offline).
Run: python3 design/fonts/specimen.py <output.html>"""
import base64, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_fonts as bf  # noqa: E402

CURRENCY = {"ar": "AED", "fa": "AED", "ur": "AED", "ps": "AED", "ckb": "AED", "sd": "AED", "ug": "AED", "he": "AED", "yi": "AED",
            "hi": "INR", "sw": "KES", "rw": "RWF", "fr": "RWF", "es": "USD", "en": "USD"}   # sample prices only: display, not data


def read(p, mode="r"):
    with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def main(out):
    reg = bf.registry()
    css = read(os.path.join(DESIGN, "fonts.css"))
    css = re.sub(r"url\('/fonts/([\w-]+\.woff2)'\)", lambda m: "url(data:font/woff2;base64," + base64.b64encode(read(os.path.join(HERE, m.group(1)), "rb")).decode() + ")", css)
    tokens = read(os.path.join(DESIGN, "generated", "tokens.css"))
    rows = []
    for code, L in reg["languages"].items():
        s = reg["scripts"][L["script"]]
        fam = lambda r: reg["families"][s[r]]["name"]
        rows.append(f"""<article class="lang" lang="{code}" dir="{s['dir']}">
  <header><h2>{html.escape(L['native'])}</h2><span class="meta" lang="en" dir="ltr">{html.escape(L['name'])} · {code} · {L['script']} · {s['dir'].upper()}</span></header>
  <p class="sample">{html.escape(L['sample'])}</p>
  <p class="letters">{html.escape(L['letters'])}</p>
  <div class="bar"><span class="pill" data-lang="{code}" data-cur="{CURRENCY.get(code, 'USD')}">1500</span><span class="arrow" aria-hidden="true">→</span></div>
  <footer lang="en" dir="ltr">Heading: {html.escape(fam('heading'))} · Body: {html.escape(fam('body'))}</footer>
</article>""")
    page = f"""<meta charset="utf-8">
<title>LynkOmni Font System</title>
<meta name="description" content="Every LynkOmni language in its brand font and writing direction.">
<style>{css}
{tokens}
body {{ margin: 0; }}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px max(16px, env(safe-area-inset-right, 0px)) 48px max(16px, env(safe-area-inset-left, 0px)); }}
.wrap > h1 {{ margin: 0 0 4px; font-size: 28px; }}
.intro {{ margin: 0 0 20px; color: var(--text-secondary); max-width: 70ch; }}
.draft {{ display: inline-block; margin-inline-start: 8px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--status-warning-border); background: var(--status-warning-bg); color: var(--status-warning-text); font-size: 12px; font-weight: 600; vertical-align: middle; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); gap: 12px; }}
.lang {{ background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; min-width: 0; }}
.lang header {{ display: flex; align-items: baseline; justify-content: space-between; gap: 8px; flex-wrap: wrap; }}
.lang h2 {{ margin: 0; font-size: 24px; }}
.meta {{ font: 600 11px var(--font-body); color: var(--text-secondary); text-transform: uppercase; letter-spacing: .05em; }}
.sample {{ margin: 0; font: 600 30px var(--font-heading); }}
.letters {{ margin: 0; font-size: 18px; overflow-wrap: anywhere; }}
.bar {{ display: flex; align-items: center; gap: 8px; }}
.pill {{ padding: 4px 12px; border-radius: 999px; background: var(--brand-subtle); color: var(--brand-ink); font-weight: 700; font-feature-settings: var(--font-feature-tabular); }}
.dark .pill {{ background: var(--bg-subtle); }}
.arrow {{ color: var(--text-secondary); margin-inline-start: auto; }}
[dir="rtl"] .arrow {{ transform: scaleX(-1); }}
.lang footer {{ font-size: 12px; color: var(--text-secondary); border-top: 1px solid var(--border-subtle); padding-top: 6px; margin-top: auto; }}
</style>
<div class="wrap">
<h1>LynkOmni font system <span class="draft">Draft</span></h1>
<p class="intro">{len(reg['languages'])} languages, {len(reg['scripts'])} scripts. Right-to-left languages run from the right, and their arrow points the other way. Every font is inside this page, so it works without internet. Sample words are short greetings; native speakers should review every translation before launch.</p>
<div class="grid">{"".join(rows)}</div>
</div>
<script>
const set = () => {{ const t = document.documentElement.getAttribute("data-theme"); document.documentElement.classList.toggle("dark", t === "dark" || (!t && matchMedia("(prefers-color-scheme: dark)").matches)); }};
set(); new MutationObserver(set).observe(document.documentElement, {{ attributes: true, attributeFilter: ["data-theme"] }});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", set);
document.querySelectorAll(".pill").forEach((el) => {{
  try {{ el.textContent = new Intl.NumberFormat(el.dataset.lang, {{ style: "currency", currency: el.dataset.cur }}).format(Number(el.textContent)); }} catch (e) {{}}
}});
</script>
"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {out} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1])
