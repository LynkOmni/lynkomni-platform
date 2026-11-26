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


@scene("motion")
def _motion(p):
    """LynkTrace (was LynkMotion's picture until the LOCATION UPDATE): a parcel moving along a dotted route between two pins, with a clock for the arrival window."""
    route = path("M70 170C110 170 110 100 160 100S220 70 252 70", stroke=p.ink2, stroke_width=3, stroke_dasharray="2 9", stroke_linecap="round")
    pin = lambda x, y, f: path(f"M{n(x)} {n(y)}c-12-14-18-22-18-31a18 18 0 0 1 36 0c0 9-6 17-18 31z", f) + circ(x, y - 31, 6, p.surface)
    box = rr(136, 82, 48, 40, 6, p.accent) + path("M136 96h48M160 82v14", stroke=p.on_accent, stroke_width=2.5)
    b = route + pin(70, 196, p.accent_soft) + pin(252, 96, p.accent) + box + circ(232, 168, 24, p.surface) + path("M232 154v14l10 6", stroke_width=3)
    return wrap(p, b, 1)


@scene("guard")
def _guard(p):
    """LynkGuard: a parked car inside a protected zone ring, with a padlock badge and a signal arc."""
    ring = el("ellipse", cx="150", cy="150", rx="112", ry="48", fill="none", stroke=p.accent, stroke_width="3", stroke_dasharray="10 8")
    car = (path("M88 150l14-30q4-8 13-8h70q9 0 13 8l14 30v22H88z", p.surface) + path("M106 124h78l9 22h-96z", p.accent_soft) +
           circ(112, 172, 11, p.ink, stroke="none") + circ(178, 172, 11, p.ink, stroke="none"))
    b = ring + car + circ(232, 90, 26, p.surface) + lock(232, 90, 26, p, p.accent_soft) + wifi_arcs(232, 52, p, p.accent_ink)
    return wrap(p, b)


@scene("motion_land")
def _motion_land(p):
    """LynkMotion Land: a delivery van on a road that curves to a map pin, with a small gauge for distance driven."""
    road = path("M40 188C110 188 120 132 190 132S262 96 286 92", stroke=p.ink2, stroke_width=3, stroke_dasharray="2 9", stroke_linecap="round")
    van = (rr(84, 124, 74, 44, 6, p.surface) + path("M158 136h22l14 16v16h-36z", p.accent_soft) + path("M164 142h12l8 10h-20z", p.surface, stroke_width=2) +
           circ(104, 170, 10, p.ink, stroke="none") + circ(176, 170, 10, p.ink, stroke="none") + rr(96, 134, 40, 14, 4, p.accent))
    pin = path("M262 104c-12-14-18-22-18-31a18 18 0 0 1 36 0c0 9-6 17-18 31z", p.accent) + circ(262, 73, 6, p.surface)
    gauge = circ(62, 82, 24, p.surface) + path("M46 90a17 17 0 0 1 32 0", stroke=p.ink2, stroke_width=3) + path("M62 90l9-10", stroke=p.accent_ink, stroke_width=3)
    return wrap(p, road + van + pin + gauge, 1)


@scene("motion_sea")
def _motion_sea(p):
    """LynkMotion Sea: a boat on waves heading to a map pin, with an anchor badge for mooring watch."""
    waves = "".join(path(f"M{40 + 0} {n(y)}q20-10 40 0t40 0t40 0t40 0t40 0t40 0", stroke=c, stroke_width=3) for y, c in ((182, p.accent_ink), (198, p.ink2)))
    hull = path("M96 150h112l-18 26h-78z", p.surface) + rr(126, 116, 50, 34, 6, p.accent_soft) + rr(136, 124, 12, 10, 2, p.surface, stroke_width=2) + rr(154, 124, 12, 10, 2, p.surface, stroke_width=2)
    mast = path("M151 116V90", stroke_width=3) + path("M151 92l18 8-18 6z", p.accent)
    pin = path("M258 116c-12-14-18-22-18-31a18 18 0 0 1 36 0c0 9-6 17-18 31z", p.accent) + circ(258, 85, 6, p.surface)
    anchor = (circ(62, 80, 24, p.surface) + circ(62, 68, 4, "none", stroke_width=2.5) + path("M62 72v22M52 82h20M50 88q12 12 24 0", stroke=p.accent_ink, stroke_width=2.5))
    return wrap(p, waves + hull + mast + pin + anchor, 2)


@scene("motion_air")
def _motion_air(p):
    """LynkMotion Air: a small aircraft on a dotted flight path and a drone below it, with a clock for the flight plan."""
    route = path("M40 176C100 150 150 96 280 70", stroke=p.ink2, stroke_width=3, stroke_dasharray="2 9", stroke_linecap="round")
    plane = path("M150 108l70-22 8 6-40 22 24 22-8 4-30-18-26 12-6-4 18-14z", p.accent) + path("M188 114l-34 16", stroke=p.on_accent, stroke_width=2)
    drone = (rr(84, 150, 36, 16, 5, p.surface) + path("M84 154l-16-8M120 154l16-8", stroke_width=3) +
             el("ellipse", cx="62", cy="144", rx="12", ry="4", fill=p.accent_soft, stroke=p.ink, stroke_width="2") +
             el("ellipse", cx="142", cy="144", rx="12", ry="4", fill=p.accent_soft, stroke=p.ink, stroke_width="2"))
    clock = circ(258, 166, 24, p.surface) + path("M258 152v14l10 6", stroke_width=3)
    return wrap(p, route + plane + drone + clock, 3)


@scene("sentry")
def _sentry(p):
    """LynkSentry: a warning beacon sending out alert rays, beside a bell and an incident file with a check."""
    beacon = (path("M120 150v-34a40 40 0 0 1 80 0v34", p.accent) + rr(108, 150, 104, 22, 6, p.surface) +
              path("M150 108a12 12 0 0 1 12-12", stroke=p.on_accent, stroke_width=3))
    rays = path("M160 44v18M104 62l12 12M216 62l-12 12M82 108h16M222 108h16", stroke=p.accent_ink, stroke_width=4, stroke_linecap="round")
    bell = circ(262, 160, 22, p.surface) + path("M252 168v-10a10 10 0 0 1 20 0v10zM249 168h26M258 172a4 4 0 0 0 8 0", stroke_width=2.5)
    file = rr(40, 132, 46, 56, 6, p.surface) + path("M50 148h26M50 160h18", stroke=p.ink2, stroke_width=2.5) + check(63, 176, 12, p.accent_ink)
    return wrap(p, beacon + rays + bell + file, 1)


@scene("cctv")
def _cctv(p):
    """LynkCCTV: a camera on a wall bracket with its view as a soft cone, a screen with a play button and a recording dot."""
    cone = path("M176 92L292 150V196L176 116z", p.accent_soft, stroke="none")
    cam = (path("M60 54v34h30", stroke_width=4) + path("M88 78l92-22 8 34-92 22z", p.surface) + path("M180 60l20-4 6 26-18 4z", p.accent) + circ(118, 84, 5, p.accent_ink, stroke="none"))
    screen = rr(54, 136, 92, 60, 8, p.surface) + path("M92 152v28l22-14z", p.accent) + circ(134, 148, 5, p.accent_ink, stroke="none")
    return wrap(p, cone + cam + screen, 2)


@scene("gate")
def _gate(p):
    """LynkGate: a barrier arm lifting at a lane, a car waiting, and a pass with a square code."""
    post = rr(70, 104, 22, 82, 5, p.surface) + rr(64, 182, 34, 10, 3, p.ink, stroke="none")
    arm = group(rr(86, 104, 150, 16, 6, p.surface) + "".join(path(f"M{n(110 + 30 * i)} 104l-10 16", stroke=p.accent, stroke_width=6) for i in range(5)), transform="rotate(-24 81 112)")
    car = (path("M150 176l10-20q3-6 10-6h52q7 0 10 6l10 20v16H150z", p.accent_soft) + circ(168, 192, 9, p.ink, stroke="none") + circ(222, 192, 9, p.ink, stroke="none"))
    ticket = rr(234, 60, 52, 60, 6, p.surface) + "".join(rr(246 + 10 * i, 72 + 10 * j, 7, 7, 1.5, p.ink if (i + j) % 2 == 0 else p.accent, stroke="none") for i in range(3) for j in range(3))
    return wrap(p, post + arm + car + ticket, 3)


@scene("attendance")
def _attendance(p):
    """LynkAttend: a door device with a PIN keypad and a fingerprint, a clock for the time in, and a check mark."""
    keys = "".join(rr(102 + 20 * i, 118 + 18 * j, 14, 12, 3, p.ground, stroke_width=2) for i in range(3) for j in range(3))
    prints = "".join(path(f"M{n(204 - r)} {n(126)}a{n(r)} {n(r * 1.1)} 0 0 1 {n(2 * r)} 0v{n(r * .5)}", stroke=p.accent_ink, stroke_width=2.5) for r in (6, 12, 18))
    b = (rr(88, 52, 144, 150, 14, p.surface) + rr(100, 66, 120, 40, 8, p.accent_soft) + path("M114 86h28M150 86h28M186 86h20", stroke=p.ink2, stroke_width=4, stroke_linecap="round") +
         keys + rr(180, 116, 46, 62, 10, p.accent_soft) + prints +
         circ(258, 74, 24, p.surface) + path("M258 60v14l10 6", stroke_width=3) + circ(66, 172, 18, p.accent) + check(66, 174, 16, p.on_accent))
    return wrap(p, b, 2)


@scene("queue")
def _queue(p):
    """LynkQueue: a ticket coming out of a kiosk, a calling screen with an arrow to a counter, and a short line of waiting markers."""
    ticket = path("M74 96h56v74l-7-5-7 5-7-5-7 5-7-5-7 5-7-5-7 5z", p.surface) + path("M84 112h36M84 126h24M84 140h30", stroke=p.ink2, stroke_width=3)
    kiosk = rr(66, 60, 72, 44, 8, p.accent_soft) + rr(80, 92, 44, 6, 3, p.ink, stroke="none")
    screen = rr(158, 54, 104, 66, 10, p.ink) + path("M174 76h34M174 96h22", stroke=p.on_accent, stroke_width=4, stroke_linecap="round") + path("M220 86h22l-8-8M242 86l-8 8", stroke=p.accent, stroke_width=3.5)
    line_up = "".join(rr(166 + 22 * i, 156, 14, 30, 7, p.accent if i == 0 else p.surface) for i in range(4))
    b = kiosk + ticket + screen + path("M210 120v18", stroke_width=3) + rr(150, 186, 120, 10, 4, p.surface) + line_up
    return wrap(p, b, 1)


@scene("survey")
def _survey(p):
    """LynkSurvey: a form with tick boxes and a star rating beside a small results chart and a sealed check badge."""
    boxes = "".join(rr(96, 92 + 26 * i, 14, 14, 3, p.accent if i != 1 else p.surface) + path(f"M118 {n(99 + 26 * i)}h44", stroke=p.ink2, stroke_width=2.5) for i in range(3))
    stars = "".join(star(104 + 18 * i, 186, 7, p.accent if i < 4 else p.surface, p) for i in range(5))
    bars = "".join(rr(206 + 16 * i, 170 - h, 10, h, 2, p.accent if i == 2 else p.accent_soft) for i, h in enumerate((40, 58, 82, 30)))
    b = (rr(80, 56, 104, 146, 10, p.surface) + rr(110, 46, 44, 18, 5, p.accent_soft) + boxes + stars + path("M196 172h76", stroke_width=2.5) + bars +
         circ(262, 60, 18, p.accent) + check(262, 62, 14, p.on_accent))
    return wrap(p, b, 2)


@scene("exchange")
def _exchange(p):
    """LynkExchange: two coins of different currencies joined by two curved arrows, with a small rate line between them."""
    b = (coin(96, 126, 34, p) + circ(224, 126, 34, p.surface) + circ(224, 126, 19, "none", stroke=p.ink2, stroke_width=2) +
         path("M124 92Q160 64 196 92", stroke=p.accent_ink, stroke_width=3.5) + path("M188 82l8 10-12 3", stroke=p.accent_ink, stroke_width=3.5) +
         path("M196 160Q160 188 124 160", stroke=p.ink2, stroke_width=3.5) + path("M132 170l-8-10 12-3", stroke=p.ink2, stroke_width=3.5) +
         path("M70 204h44l18-14 22 8 24-20 22 10h40", stroke=p.accent, stroke_width=3) + sparkle(266, 64, 9, p.accent))
    return wrap(p, b, 1)


@scene("bet")
def _bet(p):
    """LynkBet: a printed ticket with a QR square coming out of a counter printer, a check badge for a ticket that pays once and a
    small shield for safer betting. No words, odds or money shown."""
    qr = "".join(rr(150 + 9 * i, 98 + 9 * j, 7, 7, 1.5, p.ink, stroke="none") for i in range(4) for j in range(4) if (i * 3 + j * 5) % 4 != 1)
    b = (rr(86, 150, 148, 44, 10, p.accent_soft) + rr(106, 158, 108, 8, 4, p.ink2, stroke="none") +
         path("M124 54h72v108l-6-4.5-6 4.5-6-4.5-6 4.5-6-4.5-6 4.5-6-4.5-6 4.5-6-4.5-6 4.5-6-4.5z", p.surface) +
         path("M134 70h40M134 82h52", stroke=p.ink2, stroke_width=2.5) + rr(146, 94, 40, 40, 4, p.surface) + qr +
         circ(256, 78, 18, p.accent) + check(256, 80, 14, p.on_accent) +
         path("M60 102l18-8 18 8v18c0 14-8 22-18 26-10-4-18-12-18-26z", p.surface) + check(78, 120, 12, p.accent_ink))
    return wrap(p, b, 2)


@scene("vote")
def _vote(p):
    """LynkVote: a ballot box with a sealed ballot going in, a check mark on the ballot and a small lock for the sealed count."""
    b = (rr(92, 118, 136, 76, 10, p.surface) + rr(92, 118, 136, 18, 6, p.accent_soft) + rr(130, 122, 60, 6, 3, p.ink, stroke="none") +
         rr(136, 58, 48, 66, 6, p.surface) + check(160, 92, 18, p.accent_ink) + path("M146 110h28", stroke=p.ink2, stroke_width=2.5) +
         lock(160, 164, 30, p, p.accent_soft) + circ(262, 76, 18, p.accent) + check(262, 78, 14, p.on_accent))
    return wrap(p, b, 2)


@scene("hr")
def _hr(p):
    """LynkHR: an organisation chart of plain boxes joined by lines, beside a calendar page with one marked day for leave."""
    boxes = rr(118, 52, 52, 30, 7, p.accent) + "".join(rr(70 + 64 * i, 126, 46, 28, 7, p.surface) for i in range(3))
    links = path("M144 82v22M93 104h102M93 104v22M157 104v22M221 104v22", stroke_width=2.5)
    cal = (rr(226, 52, 62, 56, 8, p.surface) + rr(226, 52, 62, 16, 6, p.accent_soft) +
           "".join(rr(234 + 16 * i, 74 + 14 * j, 9, 8, 2, p.accent if (i, j) == (2, 1) else p.ground, stroke_width=1.5) for i in range(3) for j in range(2)))
    b = boxes + links + cal + path("M70 176h176", stroke=p.ink2, stroke_width=2.5) + path("M70 192h120", stroke=p.ink2, stroke_width=2.5) + circ(262, 186, 14, p.accent) + check(262, 188, 11, p.on_accent)
    return wrap(p, b, 1)


@scene("project")
def _project(p):
    """LynkProject: a board of three columns with task cards, one card moving across, and a progress bar underneath."""
    cols = "".join(rr(72 + 62 * i, 52, 54, 118, 8, p.accent_soft if i == 1 else p.surface) for i in range(3))
    cards = "".join(rr(78 + 62 * i, 64 + 26 * j, 42, 18, 4, p.ground, stroke_width=2) for i, k in ((0, 3), (1, 2), (2, 1)) for j in range(k))
    b = (cols + cards + rr(206, 98, 42, 18, 4, p.accent) + path("M196 107h-10", stroke=p.accent_ink, stroke_width=3) +
         rr(72, 184, 178, 12, 6, p.surface) + rr(72, 184, 118, 12, 6, p.accent) + circ(272, 68, 16, p.surface) + check(272, 70, 12, p.accent_ink))
    return wrap(p, b, 2)


@scene("school")
def _school(p):
    """LynkSchool: an open book on a desk with a graduation cap above it and a small timetable grid."""
    b = (path("M78 128Q118 112 160 128V188Q118 172 78 188Z", p.surface) + path("M160 128Q202 112 242 128V188Q202 172 160 188Z", p.surface) +
         path("M94 146Q122 138 146 146M94 162Q122 154 146 162M174 146Q198 138 226 146", stroke=p.ink2, stroke_width=2) +
         path("M160 54l58 22-58 22-58-22z", p.accent) + path("M128 88v20q32 16 64 0V88", p.accent_soft) + path("M218 76v26", stroke_width=3) + circ(218, 106, 5, p.accent, stroke="none") +
         "".join(rr(250 + 14 * i, 130 + 14 * j, 10, 10, 2, p.accent if (i + j) % 3 == 0 else p.surface, stroke_width=1.5) for i in range(2) for j in range(3)))
    return wrap(p, b, 1)


@scene("academy")
def _academy(p):
    """LynkAcademy: a lesson on a screen with a play mark and a progress bar, and a certificate with a ribbon seal beside it."""
    b = (rr(70, 64, 140, 96, 8, p.surface) + rr(80, 74, 120, 64, 4, p.accent_soft, stroke_width=1.5) + path("M132 92l22 14-22 14z", p.accent, stroke="none") +
         rr(80, 146, 120, 6, 3, p.ground, stroke_width=1) + rr(80, 146, 74, 6, 3, p.accent, stroke="none") + path("M118 160l-8 26h60l-8-26", p.surface) +
         rr(208, 96, 76, 96, 6, p.surface) + path("M220 116h52M220 130h52M220 144h34", stroke=p.ink2, stroke_width=2) +
         path("M256 170l-8 26 10-6 10 6-8-26", p.accent_soft) + circ(258, 168, 13, p.accent) + check(258, 170, 10, p.on_accent))
    return wrap(p, b, 1)


@scene("property")
def _property(p):
    """LynkProperty: a house with a door and windows, a key beside it and a small meter dial for readings."""
    b = (path("M84 112l66-50 66 50", p.accent_soft) + rr(94, 110, 112, 82, 4, p.surface) + rr(138, 146, 26, 46, 3, p.accent) +
         rr(106, 124, 22, 20, 3, p.ground, stroke_width=2) + rr(174, 124, 22, 20, 3, p.ground, stroke_width=2) +
         circ(246, 132, 16, p.surface) + circ(246, 132, 7, "none", stroke=p.ink2, stroke_width=2) + path("M246 148v38M246 170h10M246 182h7", stroke_width=3.5) +
         circ(262, 70, 18, p.surface) + path("M262 70l8-8", stroke=p.accent_ink, stroke_width=3) + path("M250 76h24", stroke=p.ink2, stroke_width=2))
    return wrap(p, b, 2)


@scene("files")
def _docs(p):
    """LynkFiles: a stack of documents, the top one with lines, a signature stroke and a round seal, and a pen beside it."""
    b = (rr(104, 66, 116, 136, 8, p.accent_soft) + rr(94, 56, 116, 136, 8, p.surface) + path("M112 82h80M112 98h80M112 114h56", stroke=p.ink2, stroke_width=2.5) +
         path("M112 166q10-16 20-2t20-4 18 2", stroke=p.accent_ink, stroke_width=3) + path("M112 178h80", stroke=p.ink2, stroke_width=1.5) +
         circ(182, 140, 15, p.accent) + check(182, 142, 12, p.on_accent) +
         path("M248 70l16 16-52 52-20 4 4-20z", p.surface) + path("M240 78l16 16", stroke_width=2.5))
    return wrap(p, b, 1)


@scene("jobs")
def _jobs(p):
    """LynkJobs: a briefcase with a check tag, a search glass over a list of openings, and a small star for a featured post."""
    b = (rr(70, 104, 124, 86, 10, p.surface) + path("M110 104V92a8 8 0 0 1 8-8h28a8 8 0 0 1 8 8v12", stroke_width=3) + line(70, 136, 194, 136, stroke_width=2.5) +
         rr(124, 128, 16, 16, 3, p.accent) + rr(208, 60, 72, 92, 8, p.surface) + path("M220 80h48M220 98h48M220 116h32", stroke=p.ink2, stroke_width=2.5) +
         circ(240, 152, 22, p.accent_soft) + path("M256 168l18 18", stroke_width=5, stroke_linecap="round") + star(84, 68, 10, p.accent, p) +
         circ(170, 76, 15, p.accent) + check(170, 78, 12, p.on_accent))
    return wrap(p, b, 2)


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


@scene("agent-point")
def _agent_point(p):
    """An agent point: a counter with the agent's cash on it and a phone that shows the partner's tick, joined by a dashed line
    to the licensed partner's building (the partner confirms each transaction; the cash and the float stay the agent's)."""
    notes = rr(72, 118, 46, 26, 4, p.accent_soft) + rr(78, 110, 46, 26, 4, p.surface) + circ(101, 123, 6, "none", stroke_width=2)
    b = (rr(56, 144, 136, 46, 6, p.surface) + line(56, 160, 192, 160, stroke_width=2) + notes +
         rr(140, 82, 36, 62, 7, p.surface) + rr(146, 92, 24, 36, 3, p.accent_soft, stroke="none") + check(158, 110, 14, p.accent_ink) +
         path("M184 108h40", stroke=p.ink2, stroke_width=3, stroke_dasharray="2 7") +
         path("M230 96l26-16 26 16z", p.accent_soft) + path("M238 100v44M256 100v44M274 100v44") + line(228, 148, 284, 148, stroke_width=3.5) +
         coin(76, 82, 13, p))
    return wrap(p, b, 2)


@scene("onboard-growth")
def _on4(p):
    stripes = "".join(line(98 + 124 * i / 5, 84, 84 + 152 * i / 5, 116, stroke_width=2) for i in range(1, 5))
    b = (rr(92, 116, 136, 72, 6, p.surface) + path("M84 116l14-32h124l14 32z", p.accent_soft) + stripes + rr(142, 144, 36, 44, 4, p.accent_soft) + rr(100, 132, 32, 24, 3, p.surface, stroke_width=2) +
         path("M254 140V92M242 104l12-12 12 12", stroke=p.accent_ink, stroke_width=3.5) + coin(64, 150, 14, p) + sparkle(256, 60, 10, p.accent))
    return wrap(p, b, 1)
