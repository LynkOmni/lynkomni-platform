"""The one decision function that picks the interface for a device (DEVICE, master blueprint 48.17; catalog/devices.v1.json).
The TypeScript port is ts/src/interfaces.ts; contract/vectors/interfaces.v1.json proves both choose the same interface for
every combination of device facts.

facts (all optional):
  override       {"device": id, "version": "touch"|"non_touch"} or an interface id: the person's own "Change view"
  registered     {"device": id, "version": "touch"|"non_touch"}: the registered device record (selling devices)
  os_class       "phone" | "tablet" | "desktop" | "tv" | "watch" | "car" | "eink" | "speaker" | None (what the OS reports)
  touch          a touch screen is present          coarse   the main pointer is coarse (a finger)
  fine           a fine pointer is present (mouse, trackpad, pen)      hover   the main pointer can hover
  keyboard       a physical keyboard is present      remote   TV-remote or arrow keys were seen
  width, height  the screen in CSS pixels            moving   the vehicle is moving (car screens)
  last_input     "touch" | "pen" | "mouse" | "keyboard" | "remote" | None (devices with both follow the last one)
  no_apps        the phone has no app platform (basic phone)
Never the browser's name. Returns {"interface", "class", "rule"}: rule is override, registered, reported or safe_default."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "devices.v1.json"), encoding="utf-8") as _f:
    REGISTER = json.load(_f)
INTERFACES = REGISTER["interfaces"]
DEVICES = {d["id"]: d for d in REGISTER["devices"]}
SAFE = REGISTER["safe_default"]
RULES = ("override", "registered", "reported", "safe_default")


def _from_device(spec):
    """{"device", "version"} or an interface id -> an interface id (None when the device has no such version)."""
    if isinstance(spec, str):
        return spec if spec in INTERFACES else None
    if not isinstance(spec, dict):
        return None
    d = DEVICES.get(spec.get("device"))
    if not d or spec.get("version") not in ("touch", "non_touch"):
        return None
    return d[spec["version"]]


def _reported(f):
    os_class, w = f.get("os_class"), f.get("width") or 0
    touch, fine = bool(f.get("touch")), bool(f.get("fine"))
    last = f.get("last_input")
    if os_class == "car":
        return "car.voice"                                   # voice only; full use returns when the vehicle stops (screens decide that, not the layout)
    if os_class == "speaker":
        return "voice.only"
    if os_class == "watch":
        return "watch.touch"
    if os_class == "tv":
        return "tv.remote"
    if os_class == "eink":
        return "eink.touch" if touch else "eink.buttons"
    if f.get("no_apps"):
        return "phone.text"
    if touch:
        if (os_class == "desktop" or w >= 1024) and (fine or f.get("keyboard")):
            return "computer.pointer" if last in ("mouse", "keyboard") else "computer.touch"   # a 2-in-1 follows the input used last
        if os_class == "phone" or (os_class is None and 0 < w < 600):
            return "phone.touch"
        if os_class == "tablet" or 600 <= w:
            return "tablet.touch"
        return None
    if fine and (f.get("hover") or os_class == "desktop"):
        return "computer.pointer"
    if f.get("remote") and os_class is None and w >= 1024:           # a TV that does not say so: remote keys on a big screen
        return "tv.remote"
    if f.get("keyboard") and not fine and 0 < w < 600:
        return "phone.feature" if os_class == "phone" else "phone.keypad"
    return None


def choose(facts=None):
    f = facts or {}
    for rule, pick in (("override", lambda: _from_device(f.get("override"))), ("registered", lambda: _from_device(f.get("registered"))), ("reported", lambda: _reported(f))):
        i = pick()
        if i:
            return {"interface": i, "class": INTERFACES[i]["class"], "rule": rule}
    return {"interface": SAFE, "class": INTERFACES[SAFE]["class"], "rule": "safe_default"}


def safe_to_switch(task):
    """A new interface is applied only at a safe moment: never during a payment, a count or a signature."""
    return task not in ("payment", "count", "signature")


SHAPES = REGISTER["shapes"]


def layout(facts=None):
    """The layout for a screen's shape (TURN UPDATE, master blueprint 76; catalog/devices.v1.json shapes). Port: ts/src/interfaces.ts
    layoutFor. facts: interface (from choose), width, height, posture ("flat" | "half_open"), device (a register id) and lock
    ("upright" | "sideways", set in the Emulator Panel; obeyed only on a lockable fixed device). The phone's own rotation lock is the
    phone's business: the width and height it reports already follow it.
    Returns orientation, locked, nav (bottom_bar | side_rail | rail | two_level | soft_keys | glance | board | voice), tabs (bottom bar
    size, 0 when none), columns, header (normal | small | shrinks), helper (none | slide_in | open), main_button (bottom | top_end),
    split (none | fold: content on the top half, controls on the bottom half) and max_line_ch."""
    f = facts or {}
    s = SHAPES
    iface = f.get("interface") if f.get("interface") in INTERFACES else SAFE
    w, h = int(f.get("width") or 0), int(f.get("height") or 0)
    locked = f.get("lock") in ("upright", "sideways") and f.get("device") in s["lockable"]
    if locked and (f["lock"] == "sideways") != (w > h):
        w, h = h, w                                            # a locked fixed screen draws in its own direction
    orientation = "sideways" if w > h else "upright"
    out = {"orientation": orientation, "locked": locked, "nav": "bottom_bar", "tabs": 0, "columns": 1, "header": "normal", "helper": "none",
           "main_button": "bottom", "split": "none", "max_line_ch": s["max_line_ch"]}
    cls = INTERFACES[iface]["class"]
    if iface in s["buttons_only"]:
        out["nav"] = "soft_keys"
        return out
    if cls == "voice":
        out["nav"] = "voice"
        return out
    if cls == "watch":
        out["nav"] = "glance"
        return out
    if cls == "tv":
        out.update(nav="board", columns=3 if w >= s["wide_from_px"] else 2)
        return out
    if cls not in ("phone", "tablet", "computer") or iface == "universal":   # the safe default and e-ink touch follow the width
        cls = "computer" if w >= s["computer_from_px"] else "tablet" if min(w, h) >= s["tablet_from_px"] else "phone"
    if cls == "phone":
        if orientation == "upright":
            out.update(nav="bottom_bar", tabs=4 if w < s["small_phone_below_px"] else 5)
        else:
            out.update(nav="side_rail", header="small", columns=2 if w >= s["phone_two_columns_from_px"] else 1)
    elif cls == "tablet":
        out.update(nav="rail", columns=2 if orientation == "sideways" else 1, helper="open" if orientation == "sideways" else "slide_in")
    else:
        out.update(nav="two_level", columns=3 if w >= s["wide_from_px"] else 2, helper="open", main_button="top_end")
    if 0 < h < s["short_below_px"] and out["header"] == "normal":
        out["header"] = "shrinks"                              # very short screens: the header shrinks on scroll, the main button stays
    if f.get("posture") == "half_open":
        out["split"] = "fold"
    return out


def validate():
    """Register self-check: every device version names a real interface, every interface a real class and known inputs."""
    problems = []
    for d in SHAPES["lockable"]:
        if d not in DEVICES: problems.append(f"shapes.lockable: unknown device {d}")
    for i in SHAPES["buttons_only"]:
        if i not in INTERFACES: problems.append(f"shapes.buttons_only: unknown interface {i}")
    for i, v in INTERFACES.items():
        if v["class"] not in REGISTER["classes"]: problems.append(f"{i}: unknown class")
        for x in v["inputs"]:
            if x not in REGISTER["inputs"]: problems.append(f"{i}: unknown input {x}")
    for d in REGISTER["devices"]:
        for ver in ("touch", "non_touch"):
            if d[ver] is not None and d[ver] not in INTERFACES: problems.append(f"{d['id']}.{ver}: unknown interface")
            if d[ver] is None and d["emulator"][ver] is not None: problems.append(f"{d['id']}.{ver}: emulator without a version")
    if SAFE not in INTERFACES: problems.append("safe default is not an interface")
    return problems
