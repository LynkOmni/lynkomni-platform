"""The one engine for every message and notification (MASTER UPDATE, master blueprint sections 56 and 62).

Every kind is in catalog/messages.v1.json; nothing outside it is sent or shown. One event makes one notification record per
person, whatever the number of channels or devices, and that record feeds the bell, push, email, text and the Messages page
with one read state. The engine applies, in this order: the register, the never-in-a-message rules, sent once, the lawful
basis, the person's settings, grouping and in-place updates, the daily cap, quiet hours and do not disturb (critical breaks
through), then delivery with fallback. Critical notifications repeat until acknowledged; unanswered high and critical ones
escalate to the next role. Offline backlogs are folded on reconnect so nobody is flooded.

SANDBOX: SandboxSender stands in for the email, text and push providers (provider ledger "sms_otp"); it never tracks opens."""
import json, os, re, time, uuid
from core.locale import in_quiet_hours

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "messages.v1.json"), encoding="utf-8") as _f:
    REG = json.load(_f)
KINDS = {k["id"]: k for k in REG["kinds"]}
FMT = "%Y-%m-%dT%H:%M:%SZ"
BURST_S = 3600
REPEAT_S = 300
ESCALATE_DEFAULT_S = 900
NEXT_ROLE = {"cashier": "manager", "stock_staff": "manager", "agent": "owner", "manager": "owner"}
SECRET_WORDS = {"password", "passcode", "pin", "otp", "secret", "token", "cvv", "cvc"}
SECRET_KEYS = {"code", "sign_in_code", "verification_code", "one_time_code", "recovery_code"}
POSITION_KEYS = re.compile(r"^(lat|lng|lon|latitude|longitude|position|coords?)$", re.I)
APP_LINK = re.compile(r"^https://([a-z0-9-]+\.)*lynkomni\.com(/|$)")


def _ts(t):
    return time.strftime(FMT, time.gmtime(t))


def _luhn(digits):
    s, alt = 0, False
    for c in reversed(digits):
        d = int(c)
        if alt:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        s, alt = s + d, not alt
    return s % 10 == 0


def check_content(facts):
    """The never-in-a-message rules: no secret, no full card number, no position, no link outside the signed-in app."""
    for key, val in (facts or {}).items():
        words = set(re.split(r"[_\-\s]+", key.lower()))
        if words & SECRET_WORDS or key.lower() in SECRET_KEYS:
            raise ValueError(f"'{key}' may never be sent in a message")
        if POSITION_KEYS.match(key):
            raise ValueError("a position is never sent in a message")
        text = str(val)
        for run in re.findall(r"(?:\d[ -]?){13,19}", text):
            digits = re.sub(r"\D", "", run)
            if 13 <= len(digits) <= 19 and _luhn(digits):
                raise ValueError("a full card number is never sent in a message")
        for link in re.findall(r"https?://\S+", text):
            if not APP_LINK.match(link):
                raise ValueError("links in messages only open the signed-in LynkOmni app")
    return True


class SandboxSender:
    """SANDBOX: delivers by recording; a channel listed in fail is down. It reports delivery, never opens."""
    def __init__(self, fail=()):
        self.fail, self.sent = set(fail), []

    def deliver(self, channel, person, kind, lang):
        if channel in self.fail:
            return False
        self.sent.append((channel, person, kind, lang))
        return True


class Notifier:
    def __init__(self, sender=None):
        self.sender = sender or SandboxSender()
        self.lines, self.seen_keys, self.backlog, self.sent_today, self.summary = {}, set(), {}, {}, {}

    # ---- the register and the rules
    @staticmethod
    def kind(kid):
        if kid not in KINDS:
            raise KeyError(f"{kid} is not in the message register (catalog/messages.v1.json)")
        return KINDS[kid]

    def notify(self, kid, person, event_id, now, facts=None, record=None, lang="en", country=None, business=None,
               consent=False, prefs=None, contacts=("bell", "push", "email", "text"), online=True, role=None):
        k = self.kind(kid)
        check_content(facts)
        key = (event_id, kid, person)
        if key in self.seen_keys:
            return {"state": "duplicate"}
        self.seen_keys.add(key)
        if k["basis"] == "opt_in" and consent is not True:
            return {"state": "refused", "reason": "no_opt_in"}
        prefs = prefs or {}
        if k["can_turn_off"] and (kid in prefs.get("muted", ()) or prefs.get("paused_optional")):
            return {"state": "suppressed", "reason": "muted"}
        if record and record in prefs.get("muted_records", ()) and k["can_turn_off"]:
            return {"state": "suppressed", "reason": "muted_record"}
        line = self._line(k, person, event_id, now, record, business, role, facts)
        if not online:
            self.backlog.setdefault(person, []).append(line["nid"])
            return {"state": "queued", "nid": line["nid"]}
        return self._deliver(k, line, person, now, lang, country, prefs, contacts)

    def _line(self, k, person, event_id, now, record, business, role, facts):
        for l in self.lines.values():                        # in-place updates and bursts reuse a line
            if l["person"] != person or l["kind"] != k["id"] or l["business"] != business or l["cleared"]:
                continue
            if k["group"] == "update" and record and l["record"] == record:
                l.update(at=now, read=False, seen=False, events=l["events"] + [event_id], facts=facts or {})
                return l
            if k["group"] == "burst" and not l["read"] and now - l["at"] <= BURST_S:
                l.update(at=now, count=l["count"] + 1, seen=False, events=l["events"] + [event_id])
                return l
        nid = uuid.uuid4().hex
        l = {"nid": nid, "kind": k["id"], "area": k["area"], "priority": k["priority"], "person": person, "role": role,
             "business": business, "record": record, "events": [event_id], "facts": facts or {}, "at": now, "first_at": now,
             "count": 1, "seen": False, "read": False, "acked": False, "cleared": False, "done_by": None, "escalated": False,
             "channels": []}
        self.lines[nid] = l
        return l

    def _deliver(self, k, line, person, now, lang, country, prefs, contacts):
        pr = REG["priorities"][k["priority"]]
        if k["group"] in ("daily", "summary"):
            self.summary.setdefault(person, []).append(line["nid"])
            return {"state": "in_summary", "nid": line["nid"]}
        day = (person, _ts(now)[:10])
        if pr["capped"]:
            self.sent_today[day] = self.sent_today.get(day, 0) + 1
            if self.sent_today[day] > REG["daily_cap"]:
                self.summary.setdefault(person, []).append(line["nid"])
                return {"state": "in_summary", "nid": line["nid"]}
        quiet = (country and in_quiet_hours(_ts(now), country, REG["quiet_hours"]["start"], REG["quiet_hours"]["end"])) \
            or now < prefs.get("dnd_until", 0)
        if quiet and not pr["breaks_quiet_hours"]:
            return {"state": "bell_only_until_quiet_ends", "nid": line["nid"], "channels": ["bell"]}
        allowed = prefs.get("channels", {}).get(k["area"])
        wanted = [c for c in k["channels"] if c in contacts and (not k["can_turn_off"] or allowed is None or c in allowed)]
        out = ["bell"] if "bell" in wanted else []
        delivered_one = False
        for c in [c for c in wanted if c != "bell"]:
            if delivered_one and k["priority"] != "critical":
                break                                         # one outside channel is enough, except for critical
            if self.sender.deliver(c, person, k["id"], lang):
                out.append(c)
                delivered_one = True
        line["channels"] = sorted(set(line["channels"]) | set(out))
        return {"state": "shown", "nid": line["nid"], "channels": out}

    # ---- the bell
    def bell(self, person, business=None, area=None, unread_only=False, now=None):
        cut = (now or time.time()) - REG["history_days"] * 86400
        ls = [l for l in self.lines.values() if l["person"] == person and not l["cleared"] and l["at"] >= cut
              and (business is None or l["business"] == business or l["area"] == "security")
              and (area is None or l["area"] == area) and (not unread_only or not l["read"])]
        ls.sort(key=lambda l: l["at"], reverse=True)
        return {"new": [l for l in ls if not l["seen"]], "earlier": [l for l in ls if l["seen"]]}

    def count(self, person):
        n = sum(1 for l in self.lines.values() if l["person"] == person and not l["seen"] and not l["cleared"]
                and REG["priorities"][l["priority"]]["raises_count"])
        return "99+" if n > 99 else n

    def open_bell(self, person):
        for l in self.lines.values():
            if l["person"] == person:
                l["seen"] = True

    def read(self, nid, read=True):
        self.lines[nid]["read"] = read
        self.lines[nid]["seen"] = self.lines[nid]["seen"] or read

    def mark_all_read(self, person):
        for l in self.lines.values():
            if l["person"] == person:
                l["read"] = l["seen"] = True

    def act(self, nid, by):
        """Someone acted: the same notification clears for everyone it went to, with 'Done by'."""
        l = self.lines[nid]
        for m in self.lines.values():
            if m["kind"] == l["kind"] and set(m["events"]) & set(l["events"]):
                m.update(done_by=by, read=True, seen=True, acked=True)
        return True

    def acknowledge(self, nid):
        self.lines[nid]["acked"] = True

    def why(self, nid):
        l = self.lines[nid]
        k = KINDS[l["kind"]]
        allowed = "a security or safety notice that cannot be turned off" if not k["can_turn_off"] else f"your {k['area']} notification setting"
        return {"event": k["trigger"], "because": allowed, "basis": k["basis"]}

    # ---- repeats, escalation, offline
    def tick(self, now, escalate_after=None):
        """Critical repeats until acknowledged; high and critical that nobody acted on go to the next role."""
        out = []
        for l in list(self.lines.values()):
            if l["acked"] or l["cleared"] or l["done_by"]:
                continue
            if l["priority"] == "critical" and now - l["at"] >= REPEAT_S:
                for c in KINDS[l["kind"]]["channels"]:
                    if c != "bell":
                        self.sender.deliver(c, l["person"], l["kind"], "en")
                l["at"] = now
                out.append(("repeated", l["nid"]))
            limit = (escalate_after or {}).get(l["role"], ESCALATE_DEFAULT_S)
            if l["priority"] in ("high", "critical") and not l["escalated"] and l["role"] in NEXT_ROLE and now - l["first_at"] >= limit:
                l["escalated"] = True
                out.append(("escalated", l["nid"], NEXT_ROLE[l["role"]]))
        return out

    def reconnect(self, person):
        """Deliver a backlog after being offline: only the newest line per record, so nobody is flooded."""
        nids = self.backlog.pop(person, [])
        newest = {}
        for nid in nids:
            l = self.lines[nid]
            newest[(l["kind"], l["record"] or nid)] = nid
        return [self.lines[n] for n in dict.fromkeys(newest.values())]
