#!/usr/bin/env python3
"""Builds contract version 9 from version 8 (build section 4, step A2: the events the section 4 links of catalog/connections.v1.json
need; master blueprint 66, 68.14, 71.3 and 79.10).

Version 9 adds nine events. The cloud alone writes that an invoice or a credit note is issued (an issued invoice never changes; the
fix is a credit note), that a period is closed, that a card was sent into a customer conversation, that a merchant's ad earnings
were recorded (validated impressions only), that a vote's roll was imported with the organisation's consent and that an exchange
was settled by the licensed partner. A device may also write two of them: moving a deal to another stage (field sales work offline)
and filing a document under its record. No card number, PIN, position or a person's name is ever in an event; money is integer
minor units with its currency.

Nothing in an older event changes: version 8 events read as version 9 as they are (upcaster 8 to 9 only raises the version).

    python3 contract/tools/build_v9.py          writes contract/event-payloads.v9.json and contract/command-policy-register.v9.json
    python3 contract/tools/build_v9.py --check  fails when either file is out of date (tests/test_contract_v9.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U7, U = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/uuid"}
MONEY, CUR, PERIOD, DATE = {"$ref": "#/$defs/money"}, {"$ref": "#/$defs/currency"}, {"$ref": "#/$defs/period"}, {"$ref": "#/$defs/date"}
NOTE, SHA, PREF = {"$ref": "#/$defs/note"}, {"$ref": "#/$defs/sha256"}, {"$ref": "#/$defs/provider_ref"}
INT0 = {"type": "integer", "minimum": 0}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note, part):
    return {"origins": origins, "since": "v9", "blueprint": part, "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S, DS = ["server"], ["device", "server"]
RECORDS = ("customer", "invoice", "bill", "expense", "staff", "project", "property", "school", "deal", "other")
EVENTS = {
    "InvoiceIssued": ev(S, ["invoice_id", "total", "currency", "issued_on"],
        {"invoice_id": U7, "customer_id": U7, "quote_id": U7, "total": MONEY, "currency": CUR, "issued_on": DATE, "due_on": DATE},
        "Cloud only: LynkInv issued an invoice (public id LOINV-; the printed number is a separate series). It never changes after this; the fix is a credit note.", "66 LynkInv"),
    "CreditNoteIssued": ev(S, ["credit_note_id", "invoice_id", "total", "currency"],
        {"credit_note_id": U7, "invoice_id": U7, "total": MONEY, "currency": CUR, "reason": NOTE},
        "Cloud only: a credit note corrects an issued invoice (an LOINV- record of kind credit_note with its own printed series).", "66 LynkInv"),
    "PeriodClosed": ev(S, ["period", "by"], {"period": PERIOD, "by": enum("owner", "accountant")},
        "Cloud only: the period is locked in LynkAcc; later changes go into the next open period.", "66 LynkAcc"),
    "DealStageChanged": ev(DS, ["deal_id", "stage"],
        {"deal_id": U7, "stage": enum("new", "qualified", "proposal", "won", "lost"), "value": MONEY, "currency": CUR, "customer_id": U7},
        "A deal moved to another stage in LynkCRM; field sales can do it offline and it syncs later.", "66 LynkCRM"),
    "ConversationCardSent": ev(S, ["conversation_id", "card", "record_id"],
        {"conversation_id": U7, "card": enum("invoice", "quote", "receipt", "statement", "report", "tracker"), "record_id": U7},
        "Cloud only: a card from its own service (an invoice with its pay link, a quote, a receipt) was sent into a customer conversation (LOCNV-); the card follows its service's rules and states.", "74 CHAT UPDATE"),
    "AdEarningsRecorded": ev(S, ["period", "amount", "currency", "impressions"],
        {"period": PERIOD, "amount": MONEY, "currency": CUR, "impressions": INT0},
        "Cloud only: a merchant's share of ad earnings for a period, from validated impressions only (at least half on screen for a second); posted to LynkAcc as income. Placeholders until legal sign-off.", "79 ADS UPDATE"),
    "DocumentFiled": ev(DS, ["document_id", "kind", "record_kind", "record_id", "sha256"],
        {"document_id": U7, "kind": enum("bill", "receipt", "statement", "contract", "minutes", "certificate", "other"),
         "record_kind": enum(*RECORDS), "record_id": U7, "sha256": SHA},
        "A file kept in LynkFiles under the record it belongs to, with that service's access rules; a bill or receipt is read into a draft entry a person confirms.", "69 LynkFiles"),
    "VoteRollImported": ev(S, ["vote_id", "source", "voters", "consent_id"],
        {"vote_id": U7, "source": enum("lynkcrm", "lynkacc", "lynkattend", "upload"), "voters": INT0, "consent_id": U},
        "Cloud only: a vote's roll (LOVOT-) was built from the organisation's members with its recorded consent; only the count is in the event, never a voter's name.", "68 LynkVote"),
    "ExchangeSettled": ev(S, ["order_id", "amount", "currency", "to_amount", "to_currency", "provider_reference"],
        {"order_id": U7, "amount": MONEY, "currency": CUR, "to_amount": MONEY, "to_currency": CUR, "provider_reference": PREF},
        "Cloud only: the licensed partner settled a conversion of amount (in currency) into to_amount (in to_currency); LynkOmni never holds the money. Posts the conversion and any rate gain or loss to LynkAcc.", "65 LynkExchange"),
}


def cmd(name, emits, rejections, permission=None):
    return {"name": name, "class": "A", "v9": True, "emits": emits, "permission": permission, "channels": ["mobile", "web"],
            "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
            "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"], "local_only": True}


COMMANDS = [
    cmd("ChangeDealStage", ["DealStageChanged"], ["deal_closed", "not_your_deal"]),
    cmd("FileDocument", ["DocumentFiled"], ["file_type_not_allowed", "record_not_found"]),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v9 = copy.deepcopy(load("event-payloads.v8.json"))
    v9["$id"] = "lynkomni/event-payloads.v9"
    v9["description"] = ("Contract version 9 (build section 4, step A2): version 8 plus the events of the section 4 links: invoices and credit "
                         "notes issued, a period closed, a deal's stage, a card in a conversation, ad earnings, a filed document, a vote's roll and "
                         "a settled exchange. Upcaster 8 to 9 in contract/upcasters.v1.json only raises the version.")
    for e in v9["events"].values():
        e["schema_version"] = 9
    for name, e in EVENTS.items():
        if name in v9["events"]:
            raise SystemExit(f"{name} already exists in version 8")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v9["events"][name] = {"schema_version": 9, **e}
    reg = copy.deepcopy(load("command-policy-register.v8.json"))
    reg["$id"] = "lynkomni/command-policy-register.v9"
    reg["description"] = ("Command register version 9 (build section 4, step A2): version 8's commands unchanged plus moving a deal and filing a "
                          "document, which work offline. Issuing, closing, settling and importing are written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v9.json": v9, "command-policy-register.v9.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v9.py)")
        return 1
    print("contract v9 is current" if check else "wrote contract v9")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
