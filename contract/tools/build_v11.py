#!/usr/bin/env python3
"""Builds contract version 11 from version 10 (build section 4, step D2b: the LynkAcc and LynkInv events of OFFICE UPDATE,
master blueprint 66; catalog/books.v1.json and catalog/invoices.v1.json).

Version 11 adds the facts of bills to pay, expense claims, assets, journals, documents and getting paid. A device may record a
bill (by hand or from a photo), submit an expense claim, record a customer's promise to pay and mark a dispute: those work
offline and send in order, never doubled. The cloud alone writes what needs the rules, a second person or a provider:
approvals, a payment the provider confirmed, loss of value, a journal, the documents it issues, reminders, write-offs, credit
balances, instalment plans, subscription changes and an e-invoice's answer from the tax office's network.

What is never in an event: a name, a bank account or card number, a tax number, an address, a receipt photo (it lives in the
document store; the event carries its sha256), or a message's text.

Nothing older changes: version 10 events read as version 11 as they are (upcaster 10 to 11 only raises the version).

    python3 contract/tools/build_v11.py          writes contract/event-payloads.v11.json and contract/command-policy-register.v11.json
    python3 contract/tools/build_v11.py --check  fails when either file is out of date (tests/test_contract_v11.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(os.path.dirname(ROOT), "catalog")
with open(os.path.join(CAT, "books.v1.json"), encoding="utf-8") as _f:
    BOOKS = json.load(_f)
with open(os.path.join(CAT, "invoices.v1.json"), encoding="utf-8") as _f:
    INV = json.load(_f)
with open(os.path.join(CAT, "crm.v1.json"), encoding="utf-8") as _f:
    CRM = json.load(_f)
# Frozen as published in version 11: later kinds (the payee of version 15) join only in their own contract version.
CRM_KINDS = sorted({k for ks in CRM["kinds"].values() for k in ks if k != "payee"} | {"own_kind"})
U7, SHA, MONEY, SMONEY = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/sha256"}, {"$ref": "#/$defs/money"}, {"$ref": "#/$defs/money_signed"}
CUR, DATE, PERIOD = {"$ref": "#/$defs/currency"}, {"$ref": "#/$defs/date"}, {"$ref": "#/$defs/period"}
INT0, INT1 = {"type": "integer", "minimum": 0}, {"type": "integer", "minimum": 1}
ACCOUNT = {"type": "string", "pattern": "^[0-9]{4}$", "description": "A global account code of the chart of accounts."}
ROLE = {"enum": ["owner", "manager", "accountant", "staff"]}
DIMS = {"type": "object", "additionalProperties": False, "properties": {k: U7 for k in BOOKS["dimensions"]["kinds"]}}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note, blueprint):
    return {"origins": origins, "since": "v11", "blueprint": blueprint, "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S, DS = ["server"], ["device", "server"]
ACC, IV, CR = "66 LynkAcc", "66 LynkInv", "66 LynkCRM"
LINES = {"type": "array", "minItems": 2, "maxItems": 500, "items": {"type": "object", "additionalProperties": False, "required": ["account", "debit", "credit"],
         "properties": {"account": ACCOUNT, "debit": MONEY, "credit": MONEY, "dims": DIMS}}}
EVENTS = {
    # ---- LynkAcc ------------------------------------------------------------------------------------------------------------
    "BillRecorded": ev(DS, ["bill_id", "source", "total", "currency"],
        {"bill_id": U7, "supplier_id": U7, "source": enum(*BOOKS["bills"]["sources"]), "total": MONEY, "currency": CUR, "account": ACCOUNT,
         "due_on": DATE, "order_id": U7, "document_sha256": SHA, "dims": DIMS},
        "A supplier bill was entered (by hand, photo, email or e-invoice) into Bills to pay. A photo or file stays in the document store; the event carries its sha256. It waits for approval before any payment.", ACC),
    "BillApproved": ev(S, ["bill_id", "step", "by"],
        {"bill_id": U7, "step": INT1, "by": ROLE},
        "Cloud only: one approval step of a bill, by amount and department; the person who entered the bill never approves it.", ACC),
    "BillPaymentConfirmed": ev(S, ["bill_id", "amount", "currency", "method"],
        {"bill_id": U7, "amount": MONEY, "currency": CUR, "method": enum("bank", "mobile_money", "cash", "cheque"), "run_id": U7, "provider_reference": {"$ref": "#/$defs/provider_ref"}},
        "Cloud only: a bill (or part of it) is paid. An electronic payment is written only when the licensed provider confirms it; LynkOmni never holds the money.", ACC),
    "ExpenseClaimSubmitted": ev(DS, ["claim_id", "kind", "total", "currency"],
        {"claim_id": U7, "kind": enum(*BOOKS["expenses"]["kinds"]), "total": MONEY, "currency": CUR, "account": ACCOUNT, "distance_thousandths": INT0, "days": INT0,
         "document_sha256": SHA, "dims": DIMS},
        "A staff member submitted an expense claim: a receipt, mileage (distance in thousandths of a kilometre) or daily allowances at the country pack's rate.", ACC),
    "ExpenseClaimApproved": ev(S, ["claim_id", "by"],
        {"claim_id": U7, "by": ROLE, "repaid_by": enum(*BOOKS["expenses"]["repaid_by"])},
        "Cloud only: an expense claim was approved by someone other than the claimant; it is repaid with wages or by payout.", ACC),
    "AssetAdded": ev(S, ["asset_id", "cost", "currency", "method", "years"],
        {"asset_id": U7, "cost": MONEY, "currency": CUR, "residual": MONEY, "method": enum(*BOOKS["assets"]["methods"]), "years": INT1, "rate_bp": INT0, "dims": DIMS},
        "Cloud only: an asset joined the register (public id LOAST-, the same record whether or not LynkMotion tracks it).", ACC),
    "DepreciationPosted": ev(S, ["asset_id", "period", "amount", "currency"],
        {"asset_id": U7, "period": PERIOD, "amount": MONEY, "currency": CUR},
        "Cloud only: the asset's loss of value for a period, from its schedule (the schedule ends exactly at the value left).", ACC),
    "JournalPosted": ev(S, ["journal_id", "kind", "lines", "currency", "prepared_by"],
        {"journal_id": U7, "kind": enum("manual", "reversal", "repeating", "spread", "revaluation", "disposal", "loan_payment", "year_end", "opening_balance", "group", "invoice"),
         "lines": LINES, "currency": CUR, "prepared_by": ROLE, "approved_by": ROLE, "reverses": U7, "period": PERIOD},
        "Cloud only: a balanced journal of named accounts; a sensitive kind is prepared by one person and approved by another; nothing posts on a locked date.", ACC),
    "LockDateSet": ev(S, ["lock_date", "prepared_by", "approved_by"],
        {"lock_date": DATE, "prepared_by": ROLE, "approved_by": ROLE},
        "Cloud only: nothing posts on or before the lock date; moving it back needs two people.", ACC),
    # ---- LynkInv ------------------------------------------------------------------------------------------------------------
    "DocumentIssued": ev(S, ["document_id", "kind"],
        {"document_id": U7, "kind": enum(*[k for k in INV["documents"] if k not in ("invoice", "credit_note")]), "from_id": U7, "total": MONEY, "currency": CUR, "issued_on": DATE},
        "Cloud only: LynkInv issued a document other than an invoice or credit note (those keep InvoiceIssued and CreditNoteIssued): a quote, pro-forma, sales order, delivery note, receipt, debit note, statement of account or a buyer-issued invoice where the law allows. It keeps its public id from core/ids.py and never changes.", IV),
    "InvoiceReminderSent": ev(S, ["invoice_id", "step", "channel"],
        {"invoice_id": U7, "step": enum("before", *[s["step"] for s in INV["reminders"]["steps"]]), "channel": enum("in_app", "chat", "sms", "email", "push")},
        "Cloud only: a reminder went out on a channel the customer agreed to, in their language, outside quiet hours; once per step.", IV),
    "PromiseToPayRecorded": ev(DS, ["invoice_id", "promise_on"],
        {"invoice_id": U7, "promise_on": DATE},
        "The customer promised to pay by a date; reminders pause until the day after it.", IV),
    "InvoiceDisputed": ev(DS, ["invoice_id", "amount", "currency", "reason"],
        {"invoice_id": U7, "line": INT0, "amount": MONEY, "currency": CUR, "reason": enum("not_received", "wrong_amount", "wrong_items", "quality", "already_paid", "other")},
        "A line or amount of an invoice is disputed; reminders pause for that amount until it is resolved.", IV),
    "InvoiceWrittenOff": ev(S, ["invoice_id", "amount", "currency", "prepared_by", "approved_by"],
        {"invoice_id": U7, "amount": MONEY, "currency": CUR, "prepared_by": ROLE, "approved_by": ROLE},
        "Cloud only: an amount nobody will pay is written off to bad debts, prepared by one person and approved by another.", IV),
    "CreditBalanceChanged": ev(S, ["customer_id", "change", "amount", "currency", "reason"],
        {"customer_id": U7, "change": SMONEY, "amount": MONEY, "currency": CUR, "reason": enum("overpayment", "applied", "refunded"), "invoice_id": U7},
        "Cloud only: a customer's credit balance from an overpayment grew, was used on an invoice or was refunded through the provider; it is never income.", IV),
    "InstalmentPlanAgreed": ev(S, ["invoice_id", "count", "first_on"],
        {"invoice_id": U7, "count": {"type": "integer", "minimum": 1, "maximum": INV["instalments"]["max"]}, "first_on": DATE, "every": enum(*BOOKS["repeat"]["every"])},
        "Cloud only: what is owed on an invoice is split exactly into dated parts.", IV),
    "SubscriptionChanged": ev(S, ["subscription_id", "change"],
        {"subscription_id": U7, "change": enum("start", "upgrade", "downgrade", "pause", "resume", "cancel", "renew"), "amount": SMONEY, "currency": CUR},
        "Cloud only: a subscription (LOSUB-) changed; an upgrade or downgrade is charged or credited for the whole days left in the period.", IV),
    # ---- LynkCRM -------------------------------------------------------------------------------------------------------------
    "CustomerRecordCreated": ev(DS, ["record_id", "kind"],
        {"record_id": U7, "kind": enum(*CRM_KINDS), "org_id": U7, "source": enum("hand", "import", "form", "sale", "booking", "chat", "referral")},
        "A LynkCRM record was created (offline too). Names and contact details stay in the record store and the PII vault; the event carries none.", CR),
    "CustomerRecordsMerged": ev(S, ["kept_id", "merged_ids"],
        {"kept_id": U7, "merged_ids": {"type": "array", "minItems": 1, "maxItems": 20, "uniqueItems": True, "items": U7}, "undone": {"type": "boolean"}},
        "Cloud only: likely duplicates were merged into the oldest record, keeping every activity; it can be undone for 30 days.", CR),
    "CustomerHandedOver": ev(S, ["record_id", "to_user_id"],
        {"record_id": U7, "to_user_id": U7, "reason": enum("staff_change", "territory", "workload", "other")},
        "Cloud only: a customer moved to another owner when staff changed; every past note and activity stays.", CR),
    "CaseOpened": ev(DS, ["case_id", "record_id", "priority"],
        {"case_id": U7, "record_id": U7, "priority": enum(*CRM["cases"]["priorities"]), "from": enum("chat", "call", "email", "form", "visit", "staff")},
        "A service case was opened with its priority; its promised first answer follows the priority (or the organisation's own times on Max).", CR),
    "CaseStateChanged": ev(S, ["case_id", "state"],
        {"case_id": U7, "state": enum(*CRM["cases"]["states"]), "late": {"type": "boolean"}},
        "Cloud only: a case moved on; a case past its promise is marked late, never hidden.", CR),
    "ContactConsentChanged": ev(DS, ["record_id", "channel", "given", "basis"],
        {"record_id": U7, "channel": enum(*CRM["consent"]["channels"]), "given": {"type": "boolean"}, "basis": enum(*CRM["consent"]["bases"])},
        "A person gave or withdrew consent for one channel; withdrawing stops messages at once.", CR),
    "DataRequestReceived": ev(S, ["request_id", "record_id", "kind", "due_on"],
        {"request_id": U7, "record_id": U7, "kind": enum(*CRM["data_requests"]["kinds"]), "due_on": DATE},
        "Cloud only: a person asked to see, correct, delete or move their data; it is answered by the due date of the country's rule.", CR),
    "VisitCheckedIn": ev(DS, ["visit_id", "record_id", "state"],
        {"visit_id": U7, "record_id": U7, "state": enum(*CRM["field"]["visit_states"])},
        "A field visit happened (or was missed), offline too. A position is never recorded, only that the visit happened.", CR),
    "EInvoiceStateChanged": ev(S, ["invoice_id", "state"],
        {"invoice_id": U7, "state": enum("sent", "accepted", "confirmed", "failed"), "reason": enum("format", "seller_tax_number_missing", "totals_do_not_add_up", "rejected_by_tax_office", "network_unavailable")},
        "Cloud only: the tax office's network (provider ledger e_invoice_network) answered for an invoice. Only the network's answer writes accepted, confirmed or failed.", IV),
}


def cmd(name, emits, rejections):
    return {"name": name, "class": "A", "v11": True, "emits": emits, "permission": None, "channels": ["mobile", "web"],
            "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
            "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"], "local_only": True}


COMMANDS = [
    cmd("RecordBill", ["BillRecorded"], ["total_missing", "duplicate_bill"]),
    cmd("SubmitExpenseClaim", ["ExpenseClaimSubmitted"], ["total_missing", "receipt_missing"]),
    cmd("RecordPromiseToPay", ["PromiseToPayRecorded"], ["date_in_past", "invoice_closed"]),
    cmd("DisputeInvoice", ["InvoiceDisputed"], ["amount_over_invoice", "invoice_closed"]),
    cmd("CreateCustomerRecord", ["CustomerRecordCreated"], ["kind_not_allowed", "required_field_missing"]),
    cmd("OpenCase", ["CaseOpened"], ["record_missing"]),
    cmd("ChangeContactConsent", ["ContactConsentChanged"], ["record_missing"]),
    cmd("CheckInVisit", ["VisitCheckedIn"], ["visit_closed"]),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v11 = copy.deepcopy(load("event-payloads.v10.json"))
    v11["$id"] = "lynkomni/event-payloads.v11"
    v11["description"] = ("Contract version 11 (build section 4, step D2b): version 10 plus the LynkAcc, LynkInv and LynkCRM events of OFFICE UPDATE (66): "
                          "bills, expense claims, assets, loss of value, journals and the lock date; documents, reminders, promises to pay, disputes, "
                          "write-offs, credit balances, instalment plans, subscription changes and e-invoice answers; customer records, merges, hand-overs, cases, consent per channel, data requests and field visits. "
                          "Upcaster 10 to 11 in contract/upcasters.v1.json only raises the version.")
    for e in v11["events"].values():
        e["schema_version"] = 11
    for name, e in EVENTS.items():
        if name in v11["events"]:
            raise SystemExit(f"{name} already exists in version 10")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v11["events"][name] = {"schema_version": 11, **e}
    reg = copy.deepcopy(load("command-policy-register.v10.json"))
    reg["$id"] = "lynkomni/command-policy-register.v11"
    reg["description"] = ("Command register version 11 (build section 4, step D2b): version 10's commands unchanged plus recording a bill, "
                          "submitting an expense claim, recording a promise to pay, disputing an invoice, creating a customer record, opening a case, changing consent and checking in a visit, which work offline. Approvals, "
                          "confirmed payments, journals, documents, reminders, write-offs and e-invoice answers are written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v11.json": v11, "command-policy-register.v11.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v11.py)")
        return 1
    print("contract v11 is current" if check else "wrote contract v11")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
