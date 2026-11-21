#!/usr/bin/env python3
"""Builds contract version 16 from version 15 (build section 4, step F, row 67.17: the office side of gift cards, store credit,
deposits, matching and payment costs, SERVICES UPDATE 67.2 and 67.8; core/office_money.py, catalog/office-money.v1.json).

Version 16 adds what a device records when it sells or tops up a gift card, gives store credit, takes a deposit or settles one (all
work offline and are never blocked), and what the cloud alone writes from the licensed provider: a deposit refunded electronically,
each payment's settlement with its costs, a payment matched to its sale, invoice or booking, and the provider's payouts. A balance
spent below nothing is flagged for the owner, never blocked. VoucherRedeemed (since version 2) spends a gift card or store credit.

What is never in an event: a card's printed code or PIN, a customer's name or contact, a bank account.

Nothing older changes: version 15 events read as version 16 as they are (upcaster 15 to 16 only raises the version).

    python3 contract/tools/build_v16.py          writes contract/event-payloads.v16.json and contract/command-policy-register.v16.json
    python3 contract/tools/build_v16.py --check  fails when either file is out of date (tests/test_contract_v16.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U7, UU = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/uuid"}
BOOL = {"type": "boolean"}
MONEY, SIGNED, CUR, PREF, DATE = ({"$ref": "#/$defs/money"}, {"$ref": "#/$defs/money_signed"}, {"$ref": "#/$defs/currency"},
                                  {"$ref": "#/$defs/provider_ref"}, {"$ref": "#/$defs/date"})


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note, bp="67 SERVICES UPDATE"):
    return {"origins": origins, "since": "v16", "blueprint": bp, "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S, D = ["server"], ["device"]
METHOD = enum("cash", "mobile_money", "bank_transfer", "card", "other")
EVENTS = {
    "GiftCardSold": ev(D, ["card_id", "amount", "currency", "method", "top_up"],
        {"card_id": UU, "amount": MONEY, "currency": CUR, "method": METHOD, "top_up": BOOL, "provider_reference": PREF},
        "A gift card was sold or topped up at the till or online. The money is owed to the holder (LynkAcc 2200), never held by LynkOmni. Works offline; an electronic payment is in the clearing account until the provider confirms it."),
    "StoreCreditIssued": ev(["device", "server"], ["credit_id", "customer_id", "amount", "currency", "reason"],
        {"credit_id": UU, "customer_id": UU, "amount": MONEY, "currency": CUR, "reason": enum("return", "cashback", "goodwill"), "sale_id": UU},
        "Store credit was given to a customer for a return, as cashback or as goodwill; it is owed to the customer (LynkAcc 2510). VoucherRedeemed spends it."),
    "DepositTaken": ev(D, ["deposit_id", "for", "amount", "currency", "method"],
        {"deposit_id": U7, "for": enum("pre_order", "special_order", "rental", "layaway"), "ref_id": UU, "amount": MONEY, "currency": CUR, "method": METHOD,
         "provider_reference": PREF},
        "A deposit was taken for a pre-order, a special order, a rental or a layaway; it is received in advance (LynkAcc 2500) until it settles. Works offline; never blocked."),
    "DepositSettled": ev(D, ["settlement_id", "deposit_id", "outcome", "amount", "currency"],
        {"settlement_id": U7, "deposit_id": UU, "outcome": enum("applied", "kept", "returned_cash"), "amount": MONEY, "currency": CUR},
        "A deposit (or part of it) was used for the sale, kept under terms shown before paying, or returned in cash. An electronic return is DepositRefunded, written by the cloud."),
    "DepositRefunded": ev(S, ["deposit_id", "amount", "currency", "provider_reference"],
        {"deposit_id": UU, "amount": MONEY, "currency": CUR, "provider_reference": PREF},
        "Cloud only: the provider confirmed it returned a deposit electronically."),
    "StoredValueConflictFlagged": ev(S, ["voucher_id", "held", "currency"],
        {"voucher_id": UU, "held": SIGNED, "currency": CUR},
        "Cloud only: a gift card or store credit was spent below nothing (sales made offline are never blocked); shown to the owner, nothing is posted twice."),
    "PaymentSettled": ev(S, ["provider_reference", "amount", "currency", "provider_fee", "lynkomni_part", "settled_on"],
        {"provider_reference": PREF, "amount": MONEY, "currency": CUR, "provider_fee": MONEY, "lynkomni_part": MONEY, "settled_on": DATE, "payout_id": UU},
        "Cloud only: a line of the provider's settlement report: the payment, the provider's fee and LynkOmni's part, as the provider reports them (LynkAcc 6100)."),
    "PaymentMatched": ev(S, ["provider_reference", "target", "target_id", "how"],
        {"provider_reference": PREF, "target": enum("sale", "invoice", "booking"), "target_id": UU, "how": enum("reference", "confirmed", "automatic")},
        "Cloud only: a provider's payment was matched to its sale, invoice or booking: by its reference, confirmed by a person, or by the Plus automation (undoable)."),
    "PaymentMatchUndone": ev(S, ["provider_reference"], {"provider_reference": PREF},
        "Cloud only: a match was undone; the payment is listed as unmatched again."),
    "ProviderPayoutScheduled": ev(S, ["payout_id", "expected_on", "amount", "currency"],
        {"payout_id": U7, "expected_on": DATE, "amount": MONEY, "currency": CUR},
        "Cloud only: the provider said when a payout will arrive in the shop's own bank or wallet."),
    "ProviderPayoutArrived": ev(S, ["payout_id", "amount", "currency", "provider_reference"],
        {"payout_id": UU, "amount": MONEY, "currency": CUR, "provider_reference": PREF},
        "Cloud only: the provider confirmed the payout was paid (LynkAcc 1020 from 1010)."),
}


def cmd(name, emits, rejections):
    return {"name": name, "class": "A", "v16": True, "emits": emits, "permission": None, "channels": ["mobile", "web"],
            "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
            "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"], "local_only": True}


COMMANDS = [
    cmd("SellGiftCard", ["GiftCardSold"], ["amount_missing"]),
    cmd("IssueStoreCredit", ["StoreCreditIssued"], ["amount_missing", "customer_missing"]),
    cmd("TakeDeposit", ["DepositTaken"], ["amount_missing"]),
    cmd("SettleDeposit", ["DepositSettled"], ["amount_over_deposit", "deposit_missing"]),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v16 = copy.deepcopy(load("event-payloads.v15.json"))
    v16["$id"] = "lynkomni/event-payloads.v16"
    v16["description"] = ("Contract version 16 (build section 4, step F, row 67.17): version 15 plus the office side of gift cards, store credit, "
                          "deposits, matching and payment costs (67.2, 67.8): four device events that work offline and are never blocked, and the "
                          "provider's facts written by the cloud alone. A card's code or PIN, a customer's name or contact and a bank account are never "
                          "in an event. Upcaster 15 to 16 in contract/upcasters.v1.json only raises the version.")
    for e in v16["events"].values():
        e["schema_version"] = 16
    for name, e in EVENTS.items():
        if name in v16["events"]:
            raise SystemExit(f"{name} already exists in version 15")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v16["events"][name] = {"schema_version": 16, **e}
    reg = copy.deepcopy(load("command-policy-register.v15.json"))
    reg["$id"] = "lynkomni/command-policy-register.v16"
    reg["description"] = ("Command register version 16 (build section 4, step F, row 67.17): version 15's commands plus selling a gift card, "
                          "giving store credit, taking a deposit and settling one, all class A: they work offline and the cloud never rejects them.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v16.json": v16, "command-policy-register.v16.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v16.py)")
        return 1
    print("contract v16 is current" if check else "wrote contract v16")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
