"""LynkAttend rules (LynkA, NEW UPDATE 4, owner locked 2026-11-11, master blueprint section 63). The Python reference; ts/src/attendance.ts
must agree on contract/vectors/people.v1.json (run python3 tools/people_vectors.py after a change).

At the door the PIN comes first and says who the person is and which set is theirs; the device then runs the means of the set in the
fixed order Face, Finger, IDCN. Face or Finger fails 3 times (or does not work on this device) and the next means takes over, ending
with IDCN; every backup is marked. An IDCN is the last 6 digits of the full ID number (0s added at the end when there are fewer than 6;
fewer than 4 digits means another ID document). The PIN is 6 digits, created by LynkOmni, never easy, never given twice in a PIN group
and never reused. Nothing here ever stores a PIN, an IDCN or an ID number in an event."""

SETS = ("face_finger_idcn", "face_idcn", "finger_idcn", "idcn")
ORDER = ("face", "finger", "idcn")
PIN_LENGTH = 6
IDCN_LENGTH = 6
IDCN_MIN_DIGITS = 4
BIOMETRIC_TRIES = 3          # Face or Finger: 3 tries, then the next means
IDCN_TRIES = 5               # wrong IDCN 5 times blocks the PIN
PIN_TRIES_BEFORE_PAUSE = 5   # 5 unknown PINs in a row pause the device
PIN_PAUSE_SECONDS = 60
PIN_GROUP_WARN_PERCENT = 90
NO_CHECK_OUT_AFTER_MINUTES = 120   # after the shift ends (at midnight without shifts)


def idcn(full_id_number):
    """The IDCN made from a full ID number, or None when the document has too few digits (register another ID document)."""
    digits = "".join(ch for ch in str(full_id_number) if "0" <= ch <= "9")
    if len(digits) < IDCN_MIN_DIGITS:
        return None
    return digits[-IDCN_LENGTH:].ljust(IDCN_LENGTH, "0")


def means_of(set_name):
    """The means of a set, in the fixed order Face, Finger, IDCN. IDCN is in every set."""
    if set_name not in SETS:
        raise ValueError(f"{set_name} is not a set")
    return [m for m in ORDER if m in set_name.split("_")]


def sets_allowed(face_allowed, finger_allowed):
    """The sets a manager may pick in a country: only the means that country allows."""
    return [s for s in SETS if ("face" not in s or face_allowed) and ("finger" not in s or finger_allowed)]


def is_easy_pin(pin):
    """Easy PINs are never created: one digit repeated, a run up or down (123456, 654321), a pair or three repeated (121212, 123123)."""
    if len(pin) != PIN_LENGTH or not pin.isdigit():
        return True
    d = [int(c) for c in pin]
    if len(set(d)) == 1:
        return True
    steps = {(d[i + 1] - d[i]) for i in range(PIN_LENGTH - 1)}
    if steps in ({1}, {-1}):
        return True
    return pin == pin[:2] * 3 or pin == pin[:3] * 2


EASY_PIN_COUNT = 1100          # fixed so nothing counts a million PINs at start; tests/test_people_rules.py counts them
PIN_GROUP_SIZE = 10 ** PIN_LENGTH - EASY_PIN_COUNT


def pin_group_warning(used):
    """True when a PIN group is 90% used: LynkOmni tells the manager and offers a new PIN group."""
    return used * 100 >= PIN_GROUP_SIZE * PIN_GROUP_WARN_PERCENT


def new_pin(draw, taken):
    """A new PIN for a PIN group. draw() returns a random integer below 10**6 (a secure random source in production); taken holds every
    PIN ever given in the group, live or blocked, so a PIN is never given twice and never reused."""
    if len(taken) >= PIN_GROUP_SIZE:
        raise ValueError("this PIN group is full; start a new PIN group")
    while True:
        pin = f"{draw() % 10 ** PIN_LENGTH:06d}"
        if not is_easy_pin(pin) and pin not in taken:
            return pin


def backup_reason(means, broken):
    """The mark on a record when a means is passed over: face_failed or face_not_working (and the same for finger)."""
    return f"{means}_not_working" if broken else f"{means}_failed"


def door(set_name, attempts, broken=()):
    """Runs the door for one person after their PIN. attempts lists the outcomes the person produces, in order ("ok" or "fail");
    broken lists means that do not work on this device. Returns the steps, the result ("in", "pin_blocked", "see_manager" or
    "waiting") and the means used with any backup mark."""
    steps, i, backup = [], 0, None
    for means in means_of(set_name):
        if means in broken:
            steps.append({"means": means, "result": "not_working"})
            backup = backup or backup_reason(means, True)
            continue
        tries = IDCN_TRIES if means == "idcn" else BIOMETRIC_TRIES
        for t in range(1, tries + 1):
            if i >= len(attempts):
                return {"steps": steps, "result": "waiting", "means": means, "backup_from": backup}
            outcome = attempts[i]; i += 1
            steps.append({"means": means, "try": t, "result": outcome})
            if outcome == "ok":
                return {"steps": steps, "result": "in", "means": means, "backup_from": backup}
        if means == "idcn":
            return {"steps": steps, "result": "pin_blocked", "means": None, "backup_from": backup}
        backup = backup or backup_reason(means, False)
    return {"steps": steps, "result": "see_manager", "means": None, "backup_from": backup}


def checker_choices(checkers, me):
    """The checker list a person sees: their own name is never in it."""
    return [c for c in checkers if c != me]


def checker_flags(checker_checked_in):
    """A checker who is not checked in never stops the check-in; the record is flagged for the manager."""
    return [] if checker_checked_in else ["checker_not_checked_in"]


def no_check_out_due(check_in_minute, shift_end_minute=None):
    """The minute of the day (0 to 1440) when a record with no check-out is marked "No check-out": 2 hours after the shift ends,
    or midnight without shifts."""
    if shift_end_minute is None:
        return 1440
    return min(shift_end_minute + NO_CHECK_OUT_AFTER_MINUTES, 1440) if shift_end_minute >= check_in_minute else 1440


def sets_for_country(pack):
    """The sets a manager may pick in a country, from its pack: Face or Finger is removed only where the pack says false (null means
    not yet confirmed: still selectable with the person's agreement). IDCN is always there."""
    a = ((pack or {}).get("people") or {}).get("attendance") or {}
    return sets_allowed(a.get("face_allowed") is not False, a.get("finger_allowed") is not False)
