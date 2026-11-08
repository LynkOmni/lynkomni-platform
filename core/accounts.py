"""One global chart of accounts and the double-entry journal as a projection of the event log (Step 0, blueprint 42 A).

The chart lives in contract/chart-of-accounts.v1.json, shared by every language. Every money event posts balanced lines
(debits == credits) in the merchant's base currency, at every tier: tiers decide which reports are shown, never what is
recorded. A country pack may carry `chart_of_accounts`, a mapping from a global code to its local code and name; the
mapping changes how an account is labelled in that country and nothing else. Money is integer minor units; no floats."""
import json, os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "contract", "chart-of-accounts.v1.json"), encoding="utf-8") as _f:
    CHART = json.load(_f)
ACCOUNTS = CHART["accounts"]
POSTINGS = {k: v for k, v in CHART["postings"].items() if k != "description"}
TYPES = ("asset", "liability", "equity", "income", "expense")
DEBIT_NORMAL = ("asset", "expense")          # these grow with a debit; the others grow with a credit


def local_chart(pack=None):
    """The chart as a country sees it: global code -> {code, name, type}. With no mapping the global names are used."""
    mapping = (pack or {}).get("chart_of_accounts") or {}
    out = {}
    for code, a in ACCOUNTS.items():
        m = mapping.get(code, {})
        out[code] = {"code": m.get("code", code), "name": m.get("name", a["name"]), "type": a["type"], "global_code": code}
    return out


def post(event_type, payload, amount_in_base):
    """Balanced journal lines for one event: [(account, debit, credit)]. Returns [] for events that are not money facts."""
    rule = POSTINGS.get(event_type)
    if not rule:
        return []
    if "reverse_of" in rule:
        return [(acct, cr, dr) for acct, dr, cr in post(rule["reverse_of"], payload, amount_in_base)]
    amount = amount_in_base
    if amount == 0:
        return []
    debit, credit = rule.get("debit"), rule.get("credit")
    if "by_method" in rule:
        bm = rule["by_method"]
        debit = bm.get(payload.get("method", "cash"), bm["default"])
    if rule.get("signed") and amount < 0:                    # a surplus is the mirror of a shortfall
        debit, credit, amount = credit, debit, -amount
    return [(debit, amount, 0), (credit, 0, amount)]


def amount_field(event_type):
    return POSTINGS.get(event_type, {}).get("amount", "total_minor")


def journal(events, to_base):
    """events: iterable of {id, type, payload, ts}; to_base(payload, field) -> integer minor units in the base currency.
    Returns [{event_id, type, ts, lines}] with every entry balanced."""
    out = []
    for e in events:
        rule = POSTINGS.get(e["type"])
        if not rule:
            continue
        field = amount_field(rule.get("reverse_of", e["type"]))
        p = e["payload"]
        if field == "cost_total_minor" and "cost_total_minor" not in p:            # stock received: qty x unit cost
            value = p.get("qty", 0) * p.get("cost_minor", 0)
            amount = to_base({**p, "cost_total_minor": value}, "cost_total_minor") if value else 0
        elif field not in p:
            continue
        else:
            amount = to_base(p, field)
        lines = post(e["type"], p, amount)
        if lines:
            assert sum(d for _, d, _ in lines) == sum(c for _, _, c in lines), "journal entry must balance"
            out.append({"event_id": e["id"], "type": e["type"], "ts": e.get("ts"), "lines": lines})
    return out


def trial_balance(entries):
    """{account: balance} where a balance is positive on the account's normal side (assets and expenses: debit)."""
    bal = {}
    for en in entries:
        for acct, dr, cr in en["lines"]:
            bal[acct] = bal.get(acct, 0) + (dr - cr if ACCOUNTS[acct]["type"] in DEBIT_NORMAL else cr - dr)
    return bal


def balanced(entries):
    return all(sum(d for _, d, _ in e["lines"]) == sum(c for _, _, c in e["lines"]) for e in entries)


def profit(entries):
    """Income less expenses from the journal (the same number LynkAcc's summary must agree with)."""
    tb = trial_balance(entries)
    income = sum(v for a, v in tb.items() if ACCOUNTS[a]["type"] == "income")
    expense = sum(v for a, v in tb.items() if ACCOUNTS[a]["type"] == "expense")
    return income - expense
