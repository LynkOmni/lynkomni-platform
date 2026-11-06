#!/usr/bin/env python3
"""Generates every platform's tokens from design/tokens.v1.json. Run: python3 design/generate.py   (add --check to verify nothing is stale)."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = json.load(open(os.path.join(HERE, "tokens.v1.json")))
OUT = {"design/generated/tokens.css": None, "design/generated/tailwind.preset.cjs": None, "ts/src/tokens.ts": None,
       "android/core/src/main/kotlin/com/lynkomni/core/Tokens.kt": None, "ios/Sources/LynkCore/Tokens.swift": None}
HEADER = "GENERATED from design/tokens.v1.json by design/generate.py. Do not edit by hand."

def resolved(theme):
    """A theme's full token map. High-contrast themes inherit from the matching base theme."""
    base = {"contrast-light": "light", "contrast-dark": "dark"}.get(theme, theme)
    out = {k: v[0] for k, v in SRC["common"].items()}
    out.update({k: v[0] for k, v in SRC["themes"][base].items()})
    if theme != base: out.update({k: v[0] for k, v in SRC["themes"][theme].items()})
    return out
def rgba(v):
    m = re.match(r"rgba\((\d+), (\d+), (\d+), ([\d.]+)\)", v)
    if m: return int(m[1]), int(m[2]), int(m[3]), round(float(m[4]) * 255)
    return int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16), 255
def camel(n): p = n.split("-"); return p[0] + "".join(x.capitalize() for x in p[1:])
def block(sel, m, only=None):
    items = [(k, v) for k, v in m.items() if only is None or k in only]
    return sel + " {\n" + "\n".join(f"  --{k}: {v};" for k, v in items) + "\n}\n"

def css():
    F = SRC["fonts"]; L, D = resolved("light"), resolved("dark"); CL, CD = SRC["themes"]["contrast-light"], SRC["themes"]["contrast-dark"]
    dark_only = {k: v for k, v in D.items() if L.get(k) != v}
    cl = {k: v[0] for k, v in CL.items()}; cd = {k: v[0] for k, v in CD.items()}
    s = f"/* {HEADER} */\n:root {{\n  color-scheme: light;\n  --font-heading: {F['heading']};\n  --font-body: {F['body']};\n  --font-mono: {F['mono']};\n  --font-feature-tabular: {F['feature_tabular']};\n"
    s += f"  --touch-target: {SRC['modes']['touch_target_px'] / 16}rem;\n"
    s += "".join(f"  --text-{px}: {px / 16}rem;\n" for px in F["scale_px"])
    s += "".join(f"  --{k}: {v};\n" for k, v in L.items()) + "}\n"
    s += block(".dark", dark_only).replace(".dark {\n", ".dark {\n  color-scheme: dark;\n", 1)
    s += "@media (prefers-color-scheme: dark) {\n" + block(":root:not(.light):not(.dark)", dark_only).replace("\n", "\n  ").replace(":root:not(.light):not(.dark) {\n", "  :root:not(.light):not(.dark) {\n  color-scheme: dark;\n", 1).rstrip(" ") + "}\n"
    s += "/* High contrast (sunlight mode): set data-contrast=\"high\" on <html>, or the device asks for it. */\n"
    s += block("[data-mode=\"sunlight\"]", cl) + block(".dark[data-mode=\"sunlight\"]", cd)
    s += block("[data-contrast=\"high\"]", cl) + block(".dark[data-contrast=\"high\"]", cd)
    s += "@media (prefers-contrast: more) {\n" + block(":root:not([data-contrast])", cl).replace("\n", "\n  ").rstrip(" ").replace("  :root", ":root", 0) + block(":root.dark:not([data-contrast])", cd).replace("\n", "\n  ").rstrip(" ") + "}\n"
    s += "@media (forced-colors: active) {\n  :root, .dark { --brand-primary: Highlight; --brand-ink: LinkText; --text-primary: CanvasText; --bg-base: Canvas; --bg-surface: Canvas; --border-input: CanvasText; --focus-ring: Highlight; }\n}\n"
    s += """body { background-color: var(--bg-base); color: var(--text-primary); font-family: var(--font-body); font-weight: 400; line-height: 1.5; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
h1, h2, h3, h4, h5, h6, .font-heading { font-family: var(--font-heading); font-weight: 600; letter-spacing: -0.01em; }
.badge-label, .micro-chip { font-family: var(--font-heading); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
table, .financial-ledger, .numeric-data { font-family: var(--font-body); font-feature-settings: var(--font-feature-tabular); }
pre, code, kbd, samp, .code { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }
:disabled, [aria-disabled="true"] { color: var(--text-muted); }
::placeholder { color: var(--text-secondary); }
input, select, textarea { border: 1px solid var(--border-input); }
html:lang(ar), html:lang(he), html:lang(fa), html:lang(ur) { direction: rtl; }
button, [role="button"], a.btn, input:not([type="checkbox"]):not([type="radio"]), select { min-height: var(--touch-target); min-width: var(--touch-target); }
html { font-size: 100%; }
[data-mode="lite"] { --font-heading: var(--font-body); --font-body: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif; }
[data-mode="lite"] *, [data-mode="lite"] *::before, [data-mode="lite"] *::after { animation: none !important; transition: none !important; }
[data-mode="lite"] .lite-hide, [data-mode="lite"] img[data-decorative] { display: none !important; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; } }
"""
    for k, v in SRC["states"].items():
        s += f".state-{k} {{ color: var(--status-{v['tone']}-text); background: var(--status-{v['tone']}-bg); border: 1px solid var(--status-{v['tone']}-border); }}\n"
    return s
def tailwind():
    names = sorted(set(resolved("light")) | set(resolved("dark")))
    colors = ",\n".join(f"        '{k}': 'var(--{k})'" for k in names)
    return f"/* {HEADER} */\nmodule.exports = {{\n  darkMode: 'class',\n  theme: {{ extend: {{\n    fontFamily: {{ heading: ['var(--font-heading)'], body: ['var(--font-body)'], mono: ['var(--font-mono)'] }},\n    colors: {{\n{colors}\n    }},\n    fontSize: {{ {', '.join(f'{chr(39)}t{px}{chr(39)}: {chr(39)}{px / 16}rem{chr(39)}' for px in SRC['fonts']['scale_px'])} }},\n  }} }},\n  plugins: [],\n}};\n"
def ts():
    def obj(m): return "{\n" + ",\n".join(f'    "{k}": "{v}"' for k, v in m.items()) + "\n  }"
    s = f"// {HEADER}\nexport const tokens = {{\n"
    s += f"  fonts: {json.dumps({k: v for k, v in SRC['fonts'].items()})},\n"
    for t in ("light", "dark", "contrast-light", "contrast-dark"): s += f'  "{t}": {obj(resolved(t))},\n'
    s += f"  states: {json.dumps(SRC['states'])},\n  modes: {json.dumps(SRC['modes'])},\n"
    return s + "} as const;\nexport type ThemeName = \"light\" | \"dark\" | \"contrast-light\" | \"contrast-dark\";\n"
def kotlin():
    def obj(t): return f"    val {camel(t)}: Map<String, Long> = mapOf(\n" + ",\n".join(f'        "{k}" to 0x{a:02X}{r:02X}{g:02X}{b:02X}L' for k, v in resolved(t).items() for r, g, b, a in [rgba(v)]) + "\n    )"
    return f"// {HEADER}\npackage com.lynkomni.core\n\n/** Colours as ARGB longs. Fonts: Montserrat headings, Inter body, bundled in the app so they work offline. */\nobject Tokens {{\n" + "\n".join(obj(t) for t in ("light", "dark", "contrast-light", "contrast-dark")) + "\n" + "    val states: Map<String, Triple<String, String, String>> = mapOf(\n" + ",\n".join(f'        "{k}" to Triple("{v["label"]}", "{v["icon"]}", "{v["tone"]}")' for k, v in SRC["states"].items()) + "\n    )\n}\n"
def swift():
    def obj(t): return f"    public static let {camel(t)}: [String: UInt32] = [\n" + ",\n".join(f'        "{k}": 0x{a:02X}{r:02X}{g:02X}{b:02X}' for k, v in resolved(t).items() for r, g, b, a in [rgba(v)]) + "\n    ]"
    return f"// {HEADER}\n/// Colours as ARGB values. Fonts: Montserrat headings, Inter body, bundled in the app so they work offline.\npublic enum Tokens {{\n" + "\n".join(obj(t) for t in ("light", "dark", "contrast-light", "contrast-dark")) + "\n" + "    public static let states: [String: (label: String, icon: String, tone: String)] = [\n" + ",\n".join(f'        "{k}": ("{v["label"]}", "{v["icon"]}", "{v["tone"]}")' for k, v in SRC["states"].items()) + "\n    ]\n}\n"
def build(): return {"design/generated/tokens.css": css(), "design/generated/tailwind.preset.cjs": tailwind(), "ts/src/tokens.ts": ts(),
                     "android/core/src/main/kotlin/com/lynkomni/core/Tokens.kt": kotlin(), "ios/Sources/LynkCore/Tokens.swift": swift()}
if __name__ == "__main__":
    stale = []
    for rel, text in build().items():
        p = os.path.join(ROOT, rel)
        if "--check" in sys.argv:
            if not os.path.exists(p) or open(p).read() != text: stale.append(rel)
        else:
            os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(text)
    if stale: print("stale:", stale); sys.exit(1)
    print("ok")
