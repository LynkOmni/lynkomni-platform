"""LynkQueue ticket rules (LynkQ, NEW UPDATE 4, owner locked 2026-11-11, master blueprint section 63). The Python reference;
ts/src/queue.ts must agree on contract/vectors/people.v1.json (run python3 tools/people_vectors.py after a change).

A ticket number is the 3-character section code, a dash and a 6-character Lynk Code from the Lynk Alphabet (2 to 9 and A to Z without
O, 0, I and 1, so nothing is confused): LAB-A2K9P2. Codes count up from 222222 to ZZZZZZ, 32 to the power of 6 = 1,073,741,824 for each
section at each place, and a code is never used twice there. Codes that would spell a rude word are skipped. The order is fair: first
come, first served, appointments at their time, priority by the manager's balance; staff press Call next and never choose."""

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 6
SECTION_LENGTH = 3
CAPACITY = len(ALPHABET) ** CODE_LENGTH          # 1,073,741,824
CALLS_BEFORE_MISSED = 3
PUT_BACK_MINUTES = 15
PUT_BACK_AFTER = 3            # a missed ticket put back goes in after the next 3 people
RUNNING_LATE_PLACES = 3       # running late moves a ticket back 3 places, once
PRIORITY_BALANCE = 3          # default: 1 priority after every 3 others
APPOINTMENT_GRACE_MINUTES = 10
PLEASE_COME_AT = 5            # "Please come now" when 5 people are left
BLOCK_SIZE = 1000             # codes set aside for each device for when it is cut off
# Words never spelled in a ticket code or a section code (checked after the code is made). Written in the Lynk Alphabet, so words
# that need O, I, 0 or 1 cannot appear anyway. Country packs may add words for their languages.
BLOCKED = ("FUCK", "FUK", "FCK", "SHT", "CUNT", "DCK", "PUSY", "PUSSY", "SLUT", "WHRE", "RAPE", "NAZ", "KKK", "XXX", "SEX", "ANAL", "ANUS",
           "CUM", "TWAT", "WANK", "FAG", "NGGA", "NGR", "PUTA", "PUTE", "MERDE", "SUCK", "KYS", "STFU", "WTF", "KILL")


def code(n):
    """The n-th code (n from 0), before any skipping: 0 is 222222 and CAPACITY - 1 is ZZZZZZ."""
    if not 0 <= n < CAPACITY:
        raise ValueError("no such code")
    out = []
    for _ in range(CODE_LENGTH):
        n, r = divmod(n, len(ALPHABET))
        out.append(ALPHABET[r])
    return "".join(reversed(out))


def index(c):
    """The position of a code in the count."""
    if not valid_code(c):
        raise ValueError(f"{c} is not a Lynk Code")
    n = 0
    for ch in c:
        n = n * len(ALPHABET) + ALPHABET.index(ch)
    return n


def valid_code(c):
    return isinstance(c, str) and len(c) == CODE_LENGTH and all(ch in ALPHABET for ch in c)


def valid_section(s):
    return isinstance(s, str) and len(s) == SECTION_LENGTH and all(ch in ALPHABET for ch in s) and not rude(s)


def rude(text):
    return any(w in text for w in BLOCKED)


def next_code(after=None):
    """The next code to give out after the last one given (None for the very first), skipping rude words. Returns None when the
    section's codes are used up (it then gets a new section code; old codes are never reused)."""
    n = 0 if after is None else index(after) + 1
    while n < CAPACITY:
        c = code(n)
        if not rude(c):
            return c
        n += 1
    return None


def ticket_number(section, c):
    return f"{section}-{c}"


def reserve_block(after, size=BLOCK_SIZE):
    """A block of codes set aside for one device: the first code and the last code (rude words skipped inside the block when used)."""
    first = next_code(after)
    if first is None:
        return None
    last = code(min(index(first) + size - 1, CAPACITY - 1))
    return {"first": first, "last": last}


def pick_next(waiting, served_since_priority, now_minute, balance=PRIORITY_BALANCE):
    """Who Call next brings, fairly. waiting is a list of tickets {"id", "seq" (arrival order), "priority": bool, "appointment": minute
    or None, "held": bool}; held tickets (On hold, Running late in effect) are skipped. Appointments due within the grace come first,
    then a priority ticket once `balance` others have been served since the last priority (or when no one else waits), else the oldest."""
    live = [t for t in waiting if not t.get("held")]
    if not live:
        return None
    due = sorted((t for t in live if t.get("appointment") is not None and t["appointment"] <= now_minute + APPOINTMENT_GRACE_MINUTES),
                 key=lambda t: (t["appointment"], t["seq"]))
    if due:
        return due[0]["id"]
    normal = sorted((t for t in live if not t.get("priority") and t.get("appointment") is None), key=lambda t: t["seq"])
    prio = sorted((t for t in live if t.get("priority") and t.get("appointment") is None), key=lambda t: t["seq"])
    if prio and (served_since_priority >= balance or not normal):
        return prio[0]["id"]
    if normal:
        return normal[0]["id"]
    later = sorted(live, key=lambda t: (t.get("appointment") or 0, t["seq"]))
    return later[0]["id"]


def place_of(ticket_id, order):
    """The person's place as a plain number (1 = next)."""
    return order.index(ticket_id) + 1


def wait_minutes(place, average_service_minutes, open_counters):
    """About how long, rounded up; always shown as an estimate."""
    if open_counters < 1:
        return None
    return -(-(place * average_service_minutes) // open_counters)


def put_back(order, ticket_id, missed_minute, now_minute):
    """Put a missed ticket back after the next 3 people, once, within 15 minutes; returns the new order or None when too late."""
    if now_minute - missed_minute > PUT_BACK_MINUTES:
        return None
    rest = [t for t in order if t != ticket_id]
    at = min(PUT_BACK_AFTER, len(rest))
    return rest[:at] + [ticket_id] + rest[at:]


def running_late(order, ticket_id):
    """Move a ticket back 3 places (once per ticket)."""
    rest = [t for t in order if t != ticket_id]
    at = min(order.index(ticket_id) + RUNNING_LATE_PLACES, len(rest))
    return rest[:at] + [ticket_id] + rest[at:]
