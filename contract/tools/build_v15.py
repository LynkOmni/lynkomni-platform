#!/usr/bin/env python3
"""Builds contract version 15 from version 14 (build section 4, step E4b: LynkExchange in the office services, EXCHANGE UPDATE,
master blueprint 65; core/exchange.py).

Version 15 adds the steps of an exchange order through the licensed partner (placed, the partner received the money, failed,
refunded) beside the existing ExchangeSettled, and the proof of exchange kept in LynkFiles. Every one is written by the cloud alone:
nothing about an exchange is ever queued offline, and money facts come only from the partner's confirmation. A practice order says
so and never moves money.

What is never in an event: a payee's name, bank account or contact, an identity document, or the safety word.

Nothing older changes: version 14 events read as version 15 as they are (upcaster 14 to 15 only raises the version).

    python3 contract/tools/build_v15.py          writes contract/event-payloads.v15.json and contract/command-policy-register.v15.json
    python3 contract/tools/build_v15.py --check  fails when either file is out of date (tests/test_contract_v15.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U7, SHA = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/sha256"}
INT0 = {"type": "integer", "minimum": 0}
BOOL = {"type": "boolean"}
MONEY, CUR, PREF = {"$ref": "#/$defs/money"}, {"$ref": "#/$defs/currency"}, {"$ref": "#/$defs/provider_ref"}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note):
    return {"origins": origins, "since": "v15", "blueprint": "65 LynkExchange", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S = ["server"]
KIND = enum("convert", "send", "invoice_in", "bill_out")
EVENTS = {
    "ExchangeOrderPlaced": ev(S, ["order_id", "kind", "amount", "currency", "to_currency", "part_bps", "practice"],
        {"order_id": U7, "kind": KIND, "amount": MONEY, "currency": CUR, "to_currency": CUR, "part_bps": {"type": "integer", "minimum": 0, "maximum": 9999},
         "practice": BOOL, "for_id": U7},
        "Cloud only: an exchange order was placed with the licensed partner at one full price (LynkOmni's part in basis points). for_id names the LynkInv invoice or LynkAcc bill it pays. A practice order never moves money."),
    "ExchangeOrderPaid": ev(S, ["order_id", "provider_reference"],
        {"order_id": U7, "provider_reference": PREF},
        "Cloud only: the licensed partner confirmed it received the money for the order."),
    "ExchangeOrderFailed": ev(S, ["order_id", "reason"],
        {"order_id": U7, "reason": enum("partner_refused", "price_expired", "identity_check", "limit", "cancelled")},
        "Cloud only: the order did not go through; the partner alone decides a refusal."),
    "ExchangeRefunded": ev(S, ["order_id", "amount", "currency", "provider_reference"],
        {"order_id": U7, "amount": MONEY, "currency": CUR, "provider_reference": PREF},
        "Cloud only: the licensed partner confirmed it sent the money back."),
    "ExchangeProofIssued": ev(S, ["order_id", "document_id", "code_sha256"],
        {"order_id": U7, "document_id": U7, "code_sha256": SHA},
        "Cloud only: a proof of exchange was kept in LynkFiles with a code anyone can check; the code itself is never in the event."),
}
COMMANDS = []


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v15 = copy.deepcopy(load("event-payloads.v14.json"))
    v15["$id"] = "lynkomni/event-payloads.v15"
    v15["description"] = ("Contract version 15 (build section 4, step E4b): version 14 plus LynkExchange's order steps (65): placed, paid to the "
                          "licensed partner, failed, refunded, beside the existing ExchangeSettled, and the proof of exchange. All are cloud only; a payee's name, "
                          "bank account or contact is never in an event. LynkCRM's CustomerRecordCreated also takes the kind payee. Upcaster 14 to 15 in contract/upcasters.v1.json only raises the version.")
    for e in v15["events"].values():
        e["schema_version"] = 15
    # LynkCRM's record kind "payee" (payees in LynkCRM, 65.9) joins CustomerRecordCreated here; version 11 keeps its list.
    kinds = v15["events"]["CustomerRecordCreated"]["payload"]["properties"]["kind"]["enum"]
    if "payee" not in kinds:
        v15["events"]["CustomerRecordCreated"]["payload"]["properties"]["kind"]["enum"] = sorted(kinds + ["payee"])
        v15["events"]["CustomerRecordCreated"]["note"] += " Version 15 adds the kind payee (LynkExchange payees)."
    for name, e in EVENTS.items():
        if name in v15["events"]:
            raise SystemExit(f"{name} already exists in version 14")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v15["events"][name] = {"schema_version": 15, **e}
    reg = copy.deepcopy(load("command-policy-register.v14.json"))
    reg["$id"] = "lynkomni/command-policy-register.v15"
    reg["description"] = ("Command register version 15 (build section 4, step E4b): version 14's commands unchanged. LynkExchange adds no device "
                          "command: nothing about an exchange is queued offline.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v15.json": v15, "command-policy-register.v15.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v15.py)")
        return 1
    print("contract v15 is current" if check else "wrote contract v15")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
