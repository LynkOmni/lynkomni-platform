"""The conversation engine's rules (CHAT UPDATE, master blueprint 74; build section 4 step C1), read from catalog/chat.v1.json.

One engine for every conversation in LynkOmni (LOCNV-): customer-and-business chat, Storefront chat and support, never personal,
group or staff-to-staff chat. This module is the Python reference; ts/src/chat.ts must agree on every case in
contract/vectors/chat.v1.json (python3 tools/chat_vectors.py after a change). Live signs are worked out here only to be drawn:
they are never stored and never enter an event. Masking runs before a message is queued, so a card number, PIN or code never
leaves the device and is never stored."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "chat.v1.json"), encoding="utf-8") as _f:
    CHAT = json.load(_f)

KINDS = CHAT["kinds"]
STATES = tuple(CHAT["states"]["order"])
SIGNS = CHAT["live_signs"]["signs"]
SOUND_EVENTS = CHAT["sounds"]["events"]
CARDS = CHAT["cards"]["kinds"]
ALWAYS_SEEN = ("business", "support", "assistant")


# ---- message states --------------------------------------------------------------------------------------------------------
def can_move(old, new, writer):
    """May the device or the cloud move a message from old to new? The device writes queued and sent (and a retry back to
    queued); the cloud alone writes accepted, confirmed and failed."""
    if new not in CHAT["states"]["next"].get(old, []):
        return False
    side = "device_writes" if writer == "device" else "cloud_writes"
    return new in CHAT["states"][side] or (writer == "device" and old == "failed" and new == "queued")


def shown_state(state, reader, reader_shows_seen=True):
    """The state the writer sees. A person who turned 'seen' off is never shown as having seen: their messages stop at
    accepted. A business's team, LynkOmni Support and LynkAssist always show seen."""
    if state == "confirmed" and reader not in ALWAYS_SEEN and not reader_shows_seen:
        return "accepted"
    return state


def edit_allowed(body, author, me, minutes_since):
    """Only the author fixes their own text message, within the window; the first version is kept for disputes."""
    return body == "text" and author == me and author != "system" and 0 <= minutes_since <= CHAT["edit"]["window_minutes"]


def ordered(messages):
    """Never lost, never doubled, always in order: the first copy of each id is kept, then sorted by when it was written and
    the device's own sequence."""
    seen, out = set(), []
    for m in messages:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        out.append(m)
    return sorted(out, key=lambda m: (m["written_at"], m["device_seq"], m["id"]))


# ---- masking ---------------------------------------------------------------------------------------------------------------
def _luhn(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def has_word(text, word):
    """A code word is in the text: in scripts with upper and lower case (Latin, Cyrillic, Greek...) only as a whole word, so
    'pin' is not found in 'spinach'; in scripts without spaces between words (Chinese, Japanese, Thai...) anywhere."""
    low, w = text.lower(), (word or "").lower()
    if not w:
        return False
    cased = lambda ch: ch.upper() != ch.lower()
    i = low.find(w)
    while i >= 0:
        before = low[i - 1] if i > 0 else ""
        after = low[i + len(w)] if i + len(w) < len(low) else ""
        if not (cased(w[0]) and before.isalpha()) and not (cased(w[-1]) and after.isalpha()):
            return True
        i = low.find(w, i + 1)
    return False


def mask(text, code_words=()):
    """Masks card numbers (13 to 19 digits that pass the card check, spaces or dashes allowed; the last four kept) always,
    and runs of 4 to 8 digits when the message also holds a code word (PIN, password, code and their translations). Returns
    the masked text and what was found, so the writer is warned before sending."""
    m = CHAT["masking"]
    found = []
    c = m["card"]
    sep = re.escape(c["separators"])

    kept = []

    def card(match):
        raw = match.group(0)
        digits = re.sub(r"[^0-9]", "", raw)
        if c["min_digits"] <= len(digits) <= c["max_digits"] and _luhn(digits):
            found.append("card")
            kept.append(m["mask_char"] * 4 + " " + digits[-c["keep_last"]:])
            return "\x00%d\x00" % (len(kept) - 1)
        return raw

    text = re.sub(r"(?<![0-9])[0-9](?:[%s]?[0-9]){%d,%d}(?![0-9])" % (sep, c["min_digits"] - 1, c["max_digits"] - 1), card, text)
    if any(has_word(text, w) for w in code_words):
        k = m["code"]

        def code(match):
            found.append("code")
            return k["shown_as"]

        text = re.sub(r"(?<![0-9\x00])[0-9]{%d,%d}(?![0-9\x00])" % (k["min_digits"], k["max_digits"]), code, text)
    text = re.sub(r"\x00(\d+)\x00", lambda g: kept[int(g.group(1))], text)
    return {"text": text, "found": sorted(set(found))}


# ---- live signs ------------------------------------------------------------------------------------------------------------
def live_sign(sign, author, online_both=True, reduced_motion=False, team_view=False, sender_allows=True):
    """What a live sign shows, or None. Signs need both sides online, always carry words, become still words when motion is
    off, and a person can stop sending their own typing, recording and sending signs. 'Ama is replying' is seen by the team
    only."""
    s = SIGNS.get(sign)
    if not s or author not in s["from"] or not online_both:
        return None
    if s.get("team_only") and not team_view:
        return None
    if s.get("person_can_turn_off") and not sender_allows:
        return None
    return {"words": s["words"], "motion": "none" if reduced_motion else s["motion"], "vars": list(s.get("vars", []))}


def own_connection(online, was_offline, queued):
    """The line about your own connection: waiting for internet, reconnecting, then back online with how many were sent."""
    oc = CHAT["live_signs"]["own_connection"]
    if not online:
        return {"words": oc["offline"], "n": queued}
    if was_offline:
        return {"words": oc["back_online"], "n": queued}
    return None


# ---- sounds and vibration --------------------------------------------------------------------------------------------------
def sound_for(event, s):
    """The tone and vibration for a chat event, or None for each. s holds the person's switches and the moment: sounds,
    vibration, silent, dnd, quiet_hours, focus, muted, screen, chat_open and since_last_ms (milliseconds since the last chat
    sound). Many messages at once make one sound; nothing inside a protected screen; typing never sounds."""
    snd = CHAT["sounds"]
    if event == "received":
        event = "received_open" if s.get("chat_open") else "received_closed"
    e = SOUND_EVENTS.get(event)
    if not e or e["tone"] is None and e["vibrate"] is None:
        return {"tone": None, "vibrate": None, "banner": False}
    if s.get("screen") in snd["protected_screens"]:
        return {"tone": None, "vibrate": None, "banner": not e.get("own_action", False)}
    own = e.get("own_action", False)
    hushed = (not own and (s.get("muted") or s.get("dnd") or s.get("quiet_hours") or s.get("focus"))) or \
             (not own and event.startswith("received") and s.get("since_last_ms", 10 ** 9) < snd["batch_window_ms"])
    tone = None if (hushed or s.get("silent") or not s.get("sounds", True)) else e["tone"]
    vib = None if (hushed or not s.get("vibration", True)) else e["vibrate"]
    return {"tone": tone, "vibrate": vib, "banner": False}


# ---- routing ---------------------------------------------------------------------------------------------------------------
def route_support(conv, helpers, open_now=True):
    """Who gets a support chat. Fast lane topics go straight to their own desk; otherwise LynkAssist answers first until the
    person asks for a person; out of hours it becomes a case; then the same helper as last time when free, else the least busy
    helper who covers the topic and side (a speaker of the language first, otherwise with translation); nobody free means the
    line. Ties break by helper id so the same case always routes the same way."""
    r = CHAT["routing"]["support"]
    topic = conv.get("topic", "general")
    if topic in r["fast_lane"]["topics"]:
        return {"to": "desk", "desk": r["fast_lane"]["desk"][topic], "helper": None, "reason": "fast_lane", "translate": False}
    if not conv.get("wants_person"):
        return {"to": "assistant", "desk": None, "helper": None, "reason": "assistant_first", "translate": False}
    if not open_now:
        return {"to": "case", "desk": topic, "helper": None, "reason": "out_of_hours", "translate": False}
    cap = r["max_open_per_helper"]
    can = [h for h in helpers if h.get("available") and h.get("on_shift") and h.get("open", 0) < cap
           and topic in h.get("topics", []) and conv.get("side", "internal") in h.get("sides", ["internal", "external"])
           and (not h.get("countries") or conv.get("country") in h["countries"])]
    if not can:
        return {"to": "line", "desk": topic, "helper": None, "reason": "back_in_line" if conv.get("was_with") else "least_busy", "translate": False}
    lang = conv.get("language")
    last = conv.get("last_helper")
    same = [h for h in can if h["id"] == last]
    if same:
        h = same[0]
        return {"to": "helper", "desk": topic, "helper": h["id"], "reason": "same_helper", "translate": lang not in h.get("languages", [])}
    speakers = [h for h in can if lang in h.get("languages", [])]
    pool = speakers or can
    h = sorted(pool, key=lambda h: (h.get("open", 0), h["id"]))[0]
    reason = "language" if speakers and len(speakers) < len(can) else "least_busy"
    return {"to": "helper", "desk": topic, "helper": h["id"], "reason": reason, "translate": not speakers}


def route_team(conv, staff, mode="least_busy", turn=0):
    """Who in a business's own team gets a customer chat: only people on shift; the owner's rules first (branch, product or
    order, language, the person who served this customer before), then take turns or least busy as the owner chose."""
    t = CHAT["routing"]["team"]
    on = [p for p in staff if p.get("on_shift")]
    if not on:
        return {"to": "line", "staff": None, "reason": "back_in_line"}
    if len(on) == 1:
        return {"to": "staff", "staff": on[0]["id"], "reason": "only_one_on_shift"}
    pool = on
    for rule in t["rules"]:
        if rule == "served_before":
            hit = [p for p in pool if p["id"] == conv.get("served_by")]
        elif rule == "branch":
            hit = [p for p in pool if conv.get("branch") and p.get("branch") == conv.get("branch")]
        elif rule == "product_or_order":
            hit = [p for p in pool if conv.get("product") and conv.get("product") in p.get("products", [])]
        else:
            hit = [p for p in pool if conv.get("language") and conv.get("language") in p.get("languages", [])]
        if hit:
            if rule == "served_before":
                return {"to": "staff", "staff": hit[0]["id"], "reason": "rule"}
            pool = hit
    if mode == "take_turns":
        pick = sorted(pool, key=lambda p: p["id"])[turn % len(pool)]
        return {"to": "staff", "staff": pick["id"], "reason": "take_turns"}
    pick = sorted(pool, key=lambda p: (p.get("open", 0), p["id"]))[0]
    return {"to": "staff", "staff": pick["id"], "reason": "rule" if len(pool) < len(on) else "least_busy"}


def escalate(minutes_waiting, setting=None):
    """A team chat goes to a manager after the owner's set time without an answer (5 to 120 minutes, 15 by default)."""
    e = CHAT["routing"]["team"]["escalate_after_min"]
    limit = min(max(setting if setting is not None else e["default"], e["min"]), e["max"])
    return minutes_waiting >= limit


def reply_time(first_reply_minutes):
    """'Usually replies within' from real figures: the median of the last 30 days' first replies rounded up to a bucket; not
    shown with fewer than 20 replies, never invented."""
    if len(first_reply_minutes) < 20:
        return None
    xs = sorted(first_reply_minutes)
    n = len(xs)
    med = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
    for b in (5, 10, 15, 30, 60, 120, 240, 1440):
        if med <= b:
            return b
    return None


# ---- offline, cards and tools ----------------------------------------------------------------------------------------------
def offline(what):
    """What happens to a chat action without internet: works, queued, sealed, knowledge_pack, waits or not_offered."""
    return CHAT["offline"]["what"].get(what, "waits")


def card_action(kind, action, online=True):
    """Whether a card's action is offered: only actions its service lists, and never one that needs the provider or a partner
    while offline (those cards are not offered at all offline). A ballot, card details and credentials never become cards."""
    c = CARDS.get(kind)
    if not c or action not in c["actions"]:
        return False
    if not online and (c["offline"] == "not_offered" or action in ("pay", "accept", "sign", "open_secure_step")):
        return False
    return True


def tools_ok(choices=0, fields=()):
    """Buttons and small forms stay small: at most six choices and four fields of the agreed kinds."""
    t = CHAT["tools"]
    return choices <= t["choices"]["max"] and len(fields) <= t["form_max_fields"] and all(f in t["form_fields"] for f in fields)
