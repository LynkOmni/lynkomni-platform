#!/usr/bin/env python3
"""Builds contract version 5 from version 4 (MASTER UPDATE, owner locked 2026-11-10, master blueprint section 61).

Version 5 adds the LynkVCard card request and the partner's answer, for the three card groups (prepaid, debit, credit) on the
four faces. The request is made only online (a class C command); the device records the request and only the cloud records
the issuer's, account partner's or lender's answer. No event carries a card number, a security code, an expiry date, income
figures or a balance: the form's details go to the licensed partner directly. A credit limit appears only as the integer
amount the lender granted, with its currency.

The command register also corrects one leftover: after a device's offline limit, cash selling continues and everything else
waits until it signs in again (MASTER UPDATE section 55); version 4 said selling pauses.

Nothing in an older event changes: version 4 events read as version 5 as they are (upcaster 4 to 5 only raises the version).

    python3 contract/tools/build_v5.py          writes contract/event-payloads.v5.json and contract/command-policy-register.v5.json
    python3 contract/tools/build_v5.py --check  fails when either file is out of date (tests/test_contract_v5.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U7, U = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/uuid"}
INT0 = {"type": "integer", "minimum": 0}
CUR = {"$ref": "#/$defs/currency"}
GROUPS = ("prepaid", "debit", "credit")
TIERS = ("edge", "hub", "core", "omni")


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note):
    return {"origins": origins, "since": "v5", "blueprint": "61", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


EVENTS = {
    "CardRequested": ev(["device"], ["request_id", "card_group", "tier", "form", "holder"],
                        {"request_id": U7, "card_group": enum(*GROUPS), "tier": enum(*TIERS), "form": enum("virtual", "physical"),
                         "holder": enum("self", "business", "staff", "vehicle", "purpose"), "credit_kind": enum("secured", "charge", "credit"),
                         "identity_check_id": U},
                        "A person asked for a card of one group, online only. The form's details (load amount, account, income, consent) go to the licensed partner directly and never into an event."),
    "CardRequestConfirmed": ev(["server"], ["request_id", "card_id", "partner_kind"],
                               {"request_id": U, "card_id": U, "partner_kind": enum("issuer", "account_partner", "lender"),
                                "credit_limit": INT0, "currency": CUR},
                               "Cloud only: the licensed partner issued the card. For a credit card, credit_limit is the integer amount the lender granted."),
    "CardRequestFailed": ev(["server"], ["request_id", "reason"],
                            {"request_id": U, "reason": enum("identity_not_confirmed", "partner_declined", "coming_to_country", "deposit_not_received", "cancelled")},
                            "Cloud only: the partner did not issue the card, with the reason shown to the person."),
}

COMMANDS = [{
    "name": "RequestCard", "class": "C", "v5": True, "emits": ["CardRequested"], "permission": None, "any_authenticated": True,
    "channels": ["mobile", "web"],
    "offline": {"allowed": False, "behavior": "refuse_with_reason", "note": "A card request needs the licensed partner, so it is never queued offline."},
    "cloud_may_reject": True, "cloud_outcomes": ["accepted", "rejected_coming_to_country", "rejected_identity_check_needed"],
    "local_rejections": ["offline_not_possible", "session_expired"], "ui_states": ["sent", "confirmed", "failed"]}]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v4 = load("event-payloads.v4.json")
    v5 = copy.deepcopy(v4)
    v5["$id"] = "lynkomni/event-payloads.v5"
    v5["description"] = ("Contract version 5 (MASTER UPDATE, 2026-11-10): version 4 plus the LynkVCard card request and the partner's answer for "
                         "the prepaid, debit and credit groups. No card number, code, expiry, income or balance is ever part of an event. "
                         "Upcaster 4 to 5 in contract/upcasters.v1.json only raises the version.")
    for e in v5["events"].values():
        e["schema_version"] = 5
    for name, e in EVENTS.items():
        if name in v5["events"]:
            raise SystemExit(f"{name} already exists in version 4")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v5["events"][name] = {"schema_version": 5, **e}
    reg = copy.deepcopy(load("command-policy-register.v4.json"))
    reg["$id"] = "lynkomni/command-policy-register.v5"
    reg["description"] = ("Command register version 5 (MASTER UPDATE, 2026-11-10): version 4's commands unchanged plus RequestCard (class C, "
                          "online only). The session policy is corrected: after the offline limit, cash selling continues and the rest waits.")
    reg["session_policy"]["on_expiry"] = "cash_selling_continues_rest_waits_for_sign_in"
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v5.json": v5, "command-policy-register.v5.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v5.py)")
        return 1
    print("contract v5 is current" if check else "wrote contract v5")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
