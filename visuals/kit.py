"""Drawing kit for LynkOmni visuals: a palette read from the design tokens and a few shape helpers.

Nothing here writes a colour by hand. Every colour comes from design/tokens.v1.json through `Palette`, so a
change of tokens changes every picture the next time `python3 visuals/generate.py` runs.

Style (version 1): flat shapes, 3 px rounded outlines, one accent per product, a soft ground shadow, no text
inside illustrations, no faces or people. Charts and diagrams may contain text; that text is real data."""
import math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from design import generate as _design  # noqa: E402

THEMES = ("light", "dark", "contrast-light", "contrast-dark")
STROKE = 3

# Which accent each product family wears. Everything not listed uses the brand violet.
ACCENT_OF = {"lynkbooking": "booking", "lynkessential": "essential", "lynkvcard": "vcard", "lynkmpay": "exchange", "lynkhub": "hub"}


def _lum(hexv):
    h = hexv.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class Palette:
    """The colours one picture may use, for one theme and one accent."""

    def __init__(self, theme, accent="brand"):
        t = _design.resolved(theme)
        self.theme, self.accent_name = theme, accent
        self.base, self.surface, self.ground = t["bg-base"], t["bg-surface"], t["bg-subtle"]
        self.ink, self.ink2, self.line = t["text-primary"], t["text-secondary"], t["border-strong"]
        self.brand, self.brand_soft = t["brand-primary"], t["brand-subtle"]
        if accent == "brand":
            self.accent, self.accent_soft = self.brand, self.brand_soft
        elif accent == "hub":
            self.accent, self.accent_soft = t["accent-hub"], self.ground
        else:
            self.accent = t[f"accent-{accent}"]
            self.accent_soft = {"booking": t["status-info-bg"], "essential": t["status-success-bg"], "exchange": t["status-warning-bg"], "vcard": t["brand-subtle"]}[accent]
        # Marks drawn on top of an accent fill use whichever of ink or base reads better on it.
        self.on_accent = max((self.ink, self.base), key=lambda c: contrast(c, self.accent))
        self.ok, self.ok_bg = t["status-success-text"], t["status-success-bg"]
        self.warn, self.warn_bg = t["status-warning-text"], t["status-warning-bg"]
        self.bad, self.bad_bg = t["status-danger-text"], t["status-danger-bg"]
        self.accent_ink = t.get(f"accent-{accent}-ink", t["brand-ink"]) if accent not in ("brand", "hub") else (t["brand-ink"] if accent == "brand" else t["text-primary"])

    def colours(self):
        return {v.upper() for k, v in vars(self).items() if isinstance(v, str) and v.startswith("#")}


def _attrs(kw):
    out = []
    for k, v in kw.items():
        if v is None:
            continue
        out.append(f'{k.rstrip("_").replace("_", "-")}="{v}"')
    return " ".join(out)


def el(tag, *children, **kw):
    a = _attrs(kw)
    inner = "".join(children)
    return f"<{tag} {a}>{inner}</{tag}>" if inner else f"<{tag} {a}/>"


def n(x):
    return str(int(x)) if float(x) == int(x) else f"{x:.1f}".rstrip("0").rstrip(".")


def rr(x, y, w, h, r=8, fill="none", **kw):
    return el("rect", x=n(x), y=n(y), width=n(w), height=n(h), rx=n(r), fill=fill, **kw)


def circ(cx, cy, r, fill="none", **kw):
    return el("circle", cx=n(cx), cy=n(cy), r=n(r), fill=fill, **kw)


def line(x1, y1, x2, y2, **kw):
    return el("line", x1=n(x1), y1=n(y1), x2=n(x2), y2=n(y2), **kw)


def path(d, fill="none", **kw):
    return el("path", d=d, fill=fill, **kw)


def group(*children, **kw):
    return el("g", *children, **kw)


def plain(**kw):
    """No outline (for soft shapes)."""
    return dict(stroke="none", **kw)


def check(cx, cy, s, color, w=None):
    """A check mark centred at cx, cy, about s wide."""
    return path(f"M{n(cx - s / 2)} {n(cy)}l{n(s * .32)} {n(s * .32)} {n(s * .68)} {n(-s * .66)}", stroke=color, stroke_width=w or STROKE)


def cross(cx, cy, s, color, w=None):
    h = s / 2
    return path(f"M{n(cx - h)} {n(cy - h)}l{n(s)} {n(s)}M{n(cx + h)} {n(cy - h)}l{n(-s)} {n(s)}", stroke=color, stroke_width=w or STROKE)


def sparkle(cx, cy, r, fill):
    d = f"M{n(cx)} {n(cy - r)}Q{n(cx)} {n(cy)} {n(cx + r)} {n(cy)}Q{n(cx)} {n(cy)} {n(cx)} {n(cy + r)}Q{n(cx)} {n(cy)} {n(cx - r)} {n(cy)}Q{n(cx)} {n(cy)} {n(cx)} {n(cy - r)}Z"
    return path(d, fill=fill, stroke="none")


def star(cx, cy, r, fill, p):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * .45
        pts.append(f"{n(round(cx + rad * math.cos(a), 1))},{n(round(cy + rad * math.sin(a), 1))}")
    return el("polygon", points=" ".join(pts), fill=fill)


def cloud(x, y, s, fill):
    """A cloud whose left edge is x and baseline is y; s scales it (1 = 140 px wide)."""
    d = f"M{n(x + 28 * s)} {n(y)}a{n(28 * s)} {n(28 * s)} 0 0 1 {n(4 * s)} {n(-56 * s)}a{n(40 * s)} {n(40 * s)} 0 0 1 {n(76 * s)} {n(8 * s)}a{n(24 * s)} {n(24 * s)} 0 0 1 {n(4 * s)} {n(48 * s)}z"
    return path(d, fill=fill)


def backdrop(p, seed=0):
    """Ground shadow and a few quiet dots. `seed` moves them so every picture is not identical."""
    dots = [(52, 64, 4), (272, 78, 3), (36, 150, 3), (284, 150, 4)]
    if seed % 2:
        dots = [(60, 52, 3), (264, 62, 4), (44, 132, 4), (276, 140, 3)]
    bits = [el("ellipse", cx="160", cy="206", rx="112", ry="14", fill=p.ground, stroke="none")]
    bits += [circ(x, y, r, p.accent, stroke="none") for x, y, r in dots[:2]]
    bits += [circ(x, y, r, p.accent_soft, stroke="none") for x, y, r in dots[2:]]
    bits.append(path("M262 36h12M268 30v12", stroke=p.ink2, stroke_width=2))
    return "".join(bits)


def frame(pid, alt, body, w=320, h=240, text_font=None):
    """Wrap a picture as a standalone SVG with a title (the accessible name)."""
    tid = f"t-{pid}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="{tid}" focusable="false">'
            f'<title id="{tid}">{esc(alt)}</title>{body}</svg>')


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def pen(p, **kw):
    """The default outline group every scene sits in."""
    return dict(stroke=p.ink, stroke_width=STROKE, stroke_linecap="round", stroke_linejoin="round", fill="none", **kw)


def text(x, y, s, p, size=14, weight=400, anchor="start", fill=None, family="body", **kw):
    fam = {"body": _design.SRC["fonts"]["body"], "heading": _design.SRC["fonts"]["heading"]}[family]
    return el("text", esc(s), x=n(x), y=n(y), fill=fill or p.ink, font_size=n(size), font_weight=weight, text_anchor=anchor,
              font_family=fam.replace('"', "'"), stroke="none", **kw)
