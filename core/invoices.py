"""LynkInv's rules (OFFICE UPDATE, master blueprint 66.3; section 4 step D2a), read from catalog/invoices.v1.json, on top of
LynkAcc's rules in core/books.py (taxes on a line, exact splits, dates).

The documents and what each may be made from, the invoice states, payment terms and due dates, totals with several taxes and
discounts, the credit-limit warning, stepped reminders with promise-to-pay and disputes, late fees only where the law allows,
ageing, paying several invoices at once with a credit balance, instalment plans, subscription changes for the days left,
billing by use, project stages and retainers, approval before sending, another currency, cash rounding, e-invoices and keeping
times. A country's own rule comes from its pack's office settings (tools/country_office.py); while unknown, the safe default
applies. Money is integer minor units; quantities are integer thousandths.

This module is the Python reference; ts/src/invoices.ts must agree on every case of contract/vectors/invoices.v1.json
(python3 tools/invoices_vectors.py after a change)."""
import datetime as _dt
import json, os

from core import books as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "invoices.v1.json"), encoding="utf-8") as _f:
    INV = json.load(_f)


def _office(pack):
    return (pack or {}).get("office") or {}


def _day(s):
    return _dt.date.fromisoformat(s).toordinal()


def _iso(n):
    return _dt.date.fromordinal(n).isoformat()


# ---- documents and states ----------------------------------------------------------------------------------------------------
def may_make(from_kind, to_kind, pack=None):
    """Whether a document of to_kind may be made from one of from_kind (None: made on its own)."""
    d = INV["documents"].get(to_kind)
    if not d or not doc_allowed(to_kind, pack):
        return False
    return from_kind is None or from_kind in d["from"]


def doc_allowed(kind, pack=None):
    """A kind that exists only where the country allows it (a buyer-issued invoice) is off while the pack does not say yes."""
    d = INV["documents"].get(kind)
    if not d:
        return False
    flag = d.get("only_where")
    return not flag or _office(pack).get(flag) is True


def inv_move(state, action):
    return INV["moves"].get(state, {}).get(action)


def label_word(pack=None):
    """'tax invoice' only when the country's workflow is confirmed in writing."""
    return "iv_doc_tax_invoice" if ((pack or {}).get("flags") or {}).get("tax_invoice_confirmed") is True else "iv_doc_invoice"


# ---- terms and totals --------------------------------------------------------------------------------------------------------
def due_date(issued, term=None):
    """The due date from a payment term of the library."""
    t = INV["terms"]["library"][term or INV["terms"]["default"]]
    d = _dt.date.fromisoformat(issued)
    if t == "eom":
        return _dt.date(d.year, d.month, B._days_in_month(d.year, d.month)).isoformat()
    if t == "eonm":
        y, m = d.year + (d.month == 12), d.month % 12 + 1
        return _dt.date(y, m, B._days_in_month(y, m)).isoformat()
    return _iso(_day(issued) + t)


def totals(lines, taxes=(), included=False, discount_bp=0):
    """An invoice's totals. lines: [{"qty" (thousandths), "unit_minor", "discount_minor", "taxes"}]; a line's own taxes win
    over the invoice's. A discount per invoice (basis points) is taken off each line before tax."""
    out, net, total, withheld, reverse, by_kind = [], 0, 0, 0, 0, {}
    for ln in lines:
        amount = B.round_div(ln["qty"] * ln["unit_minor"], 1000) - ln.get("discount_minor", 0)
        amount -= B.round_div(amount * discount_bp, 10000)
        t = B.tax_line(amount, ln.get("taxes", list(taxes)), included)
        out.append(t)
        net += t["net"]; total += t["total"]; withheld += t["withheld"]; reverse += t["reverse_charge"]
        for x in t["taxes"]:
            by_kind[x["kind"]] = by_kind.get(x["kind"], 0) + x["amount"]
    return {"lines": out, "net": net, "taxes": dict(sorted(by_kind.items())), "total": total, "withheld": withheld, "to_pay": total - withheld, "reverse_charge": reverse}


def credit_check(limit, open_balance, new_total):
    """A warning (never a block) before an invoice would pass the customer's credit limit."""
    if limit is None:
        return {"warn": False, "over_by": 0}
    over = open_balance + new_total - limit
    return {"warn": over > 0, "over_by": max(over, 0)}


def needs_approval(total, over_minor=None, preparer=None, named=()):
    """An invoice above the owner's amount, or prepared by a person the owner named, waits for approval before sending."""
    over = INV["approval"]["default_over_minor"] if over_minor is None else over_minor
    return total > over or (preparer is not None and preparer in named)


# ---- getting paid on time ----------------------------------------------------------------------------------------------------
def reminder_due(due, today, sent=(), promise=None, disputed=False):
    """The reminder to send today, or None: 'before' a few days before the due date, then friendly, firm and final; each once;
    a promise-to-pay date pauses them until the day after it; a fully disputed invoice is not reminded."""
    r = INV["reminders"]
    if disputed or (promise is not None and today <= promise):
        return None
    late = _day(today) - _day(due)
    if late < 0:
        return "before" if -late <= r["before_due_days"] and "before" not in sent else None
    reached = [s["step"] for s in r["steps"] if late >= s["after_due_days"]]
    return reached[-1] if reached and reached[-1] not in sent else None


def late_fee(amount, days_late, pack=None, owner_rate_bp=None):
    """A late fee only where the law allows it: the pack's fixed fee plus interest for the days late, never above the pack's
    rate (the owner may set a lower one). Unknown or not allowed: nothing."""
    lf = _office(pack).get("late_fees") or {}
    if lf.get("allowed") is not True or days_late <= 0:
        return {"allowed": lf.get("allowed") is True, "fee": 0}
    rate = lf.get("max_rate_bp_year") or 0
    if owner_rate_bp is not None:
        rate = min(rate, owner_rate_bp)
    fee = (lf.get("fixed_fee_minor") or 0) + B.round_div(amount * rate * days_late, 10000 * 365)
    return {"allowed": True, "fee": fee}


def ageing(items, today):
    """What is owed by how late it is: [{"id", "outstanding", "due"}] into the register's buckets."""
    buckets = INV["ageing"]["buckets"]
    tot = {b["id"]: 0 for b in buckets}
    rows = []
    for it in items:
        late = max(_day(today) - _day(it["due"]), 0)
        bid = next(b["id"] for b in buckets if b["up_to"] is None or late <= b["up_to"])
        tot[bid] += it["outstanding"]
        rows.append({"id": it["id"], "bucket": bid, "days_late": late})
    return {"totals": tot, "items": rows}


def apply_payment(amount, invoices, order=None):
    """One payment across several invoices: the oldest due first, or the customer's own order of ids; what is left is a
    credit balance."""
    todo = [i for i in invoices if i["outstanding"] > 0]
    if order:
        pos = {k: n for n, k in enumerate(order)}
        todo = sorted([i for i in todo if i["id"] in pos], key=lambda i: pos[i["id"]])
    else:
        todo = sorted(todo, key=lambda i: (i["due"], i["id"]))
    left, used = amount, []
    for i in todo:
        if left <= 0:
            break
        take = min(left, i["outstanding"])
        used.append({"id": i["id"], "amount": take, "paid": take == i["outstanding"]})
        left -= take
    return {"used": used, "credit_balance": left}


def instalments(total, count, start, every="month"):
    if count <= 0 or count > INV["instalments"]["max"]:
        return []
    return [{"date": d, "amount": a} for d, a in zip(B.repeat_dates(start, every, count), B.split(total, count))]


# ---- ways to bill ------------------------------------------------------------------------------------------------------------
def prorate(old_price, new_price, period_days, days_left):
    """An upgrade (charge) or downgrade (credit, negative) for the whole days left in the period."""
    if period_days <= 0 or not 0 <= days_left <= period_days:
        raise ValueError("days left must be within the period")
    return B.round_div((new_price - old_price) * days_left, period_days)


def usage(qty, bands, mode="graduated"):
    """Billing by use. qty in thousandths; bands: [{"up_to" (thousandths or None), "unit_minor"}] in order."""
    if not bands or qty <= 0:
        return 0
    if mode == "per_unit":
        return B.round_div(qty * bands[0]["unit_minor"], 1000)
    if mode == "volume":
        band = next(b for b in bands if b["up_to"] is None or qty <= b["up_to"])
        return B.round_div(qty * band["unit_minor"], 1000)
    amount, low = 0, 0
    for b in bands:
        top = qty if b["up_to"] is None else min(qty, b["up_to"])
        if top > low:
            amount += B.round_div((top - low) * b["unit_minor"], 1000)
        if b["up_to"] is None or qty <= b["up_to"]:
            break
        low = b["up_to"]
    return amount


def stages(total, shares_bp):
    """A project billed in stages whose shares add up to the whole (10000 basis points); the amounts add up exactly."""
    if sum(shares_bp) != 10000:
        raise ValueError("stage shares must add up to 10000")
    return B.allocate(total, shares_bp)


def retainer_draw(balance, amount):
    """Work drawn from a retainer; what the retainer does not cover is invoiced."""
    used = min(balance, amount)
    return {"used": used, "left": balance - used, "to_invoice": amount - used}


# ---- currency, rounding, e-invoices, keeping, languages ----------------------------------------------------------------------
def to_base(amount, num, den):
    """An amount in the customer's currency in the base currency at the recorded rate num/den."""
    return B.round_div(amount * num, den)


def cash_round(amount, step):
    """Cash rounding to the country's step (shown as its own line); a step of 1 changes nothing."""
    if step <= 1:
        return {"amount": amount, "rounding": 0}
    r = B.round_div(amount, step) * step
    return {"amount": r, "rounding": r - amount}


def e_invoice_required(pack=None):
    """True or False when the pack says; None while unknown."""
    return (_office(pack).get("e_invoice") or {}).get("required")


def keep_years(pack=None):
    return _office(pack).get("keep_years") or INV["keeping"]["default_years"]


def languages_ok(langs):
    return 1 <= len(langs) <= INV["languages"]["max_on_one"] and len(set(langs)) == len(langs)
