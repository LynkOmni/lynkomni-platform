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


def validate():
    """Register self-check: every device version names a real interface, every interface a real class and known inputs."""
    problems = []
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
