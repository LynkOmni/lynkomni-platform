"""Notifications and messages of the Business app and LynkPOS devices (MASTER UPDATE, master blueprint sections 56 and 62;
build section 3). Everything goes through the message register (catalog/messages.v1.json) and services/messages.py.

- Role routing and "Done by": a business notice goes to the people whose role the register names (stock to stock staff,
  a staff request to the owner, a failed sale to the cashier who made it); when one person acts, the same line clears for
  everyone it went to with "Done by", and high or critical notices nobody acted on move to the next role.
- The owner's thresholds: when low stock, a cash difference, or an act above a staff member's limit is worth telling. The
  owner sets them; nobody else can, and only the owner hears about a change.
- Receipts and documents by message: only when the customer asks, by email or text, to a contact held as a personal-details
  vault reference; the message carries the record number and a lynkomni.com link, never a card number or a secret.
- The owner's summary: daily or weekly, by the channel and at the time the owner picks, and only with the owner's consent
  (opt-in): sales, cash expected and counted, stock to reorder and what needs attention. Money is integer minor units with
  the currency code.
- The device's own offline bell: a device raises its own lines while offline (folded by kind, never more than one line per
  kind and record), and on reconnecting merges them with the cloud's, so nothing shows twice."""
import time, uuid

from identity.device_access import emit_checked
from services.messages import KINDS

THRESHOLDS = {"stock_low_milli": 5000, "cash_difference_minor": 500, "over_limit_minor": 0}
SUMMARY_PERIODS = ("day", "week")
RECEIPT_CHANNELS = ("email", "text")


def _now(n):
    return time.time() if n is None else n


class BusinessNotices:
    def __init__(self, business_id, owner, notifier, emit=None):
        self.business, self.owner, self.n = business_id, owner, notifier
        self.emit_fn = emit or (lambda t, p: None)
        self.thresholds = dict(THRESHOLDS)
        self.people = {owner: "owner"}          # person -> role in this business
        self.summary = None                     # {"period", "channel", "hour", "consent"}

    def emit(self, t, p):
        emit_checked(self.emit_fn, t, p)

    # ------------------------------------------------------------------ people and role routing
    def staff(self, person, role):
        self.people[person] = role

    def route(self, kind, event_id, now=None, facts=None, record=None, person=None, lang_of=None):
        """Send a register kind to everyone whose role the register names (or to one person when the kind is about them)."""
        k = KINDS[kind]
        audience = k["audience"]
        if person is not None:
            targets = [person]
        elif audience == "owner":
            targets = [p for p, r in self.people.items() if r == "owner"]
        else:
            targets = [p for p, r in self.people.items() if r == audience]
        out = []
        for p in targets:
            out.append(self.n.notify(kind, p, event_id, _now(now), facts=facts, record=record, business=self.business,
                                     role=self.people.get(p), lang=(lang_of or {}).get(p, "en")))
        return out

    def done_by(self, nid, person):
        """One person acted: the line clears for everyone it went to, with their name."""
        return self.n.act(nid, person)

    # ------------------------------------------------------------------ the owner's thresholds
    def set_threshold(self, by, name, value):
        if self.people.get(by) != "owner":
            raise PermissionError("only the owner sets notification thresholds")
        if name not in THRESHOLDS or not isinstance(value, int) or value < 0:
            raise ValueError("a threshold is a known name and a whole number of zero or more")
        self.thresholds[name] = value
        self.emit("ThresholdChanged", {"threshold": name, "value": value, "by": by})

    def stock_level(self, product, level_milli, event_id, now=None):
        if level_milli <= self.thresholds["stock_low_milli"]:
            return self.route("stock_low", event_id, now, record=product)
        return []

    def cash_count(self, expected_minor, counted_minor, currency, event_id, now=None):
        diff = counted_minor - expected_minor
        if abs(diff) > self.thresholds["cash_difference_minor"]:
            return self.route("cash_difference", event_id, now, facts={"difference_minor": diff, "currency": currency})
        return []

    def over_limit(self, act, amount_minor, by, event_id, now=None):
        if amount_minor > self.thresholds["over_limit_minor"]:
            return self.route("large_void", event_id, now, facts={"act": act, "amount_minor": amount_minor, "approved_by": by})
        return []

    # ------------------------------------------------------------------ receipts and documents by message
    def send_document(self, kind, record_id, channel, contact_ref, asked_by_customer, by, lang="en", now=None):
        """kind: receipt (LORCP-) or document (LODOC-). Sent only when the customer asked, to a vault reference."""
        if not asked_by_customer:
            raise PermissionError("a receipt or document goes by message only when the customer asks for it")
        if channel not in RECEIPT_CHANNELS:
            raise ValueError("by email or text message; print and QR need no message")
        if not str(contact_ref).startswith("pii_"):
            raise ValueError("the customer's contact is held only as a personal-details vault reference")
        facts = {"record": record_id, "link": f"https://pay.lynkomni.com/r/{record_id}"}
        r = self.n.notify(kind, contact_ref, f"{kind}-{record_id}-{channel}", _now(now), facts=facts, record=record_id,
                          lang=lang, contacts=(channel,), business=self.business)
        self.emit("DocumentSent", {"document_id": record_id, "kind": kind, "channel": channel, "by": by})
        return r

    # ------------------------------------------------------------------ the owner's summary
    def choose_summary(self, by, period, channel, hour, consent):
        if self.people.get(by) != "owner":
            raise PermissionError("only the owner chooses the owner's summary")
        if period not in SUMMARY_PERIODS or channel not in KINDS["owner_summary"]["channels"] or not 0 <= hour <= 23:
            raise ValueError("daily or weekly, by a channel of the register, at an hour of the day")
        self.summary = {"period": period, "channel": channel, "hour": hour, "consent": consent is True}

    @staticmethod
    def build_summary(sales, cash, stock, attention, currency):
        """sales: [amount_minor]; cash: (expected_minor, counted_minor or None); stock: [(product, level_milli, threshold_milli)];
        attention: [notice titles]. Integers only."""
        return {"sales_count": len(sales), "sales_minor": sum(sales), "currency": currency,
                "cash_expected_minor": cash[0], "cash_counted_minor": cash[1],
                "to_reorder": sorted(p for p, lvl, th in stock if lvl <= th), "needs_attention": len(attention)}

    def send_summary(self, facts, period_key, now=None):
        if not self.summary or not self.summary["consent"]:
            return {"state": "refused", "reason": "no_opt_in"}
        r = self.n.notify("owner_summary", self.owner, f"summary-{period_key}", _now(now), facts=facts, consent=True,
                          contacts=(self.summary["channel"],), business=self.business, role="owner")
        self.emit("OwnerSummaryBuilt", {"business_id": self.business, "period": self.summary["period"], "channel": self.summary["channel"]})
        return r


class DeviceBell:
    """A device's own bell while it is offline: lines from what the device itself sees (sync waiting, printer, low stock on
    this device, a queued LynkAssist action), folded by kind and record, kept on the device and merged on reconnect."""

    def __init__(self, device_id):
        self.device = device_id
        self.lines = {}                         # (kind, record) -> line

    def raise_(self, kind, event_id, title, record=None, now=None):
        if kind not in KINDS:
            raise KeyError(f"{kind} is not in the message register")
        key = (kind, record)
        l = self.lines.get(key)
        if l:
            l.update(count=l["count"] + 1, at=_now(now), read=False, events=l["events"] + [event_id])
            return l
        l = {"nid": uuid.uuid4().hex, "kind": kind, "title": title, "record": record, "at": _now(now), "count": 1,
             "read": False, "events": [event_id], "origin": "device", "priority": KINDS[kind]["priority"]}
        self.lines[key] = l
        return l

    def unread(self):
        return sorted((l for l in self.lines.values() if not l["read"]), key=lambda l: (["critical", "high", "normal", "low"].index(l["priority"]), -l["at"]))

    def read(self, nid):
        for l in self.lines.values():
            if l["nid"] == nid:
                l["read"] = True

    def merge(self, cloud_lines):
        """On reconnect: the cloud's lines and the device's own, one per event; a line the cloud already has is not shown twice."""
        seen = {e for l in cloud_lines for e in l.get("events", [])}
        own = [l for l in self.lines.values() if not set(l["events"]) & seen]
        return list(cloud_lines) + own
