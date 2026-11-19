"""The Emulator Panel's rules (EMULATOR UPDATE, master blueprint section 70; build section 3A).

An emulator is a LynkOmni device in software (a POS terminal, a queue kiosk, a counter screen, a number board). The panel gives
emulators to devices, shows every device live and connects or disconnects them. The register is catalog/emulators.v1.json; these
rules are the reference, ts/src/emulators.ts is the port and contract/vectors/emulators.v1.json (python3 tools/emulators_vectors.py)
proves they agree.

Rules kept here:
- Only staff emulators connected at the same time count against the plan; a device that runs several services' till counts once;
  customer-facing screens are free and unlimited; practice mode never counts. Numbers come only from services/billing.py.
- An assignment code is a 6-character Lynk Code that works once and expires after CODE_MINUTES.
- The check before assigning refuses only a device that cannot run the emulator at all, and names the way round for the rest.
- Key tones and press vibration follow the manager's setting, the user's choice where allowed, and switch off in silent mode,
  do not disturb and the place's quiet hours; a device without vibration plays the tone only. Never the only signal.
- The delivery menu shows only what works on the device at that moment; offline, messages wait as "queued".
- States shown to people are only queued, sent, accepted, confirmed and failed.
"""
import json, os

from core import queue_tickets as Q

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "catalog", "emulators.v1.json"), encoding="utf-8") as _f:
    REG = json.load(_f)
EMULATORS = {e["id"]: e for e in REG["emulators"]}
DEVICE_NAMES = ("LynkMobile", "LynkTab", "LynkPC", "LynkPOS", "LynkKiosk", "LynkDScreen", "LynkCDisplay")

CODE_MINUTES = 10                   # an assignment code works once and only for this long
REAPPROVE_DAYS = 30                 # a device not seen for this many days must be approved again
DOWNGRADE_GRACE_DAYS = 3            # on a downgrade nothing is cut off mid-day; the owner chooses, with these days of grace
ARTWORK_MIN_PX = 48                 # spare space on a side below this is left plain
VOLUMES = ("low", "medium", "high")
SOUNDS = ("key", "confirm", "cancel", "error", "scan", "paid", "printer")
STATES = ("queued", "sent", "accepted", "confirmed", "failed")

# Where each kind of hardware can be connected (blueprint 70.9), most reliable first.
HARDWARE_WAYS = {
    "receipt_printer": ("network", "bluetooth", "usb", "device_print"),
    "ticket_printer": ("network", "bluetooth", "usb", "device_print"),
    "kitchen_printer": ("network", "usb"),
    "label_printer": ("network", "bluetooth", "usb"),
    "scanner": ("bluetooth", "usb", "camera"),
    "cash_drawer": ("drawer_cable",),
    "scale": ("usb", "serial", "bluetooth"),
    "card_reader": ("bluetooth",),
    "fingerprint_reader": ("usb",),
    "pager": ("bluetooth", "network"),
    "camera": ("camera",),
}
# What each kind of device's browser allows today (the native apps of build section 14 allow more).
OS_WAYS = {
    "android": ("network", "bluetooth", "usb", "serial", "device_print", "camera", "drawer_cable"),
    "windows": ("network", "bluetooth", "usb", "serial", "device_print", "camera", "drawer_cable"),
    "mac": ("network", "bluetooth", "usb", "serial", "device_print", "camera", "drawer_cable"),
    "linux": ("network", "bluetooth", "usb", "serial", "device_print", "camera", "drawer_cable"),
    "chromeos": ("network", "bluetooth", "usb", "serial", "device_print", "camera", "drawer_cable"),
    "ios": ("network", "device_print", "camera", "drawer_cable"),            # honest limit: little by cable or Bluetooth in the browser
    "tv": ("network",),
    "other": ("network", "device_print"),
}


def slots(family, tier):
    """Staff emulator slots of a family's tier: a whole number, None for no limit, or "own_units" for LynkAttend, LynkQueue and
    LynkSurvey, which keep their own locked units (places, counters, creators) and are not limited again here."""
    from services import billing
    f = billing.FEATURES.get(family)
    if not f:
        return None
    ent = {}
    for d in f[: billing.MT.index(tier) + 1]:
        ent.update(d)
    return ent.get("emulator_slots")


def extra_slot_cents(family):
    """One more staff device a month for this family on Plus and Pro (services/billing.py EMULATOR_EXTRA_CENTS), or None."""
    from services import billing
    return billing.EMULATOR_EXTRA_CENTS.get(family)


def day_pass_cents():
    from services import billing
    return billing.SERVICE_FEES["emulator_day_pass_cents"]


def day_pass_max_days():
    from services import billing
    return billing.SERVICE_FEES["emulator_day_pass_max_days"]


def cheaper_tier(family, tier, extras):
    """The next tier when it costs less a month than this tier with these extra devices (the panel says so; it never upgrades by
    itself), else None. Prices come only from services/billing.py."""
    from services import billing
    tiers, prices = list(billing.FAMILIES[family][2]), billing.FAMILIES[family][3]
    i = tiers.index(tier)
    cents = extra_slot_cents(family)
    if not extras or cents is None or i + 1 >= len(tiers):
        return None
    now = round(prices[i] * 100) + extras * cents
    nxt = round(prices[i + 1] * 100)
    nxt_slots, now_slots = slots(family, tiers[i + 1]), slots(family, tier)
    fits = nxt_slots is None or (isinstance(nxt_slots, int) and isinstance(now_slots, int) and nxt_slots >= now_slots + extras)
    return tiers[i + 1] if fits and nxt <= now else None


def counts_for(emulator_id):
    """The family whose plan a connected emulator counts against, or None when it is free (customer-facing)."""
    e = EMULATORS[emulator_id]
    if not e["counted"]:
        return None
    return e["shared_with"] or e["service"]


def in_use(family, connections):
    """How many staff slots of a family are taken: distinct devices with a connected, counted emulator of that family (a till that
    runs LynkPOS, LynkRewards and payments counts once; practice mode never counts). connections: [{device, emulator, connected,
    practice?}]."""
    devices = set()
    for c in connections:
        if not c.get("connected") or c.get("practice"):
            continue
        if counts_for(c["emulator"]) == family:
            devices.add(c["device"])
    return len(devices)


def may_connect(limit, family, connections, new, extra=0):
    """Whether one more connection fits the plan. limit: slots(...) (a number, None or "own_units"); new: {device, emulator, practice?}.
    Returns (True, None) or (False, "plan_limit")."""
    fam = counts_for(new["emulator"])
    if fam is None or new.get("practice") or limit is None or limit == "own_units":
        return True, None
    if fam != family:
        return True, None
    after = connections + [dict(new, connected=True)]
    if in_use(family, after) <= limit + extra:
        return True, None
    return False, "plan_limit"


def code_valid(issued_at, now, used=False):
    """An assignment code works once, for CODE_MINUTES (seconds since the epoch in, True or False out)."""
    return not used and 0 <= now - issued_at <= CODE_MINUTES * 60


def new_code(n):
    """The n-th assignment code: a 6-character Lynk Code from the Lynk Alphabet (the same alphabet as queue tickets)."""
    return Q.code(n % Q.CAPACITY)


def can_run(emulator_id, caps):
    """The check before assigning. caps: {short_side, touch, keys, camera, speaker, vibration, os, hardware: [kinds connected]}.
    Returns {"ok", "refused", "missing": [{"need", "way"}]}: refused only when the device cannot run it at all."""
    e = EMULATORS[emulator_id]
    missing = []
    if caps.get("short_side", 0) < e["needs"]["min_short_side_px"]:
        return {"ok": False, "refused": "screen_too_small", "missing": []}
    if not caps.get("touch") and not caps.get("keys"):
        return {"ok": False, "refused": "no_way_to_use", "missing": []}
    if e["checks"]["touch"] is not True and caps.get("touch") and not caps.get("keys"):
        missing.append({"need": "remote_or_keys", "way": "use_remote_or_keyboard"})
    hw = set(caps.get("hardware", ()))
    for need in e["needs"]["outputs"]:
        if need == "camera_or_scanner" and not caps.get("camera") and "scanner" not in hw:
            missing.append({"need": need, "way": "connect_a_scanner"})
        if need == "speaker" and not caps.get("speaker"):
            missing.append({"need": need, "way": "use_a_device_with_sound"})
    return {"ok": True, "refused": None, "missing": missing}


def connect_ways(kind, os_name):
    """The ways a kind of hardware can be connected from this kind of device, best first. Empty means it cannot be connected here,
    and the answer is to print or scan through another device (blueprint 70.9)."""
    allowed = OS_WAYS.get(os_name, OS_WAYS["other"])
    return [w for w in HARDWARE_WAYS.get(kind, ()) if w in allowed]


def hardware_advice(kind, os_name):
    """The plain answer when hardware is added: the ways that work here, or the way round when none does."""
    ways = connect_ways(kind, os_name)
    if ways:
        return {"ways": ways, "fallback": None}
    return {"ways": [], "fallback": "through_another_device"}


def tones(manager, user=None, customer_facing=False, silent=False, quiet_hours=False, vibrates=True):
    """The key tone and press vibration on a device. manager: {tones, vibration, volume, user_may_change, pin_same_tone};
    user: the signed-in user's own choice ({tones?, vibration?, volume?}) where the manager allows it. A customer-facing screen
    follows the manager. Silent mode, do not disturb and quiet hours switch the tones off; a device without vibration plays the
    tone only. The screen always shows the press as well."""
    s = {"tones": bool(manager.get("tones", True)), "vibration": bool(manager.get("vibration", True)), "volume": manager.get("volume", "medium")}
    if user and manager.get("user_may_change", True) and not customer_facing:
        for k in ("tones", "vibration", "volume"):
            if user.get(k) is not None:
                s[k] = user[k]
    if s["volume"] not in VOLUMES:
        s["volume"] = "medium"
    if silent or quiet_hours:
        s["tones"] = False
    if not vibrates:
        s["vibration"] = False
    s["pin_tones"] = "same" if manager.get("pin_same_tone") else "per_key"
    return s


def delivery_ways(caps, online, printer_ready, customer_known, contact_given):
    """The delivery menu for a receipt, ticket or document: only what works on this device now, in a fixed order. Each way is
    "now" or "queued" (a message made offline waits). A printed and a digital copy are the same document."""
    out = []
    if printer_ready or caps.get("device_print") or caps.get("print_through"):
        out.append({"way": "print", "state": "now"})
    out.append({"way": "qr", "state": "now"})
    if customer_known:
        out.append({"way": "account", "state": "now" if online else "queued"})
        out.append({"way": "lynkchat", "state": "now" if online else "queued"})
    if contact_given:
        out.append({"way": "message", "state": "now" if online else "queued"})
    if caps.get("nearby"):
        out.append({"way": "nearby", "state": "now"})
    out.append({"way": "file", "state": "now"})
    return out


def request_state(step):
    """The state a person sees for an assignment step (the five states only)."""
    return {"made_offline": "queued", "offered": "sent", "accepted": "accepted", "connected": "confirmed",
            "denied": "failed", "expired": "failed", "disconnect_sent": "sent", "disconnected": "confirmed"}[step]


def reapproval_due(last_seen_day, today, days=REAPPROVE_DAYS):
    """A device not seen for `days` must be approved again before it works."""
    return today - last_seen_day >= days


def downgrade(limit, family, connections):
    """After a downgrade: how many connected devices the owner must choose to disconnect, and the grace in days (nothing is cut
    off mid-day). limit None or "own_units" means none."""
    if limit is None or limit == "own_units":
        return {"to_disconnect": 0, "grace_days": 0}
    over = max(0, in_use(family, connections) - limit)
    return {"to_disconnect": over, "grace_days": DOWNGRADE_GRACE_DAYS if over else 0}


def fit(screen_w, screen_h, design_w, design_h):
    """Fits an emulator's screen into a device's screen without stretching: one scale for both sides, never above 1.5 or below the
    point where text would break (0.75 keeps the device-fit rules), and the spare space left and right or above and below, filled
    by the service's artwork when it is at least ARTWORK_MIN_PX."""
    scale = min(screen_w / design_w, screen_h / design_h)
    scale = max(0.75, min(1.5, scale))
    w, h = round(design_w * scale), round(design_h * scale)
    spare_x, spare_y = max(0, screen_w - w), max(0, screen_h - h)
    side = "sides" if spare_x >= 2 * ARTWORK_MIN_PX else "top_bottom" if spare_y >= 2 * ARTWORK_MIN_PX else "none"
    return {"scale_pct": round(scale * 100), "width": w, "height": h, "spare_x": spare_x, "spare_y": spare_y, "artwork": side}


def four_checks(e):
    """The four checks every emulator states (blueprint 70.14): a list of what is missing (empty when all four are stated)."""
    c, out = e.get("checks", {}), []
    t = c.get("touch")
    if t is not True and not (isinstance(t, dict) and t.get("why") in REG["touch_exceptions"]):
        out.append("touch")
    if c.get("buttons_only") is not True:
        out.append("buttons_only")
    if c.get("offline") not in REG["offline_kinds"]:
        out.append("offline")
    if not c.get("sides") or not set(c["sides"]) <= {"internal", "external"}:
        out.append("sides")
    return out
