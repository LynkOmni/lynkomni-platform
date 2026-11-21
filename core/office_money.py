"""The office side of gift cards, store credit, deposits, matching and payment costs (SERVICES UPDATE 67.2 and 67.8; section 4 step
F, row 67.17). The register is catalog/office-money.v1.json.

This module is the Python reference; ts/src/officemoney.ts must agree on every case of contract/vectors/office-money.v1.json
(python3 tools/office_money_vectors.py after a change). Money is whole minor units; dates are YYYY-MM-DD strings.

- balances: what each gift card or store credit still holds, and the ones spent below nothing (flagged, never blocked).
- deposit_left: what a deposit still holds after its settlements; a settlement above it is refused.
- match: provider payments against open sales, invoices and bookings: by reference, then one candidate by amount within the window
  (a suggestion), never a guess between two.
- costs: the provider's fee and LynkOmni's part per payment and per month.
- payouts: each payout expected, arrived or late.
"""
import datetime
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "catalog", "office-money.v1.json"), encoding="utf-8") as _f:
    MONEY = json.load(_f)


def _whole(*vals):
    for v in vals:
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("whole minor units only")


def _day(text):
    return datetime.date.fromisoformat(text)


def balances(moves):
    """moves: [{"id", "kind": "issue"|"spend", "amount"}] in order. {"held": {id: left}, "overdrawn": [ids]}."""
    held, over = {}, []
    for mv in moves:
        _whole(mv["amount"])
        if mv["amount"] <= 0:
            raise ValueError("an amount is more than nothing")
        sign = 1 if mv["kind"] == "issue" else -1
        held[mv["id"]] = held.get(mv["id"], 0) + sign * mv["amount"]
        if held[mv["id"]] < 0 and mv["id"] not in over:
            over.append(mv["id"])
    return {"held": held, "overdrawn": over}


def deposit_left(taken, settled):
    """What a deposit still holds; raises when the settlements go beyond what was taken."""
    _whole(taken, *settled)
    left = taken - sum(settled)
    if taken <= 0 or any(a <= 0 for a in settled) or left < 0:
        raise ValueError("a deposit settles at most what it holds")
    return left


def match(payments, targets, window_days=None):
    """payments: [{"ref", "amount", "currency", "on", "target_ref"?}] from the provider; targets: [{"kind", "id", "ref"?, "amount",
    "currency", "on"}] still open. Returns {"matched": [[ref, kind, id]], "suggested": [[ref, kind, id]], "unmatched": [ref]}."""
    window = MONEY["matching"]["window_days"] if window_days is None else window_days
    open_t = list(targets)
    out = {"matched": [], "suggested": [], "unmatched": []}
    by_ref = {t["ref"]: t for t in open_t if t.get("ref")}
    rest = []
    for p in payments:                                   # by reference first, for every payment, so a reference always wins
        _whole(p["amount"])
        t = by_ref.get(p["ref"])
        if t and t in open_t and t["amount"] == p["amount"] and t["currency"] == p["currency"]:
            out["matched"].append([p["ref"], t["kind"], t["id"]]); open_t.remove(t)
        else:
            rest.append(p)
    for p in rest:
        c = [t for t in open_t if t["amount"] == p["amount"] and t["currency"] == p["currency"]
             and abs((_day(p["on"]) - _day(t["on"])).days) <= window]
        if len(c) == 1:
            out["suggested"].append([p["ref"], c[0]["kind"], c[0]["id"]]); open_t.remove(c[0])
        else:
            out["unmatched"].append(p["ref"])
    return out


def costs(lines):
    """lines: [{"ref", "on", "currency", "amount", "provider_fee", "lynkomni_part"}]. Per payment and per month and currency."""
    per, months = [], {}
    for l in lines:
        _whole(l["amount"], l["provider_fee"], l["lynkomni_part"])
        if l["provider_fee"] < 0 or l["lynkomni_part"] < 0 or l["provider_fee"] + l["lynkomni_part"] > l["amount"]:
            raise ValueError("costs are never negative and never more than the payment")
        cost = l["provider_fee"] + l["lynkomni_part"]
        per.append({"ref": l["ref"], "cost": cost, "net": l["amount"] - cost})
        key = l["on"][:7] + "|" + l["currency"]
        mo = months.setdefault(key, {"month": l["on"][:7], "currency": l["currency"], "payments": 0, "amount": 0, "provider_fee": 0, "lynkomni_part": 0})
        mo.update(payments=mo["payments"] + 1, amount=mo["amount"] + l["amount"], provider_fee=mo["provider_fee"] + l["provider_fee"],
                  lynkomni_part=mo["lynkomni_part"] + l["lynkomni_part"])
    return {"payments": per, "months": [months[k] for k in sorted(months)]}


def payouts(scheduled, arrived, today):
    """scheduled: [{"id", "expected_on", "amount", "currency"}]; arrived: {id: date}. Each with its state, by expected date."""
    late = MONEY["payouts"]["late_after_days"]
    rows = []
    for p in sorted(scheduled, key=lambda x: (x["expected_on"], x["id"])):
        _whole(p["amount"])
        if p["id"] in arrived:
            state = "arrived"
        elif (_day(today) - _day(p["expected_on"])).days > late:
            state = "late"
        else:
            state = "expected"
        rows.append({**p, "state": state})
    return rows
