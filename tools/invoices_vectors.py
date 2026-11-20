#!/usr/bin/env python3
"""Shared vectors for LynkInv's rules (OFFICE UPDATE, master blueprint 66.3): core/invoices.py is the reference and
ts/src/invoices.ts must agree on every case. Also writes the register into ts/src/invoices.generated.ts.
  python3 tools/invoices_vectors.py          writes contract/vectors/invoices.v1.json and ts/src/invoices.generated.ts
  python3 tools/invoices_vectors.py --check  fails when either file is out of date (tests/test_invoices.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import invoices as I  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "invoices.v1.json")
TS = os.path.join(ROOT, "ts", "src", "invoices.generated.ts")

PACKS = {
    "unknown": {"office": {"late_fees": {"allowed": None}, "e_invoice": {"required": None}, "keep_years": None, "buyer_issued_invoices": None}},
    "allowed": {"flags": {"tax_invoice_confirmed": True}, "office": {"late_fees": {"allowed": True, "max_rate_bp_year": 1200, "fixed_fee_minor": 500},
                "e_invoice": {"required": True}, "keep_years": 7, "buyer_issued_invoices": True}},
    "no_fees": {"office": {"late_fees": {"allowed": False, "max_rate_bp_year": 900}, "e_invoice": {"required": False}, "keep_years": 5}},
    "none": None,
}


def build():
    kinds = list(I.INV["documents"])
    make = [{"from": f, "to": t, "pack": p, "expect": I.may_make(f, t, PACKS[p])} for f in [None] + kinds for t in kinds for p in ("unknown", "allowed")]
    moves = [{"state": s, "action": a, "expect": I.inv_move(s, a)} for s in I.INV["states"]
             for a in ("submit", "issue", "approve", "reject", "view", "pay_part", "pay_all", "due", "dispute", "resolve", "write_off", "credit_all", "void_unpaid", "void", "made_up")]
    lines = [[{"qty": 2000, "unit_minor": 1500}],
             [{"qty": 1500, "unit_minor": 999, "discount_minor": 100}, {"qty": 333, "unit_minor": 1001}],
             [{"qty": 1000, "unit_minor": 118000, "taxes": [{"kind": "sales", "rate_bp": 1800}]}, {"qty": 1000, "unit_minor": 5000, "taxes": []}],
             [{"qty": 12500, "unit_minor": 777, "taxes": [{"kind": "sales", "rate_bp": 1600}, {"kind": "withholding", "rate_bp": 500}]}]]
    doc_taxes = [[], [{"kind": "sales", "rate_bp": 1800}], [{"kind": "sales", "rate_bp": 750}, {"kind": "import", "rate_bp": 250}, {"kind": "withholding", "rate_bp": 300}]]
    tot = [{"lines": ls, "taxes": t, "included": inc, "bp": bp, "expect": I.totals(ls, t, inc, bp)} for ls in lines for t in doc_taxes for inc in (False, True) for bp in (0, 1000)]
    rem = [{"due": "2026-03-10", "today": td, "sent": s, "promise": p, "disputed": d, "expect": I.reminder_due("2026-03-10", td, s, p, d)}
           for td in ("2026-03-01", "2026-03-07", "2026-03-10", "2026-03-11", "2026-03-24", "2026-04-09", "2026-06-01")
           for s in ([], ["before"], ["friendly"], ["friendly", "firm"], ["friendly", "firm", "final"])
           for p, d in ((None, False), ("2026-03-30", False), (None, True))]
    fees = [{"amount": a, "days": d, "pack": p, "owner": o, "expect": I.late_fee(a, d, PACKS[p], o)}
            for a in (100000, 1) for d in (0, 1, 30, 365) for p in PACKS for o in (None, 600, 5000)]
    items = [{"id": "a", "outstanding": 1000, "due": "2026-03-10"}, {"id": "b", "outstanding": 2500, "due": "2026-01-01"},
             {"id": "c", "outstanding": 400, "due": "2026-02-20"}, {"id": "d", "outstanding": 0, "due": "2025-12-01"}, {"id": "e", "outstanding": 999, "due": "2025-11-01"}]
    return {"version": 1, "description": "LynkInv's rules (OFFICE UPDATE 66.3). core/invoices.py is the reference; ts/src/invoices.ts must agree.",
            "packs": PACKS, "make": make, "moves": moves,
            "labels": {p: I.label_word(PACKS[p]) for p in PACKS},
            "due": [{"issued": d, "term": t, "expect": I.due_date(d, t)} for d in ("2026-01-31", "2026-02-15", "2026-12-20", "2024-02-29") for t in [None] + list(I.INV["terms"]["library"])],
            "totals": tot,
            "credit": [{"limit": l, "open": o, "new": n, "expect": I.credit_check(l, o, n)} for l in (None, 100000) for o, n in ((0, 50000), (60000, 50000), (100000, 0))],
            "approval": [{"total": t, "over": o, "prep": p, "named": nm, "expect": I.needs_approval(t, o, p, nm)}
                         for t in (100, 500000, 500001) for o in (None, 100) for p, nm in ((None, []), ("u2", ["u2"]), ("u1", ["u2"]))],
            "reminders": rem, "fees": fees,
            "ageing": {"items": items, "today": "2026-04-15", "expect": I.ageing(items, "2026-04-15")},
            "pay": [{"amount": a, "order": o, "expect": I.apply_payment(a, items, o)} for a in (0, 1500, 3900, 9999) for o in (None, ["c", "a"], ["zz"])],
            "instalments": [{"t": t, "n": n, "start": s, "every": e, "expect": I.instalments(t, n, s, e)}
                            for t, n in ((100000, 3), (101, 4), (5, 25), (1000, 0)) for s, e in (("2026-01-31", "month"), ("2026-03-02", "week"))],
            "prorate": [{"o": o, "n": n, "p": p, "l": l, "expect": I.prorate(o, n, p, l)} for o, n in ((1900, 4900), (4900, 1900), (1000, 1000)) for p, l in ((30, 0), (30, 17), (31, 31))],
            "usage": [{"qty": q, "bands": b, "mode": m, "expect": I.usage(q, b, m)}
                      for q in (0, 500, 1000000, 1500000, 12345678)
                      for b in ([{"up_to": None, "unit_minor": 25}], [{"up_to": 1000000, "unit_minor": 50}, {"up_to": 5000000, "unit_minor": 30}, {"up_to": None, "unit_minor": 10}])
                      for m in ("per_unit", "graduated", "volume")],
            "stages": [{"t": t, "s": s, "expect": I.stages(t, s)} for t in (1000000, 333) for s in ([3000, 4000, 3000], [10000], [2500, 2500, 2500, 2500])],
            "retainer": [{"b": b, "a": a, "expect": I.retainer_draw(b, a)} for b, a in ((50000, 20000), (50000, 70000), (0, 100))],
            "base": [{"a": a, "n": n, "d": d, "expect": I.to_base(a, n, d)} for a, n, d in ((10000, 1281, 10), (333, 130, 1), (-500, 7, 3))],
            "cash": [{"a": a, "s": s, "expect": I.cash_round(a, s)} for a in (1234, 1235, 1237, 100) for s in (1, 5, 10, 50)],
            "einvoice": {p: I.e_invoice_required(PACKS[p]) for p in PACKS},
            "keep": {p: I.keep_years(PACKS[p]) for p in PACKS},
            "languages": [{"l": l, "expect": I.languages_ok(l)} for l in ([], ["en"], ["en", "fr"], ["en", "fr", "rw"], ["en", "en"])]}


def ts_source():
    reg = json.dumps(I.INV, ensure_ascii=False, separators=(",", ":"))
    return ("// GENERATED by tools/invoices_vectors.py from catalog/invoices.v1.json. Do not edit by hand.\n"
            "import type { InvoicesRegister } from \"./invoices.js\";\n"
            f"export const INVOICES = {reg} as unknown as InvoicesRegister;\n")


def main():
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_source()
    if "--check" in sys.argv:
        stale = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != want]
        if stale:
            print("out of date:", ", ".join(os.path.relpath(p, ROOT) for p in stale), "- run python3 tools/invoices_vectors.py")
            sys.exit(1)
        return
    for p, text in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
