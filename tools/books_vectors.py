#!/usr/bin/env python3
"""Shared vectors for LynkAcc's rules (OFFICE UPDATE, master blueprint 66.2): core/books.py is the reference and ts/src/books.ts
must agree on every case. Also writes the register and the chart of accounts (version 2) into ts/src/books.generated.ts.
  python3 tools/books_vectors.py          writes contract/vectors/books.v1.json and ts/src/books.generated.ts
  python3 tools/books_vectors.py --check  fails when either file is out of date (tests/test_books.py)"""
import itertools, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import accounts as AC  # noqa: E402
from core import books as B  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "books.v1.json")
TS = os.path.join(ROOT, "ts", "src", "books.generated.ts")


def entries():
    """A small year of books: owner puts money in, sales, a bill, an asset bought and losing value, a loan and its first
    payment, a payout and a transfer between cash accounts."""
    js = [
        [["1020", 1000000, 0], ["3000", 0, 1000000]],
        [["1000", 250000, 0], ["4000", 0, 250000]],
        [["5000", 90000, 0], ["1200", 0, 90000]],
        [["6000", 40000, 0], ["2000", 0, 40000]],
        [["2000", 40000, 0], ["1020", 0, 40000]],
        [["1500", 600000, 0], ["1020", 0, 600000]],
        [["6500", 120000, 0], ["1510", 0, 120000]],
        [["1020", 500000, 0], ["2600", 0, 500000]],
        B.loan_lines(B.loan_schedule(500000, 1200, 12)[0]),
        [["1020", 100000, 0], ["1000", 0, 100000]],
        [["1200", 150000, 0], ["2000", 0, 150000]],
    ]
    return [{"lines": [list(l) for l in j]} for j in js]


def build():
    taxes = [[], [{"kind": "sales", "rate_bp": 1800}], [{"kind": "sales", "rate_bp": 1600}, {"kind": "import", "rate_bp": 250}],
             [{"kind": "sales", "rate_bp": 1800}, {"kind": "withholding", "rate_bp": 300}], [{"kind": "reverse_charge", "rate_bp": 1800}],
             [{"kind": "sales", "rate_bp": 750}, {"kind": "sales", "rate_bp": 500}, {"kind": "withholding", "rate_bp": 1500}]]
    tax = [{"amount": a, "taxes": t, "included": inc, "expect": B.tax_line(a, t, inc)}
           for a in (0, 1, 999, 10000, 118000, 123457, 99999999) for t in taxes for inc in (False, True)]
    moves = [{"state": s, "action": a, "expect": B.bill_move(s, a)} for s in B.BOOKS["bills"]["states"]
             for a in ("submit", "approve", "reject", "schedule", "pay_part", "pay_all", "dispute", "resolve", "void", "unschedule", "made_up")]
    po = [{"sku": "A", "qty": 10000, "price_minor": 500}, {"sku": "B", "qty": 2000, "price_minor": 1200}, {"sku": "C", "qty": 1000, "price_minor": 100}]
    rec = [{"sku": "A", "qty": 6000}, {"sku": "A", "qty": 4000}, {"sku": "B", "qty": 1500}]
    bills = [[{"sku": "A", "qty": 10000, "price_minor": 500}], [{"sku": "A", "qty": 10000, "price_minor": 510}], [{"sku": "B", "qty": 2000, "price_minor": 1200}],
             [{"sku": "C", "qty": 1000, "price_minor": 100}], [{"sku": "D", "qty": 1, "price_minor": 1}], [{"sku": "A", "qty": 11000, "price_minor": 600}, {"sku": "B", "qty": 1000, "price_minor": 1200}]]
    match = [{"bill": bl, "tol": t, "expect": B.match3(po, rec, bl, t)} for bl in bills for t in (0, 200)]
    spends = [{"id": "s1", "amount": 4500, "day": 10}, {"id": "s2", "amount": 4500, "day": 11}, {"id": "s3", "amount": 900, "day": 20}, {"id": "s4", "amount": 77, "day": 1}]
    receipts = [{"id": "r1", "amount": 4500, "day": 12}, {"id": "r2", "amount": 900, "day": 24}, {"id": "r3", "amount": 4500, "day": 11}]
    loans = [{"p": p, "bp": bp, "n": n, "expect": B.loan_schedule(p, bp, n)} for p, bp, n in ((500000, 1200, 12), (100000, 0, 7), (99999, 2450, 36), (1, 500, 3), (250000000, 1875, 60))]
    deps = [{"c": c, "r": r, "y": y, "m": m, "bp": bp, "expect": B.depreciation(c, r, y, m, bp)}
            for c, r, y in ((600000, 0, 5), (100001, 1000, 3), (50000, 50000, 2), (10, 0, 4), (1000, 2000, 3)) for m, bp in (("straight_line", 0), ("reducing_balance", 4000))]
    dates = [{"start": s, "every": e, "count": 6, "expect": B.repeat_dates(s, e, 6)}
             for s in ("2026-01-31", "2026-01-15", "2024-02-29", "2026-11-30", "2026-12-31") for e in ("week", "month", "quarter", "year")]
    lines = [{"id": "l1", "amount": 25000, "day": 5, "ref": "PAY LOINV-7KX2 thanks"}, {"id": "l2", "amount": 25000, "day": 6, "ref": ""},
             {"id": "l3", "amount": 1000, "day": 30, "ref": "fee"}, {"id": "l4", "amount": 25000, "day": 40, "ref": ""}]
    items = [{"id": "i1", "amount": 25000, "day": 6, "ref": ""}, {"id": "i2", "amount": 25000, "day": 3, "ref": "LOINV-7KX2"}, {"id": "i3", "amount": 1000, "day": 34, "ref": ""}]
    ents = entries()
    tb = AC.trial_balance([{"lines": [tuple(l) for l in e["lines"]]} for e in ents])
    open_items = [{"id": "a", "foreign_minor": 10000, "booked_minor": 1300000, "side": "owed_to_us"}, {"id": "b", "foreign_minor": 5000, "booked_minor": 640000, "side": "we_owe"},
                  {"id": "c", "foreign_minor": 333, "booked_minor": 43000, "side": "owed_to_us"}]
    smoves = [{"kind": "in", "qty": 10000, "unit_cost_minor": 300, "extra_minor": 500}, {"kind": "in", "qty": 5000, "unit_cost_minor": 420},
              {"kind": "out", "qty": 4000}, {"kind": "out", "qty": 7000}, {"kind": "in", "qty": 3000, "unit_cost_minor": 399, "extra_minor": 1}, {"kind": "out", "qty": 9000}]
    group = [{"id": "hold", "tb": {"1020": 500000, "1600": 120000, "3000": 400000, "4000": 300000, "5000": 80000}, "num": 1, "den": 1},
             {"id": "sub", "tb": {"1020": 900, "2700": 1000, "3000": 500, "4000": 900, "6000": 1500}, "num": 120, "den": 1, "share_bp": 7500}]
    return {"version": 1, "description": "LynkAcc's rules (OFFICE UPDATE 66.2). core/books.py is the reference; ts/src/books.ts must agree.",
            "round_div": [{"n": n, "d": d, "expect": B.round_div(n, d)} for n, d in itertools.product((0, 1, 5, 15, 25, -5, -15, 99999999999, -7), (1, 2, 3, 10, 7))],
            "split": [{"t": t, "p": p, "expect": B.split(t, p)} for t in (0, 10, 101, -101, 7) for p in (0, 1, 3, 4)],
            "allocate": [{"t": t, "w": w, "expect": B.allocate(t, w)} for t in (100, 1001, -55) for w in ([], [1], [1, 1, 1], [1800, 250], [0, 0])],
            "tax": tax, "moves": moves,
            "approvers": [{"amount": a, "expect": B.approvers(a)} for a in (0, 50000, 50001, 9999999)],
            "may_approve": [{"p": p, "a": a, "expect": B.may_approve(p, a)} for p, a in (("u1", "u1"), ("u1", "u2"), ("u1", None))],
            "po": po, "received": rec, "match": match,
            "early": [{"a": a, "bp": bp, "w": w, "after": d, "expect": B.early_discount(a, bp, w, d)} for a, bp, w, d in ((100000, 200, 10, 5), (100000, 200, 10, 11), (333, 150, 0, 0))],
            "mileage": [{"km": k, "rate": r, "expect": B.mileage(k, r)} for k, r in ((12500, 300), (1, 300), (999999, 47), (0, 300))],
            "card": {"spends": spends, "receipts": receipts, "expect": B.card_match(spends, receipts)},
            "depreciation": deps, "loans": loans,
            "loan_lines": [{"row": r, "m": m, "expect": B.loan_lines(r, m)} for r in B.loan_schedule(500000, 1200, 2) + B.loan_schedule(9, 0, 2) for m in ("bank", "mobile_money")],
            "disposal": [{"c": c, "s": s, "p": p, "m": m, "expect": B.disposal(c, s, p, m)} for c, s, p, m in ((600000, 240000, 400000, "bank"), (600000, 240000, 300000, "cash"), (600000, 600000, 0, "bank"), (1000, 0, 1000, "mobile_money"))],
            "dates": dates, "reversal": {d: B.reversal_date(d) for d in ("2026-01-31", "2026-12-31", "2024-02-28", "2026-02-28")},
            "may_post": [{"d": d, "lock": l, "expect": B.may_post(d, l)} for d in ("2026-03-31", "2026-04-01") for l in (None, "2026-03-31")],
            "two_person": [{"k": k, "p": p, "a": a, "expect": B.two_person(k, p, a)} for k in ("manual_journal", "write_off", "bill") for p, a in (("u1", "u1"), ("u1", "u2"), ("u1", None))],
            "close": [{"done": d, "expect": B.close_missing(d)} for d in ([], ["bank_matched", "tax_reviewed"], list(B.BOOKS["closing"]["checklist"]))],
            "bank": {"lines": lines, "items": items, "expect": B.bank_match(lines, items)},
            "entries": ents, "tb": tb, "statements": B.statements(tb), "year_end": B.year_end_lines(tb),
            "cash_flow": B.cash_flow(ents), "equity": B.equity_changes(0, [{"lines": [tuple(l) for l in e["lines"]]} for e in ents]),
            "revalue": [{"items": open_items, "num": n, "den": d, "expect": B.revalue(open_items, n, d)} for n, d in ((130, 1), (1281, 10), (127, 1))],
            "stock": [{"moves": smoves, "method": m, "expect": B.stock_cost(smoves, m)} for m in ("fifo", "average")],
            "group": [{"entities": group, "ic": ic, "expect": B.consolidate(group, ic)} for ic in (0, 50000)],
            "mirror": {"invoice": {"from": "hold", "to": "sub", "number": "A-17", "lines": [{"sku": "A", "qty": 1000}], "total_minor": 5000, "currency": "USD"}},
            "budget": [{"b": b, "a": a, "expect": B.budget_vs_actual(b, a)} for b, a in (({"sales": 100000, "travel": 0}, {"sales": 87500, "rent": 3000}), ({}, {}))],
            "funds": [{"f": f, "p": p, "expect": B.fund_spend_ok(f, p)} for f in ({"restricted": True, "purpose": "school_meals"}, {"restricted": False}) for p in ("school_meals", "rent")],
            "dims": [{"d": d, "expect": B.dims_ok(d)} for d in ({}, {"project": "p1", "fund": "f1"}, {"colour": "red"})],
            "tools": {k: B.entity_tools(k) for k in ("household", "nonprofit", "school", "public_body", "cooperative", "spaceship")}}


def ts_source():
    reg = json.dumps(B.BOOKS, ensure_ascii=False, separators=(",", ":"))
    chart = json.dumps(AC.ACCOUNTS, ensure_ascii=False, separators=(",", ":"))
    return ("// GENERATED by tools/books_vectors.py from catalog/books.v1.json and contract/chart-of-accounts.v2.json. Do not edit by hand.\n"
            "import type { BooksRegister, Account } from \"./books.js\";\n"
            f"export const BOOKS = {reg} as unknown as BooksRegister;\n"
            f"export const CHART = {chart} as Record<string, Account>;\n")


def main():
    vec = json.dumps(build(), ensure_ascii=False, indent=None, separators=(",", ":")) + "\n"
    ts = ts_source()
    if "--check" in sys.argv:
        stale = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != want]
        if stale:
            print("out of date:", ", ".join(os.path.relpath(p, ROOT) for p in stale), "- run python3 tools/books_vectors.py")
            sys.exit(1)
        return
    for p, text in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
