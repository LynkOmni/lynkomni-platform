"""LynkVCard faces, one per tier, and the tier ladder diagram.

Tier names, colours and design ideas come from the approved LynkVCard specification:
  Free = EDGE (slate, one dot etched at the edge), Plus = HUB (brushed silver, a hub with three lines),
  Pro = CORE (jet black, a glowing core dot with a spend ring), Max = OMNI (obsidian, a sphere, no numbers on the front).
Card colours are the design tokens vcard-edge-bg, vcard-hub-bg, vcard-core-bg and vcard-omni-bg and the matching on-vcard-* text colours.

Rules for these pictures (also in CLAUDE.md): a face never shows a card number, a card holder name, a bank name or a payment
network mark (the licensed issuer adds the network mark and prints the last four digits itself); the only words are the fixed
tier line below; the emblem comes from the brand module (surface vcard-face, one colour). Prices and limits in the ladder are read
from services/billing.py and are placeholders until market-tested."""
import math
from .kit import rr, circ, line, path, el, text, frame, n, esc, Palette, _design
from . import figures
from services import billing

TIERS = ("edge", "hub", "core", "omni")
FAMILY_TIER = {"free": "edge", "plus": "hub", "pro": "core", "max": "omni"}     # billing tier -> card
# The only words allowed on a card face (from the approved spec). The check fails on any other text.
TIER_TEXT = {"edge": "EDGE // FIRST LIGHT", "hub": "HUB // CENTER POINT", "core": "CORE // DEEP SYSTEM", "omni": "OMNI // OWN ALL COMMERCE"}
ALT = {
    "edge": "Slate grey LynkVCard for the Free tier: one dot etched near the right edge with pulse rings, the emblem, masked number dots and the line EDGE // FIRST LIGHT.",
    "hub": "Brushed silver LynkVCard for the Plus tier: a hub with three lines running out to three nodes, the emblem, masked number dots and the line HUB // CENTER POINT.",
    "core": "Jet black LynkVCard for the Pro tier: a glowing green core dot inside a spend ring that is partly filled, the emblem, masked number dots and the line CORE // DEEP SYSTEM.",
    "omni": "Solid obsidian LynkVCard for the Max tier: an engraved sphere, the emblem, a polished edge, no number on the front, and the line OMNI // OWN ALL COMMERCE.",
}
W, H = 340, 214
START, END = "<!--card:start-->", "<!--card:end-->"   # colours between these markers may use the dark-theme glow tokens


def _tok():
    return _design.resolved("dark")


def _pt(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _centrepiece(tier, fg, t):
    cx, cy = 214, 88
    if tier == "edge":
        return (circ(300, 107, 20, "none", stroke=fg, stroke_opacity=".22", stroke_width=1.5) + circ(300, 107, 12, "none", stroke=fg, stroke_opacity=".45", stroke_width=1.5) +
                circ(300, 107, 6, fg, stroke="none"))
    if tier == "hub":
        parts = ""
        for deg in (-90, 30, 150):
            x, y = _pt(cx, cy, 46, deg)
            parts += (line(cx, cy, x, y, stroke=fg, stroke_opacity=".18", stroke_width=11, stroke_linecap="round") + line(cx, cy, x, y, stroke=fg, stroke_width=3, stroke_linecap="round") +
                      circ(x, y, 6, fg, stroke="none"))
        return parts + circ(cx, cy, 10, fg, stroke="none")
    if tier == "core":
        green = t["status-success-text"]
        c = 2 * math.pi * 44
        glow = "".join(circ(cx, cy, r, green, stroke="none", fill_opacity=op) for r, op in ((34, ".07"), (24, ".14"), (15, ".32")))
        ring = (circ(cx, cy, 44, "none", stroke=fg, stroke_opacity=".25", stroke_width=4) +
                el("circle", cx=n(cx), cy=n(cy), r="44", fill="none", stroke=green, stroke_width="4", stroke_linecap="round",
                   stroke_dasharray=f"{n(round(c * .62, 1))} {n(round(c, 1))}", transform=f"rotate(-90 {cx} {cy})"))
        return glow + ring + circ(cx, cy, 8, green, stroke="none")
    # omni: an engraved sphere
    edge = t["border-strong"]
    return (circ(cx, cy, 40, t["vcard-core-bg"], stroke=fg, stroke_opacity=".8", stroke_width=1.5) +
            el("ellipse", cx=n(cx), cy=n(cy), rx="40", ry="13", fill="none", stroke=fg, stroke_opacity=".4", stroke_width="1.5") +
            el("ellipse", cx=n(cx), cy=n(cy), rx="15", ry="40", fill="none", stroke=fg, stroke_opacity=".4", stroke_width="1.5") +
            el("ellipse", cx=n(cx), cy=n(cy), rx="30", ry="40", fill="none", stroke=fg, stroke_opacity=".25", stroke_width="1.5") +
            circ(cx - 14, cy - 18, 4.5, fg, stroke="none", fill_opacity=".55") + rr(3, 3, W - 6, H - 6, 13, "none", stroke=edge, stroke_width=2))


def face_group(tier, with_emblem=True):
    """The card face as a <g> in a 340 x 214 box. Colours may include the dark-theme glow tokens, so it is wrapped in markers."""
    t = _tok()
    bg, fg = t[f"vcard-{tier}-bg"], t[f"on-vcard-{tier}"]
    body = rr(0, 0, W, H, 16, bg, stroke="none") + rr(1, 1, W - 2, H - 2, 15, "none", stroke=fg, stroke_opacity=".25", stroke_width=1)
    if with_emblem:
        mark, _ = figures.brand_asset("emblem", "light", 24, 22, 38, "vcard-face")
        body += f'<g color="{fg}">{mark}</g>'
    body += "".join(path(f"M{n(284 + r * .55)} {n(36 - r * .83)}A{n(r)} {n(r)} 0 0 1 {n(284 + r * .55)} {n(36 + r * .83)}", stroke=fg, stroke_width=2.5, stroke_linecap="round", fill="none") for r in (7, 13, 19))
    body += _centrepiece(tier, fg, t)
    if tier != "omni":      # the front never shows a number; these dots only stand for the issuer-hosted number
        body += "".join(circ(24 + g * 54 + k * 11, 150, 2.4, fg, stroke="none", fill_opacity=".8") for g in range(4) for k in range(4))
    body += el("text", esc(TIER_TEXT[tier]), x="24", y="192", fill=fg, font_size="12", font_weight="600", letter_spacing="0.04em",
               font_family=_design.SRC["fonts"]["heading"].replace('"', "'"), stroke="none")
    return f'{START}<g>{body}</g>{END}'


def card_face(tier):
    return frame(f"vcard-{tier}", ALT[tier], face_group(tier), W, H)


def _headline(feat):
    if feat.get("branch_cards"):
        return "Branch cards, physical companion"
    if feat.get("approvals"):
        return "Approvals, time and shift locks"
    if feat.get("team_cards"):
        return "Team and supplier cards"
    return "Single-use supplier card"


def tier_ladder(theme):
    """The four card tiers side by side, with limits and prices read from services/billing.py (placeholders)."""
    p = Palette(theme, "vcard")
    fam = billing.FAMILIES["lynkvcard"]
    feats = billing.FEATURES["lynkvcard"]
    Wd, Hd = 800, 372
    body = [rr(0, 0, Wd, Hd, 0, p.base, stroke="none"), text(24, 34, "LynkVCard by tier", p, 20, 700, family="heading"),
            text(24, 56, "Card colour and design grow with the tier: a dot, a hub, a core, a sphere.", p, 13, fill=p.ink2)]
    for i, (tier_name, price) in enumerate(zip(fam[2], fam[3])):
        key = FAMILY_TIER[tier_name]
        f = feats[i]
        x = 24 + i * 190
        body.append(f'<g transform="translate({n(x)} 76) scale(0.5)">{face_group(key, with_emblem=False)}</g>')
        if i < 3:
            body.append(path(f"M{n(x + 174)} 123l8 6 -8 6z", p.ink2, stroke="none"))
        cards = "Unlimited cards" if f["active_cards"] is None else f"{f['active_cards']} card" + ("s" if f["active_cards"] != 1 else "")
        cap = f"Up to ${f['monthly_cap_usd']:,}" + ("+" if f.get("custom_limits") else "") + " a month"
        users = "Unlimited users" if f["users"] is None else f"{f['users']} user" + ("s" if f["users"] != 1 else "")
        body += [text(x, 214, tier_name.capitalize(), p, 16, 700, family="heading"),
                 text(x, 234, f"${price:g} a month", p, 14, 600, fill=p.accent_ink),
                 text(x, 258, cards, p, 13), text(x, 276, cap, p, 12, fill=p.ink2), text(x, 294, users, p, 12, fill=p.ink2),
                 text(x, 316, _headline(f), p, 12, 500)]
    body.append(text(24, Hd - 10, "Prices and limits are placeholders until market-tested (services/billing.py). Cards come from a licensed issuer; LynkOmni never holds funds.", p, 11, fill=p.ink2))
    alt = ("Diagram of the four LynkVCard tiers from left to right: Free with a slate EDGE card, Plus with a silver HUB card, Pro with a black CORE card "
           "and Max with an obsidian OMNI card, each with its price, number of cards, monthly spend limit, users and main feature.")
    return frame("diagram-vcard-tiers", alt, "".join(body), Wd, Hd)
