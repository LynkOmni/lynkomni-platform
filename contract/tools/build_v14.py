#!/usr/bin/env python3
"""Builds contract version 14 from version 13 (build section 4, step E4a: LynkBooking's money and figures in the office services,
BOOKING UPDATE, master blueprint 64; core/booking.py).

Version 14 adds the facts the office services need from a booking: confirmed (with its kind, where it came from, when and its total),
paid through the provider (in full, a deposit or the balance), checked in, cancelled, nobody came, refunded, and LynkOmni's commission.
Checking in and cancelling at the front desk may come from a device, offline; everything else is written by the cloud alone, and a
payment or refund only when the provider confirms.

What is never in an event: a customer's name or contact, a ticket's code or an address. A customer appears only as their LynkCRM
record's internal id, and only when the business keeps one.

Nothing older changes: version 13 events read as version 14 as they are (upcaster 13 to 14 only raises the version).

    python3 contract/tools/build_v14.py          writes contract/event-payloads.v14.json and contract/command-policy-register.v14.json
    python3 contract/tools/build_v14.py --check  fails when either file is out of date (tests/test_contract_v14.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))
from core.booking import KINDS, SOURCES  # noqa: E402
U, U7 = {"$ref": "#/$defs/uuid"}, {"$ref": "#/$defs/uuid7"}
INT1 = {"type": "integer", "minimum": 1}
BOOL, TS = {"type": "boolean"}, {"$ref": "#/$defs/timestamp_utc"}
MONEY, CUR, PREF = {"$ref": "#/$defs/money"}, {"$ref": "#/$defs/currency"}, {"$ref": "#/$defs/provider_ref"}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note):
    return {"origins": origins, "since": "v14", "blueprint": "64 LynkBooking", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S, DS = ["server"], ["device", "server"]
EVENTS = {
    "BookingConfirmed": ev(S, ["booking_id", "kind", "place_id", "starts_at", "minutes", "guests", "source", "total", "currency"],
        {"booking_id": U7, "kind": enum(*KINDS), "place_id": U, "starts_at": TS, "minutes": INT1, "guests": INT1, "source": enum(*SOURCES),
         "first_visit": BOOL, "customer_id": U7, "company": BOOL, "total": MONEY, "currency": CUR},
        "Cloud only: a booking was confirmed with its kind, place, time, number of guests, where the customer came from and its total. The customer is only their LynkCRM record's id, when the business keeps one."),
    "BookingPaid": ev(S, ["booking_id", "part", "amount", "currency", "provider_reference"],
        {"booking_id": U7, "part": enum("full", "deposit", "balance"), "amount": MONEY, "currency": CUR, "provider_reference": PREF},
        "Cloud only: the provider confirmed a payment for a booking, in full, a deposit or the balance. Cash at the venue is PaymentRecorded cash_received, as everywhere."),
    "BookingCheckedIn": ev(DS, ["booking_id"],
        {"booking_id": U7},
        "The customer arrived and was checked in, at the front desk or by self check-in; works offline at the desk."),
    "BookingCancelled": ev(DS, ["booking_id", "by", "fee", "currency"],
        {"booking_id": U7, "by": enum("customer", "business"), "fee": MONEY, "currency": CUR},
        "A booking was cancelled, with the fee kept under the cancelling rule shown before booking (zero when none applies)."),
    "BookingNoShow": ev(S, ["booking_id", "fee", "currency"],
        {"booking_id": U7, "fee": MONEY, "currency": CUR},
        "Cloud only: nobody came; the no-show fee kept is only the one shown before booking."),
    "BookingRefunded": ev(S, ["booking_id", "amount", "currency", "provider_reference"],
        {"booking_id": U7, "amount": MONEY, "currency": CUR, "provider_reference": PREF},
        "Cloud only: the provider confirmed a refund for a booking."),
    "BookingCommissionRecorded": ev(S, ["booking_id", "amount", "currency"],
        {"booking_id": U7, "amount": MONEY, "currency": CUR},
        "Cloud only: LynkOmni's commission on a booking LynkBooking brought, taken by the provider from the payout; never on the business's own customers."),
}


def cmd(name, emits, rejections):
    return {"name": name, "class": "A", "v14": True, "emits": emits, "permission": None, "channels": ["mobile", "web", "kiosk"],
            "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
            "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"], "local_only": True}


COMMANDS = [
    cmd("CheckInBooking", ["BookingCheckedIn"], ["booking_not_today", "already_checked_in"]),
    cmd("CancelBookingAtDesk", ["BookingCancelled"], ["booking_already_used"]),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v14 = copy.deepcopy(load("event-payloads.v13.json"))
    v14["$id"] = "lynkomni/event-payloads.v14"
    v14["description"] = ("Contract version 14 (build section 4, step E4a): version 13 plus LynkBooking's facts for the office services (64): a booking "
                          "confirmed, paid through the provider, checked in, cancelled, a no-show, refunded, and LynkOmni's commission. A customer's name or "
                          "contact, a ticket's code or an address is never in an event. Upcaster 13 to 14 in contract/upcasters.v1.json only raises the version.")
    for e in v14["events"].values():
        e["schema_version"] = 14
    for name, e in EVENTS.items():
        if name in v14["events"]:
            raise SystemExit(f"{name} already exists in version 13")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v14["events"][name] = {"schema_version": 14, **e}
    reg = copy.deepcopy(load("command-policy-register.v13.json"))
    reg["$id"] = "lynkomni/command-policy-register.v14"
    reg["description"] = ("Command register version 14 (build section 4, step E4a): version 13's commands unchanged plus checking in and cancelling a "
                          "booking at the front desk, which a device may do offline. Confirming, payments, no-shows, refunds and commission are written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v14.json": v14, "command-policy-register.v14.json": reg}


def main(check=False):
    stale = []
    for name, data in build().items():
        text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
        path = os.path.join(ROOT, name)
        if check:
            if not os.path.isfile(path) or open(path, encoding="utf-8").read() != text:
                stale.append(name)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
    if stale:
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v14.py)")
        return 1
    print("contract v14 is current" if check else "wrote contract v14")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
