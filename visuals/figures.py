"""Charts, the sync-state diagram and composite images (share card, store graphics, app icons).

Charts use real numbers read from the code (services/billing.py, finance/revenue_model.py, design tokens); nothing
is typed in by hand. Where a number is an assumption the picture says so. Logos are placed only through the brand
module, wrapped in <g data-brand="..."> so the gate knows they are brand artwork, not drawing colours."""
import math, os, re, sys
from .kit import ROOT, Palette, rr, circ, line, path, group, el, frame, text, esc, n, backdrop, pen, _design
from .scenes import SCENES

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import brand  # noqa: E402
from services import billing  # noqa: E402
from finance import revenue_model  # noqa: E402

SKIP_PRICE_CHART = ("lynkdev", "lynksuite")   # other price scales; the chart says so


def _inner(svg):
    m = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S)
    return m.group(1)


def _viewbox(svg):
    return [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]


def brand_asset(asset_id, theme, x, y, width, surface_id=None):
    """Brand artwork placed at x, y with a given width, through the brand module (never a file name here)."""
    a = brand.for_surface(surface_id, theme, width) if surface_id else brand.asset(asset_id, theme)
    with open(a.path, encoding="utf-8") as fh:
        svg = fh.read()
    vx, vy, vw, vh = _viewbox(svg)
    h = width * vh / vw
    return f'<g data-brand="{asset_id}"><svg x="{n(x)}" y="{n(y)}" width="{n(width)}" height="{n(round(h, 1))}" viewBox="{n(vx)} {n(vy)} {n(vw)} {n(vh)}">{_inner(svg)}</svg></g>', h


def emblem(theme, x, y, size):
    return brand_asset("emblem", theme, x, y, size, "app-icon")


# ------------------------------------------------------------------ charts
def pricing_ladder(theme):
    """Standard monthly USD price of the Plus, Pro and Max tiers for each product family (services/billing.py)."""
    p = Palette(theme)
    fams = [(k, v) for k, v in billing.FAMILIES.items() if k not in SKIP_PRICE_CHART]
    W, top, row, left, scale_w = 720, 92, 30, 128, 380
    vmax = max(v[3][3] for _, v in fams)
    H = top + row * len(fams) + 84
    fills = (p.brand_soft, p.brand, p.ink)
    body = [rr(0, 0, W, H, 0, p.base, stroke="none"), text(24, 34, "Standard monthly price by tier (USD)", p, 20, 700, family="heading")]
    for i, (lab, f) in enumerate(zip(("Plus", "Pro", "Max"), fills)):
        x = 24 + 96 * i
        body += [rr(x, 50, 14, 14, 3, f, stroke=p.ink, stroke_width=1.5), text(x + 22, 62, lab, p, 14)]
    for r, (k, v) in enumerate(fams):
        y = top + r * row
        body.append(text(left - 12, y + 16, v[1], p, 13, 500, "end"))
        for t in range(3):
            price = v[3][t + 1]
            w = max(2, scale_w * price / vmax)
            body.append(rr(left, y + t * 8, w, 7, 2, fills[t], stroke=p.ink, stroke_width=1))
        body.append(text(left + scale_w + 16, y + 16, " · ".join(f"${v[3][t + 1]:g}" for t in range(3)), p, 13, 400, fill=p.ink2))
    body.append(text(24, H - 28, "LynkSuite and LynkDev use their own price scales and are not shown. Free tier is $0.", p, 12, fill=p.ink2))
    body.append(text(24, H - 10, "Source: services/billing.py (prices locked v1).", p, 12, fill=p.ink2))
    alt = ("Bar chart of the standard monthly price in US dollars for the Plus, Pro and Max tiers of each LynkOmni product family, "
           "with the three prices written beside every row. LynkSuite and LynkDev are not shown.")
    return frame("chart-pricing-ladder", alt, "".join(body), W, H)


def revenue_path(theme):
    """Modelled monthly revenue at the end of each growth stage (finance/revenue_model.py). An assumption, not a forecast."""
    p = Palette(theme)
    pts = revenue_model.path()
    W, H, base_y, top_y, left = 720, 420, 330, 96, 104
    lo, hi = 3.0, 8.0     # log10 range of the vertical axis ($1,000 to $100,000,000)
    body = [rr(0, 0, W, H, 0, p.base, stroke="none"), text(24, 34, "Modelled monthly revenue by number of merchants", p, 20, 700, family="heading"),
            text(24, 58, "Assumption-based model, not a forecast. Vertical axis is logarithmic.", p, 13, fill=p.ink2)]
    for e in range(int(lo), int(hi) + 1):
        y = base_y - (e - lo) / (hi - lo) * (base_y - top_y)
        body += [line(left, y, W - 24, y, stroke=p.line, stroke_width=1, stroke_dasharray="2 5"), text(left - 8, y + 4, f"${10 ** e:,}", p, 11, 400, "end", fill=p.ink2)]
    keys = sorted(pts)
    step = (W - 24 - left) / len(keys)
    for i, k in enumerate(keys):
        v = pts[k]
        h = (math.log10(v["end"]) - lo) / (hi - lo) * (base_y - top_y)
        x = left + i * step + step * .2
        bw = step * .6
        body += [rr(x, base_y - h, bw, h, 3, p.brand if k == keys[-1] else p.brand_soft, stroke=p.ink, stroke_width=1.5),
                 text(x + bw / 2, base_y - h - 8, f"${v['end']:,}", p, 12, 600, "middle"),
                 text(x + bw / 2, base_y + 20, f"{v['merchants']:,}", p, 12, 400, "middle"),
                 ]
    body.append(text(left, base_y + 44, "Merchants (stage by stage). Source: finance/revenue_model.py.", p, 12, fill=p.ink2))
    alt = ("Column chart of modelled monthly revenue in US dollars at each growth stage, from 500 to 2,000,000 merchants, on a logarithmic "
           "scale. It is an assumption-based model, not a forecast, and each column's value is written above it.")
    return frame("chart-revenue-path", alt, "".join(body), W, H)


# ------------------------------------------------------------------ diagram
def sync_states(theme):
    """Where each of the five user-facing states happens (design/tokens.v1.json `states`; brand status icons)."""
    p = Palette(theme)
    W, H = 760, 330
    states = _design.SRC["states"]
    body = [rr(0, 0, W, H, 0, p.base, stroke="none"), text(24, 34, "How a sale moves, and what each state means", p, 20, 700, family="heading")]
    order = ("queued", "sent", "accepted", "confirmed", "failed")
    cw, gap = 132, 14
    x0 = (W - (cw * 5 + gap * 4)) / 2
    nodes = [("This device", None), ("Nearby relay", "(optional)"), ("Cloud", None), ("Payment provider", None), ("Any step", None)]
    for i, (l1, l2) in enumerate(nodes):
        x = x0 + i * (cw + gap)
        dashed = i in (1, 4)
        body.append(rr(x, 64, cw, 64, 12, p.surface, stroke=p.ink, stroke_width=2.5, stroke_dasharray="5 5" if dashed else None))
        if l2:
            body += [text(x + cw / 2, 93, l1, p, 14, 600, "middle"), text(x + cw / 2, 112, l2, p, 12, 400, "middle", fill=p.ink2)]
        else:
            body.append(text(x + cw / 2, 101, l1, p, 14, 600, "middle"))
        if i < 3:
            ax = x + cw
            body.append(path(f"M{n(ax + 2)} 96H{n(ax + gap - 2)}", fill="none", stroke=p.ink, stroke_width=2.5))
            body.append(path(f"M{n(ax + gap - 8)} 90l6 6 -6 6", fill="none", stroke=p.ink, stroke_width=2.5))
    for i, key in enumerate(order):
        st = states[key]
        x, y = x0 + i * (cw + gap), 170
        bg, fg = {"neutral": (p.ground, p.ink), "info": (p.brand_soft, p.ink), "success": (p.ok_bg, p.ok), "danger": (p.bad_bg, p.bad)}[st["tone"]]
        body.append(path(f"M{n(x + cw / 2)} 128V170", fill="none", stroke=p.ink2, stroke_width=1.5, stroke_dasharray="3 4"))
        body.append(rr(x, y, cw, 52, 10, bg, stroke=fg, stroke_width=2))
        ic = brand.icon_svg(f"status-{key}")
        body.append(f'<g transform="translate({n(x + 12)} {n(y + 14)})" color="{fg}" stroke="{fg}" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{_inner(ic)}</g>')
        body.append(text(x + 44, y + 31, st["label"], p, 15, 600, fill=fg))
    notes = [("queued", "Saved on this device, not sent yet."), ("sent", "Left this device, awaiting the cloud."), ("accepted", "The cloud stored it. No money confirmed."),
             ("confirmed", "The provider confirmed it."), ("failed", "It did not go through.")]
    for i, (k, s) in enumerate(notes):
        x = x0 + i * (cw + gap)
        words, line_, lines = s.split(), "", []
        for w_ in words:
            if len(line_ + w_) > 19:
                lines.append(line_.strip()); line_ = ""
            line_ += w_ + " "
        lines.append(line_.strip())
        for j, ln in enumerate(lines):
            body.append(text(x + 4, 246 + 16 * j, ln, p, 12, 400, fill=p.ink2))
    body.append(text(24, H - 8, "A relayed sale stays “sent” until the cloud accepts it. LynkOmni never holds the money.", p, 12, fill=p.ink2))
    alt = ("Diagram of a sale moving from this device, optionally through a nearby relay, to the cloud and then the payment provider, "
           "with the five states Queued, Sent, Accepted, Confirmed and Failed, each with an icon, a label and a short meaning.")
    return frame("diagram-sync-states", alt, "".join(body), W, H)


# ------------------------------------------------------------------ composites
def _scene_group(name, theme, x, y, scale, accent="brand"):
    p = Palette(theme, accent)
    return f'<g transform="translate({n(x)} {n(y)}) scale({scale})">{SCENES[name](p)}</g>'


def share_card(theme):
    """1200 x 630 link-preview image: logo and one picture, no words."""
    p = Palette(theme)
    logo, h = brand_asset("logo", theme, 90, 0, 470, "share-image")
    logo, _ = brand_asset("logo", theme, 90, (630 - h) / 2, 470, "share-image")
    body = (rr(0, 0, 1200, 630, 0, p.base, stroke="none") + el("circle", cx="890", cy="315", r="270", fill=p.brand_soft) +
            rr(0, 0, 1200, 14, 0, p.brand, stroke="none") + logo + _scene_group("suite", theme, 570, 75, 2.0))
    return frame("share-card", "LynkOmni logo beside a hub connected to seven small tiles, standing for the connected products.", body, 1200, 630)


def store_feature(theme):
    """1024 x 500 store feature graphic: logo and one picture, no words."""
    p = Palette(theme)
    logo, _ = brand_asset("logo", theme, 72, 70, 380, "share-image")
    body = (rr(0, 0, 1024, 500, 0, p.base, stroke="none") + el("circle", cx="770", cy="260", r="240", fill=p.brand_soft) + rr(0, 0, 1024, 12, 0, p.brand, stroke="none") +
            logo + _scene_group("onboard-offline", theme, 530, 40, 1.45) + _scene_group("pos", theme, 40, 240, .8))
    return frame("store-feature-graphic", "LynkOmni logo with a phone that has saved a sale and a cash register, showing selling that works without internet.", body, 1024, 500)


def app_icon(theme, size_pct=58, rounded=False, bg=None, view=1024):
    """Square launcher icon: emblem centred on the theme background (full bleed; the stores apply their own mask)."""
    p = Palette(theme)
    s = view * size_pct / 100
    r = view * .22 if rounded else 0
    _, h = emblem(theme, 0, 0, s)
    mark, _ = emblem(theme, (view - s) / 2, (view - h) / 2, s)
    body = rr(0, 0, view, view, r, bg or p.base, stroke="none") + mark
    return frame(f"app-icon-{theme}", "LynkOmni emblem on a plain background.", body, view, view)
