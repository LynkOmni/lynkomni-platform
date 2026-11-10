"""The Notifications settings page (MASTER UPDATE, master blueprint section 62; build section 2).

A person's choices, turned into the rules services/messages.py applies. The page offers:
- the grid: each area by channel (bell, phone notification, email, text); security and safety cannot be turned off;
- each business on or off (security always reaches the person);
- mute a kind, or snooze it for a while; do not disturb until a time (critical still breaks through);
- "Pause all optional notifications" in one tap, for holidays;
- the owner's summary: its time and channel;
- the lock screen for each kind: neutral (the default), full or nothing;
- a deputy while away: business notices for the owner's role go to the deputy within the deputy's own role, and the owner
  sees what was handled on return; personal, security and safety notices never go to a deputy;
- "Send me a test" on each channel and a health check that says when a phone has notifications switched off or its push link
  has gone stale, with the fix;
- personal reminders on any record ("remind me to chase this invoice on Friday"), which arrive as a normal notification and can
  be snoozed or cleared.
Nothing here can switch off a kind the register says cannot be turned off."""
import time, uuid
from services.messages import KINDS, PERSONAL_AREAS, REG

CHANNELS = ("bell", "push", "email", "text")
LOCKED_AREAS = ("security", "safety")
STALE_PUSH_DAYS = 30
MAX_SNOOZE_HOURS = 7 * 24
MAX_DEPUTY_DAYS = 90


def _now(n):
    return time.time() if n is None else n


class Settings:
    def __init__(self, notifier, emit=None):
        self.n, self.emit = notifier, emit or (lambda person, type_, payload, now=None: None)
        self.s, self.reminders = {}, {}

    def of(self, person):
        return self.s.setdefault(person, {"grid": {}, "businesses_off": set(), "muted": set(), "snoozed": {}, "dnd_until": 0, "pause_optional": False,
                                          "summary": {"time": "18:00", "channel": "bell"}, "lock_screen": {}, "deputy": None})

    # ---- the grid, businesses, mute, snooze, do not disturb, pause all
    def set_channel(self, person, area, channel, on):
        if channel not in CHANNELS:
            raise ValueError("a channel is bell, push, email or text")
        if area in LOCKED_AREAS and not on:
            raise PermissionError(f"{area} notices cannot be turned off")
        g = self.of(person)["grid"].setdefault(area, set(CHANNELS))
        (g.add if on else g.discard)(channel)

    def set_business(self, person, business, on):
        (self.of(person)["businesses_off"].discard if on else self.of(person)["businesses_off"].add)(business)

    def mute(self, person, kind, on=True):
        if not KINDS[kind]["can_turn_off"]:
            raise PermissionError(f"{kind} cannot be turned off")
        (self.of(person)["muted"].add if on else self.of(person)["muted"].discard)(kind)

    def snooze(self, person, kind, hours, now=None):
        if not KINDS[kind]["can_turn_off"]:
            raise PermissionError(f"{kind} cannot be snoozed")
        if not 1 <= hours <= MAX_SNOOZE_HOURS:
            raise ValueError("snooze for 1 hour to 7 days")
        self.of(person)["snoozed"][kind] = _now(now) + hours * 3600

    def do_not_disturb(self, person, until):
        self.of(person)["dnd_until"] = until

    def pause_all_optional(self, person, on):
        self.of(person)["pause_optional"] = bool(on)

    def set_summary(self, person, at, channel):
        if channel not in CHANNELS:
            raise ValueError("a channel is bell, push, email or text")
        h, m = (int(x) for x in at.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError("a time is HH:MM")
        self.of(person)["summary"] = {"time": f"{h:02d}:{m:02d}", "channel": channel}

    def set_lock_screen(self, person, kind, mode):
        if mode not in REG["lock_screen"]:
            raise ValueError("neutral, full or none")
        self.of(person)["lock_screen"][kind] = mode

    # ---- the deputy
    def set_deputy(self, person, deputy, role, until, now=None):
        if deputy == person:
            raise ValueError("choose someone else")
        if role not in ("manager", "cashier", "accountant", "stock_staff"):
            raise ValueError("a deputy keeps their own role; it is never owner")
        if until <= _now(now) or until - _now(now) > MAX_DEPUTY_DAYS * 86400:
            raise ValueError("a deputy is named for up to 90 days")
        self.of(person)["deputy"] = {"person": deputy, "role": role, "until": until}
        self.emit(person, "DeputyNamed", {"deputy": deputy, "role": role, "until": int(until)}, now)

    def end_deputy(self, person):
        self.of(person)["deputy"] = None
        return self.n.while_away(person)

    # ---- what the engine applies
    def prefs(self, person, now=None):
        st = self.of(person)
        n = _now(now)
        muted = set(st["muted"]) | {k for k, until in st["snoozed"].items() if until > n}
        grid = {a: sorted(c) for a, c in st["grid"].items() if a not in LOCKED_AREAS}
        return {"muted": muted, "paused_optional": st["pause_optional"], "dnd_until": st["dnd_until"], "channels": grid,
                "businesses_off": set(st["businesses_off"]), "lock_screen": dict(st["lock_screen"]), "deputy": st["deputy"]}

    # ---- test and health check
    def send_test(self, person, channel, lang="en"):
        """'Send me a test': one message on that channel, so the person sees it arrive."""
        if channel not in CHANNELS:
            raise ValueError("a channel is bell, push, email or text")
        ok = channel == "bell" or self.n.sender.deliver(channel, person, "test", lang)
        return {"channel": channel, "delivered": bool(ok)}

    @staticmethod
    def health(devices, contacts):
        """Problems with how notices reach the person, each with its fix. devices: [{"name", "push_allowed", "push_link_age_days"}]."""
        out = []
        for d in devices:
            if not d.get("push_allowed", True):
                out.append({"problem": "push_off", "device": d["name"], "fix": "open_phone_settings"})
            elif d.get("push_link_age_days", 0) > STALE_PUSH_DAYS:
                out.append({"problem": "push_stale", "device": d["name"], "fix": "open_the_app"})
        if not contacts.get("email") and not contacts.get("phone"):
            out.append({"problem": "no_contact", "fix": "add_contact"})
        return out

    # ---- personal reminders
    def remind(self, person, record, at, note_key="reminder", now=None):
        if at <= _now(now):
            raise ValueError("a reminder is set for later")
        rid = uuid.uuid4().hex
        self.reminders[rid] = {"person": person, "record": record, "at": at, "note": note_key, "state": "set"}
        self.emit(person, "ReminderSet", {"reminder_id": rid, "record": record, "at": int(at)}, now)
        return rid

    def snooze_reminder(self, rid, until):
        self.reminders[rid].update(at=until, state="set")

    def clear_reminder(self, rid):
        self.reminders[rid]["state"] = "cleared"

    def due(self, now=None):
        """Runs on a schedule: each due reminder arrives as a normal notification, then waits to be snoozed or cleared."""
        out = []
        for rid, r in self.reminders.items():
            if r["state"] == "set" and r["at"] <= _now(now):
                r["state"] = "sent"
                self.emit(r["person"], "ReminderDue", {"reminder_id": rid, "record": r["record"]}, now)
                out.append(self.n.notify("personal_reminder", r["person"], f"reminder:{rid}:{int(r['at'])}", _now(now), record=r["record"], prefs=self.prefs(r["person"], now)))
        return out


assert set(PERSONAL_AREAS) >= set(LOCKED_AREAS)
