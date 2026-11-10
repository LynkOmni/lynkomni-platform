"""LynkVCard faces, one per tier, and the tier ladder diagram (NEW UPDATE 1, owner approved 10 November 2026).

Each tier has its own colour, finish and metal, and everything rises with the tier: Free = EDGE (Aurora Teal, aurora waves, a
point of light, silver chip), Plus = HUB (Royal Sapphire, a fine guilloche, a silver hub with three nodes, silver chip), Pro = CORE
(Imperial Amethyst, guilloche and a holographic band, a glowing core in its spend gauge, gold chip), Max = OMNI (Black Gold, gold
pinstripes and a gold foil edge, a gold globe with its orbit, gold chip, every word in gold). Colours are the vcard-* tokens.

Rules for these pictures (also in CLAUDE.md): a face never shows a card number, a card holder name, a bank name, a contactless
symbol or a payment network mark (the licensed issuer adds the network mark and prints the last four digits itself, and card details
are shown only in the issuer's secure display); the only words are the fixed tier line on the front and the tier word on the back;
the full logo (one artwork) comes from the brand module (surface vcard-face, one colour). Prices and limits in the ladder are read
from services/billing.py and are placeholders until market-tested."""
import math
from .kit import rr, circ, line, path, el, text, frame, n, esc, Palette, _design
from . import figures
from services import billing

TIERS = ("edge", "hub", "core", "omni")
FAMILY_TIER = {"free": "edge", "plus": "hub", "pro": "core", "max": "omni"}     # billing tier -> card
# The only words allowed on a card (owner approved): the tier line on the front and the tier word on the back. The check fails on any other text.
TIER_TEXT = {"edge": "EDGE // FIRST LIGHT", "hub": "HUB // CENTER POINT", "core": "CORE // DEEP SYSTEM", "omni": "OMNI // OWN ALL COMMERCE"}
BACK_TEXT = {t: t.upper() for t in TIERS}
# MASTER UPDATE 61 (owner, 10 November 2026): the same four faces serve three card groups, and SAMPLE faces (outside a person's
# own card: the store, marketing, "Get a card", design reviews) show placeholders that can never work as a real card
# (services/card_groups.py SAMPLE; the check digit fails). A person's real card is never drawn with its details: the app shows the
# plain face and the issuer prints the last four in its own secure display.
from services import card_groups as _cg     # noqa: E402
GROUPS = _cg.GROUPS
GROUP_TEXT = dict(_cg.CARD_WORD)            # the group word on the card, just above the network space
SAMPLE_TEXT = {"number": _cg.SAMPLE["number"], "valid": "VALID THRU", "expiry": _cg.SAMPLE["expiry"], "holder": _cg.SAMPLE["holder"],
               "code": _cg.SAMPLE["code"], "sample": _cg.SAMPLE["sample_word"]}
ALLOWED_TEXT = set(TIER_TEXT.values()) | set(BACK_TEXT.values()) | set(GROUP_TEXT.values()) | set(SAMPLE_TEXT.values())
# The fixed layout (x, y, width, height in the 340 x 214 card): spaces kept empty for what only the licensed issuer adds.
ZONES = {"contactless": (288, 14, 38, 40), "network": (262, 166, 60, 36)}
NAMES = {"edge": "Aurora Teal", "hub": "Royal Sapphire", "core": "Imperial Amethyst", "omni": "Black Gold"}
ALT_BACK = {
    "edge": "Back of the Aurora Teal EDGE LynkVCard: a dark stripe, a calm panel where the issuer shows the card details, the point of light as a faint watermark, the LynkOmni logo and the word EDGE. No number is drawn.",
    "hub": "Back of the Royal Sapphire HUB LynkVCard: a dark stripe, a calm panel where the issuer shows the card details, the hub as a faint watermark, the LynkOmni logo and the word HUB. No number is drawn.",
    "core": "Back of the Imperial Amethyst CORE LynkVCard: a dark stripe, a calm panel where the issuer shows the card details, the core as a faint watermark, the LynkOmni logo and the word CORE. No number is drawn.",
    "omni": "Back of the Black Gold OMNI LynkVCard: a dark stripe, a calm panel where the issuer shows the card details, the globe as a faint gold watermark, the LynkOmni logo and the word OMNI in gold. No number or bank name is drawn.",
}
ALT_EXTRA = {
    "core-near-limit": "The Imperial Amethyst CORE LynkVCard near its spend limit: an amber gauge almost full with a triangle marker and a diamond centre instead of a dot, so the warning does not rely on colour.",
    "omni-physical": "The physical companion for the OMNI LynkVCard: a full metal Black Gold card with a gold chip, a gold globe and orbit, a gold foil edge, no number on the front and the line OMNI // OWN ALL COMMERCE.",
}
ALT = {
    "edge": "Aurora Teal LynkVCard for the Free tier: deep teal rising to lagoon green with soft aurora waves, a silver chip, one point of mint light, the LynkOmni logo and the line EDGE // FIRST LIGHT. No number is drawn.",
    "hub": "Royal Sapphire LynkVCard for the Plus tier: midnight to royal blue with a fine guilloche pattern, a silver chip, a silver hub with three nodes, the LynkOmni logo and the line HUB // CENTER POINT. No number is drawn.",
    "core": "Imperial Amethyst LynkVCard for the Pro tier: deep violet rising to brand violet with guilloche and a holographic band, a gold chip, a glowing magenta core inside its spend gauge, the LynkOmni logo and the line CORE // DEEP SYSTEM. No number is drawn.",
    "omni": "Black Gold LynkVCard for the Max tier: pure black with gold pinstripes and a gold foil edge, a gold chip, a gold globe with an orbit, the LynkOmni logo and the line OMNI // OWN ALL COMMERCE in gold. No number is drawn.",
}
W, H = 340, 214
START, END = "<!--card:start-->", "<!--card:end-->"   # colours between these markers may use the dark-theme glow tokens


def _tok():
    return _design.resolved("dark")


def _pt(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _defs(tier, t, uid):
    """Gradients for one card (ids made unique per drawing, because the ladder draws four cards in one picture)."""
    g = f"g{uid}"
    stops = lambda c: "".join(f'<stop offset="{o}" stop-color="{v}"/>' for o, v in c)
    out = (f'<linearGradient id="{g}bg" x1="0" y1="1" x2="1" y2="0">' + stops((("0", t[f"vcard-{tier}-deep"]), (".55", t[f"vcard-{tier}-bg"]), ("1", t[f"vcard-{tier}-light"]))) + "</linearGradient>" +
           f'<radialGradient id="{g}glow"><stop offset="0" stop-color="{t[f"vcard-{tier}-accent"]}" stop-opacity=".55"/><stop offset="1" stop-color="{t[f"vcard-{tier}-accent"]}" stop-opacity="0"/></radialGradient>' +
           f'<linearGradient id="{g}gold" x1="0" y1="0" x2="1" y2="1">' + stops((("0", t["vcard-gold-light"]), (".4", t["vcard-omni-accent"]), (".7", t["vcard-gold-dark"]), ("1", t["vcard-gold-light"]))) + "</linearGradient>" +
           f'<linearGradient id="{g}silver" x1="0" y1="0" x2="1" y2="1">' + stops((("0", t["vcard-silver-light"]), (".5", t["vcard-silver-dark"]), ("1", t["vcard-silver-light"]))) + "</linearGradient>" +
           f'<linearGradient id="{g}sheen" x1="0" y1="0" x2="1" y2=".4"><stop offset=".25" stop-color="{t["vcard-silver-light"]}" stop-opacity="0"/><stop offset=".45" stop-color="{t["vcard-silver-light"]}" stop-opacity=".1"/><stop offset=".7" stop-color="{t["vcard-silver-light"]}" stop-opacity="0"/></linearGradient>' +
           f'<linearGradient id="{g}holo" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["vcard-edge-accent"]}" stop-opacity="0"/><stop offset=".3" stop-color="{t["vcard-edge-accent"]}" stop-opacity=".18"/><stop offset=".5" stop-color="{t["vcard-core-accent"]}" stop-opacity=".22"/><stop offset=".7" stop-color="{t["vcard-hub-accent"]}" stop-opacity=".18"/><stop offset="1" stop-color="{t["vcard-hub-accent"]}" stop-opacity="0"/></linearGradient>' +
           f'<clipPath id="{g}clip"><rect width="{W}" height="{H}" rx="14"/></clipPath>')
    return f"<defs>{out}</defs>", g


def _finish(tier, t, g, detail=True):
    """The finish rises with the tier: aurora waves, then guilloche, then a holographic band, then gold pinstripes."""
    out = ""
    acc = t[f"vcard-{tier}-accent"]
    if tier == "edge":
        for i, (dy, op) in enumerate(((0, ".2"), (16, ".12"), (32, ".08"))):
            out += path(f"M-16 {n(171 - dy)}C80 {n(119 - dy)} 168 {n(207 - dy)} 356 {n(99 - dy)}", stroke=acc, stroke_opacity=op, stroke_width=7 - i * 2, fill="none")
    if tier in ("hub", "core", "omni") and detail:
        op = {"hub": ".1", "core": ".07", "omni": ".07"}[tier]
        for k in range(14):
            r = 24 + k * 10
            out += el("ellipse", cx="262", cy="99", rx=n(r), ry=n(round(r * .62, 1)), fill="none", stroke=acc, stroke_opacity=op, stroke_width="0.6", transform=f"rotate({k * 4} 262 99)")
    if tier in ("core", "omni"):
        out += el("rect", x="-40", y="0", width="440", height=str(H), fill=f"url(#{g}holo)", opacity="1" if tier == "core" else ".45", transform="rotate(-24 170 107)")
    if tier == "omni" and detail:
        out += "".join(line(x, 0, x - 104, H, stroke=acc, stroke_opacity=".05", stroke_width=.6) for x in range(0, 460, 5))
    return out + el("rect", width=str(W), height=str(H), fill=f"url(#{g}sheen)")


def _motif(tier, t, g, cx=270, cy=82, k=1.0, op="1", near=False):
    """The tier motif: a point of light, a hub with three nodes, a core in its gauge, a globe with an orbit."""
    acc, fg = t[f"vcard-{tier}-accent"], t[f"on-vcard-{tier}"]
    if tier == "edge":
        body = circ(cx, cy, 48 * k, f"url(#{g}glow)", stroke="none") + circ(cx, cy, 12 * k, "none", stroke=acc, stroke_opacity=".55", stroke_width=1) + circ(cx, cy, 4 * k, fg, stroke="none")
    elif tier == "hub":
        rings = "".join(circ(cx, cy, r * k, "none", stroke=acc, stroke_opacity=o, stroke_width=1) for r, o in ((20, ".5"), (37, ".3"), (52, ".18")))
        spokes = ""
        for deg in (-90, 30, 150):
            x, y = _pt(cx, cy, 44 * k, deg)
            spokes += line(cx, cy, round(x, 1), round(y, 1), stroke=f"url(#{g}silver)", stroke_width=2.2 * k, stroke_linecap="round") + circ(round(x, 1), round(y, 1), 5.2 * k, f"url(#{g}silver)", stroke="none")
        body = circ(cx, cy, 56 * k, f"url(#{g}glow)", stroke="none", opacity=".6") + rings + spokes + circ(cx, cy, 8.8 * k, f"url(#{g}silver)", stroke="none") + circ(cx, cy, 3.6 * k, t["vcard-hub-bg"], stroke="none")
    elif tier == "core":
        color = t["status-warning-text"] if near else acc
        ticks = "".join(line(round(_pt(cx, cy, 46 * k, a)[0], 1), round(_pt(cx, cy, 46 * k, a)[1], 1), round(_pt(cx, cy, 50 * k, a)[0], 1), round(_pt(cx, cy, 50 * k, a)[1], 1),
                             stroke=t["vcard-core-accent"], stroke_opacity=".45", stroke_width=.7) for a in range(0, 360, 15))
        r, share = 40 * k, (.97 if near else .62)
        a0 = math.radians(135); a1 = math.radians(135 + 270 * share)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0); x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        big = 1 if 270 * share > 180 else 0
        arc = path(f"M{n(round(x0, 1))} {n(round(y0, 1))}A{n(r)} {n(r)} 0 {big} 1 {n(round(x1, 1))} {n(round(y1, 1))}", stroke=color, stroke_width=2.8 * k, stroke_linecap="round", fill="none")
        a2 = math.radians(135 + 270)
        track = path(f"M{n(round(x0, 1))} {n(round(y0, 1))}A{n(r)} {n(r)} 0 1 1 {n(round(cx + r * math.cos(a2), 1))} {n(round(cy + r * math.sin(a2), 1))}", stroke=fg, stroke_opacity=".14", stroke_width=2.8 * k, fill="none")
        if near:   # the shape changes too, never colour alone: a triangle marker at the end and a diamond centre
            marker = el("polygon", points=f"{n(round(x1, 1))},{n(round(y1 - 7, 1))} {n(round(x1 + 6, 1))},{n(round(y1 + 5, 1))} {n(round(x1 - 6, 1))},{n(round(y1 + 5, 1))}", fill=color)
            centre = el("polygon", points=f"{n(cx)},{n(cy - 9)} {n(cx + 9)},{n(cy)} {n(cx)},{n(cy + 9)} {n(cx - 9)},{n(cy)}", fill=color)
        else:
            marker, centre = "", circ(cx, cy, 10 * k, acc, stroke="none") + circ(cx, cy, 4.6 * k, fg, stroke="none")
        body = circ(cx, cy, 68 * k, f"url(#{g}glow)", stroke="none") + ticks + track + arc + circ(cx, cy, 19 * k, "none", stroke=t["vcard-core-accent"], stroke_opacity=".4", stroke_width=.7) + marker + centre
    else:
        R = 45 * k
        mer = "".join(el("ellipse", cx=n(cx), cy=n(cy), rx=n(round(R * abs(math.cos(math.radians(a))), 1)), ry=n(round(R, 1)), fill="none", stroke=f"url(#{g}gold)", stroke_opacity=".55", stroke_width=".5") for a in (0, 30, 60, 78))
        lat = "".join(el("ellipse", cx=n(cx), cy=n(round(cy + R * math.sin(math.radians(b)), 1)), rx=n(round(R * math.cos(math.radians(b)), 1)), ry=n(round(R * math.cos(math.radians(b)) * .18, 1)),
                         fill="none", stroke=f"url(#{g}gold)", stroke_opacity=".45", stroke_width=".45") for b in (-45, -20, 0, 20, 45))
        ox, oy = cx + 73 * k, cy
        orbit = (f'<g transform="rotate(-18 {n(cx)} {n(cy)})">' + el("ellipse", cx=n(cx), cy=n(cy), rx=n(round(73 * k, 1)), ry=n(round(18 * k, 1)), fill="none", stroke=f"url(#{g}gold)", stroke_width=".9") +
                 circ(round(ox, 1), oy, 8 * k, t["vcard-omni-accent"], stroke="none", fill_opacity=".25") + circ(round(ox, 1), oy, 2.8 * k, t["vcard-gold-light"], stroke="none") + "</g>")
        body = (circ(cx, cy, 66 * k, f"url(#{g}glow)", stroke="none", opacity=".45") + circ(cx, cy, R, t["vcard-omni-deep"], stroke="none") + mer + lat +
                circ(cx, cy, R, "none", stroke=f"url(#{g}gold)", stroke_width=.8) + orbit)
    return f'<g opacity="{op}">{body}</g>'


def _chip(x, y, metal, g, t):
    f = f"url(#{g}{metal})"
    seam = t["vcard-stripe"]
    return (rr(x, y, 37, 28, 5, f, stroke="none") + line(x, y + 9.5, x + 37, y + 9.5, stroke=seam, stroke_opacity=".25", stroke_width=.6) +
            line(x, y + 18.5, x + 37, y + 18.5, stroke=seam, stroke_opacity=".25", stroke_width=.6) + line(x + 13.5, y, x + 13.5, y + 28, stroke=seam, stroke_opacity=".25", stroke_width=.6) +
            line(x + 23.5, y, x + 23.5, y + 28, stroke=seam, stroke_opacity=".25", stroke_width=.6) + rr(x + 13.5, y + 9.5, 10, 9, 2, f, stroke=seam, stroke_opacity=".25", stroke_width=.6))


def _edge(tier, t, g):
    if tier == "omni":
        return rr(1, 1, W - 2, H - 2, 13, "none", stroke=f"url(#{g}gold)", stroke_width=1.6)
    return rr(.75, .75, W - 1.5, H - 1.5, 13.5, "none", stroke=t[f"vcard-{tier}-accent"], stroke_opacity=".45" if tier != "edge" else ".3", stroke_width=1)


def _ink(tier, g, t):
    return f"url(#{g}gold)" if tier == "omni" else t[f"on-vcard-{tier}"]


def face_group(tier, with_logo=True, near=False, uid=None, detail=True):
    """The card face as a <g> in a 340 x 214 box. Colours are card tokens, so it is wrapped in card markers."""
    t = _tok()
    defs, g = _defs(tier, t, uid or f"{tier}{'n' if near else ''}{'' if with_logo else 'l'}")
    fg = t[f"on-vcard-{tier}"]
    inner = el("rect", width=str(W), height=str(H), fill=f"url(#{g}bg)") + _finish(tier, t, g, detail) + (_motif(tier, t, g, cx=256, k=.92) if tier == "omni" else _motif(tier, t, g, near=near))
    inner += _chip(25, 67, "gold" if tier in ("core", "omni") else "silver", g, t)
    if with_logo:
        mark, _ = figures.brand_asset("logo", "light", 24, 20, 110, "vcard-face")
        inner += f'<g color="{fg}">{mark}</g>'
    accent_line = t[f"vcard-{tier}-accent"] if tier in ("edge", "hub", "core") else fg
    inner += el("text", esc(TIER_TEXT[tier]), x="25", y="192", fill=_ink(tier, g, t) if tier == "omni" else accent_line, font_size="11", font_weight="800", letter_spacing="0.12em",
                font_family=_design.SRC["fonts"]["heading"].replace('"', "'"), stroke="none")
    body = defs + f'<g clip-path="url(#{g}clip)">{inner}</g>' + _edge(tier, t, g)
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
            text(24, 56, "Colour, finish and metal rise with the tier: teal, sapphire, amethyst, black and gold.", p, 13, fill=p.ink2)]
    for i, (tier_name, price) in enumerate(zip(fam[2], fam[3])):
        key = FAMILY_TIER[tier_name]
        f = feats[i]
        x = 24 + i * 190
        body.append(f'<g transform="translate({n(x)} 76) scale(0.5)">{face_group(key, with_logo=False, uid=key + "l", detail=False)}</g>')
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
    alt = ("Diagram of the four LynkVCard tiers from left to right: Free with an Aurora Teal EDGE card, Plus with a Royal Sapphire HUB card, Pro with an Imperial Amethyst CORE card "
           "and Max with a Black Gold OMNI card, each with its price, number of cards, monthly spend limit, users and main feature.")
    return frame("diagram-vcard-tiers", alt, "".join(body), Wd, Hd)


def back_group(tier, uid=None):
    """Back of a card: a dark stripe, a calm panel where the issuer shows the card details (hosted by the issuer, never stored
    here), the tier motif as a faint watermark, the logo and the tier word."""
    t = _tok()
    defs, g = _defs(tier, t, uid or f"{tier}b")
    fg = t[f"on-vcard-{tier}"]
    inner = el("rect", width=str(W), height=str(H), fill=f"url(#{g}bg)") + _finish(tier, t, g) + _motif(tier, t, g, cx=280, cy=130, k=1.5, op=".16")
    inner += rr(0, 22, W, 36, 0, t["vcard-stripe"], stroke="none") + el("rect", y="22", width=str(W), height="36", fill=f"url(#{g}sheen)")
    inner += rr(22, 74, 206, 26, 4, t["vcard-panel"], stroke="none", fill_opacity=".92")
    mark, _ = figures.brand_asset("logo", "light", 22, 166, 90, "vcard-face")
    inner += f'<g color="{fg}">{mark}</g>'
    inner += el("text", esc(BACK_TEXT[tier]), x="318", y="194", text_anchor="end", fill=_ink(tier, g, t) if tier == "omni" else t[f"vcard-{tier}-accent"], font_size="10", font_weight="800",
                letter_spacing="0.2em", font_family=_design.SRC["fonts"]["heading"].replace('"', "'"), stroke="none")
    body = defs + f'<g clip-path="url(#{g}clip)">{inner}</g>' + _edge(tier, t, g)
    return f"{START}<g>{body}</g>{END}"


def card_back(tier):
    return frame(f"vcard-{tier}-back", ALT_BACK[tier], back_group(tier), W, H)


def near_limit():
    return frame("vcard-core-near-limit", ALT_EXTRA["core-near-limit"], face_group("core", near=True), W, H)


def physical_group():
    """Physical companion for OMNI (on demand, full metal): the same face; the chip is real and the edge is gold foil. No number."""
    return face_group("omni", uid="omnip")


def physical():
    return frame("vcard-omni-physical", ALT_EXTRA["omni-physical"], physical_group(), W, H)


# ---------------------------------------------------------------- the twelve sample cards (MASTER UPDATE 61)
def _txt(words, x, y, size, fill, weight="700", anchor="start", spacing="0.08em", family="mono", opacity=None):
    fam = _design.SRC["fonts"][family].replace('"', "'")
    extra = {"fill_opacity": opacity} if opacity else {}
    return el("text", esc(words), x=n(x), y=n(y), fill=fill, font_size=n(size), font_weight=weight, letter_spacing=spacing, text_anchor=anchor, font_family=fam, stroke="none", **extra)


def sample_face(tier, group):
    """A sample front in the fixed layout: logo top left, the contactless space top right left empty, chip, the sample number in the
    middle, VALID THRU and the name under it, the tier line bottom left, and bottom right an empty outline where the issuer adds
    the network mark, with the group word just above it. A small SAMPLE word says it is not a real card."""
    t = _tok()
    defs, g = _defs(tier, t, f"{tier}{group[0]}s")
    fg = t[f"on-vcard-{tier}"]
    ink = _ink(tier, g, t) if tier == "omni" else fg
    # the motif sits a little smaller and higher than on the plain face, clear of the number and of the issuer's spaces
    inner = el("rect", width=str(W), height=str(H), fill=f"url(#{g}bg)") + _finish(tier, t, g) + _motif(tier, t, g, cx=250, cy=74, k=.75)
    inner += _chip(25, 62, "gold" if tier in ("core", "omni") else "silver", g, t)
    mark, _ = figures.brand_asset("logo", "light", 24, 20, 110, "vcard-face")
    inner += f'<g color="{fg}">{mark}</g>'
    inner += _txt(SAMPLE_TEXT["sample"], 200, 30, 8, ink, "800", "middle", "0.3em", "body", ".85")
    inner += _txt(SAMPLE_TEXT["number"], 25, 124, 17, ink, "700", spacing="0.06em")
    inner += _txt(SAMPLE_TEXT["valid"], 150, 143, 6, ink, "700", spacing="0.12em", family="body", opacity=".85")
    inner += _txt(SAMPLE_TEXT["expiry"], 150, 156, 11, ink, "700")
    inner += _txt(SAMPLE_TEXT["holder"], 25, 166, 11, ink, "700", spacing="0.1em", family="body")
    accent_line = t[f"vcard-{tier}-accent"] if tier in ("edge", "hub", "core") else fg
    inner += el("text", esc(TIER_TEXT[tier]), x="25", y="192", fill=ink if tier == "omni" else accent_line, font_size="11", font_weight="800", letter_spacing="0.12em",
                font_family=_design.SRC["fonts"]["heading"].replace('"', "'"), stroke="none")
    zx, zy, zw, zh = ZONES["network"]
    inner += _txt(GROUP_TEXT[group], zx + zw, zy - 6, 9, ink, "800", "end", "0.16em", "heading")
    inner += rr(zx, zy, zw, zh, 5, "none", stroke=fg, stroke_opacity=".55", stroke_width=1, stroke_dasharray="3 3")   # empty: the issuer's network mark goes here
    body = defs + f'<g clip-path="url(#{g}clip)">{inner}</g>' + _edge(tier, t, g)
    return frame(f"vcard-{tier}-{group}", sample_alt(tier, group), f"{START}<g>{body}</g>{END}", W, H)


def sample_back(tier, group):
    """A sample back: the calm back with the placeholder security code 000 in the issuer's panel and the SAMPLE word."""
    t = _tok()
    defs, g = _defs(tier, t, f"{tier}{group[0]}sb")
    fg = t[f"on-vcard-{tier}"]
    inner = el("rect", width=str(W), height=str(H), fill=f"url(#{g}bg)") + _finish(tier, t, g) + _motif(tier, t, g, cx=280, cy=130, k=1.5, op=".16")
    inner += rr(0, 22, W, 36, 0, t["vcard-stripe"], stroke="none") + el("rect", y="22", width=str(W), height="36", fill=f"url(#{g}sheen)")
    inner += rr(22, 74, 206, 26, 4, t["vcard-panel"], stroke="none")
    inner += _txt(SAMPLE_TEXT["code"], 220, 92, 11, t["vcard-stripe"], "700", "end")
    mark, _ = figures.brand_asset("logo", "light", 22, 166, 90, "vcard-face")
    inner += f'<g color="{fg}">{mark}</g>'
    inner += _txt(SAMPLE_TEXT["sample"], 170, 132, 8, _ink(tier, g, t) if tier == "omni" else fg, "800", "middle", "0.3em", "body", ".85")
    inner += el("text", esc(BACK_TEXT[tier]), x="318", y="194", text_anchor="end", fill=_ink(tier, g, t) if tier == "omni" else t[f"vcard-{tier}-accent"], font_size="10", font_weight="800",
                letter_spacing="0.2em", font_family=_design.SRC["fonts"]["heading"].replace('"', "'"), stroke="none")
    body = defs + f'<g clip-path="url(#{g}clip)">{inner}</g>' + _edge(tier, t, g)
    return frame(f"vcard-{tier}-{group}-back", sample_alt(tier, group, back=True), f"{START}<g>{body}</g>{END}", W, H)


TIER_WORD = {"edge": "Free", "hub": "Plus", "core": "Pro", "omni": "Max"}


def sample_alt(tier, group, back=False):
    name = f"{_cg.NAMES[group]} {TIER_WORD[tier]}"
    if back:
        return (f"Back of a sample {name} card ({NAMES[tier]}, {tier.upper()}, {group}): a dark stripe, the issuer's panel with the sample "
                f"security code 000, the word SAMPLE, the LynkOmni logo and the word {tier.upper()}. Not a real card.")
    return (f"Sample {name} card ({NAMES[tier]}, {tier.upper()}, {group}): the LynkOmni logo top left, the chip, the sample number "
            f"1234 5678 9012 3456, VALID THRU MM/YY, CARD HOLDER, the line {TIER_TEXT[tier]}, the word {GROUP_TEXT[group]} above an empty space "
            "where the issuer adds the network mark, and the word SAMPLE. Not a real card.")
