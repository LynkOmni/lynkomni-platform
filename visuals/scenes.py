"""Illustration scenes (320 x 240). One function per scene; each returns SVG markup using only the Palette.

A scene never contains words, faces or people. Each shows the one idea its purpose needs, in the same flat,
outlined style. Scenes are named in visuals/needs.v1.json; the generator calls them by name."""
import math
from .kit import (rr, circ, line, path, group, el, check, cross, sparkle, star, cloud, backdrop, pen, n)

SCENES = {}


def scene(name):
    def deco(fn):
        SCENES[name] = fn
        return fn
    return deco


def wrap(p, body, seed=0):
    return backdrop(p, seed) + group(body, **pen(p))


def coin(cx, cy, r, p, fill=None):
    return circ(cx, cy, r, fill or p.accent) + circ(cx, cy, r * .55, "none", stroke=p.on_accent if fill is None else p.ink, stroke_width=2)


def lock(cx, cy, s, p, fill=None):
    w, h = s, s * .8
    return (path(f"M{n(cx - w * .32)} {n(cy - h * .1)}v{n(-h * .3)}a{n(w * .32)} {n(w * .32)} 0 0 1 {n(w * .64)} 0v{n(h * .3)}") +
            rr(cx - w / 2, cy - h * .1, w, h * .75, 5, fill or p.surface) + circ(cx, cy + h * .22, s * .08, p.ink, stroke="none"))


def wifi_arcs(cx, cy, p, color=None):
    c = color or p.ink2
    return "".join(path(f"M{n(cx - r)} {n(cy - r * .6)}a{n(r * 1.2)} {n(r * 1.2)} 0 0 1 {n(2 * r)} 0", stroke=c, stroke_width=3) for r in (10, 20, 30)) + circ(cx, cy + 6, 3.5, c, stroke="none")


# ---------------------------------------------------------------- product scenes
@scene("pos")
def _pos(p):
    b = (rr(110, 62, 100, 52, 8, p.surface) + path("M126 80h44M126 94h28", stroke=p.ink2, stroke_width=2) + path("M184 80l8 8 14-14", stroke=p.accent_ink, stroke_width=3) +
         rr(90, 114, 140, 66, 10, p.accent_soft) + "".join(circ(112 + 24 * i, 138 + 22 * j, 5, p.surface, stroke_width=2) for i in range(5) for j in range(2) if (i, j) != (4, 1)) +
         rr(204, 150, 18, 18, 4, p.accent) +
         path("M244 96h40v82l-6.7-5-6.7 5-6.7-5-6.7 5-6.7-5-6.6 5z", p.surface) + path("M252 110h24M252 122h24M252 134h16", stroke=p.ink2, stroke_width=2) +
         coin(62, 164, 16, p))
    return wrap(p, b)


@scene("ledger")
def _ledger(p):
    b = (path("M64 92Q112 76 160 94V182Q112 166 64 182Z", p.surface) + path("M160 94Q208 76 256 92V182Q208 166 160 182Z", p.surface) +
         path("M80 112Q112 104 144 112M80 130Q112 122 144 130M80 148Q112 140 144 148", stroke=p.ink2, stroke_width=2) +
         path("M178 112l6 6 10-12M178 134l6 6 10-12M178 156l6 6 10-12", stroke=p.accent_ink, stroke_width=3) +
         path("M204 112h34M204 134h34M204 156h26", stroke=p.ink2, stroke_width=2) +
         path("M222 86v36l10-8 10 8V84", p.accent) + coin(54, 170, 14, p))
    return wrap(p, b, 1)


@scene("invoice")
def _invoice(p):
    b = (rr(84, 44, 120, 152, 8, p.surface) + rr(84, 44, 120, 26, 8, p.accent_soft) + path("M100 88h56M100 104h88M100 120h88M100 136h64", stroke=p.ink2, stroke_width=2.5) +
         line(100, 158, 188, 158, stroke_width=2) + rr(148, 166, 40, 12, 3, p.accent) +
         path("M220 118l52-26-16 58-12-18z", p.surface) + path("M244 132l28-40", stroke_width=2) + path("M232 150q-10 16-30 20", stroke=p.accent_ink, stroke_width=3, stroke_dasharray="3 6"))
    return wrap(p, b, 1)


@scene("crm")
def _crm(p):
    nodes = ""
    for i, (y, f) in enumerate(((70, p.accent), (110, p.accent_soft), (150, p.accent_soft), (190, p.surface))):
        nodes += circ(112, y, 9, f) + rr(132, y - 14, 104 - 12 * i, 28, 8, p.surface) + path(f"M144 {n(y)}h{n(56 - 10 * i)}", stroke=p.ink2, stroke_width=2.5)
    b = line(112, 70, 112, 190, stroke=p.line, stroke_width=3) + nodes + star(254, 62, 16, p.accent, p) + sparkle(70, 96, 9, p.accent)
    return wrap(p, b)


@scene("ops")
def _ops(p):
    tiles = (rr(78, 92, 52, 60, 8, p.surface) + path("M88 108h32M88 120h32M88 132h20", stroke=p.ink2, stroke_width=2) +
             rr(134, 92, 52, 60, 8, p.accent_soft) + path("M146 106h28M146 118h28", stroke=p.ink2, stroke_width=2) + rr(160, 132, 16, 8, 2, p.accent) +
             rr(190, 92, 52, 60, 8, p.surface) + circ(204, 108, 4, p.accent) + circ(204, 122, 4, p.ink2, stroke="none") + circ(204, 136, 4, p.ink2, stroke="none") +
             path("M214 108h18M214 122h14M214 136h18", stroke=p.ink2, stroke_width=2))
    b = rr(62, 74, 196, 98, 16, "none", stroke=p.accent_ink, stroke_width=3) + tiles + coin(160, 196, 14, p) + path("M160 172v10", stroke=p.accent_ink, stroke_width=3)
    return wrap(p, b, 1)


@scene("stock")
def _stock(p):
    def box(x, y, w, h, f):
        return rr(x, y, w, h, 6, f) + path(f"M{n(x + w / 2)} {n(y)}v{n(h * .38)}", stroke_width=3) + rr(x + w / 2 + 8, y + h * .5, w * .22, h * .18, 3, p.surface, stroke_width=2)
    b = box(62, 134, 92, 58, p.accent_soft) + box(166, 134, 92, 58, p.surface) + box(112, 72, 96, 60, p.accent_soft) + path("M262 60v34M250 82l12 12 12-12", stroke=p.accent_ink, stroke_width=3)
    return wrap(p, b)


@scene("rewards")
def _rewards(p):
    cells = ""
    for i in range(8):
        cx, cy = 112 + 32 * (i % 4), 118 + 38 * (i // 4)
        cells += (circ(cx, cy, 12, p.accent) + check(cx, cy + 1, 10, p.on_accent, 2.5)) if i < 5 else circ(cx, cy, 12, "none", stroke_dasharray="4 5", stroke=p.ink2, stroke_width=2)
    b = rr(76, 74, 168, 118, 14, p.surface) + rr(76, 74, 168, 22, 14, p.accent_soft) + cells + star(248, 62, 20, p.accent, p) + sparkle(64, 70, 10, p.accent)
    return wrap(p, b, 1)


@scene("dash")
def _dash(p):
    bars = "".join(rr(96 + 32 * i, 168 - h, 22, h, 4, p.accent if i == 4 else p.accent_soft) for i, h in enumerate((22, 36, 30, 54, 76)))
    b = (rr(66, 56, 188, 136, 12, p.surface) + "".join(circ(84 + 12 * i, 72, 3, p.ink2, stroke="none") for i in range(3)) + path("M80 168H240", stroke_width=2) + bars +
         path("M104 118l32-14 30 8 52-34", stroke=p.ink, stroke_width=2.5, stroke_dasharray="2 6") + path("M206 78h12v12", stroke=p.ink, stroke_width=2.5))
    return wrap(p, b)


@scene("grow")
def _grow(p):
    b = (path("M120 156h80l-8 36h-64z", p.accent_soft) + line(120, 156, 200, 156) + path("M160 156V104") +
         path("M160 126C132 128 120 108 126 90 150 90 164 104 160 126Z", p.accent) + path("M160 114C184 116 198 98 192 82 170 82 158 94 160 114Z", p.accent_soft) +
         path("M246 140V92M234 104l12-12 12 12", stroke=p.accent_ink, stroke_width=3.5) + coin(78, 120, 14, p) + sparkle(220, 60, 9, p.accent))
    return wrap(p, b, 1)


@scene("chat")
def _chat(p):
    b = (rr(58, 62, 148, 76, 16, p.surface) + path("M88 138l-6 24 28-24", p.surface) + "".join(circ(100 + 24 * i, 100, 5, p.ink2, stroke="none") for i in range(3)) +
         rr(124, 112, 140, 70, 16, p.accent_soft) + path("M236 182l8 20-28-20", p.accent_soft) + path("M144 134h84M144 152h56", stroke=p.ink2, stroke_width=2.5))
    return wrap(p, b)


@scene("mpay")
def _mpay(p):
    b = (rr(116, 40, 88, 160, 16, p.surface) + rr(126, 56, 68, 110, 6, p.accent_soft) + coin(160, 100, 20, p) + check(160, 102, 14, p.on_accent) +
         path("M144 140h32M148 152h24", stroke=p.ink2, stroke_width=2.5) + circ(160, 184, 5) +
         path("M222 96q14 24 0 48M238 84q24 36 0 72", stroke=p.accent_ink, stroke_width=3) + path("M98 96q-14 24 0 48M82 84q-24 36 0 72", stroke=p.accent_ink, stroke_width=3))
    return wrap(p, b, 1)


@scene("recover")
def _recover(p):
    b = (path("M134 108V92a26 26 0 0 1 52 0v16") + rr(112, 106, 96, 72, 10, p.surface) + circ(160, 134, 9, p.accent) + line(160, 143, 160, 158) +
         path("M236 100A82 82 0 0 1 218 170", stroke=p.accent_ink, stroke_width=3.5) + path("M206 164l13 7 6-14", stroke=p.accent_ink, stroke_width=3.5) +
         path("M84 140A82 82 0 0 1 102 70", stroke=p.accent_ink, stroke_width=3.5) + path("M114 76l-13-7-6 14", stroke=p.accent_ink, stroke_width=3.5))
    return wrap(p, b)


@scene("checkout")
def _checkout(p):
    b = (rr(92, 46, 128, 148, 8, p.surface) + path("M110 70h56M110 90h92M110 106h92M110 122h70", stroke=p.ink2, stroke_width=2.5) + line(110, 146, 202, 146, stroke_width=2) +
         path("M178 164h24", stroke_width=3.5) + circ(216, 172, 24, p.accent) + check(216, 174, 20, p.on_accent) + sparkle(256, 66, 10, p.accent))
    return wrap(p, b, 1)


@scene("assist")
def _assist(p):
    ring = el("circle", cx="160", cy="118", r="42", fill="none", stroke=p.accent, stroke_width="30", stroke_dasharray="33 33", transform="rotate(-20 160 118)")
    b = (ring + circ(160, 118, 57) + circ(160, 118, 27) + rr(206, 150, 64, 40, 12, p.surface) + path("M222 190l-4 14 18-14", p.surface) +
         "".join(circ(224 + 14 * i, 170, 3.5, p.ink2, stroke="none") for i in range(3)) + sparkle(76, 66, 11, p.accent))
    return wrap(p, b)


@scene("vcard")
def _vcard(p):
    wavy = path("M214 98q8 10 0 20M224 92q12 16 0 32", stroke=p.on_accent, stroke_width=2.5)
    b = group(rr(76, 64, 168, 106, 14, p.accent) + rr(96, 90, 30, 24, 5, p.surface, stroke_width=2.5) + wavy +
              path("M96 142h18M124 142h18M152 142h18M180 142h18", stroke=p.on_accent, stroke_width=4), transform="rotate(-7 160 118)") + \
        circ(236, 170, 26, p.surface) + lock(236, 170, 26, p, p.accent_soft)
    return wrap(p, b, 1)


@scene("dev")
def _dev(p):
    b = (rr(58, 58, 204, 134, 12, p.surface) + line(58, 86, 262, 86, stroke_width=2) + "".join(circ(76 + 14 * i, 72, 3.5, p.ink2, stroke="none") for i in range(3)) +
         path("M80 108l14 12-14 12", stroke=p.accent_ink, stroke_width=3.5) + rr(102, 150, 26, 7, 2, p.accent) +
         path("M172 106l-16 14 16 14M212 106l16 14-16 14M198 100l-12 40", stroke_width=3.5) + sparkle(258, 56, 9, p.accent))
    return wrap(p, b)


@scene("booking")
def _booking(p):
    cells = "".join(rr(94 + 30 * i, 106 + 28 * j, 18, 16, 3, p.ground, stroke_width=2) for i in range(5) for j in range(3) if (i, j) != (2, 1))
    b = (rr(72, 56, 176, 138, 12, p.surface) + path("M72 68a12 12 0 0 1 12-12h152a12 12 0 0 1 12 12v22H72z", p.accent) + path("M110 46v22M210 46v22", stroke_width=4) +
         cells + circ(163, 142, 15, p.accent) + check(163, 144, 14, p.on_accent) + circ(236, 176, 24, p.surface) + path("M236 162v14l9 6", stroke_width=3))
    return wrap(p, b, 1)


@scene("essential")
def _essential(p):
    b = (path("M98 96h124l10 98H88z", p.accent_soft) + path("M132 96V84a28 28 0 0 1 56 0v12") +
         path("M160 176c-22 0-28-18-24-36 20 0 30 12 24 36Z", p.accent) + path("M160 176c4-14 10-24 20-30", stroke_width=2.5) + circ(196, 120, 5, p.surface, stroke_width=2) + sparkle(256, 74, 10, p.accent))
    return wrap(p, b)


@scene("suite")
def _suite(p):
    cx, cy, rad = 160, 118, 76
    items = ""
    for i in range(9):
        a = -math.pi / 2 + i * 2 * math.pi / 9
        x, y = cx + rad * math.cos(a), cy + rad * math.sin(a) * .82
        items = line(cx, cy, x, y, stroke=p.line, stroke_width=2) + items + rr(x - 17, y - 17, 34, 34, 8, p.surface if i % 2 else p.accent_soft)
    b = items + circ(cx, cy, 24, p.accent) + circ(cx, cy, 9, p.on_accent, stroke="none")
    return wrap(p, b, 1)


# ---------------------------------------------------------------- state scenes
@scene("offline")
def _offline(p):
    b = (cloud(76, 150, 1.1, p.surface) + line(84, 70, 190, 168, stroke=p.ink2, stroke_width=3.5) +
         rr(212, 100, 56, 92, 10, p.surface) + rr(220, 112, 40, 58, 4, p.accent_soft) + check(240, 142, 16, p.accent_ink) + circ(240, 181, 3.5, p.ink, stroke="none"))
    return wrap(p, b)


@scene("error")
def _error(p):
    b = (rr(84, 58, 152, 124, 12, p.surface) + circ(160, 104, 28, p.bad_bg) + cross(160, 104, 20, p.bad, 4.5) + path("M118 152h84M134 168h52", stroke=p.ink2, stroke_width=2.5) + sparkle(256, 70, 9, p.accent))
    return wrap(p, b, 1)


@scene("not-found")
def _notfound(p):
    b = (rr(92, 50, 116, 146, 8, p.surface) + path("M110 76h60M110 94h80M110 112h48", stroke=p.ink2, stroke_width=2.5, stroke_dasharray="2 6") +
         circ(206, 146, 32, p.surface) + line(229, 169, 254, 194, stroke_width=5) + path("M196 138a10 10 0 1 1 14 9c-4 2-4 5-4 8", stroke=p.accent_ink, stroke_width=3.5) + circ(206, 168, 2.5, p.ink, stroke="none"))
    return wrap(p, b)


@scene("no-results")
def _noresults(p):
    rows = "".join(rr(84, 58 + 34 * i, 120, 24, 6, p.ground if i else p.accent_soft, stroke_dasharray="4 5" if i else None, stroke_width=2) for i in range(4))
    b = rows + circ(218, 140, 32, p.surface) + line(241, 163, 262, 186, stroke_width=5) + line(204, 140, 232, 140, stroke=p.accent_ink, stroke_width=3.5)
    return wrap(p, b, 1)


@scene("success")
def _success(p):
    conf = (rr(80, 62, 10, 10, 2, p.accent, stroke="none", transform="rotate(20 85 67)") + circ(246, 70, 5, p.warn_bg, stroke=p.warn, stroke_width=2) +
            rr(236, 160, 10, 10, 2, p.accent, stroke="none", transform="rotate(-18 241 165)") + circ(78, 160, 5, p.ok_bg, stroke=p.ok, stroke_width=2) + sparkle(258, 120, 9, p.accent) + sparkle(64, 112, 8, p.accent))
    b = conf + circ(160, 118, 56, p.ok_bg) + check(160, 122, 52, p.ok, 8)
    return wrap(p, b)


@scene("permission")
def _permission(p):
    b = (path("M160 48l62 22v50c0 40-28 62-62 76-34-14-62-36-62-76V70z", p.surface) + lock(160, 116, 46, p, p.accent_soft) + sparkle(256, 64, 9, p.accent))
    return wrap(p, b, 1)


@scene("maintenance")
def _maintenance(p):
    teeth = "".join(rr(150, 48, 20, 16, 3, p.accent_soft, transform=f"rotate({a} 160 108)") for a in range(0, 360, 45))
    b = teeth + circ(160, 108, 38, p.surface) + circ(160, 108, 14, p.accent) + rr(96, 170, 128, 14, 7, p.surface) + rr(96, 170, 76, 14, 7, p.accent)
    return wrap(p, b)


@scene("sync-pending")
def _syncpending(p):
    b = (cloud(104, 140, 1.15, p.surface) + path("M176 118V92M164 104l12-12 12 12", stroke=p.accent_ink, stroke_width=3.5) +
         "".join(rr(46, 128 + 20 * i, 52, 14, 4, p.accent_soft if i == 0 else p.surface, stroke_width=2) for i in range(3)) + circ(250, 168, 20, p.surface) + path("M250 156v12l8 5", stroke_width=3))
    return wrap(p, b, 1)


@scene("coming-soon")
def _region(p):
    b = (circ(150, 120, 58, p.surface) + el("ellipse", cx="150", cy="120", rx="24", ry="58", fill="none") + line(92, 120, 208, 120) + path("M100 92h100M100 148h100", stroke_width=2) +
         el("circle", cx="150", cy="120", r="72", fill="none", stroke=p.ink2, stroke_width="2", stroke_dasharray="3 8") +
         path("M214 74a16 16 0 0 1 16 16c0 14-16 32-16 32s-16-18-16-32a16 16 0 0 1 16-16z", p.accent) + circ(214, 90, 5, p.on_accent, stroke="none"))
    return wrap(p, b)


# ---------------------------------------------------------------- onboarding scenes
@scene("onboard-offline")
def _on1(p):
    b = (rr(112, 42, 96, 158, 16, p.surface) + rr(122, 58, 76, 112, 6, p.accent_soft) + circ(160, 100, 22, p.surface) + check(160, 102, 20, p.accent_ink) +
         path("M136 142h48M144 154h32", stroke=p.ink2, stroke_width=2.5) + circ(160, 184, 5) + wifi_arcs(250, 96, p) + line(228, 70, 276, 128, stroke=p.ink, stroke_width=3.5))
    return wrap(p, b)


@scene("onboard-chain")
def _on2(p):
    blocks = "".join(rr(40 + 80 * i, 92, 64, 56, 10, p.accent_soft if i % 2 == 0 else p.surface) + path(f"M{54 + 80 * i} 112h36M{54 + 80 * i} 126h24", stroke=p.ink2, stroke_width=2) for i in range(3))
    links = "".join(path(f"M{104 + 80 * i} 120h16", stroke=p.accent_ink, stroke_width=3.5) for i in range(2))
    b = blocks + links + circ(160, 56, 20, p.surface) + lock(160, 58, 20, p, p.accent_soft) + path("M80 92V76q0-20 40-20M240 92V76q0-20-40-20", stroke=p.line, stroke_width=2, stroke_dasharray="3 6") + sparkle(262, 184, 10, p.accent)
    return wrap(p, b, 1)


@scene("onboard-provider")
def _on3(p):
    b = (coin(70, 128, 22, p) + path("M104 128h30", stroke=p.ink2, stroke_width=3, stroke_dasharray="2 7") +
         path("M166 78l34 13v30c0 22-17 36-34 44-17-8-34-22-34-44V91z", p.surface) + check(166, 124, 22, p.accent_ink) +
         path("M208 128h22", stroke=p.ink2, stroke_width=3, stroke_dasharray="2 7") +
         path("M234 108l24-14 24 14z", p.accent_soft) + path("M240 112v44M258 112v44M276 112v44") + line(232, 160, 284, 160, stroke_width=3.5))
    return wrap(p, b)


@scene("onboard-growth")
def _on4(p):
    stripes = "".join(line(98 + 124 * i / 5, 84, 84 + 152 * i / 5, 116, stroke_width=2) for i in range(1, 5))
    b = (rr(92, 116, 136, 72, 6, p.surface) + path("M84 116l14-32h124l14 32z", p.accent_soft) + stripes + rr(142, 144, 36, 44, 4, p.accent_soft) + rr(100, 132, 32, 24, 3, p.surface, stroke_width=2) +
         path("M254 140V92M242 104l12-12 12 12", stroke=p.accent_ink, stroke_width=3.5) + coin(64, 150, 14, p) + sparkle(256, 60, 10, p.accent))
    return wrap(p, b, 1)
